"""
Pruebas de src/arduino_collector.py — interpretación, validación y persistencia.

Tras el refactor ya no queda nada fuera de alcance por hardware: la lógica de
interpretación se extrajo a parsear_lectura(), el puerto serie se inyecta como
parámetro y el bucle admite una cota de lecturas. Ninguna prueba abre un puerto
real ni depende del Arduino.
"""

import csv
import json
import random
import sys
import types
from datetime import datetime

import pytest

import arduino_collector as ac

# ---------------------------------------------------------------
# DEMO DE EXPOSICION - NO FUSIONAR
# Desactiva las 68 pruebas de este archivo para demostrar que el
# umbral fail_under=95 bloquea el Pull Request.
# Deshacer con:  git checkout tests/test_arduino_collector.py
# ---------------------------------------------------------------
pytestmark = pytest.mark.skip("DEMO de exposicion")


class SerialFalso:
    """
    Doble del puerto serie.

    Entrega las líneas encoladas y, al agotarse, lanza KeyboardInterrupt —
    exactamente lo que produce un Ctrl+C real. Así el bucle termina por su
    camino normal y una prueba mal construida nunca puede colgar la suite.
    """

    def __init__(self, lineas):
        self.pendientes = list(lineas)
        self.cerrado = False

    def readline(self) -> bytes:
        if not self.pendientes:
            raise KeyboardInterrupt
        return (self.pendientes.pop(0) + "\n").encode("utf-8")

    def close(self):
        self.cerrado = True


class RngFijo:
    """
    Generador determinista para aislar la física de la aleatoriedad.

    Por defecto randint devuelve el límite inferior del rango pedido, que
    sí depende de la hora y la densidad; así se puede comparar hora pico
    contra valle. Con `randint_val` devuelve un valor fijo, útil para
    forzar los topes de saturación.
    """

    def __init__(self, gauss_val=0.0, randint_val=None):
        self._g = gauss_val
        self._r = randint_val

    def gauss(self, mu, sigma):
        return self._g

    def randint(self, a, b):
        return a if self._r is None else self._r


@pytest.fixture
def rutas_temporales(tmp_path, monkeypatch):
    """Redirige la persistencia a un directorio temporal."""
    datos = tmp_path / "data.csv"
    vivo  = tmp_path / "live" / "latest.json"
    monkeypatch.setattr(ac, "DATA_PATH", str(datos))
    monkeypatch.setattr(ac, "LIVE_PATH", str(vivo))
    return datos, vivo

TS = datetime(2025, 3, 10, 14, 30, 0)


# ---------------------------------------------------------------
# validar_lectura
# ---------------------------------------------------------------
def test_validar_lectura_acepta_valores_normales():
    assert ac.validar_lectura(14.0, 70.0, 500, 55) is True


# validar_lectura(temp, hum, luz, ruido) recibe posicionales en este orden
ORDEN = ["temperatura", "humedad", "luz", "ruido"]


def _lectura_con(columna, valor):
    """Lectura válida salvo por `columna`, que toma `valor`."""
    base = {"temperatura": 14.0, "humedad": 70.0, "luz": 500, "ruido": 55}
    base[columna] = valor
    return [base[c] for c in ORDEN]


@pytest.mark.parametrize("columna", ORDEN)
def test_validar_lectura_acepta_los_extremos_del_rango(columna):
    """Los límites son inclusivos: lo <= val <= hi."""
    for extremo in ac.RANGOS[columna]:
        assert ac.validar_lectura(*_lectura_con(columna, extremo)) is True


@pytest.mark.parametrize("columna", ORDEN)
def test_validar_lectura_rechaza_valores_por_encima_del_maximo(columna):
    fuera = ac.RANGOS[columna][1] + 0.1

    assert ac.validar_lectura(*_lectura_con(columna, fuera)) is False


