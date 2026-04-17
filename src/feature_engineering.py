import numpy as np
import pandas as pd

# Columnas que usa el modelo — importar desde aquí para mantener consistencia
FEATURE_COLS = [
    "temperatura", "humedad", "luz", "ruido",
    "hora_sin", "hora_cos",       # codificación cíclica de hora
    "mes_sin", "mes_cos",         # codificación cíclica de mes
    "es_dia",                     # flag binario día/noche
    "temp_prom_30m",              # promedio móvil 30 min (3 lecturas)
    "temp_prom_1h",               # promedio móvil 1 hora (6 lecturas)
    "cambio_temp",                # delta temperatura 10 min
    "tendencia_1h",               # delta temperatura 1 hora
    "humedad_prom",               # promedio móvil humedad 30 min
    "presion_vapor",              # presión de vapor (proxy físico)
]


def create_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    hora = df["timestamp"].dt.hour
    mes = df["timestamp"].dt.month

    # Codificación cíclica — evita discontinuidad en 23→0 y en dic→ene
    df["hora_sin"] = np.sin(2 * np.pi * hora / 24)
    df["hora_cos"] = np.cos(2 * np.pi * hora / 24)
    df["mes_sin"]  = np.sin(2 * np.pi * mes / 12)
    df["mes_cos"]  = np.cos(2 * np.pi * mes / 12)

    df["es_dia"] = ((hora >= 6) & (hora <= 18)).astype(int)

    # Promedios móviles de temperatura
    df["temp_prom_30m"] = df["temperatura"].rolling(window=3, min_periods=1).mean()
    df["temp_prom_1h"]  = df["temperatura"].rolling(window=6, min_periods=1).mean()

    # Tasas de cambio
    df["cambio_temp"]  = df["temperatura"].diff().fillna(0)
    df["tendencia_1h"] = df["temperatura"].diff(6).fillna(0)

    # Promedio móvil de humedad
    df["humedad_prom"] = df["humedad"].rolling(window=3, min_periods=1).mean()

    # Presión de vapor (fórmula Magnus aproximada) — magnitud física útil
    df["presion_vapor"] = (
        (df["humedad"] / 100)
        * 6.1078
        * np.exp(17.27 * df["temperatura"] / (237.3 + df["temperatura"]))
    ).round(4)

    return df


def create_target(df: pd.DataFrame, steps: int = 3) -> pd.DataFrame:
    """Agrega temp_futura (steps × 10 min hacia adelante) y elimina NaN."""
    df = df.copy()
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
) -> pd.DataFrame:
    """
    Construye un DataFrame de una fila con todos los FEATURE_COLS
    a partir de valores crudos del sensor.

    Si se pasa `historia` (DataFrame con columnas temperatura/humedad
    y al menos 6 filas recientes), se calculan los promedios móviles
    reales. Sin historia, se usan el valor actual como proxy.
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
        "temperatura":   temperatura,
        "humedad":       humedad,
        "luz":           luz,
        "ruido":         ruido,
        "hora_sin":      hora_sin,
        "hora_cos":      hora_cos,
        "mes_sin":       mes_sin,
        "mes_cos":       mes_cos,
        "es_dia":        es_dia,
        "temp_prom_30m": temp_prom_30m,
        "temp_prom_1h":  temp_prom_1h,
        "cambio_temp":   cambio_temp,
        "tendencia_1h":  tendencia_1h,
        "humedad_prom":  humedad_prom,
        "presion_vapor": presion_vapor,
    }])[FEATURE_COLS]
