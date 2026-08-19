"""Lógica de negocio del panel: agregaciones del dataset y predicciones.

Cada función devuelve estructuras JSON-serializables listas para la API.
"""

from datetime import datetime

import pandas as pd

from api import config, repositorio

config.registrar_src_en_path()

from feature_engineering import features_from_raw  # noqa: E402
from localidades import LOCALIDADES  # noqa: E402

COLUMNAS_TABLA = ["timestamp", "localidad", "temperatura", "humedad", "luz", "ruido"]

# Horas en las que la luz de interior se escala al rango exterior del modelo.
HORA_DIA_INICIO = 6
HORA_DIA_FIN = 18
FACTOR_LUZ_INTERIOR = 3.5
LUZ_MAXIMA = 1000.0


class SolicitudInvalida(ValueError):
    """Datos de entrada rechazados por la API (se traduce a HTTP 400)."""


def escalar_luz_interior(luz: float, hora: int) -> float:
    """Convierte lux de entorno cerrado al rango exterior que espera el modelo.

    Solo escala durante horas diurnas; de noche los valores ya coinciden.
    """
    if HORA_DIA_INICIO <= hora <= HORA_DIA_FIN:
        return min(LUZ_MAXIMA, luz * FACTOR_LUZ_INTERIOR)
    return luz


def listar_localidades() -> list[dict]:
    """Catálogo de las 20 localidades ordenado por identificador."""
    return [
        {
            "id": lid,
            "nombre": info["nombre"],
            "lat": info["lat"],
            "lon": info["lon"],
            "altitud": info["altitud"],
            "densidad_urbana": info["densidad_urbana"],
            "zona": info["zona"],
        }
        for lid, info in sorted(LOCALIDADES.items())
    ]


def obtener_localidad(localidad_id) -> dict:
    """Devuelve la localidad pedida o lanza SolicitudInvalida si no existe."""
    if localidad_id is None:
        return LOCALIDADES[config.LOCALIDAD_DEFECTO]
    info = LOCALIDADES.get(localidad_id)
    if info is None:
        raise SolicitudInvalida("Localidad fuera del rango 1-20")
    return info


def metricas_modelo() -> dict:
    """Métricas del modelo y disponibilidad de los artefactos en disco."""
    return {
        "metricas": repositorio.cargar_metricas(),
        "hay_modelo": repositorio.hay_modelo(),
        "hay_dataset": repositorio.hay_dataset(),
    }


def _filtrar_localidad(df: pd.DataFrame, localidad_id):
    """Subconjunto del dataset para una localidad; el dataset completo si no aplica."""
    if localidad_id is None or "localidad_id" not in df.columns:
        return df
    return df[df["localidad_id"] == localidad_id]


def _fila_a_lectura(fila) -> dict:
    """Convierte una fila del dataset en el contrato de lectura de la API."""
    return {
        "timestamp": fila["timestamp"].strftime(config.FORMATO_TS),
        "temperatura": round(float(fila["temperatura"]), 2),
        "humedad": round(float(fila["humedad"]), 1),
        "luz": round(float(fila["luz"]), 0),
        "ruido": round(float(fila["ruido"]), 0),
    }


def resumen_dataset(localidad_id=None) -> dict:
    """Totales globales y de la localidad seleccionada."""
    df = repositorio.cargar_dataset()
    tiene_localidades = "localidad_id" in df.columns
    dias = (df["timestamp"].max() - df["timestamp"].min()).days

    df_loc = _filtrar_localidad(df, localidad_id)

    return {
        "registros": int(len(df)),
        "temp_media": round(float(df["temperatura"].mean()), 1),
        "humedad_media": round(float(df["humedad"].mean()), 0),
        "dias": int(dias),
        "localidades": int(df["localidad_id"].nunique()) if tiene_localidades else None,
        "tiene_localidades": tiene_localidades,
        "registros_localidad": int(len(df_loc)),
    }


def serie_temporal(localidad_id=None, limite: int = 144) -> dict:
    """Últimos puntos de temperatura y humedad de una localidad, para graficar."""
    df_loc = _filtrar_localidad(repositorio.cargar_dataset(), localidad_id).tail(limite)
    return {"puntos": [_fila_a_lectura(fila) for _, fila in df_loc.iterrows()]}