@pytest.mark.parametrize("columna", ORDEN)
def test_validar_lectura_rechaza_valores_por_debajo_del_minimo(columna):
    fuera = ac.RANGOS[columna][0] - 0.1

    assert ac.validar_lectura(*_lectura_con(columna, fuera)) is False


def test_validar_lectura_rechaza_una_desconexion_del_sensor():
    """Un DHT desconectado suele reportar -999."""
    assert ac.validar_lectura(-999.0, -999.0, 0, 55) is False


# ---------------------------------------------------------------
# guardar_fila
# ---------------------------------------------------------------
def test_guardar_fila_crea_el_csv_con_encabezado(tmp_path, monkeypatch, loc_info):
    destino = tmp_path / "data.csv"
    monkeypatch.setattr(ac, "DATA_PATH", str(destino))

    ac.guardar_fila(TS, 14.0, 70.0, 500, 55, 13, loc_info)

    filas = list(csv.reader(destino.open(encoding="utf-8")))
    assert filas[0] == ac.COLUMNAS
    assert len(filas) == 2


def test_guardar_fila_escribe_el_encabezado_una_sola_vez(tmp_path, monkeypatch, loc_info):
    destino = tmp_path / "data.csv"
    monkeypatch.setattr(ac, "DATA_PATH", str(destino))

    ac.guardar_fila(TS, 14.0, 70.0, 500, 55, 13, loc_info)
    ac.guardar_fila(TS, 15.0, 71.0, 510, 56, 13, loc_info)
    ac.guardar_fila(TS, 16.0, 72.0, 520, 57, 13, loc_info)

    filas = list(csv.reader(destino.open(encoding="utf-8")))
    assert len(filas) == 4                 # 1 encabezado + 3 lecturas
    assert filas.count(ac.COLUMNAS) == 1


def test_guardar_fila_serializa_los_metadatos_de_localidad(tmp_path, monkeypatch, loc_info):
    destino = tmp_path / "data.csv"
    monkeypatch.setattr(ac, "DATA_PATH", str(destino))

    ac.guardar_fila(TS, 14.0, 70.0, 500, 55, 13, loc_info)

    fila = dict(zip(*list(csv.reader(destino.open(encoding="utf-8")))))
    assert fila["timestamp"] == "2025-03-10 14:30:00"
    assert fila["localidad_id"] == "13"
    assert fila["localidad"] == "Teusaquillo"
    assert fila["altitud"] == "2600"
    assert fila["temperatura"] == "14.0"


# ---------------------------------------------------------------
# actualizar_live
# ---------------------------------------------------------------
def test_actualizar_live_escribe_json_valido(tmp_path, monkeypatch, loc_info):
    destino = tmp_path / "live" / "latest.json"
    monkeypatch.setattr(ac, "LIVE_PATH", str(destino))

    ac.actualizar_live(TS, 14.567, 70.44, 500.9, 55.2, 18.512, 13, loc_info)

    datos = json.loads(destino.read_text(encoding="utf-8"))
    assert datos["timestamp"] == "2025-03-10 14:30:00"
    assert datos["localidad_id"] == 13
    assert datos["localidad"] == "Teusaquillo"
    assert datos["temperatura"] == 14.57      # redondeo a 2 decimales
    assert datos["humedad"] == 70.4           # redondeo a 1 decimal
    assert datos["luz"] == 500                # truncado a entero
    assert datos["ruido"] == 55
    assert datos["prediccion"] == 18.51


def test_actualizar_live_admite_prediccion_nula(tmp_path, monkeypatch, loc_info):
    """Cubre la rama ternaria cuando el modelo no está disponible."""
    destino = tmp_path / "live" / "latest.json"
    monkeypatch.setattr(ac, "LIVE_PATH", str(destino))

    ac.actualizar_live(TS, 14.0, 70.0, 500, 55, None, 13, loc_info)

    datos = json.loads(destino.read_text(encoding="utf-8"))
    assert datos["prediccion"] is None


