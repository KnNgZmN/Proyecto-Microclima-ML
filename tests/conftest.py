"""Fixtures compartidas por la suite de pruebas."""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def df_una_localidad() -> pd.DataFrame:
    """Seis lecturas consecutivas de una sola localidad (sin localidad_id)."""
    return pd.DataFrame({
        "timestamp":   pd.date_range("2025-03-10 00:00", periods=6, freq="10min"),
        "temperatura": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0],
        "humedad":     [70.0, 71.0, 72.0, 73.0, 74.0, 75.0],
        "luz":         [0, 0, 10, 20, 30, 40],
        "ruido":       [40, 41, 42, 43, 44, 45],
    })


@pytest.fixture
def df_dos_localidades() -> pd.DataFrame:
    """
    Lecturas intercaladas de dos localidades.

    El orden de filas es [loc1, loc2, loc1, loc2, loc1, loc2], que es
    exactamente el que produce generate_dataset.py al ordenar por
    (timestamp, localidad_id). Sirve para verificar que los promedios
    móviles no se contaminen entre localidades.
    """
    ts = pd.date_range("2025-03-10 00:00", periods=3, freq="10min")
    return pd.DataFrame({
        "timestamp":    [ts[0], ts[0], ts[1], ts[1], ts[2], ts[2]],
        "localidad_id": [1, 2, 1, 2, 1, 2],
        "temperatura":  [10.0, 20.0, 11.0, 21.0, 12.0, 22.0],
        "humedad":      [70.0, 80.0, 71.0, 81.0, 72.0, 82.0],
        "luz":          [0, 0, 10, 10, 20, 20],
        "ruido":        [40, 50, 41, 51, 42, 52],
    })


@pytest.fixture
def loc_info() -> dict:
    """Metadatos de localidad con la forma que consumen las funciones de src/."""
    return {
        "nombre": "Teusaquillo",
        "lat": 4.6321, "lon": -74.0871,
        "altitud": 2600, "densidad_urbana": 0.87,
        "zona": "centro",
    }


class ModeloFalso:
    """
    Doble de prueba del RandomForestRegressor entrenado.

    models/model.pkl está en .gitignore, por lo que no existe en CI; las
    pruebas nunca deben depender del artefacto real. Guarda la matriz de
    features recibida para poder hacer aserciones sobre ella.
    """

    def __init__(self, valor: float = 18.5):
        self.valor = valor
        self.X_recibido = None
        self.n_llamadas = 0

    def predict(self, X):
        self.X_recibido = X
        self.n_llamadas += 1
        return np.array([self.valor] * len(X))


@pytest.fixture
def modelo_falso() -> ModeloFalso:
    return ModeloFalso()
