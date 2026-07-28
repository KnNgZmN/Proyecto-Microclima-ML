"""
Pruebas de src/arduino_collector.py — validación y persistencia de lecturas.

Solo se cubren las funciones sin dependencia de hardware. leer_serial() y
simular() quedan fuera del alcance (ver docs/cobertura-alcance.md): abren un
puerto serie y ejecutan bucles infinitos.
"""

import csv
import json
from datetime import datetime

import pytest

import arduino_collector as ac

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