def test_actualizar_live_crea_el_directorio_si_no_existe(tmp_path, monkeypatch, loc_info):
    destino = tmp_path / "nueva" / "ruta" / "latest.json"
    monkeypatch.setattr(ac, "LIVE_PATH", str(destino))

    ac.actualizar_live(TS, 14.0, 70.0, 500, 55, None, 13, loc_info)

    assert destino.exists()


def test_actualizar_live_sobrescribe_la_lectura_anterior(tmp_path, monkeypatch, loc_info):
    destino = tmp_path / "live" / "latest.json"
    monkeypatch.setattr(ac, "LIVE_PATH", str(destino))

    ac.actualizar_live(TS, 14.0, 70.0, 500, 55, None, 13, loc_info)
    ac.actualizar_live(TS, 22.0, 60.0, 900, 70, 23.0, 20, loc_info)

    datos = json.loads(destino.read_text(encoding="utf-8"))
    assert datos["temperatura"] == 22.0
    assert datos["localidad_id"] == 20


# ---------------------------------------------------------------
# predecir_en_vivo
# ---------------------------------------------------------------
@pytest.fixture(autouse=True)
def restaurar_modelo_del_colector():
    original = ac._modelo
    yield
    ac._modelo = original


def test_predecir_en_vivo_devuelve_none_sin_modelo_entrenado(monkeypatch, loc_info):
    """Sin models/model.pkl la app debe degradarse, no romperse."""
    monkeypatch.setattr(ac, "_modelo", None)
    monkeypatch.setattr(ac.os.path, "exists", lambda ruta: False)

    resultado = ac.predecir_en_vivo(14.0, 70.0, 500, 55, 10, 3, None, loc_info)

    assert resultado is None


def test_predecir_en_vivo_usa_el_modelo_en_cache(monkeypatch, modelo_falso, loc_info):
    monkeypatch.setattr(ac, "_modelo", modelo_falso)

    resultado = ac.predecir_en_vivo(14.0, 70.0, 500, 55, 10, 3, None, loc_info)

    assert resultado == pytest.approx(modelo_falso.valor)
    assert modelo_falso.X_recibido.iloc[0]["altitud"] == loc_info["altitud"]
    assert modelo_falso.X_recibido.iloc[0]["densidad_urbana"] == loc_info["densidad_urbana"]


# ---------------------------------------------------------------
# Constantes de configuración
# ---------------------------------------------------------------
def test_columnas_del_csv_coinciden_con_el_orden_de_guardar_fila():
    assert ac.COLUMNAS[0] == "timestamp"
    assert ac.COLUMNAS[-4:] == ["temperatura", "humedad", "luz", "ruido"]


def test_historia_max_permite_calcular_la_tendencia_de_una_hora():
    """features_from_raw necesita 6 lecturas previas para tendencia_1h."""
    assert ac.HISTORIA_MAX >= 6


# ---------------------------------------------------------------
# parsear_lectura — la lógica que antes vivía dentro del bucle serial
# ---------------------------------------------------------------
def test_cuatro_valores_se_leen_en_orden(loc_info):
    lectura = ac.parsear_lectura("18.5,72.3,850,45", loc_info)

    assert (lectura.temperatura, lectura.humedad) == (18.5, 72.3)
    assert (lectura.luz, lectura.ruido) == (850.0, 45.0)
    assert lectura.nota == ""


def test_valores_extra_se_descartan(loc_info):
    """El sketch podría enviar campos adicionales; solo importan los cuatro."""
    lectura = ac.parsear_lectura("18.5,72.3,850,45,99,100", loc_info)

    assert lectura[:4] == (18.5, 72.3, 850.0, 45.0)


def test_tres_valores_asumen_ruido_por_defecto(loc_info):
    lectura = ac.parsear_lectura("18.5,72.3,850", loc_info)

    assert lectura.ruido == 45.0
    assert "Ruido default=45" in lectura.nota


