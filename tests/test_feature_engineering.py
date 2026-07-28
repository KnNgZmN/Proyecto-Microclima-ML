"""Pruebas de src/feature_engineering.py — derivación de features del modelo."""

import numpy as np
import pandas as pd
import pytest

from feature_engineering import (
    DEFAULT_ALTITUD,
    DEFAULT_DENSIDAD,
    DEFAULT_LAT,
    DEFAULT_LON,
    FEATURE_COLS,
    create_features,
    create_target,
    features_from_raw,
)


def _presion_vapor_esperada(temp, hum):
    return (hum / 100) * 6.1078 * np.exp(17.27 * temp / (237.3 + temp))


# ---------------------------------------------------------------
# create_features — contrato de columnas
# ---------------------------------------------------------------
def test_create_features_produce_todas_las_feature_cols(df_una_localidad):
    salida = create_features(df_una_localidad)

    faltantes = set(FEATURE_COLS) - set(salida.columns)
    assert faltantes == set()


def test_create_features_no_muta_la_entrada(df_una_localidad):
    entrada = df_una_localidad.copy()

    create_features(df_una_localidad)

    pd.testing.assert_frame_equal(df_una_localidad, entrada)


# ---------------------------------------------------------------
# Codificación cíclica temporal
# ---------------------------------------------------------------
@pytest.mark.parametrize("hora,sin_esp,cos_esp", [
    (0,  0.0,  1.0),
    (6,  1.0,  0.0),
    (12, 0.0, -1.0),
    (18, -1.0, 0.0),
])
def test_codificacion_ciclica_de_la_hora(hora, sin_esp, cos_esp):
    df = pd.DataFrame({
        "timestamp":   [pd.Timestamp(f"2025-03-10 {hora:02d}:00")],
        "temperatura": [14.0], "humedad": [70.0], "luz": [100], "ruido": [45],
    })

    salida = create_features(df)

    assert salida["hora_sin"].iloc[0] == pytest.approx(sin_esp, abs=1e-9)
    assert salida["hora_cos"].iloc[0] == pytest.approx(cos_esp, abs=1e-9)


def test_codificacion_ciclica_de_la_hora_es_continua_en_medianoche():
    """23:00 y 00:00 deben quedar adyacentes en el círculo unitario."""
    df = pd.DataFrame({
        "timestamp":   pd.to_datetime(["2025-03-10 23:00", "2025-03-11 00:00"]),
        "temperatura": [14.0, 14.0], "humedad": [70.0, 70.0],
        "luz": [0, 0], "ruido": [45, 45],
    })

    s = create_features(df)
    distancia = np.hypot(
        s["hora_sin"].iloc[1] - s["hora_sin"].iloc[0],
        s["hora_cos"].iloc[1] - s["hora_cos"].iloc[0],
    )

    assert distancia == pytest.approx(2 * np.sin(np.pi / 24), abs=1e-9)


@pytest.mark.parametrize("hora,esperado", [
    (5, 0), (6, 1), (12, 1), (18, 1), (19, 0), (23, 0),
])
def test_es_dia_respeta_los_limites_6_a_18_inclusive(hora, esperado):
    df = pd.DataFrame({
        "timestamp":   [pd.Timestamp(f"2025-03-10 {hora:02d}:30")],
        "temperatura": [14.0], "humedad": [70.0], "luz": [100], "ruido": [45],
    })

    assert create_features(df)["es_dia"].iloc[0] == esperado


def test_codificacion_ciclica_del_mes():
    df = pd.DataFrame({
        "timestamp":   pd.to_datetime(["2025-03-10", "2025-09-10"]),
        "temperatura": [14.0, 14.0], "humedad": [70.0, 70.0],
        "luz": [0, 0], "ruido": [45, 45],
    })

    s = create_features(df)

    assert s["mes_sin"].iloc[0] == pytest.approx(np.sin(2 * np.pi * 3 / 12))
    assert s["mes_cos"].iloc[1] == pytest.approx(np.cos(2 * np.pi * 9 / 12))


# ---------------------------------------------------------------
# Presión de vapor (fórmula de Magnus-Tetens)
# ---------------------------------------------------------------
def test_presion_vapor_sigue_la_formula_de_magnus(df_una_localidad):
    salida = create_features(df_una_localidad)

    esperado = _presion_vapor_esperada(
        df_una_localidad["temperatura"], df_una_localidad["humedad"]
    ).round(4)

    np.testing.assert_allclose(salida["presion_vapor"], esperado, atol=1e-4)


