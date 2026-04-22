import sys
import os
import json
from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib

_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_base_dir, "src"))

from feature_engineering import features_from_raw, FEATURE_COLS
from data_processing import load_data, clean_data
from localidades import LOCALIDADES

DATA_PATH    = os.path.join(_base_dir, "data", "raw", "data.csv")
MODEL_PATH   = os.path.join(_base_dir, "models", "model.pkl")
METRICS_PATH = os.path.join(_base_dir, "models", "metrics.json")

# Mapa rápido nombre → id para el selector de UI
_NOMBRE_A_ID = {v["nombre"]: k for k, v in LOCALIDADES.items()}
_NOMBRES_ORD = [LOCALIDADES[i]["nombre"] for i in sorted(LOCALIDADES)]


@st.cache_data
def cargar_datos():
    df = load_data(DATA_PATH)
    return clean_data(df)


@st.cache_resource
def cargar_modelo():
    return joblib.load(MODEL_PATH)


# ---------------------------------------------------------------
# Config página
# ---------------------------------------------------------------
st.set_page_config(
    page_title="Microclima Bogotá — Localidades",
    page_icon="🌫️",
    layout="wide",
)
st.title("🌫️ Microclima Bogotá D.C. — Predicción por Localidad")

# ---------------------------------------------------------------
# Sidebar — métricas del modelo
# ---------------------------------------------------------------
with st.sidebar:
    st.header("📋 Modelo")
    if os.path.exists(METRICS_PATH):
        with open(METRICS_PATH) as f:
            m = json.load(f)
        st.metric("MAE (CV)", f"{m['mae_cv_mean']:.3f} ± {m['mae_cv_std']:.3f} °C")
        st.metric("RMSE (CV)", f"{m['rmse_cv_mean']:.3f} ± {m['rmse_cv_std']:.3f} °C")
        n_loc = m.get("n_localidades", "—")
        st.caption(
            f"Features: {m['n_features']}  |  "
            f"Registros: {m['n_registros']:,}  |  "
            f"Localidades: {n_loc}"
        )
    else:
        st.info("Ejecuta train_model.py para ver métricas.")

    st.divider()
    st.markdown("**Comandos rápidos**")
    st.code("python src/generate_dataset.py", language="bash")
    st.code("python src/train_model.py",      language="bash")
    st.code("python src/arduino_collector.py --port COM3 --predict", language="bash")

# ---------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------
tab_datos, tab_pred, tab_comp, tab_arduino = st.tabs([
    "📊 Datos históricos",
    "🔮 Predicción por localidad",
    "📍 Comparativa de localidades",
    "🔌 Modo Arduino",
])

# ===========================
# TAB 1 — Datos históricos
# ===========================
with tab_datos:
    if not os.path.exists(DATA_PATH):
        st.warning("No se encontró data.csv. Ejecuta generate_dataset.py primero.")
        st.stop()

    df = cargar_datos()
    tiene_localidades = "localidad_id" in df.columns

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Registros totales", f"{len(df):,}")
    col2.metric("Temp. promedio global", f"{df['temperatura'].mean():.1f} °C")
    col3.metric("Humedad promedio", f"{df['humedad'].mean():.0f} %")
    if tiene_localidades:
        col4.metric("Localidades", f"{df['localidad_id'].nunique()}")
    else:
        col4.metric("Días cubiertos",
                    f"{(df['timestamp'].max() - df['timestamp'].min()).days}")

    # Filtro de localidad para vista histórica
    if tiene_localidades:
        loc_sel_hist = st.selectbox(
            "Filtrar por localidad",
            options=_NOMBRES_ORD,
            index=_NOMBRES_ORD.index("Teusaquillo"),
            key="hist_loc",
        )
        lid_hist = _NOMBRE_A_ID[loc_sel_hist]
        df_loc   = df[df["localidad_id"] == lid_hist]
        loc_info = LOCALIDADES[lid_hist]
        st.caption(
            f"📍 **{loc_sel_hist}** — "
            f"Altitud: {loc_info['altitud']} m  |  "
            f"Densidad urbana: {loc_info['densidad_urbana']:.0%}  |  "
            f"Zona: {loc_info['zona']}"
        )
    else:
        df_loc = df

    st.subheader("Últimas lecturas")
    cols_show = [c for c in ["timestamp", "localidad", "temperatura", "humedad", "luz", "ruido"]
                 if c in df_loc.columns]
    st.dataframe(df_loc.tail(12)[cols_show], use_container_width=True)

    st.subheader("Temperatura — últimas 24 horas")
    ultimas = df_loc.tail(144)
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(ultimas["timestamp"], ultimas["temperatura"], color="#e05c2a", linewidth=1.2)
    ax.set_xlabel("Hora")
    ax.set_ylabel("°C")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    st.pyplot(fig)

    st.subheader("Temperatura vs Humedad (muestra 500 puntos)")
    muestra = df_loc.sample(min(500, len(df_loc))).sort_values("timestamp")
    fig2, ax2 = plt.subplots(figsize=(10, 3))
    ax2b = ax2.twinx()
    ax2.plot(muestra["timestamp"],  muestra["temperatura"], color="#e05c2a", alpha=0.7, label="Temperatura")
    ax2b.plot(muestra["timestamp"], muestra["humedad"],     color="#2a7be0", alpha=0.5, label="Humedad")
    ax2.set_ylabel("°C",  color="#e05c2a")
    ax2b.set_ylabel("%", color="#2a7be0")
    ax2.grid(True, alpha=0.2)
    fig2.tight_layout()
    st.pyplot(fig2)

