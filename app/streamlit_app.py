import subprocess
import sys
import os
import json
from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib
from streamlit_autorefresh import st_autorefresh

_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_base_dir, "src"))

from feature_engineering import features_from_raw, FEATURE_COLS
from data_processing import load_data, clean_data
from localidades import LOCALIDADES

DATA_PATH    = os.path.join(_base_dir, "data", "raw", "data.csv")
MODEL_PATH   = os.path.join(_base_dir, "models", "model.pkl")
METRICS_PATH = os.path.join(_base_dir, "models", "metrics.json")
LIVE_PATH    = os.path.join(_base_dir, "data", "live", "latest.json")

_NOMBRE_A_ID = {v["nombre"]: k for k, v in LOCALIDADES.items()}
_NOMBRES_ORD = [LOCALIDADES[i]["nombre"] for i in sorted(LOCALIDADES)]


@st.cache_data(ttl=10)
def cargar_datos():
    df = load_data(DATA_PATH)
    return clean_data(df)


@st.cache_resource
def cargar_modelo():
    return joblib.load(MODEL_PATH)


def leer_live() -> dict | None:
    """Devuelve el JSON de última lectura o None si no existe / está corrupto."""
    if not os.path.exists(LIVE_PATH):
        return None
    try:
        with open(LIVE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def segundos_desde(ts_str: str) -> int:
    ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    return int((datetime.now() - ts).total_seconds())


# ---------------------------------------------------------------
# Config página
# ---------------------------------------------------------------
st.set_page_config(
    page_title="Microclima Bogotá — Localidades",
    page_icon="🌫️",
    layout="wide",
)
st.title("🌫️ Microclima Bogotá D.C. — Predicción por Localidad")

st_autorefresh(interval=5000, key="refresh")

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
    live = leer_live()
    if live:
        hace_s = segundos_desde(live["timestamp"])
        color  = "🟢" if hace_s < 15 else ("🟡" if hace_s < 60 else "🔴")
        st.caption(f"{color} Arduino: {live['localidad']} · hace {hace_s}s")

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
    "🔌 Arduino en vivo",
])

