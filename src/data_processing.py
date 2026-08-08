import pandas as pd

# Rangos válidos para sensores de microclima en Bogotá
RANGOS_VALIDOS = {
    "temperatura": (-2.0, 30.0),   # °C — rango real posible en Bogotá
    "humedad":     (30.0, 100.0),  # %
    "luz":         (0.0, 1100.0),  # lux
    "ruido":       (20.0, 110.0),  # dB
}


def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Eliminar filas completamente vacías
    df = df.dropna(how="all")

    # Reemplazar valores fuera de rango con NaN (anomalías de sensor)
    for col, (lo, hi) in RANGOS_VALIDOS.items():
        if col in df.columns:
            mask_fuera = (df[col] < lo) | (df[col] > hi)
            if mask_fuera.any():
                df.loc[mask_fuera, col] = pd.NA

    # Interpolación lineal para rellenar huecos puntuales (máx. 3 consecutivos)
    cols_sensor = [c for c in RANGOS_VALIDOS if c in df.columns]
    df[cols_sensor] = (
        df[cols_sensor]
        .interpolate(method="linear", limit=3, limit_direction="both")
    )

    # Eliminar filas que siguen con NaN tras la interpolación
    df = df.dropna(subset=cols_sensor)

    return df.reset_index(drop=True)


# ---------------------------------------------------------------
# DEMO DE EXPOSICION - NO FUSIONAR
# Funcion nueva sin ninguna prueba, para demostrar el diff coverage.
# Deshacer con:  git checkout src/data_processing.py
# ---------------------------------------------------------------
def clasificar_confort(temp: float, hum: float) -> str:
    """Clasifica el confort termico de una lectura."""
    if temp < 12.0:
        return "frio"
    if temp > 24.0:
        return "calido"
    if hum > 85.0:
        return "humedo"
    return "confortable"