# ===========================
# TAB 2 — Predicción por localidad
# ===========================
with tab_pred:
    if not os.path.exists(MODEL_PATH):
        st.warning("Modelo no encontrado. Ejecuta train_model.py primero.")
        st.stop()

    model = cargar_modelo()

    st.markdown("Selecciona una localidad e ingresa los valores del sensor para predecir la temperatura en **30 minutos**.")

    # Selector de localidad — ocupa toda la fila superior
    loc_sel = st.selectbox(
        "📍 Localidad de Bogotá",
        options=_NOMBRES_ORD,
        index=_NOMBRES_ORD.index("Teusaquillo"),
        key="pred_loc",
    )
    lid    = _NOMBRE_A_ID[loc_sel]
    loc_info = LOCALIDADES[lid]

    # Tarjeta de info de la localidad seleccionada
    mi1, mi2, mi3, mi4 = st.columns(4)
    mi1.metric("Altitud", f"{loc_info['altitud']} m")
    mi2.metric("Densidad urbana", f"{loc_info['densidad_urbana']:.0%}")
    mi3.metric("Latitud",  f"{loc_info['lat']:.4f}°")
    mi4.metric("Longitud", f"{loc_info['lon']:.4f}°")

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        temp    = st.number_input("🌡️ Temperatura actual (°C)", min_value=-5.0, max_value=30.0, value=13.5, step=0.1)
        humedad = st.number_input("💧 Humedad (%)", min_value=30.0, max_value=100.0, value=72.0, step=0.5)
        luz     = st.number_input("☀️ Luz (lux)", min_value=0.0, max_value=1100.0, value=600.0, step=10.0)
    with c2:
        ruido   = st.number_input("🔊 Ruido (dB)", min_value=20.0, max_value=110.0, value=45.0, step=1.0)
        hora    = st.slider("🕐 Hora del día", 0, 23, datetime.now().hour)
        mes     = st.slider("📅 Mes", 1, 12, datetime.now().month)

    if "historia" not in st.session_state:
        st.session_state.historia = pd.DataFrame(columns=["temperatura", "humedad"])

    if st.button("🔮 Predecir temperatura T+30 min", type="primary"):
        historia = st.session_state.historia if len(st.session_state.historia) > 0 else None
        X = features_from_raw(
            temperatura     = temp,
            humedad         = humedad,
            luz             = luz,
            ruido           = ruido,
            hora            = hora,
            mes             = mes,
            historia        = historia,
            altitud         = loc_info["altitud"],
            latitud         = loc_info["lat"],
            longitud        = loc_info["lon"],
            densidad_urbana = loc_info["densidad_urbana"],
        )
        pred  = float(model.predict(X)[0])
        delta = pred - temp

        st.success(f"🌡️ Temperatura estimada en **{loc_sel}** en 30 min: **{pred:.2f} °C**")
        st.metric("Cambio esperado", f"{delta:+.2f} °C", delta=round(delta, 2))

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
# TAB 3 — Comparativa de localidades
# ===========================
with tab_comp:
    if not os.path.exists(DATA_PATH):
        st.warning("No se encontró data.csv.")
        st.stop()

    df = cargar_datos()
    if "localidad_id" not in df.columns:
        st.info("El dataset actual no tiene columna de localidad. Regenera el dataset con generate_dataset.py.")
        st.stop()

    st.markdown("Comparación de temperatura y humedad media entre localidades.")

    # Estadísticas por localidad
    resumen = (
        df.groupby(["localidad_id", "localidad"])
        .agg(
            temp_media  = ("temperatura", "mean"),
            temp_min    = ("temperatura", "min"),
            temp_max    = ("temperatura", "max"),
            humedad_med = ("humedad",     "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values("temp_media")
    )

    # Enriquecer con altitud
    resumen["altitud"] = resumen["localidad_id"].map(
        lambda i: LOCALIDADES[i]["altitud"]
    )
    resumen["zona"] = resumen["localidad_id"].map(
        lambda i: LOCALIDADES[i]["zona"]
    )

    st.subheader("Temperatura media por localidad")
    fig3, ax3 = plt.subplots(figsize=(12, 5))
    bars = ax3.barh(
        resumen["localidad"],
        resumen["temp_media"],
        color=plt.cm.RdYlBu_r(
            (resumen["temp_media"] - resumen["temp_media"].min())
            / (resumen["temp_media"].max() - resumen["temp_media"].min())
        ),
    )
    ax3.set_xlabel("°C")
    ax3.set_title("Temperatura media — cada barra representa una localidad")
    ax3.grid(axis="x", alpha=0.3)
    fig3.tight_layout()
    st.pyplot(fig3)

    st.subheader("Temperatura media vs Altitud")
    fig4, ax4 = plt.subplots(figsize=(9, 4))
    sc = ax4.scatter(
        resumen["altitud"],
        resumen["temp_media"],
        c=resumen["humedad_med"],
        cmap="Blues",
        s=80,
        edgecolors="gray",
        linewidth=0.5,
    )
    for _, row in resumen.iterrows():
        ax4.annotate(
            row["localidad"],
            (row["altitud"], row["temp_media"]),
            textcoords="offset points",
            xytext=(4, 2),
            fontsize=6.5,
        )
    plt.colorbar(sc, ax=ax4, label="Humedad media (%)")
    ax4.set_xlabel("Altitud (m)")
    ax4.set_ylabel("Temperatura media (°C)")
    ax4.grid(True, alpha=0.3)
    fig4.tight_layout()
    st.pyplot(fig4)

    st.subheader("Tabla de estadísticas por localidad")
    st.dataframe(
        resumen[["localidad", "zona", "altitud", "temp_min", "temp_media", "temp_max", "humedad_med"]]
        .rename(columns={
            "localidad":   "Localidad",
            "zona":        "Zona",
            "altitud":     "Altitud (m)",
            "temp_min":    "Temp. mín °C",
            "temp_media":  "Temp. media °C",
            "temp_max":    "Temp. máx °C",
            "humedad_med": "Humedad media %",
        }),
        use_container_width=True,
        hide_index=True,
    )

# ===========================
# TAB 4 — Modo Arduino
# ===========================
with tab_arduino:
    st.markdown("""
    ### Integración con Arduino

    El módulo `arduino_collector.py` recibe datos del sensor en tiempo real.
    Ahora puedes especificar la **localidad** donde está instalado el Arduino.

    #### Formato Serial (Arduino → PC)
    ```
    18.50,72.30,850,45
    ```
    `temperatura(°C), humedad(%), luz(lux), ruido(dB)`

    #### Comandos
    | Acción | Comando |
    |--------|---------|
    | Colectar datos (Arduino real) | `python src/arduino_collector.py --port COM3` |
    | Colectar + predecir (con localidad) | `python src/arduino_collector.py --port COM3 --predict --localidad 8` |
    | Probar sin hardware | `python src/arduino_collector.py --simulate --predict --localidad 13` |
    | Re-generar dataset multi-localidad | `python src/generate_dataset.py` |
    | Re-entrenar modelo | `python src/train_model.py` |

    #### IDs de localidad para el parámetro `--localidad`
    """)

    # Tabla de localidades
    loc_tabla = pd.DataFrame([
        {"ID": lid, "Localidad": info["nombre"], "Altitud (m)": info["altitud"],
         "Zona": info["zona"], "Densidad": f"{info['densidad_urbana']:.0%}"}
        for lid, info in sorted(LOCALIDADES.items())
    ])
    st.dataframe(loc_tabla, use_container_width=True, hide_index=True)

    st.markdown("""
    #### Sensores recomendados
    | Sensor | Variable medida | Pines sugeridos |
    |--------|-----------------|-----------------|
    | DHT22  | Temperatura + Humedad | D2 |
    | LDR + R10kΩ | Luz (lux) | A0 |
    | KY-038 | Ruido (dB) | A1 |
    """)

    if os.path.exists(DATA_PATH):
        df_check = load_data(DATA_PATH)
        ultima = df_check["timestamp"].max()
        hace   = (datetime.now() - ultima.to_pydatetime()).seconds // 60
        if hace < 30:
            st.success(f"✅ Última lectura hace {hace} minutos — datos actualizados.")
        else:
            st.info(f"ℹ️  Última lectura hace {hace} minutos ({ultima.strftime('%Y-%m-%d %H:%M')}).")
