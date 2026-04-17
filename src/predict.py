import os
import joblib
import pandas as pd
from datetime import datetime

from feature_engineering import features_from_raw, FEATURE_COLS

# Ruta absoluta al modelo (funciona desde cualquier directorio)
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
) -> float:
    """
    Predice la temperatura 30 minutos hacia adelante.

    Parámetros
    ----------
    temperatura : °C actual del sensor
    humedad     : % HR actual del sensor
    luz         : lux actual del sensor
    ruido       : dB actual del sensor
    hora        : hora del día (0-23); si None usa hora actual del sistema
    mes         : mes (1-12); si None usa mes actual del sistema
    historia    : DataFrame con lecturas recientes para calcular promedios
                  reales (columnas: temperatura, humedad)

    Retorna
    -------
    float : temperatura estimada en °C para t+30 min
    """
    now = datetime.now()
    if hora is None:
        hora = now.hour
    if mes is None:
        mes = now.month

    X = features_from_raw(temperatura, humedad, luz, ruido, hora, mes, historia)
    return float(_load_model().predict(X)[0])
