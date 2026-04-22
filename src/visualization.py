"""
visualization.py — Gráficas de diagnóstico del modelo.

Genera tres gráficas para la localidad de Teusaquillo (ID=13):
  1. Predicción vs. valor real (primeras 200 muestras del set de test)
  2. Error de predicción en el tiempo
  3. Serie de temperatura con banda de error del modelo

Uso:
    python src/visualization.py
"""

import os
import sys
import joblib
import matplotlib.pyplot as plt
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_processing import load_data, clean_data
from feature_engineering import create_features, create_target, FEATURE_COLS
from localidades import LOCALIDADES

base_dir   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_path  = os.path.join(base_dir, "data", "raw", "data.csv")
model_path = os.path.join(base_dir, "models", "model.pkl")

LOCALIDAD_ID = 13   # Teusaquillo — sede universitaria

# ---------------------------------------------------------------
# Carga y preparación
# ---------------------------------------------------------------
if not os.path.exists(data_path):
    print("ERROR: data.csv no encontrado. Ejecuta generate_dataset.py primero.")
    sys.exit(1)

if not os.path.exists(model_path):
    print("ERROR: model.pkl no encontrado. Ejecuta train_model.py primero.")
    sys.exit(1)

print(f"Cargando datos y modelo para {LOCALIDADES[LOCALIDAD_ID]['nombre']}...")

df_raw = load_data(data_path)
df_raw = clean_data(df_raw)

# Filtrar solo la localidad de interés
df_loc = df_raw[df_raw["localidad_id"] == LOCALIDAD_ID].copy()
df_loc = create_features(df_loc)
df_loc = create_target(df_loc, steps=3)

X = df_loc[FEATURE_COLS]
y = df_loc["temp_futura"]

# Usar el último fold de TimeSeriesSplit como conjunto de test
tscv   = TimeSeriesSplit(n_splits=5)
splits = list(tscv.split(X))
_, test_idx = splits[-1]

X_test = X.iloc[test_idx]
y_test = y.iloc[test_idx]
ts_test = df_loc["timestamp"].iloc[test_idx]

model  = joblib.load(model_path)
y_pred = model.predict(X_test)
error  = y_test.values - y_pred
mae    = mean_absolute_error(y_test, y_pred)

print(f"MAE en test (ultimo fold): {mae:.3f} C")
print(f"Registros en test:         {len(y_test):,}")

# ---------------------------------------------------------------
# Grafica 1 — Prediccion vs Real
# ---------------------------------------------------------------
N = min(200, len(y_test))
fig1, ax1 = plt.subplots(figsize=(12, 4))
ax1.plot(range(N), y_test.values[:N], label="Real",      color="#2a7be0", linewidth=1.4)
ax1.plot(range(N), y_pred[:N],        label="Prediccion", color="#e05c2a", linewidth=1.2, linestyle="--")
ax1.set_title(f"Prediccion vs Real — {LOCALIDADES[LOCALIDAD_ID]['nombre']} (primeras {N} muestras del test)")
ax1.set_xlabel("Muestra")
ax1.set_ylabel("Temperatura (°C)")
ax1.legend()
ax1.grid(True, alpha=0.3)
fig1.tight_layout()

# ---------------------------------------------------------------
# Grafica 2 — Error en el tiempo
# ---------------------------------------------------------------
N2 = min(300, len(error))
fig2, ax2 = plt.subplots(figsize=(12, 3))
ax2.plot(ts_test.values[:N2], error[:N2], color="#444", linewidth=0.8, alpha=0.7)
ax2.axhline(0,   color="red",    linewidth=1.0, linestyle="--")
ax2.axhline(mae, color="orange", linewidth=0.9, linestyle=":", label=f"+MAE ({mae:.2f} °C)")
ax2.axhline(-mae,color="orange", linewidth=0.9, linestyle=":")
ax2.set_title("Error de prediccion en el tiempo (Real - Prediccion)")
ax2.set_xlabel("Fecha")
ax2.set_ylabel("Error (°C)")
ax2.legend()
ax2.grid(True, alpha=0.3)
plt.xticks(rotation=30)
fig2.tight_layout()

# ---------------------------------------------------------------
# Grafica 3 — Serie de temperatura + banda de error
# ---------------------------------------------------------------
N3 = min(500, len(y_test))
ts_plot   = ts_test.values[:N3]
real_plot = y_test.values[:N3]
pred_plot = y_pred[:N3]

fig3, ax3 = plt.subplots(figsize=(12, 4))
ax3.fill_between(ts_plot, pred_plot - mae, pred_plot + mae,
                 alpha=0.25, color="#e05c2a", label=f"Banda ±MAE ({mae:.2f} °C)")
ax3.plot(ts_plot, real_plot, label="Real",       color="#2a7be0", linewidth=1.2)
ax3.plot(ts_plot, pred_plot, label="Prediccion", color="#e05c2a", linewidth=1.0, linestyle="--")
ax3.set_title(f"Temperatura T+30 min — {LOCALIDADES[LOCALIDAD_ID]['nombre']}")
ax3.set_xlabel("Fecha")
ax3.set_ylabel("Temperatura (°C)")
ax3.legend()
ax3.grid(True, alpha=0.3)
plt.xticks(rotation=30)
fig3.tight_layout()

plt.show()