def ultimas_lecturas(localidad_id=None, cantidad: int = 12) -> dict:
    """Tabla de las lecturas más recientes, de la más nueva a la más antigua."""
    df_loc = _filtrar_localidad(repositorio.cargar_dataset(), localidad_id).tail(cantidad)
    columnas = [c for c in COLUMNAS_TABLA if c in df_loc.columns]

    filas = [
        {columna: _celda(fila, columna) for columna in columnas}
        for _, fila in df_loc.iloc[::-1].iterrows()
    ]
    return {"columnas": columnas, "filas": filas}


def _celda(fila, columna: str):
    """Normaliza el valor de una celda del dataset para enviarlo como JSON."""
    valor = fila[columna]
    if columna == "timestamp":
        return valor.strftime(config.FORMATO_TS)
    if columna == "localidad":
        return str(valor)
    return round(float(valor), 2)


def _historia_localidad(df: pd.DataFrame, localidad_id, ventana: int = 20):
    """Últimas lecturas de temperatura/humedad usadas por los promedios móviles."""
    df_loc = _filtrar_localidad(df, localidad_id)
    if df_loc.empty:
        return None
    return df_loc[["temperatura", "humedad"]].tail(ventana)


def _predecir_con_modelo(lectura: dict, loc_info: dict, historia) -> float:
    """Ejecuta el modelo sobre una lectura cruda y devuelve la temperatura T+30."""
    X = features_from_raw(
        temperatura=lectura["temperatura"],
        humedad=lectura["humedad"],
        luz=lectura["luz"],
        ruido=lectura["ruido"],
        hora=lectura["hora"],
        mes=lectura["mes"],
        historia=historia,
        altitud=loc_info["altitud"],
        latitud=loc_info["lat"],
        longitud=loc_info["lon"],
        densidad_urbana=loc_info["densidad_urbana"],
    )
    return float(repositorio.cargar_modelo().predict(X)[0])


def estado_live(localidad_id=None) -> dict:
    """Estado del archivo latest.json: contenido, antigüedad y vigencia."""
    live = repositorio.leer_live()
    if live is None:
        return {"disponible": False, "lectura": None, "antiguedad_s": None, "vigente": False}

    antiguedad = repositorio.segundos_desde(live["timestamp"])
    misma_localidad = localidad_id is None or live.get("localidad_id") == localidad_id
    return {
        "disponible": True,
        "lectura": live,
        "antiguedad_s": antiguedad,
        "vigente": antiguedad < config.FRESCURA_LIVE_S and misma_localidad,
    }


