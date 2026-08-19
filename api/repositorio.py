"""Acceso a los artefactos en disco: dataset, modelo, métricas y lectura viva.

Todas las lecturas se memorizan usando la fecha de modificación del archivo
como clave, para no releer 259 000 filas de CSV en cada petición HTTP.
"""

import json
import os
import threading
import time
from datetime import datetime

from api import config

config.registrar_src_en_path()

import joblib  # noqa: E402  (requiere src/ en sys.path)
import pandas as pd  # noqa: E402

from data_processing import clean_data, load_data  # noqa: E402

_lock = threading.Lock()
_cache_dataset: dict = {"mtime": None, "df": None, "verificado_en": 0.0}
_cache_modelo: dict = {"mtime": None, "modelo": None}


def _mtime(path: str):
    """Fecha de modificación del archivo, o None si no existe."""
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def hay_dataset() -> bool:
    return os.path.exists(config.DATA_PATH)


def hay_modelo() -> bool:
    return os.path.exists(config.MODEL_PATH)


def cargar_dataset() -> pd.DataFrame:
    """Devuelve el dataset limpio, releyéndolo solo si el CSV cambió.

    Entre comprobaciones se respeta un TTL para que las escrituras continuas
    del colector no obliguen a releer el CSV completo en cada petición.
    """
    with _lock:
        ahora = time.monotonic()
        vigente = ahora - _cache_dataset["verificado_en"] < config.TTL_DATASET_S
        if _cache_dataset["df"] is not None and vigente:
            return _cache_dataset["df"]

        mtime = _mtime(config.DATA_PATH)
        if mtime is None:
            raise FileNotFoundError("No se encontró data/raw/data.csv")

        if _cache_dataset["mtime"] != mtime:
            _cache_dataset["df"] = clean_data(load_data(config.DATA_PATH))
            _cache_dataset["mtime"] = mtime
        _cache_dataset["verificado_en"] = ahora
        return _cache_dataset["df"]


def cargar_modelo():
    """Devuelve el modelo entrenado, recargándolo si el .pkl cambió."""
    mtime = _mtime(config.MODEL_PATH)
    if mtime is None:
        raise FileNotFoundError("No se encontró models/model.pkl")

    with _lock:
        if _cache_modelo["mtime"] != mtime:
            _cache_modelo["modelo"] = joblib.load(config.MODEL_PATH)
            _cache_modelo["mtime"] = mtime
        return _cache_modelo["modelo"]


def cargar_metricas():
    """Métricas de validación cruzada del modelo, o None si aún no se entrenó."""
    return _leer_json(config.METRICS_PATH)


def leer_live():
    """Última lectura publicada por el colector, o None si no existe."""
    return _leer_json(config.LIVE_PATH)


def _leer_json(path: str):
    """Lee un JSON tolerando ausencia o contenido corrupto."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as archivo:
            return json.load(archivo)
    except (OSError, ValueError):
        return None


def segundos_desde(ts_str: str) -> int:
    """Antigüedad en segundos de una marca de tiempo del colector."""
    ts = datetime.strptime(ts_str, config.FORMATO_TS)
    return int((datetime.now() - ts).total_seconds())
