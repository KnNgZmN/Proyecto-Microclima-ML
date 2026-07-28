"""
Pruebas de src/predict.py — inferencia con el modelo entrenado.

models/model.pkl está en .gitignore y no existe en CI, así que todas las
pruebas sustituyen el modelo por un doble (ver ModeloFalso en conftest.py).
"""

import pytest

import predict as predict_mod
from feature_engineering import FEATURE_COLS
from localidades import LOCALIDADES


@pytest.fixture(autouse=True)
def restaurar_cache_del_modelo():
    """Aísla el singleton _model entre pruebas."""
    original = predict_mod._model
    yield
    predict_mod._model = original


@pytest.fixture
def modelo_inyectado(modelo_falso, monkeypatch):
    monkeypatch.setattr(predict_mod, "_model", modelo_falso)
    return modelo_falso


# ---------------------------------------------------------------
# Contrato de salida
# ---------------------------------------------------------------
def test_predict_devuelve_un_float(modelo_inyectado):
    resultado = predict_mod.predict(14.0, 70.0, 500, 55, hora=10, mes=3)

    assert isinstance(resultado, float)
    assert resultado == pytest.approx(modelo_inyectado.valor)


def test_predict_entrega_al_modelo_las_features_esperadas(modelo_inyectado):
    predict_mod.predict(14.0, 70.0, 500, 55, hora=10, mes=3)

    X = modelo_inyectado.X_recibido
    assert list(X.columns) == FEATURE_COLS
    assert len(X) == 1


def test_predict_propaga_las_lecturas_crudas_del_sensor(modelo_inyectado):
    predict_mod.predict(14.0, 70.0, 500, 55, hora=10, mes=3)

    fila = modelo_inyectado.X_recibido.iloc[0]
    assert fila["temperatura"] == 14.0
    assert fila["humedad"] == 70.0
    assert fila["luz"] == 500
    assert fila["ruido"] == 55


# ---------------------------------------------------------------
# Resolución de localidad
# ---------------------------------------------------------------
def test_predict_usa_la_geolocalizacion_de_la_localidad_indicada(modelo_inyectado):
    predict_mod.predict(14.0, 70.0, 500, 55, hora=10, mes=3, localidad_id=20)

    sumapaz = LOCALIDADES[20]
    fila = modelo_inyectado.X_recibido.iloc[0]
    assert fila["altitud"] == sumapaz["altitud"]
    assert fila["latitud"] == sumapaz["lat"]
    assert fila["longitud"] == sumapaz["lon"]
    assert fila["densidad_urbana"] == sumapaz["densidad_urbana"]


def test_predict_usa_teusaquillo_por_defecto(modelo_inyectado):
    predict_mod.predict(14.0, 70.0, 500, 55, hora=10, mes=3)

    assert modelo_inyectado.X_recibido.iloc[0]["altitud"] == LOCALIDADES[13]["altitud"]


def test_predict_cae_en_teusaquillo_ante_una_localidad_desconocida(modelo_inyectado):
    """Cubre la rama de fallback de LOCALIDADES.get(...)."""
    predict_mod.predict(14.0, 70.0, 500, 55, hora=10, mes=3, localidad_id=999)

    fila = modelo_inyectado.X_recibido.iloc[0]
    assert fila["altitud"] == LOCALIDADES[13]["altitud"]
    assert fila["latitud"] == LOCALIDADES[13]["lat"]


@pytest.mark.parametrize("loc_id", sorted(LOCALIDADES))
def test_predict_funciona_para_las_veinte_localidades(modelo_inyectado, loc_id):
    resultado = predict_mod.predict(14.0, 70.0, 500, 55, hora=10, mes=3,
                                    localidad_id=loc_id)

    assert isinstance(resultado, float)
    assert modelo_inyectado.X_recibido.iloc[0]["altitud"] == LOCALIDADES[loc_id]["altitud"]


# ---------------------------------------------------------------
# Valores temporales por defecto
# ---------------------------------------------------------------
def test_predict_usa_la_hora_y_mes_del_sistema_si_no_se_indican(
    modelo_inyectado, monkeypatch
):
    """Cubre las ramas 'if hora is None' / 'if mes is None' sin depender del reloj."""
    class RelojFalso:
        @staticmethod
        def now():
            import datetime as _dt
            return _dt.datetime(2025, 7, 15, 3, 0, 0)   # 03:00 → noche, mes 7

    monkeypatch.setattr(predict_mod, "datetime", RelojFalso)

    predict_mod.predict(14.0, 70.0, 500, 55)

    import numpy as np
    fila = modelo_inyectado.X_recibido.iloc[0]
    assert fila["es_dia"] == 0
    assert fila["hora_sin"] == pytest.approx(np.sin(2 * np.pi * 3 / 24))
    assert fila["mes_sin"] == pytest.approx(np.sin(2 * np.pi * 7 / 12))


def test_predict_respeta_la_hora_explicita(modelo_inyectado):
    predict_mod.predict(14.0, 70.0, 500, 55, hora=13, mes=3)

    assert modelo_inyectado.X_recibido.iloc[0]["es_dia"] == 1


# ---------------------------------------------------------------
# Carga perezosa del modelo
# ---------------------------------------------------------------
def test_load_model_carga_una_sola_vez(monkeypatch, modelo_falso):
    """El singleton evita releer model.pkl en cada predicción."""
    llamadas = []

    def joblib_load_falso(ruta):
        llamadas.append(ruta)
        return modelo_falso

    monkeypatch.setattr(predict_mod, "_model", None)
    monkeypatch.setattr(predict_mod.joblib, "load", joblib_load_falso)

    primero = predict_mod._load_model()
    segundo = predict_mod._load_model()

    assert primero is segundo is modelo_falso
    assert len(llamadas) == 1
    assert llamadas[0].endswith("model.pkl")


def test_predict_dispara_la_carga_del_modelo_si_no_esta_en_cache(
    monkeypatch, modelo_falso
):
    monkeypatch.setattr(predict_mod, "_model", None)
    monkeypatch.setattr(predict_mod.joblib, "load", lambda ruta: modelo_falso)

    resultado = predict_mod.predict(14.0, 70.0, 500, 55, hora=10, mes=3)

    assert resultado == pytest.approx(modelo_falso.valor)
    assert predict_mod._model is modelo_falso


# ---------------------------------------------------------------
# Historia de lecturas
# ---------------------------------------------------------------
def test_predict_usa_la_historia_para_los_promedios_moviles(modelo_inyectado):
    import pandas as pd

    historia = pd.DataFrame({
        "temperatura": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0],
        "humedad":     [60.0, 61.0, 62.0, 63.0, 64.0, 65.0],
    })

    predict_mod.predict(16.0, 70.0, 500, 55, hora=10, mes=3, historia=historia)

    fila = modelo_inyectado.X_recibido.iloc[0]
    assert fila["temp_prom_30m"] == pytest.approx(15.0)
    assert fila["tendencia_1h"] == pytest.approx(6.0)
