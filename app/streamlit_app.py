import sys
import os
import json
from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib

# Añadir src al path
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_base_dir, "src"))

from feature_engineering import features_from_raw, FEATURE_COLS
from data_processing import load_data, clean_data

# -------------------------------------------------------
# Rutas
# -------------------------------------------------------
DATA_PATH    = os.path.join(_base_dir, "data", "raw", "data.csv")
MODEL_PATH   = os.path.join(_base_dir, "models", "model.pkl")
METRICS_PATH = os.path.join(_base_dir, "models", "metrics.json")

# -------------------------------------------------------
# Carga de recursos (cacheados por Streamlit)
# -------------------------------------------------------
@st.cache_data
def cargar_datos():
    df = load_data(DATA_PATH)
    return clean_data(df)

@st.cache_resource
def cargar_modelo():
    return joblib.load(MODEL_PATH)

# -------------------------------------------------------
# UI principal
# -------------------------------------------------------
st.set_page_config(page_title="Microclima Bogotá", page_icon="🌫️", layout="wide")
st.title("🌫️ Microclima Bogotá — Predicción Inteligente")

# ---- Métricas del modelo (sidebar) ----
with st.sidebar:
    st.header("📋 Información del modelo")
    if os.path.exists(METRICS_PATH):
        with open(METRICS_PATH) as f:
            m = json.load(f)
        st.metric("MAE (validación cruzada)", f"{m['mae_cv_mean']:.3f} ± {m['mae_cv_std']:.3f} °C")
        st.metric("RMSE (validación cruzada)", f"{m['rmse_cv_mean']:.3f} ± {m['rmse_cv_std']:.3f} °C")
        st.caption(f"Features: {m['n_features']}  |  Registros: {m['n_registros']:,}")
    else:
        st.info("Ejecuta train_model.py para ver las métricas.")

    st.divider()
    st.caption("Datos reales via Arduino:")
    st.code("python src/arduino_collector.py --port COM3 --predict", language="bash")
    st.caption("Modo simulación:")
    st.code("python src/arduino_collector.py --simulate --predict", language="bash")

# -------------------------------------------------------
# Tabs principales
# -------------------------------------------------------
tab_datos, tab_prediccion, tab_arduino = st.tabs(
    ["📊 Datos históricos", "🔮 Predicción manual", "🔌 Modo Arduino"]
)

# ===========================
# TAB 1 — Datos históricos
# ===========================
with tab_datos:
    if not os.path.exists(DATA_PATH):
        st.warning("No se encontró data.csv. Ejecuta generate_dataset.py primero.")
        st.stop()

    df = cargar_datos()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Registros totales", f"{len(df):,}")
    col2.metric("Temp. promedio", f"{df['temperatura'].mean():.1f} °C")
    col3.metric("Humedad promedio", f"{df['humedad'].mean():.0f} %")
    col4.metric("Días cubiertos", f"{(df['timestamp'].max() - df['timestamp'].min()).days}")

    st.subheader("Últimas lecturas")
    st.dataframe(df.tail(10)[["timestamp", "temperatura", "humedad", "luz", "ruido"]], use_container_width=True)

    st.subheader("Temperatura — últimas 24 horas")
    ultimas = df.tail(144)   # 144 × 10 min = 24 h
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(ultimas["timestamp"], ultimas["temperatura"], color="#e05c2a", linewidth=1.2)
    ax.set_xlabel("Hora")
    ax.set_ylabel("°C")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    st.pyplot(fig)

    st.subheader("Temperatura vs Humedad (muestra 500 puntos)")
    muestra = df.sample(min(500, len(df))).sort_values("timestamp")
    fig2, ax2 = plt.subplots(figsize=(10, 3))
    ax2b = ax2.twinx()
    ax2.plot(muestra["timestamp"], muestra["temperatura"], color="#e05c2a", alpha=0.7, label="Temperatura")
    ax2b.plot(muestra["timestamp"], muestra["humedad"], color="#2a7be0", alpha=0.5, label="Humedad")
    ax2.set_ylabel("°C", color="#e05c2a")
    ax2b.set_ylabel("%", color="#2a7be0")
    ax2.grid(True, alpha=0.2)
    fig2.tight_layout()
    st.pyplot(fig2)