def test_dos_valores_se_leen_como_temperatura_y_humedad(loc_info):
    lectura = ac.parsear_lectura("18.5,72.3", loc_info)

    assert (lectura.temperatura, lectura.humedad) == (18.5, 72.3)
    assert (lectura.luz, lectura.ruido) == (600.0, 45.0)
    assert "Luz default=600" in lectura.nota


def test_sin_dht_la_temperatura_se_estima_por_altitud(loc_info):
    """Teusaquillo, 2.600 m: 14,0 + (2625 − 2600) × 0,0065 = 14,2 °C."""
    lectura = ac.parsear_lectura("850,45", loc_info)

    assert (lectura.luz, lectura.ruido) == (850.0, 45.0)
    assert lectura.temperatura == pytest.approx(14.2)
    assert lectura.humedad == 72.0
    assert "estimada por altitud" in lectura.nota


def test_la_temperatura_estimada_cae_con_la_altitud():
    """Sumapaz, 3.150 m: 14,0 + (2625 − 3150) × 0,0065 = 10,6 °C."""
    sumapaz = ac.parsear_lectura("850,45", {"altitud": 3150})

    assert sumapaz.temperatura == pytest.approx(10.6)


def test_ante_dos_valores_ambiguos_se_prefiere_temperatura_y_humedad(loc_info):
    """
    Fija el contrato en un caso genuinamente ambiguo.

    '25,50' cae dentro de los dos rangos a la vez: podría ser 25 °C con
    50 % de humedad, o 25 lux con 50 dB. El código resuelve por el orden
    de las ramas; esta prueba deja esa decisión explícita para que un
    reordenamiento accidental no la cambie en silencio.
    """
    lectura = ac.parsear_lectura("25,50", loc_info)

    assert (lectura.temperatura, lectura.humedad) == (25.0, 50.0)
    assert (lectura.luz, lectura.ruido) == (600.0, 45.0)


@pytest.mark.parametrize("linea", ["", "   ", "\n"])
def test_las_lineas_vacias_se_ignoran(linea, loc_info):
    assert ac.parsear_lectura(linea, loc_info) is None


def test_los_comentarios_del_sketch_se_ignoran(loc_info):
    """El sketch emite '# ERROR sensor DHT22' cuando el sensor falla."""
    assert ac.parsear_lectura("# ERROR sensor DHT22", loc_info) is None


def test_los_valores_no_numericos_se_ignoran(loc_info):
    assert ac.parsear_lectura("abc,def,ghi,jkl", loc_info) is None


def test_dos_valores_fuera_de_todo_rango_conocido_se_ignoran(loc_info):
    assert ac.parsear_lectura("5000,6000", loc_info) is None


def test_una_linea_con_un_solo_valor_es_incompleta(loc_info):
    with pytest.raises(ac.LineaIncompleta):
        ac.parsear_lectura("18.5", loc_info)


def test_los_espacios_sobrantes_no_estorban(loc_info):
    lectura = ac.parsear_lectura("  18.5,72.3,850,45  \r\n", loc_info)

    assert lectura[:4] == (18.5, 72.3, 850.0, 45.0)


# ---------------------------------------------------------------
# abrir_puerto — traduce fallos de hardware a ColectorError
# ---------------------------------------------------------------
def _modulo_serial_falso(al_construir=None):
    modulo = types.ModuleType("serial")

    class SerialException(Exception):
        pass

    def Serial(port, baud, timeout=None):
        if al_construir is not None:
            raise al_construir
        return SerialFalso([])

    modulo.SerialException = SerialException
    modulo.Serial = Serial
    return modulo


def test_abrir_puerto_devuelve_la_conexion(monkeypatch):
    monkeypatch.setitem(sys.modules, "serial", _modulo_serial_falso())

    conexion = ac.abrir_puerto("COM3", 9600)

    assert hasattr(conexion, "readline")


def test_abrir_puerto_traduce_el_fallo_del_puerto(monkeypatch):
    modulo = _modulo_serial_falso()
    monkeypatch.setitem(sys.modules, "serial", modulo)
    monkeypatch.setattr(
        modulo, "Serial",
        lambda *a, **k: (_ for _ in ()).throw(modulo.SerialException("ocupado")),
    )

    with pytest.raises(ac.ColectorError, match="No se pudo abrir el puerto"):
        ac.abrir_puerto("COM3", 9600)


