"""
Generador de dataset sintético multi-localidad para Bogotá D.C.

Produce datos realistas para las 20 localidades usando:
  - Corrección altitudinal (tasa de caída ambiental: 6.5 °C/1000 m)
  - Isla de calor urbana (mayor efecto nocturno en zonas densas)
  - Patrón bimodal de lluvias de Bogotá (abr-may y oct-nov)
  - Mayor probabilidad de lluvia en localidades orientales (mayores)
  - Ciclos diurnos y estacionales calibrados con datos IDEAM
"""

import pandas as pd
import numpy as np
import os

from localidades import LOCALIDADES, ALT_REFERENCIA, LAPSE_RATE

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_path = os.path.join(base_dir, "data", "raw")
os.makedirs(data_path, exist_ok=True)

NUM_DIAS = 90          # días por localidad (≈ 3 meses, manejable en RAM)
FRECUENCIA_MIN = 10    # intervalo entre lecturas en minutos

date_range = pd.date_range(
    start="2025-01-01",
    periods=int((24 * 60 / FRECUENCIA_MIN) * NUM_DIAS),
    freq=f"{FRECUENCIA_MIN}min",
)

LLUVIA_PROB_MES = {
    1: 0.12, 2: 0.15, 3: 0.28, 4: 0.45,
    5: 0.48, 6: 0.22, 7: 0.18, 8: 0.20,
    9: 0.35, 10: 0.46, 11: 0.44, 12: 0.18,
}

VARIACION_MES_TEMP = {
    1: 1.0, 2: 1.5, 3: 0.5, 4: -0.5, 5: -0.8,
    6: 0.3, 7: 0.8, 8: 0.8, 9: 0.0, 10: -0.5,
    11: -0.8, 12: 0.5,
}


