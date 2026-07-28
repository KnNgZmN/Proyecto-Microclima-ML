"""Pruebas de src/data_processing.py — carga y saneamiento de lecturas."""

import pandas as pd
import pytest

from data_processing import RANGOS_VALIDOS, clean_data, load_data


# ---------------------------------------------------------------
# load_data
# ---------------------------------------------------------------
def test_load_data_convierte_timestamp_a_datetime(tmp_path):
    csv = tmp_path / "data.csv"
    csv.write_text(
        "timestamp,temperatura,humedad,luz,ruido\n"
        "2025-03-10 00:00:00,14.5,70.0,0,45\n"
        "2025-03-10 00:10:00,14.8,71.0,0,46\n",
        encoding="utf-8",
    )

    df = load_data(str(csv))

    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])
    assert len(df) == 2
    assert df["timestamp"].iloc[0] == pd.Timestamp("2025-03-10 00:00:00")


# ---------------------------------------------------------------
# clean_data — valores fuera de rango
# ---------------------------------------------------------------
@pytest.mark.parametrize("columna", list(RANGOS_VALIDOS))
def test_clean_data_interpola_valor_sobre_el_limite(df_una_localidad, columna):
    """Un valor por encima del máximo se reemplaza por interpolación, no se conserva."""
    _, hi = RANGOS_VALIDOS[columna]
    df = df_una_localidad.copy()
    df.loc[2, columna] = hi + 100

    limpio = clean_data(df)

    assert len(limpio) == len(df)
    assert limpio[columna].max() <= hi


@pytest.mark.parametrize("columna", list(RANGOS_VALIDOS))
def test_clean_data_interpola_valor_bajo_el_limite(df_una_localidad, columna):
    lo, _ = RANGOS_VALIDOS[columna]
    df = df_una_localidad.copy()
    df.loc[2, columna] = lo - 100

    limpio = clean_data(df)

    assert len(limpio) == len(df)
    assert limpio[columna].min() >= lo


def test_clean_data_interpola_con_el_valor_intermedio(df_una_localidad):
    """La interpolación es lineal: 11.0 y 13.0 alrededor de un hueco → 12.0."""
    df = df_una_localidad.copy()
    df.loc[2, "temperatura"] = 999.0   # fuera de rango → NaN → interpolado

    limpio = clean_data(df)

    assert limpio.loc[2, "temperatura"] == pytest.approx(12.0)


def test_clean_data_conserva_valores_en_los_limites(df_una_localidad):
    """Los extremos del rango son inclusivos y no deben marcarse como anomalía."""
    lo, hi = RANGOS_VALIDOS["temperatura"]
    df = df_una_localidad.copy()
    df.loc[1, "temperatura"] = lo
    df.loc[3, "temperatura"] = hi

    limpio = clean_data(df)

    assert limpio.loc[1, "temperatura"] == lo
    assert limpio.loc[3, "temperatura"] == hi


# ---------------------------------------------------------------
# clean_data — filas vacías, índice y no-mutación
# ---------------------------------------------------------------
def test_clean_data_elimina_filas_completamente_vacias(df_una_localidad):
    # reindex agrega una fila totalmente vacía conservando los dtypes numéricos
    df = df_una_localidad.reindex(range(len(df_una_localidad) + 1))

    limpio = clean_data(df)

    assert len(limpio) == 6


def test_clean_data_reinicia_el_indice(df_una_localidad):
    df = df_una_localidad.copy()
    df.loc[0, "temperatura"] = 999.0
    df.loc[1, "temperatura"] = 999.0

    limpio = clean_data(df)

    assert list(limpio.index) == list(range(len(limpio)))


def test_clean_data_no_muta_el_dataframe_original(df_una_localidad):
    original = df_una_localidad.copy()
    df_una_localidad.loc[2, "temperatura"] = 999.0
    entrada = df_una_localidad.copy()

    clean_data(df_una_localidad)

    pd.testing.assert_frame_equal(df_una_localidad, entrada)
    assert original.loc[2, "temperatura"] == 12.0


def test_clean_data_tolera_columnas_de_sensor_ausentes():
    """Cubre la rama 'if col in df.columns' cuando faltan sensores."""
    df = pd.DataFrame({
        "timestamp":   pd.date_range("2025-03-10", periods=3, freq="10min"),
        "temperatura": [14.0, 15.0, 16.0],
    })

    limpio = clean_data(df)

    assert list(limpio.columns) == ["timestamp", "temperatura"]
    assert len(limpio) == 3