def test_abrir_puerto_avisa_si_falta_pyserial(monkeypatch):
    """Con sys.modules['serial'] en None, 'import serial' lanza ImportError."""
    monkeypatch.setitem(sys.modules, "serial", None)

    with pytest.raises(ac.ColectorError, match="pyserial"):
        ac.abrir_puerto("COM3", 9600)


# ---------------------------------------------------------------
# leer_serial — ahora ejecutable sin hardware
# ---------------------------------------------------------------
def test_leer_serial_persiste_las_lecturas_validas(rutas_temporales, loc_info):
    datos, vivo = rutas_temporales
    puerto = SerialFalso(["18.5,72.3,850,45", "19.0,71.0,860,46"])

    guardadas = ac.leer_serial("COM3", 9600, 0, False, 13, loc_info, conexion=puerto)

    assert guardadas == 2
    filas = list(csv.reader(datos.open(encoding="utf-8")))
    assert len(filas) == 3                       # encabezado + 2 lecturas
    assert json.loads(vivo.read_text(encoding="utf-8"))["temperatura"] == 19.0


def test_leer_serial_cierra_el_puerto_al_terminar(rutas_temporales, loc_info):
    puerto = SerialFalso(["18.5,72.3,850,45"])

    ac.leer_serial("COM3", 9600, 0, False, 13, loc_info, conexion=puerto)

    assert puerto.cerrado is True


def test_max_lecturas_detiene_el_bucle(rutas_temporales, loc_info):
    puerto = SerialFalso(["18.5,72.3,850,45"] * 5)

    guardadas = ac.leer_serial("COM3", 9600, 0, False, 13, loc_info,
                               conexion=puerto, max_lecturas=2)

    assert guardadas == 2
    assert len(puerto.pendientes) == 3           # no llegó a leerlas


def test_leer_serial_ignora_comentarios_y_lineas_ilegibles(rutas_temporales, loc_info):
    puerto = SerialFalso([
        "# ERROR sensor DHT22",
        "abc,def,ghi,jkl",
        "18.5,72.3,850,45",
    ])

    guardadas = ac.leer_serial("COM3", 9600, 0, False, 13, loc_info, conexion=puerto)

    assert guardadas == 1


def test_leer_serial_descarta_lecturas_fuera_de_rango(rutas_temporales, loc_info):
    """Un DHT desconectado reporta -999: no debe llegar al CSV."""
    puerto = SerialFalso(["-999,-999,850,45", "18.5,72.3,850,45"])

    guardadas = ac.leer_serial("COM3", 9600, 0, False, 13, loc_info, conexion=puerto)

    assert guardadas == 1


def test_diez_lineas_incompletas_seguidas_abortan(rutas_temporales, loc_info):
    """Señal de que el sketch envía en un formato que no reconocemos."""
    puerto = SerialFalso(["basura"] * 12)

    guardadas = ac.leer_serial("COM3", 9600, 0, False, 13, loc_info, conexion=puerto)

    assert guardadas == 0
    assert len(puerto.pendientes) == 2           # cortó en la décima


def test_una_linea_valida_reinicia_el_contador_de_errores(rutas_temporales, loc_info):
    """Nueve errores, una lectura buena y nueve más: no debe abortar."""
    puerto = SerialFalso(["basura"] * 9 + ["18.5,72.3,850,45"] + ["basura"] * 9)

    guardadas = ac.leer_serial("COM3", 9600, 0, False, 13, loc_info, conexion=puerto)

    assert guardadas == 1
    assert puerto.pendientes == []               # las consumió todas