# ===========================
# TAB 1 — Datos históricos
# ===========================
with tab_datos:
    if not os.path.exists(DATA_PATH):
        st.warning("No se encontró data.csv. Ejecuta generate_dataset.py primero.")
    else:
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

        if tiene_localidades:
            loc_sel_hist = st.selectbox(
                "Filtrar por localidad",
                options=_NOMBRES_ORD,
                index=_NOMBRES_ORD.index("Teusaquillo"),
                key="hist_loc",
            )
            lid_hist  = _NOMBRE_A_ID[loc_sel_hist]
            df_loc    = df[df["localidad_id"] == lid_hist]
            loc_info  = LOCALIDADES[lid_hist]
            st.caption(
                f"📍 **{loc_sel_hist}** — "
                f"Altitud: {loc_info['altitud']} m  |  "
                f"Densidad urbana: {loc_info['densidad_urbana']:.0%}  |  "
                f"Zona: {loc_info['zona']}"
            )
        else:
            df_loc   = df
            loc_info = None
            lid_hist = None

        if df_loc.empty:
            st.warning("No hay datos para esta localidad aún.")
        else:
            # ── Lectura en tiempo real ──────────────────────────────
            st.subheader("📡 Lectura en tiempo real")

            # Preferir latest.json si corresponde a la misma localidad y es reciente
            live = leer_live()
            usar_live = (
                live is not None
                and segundos_desde(live["timestamp"]) < 60
                and (lid_hist is None or live.get("localidad_id") == lid_hist)
            )

            if usar_live:
                t_val, h_val, l_val, r_val = (
                    live["temperatura"], live["humedad"],
                    live["luz"], live["ruido"]
                )
                pred_live = live.get("prediccion")
                st.success(f"🟢 Datos en vivo — Arduino ({live['localidad']})")
            else:
                ultima = df_loc.iloc[-1]
                t_val  = ultima["temperatura"]
                h_val  = ultima["humedad"]
                l_val  = ultima["luz"]
                r_val  = ultima["ruido"]
                pred_live = None

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🌡️ Temp",    f"{t_val:.2f} °C")
            c2.metric("💧 Humedad", f"{h_val:.1f} %")
            c3.metric("☀️ Luz",     f"{l_val:.0f}")
            c4.metric("🔊 Ruido",   f"{r_val:.0f}")

            # ── Predicción en vivo ──────────────────────────────────
            if pred_live is not None:
                delta = pred_live - t_val
                st.success(f"🔮 Predicción en 30 min: **{pred_live:.2f} °C**")
                st.metric("Cambio esperado", f"{delta:+.2f} °C")
            elif os.path.exists(MODEL_PATH):
                model   = cargar_modelo()
                historia = df_loc[["temperatura", "humedad"]].tail(20)
                ultima   = df_loc.iloc[-1]
                ts_row   = ultima["timestamp"]
                X = features_from_raw(
                    temperatura     = t_val,
                    humedad         = h_val,
                    luz             = l_val,
                    ruido           = r_val,
                    hora            = ts_row.hour,
                    mes             = ts_row.month,
                    historia        = historia,
                    altitud         = loc_info["altitud"],
                    latitud         = loc_info["lat"],
                    longitud        = loc_info["lon"],
                    densidad_urbana = loc_info["densidad_urbana"],
                )
                pred  = float(model.predict(X)[0])
                delta = pred - t_val
                st.success(f"🔮 Predicción en 30 min: **{pred:.2f} °C**")
                st.metric("Cambio esperado", f"{delta:+.2f} °C")

            # ── Tabla + gráficas ────────────────────────────────────
            st.subheader("Últimas lecturas")
            cols_show = [c for c in ["timestamp", "localidad", "temperatura", "humedad", "luz", "ruido"]
                         if c in df_loc.columns]
            st.dataframe(df_loc.tail(12)[cols_show], use_container_width=True)

            st.subheader("Temperatura — últimas 24 horas")
            ultimas = df_loc.tail(144)
            fig, ax = plt.subplots(figsize=(10, 3))
            ax.plot(ultimas["timestamp"], ultimas["temperatura"], linewidth=1.5)
            ax.set_title("Evolución de temperatura (últimas 24h)")
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

            # Estado del sistema
            ultima_ts = df_loc.iloc[-1]["timestamp"]
            minutos = (datetime.now() - ultima_ts.to_pydatetime()).seconds // 60
            if usar_live:
                pass  # ya mostramos status arriba
            elif minutos < 1:
                st.success("🟢 Datos en vivo")
            elif minutos < 10:
                st.warning(f"🟡 Última lectura hace {minutos} min")
            else:
                st.error(f"🔴 Sin datos recientes ({minutos} min)")

