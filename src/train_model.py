import os
import json
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error

from data_processing import load_data, clean_data
from feature_engineering import create_features, create_target, FEATURE_COLS

base_dir   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_path  = os.path.join(base_dir, "data", "raw", "data.csv")
model_dir  = os.path.join(base_dir, "models")
os.makedirs(model_dir, exist_ok=True)

# ---------------------------------------------------------------
# Carga y limpieza
# ---------------------------------------------------------------
df = load_data(data_path)
df = clean_data(df)

# El dataset multi-localidad ya viene ordenado por [timestamp, localidad_id].
# TimeSeriesSplit respeta este orden: cada fold usa datos más recientes como test,
# garantizando que el modelo nunca vea el futuro durante la validación.
df = create_features(df)
df = create_target(df, steps=3)   # predice temperatura en t+30 min

X = df[FEATURE_COLS]
y = df["temp_futura"]

n_loc = df["localidad_id"].nunique() if "localidad_id" in df.columns else 1
print(f"[*] Registros para entrenamiento: {len(df):,}  ({n_loc} localidades)")
print(f"[F] Features ({len(FEATURE_COLS)}): {FEATURE_COLS}")

# ---------------------------------------------------------------
# Validación cruzada temporal — TimeSeriesSplit
# ---------------------------------------------------------------
tscv = TimeSeriesSplit(n_splits=5)
mae_folds, rmse_folds = [], []

for fold, (train_idx, test_idx) in enumerate(tscv.split(X), 1):
    X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
    y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]

    m = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
    m.fit(X_tr, y_tr)
    y_pred = m.predict(X_te)

    mae_folds.append(mean_absolute_error(y_te, y_pred))
    rmse_folds.append(np.sqrt(mean_squared_error(y_te, y_pred)))
    print(f"  Fold {fold}: MAE={mae_folds[-1]:.3f} °C  RMSE={rmse_folds[-1]:.3f} °C")

print(f"\n[CV] MAE promedio CV:  {np.mean(mae_folds):.3f} ± {np.std(mae_folds):.3f} °C")
print(f"[CV] RMSE promedio CV: {np.mean(rmse_folds):.3f} ± {np.std(rmse_folds):.3f} °C")

# ---------------------------------------------------------------
# Entrenamiento final con todos los datos
# ---------------------------------------------------------------
model = RandomForestRegressor(n_estimators=150, max_depth=12, random_state=42, n_jobs=-1)
model.fit(X, y)

importancias = pd.Series(model.feature_importances_, index=FEATURE_COLS)
importancias = importancias.sort_values(ascending=False)
print("\n[>] Importancia de features (top 10):")
print(importancias.head(10).round(4).to_string())

# ---------------------------------------------------------------
# Guardar modelo y métricas
# ---------------------------------------------------------------
joblib.dump(model, os.path.join(model_dir, "model.pkl"))

metricas = {
    "mae_cv_mean":   round(float(np.mean(mae_folds)), 4),
    "mae_cv_std":    round(float(np.std(mae_folds)), 4),
    "rmse_cv_mean":  round(float(np.mean(rmse_folds)), 4),
    "rmse_cv_std":   round(float(np.std(rmse_folds)), 4),
    "n_features":    len(FEATURE_COLS),
    "n_registros":   len(df),
    "n_localidades": n_loc,
    "feature_cols":  FEATURE_COLS,
}
with open(os.path.join(model_dir, "metrics.json"), "w") as f:
    json.dump(metricas, f, indent=2)

print("\n[OK] Modelo guardado en models/model.pkl")
print("[OK] Métricas guardadas en models/metrics.json")