def test_leer_serial_incluye_la_prediccion_cuando_se_pide(
    rutas_temporales, monkeypatch, modelo_falso, loc_info
):
    _, vivo = rutas_temporales
    monkeypatch.setattr(ac, "_modelo", modelo_falso)
    puerto = SerialFalso(["18.5,72.3,850,45"])

    ac.leer_serial("COM3", 9600, 0, True, 13, loc_info, conexion=puerto)

    assert json.loads(vivo.read_text(encoding="utf-8"))["prediccion"] == pytest.approx(
        round(modelo_falso.valor, 2)
    )


# ---------------------------------------------------------------
# sintetizar_lectura — la física del modo simulación
# ---------------------------------------------------------------
def test_sintetizar_lectura_es_reproducible_con_la_misma_semilla():
    a = ac.sintetizar_lectura(14, 0.87, 0.1625, random.Random(7))
    b = ac.sintetizar_lectura(14, 0.87, 0.1625, random.Random(7))

    assert a == b


def test_la_isla_de_calor_pesa_mas_de_noche():
    """
    Con la misma semilla el ruido aleatorio se cancela en la resta, así que
    la diferencia entre zona densa y rural aísla el efecto de isla de calor.
    """
    denso_dia    = ac.sintetizar_lectura(12, 0.9, 0.0, random.Random(1)).temperatura
    rural_dia    = ac.sintetizar_lectura(12, 0.1, 0.0, random.Random(1)).temperatura
    denso_noche  = ac.sintetizar_lectura(2,  0.9, 0.0, random.Random(1)).temperatura
    rural_noche  = ac.sintetizar_lectura(2,  0.1, 0.0, random.Random(1)).temperatura

    assert (denso_noche - rural_noche) > (denso_dia - rural_dia)


def test_la_temperatura_baja_con_la_altitud():
    """Sumapaz (3.150 m) debe ser más frío que Bosa (2.565 m) a la misma hora."""
    sumapaz = ac.sintetizar_lectura(12, 0.5, (2625 - 3150) * 0.0065, random.Random(3))
    bosa    = ac.sintetizar_lectura(12, 0.5, (2625 - 2565) * 0.0065, random.Random(3))

    assert sumapaz.temperatura < bosa.temperatura


def test_hay_mas_luz_de_dia_que_de_noche():
    dia   = ac.sintetizar_lectura(12, 0.5, 0.0, random.Random(5)).luz
    noche = ac.sintetizar_lectura(3,  0.5, 0.0, random.Random(5)).luz

    assert dia > noche


def test_hay_mas_ruido_en_hora_pico():
    """7-9 y 17-19 usan un rango desplazado 20 dB por encima del de valle."""
    pico  = ac.sintetizar_lectura(8,  0.8, 0.0, RngFijo()).ruido
    valle = ac.sintetizar_lectura(14, 0.8, 0.0, RngFijo()).ruido

    assert pico > valle


@pytest.mark.parametrize("gauss,esperado", [(999.0, 100.0), (-999.0, 40.0)])
def test_la_humedad_se_mantiene_en_su_rango_fisico(gauss, esperado):
    lectura = ac.sintetizar_lectura(0, 0.5, 0.0, RngFijo(gauss_val=gauss))

    assert lectura.humedad == esperado


@pytest.mark.parametrize("randint,esperado", [(5000, 100), (-5000, 30)])
def test_el_ruido_se_mantiene_en_su_rango_fisico(randint, esperado):
    lectura = ac.sintetizar_lectura(12, 0.5, 0.0, RngFijo(randint_val=randint))

    assert lectura.ruido == esperado


# ---------------------------------------------------------------
# simular — modo sin hardware, de extremo a extremo
# ---------------------------------------------------------------
def test_simular_persiste_la_cantidad_de_lecturas_pedida(rutas_temporales, loc_info):
    datos, vivo = rutas_temporales

    generadas = ac.simular(0, False, 3, 13, loc_info, rng=random.Random(11))

    assert generadas == 3
    filas = list(csv.reader(datos.open(encoding="utf-8")))
    assert len(filas) == 4                       # encabezado + 3 lecturas
    assert vivo.exists()


