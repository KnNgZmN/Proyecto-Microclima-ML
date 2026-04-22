import numpy as np
import pandas as pd

# Coordenadas y altitud del centro histórico de Bogotá (La Candelaria)
# — valores por defecto cuando no se especifica localidad
DEFAULT_LAT      = 4.5969
DEFAULT_LON      = -74.0680
DEFAULT_ALTITUD  = 2625.0
DEFAULT_DENSIDAD = 0.70

FEATURE_COLS = [
    # Lecturas crudas del sensor
    "temperatura", "humedad", "luz", "ruido",
    # Codificación cíclica temporal
    "hora_sin", "hora_cos",
    "mes_sin",  "mes_cos",
    # Contexto temporal
    "es_dia",
    # Promedios móviles de temperatura
    "temp_prom_30m",
    "temp_prom_1h",
    # Tasas de cambio
    "cambio_temp",
    "tendencia_1h",
    # Promedio móvil de humedad
    "humedad_prom",
    # Proxy físico de energía disponible en el aire
    "presion_vapor",
    # Geolocalización — diferencian microclima por localidad
    "altitud",
    "latitud",
    "longitud",
    "densidad_urbana",
]


def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega todas las columnas derivadas que usa el modelo.
    Si el DataFrame tiene columna 'localidad_id', los promedios
    móviles y deltas se calculan dentro de cada grupo para no
    contaminar los límites entre localidades.
    """
    df = df.copy()

    hora = df["timestamp"].dt.hour
    mes  = df["timestamp"].dt.month

    df["hora_sin"] = np.sin(2 * np.pi * hora / 24)
    df["hora_cos"] = np.cos(2 * np.pi * hora / 24)
    df["mes_sin"]  = np.sin(2 * np.pi * mes / 12)
    df["mes_cos"]  = np.cos(2 * np.pi * mes / 12)
    df["es_dia"]   = ((hora >= 6) & (hora <= 18)).astype(int)

    if "localidad_id" in df.columns:
        grp = df.groupby("localidad_id", sort=False)
        df["temp_prom_30m"] = grp["temperatura"].transform(
            lambda x: x.rolling(3, min_periods=1).mean()
        )
        df["temp_prom_1h"] = grp["temperatura"].transform(
            lambda x: x.rolling(6, min_periods=1).mean()
        )
        df["cambio_temp"]  = grp["temperatura"].transform(
            lambda x: x.diff().fillna(0)
        )
        df["tendencia_1h"] = grp["temperatura"].transform(
            lambda x: x.diff(6).fillna(0)
        )
        df["humedad_prom"] = grp["humedad"].transform(
            lambda x: x.rolling(3, min_periods=1).mean()
        )
    else:
        df["temp_prom_30m"] = df["temperatura"].rolling(3, min_periods=1).mean()
        df["temp_prom_1h"]  = df["temperatura"].rolling(6, min_periods=1).mean()
        df["cambio_temp"]   = df["temperatura"].diff().fillna(0)
        df["tendencia_1h"]  = df["temperatura"].diff(6).fillna(0)
        df["humedad_prom"]  = df["humedad"].rolling(3, min_periods=1).mean()

    df["presion_vapor"] = (
        (df["humedad"] / 100)
        * 6.1078
        * np.exp(17.27 * df["temperatura"] / (237.3 + df["temperatura"]))
    ).round(4)

    # Si las columnas de geolocalización no existen, usar defaults
    for col, default in [
        ("altitud",         DEFAULT_ALTITUD),
        ("latitud",         DEFAULT_LAT),
        ("longitud",        DEFAULT_LON),
        ("densidad_urbana", DEFAULT_DENSIDAD),
    ]:
        if col not in df.columns:
            df[col] = default

    return df


def create_target(df: pd.DataFrame, steps: int = 3) -> pd.DataFrame:
    """Agrega temp_futura (steps × 10 min adelante) dentro de cada localidad."""
    df = df.copy()
    if "localidad_id" in df.columns:
        df["temp_futura"] = df.groupby("localidad_id")["temperatura"].transform(
            lambda x: x.shift(-steps)
        )
    else:
        df["temp_futura"] = df["temperatura"].shift(-steps)
    return df.dropna(subset=["temp_futura"])


def features_from_raw(
    temperatura: float,
    humedad: float,
    luz: float,
    ruido: float,
    hora: int,
    mes: int,
    historia: pd.DataFrame = None,
    altitud: float = DEFAULT_ALTITUD,
    latitud: float = DEFAULT_LAT,
    longitud: float = DEFAULT_LON,
    densidad_urbana: float = DEFAULT_DENSIDAD,
) -> pd.DataFrame:
    """
    Construye un DataFrame de una fila con todos los FEATURE_COLS
    a partir de valores crudos del sensor y metadatos de localidad.

    historia : DataFrame con columnas temperatura/humedad (últimas lecturas)
               para calcular promedios móviles reales.
    """
    hora_sin = np.sin(2 * np.pi * hora / 24)
    hora_cos = np.cos(2 * np.pi * hora / 24)
    mes_sin  = np.sin(2 * np.pi * mes / 12)
    mes_cos  = np.cos(2 * np.pi * mes / 12)
    es_dia   = 1 if 6 <= hora <= 18 else 0

    presion_vapor = (
        (humedad / 100) * 6.1078
        * np.exp(17.27 * temperatura / (237.3 + temperatura))
    )

    if historia is not None and len(historia) >= 2:
        temps = list(historia["temperatura"].tail(6)) + [temperatura]
        hums  = list(historia["humedad"].tail(3)) + [humedad]
        temp_prom_30m = float(np.mean(temps[-3:]))
        temp_prom_1h  = float(np.mean(temps[-6:]))
        cambio_temp   = temperatura - temps[-2] if len(temps) >= 2 else 0.0
        tendencia_1h  = temperatura - temps[0]  if len(temps) >= 7 else 0.0
        humedad_prom  = float(np.mean(hums[-3:]))
    else:
        temp_prom_30m = temperatura
        temp_prom_1h  = temperatura
        cambio_temp   = 0.0
        tendencia_1h  = 0.0
        humedad_prom  = humedad

    return pd.DataFrame([{
        "temperatura":    temperatura,
        "humedad":        humedad,
        "luz":            luz,
        "ruido":          ruido,
        "hora_sin":       hora_sin,
        "hora_cos":       hora_cos,
        "mes_sin":        mes_sin,
        "mes_cos":        mes_cos,
        "es_dia":         es_dia,
        "temp_prom_30m":  temp_prom_30m,
        "temp_prom_1h":   temp_prom_1h,
        "cambio_temp":    cambio_temp,
        "tendencia_1h":   tendencia_1h,
        "humedad_prom":   humedad_prom,
        "presion_vapor":  presion_vapor,
        "altitud":        altitud,
        "latitud":        latitud,
        "longitud":       longitud,
        "densidad_urbana": densidad_urbana,
    }])[FEATURE_COLS]