def test_presion_vapor_crece_con_la_humedad():
    df = pd.DataFrame({
        "timestamp":   pd.date_range("2025-03-10", periods=2, freq="10min"),
        "temperatura": [14.0, 14.0], "humedad": [40.0, 90.0],
        "luz": [0, 0], "ruido": [45, 45],
    })

    s = create_features(df)

    assert s["presion_vapor"].iloc[1] > s["presion_vapor"].iloc[0]


# ---------------------------------------------------------------
# Aislamiento por localidad — el comportamiento crítico del módulo
# ---------------------------------------------------------------
def test_promedios_moviles_no_se_contaminan_entre_localidades(df_dos_localidades):
    """
    Con filas intercaladas, el promedio móvil debe calcularse dentro de cada
    localidad. Sin agrupar, la fila 1 (loc 2, 20 °C) arrastraría la fila 0
    (loc 1, 10 °C) y daría 15.0.
    """
    salida = create_features(df_dos_localidades)

    esperado = [10.0, 20.0, 10.5, 20.5, 11.0, 21.0]
    np.testing.assert_allclose(salida["temp_prom_30m"], esperado)


def test_cambio_temp_se_calcula_dentro_de_cada_localidad(df_dos_localidades):
    salida = create_features(df_dos_localidades)

    # Primera lectura de cada localidad → sin anterior → 0
    esperado = [0.0, 0.0, 1.0, 1.0, 1.0, 1.0]
    np.testing.assert_allclose(salida["cambio_temp"], esperado)


def test_humedad_prom_se_calcula_dentro_de_cada_localidad(df_dos_localidades):
    salida = create_features(df_dos_localidades)

    esperado = [70.0, 80.0, 70.5, 80.5, 71.0, 81.0]
    np.testing.assert_allclose(salida["humedad_prom"], esperado)


def test_promedios_moviles_sin_columna_de_localidad(df_una_localidad):
    """Rama alternativa: sin localidad_id se usa la serie completa."""
    salida = create_features(df_una_localidad)

    esperado = [10.0, 10.5, 11.0, 12.0, 13.0, 14.0]
    np.testing.assert_allclose(salida["temp_prom_30m"], esperado)


def test_tendencia_1h_es_cero_sin_seis_lecturas_previas(df_una_localidad):
    salida = create_features(df_una_localidad)

    assert (salida["tendencia_1h"] == 0.0).all()


# ---------------------------------------------------------------
# Valores por defecto de geolocalización
# ---------------------------------------------------------------
def test_geolocalizacion_usa_defaults_si_faltan_las_columnas(df_una_localidad):
    salida = create_features(df_una_localidad)

    assert (salida["altitud"] == DEFAULT_ALTITUD).all()
    assert (salida["latitud"] == DEFAULT_LAT).all()
    assert (salida["longitud"] == DEFAULT_LON).all()
    assert (salida["densidad_urbana"] == DEFAULT_DENSIDAD).all()


def test_geolocalizacion_respeta_las_columnas_existentes(df_una_localidad):
    df = df_una_localidad.copy()
    df["altitud"] = 3150.0
    df["latitud"] = 4.3304

    salida = create_features(df)

    assert (salida["altitud"] == 3150.0).all()
    assert (salida["latitud"] == 4.3304).all()
    assert (salida["longitud"] == DEFAULT_LON).all()


# ---------------------------------------------------------------
# create_target
# ---------------------------------------------------------------
def test_create_target_desplaza_la_temperatura_hacia_el_futuro(df_una_localidad):
    salida = create_target(df_una_localidad, steps=3)

    # 6 filas − 3 pasos = 3 filas con objetivo conocido
    assert len(salida) == 3
    np.testing.assert_allclose(salida["temp_futura"], [13.0, 14.0, 15.0])


def test_create_target_descarta_las_filas_sin_futuro(df_una_localidad):
    salida = create_target(df_una_localidad, steps=5)

    assert len(salida) == 1
    assert salida["temp_futura"].iloc[0] == 15.0


def test_create_target_agrupa_por_localidad(df_dos_localidades):
    """Con 3 lecturas por localidad y 1 paso, quedan 2 filas por localidad."""
    salida = create_target(df_dos_localidades, steps=1)

    assert len(salida) == 4
    assert salida[salida["localidad_id"] == 1]["temp_futura"].tolist() == [11.0, 12.0]
    assert salida[salida["localidad_id"] == 2]["temp_futura"].tolist() == [21.0, 22.0]


def test_create_target_no_muta_la_entrada(df_una_localidad):
    entrada = df_una_localidad.copy()

    create_target(df_una_localidad)

    pd.testing.assert_frame_equal(df_una_localidad, entrada)