# ===========================
# TAB 2 — Predicción por localidad
# ===========================
with tab_pred:
    if not os.path.exists(MODEL_PATH):
        st.warning("Modelo no encontrado. Ejecuta train_model.py primero.")
    else:
        model = cargar_modelo()

        st.markdown("Selecciona una localidad e ingresa los valores del sensor para predecir la temperatura en **30 minutos**.")

        loc_sel = st.selectbox(
            "📍 Localidad de Bogotá",
            options=_NOMBRES_ORD,
            index=_NOMBRES_ORD.index("Teusaquillo"),
            key="pred_loc",
        )
        lid      = _NOMBRE_A_ID[loc_sel]
        loc_info = LOCALIDADES[lid]

        mi1, mi2, mi3, mi4 = st.columns(4)
        mi1.metric("Altitud",        f"{loc_info['altitud']} m")
        mi2.metric("Densidad urbana",f"{loc_info['densidad_urbana']:.0%}")
        mi3.metric("Latitud",        f"{loc_info['lat']:.4f}°")
        mi4.metric("Longitud",       f"{loc_info['lon']:.4f}°")

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            temp    = st.number_input("🌡️ Temperatura actual (°C)", min_value=-5.0, max_value=30.0, value=13.5, step=0.1)
            humedad = st.number_input("💧 Humedad (%)", min_value=30.0, max_value=100.0, value=72.0, step=0.5)
            luz     = st.number_input("☀️ Luz (lux)", min_value=0.0, max_value=1100.0, value=600.0, step=10.0)
        with c2:
            ruido = st.number_input("🔊 Ruido (dB)", min_value=20.0, max_value=110.0, value=45.0, step=1.0)
            hora  = st.slider("🕐 Hora del día", 0, 23, datetime.now().hour)
            mes   = st.slider("📅 Mes", 1, 12, datetime.now().month)

        if "historia" not in st.session_state:
            st.session_state.historia = pd.DataFrame(columns=["temperatura", "humedad"])
        if "pred_tab2" not in st.session_state:
            st.session_state.pred_tab2 = None

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
            st.session_state.pred_tab2 = {
                "pred": pred, "delta": delta, "loc": loc_sel, "temp": temp,
            }
            nueva = pd.DataFrame([{"temperatura": temp, "humedad": humedad}])
            st.session_state.historia = pd.concat(
                [st.session_state.historia, nueva], ignore_index=True
            ).tail(20)

        # Mostrar resultado FUERA del bloque del botón para que persista en cada rerun
        if st.session_state.pred_tab2:
            r = st.session_state.pred_tab2
            st.success(
                f"🌡️ Temperatura estimada en **{r['loc']}** en 30 min: **{r['pred']:.2f} °C**"
            )
            st.metric("Cambio esperado", f"{r['delta']:+.2f} °C", delta=round(r["delta"], 2))
            if st.button("Borrar resultado"):
                st.session_state.pred_tab2 = None
                st.rerun()

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
    else:
        df = cargar_datos()
        if "localidad_id" not in df.columns:
            st.info("El dataset actual no tiene columna de localidad. Regenera el dataset con generate_dataset.py.")
        else:
            st.markdown("Comparación de temperatura y humedad media entre localidades.")

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
            resumen["altitud"] = resumen["localidad_id"].map(lambda i: LOCALIDADES[i]["altitud"])
            resumen["zona"]    = resumen["localidad_id"].map(lambda i: LOCALIDADES[i]["zona"])

            st.subheader("Temperatura media por localidad")
            fig3, ax3 = plt.subplots(figsize=(12, 5))
            ax3.barh(
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
# TAB 4 — Arduino en vivo
# ===========================
with tab_arduino:

    # ── Panel de control ────────────────────────────────────────
    st.subheader("🎮 Control del colector")

    ca1, ca2, ca3 = st.columns(3)
    with ca1:
        ard_port = st.text_input("Puerto serial", value="COM3", key="ard_port")
    with ca2:
        ard_loc_nombre = st.selectbox(
            "Localidad del Arduino",
            _NOMBRES_ORD,
            index=_NOMBRES_ORD.index("Teusaquillo"),
            key="ard_loc",
        )
        ard_loc_id = _NOMBRE_A_ID[ard_loc_nombre]
    with ca3:
        ard_baud = st.selectbox("Baud rate", [9600, 115200], key="ard_baud")

    if "arduino_proc" not in st.session_state:
        st.session_state.arduino_proc = None

    proc = st.session_state.arduino_proc
    proc_running = proc is not None and proc.poll() is None

    cb1, cb2, cb3 = st.columns(3)
    _collector = os.path.join(_base_dir, "src", "arduino_collector.py")

    with cb1:
        if st.button("▶ Iniciar Arduino real", disabled=proc_running, use_container_width=True):
            cmd = [
                sys.executable, _collector,
                "--port", ard_port,
                "--baud", str(ard_baud),
                "--localidad", str(ard_loc_id),
                "--predict",
            ]
            st.session_state.arduino_proc = subprocess.Popen(cmd)
            st.rerun()

    with cb2:
        if st.button("🧪 Iniciar simulación", disabled=proc_running, use_container_width=True):
            cmd = [
                sys.executable, _collector,
                "--simulate",
                "--lecturas", "99999",
                "--intervalo", "3",
                "--localidad", str(ard_loc_id),
                "--predict",
            ]
            st.session_state.arduino_proc = subprocess.Popen(cmd)
            st.rerun()

    with cb3:
        if st.button("⏹ Detener", disabled=not proc_running, use_container_width=True):
            st.session_state.arduino_proc.terminate()
            st.session_state.arduino_proc = None
            st.rerun()

    if proc_running:
        st.success(f"🟢 Colector en ejecución (PID {proc.pid}) — localidad: **{ard_loc_nombre}**")
    elif proc is not None and proc.poll() is not None:
        st.error(f"🔴 El colector terminó (código {proc.poll()}). Revisa el puerto o reinicia.")
        st.session_state.arduino_proc = None
    else:
        st.info("🔌 Colector detenido. Inicia Arduino real o la simulación.")

    st.divider()

    # ── Datos en vivo (latest.json) ─────────────────────────────
    st.subheader("📡 Lectura en vivo")

    live = leer_live()
    if live:
        hace_s = segundos_desde(live["timestamp"])
        if hace_s < 15:
            st.success(f"🟢 Actualizado hace {hace_s} s")
        elif hace_s < 60:
            st.warning(f"🟡 Hace {hace_s} s — revisa el colector")
        else:
            st.error(f"🔴 Sin actualización desde hace {hace_s // 60} min")

        lv1, lv2, lv3, lv4 = st.columns(4)
        lv1.metric("🌡️ Temperatura", f"{live['temperatura']:.2f} °C")
        lv2.metric("💧 Humedad",     f"{live['humedad']:.1f} %")
        lv3.metric("☀️ Luz",         f"{live['luz']} lux")
        lv4.metric("🔊 Ruido",       f"{live['ruido']} dB")

        if live.get("prediccion") is not None:
            delta_p = live["prediccion"] - live["temperatura"]
            st.info(
                f"🔮 Predicción T+30 min: **{live['prediccion']:.2f} °C**  "
                f"({'↑' if delta_p >= 0 else '↓'} {abs(delta_p):.2f} °C)"
            )

        st.caption(
            f"📍 {live['localidad']} · {live['timestamp']}"
        )
    else:
        st.info("Sin datos en vivo todavía. Inicia el colector arriba.")

    st.divider()

    # ── Historial reciente (CSV) ─────────────────────────────────
    st.subheader("📈 Historial reciente del dataset")

    if not os.path.exists(DATA_PATH):
        st.info("No hay dataset aún. El colector lo generará automáticamente al recibir datos.")
    else:
        df_ard = cargar_datos()

        # Localidad a mostrar: la del live si existe, si no la seleccionada en el control
        filter_id = live["localidad_id"] if live else ard_loc_id
        filter_nombre = LOCALIDADES[filter_id]["nombre"]

        if "localidad_id" in df_ard.columns:
            df_reciente = df_ard[df_ard["localidad_id"] == filter_id].tail(120)
        else:
            df_reciente = df_ard.tail(120)

        if not df_reciente.empty:
            fig_r, ax_r = plt.subplots(figsize=(10, 3))
            ax_r2 = ax_r.twinx()
            ax_r.plot(df_reciente["timestamp"], df_reciente["temperatura"],
                      color="#e05c2a", linewidth=1.5, label="Temperatura")
            ax_r2.plot(df_reciente["timestamp"], df_reciente["humedad"],
                       color="#2a7be0", alpha=0.6, linewidth=1, label="Humedad")
            ax_r.set_ylabel("°C",  color="#e05c2a")
            ax_r2.set_ylabel("%", color="#2a7be0")
            ax_r.set_title(f"Últimas lecturas — {filter_nombre}")
            ax_r.grid(True, alpha=0.3)
            fig_r.tight_layout()
            st.pyplot(fig_r)

            cols_show = [c for c in ["timestamp", "localidad", "temperatura", "humedad", "luz", "ruido"]
                         if c in df_reciente.columns]
            st.dataframe(df_reciente.tail(10)[cols_show], use_container_width=True)
        else:
            st.info(f"No hay registros para {filter_nombre} aún.")

    st.divider()

    # ── Predicción manual desde Tab Arduino ─────────────────────
    st.subheader("🔮 Predicción manual")

    if not os.path.exists(MODEL_PATH):
        st.warning("Modelo no disponible. Ejecuta train_model.py primero.")
    else:
        # Pre-rellenar con valores del live si disponible
        _t_def  = float(live["temperatura"]) if live else 13.5
        _h_def  = float(live["humedad"])     if live else 72.0
        _l_def  = float(live["luz"])         if live else 600.0
        _r_def  = float(live["ruido"])       if live else 45.0
        _loc_pm = live["localidad_id"]       if live else ard_loc_id
        _loc_pm_nombre = LOCALIDADES[_loc_pm]["nombre"]

        if "pred_arduino" not in st.session_state:
            st.session_state.pred_arduino = None

        with st.form("pred_manual_arduino"):
            pm1, pm2 = st.columns(2)
            with pm1:
                pm_temp = st.number_input("🌡️ Temperatura (°C)", value=_t_def, min_value=-5.0, max_value=30.0, step=0.1)
                pm_hum  = st.number_input("💧 Humedad (%)", value=_h_def, min_value=30.0, max_value=100.0, step=0.5)
                pm_luz  = st.number_input("☀️ Luz (lux)", value=_l_def, min_value=0.0, max_value=1100.0, step=10.0)
            with pm2:
                pm_ruido = st.number_input("🔊 Ruido (dB)", value=_r_def, min_value=20.0, max_value=110.0, step=1.0)
                pm_hora  = st.slider("🕐 Hora", 0, 23, datetime.now().hour)
                pm_mes   = st.slider("📅 Mes",  1, 12, datetime.now().month)

            pm_loc_sel = st.selectbox(
                "📍 Localidad",
                _NOMBRES_ORD,
                index=_NOMBRES_ORD.index(_loc_pm_nombre),
                key="pm_loc",
            )
            submitted = st.form_submit_button("🔮 Predecir", type="primary")

        if submitted:
            pm_lid      = _NOMBRE_A_ID[pm_loc_sel]
            pm_loc_info = LOCALIDADES[pm_lid]
            pm_model    = cargar_modelo()

            _hist = None
            if os.path.exists(DATA_PATH):
                _df_h = cargar_datos()
                if "localidad_id" in _df_h.columns:
                    _hist = _df_h[_df_h["localidad_id"] == pm_lid][["temperatura", "humedad"]].tail(20)

            X_pm = features_from_raw(
                temperatura     = pm_temp,
                humedad         = pm_hum,
                luz             = pm_luz,
                ruido           = pm_ruido,
                hora            = pm_hora,
                mes             = pm_mes,
                historia        = _hist,
                altitud         = pm_loc_info["altitud"],
                latitud         = pm_loc_info["lat"],
                longitud        = pm_loc_info["lon"],
                densidad_urbana = pm_loc_info["densidad_urbana"],
            )
            pm_pred  = float(pm_model.predict(X_pm)[0])
            pm_delta = pm_pred - pm_temp
            st.session_state.pred_arduino = {
                "pred": pm_pred, "delta": pm_delta, "loc": pm_loc_sel,
            }

        # Mostrar resultado FUERA del bloque del form para que persista en cada rerun
        if st.session_state.pred_arduino:
            ra = st.session_state.pred_arduino
            st.success(
                f"🌡️ **{ra['loc']}** — Temperatura en 30 min: **{ra['pred']:.2f} °C** "
                f"({'↑' if ra['delta'] >= 0 else '↓'} {abs(ra['delta']):.2f} °C)"
            )

    st.divider()

    # ── Dataset completo ─────────────────────────────────────────
    st.subheader("📊 Dataset completo")

    if os.path.exists(DATA_PATH):
        df_dl = cargar_datos()
        ds1, ds2, ds3 = st.columns(3)
        ds1.metric("Total registros", f"{len(df_dl):,}")
        n_loc_ds = df_dl["localidad_id"].nunique() if "localidad_id" in df_dl.columns else "—"
        ds2.metric("Localidades", f"{n_loc_ds}")
        ds3.metric(
            "Rango de fechas",
            f"{(df_dl['timestamp'].max() - df_dl['timestamp'].min()).days} días",
        )
        csv_bytes = df_dl.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇ Descargar dataset (CSV)",
            data=csv_bytes,
            file_name="microclima_bogota.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("Dataset no disponible aún.")

    # ── Referencia de Arduino ────────────────────────────────────
    with st.expander("📖 Sketch de Arduino y conexión"):
        st.markdown("""
**Formato serial esperado** (una línea cada 10 s):
```
18.50,72.30,850,45
```
`temperatura(°C), humedad(%), luz(lux), ruido(dB)`

**Sensores recomendados**
| Sensor | Variable | Pin |
|--------|----------|-----|
| DHT22  | Temperatura + Humedad | D2 |
| LDR + R10kΩ | Luz | A0 |
| KY-038 | Ruido | A1 |
        """)
        st.code("""
#include <DHT.h>
#define DHTPIN 2
#define DHTTYPE DHT22
#define PIN_LUZ A0
#define PIN_RUIDO A1
DHT dht(DHTPIN, DHTTYPE);

void setup() {
    Serial.begin(9600);
    dht.begin();
}

void loop() {
    float temp = dht.readTemperature();
    float hum  = dht.readHumidity();
    int   luz  = map(analogRead(PIN_LUZ),   0, 1023, 0, 1000);
    int   ruido= map(analogRead(PIN_RUIDO), 0, 1023, 20, 110);
    if (isnan(temp) || isnan(hum)) { delay(2000); return; }
    Serial.print(temp, 2); Serial.print(",");
    Serial.print(hum, 1);  Serial.print(",");
    Serial.print(luz);     Serial.print(",");
    Serial.println(ruido);
    delay(10000);
}
        """, language="cpp")
