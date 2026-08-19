"""Control del proceso colector de Arduino (src/arduino_collector.py).

El backend lanza el colector como subproceso independiente; la comunicación
con el front ocurre a través de data/live/latest.json, igual que en la
aplicación de Streamlit.
"""

import re
import subprocess
import sys
import threading

from api import config, servicios

MODO_REAL = "real"
MODO_SIMULACION = "simulacion"

# Formato aceptado para el puerto serie: COM1-COM999 en Windows o /dev/ttyXXX
# en Linux/macOS. Se valida con lista blanca porque el valor llega por HTTP y
# termina en la línea de comandos del subproceso.
PATRON_PUERTO = re.compile(r"^(COM[0-9]{1,3}|/dev/tty[A-Za-z0-9._-]{1,20})$")

# Velocidades estándar del Arduino; cualquier otra se rechaza.
BAUDIOS_VALIDOS = (9600, 19200, 38400, 57600, 115200)

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


def _validar_puerto(puerto: str) -> str:
    """Comprueba que el puerto tenga un formato de dispositivo serie conocido."""
    if not PATRON_PUERTO.match(puerto):
        raise servicios.SolicitudInvalida(
            "Puerto serial no válido: usa el formato COM3 o /dev/ttyUSB0"
        )
    return puerto


def _validar_baud(baud: int) -> int:
    """Comprueba que la velocidad esté entre las estándar del Arduino."""
    if baud not in BAUDIOS_VALIDOS:
        permitidos = ", ".join(str(valor) for valor in BAUDIOS_VALIDOS)
        raise servicios.SolicitudInvalida(f"Baud rate no válido: usa uno de {permitidos}")
    return baud


def _comando(modo: str, puerto: str, baud: int, localidad_id: int) -> list[str]:
    """Arma la línea de comando del colector según el modo solicitado.

    Todos los argumentos ya vienen validados (modo, puerto, baudios y
    localidad) y se pasan como lista, sin intérprete de comandos de por medio.
    """
    base = [sys.executable, config.COLLECTOR_PATH, "--localidad", str(int(localidad_id)),
            "--predict"]
    if modo == MODO_SIMULACION:
        return base + ["--simulate", "--lecturas", _LECTURAS_SIMULACION,
                       "--intervalo", _INTERVALO_SIMULACION]
    return base + ["--port", _validar_puerto(puerto), "--baud", str(_validar_baud(baud))]


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

    if modo == MODO_REAL:
        _validar_puerto(puerto)
        _validar_baud(baud)

    with _lock:
        if _en_ejecucion():
            raise servicios.SolicitudInvalida("El colector ya está en ejecución")

        puertos = listar_puertos()
        if modo == MODO_REAL and puertos and puerto not in puertos:
            raise servicios.SolicitudInvalida(
                f"Puerto {puerto} no detectado. Disponibles: {', '.join(puertos)}"
            )

        comando = _comando(modo, puerto, baud, localidad_id)
        _estado["error"] = None
        _estado["proceso"] = subprocess.Popen(  # noqa: S603 - argumentos validados, sin shell
            comando,
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