# ---------------------------------------------------------------
# features_from_raw — camino de inferencia en vivo
# ---------------------------------------------------------------
def test_features_from_raw_devuelve_una_fila_con_las_columnas_en_orden():
    X = features_from_raw(14.0, 70.0, 500, 55, hora=10, mes=3)

    assert X.shape == (1, len(FEATURE_COLS))
    assert list(X.columns) == FEATURE_COLS


def test_features_from_raw_sin_historia_usa_la_lectura_actual():
    X = features_from_raw(14.0, 70.0, 500, 55, hora=10, mes=3)

    fila = X.iloc[0]
    assert fila["temp_prom_30m"] == 14.0
    assert fila["temp_prom_1h"] == 14.0
    assert fila["humedad_prom"] == 70.0
    assert fila["cambio_temp"] == 0.0
    assert fila["tendencia_1h"] == 0.0


def test_features_from_raw_con_una_sola_fila_de_historia_usa_el_fallback():
    """El módulo exige len(historia) >= 2 para calcular promedios reales."""
    historia = pd.DataFrame({"temperatura": [10.0], "humedad": [60.0]})

    X = features_from_raw(14.0, 70.0, 500, 55, hora=10, mes=3, historia=historia)

    assert X.iloc[0]["temp_prom_30m"] == 14.0
    assert X.iloc[0]["cambio_temp"] == 0.0


def test_features_from_raw_con_historia_corta_no_calcula_tendencia():
    """Con menos de 7 temperaturas acumuladas, tendencia_1h queda en 0."""
    historia = pd.DataFrame({
        "temperatura": [10.0, 11.0],
        "humedad":     [60.0, 61.0],
    })

    fila = features_from_raw(12.0, 70.0, 500, 55, hora=10, mes=3,
                             historia=historia).iloc[0]

    assert fila["temp_prom_30m"] == pytest.approx(11.0)   # media de 10, 11, 12
    assert fila["temp_prom_1h"] == pytest.approx(11.0)
    assert fila["cambio_temp"] == pytest.approx(1.0)      # 12 − 11
    assert fila["tendencia_1h"] == 0.0


def test_features_from_raw_con_historia_completa_calcula_tendencia():
    historia = pd.DataFrame({
        "temperatura": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0],
        "humedad":     [60.0, 61.0, 62.0, 63.0, 64.0, 65.0],
    })

    fila = features_from_raw(16.0, 70.0, 500, 55, hora=10, mes=3,
                             historia=historia).iloc[0]

    assert fila["temp_prom_30m"] == pytest.approx(15.0)   # media de 14, 15, 16
    assert fila["temp_prom_1h"] == pytest.approx(13.5)    # media de 11..16
    assert fila["cambio_temp"] == pytest.approx(1.0)      # 16 − 15
    assert fila["tendencia_1h"] == pytest.approx(6.0)     # 16 − 10
    assert fila["humedad_prom"] == pytest.approx(199 / 3)  # media de 64, 65, 70


def test_features_from_raw_propaga_los_metadatos_de_localidad():
    X = features_from_raw(
        14.0, 70.0, 500, 55, hora=10, mes=3,
        altitud=3150.0, latitud=4.3304, longitud=-74.3247, densidad_urbana=0.05,
    )

    fila = X.iloc[0]
    assert fila["altitud"] == 3150.0
    assert fila["latitud"] == 4.3304
    assert fila["longitud"] == -74.3247
    assert fila["densidad_urbana"] == 0.05


def test_features_from_raw_usa_defaults_de_localidad():
    fila = features_from_raw(14.0, 70.0, 500, 55, hora=10, mes=3).iloc[0]

    assert fila["altitud"] == DEFAULT_ALTITUD
    assert fila["densidad_urbana"] == DEFAULT_DENSIDAD


@pytest.mark.parametrize("hora,esperado", [(5, 0), (6, 1), (18, 1), (19, 0)])
def test_features_from_raw_es_dia_coincide_con_create_features(hora, esperado):
    """Ambos caminos (batch y en vivo) deben aplicar el mismo criterio."""
    fila = features_from_raw(14.0, 70.0, 500, 55, hora=hora, mes=3).iloc[0]

    assert fila["es_dia"] == esperado


def test_features_from_raw_presion_vapor_coincide_con_create_features():
    """Regresión: las dos rutas de cálculo no deben divergir."""
    temp, hum = 14.0, 70.0

    fila = features_from_raw(temp, hum, 500, 55, hora=10, mes=3).iloc[0]

    assert fila["presion_vapor"] == pytest.approx(
        _presion_vapor_esperada(temp, hum), abs=1e-4
    )
