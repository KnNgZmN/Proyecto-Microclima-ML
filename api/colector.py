"""Control del proceso colector de Arduino (src/arduino_collector.py).

El backend lanza el colector como subproceso independiente; la comunicación
con el front ocurre a través de data/live/latest.json, igual que en la
aplicación de Streamlit.
"""

import subprocess
import sys
import threading

from api import config, servicios

MODO_REAL = "real"
MODO_SIMULACION = "simulacion"

_LECTURAS_SIMULACION = "99999"
_INTERVALO_SIMULACION = "3"

_lock = threading.Lock()
_estado: dict = {"proceso": None, "modo": None, "localidad_id": None, "error": None}


def listar_puertos() -> list[str]:
    """Puertos serie detectados en el equipo (lista vacía si pyserial falla)."""
    try:
        import serial.tools.list_ports

        return [puerto.device for puerto in serial.tools.list_ports.comports()]
    except (ImportError, OSError):
        return []


def _en_ejecucion() -> bool:
    """Indica si el subproceso sigue vivo."""
    proceso = _estado["proceso"]
    return proceso is not None and proceso.poll() is None


def _comando(modo: str, puerto: str, baud: int, localidad_id: int) -> list[str]:
    """Arma la línea de comando del colector según el modo solicitado."""
    base = [sys.executable, config.COLLECTOR_PATH, "--localidad", str(localidad_id), "--predict"]
    if modo == MODO_SIMULACION:
        return base + ["--simulate", "--lecturas", _LECTURAS_SIMULACION,
                       "--intervalo", _INTERVALO_SIMULACION]
    return base + ["--port", puerto, "--baud", str(baud)]


def _recoger_error() -> None:
    """Traduce la salida de error de un proceso terminado a un mensaje legible."""
    proceso = _estado["proceso"]
    if proceso is None or proceso.poll() is None:
        return

    codigo = proceso.poll()
    salida = ""
    if proceso.stderr is not None:
        salida = proceso.stderr.read().decode("utf-8", errors="ignore").strip()

    if "No se pudo abrir el puerto" in salida or "SerialException" in salida:
        _estado["error"] = ("No se pudo abrir el puerto serial. Verifica que el Arduino "
                            "esté conectado y que el puerto sea el correcto.")
    elif salida:
        _estado["error"] = f"Error del colector (código {codigo}): {salida}"
    else:
        _estado["error"] = f"El colector terminó inesperadamente (código {codigo})."

    _estado["proceso"] = None


def iniciar(modo: str, puerto: str, baud: int, localidad_id: int) -> dict:
    """Arranca el colector en modo real o simulación."""
    if modo not in (MODO_REAL, MODO_SIMULACION):
        raise servicios.SolicitudInvalida("Modo de colector no reconocido")
    servicios.obtener_localidad(localidad_id)

    with _lock:
        if _en_ejecucion():
            raise servicios.SolicitudInvalida("El colector ya está en ejecución")

        puertos = listar_puertos()
        if modo == MODO_REAL and puertos and puerto not in puertos:
            raise servicios.SolicitudInvalida(
                f"Puerto {puerto} no detectado. Disponibles: {', '.join(puertos)}"
            )

        _estado["error"] = None
        _estado["proceso"] = subprocess.Popen(  # noqa: S603 - comando construido internamente
            _comando(modo, puerto, baud, localidad_id),
            stdout=subprocess.DEVNULL,  # la salida útil se publica en latest.json
            stderr=subprocess.PIPE,
        )
        _estado["modo"] = modo
        _estado["localidad_id"] = localidad_id
        return _instantanea()


def detener() -> dict:
    """Termina el colector si está corriendo."""
    with _lock:
        if _en_ejecucion():
            _estado["proceso"].terminate()
        _estado["proceso"] = None
        _estado["modo"] = None
        _estado["error"] = None
        return _instantanea()


def estado() -> dict:
    """Estado actual del colector, actualizando errores de procesos caídos."""
    with _lock:
        if not _en_ejecucion():
            _recoger_error()
        return _instantanea()


def _instantanea() -> dict:
    """Vista serializable del estado interno."""
    proceso = _estado["proceso"]
    activo = proceso is not None and proceso.poll() is None
    return {
        "activo": activo,
        "modo": _estado["modo"] if activo else None,
        "pid": proceso.pid if activo else None,
        "localidad_id": _estado["localidad_id"],
        "error": _estado["error"],
        "puertos": listar_puertos(),
    }