def _generar_localidad(localidad_id: int, info: dict) -> pd.DataFrame:
    """Genera un DataFrame de lecturas para una sola localidad."""
    rng = np.random.RandomState(42 + localidad_id)
    N = len(date_range)

    hora_arr = np.array(date_range.hour,  dtype=int)
    mes_arr  = np.array(date_range.month, dtype=int)
    hora_rad = (hora_arr / 24) * 2 * np.pi

    alt      = info["altitud"]
    densidad = info["densidad_urbana"]

    # Corrección altitudinal: mayor altitud → temperatura más baja
    alt_corr = (ALT_REFERENCIA - alt) * LAPSE_RATE

    # Isla de calor urbana: efecto diurno moderado, nocturno más pronunciado
    es_dia = (hora_arr >= 6) & (hora_arr <= 18)
    uhi = np.where(es_dia, (densidad - 0.5) * 1.0, (densidad - 0.5) * 2.5)

    # ---- Lluvia ------------------------------------------------
    # Localidades más altas (oriente) tienen mayor probabilidad de lluvia
    factor_lluvia = 1.0 + (alt - ALT_REFERENCIA) / 1500.0

    dias_unicos = pd.Series(date_range).dt.date.unique()
    ventanas_lluvia: dict = {}
    for dia in dias_unicos:
        mes = pd.Timestamp(dia).month
        prob = min(LLUVIA_PROB_MES[mes] * factor_lluvia, 0.75)
        if rng.random() < prob:
            inicio   = rng.randint(11, 15)
            duracion = rng.randint(1, 4)
            ventanas_lluvia[dia] = (inicio, inicio + duracion)
        else:
            ventanas_lluvia[dia] = None

    lluvia = np.array([
        1 if (v := ventanas_lluvia.get(ts.date())) and v[0] <= ts.hour < v[1] else 0
        for ts in date_range
    ], dtype=float)

    # Nubosidad diaria (0=despejado, 1=muy nublado)
    nubosidad_dia = {dia: rng.beta(2, 5) for dia in dias_unicos}
    nubosidad = np.array([
        nubosidad_dia[ts.date()] for ts in date_range
    ], dtype=float)

    # ---- Temperatura -------------------------------------------
    mes_var = np.array([VARIACION_MES_TEMP[m] for m in mes_arr], dtype=float)
    lluvia_mask = lluvia == 1

    temperatura = (
        13.0
        + 6.0 * np.sin(hora_rad - np.pi / 2)
        + mes_var
        + alt_corr
        + uhi
        - 1.5 * nubosidad
        + rng.normal(0, 0.8, N)
    )
    temperatura[lluvia_mask] -= rng.uniform(3.0, 6.0, int(lluvia_mask.sum()))

    # Drift gradual del sensor (+0.05 °C/mes)
    dias_elapsed = (date_range - date_range[0]).days
    temperatura += dias_elapsed / 30 * 0.05

    # Anomalías de sensor (≈3 % de lecturas)
    spike_mask = rng.random(N) < 0.03
    spike_vals = rng.choice([-7, -6, 5, 6, 8], int(spike_mask.sum()))
    temperatura[spike_mask] += spike_vals

    temperatura = np.round(temperatura, 2)

    # ---- Humedad -----------------------------------------------
    # Zonas altas y rurales tienden a ser más húmedas
    humedad_base = 72.0 + (alt - ALT_REFERENCIA) * 0.005 + (1 - densidad) * 5.0
    humedad = (
        humedad_base
        - 8.0 * np.sin(hora_rad - np.pi / 2)
        + 15.0 * nubosidad
        + rng.normal(0, 4.0, N)
    )
    humedad[lluvia_mask] += rng.uniform(15.0, 25.0, int(lluvia_mask.sum()))
    humedad = np.clip(humedad, 40, 100).round(1)

    # ---- Luz (lux) ---------------------------------------------
    luz_base = np.where(
        (hora_arr >= 6) & (hora_arr <= 18),
        rng.randint(500, 1001, N),
        rng.randint(0, 51, N),
    )
    reduccion_nubosidad = nubosidad * 400
    reduccion_lluvia    = lluvia * rng.uniform(300, 600, N)
    luz = np.clip(luz_base - reduccion_nubosidad - reduccion_lluvia, 0, 1000).astype(int)

    # ---- Ruido (dB) --------------------------------------------
    # Zonas más densas tienen niveles de ruido más altos
    ruido_base_nivel = 40 + densidad * 20
    hora_pico = ((hora_arr >= 7) & (hora_arr <= 9)) | ((hora_arr >= 17) & (hora_arr <= 19))

    lo_peak, hi_peak   = int(ruido_base_nivel + 10), int(ruido_base_nivel + 31)
    lo_off,  hi_off    = int(ruido_base_nivel - 10), int(ruido_base_nivel + 11)
    ruido_base = np.where(
        hora_pico,
        rng.randint(lo_peak, hi_peak, N),
        rng.randint(lo_off,  hi_off,  N),
    )
    ruido_lluvia_add = lluvia * rng.uniform(5, 15, N)
    ruido = np.clip(ruido_base + ruido_lluvia_add, 30, 100).astype(int)

    df = pd.DataFrame({
        "timestamp":       date_range,
        "localidad_id":    localidad_id,
        "localidad":       info["nombre"],
        "latitud":         round(info["lat"], 4),
        "longitud":        round(info["lon"], 4),
        "altitud":         float(alt),
        "densidad_urbana": round(float(densidad), 2),
        "temperatura":     temperatura,
        "humedad":         humedad,
        "luz":             luz,
        "ruido":           ruido,
    })

    return df


# ---------------------------------------------------------------
# Generar y combinar todas las localidades
# ---------------------------------------------------------------
print(f"Generando datos para {len(LOCALIDADES)} localidades x {NUM_DIAS} dias...")

frames = []
for lid, info in LOCALIDADES.items():
    frames.append(_generar_localidad(lid, info))
    print(f"  OK {info['nombre']:25s}  alt={info['altitud']}m  densidad={info['densidad_urbana']}")

# Ordenar por timestamp para que TimeSeriesSplit funcione correctamente
df_all = pd.concat(frames, ignore_index=True)
df_all = df_all.sort_values(["timestamp", "localidad_id"]).reset_index(drop=True)

file_path = os.path.join(data_path, "data.csv")
df_all.to_csv(file_path, index=False)

print(f"\nDataset multi-localidad generado con exito")
print(f"Guardado en: {file_path}")
print(f"Registros totales: {len(df_all):,}  ({NUM_DIAS} dias x {len(LOCALIDADES)} localidades x {FRECUENCIA_MIN} min)")
print(f"Columnas: {list(df_all.columns)}")
print("\nRango de temperatura por localidad:")
resumen = df_all.groupby("localidad")["temperatura"].agg(["min", "mean", "max"]).round(2)
resumen.columns = ["min C", "media C", "max C"]
print(resumen.sort_values("media C").to_string())