def lectura_actual(localidad_id=None, entorno_interior: bool = False) -> dict:
    """Lectura vigente (Arduino si está fresca, si no la última del dataset).

    Incluye la predicción a 30 minutos cuando el modelo está disponible.
    """
    loc_id = localidad_id if localidad_id is not None else config.LOCALIDAD_DEFECTO
    loc_info = obtener_localidad(loc_id)
    live = estado_live(loc_id)

    if live["vigente"]:
        origen = "arduino"
        actual = _lectura_desde_live(live["lectura"])
        prediccion = live["lectura"].get("prediccion")
    else:
        origen = "dataset"
        actual = _ultima_del_dataset(loc_id)
        prediccion = None

    if actual is None:
        return {"origen": "sin_datos", "localidad_id": loc_id, "lectura": None, "prediccion": None}

    ts = datetime.strptime(actual["timestamp"], config.FORMATO_TS)
    luz_modelo = escalar_luz_interior(actual["luz"], ts.hour) if entorno_interior else actual["luz"]

    if (prediccion is None or entorno_interior) and repositorio.hay_modelo():
        entrada = dict(actual, luz=luz_modelo, hora=ts.hour, mes=ts.month)
        historia = _historia_dataset(loc_id)
        prediccion = _predecir_con_modelo(entrada, loc_info, historia)

    return {
        "origen": origen,
        "localidad_id": loc_id,
        "localidad": loc_info["nombre"],
        "lectura": actual,
        "luz_modelo": round(luz_modelo, 0),
        "prediccion": round(prediccion, 2) if prediccion is not None else None,
        "delta": round(prediccion - actual["temperatura"], 2) if prediccion is not None else None,
        "antiguedad_min": int((datetime.now() - ts).total_seconds() // 60),
    }


def _lectura_desde_live(live: dict) -> dict:
    """Normaliza la lectura de latest.json al contrato de lectura de la API."""
    return {
        "timestamp": live["timestamp"],
        "temperatura": float(live["temperatura"]),
        "humedad": float(live["humedad"]),
        "luz": float(live["luz"]),
        "ruido": float(live["ruido"]),
    }


def _historia_dataset(localidad_id):
    """Historial de la localidad tomado del dataset, si el CSV existe."""
    if not repositorio.hay_dataset():
        return None
    return _historia_localidad(repositorio.cargar_dataset(), localidad_id)


def _ultima_del_dataset(localidad_id):
    """Última fila registrada para la localidad, o None si no hay datos."""
    if not repositorio.hay_dataset():
        return None
    df_loc = _filtrar_localidad(repositorio.cargar_dataset(), localidad_id)
    if df_loc.empty:
        return None
    return _fila_a_lectura(df_loc.iloc[-1])


def comparativa() -> dict:
    """Estadísticas de temperatura y humedad agregadas por localidad."""
    df = repositorio.cargar_dataset()
    if "localidad_id" not in df.columns:
        return {"disponible": False, "filas": []}

    resumen = (
        df.groupby(["localidad_id", "localidad"])
        .agg(
            temp_media=("temperatura", "mean"),
            temp_min=("temperatura", "min"),
            temp_max=("temperatura", "max"),
            humedad_med=("humedad", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values("temp_media")
    )

    filas = []
    for _, fila in resumen.iterrows():
        info = LOCALIDADES[int(fila["localidad_id"])]
        filas.append({
            "localidad_id": int(fila["localidad_id"]),
            "localidad": str(fila["localidad"]),
            "zona": info["zona"],
            "altitud": info["altitud"],
            "temp_min": float(fila["temp_min"]),
            "temp_media": float(fila["temp_media"]),
            "temp_max": float(fila["temp_max"]),
            "humedad_med": float(fila["humedad_med"]),
        })

    return {"disponible": True, "filas": filas}


def _historia_desde_payload(historia):
    """Convierte el historial enviado por el front en el DataFrame que espera el modelo."""
    if not historia:
        return None
    filas = [
        {"temperatura": float(item["temperatura"]), "humedad": float(item["humedad"])}
        for item in historia
        if isinstance(item, dict) and "temperatura" in item and "humedad" in item
    ]
    return pd.DataFrame(filas) if filas else None


def predecir(datos: dict) -> dict:
    """Predice la temperatura a 30 minutos a partir de valores crudos del sensor."""
    if not repositorio.hay_modelo():
        raise SolicitudInvalida("Modelo no disponible. Ejecuta train_model.py primero.")

    ahora = datetime.now()
    temperatura = _numero(datos, "temperatura", -5.0, 30.0)
    humedad = _numero(datos, "humedad", 30.0, 100.0)
    luz = _numero(datos, "luz", 0.0, 1100.0)
    ruido = _numero(datos, "ruido", 20.0, 110.0)
    hora = int(_numero(datos, "hora", 0, 23, ahora.hour))
    mes = int(_numero(datos, "mes", 1, 12, ahora.month))

    loc_id = datos.get("localidad_id", config.LOCALIDAD_DEFECTO)
    loc_info = obtener_localidad(loc_id)

    entorno_interior = bool(datos.get("entorno_interior", False))
    luz_modelo = escalar_luz_interior(luz, hora) if entorno_interior else luz

    historia = _historia_desde_payload(datos.get("historia"))
    if historia is None and datos.get("usar_historial_dataset"):
        historia = _historia_dataset(loc_id)

    lectura = {
        "temperatura": temperatura,
        "humedad": humedad,
        "luz": luz_modelo,
        "ruido": ruido,
        "hora": hora,
        "mes": mes,
    }
    prediccion = _predecir_con_modelo(lectura, loc_info, historia)

    return {
        "localidad_id": loc_id,
        "localidad": loc_info["nombre"],
        "temperatura_actual": temperatura,
        "luz_modelo": round(luz_modelo, 0),
        "prediccion": round(prediccion, 2),
        "delta": round(prediccion - temperatura, 2),
    }


def _numero(datos: dict, clave: str, minimo: float, maximo: float, defecto=None) -> float:
    """Valida que la clave sea numérica y esté dentro del rango permitido."""
    valor = datos.get(clave, defecto)
    if valor is None:
        raise SolicitudInvalida("Falta el campo " + clave)
    try:
        numero = float(valor)
    except (TypeError, ValueError) as error:
        raise SolicitudInvalida("El campo " + clave + " debe ser numérico") from error
    if numero < minimo or numero > maximo:
        raise SolicitudInvalida(f"{clave} debe estar entre {minimo} y {maximo}")
    return numero


def dataset_csv() -> bytes:
    """Dataset limpio serializado en CSV para descarga."""
    return repositorio.cargar_dataset().to_csv(index=False).encode("utf-8")
