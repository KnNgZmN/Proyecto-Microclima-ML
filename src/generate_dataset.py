import pandas as pd
import numpy as np
import os

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_path = os.path.join(base_dir, "data", "raw")
os.makedirs(data_path, exist_ok=True)

np.random.seed(42)

num_dias = 180
frecuencia_min = 10

date_range = pd.date_range(
    start="2025-01-01",
    periods=int((24 * 60 / frecuencia_min) * num_dias),
    freq=f"{frecuencia_min}min"
)

N = len(date_range)
df = pd.DataFrame({"timestamp": date_range})
df["hora"] = df["timestamp"].dt.hour
df["mes"] = df["timestamp"].dt.month

# -------------------------------------------------------
# Probabilidad de lluvia por mes (patrón bimodal Bogotá)
# Temporadas lluviosas: abr-may y oct-nov
# -------------------------------------------------------
lluvia_prob_mes = {
    1: 0.12, 2: 0.15, 3: 0.28, 4: 0.45,
    5: 0.48, 6: 0.22, 7: 0.18, 8: 0.20,
    9: 0.35, 10: 0.46, 11: 0.44, 12: 0.18
}

# Ventana de lluvia por día: inicio y fin en horas
dias_unicos = df["timestamp"].dt.date.unique()
ventanas_lluvia = {}
for dia in dias_unicos:
    mes = pd.Timestamp(dia).month
    if np.random.random() < lluvia_prob_mes[mes]:
        inicio = np.random.randint(12, 15)   # lluvia típicamente 12-15h en Bogotá
        duracion = np.random.randint(1, 4)   # 1-3 horas
        ventanas_lluvia[dia] = (inicio, inicio + duracion)
    else:
        ventanas_lluvia[dia] = None

def marca_lluvia(ts):
    ventana = ventanas_lluvia.get(ts.date())
    if ventana is None:
        return 0
    return 1 if ventana[0] <= ts.hour < ventana[1] else 0

df["lluvia"] = df["timestamp"].apply(marca_lluvia)

# Nubosidad diaria (0=despejado, 1=muy nublado) — afecta luz y temperatura
nubosidad_dia = {dia: np.random.beta(2, 5) for dia in dias_unicos}
df["nubosidad"] = df["timestamp"].dt.date.map(nubosidad_dia)

# -------------------------------------------------------
# TEMPERATURA — base Bogotá (~7-19 °C)
# Pico ~14h (desplazamiento -π/2 del seno)
# -------------------------------------------------------
hora_rad = (df["hora"] / 24) * 2 * np.pi

variacion_mes = {
    1: 1.0, 2: 1.5, 3: 0.5, 4: -0.5, 5: -0.8,
    6: 0.3, 7: 0.8, 8: 0.8, 9: 0.0, 10: -0.5,
    11: -0.8, 12: 0.5
}

df["temperatura"] = (
    13.0
    + 6.0 * np.sin(hora_rad - np.pi / 2)
    + df["mes"].map(variacion_mes)
    - 1.5 * df["nubosidad"]          # días nublados más fríos
    + np.random.normal(0, 0.8, N)    # ruido de sensor
)

# Caída brusca por lluvia (3-6 °C)
lluvia_mask = df["lluvia"] == 1
df.loc[lluvia_mask, "temperatura"] -= np.random.uniform(3.0, 6.0, lluvia_mask.sum())

# Drift del sensor: +0.05 °C/mes (degradación gradual)
dias_transcurridos = (df["timestamp"] - df["timestamp"].iloc[0]).dt.days
df["temperatura"] += dias_transcurridos / 30 * 0.05

# Anomalías/picos (≈3 % de lecturas): simula lecturas erróneas del sensor
spike_mask = np.random.random(N) < 0.03
spike_vals = np.random.choice([-7, -6, 5, 6, 8], spike_mask.sum())
df.loc[spike_mask, "temperatura"] += spike_vals

df["temperatura"] = df["temperatura"].round(2)

# -------------------------------------------------------
# HUMEDAD
# -------------------------------------------------------
df["humedad"] = (
    72.0
    - 8.0 * np.sin(hora_rad - np.pi / 2)
    + 15.0 * df["nubosidad"]
    + np.random.normal(0, 4.0, N)
)
df.loc[lluvia_mask, "humedad"] += np.random.uniform(15.0, 25.0, lluvia_mask.sum())
df["humedad"] = df["humedad"].clip(40, 100).round(1)

# -------------------------------------------------------
# LUZ (lux)
# -------------------------------------------------------
luz_base = np.where(
    (df["hora"] >= 6) & (df["hora"] <= 18),
    np.random.randint(500, 1001, N),
    np.random.randint(0, 51, N)
)
# Reducción por nubosidad y lluvia
reduccion_nubosidad = (df["nubosidad"] * 400).values
reduccion_lluvia = (df["lluvia"] * np.random.uniform(300, 600, N))
df["luz"] = np.clip(luz_base - reduccion_nubosidad - reduccion_lluvia, 0, 1000).astype(int)

# -------------------------------------------------------
# RUIDO (dB)
# -------------------------------------------------------
ruido_base = np.where(
    ((df["hora"] >= 7) & (df["hora"] <= 9)) | ((df["hora"] >= 17) & (df["hora"] <= 19)),
    np.random.randint(60, 91, N),
    np.random.randint(30, 61, N)
)
ruido_lluvia = (df["lluvia"] * np.random.uniform(5, 15, N)).values
df["ruido"] = np.clip(ruido_base + ruido_lluvia, 30, 100).astype(int)

# -------------------------------------------------------
# Dataset final — solo columnas de sensor
# -------------------------------------------------------
df = df[["timestamp", "temperatura", "humedad", "luz", "ruido"]]

file_path = os.path.join(data_path, "data.csv")
df.to_csv(file_path, index=False)

print("✅ Dataset generado con éxito")
print(f"📁 Guardado en: {file_path}")
print(f"📊 Registros: {len(df):,} ({num_dias} días × {frecuencia_min} min)")
print(df.describe().round(2))