def test_simular_registra_la_localidad_indicada(rutas_temporales, loc_info):
    _, vivo = rutas_temporales

    ac.simular(0, False, 1, 13, loc_info, rng=random.Random(2))

    assert json.loads(vivo.read_text(encoding="utf-8"))["localidad"] == "Teusaquillo"


def test_simular_incluye_la_prediccion_cuando_se_pide(
    rutas_temporales, monkeypatch, modelo_falso, loc_info
):
    _, vivo = rutas_temporales
    monkeypatch.setattr(ac, "_modelo", modelo_falso)

    ac.simular(0, True, 1, 13, loc_info, rng=random.Random(4))

    datos = json.loads(vivo.read_text(encoding="utf-8"))
    assert datos["prediccion"] == pytest.approx(round(modelo_falso.valor, 2))


def test_simular_sigue_generando_sin_modelo_entrenado(
    rutas_temporales, monkeypatch, loc_info
):
    """Se pide predicción pero no hay model.pkl: simula igual, sin predecir."""
    _, vivo = rutas_temporales
    monkeypatch.setattr(ac, "_modelo", None)
    monkeypatch.setattr(ac.os.path, "exists", lambda ruta: False)

    generadas = ac.simular(0, True, 1, 13, loc_info, rng=random.Random(6))

    assert generadas == 1
    assert json.loads(vivo.read_text(encoding="utf-8"))["prediccion"] is None


# ---------------------------------------------------------------
# Caminos que solo se recorren con el sistema completo
# ---------------------------------------------------------------
def test_predecir_en_vivo_carga_el_modelo_del_disco(monkeypatch, modelo_falso, loc_info):
    """Primera predicción con model.pkl presente: lo carga y lo memoriza."""
    import joblib

    monkeypatch.setattr(ac, "_modelo", None)
    monkeypatch.setattr(ac.os.path, "exists", lambda ruta: True)
    monkeypatch.setattr(joblib, "load", lambda ruta: modelo_falso)

    resultado = ac.predecir_en_vivo(14.0, 70.0, 500, 55, 10, 3, None, loc_info)

    assert resultado == pytest.approx(modelo_falso.valor)
    assert ac._modelo is modelo_falso


def test_leer_serial_abre_el_puerto_si_no_se_le_inyecta(
    rutas_temporales, monkeypatch, loc_info
):
    """Sin `conexion`, la función debe abrir el puerto por su cuenta."""
    modulo = _modulo_serial_falso()
    monkeypatch.setattr(modulo, "Serial",
                        lambda *a, **k: SerialFalso(["18.5,72.3,850,45"]))
    monkeypatch.setitem(sys.modules, "serial", modulo)

    guardadas = ac.leer_serial("COM3", 9600, 0, False, 13, loc_info)

    assert guardadas == 1


def test_leer_serial_informa_los_supuestos_aplicados(
    rutas_temporales, capsys, loc_info
):
    """Con 3 valores se asume el ruido, y el usuario debe enterarse."""
    puerto = SerialFalso(["18.5,72.3,850"])

    ac.leer_serial("COM3", 9600, 0, False, 13, loc_info, conexion=puerto)

    assert "Ruido default=45" in capsys.readouterr().out


def test_leer_serial_sigue_recolectando_sin_modelo_entrenado(
    rutas_temporales, monkeypatch, loc_info
):
    """Se pide predicción pero no hay model.pkl: guarda igual, sin predecir."""
    _, vivo = rutas_temporales
    monkeypatch.setattr(ac, "_modelo", None)
    monkeypatch.setattr(ac.os.path, "exists", lambda ruta: False)
    puerto = SerialFalso(["18.5,72.3,850,45"])

    guardadas = ac.leer_serial("COM3", 9600, 0, True, 13, loc_info, conexion=puerto)

    assert guardadas == 1
    assert json.loads(vivo.read_text(encoding="utf-8"))["prediccion"] is None
