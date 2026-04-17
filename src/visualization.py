import pandas as pd
import os
import matplotlib.pyplot as plt
import joblib
from sklearn.model_selection import train_test_split

# -------------------------
# 📁 Rutas
# -------------------------
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_path = os.path.join(base_dir, "data", "raw", "data.csv")
model_path = os.path.join(base_dir, "models", "model.pkl")

# -------------------------
# 📊 Cargar datos
# -------------------------
df = pd.read_csv(data_path)
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Features
df["hora"] = df["timestamp"].dt.hour
df["temp_prom"] = df["temperatura"].rolling(window=3).mean()
df["cambio_temp"] = df["temperatura"].diff()
df["temp_futura"] = df["temperatura"].shift(-3)

df = df.dropna()

# Variables
X = df[["temperatura", "humedad", "luz", "hora", "temp_prom", "cambio_temp"]]
y = df["temp_futura"]

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, shuffle=False
)

# -------------------------
# 🤖 Cargar modelo
# -------------------------
model = joblib.load(model_path)

y_pred = model.predict(X_test)

# -------------------------
# 📈 GRÁFICA 1
# -------------------------
plt.figure()
plt.plot(y_test.values[:200], label="Real")
plt.plot(y_pred[:200], label="Predicción")
plt.title("Predicción vs Real (Temperatura)")
plt.xlabel("Tiempo")
plt.ylabel("Temperatura")
plt.legend()
plt.show()

# -------------------------
# 📉 GRÁFICA 2: Error
# -------------------------
error = y_test.values - y_pred

plt.figure()
plt.plot(error[:300])
plt.title("Error de Predicción")
plt.xlabel("Tiempo")
plt.ylabel("Error (°C)")
plt.show()

# -------------------------
# 🌡️ GRÁFICA 3: Temperatura en el tiempo
# -------------------------
plt.figure()
plt.plot(df["timestamp"][:500], df["temperatura"][:500])
plt.title("Temperatura en el tiempo")
plt.xlabel("Fecha")
plt.ylabel("Temperatura")
plt.xticks(rotation=45)
plt.show()