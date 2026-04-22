import os
import joblib
import pandas as pd
from datetime import datetime

from feature_engineering import features_from_raw, FEATURE_COLS
from localidades import LOCALIDADES

_base_dir   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_model_path = os.path.join(_base_dir, "models", "model.pkl")

_model = None


def _load_model():
    global _model
    if _model is None:
        _model = joblib.load(_model_path)
    return _model


def predict(
    temperatura: float,
    humedad: float,
    luz: float,
    ruido: float,
    hora: int = None,
    mes: int = None,
    historia: pd.DataFrame = None,
    localidad_id: int = 13,  # Teusaquillo — sede de despliegue universitario
) -> float:
    """
    Predice la temperatura 30 minutos hacia adelante para una localidad de Bogotá.

    Parámetros
    ----------
    temperatura  : °C actual del sensor
    humedad      : % HR actual del sensor
    luz          : lux actual del sensor
    ruido        : dB actual del sensor
    hora         : hora del día (0-23); None → hora actual del sistema
    mes          : mes (1-12); None → mes actual del sistema
    historia     : DataFrame con lecturas recientes (columnas: temperatura, humedad)
    localidad_id : ID de la localidad 1-20 (defecto: 17 = La Candelaria)

    Retorna
    -------
    float : temperatura estimada en °C para t+30 min
    """
    now = datetime.now()
    if hora is None:
        hora = now.hour
    if mes is None:
        mes = now.month

    loc = LOCALIDADES.get(localidad_id, LOCALIDADES[13])

    X = features_from_raw(
        temperatura     = temperatura,
        humedad         = humedad,
        luz             = luz,
        ruido           = ruido,
        hora            = hora,
        mes             = mes,
        historia        = historia,
        altitud         = loc["altitud"],
        latitud         = loc["lat"],
        longitud        = loc["lon"],
        densidad_urbana = loc["densidad_urbana"],
    )
    return float(_load_model().predict(X)[0])