# ===========================
# TAB 2 — Predicción manual
# ===========================
with tab_prediccion:
    if not os.path.exists(MODEL_PATH):
        st.warning("Modelo no encontrado. Ejecuta train_model.py primero.")
        st.stop()

    model = cargar_modelo()

    st.markdown("Ingresa los valores actuales del sensor para predecir la temperatura en **30 minutos**.")

    c1, c2 = st.columns(2)
    with c1:
        temp    = st.number_input("🌡️ Temperatura actual (°C)", min_value=-2.0, max_value=30.0, value=13.5, step=0.1)
        humedad = st.number_input("💧 Humedad (%)", min_value=30.0, max_value=100.0, value=72.0, step=0.5)
        luz     = st.number_input("☀️ Luz (lux)", min_value=0.0, max_value=1100.0, value=600.0, step=10.0)
    with c2:
        ruido   = st.number_input("🔊 Ruido (dB)", min_value=20.0, max_value=110.0, value=45.0, step=1.0)
        hora    = st.slider("🕐 Hora del día", 0, 23, datetime.now().hour)
        mes     = st.slider("📅 Mes", 1, 12, datetime.now().month)

    # Buffer de historial en sesión (para promedios móviles reales)
    if "historia" not in st.session_state:
        st.session_state.historia = pd.DataFrame(columns=["temperatura", "humedad"])

    if st.button("🔮 Predecir temperatura T+30 min", type="primary"):
        historia = st.session_state.historia if len(st.session_state.historia) > 0 else None
        X = features_from_raw(temp, humedad, luz, ruido, hora, mes, historia)
        pred = float(model.predict(X)[0])
        delta = pred - temp

        st.success(f"🌡️ Temperatura estimada en 30 min: **{pred:.2f} °C**")
        st.metric("Cambio esperado", f"{delta:+.2f} °C", delta=round(delta, 2))

        # Guardar en historial de sesión
        nueva = pd.DataFrame([{"temperatura": temp, "humedad": humedad}])
        st.session_state.historia = pd.concat(
            [st.session_state.historia, nueva], ignore_index=True
        ).tail(20)

    if len(st.session_state.historia) > 0:
        with st.expander("Ver historial de la sesión"):
            st.dataframe(st.session_state.historia, use_container_width=True)
        if st.button("Limpiar historial"):
            st.session_state.historia = pd.DataFrame(columns=["temperatura", "humedad"])

# ===========================
# TAB 3 — Modo Arduino
# ===========================
with tab_arduino:
    st.markdown("""
    ### Integración con Arduino

    El módulo `arduino_collector.py` recibe datos del sensor en tiempo real
    y los guarda en `data/raw/data.csv` para re-entrenamiento continuo.

    #### Formato esperado por el Serial (Arduino → PC)
    ```
    18.50,72.30,850,45
    ```
    `temperatura(°C), humedad(%), luz(lux), ruido(dB)`

    #### Comandos
    | Acción | Comando |
    |--------|---------|
    | Colectar datos (Arduino real) | `python src/arduino_collector.py --port COM3` |
    | Colectar + predecir en vivo | `python src/arduino_collector.py --port COM3 --predict` |
    | Probar sin hardware | `python src/arduino_collector.py --simulate --predict` |
    | Ver sketch de referencia | `python src/arduino_collector.py --sketch` |
    | Re-entrenar modelo | `python src/train_model.py` |

    #### Sensores recomendados para el sketch
    | Sensor | Variable | Pines sugeridos |
    |--------|----------|-----------------|
    | DHT22  | Temperatura + Humedad | D2 |
    | LDR + R10k | Luz | A0 |
    | KY-038 | Ruido | A1 |
    """)

    if os.path.exists(DATA_PATH):
        df_check = load_data(DATA_PATH)
        ultima = df_check["timestamp"].max()
        hace = (datetime.now() - ultima.to_pydatetime()).seconds // 60
        if hace < 30:
            st.success(f"✅ Última lectura hace {hace} minutos — datos actualizados.")
        else:
            st.info(f"ℹ️  Última lectura hace {hace} minutos ({ultima.strftime('%Y-%m-%d %H:%M')}).")
