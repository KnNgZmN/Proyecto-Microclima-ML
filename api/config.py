"""Rutas y constantes compartidas por el backend."""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
WEB_DIR = os.path.join(BASE_DIR, "web")

DATA_PATH = os.path.join(BASE_DIR, "data", "raw", "data.csv")
MODEL_PATH = os.path.join(BASE_DIR, "models", "model.pkl")
METRICS_PATH = os.path.join(BASE_DIR, "models", "metrics.json")
LIVE_PATH = os.path.join(BASE_DIR, "data", "live", "latest.json")
COLLECTOR_PATH = os.path.join(SRC_DIR, "arduino_collector.py")

# Localidad por defecto: Teusaquillo (sede de despliegue universitario).
LOCALIDAD_DEFECTO = 13

# Segundos que una lectura en vivo sigue considerándose vigente.
FRESCURA_LIVE_S = 60

# Antigüedad máxima del dataset en memoria antes de comprobar el CSV en disco.
# Evita releer 259 000 filas en cada petición mientras el colector escribe.
TTL_DATASET_S = 10

# Formato de marca de tiempo usado por el colector en latest.json.
FORMATO_TS = "%Y-%m-%d %H:%M:%S"

# Tamaño máximo aceptado en un cuerpo POST (protege contra cargas abusivas).
MAX_BODY_BYTES = 64 * 1024


def registrar_src_en_path() -> None:
    """Agrega src/ al sys.path para reutilizar los módulos del proyecto.

    Los módulos de src/ se importan de forma plana (``from predict import ...``)
    porque el directorio no es un paquete instalable; la misma convención se
    aplica en las pruebas mediante ``pythonpath`` en pyproject.toml.
    """
    if SRC_DIR not in sys.path:
        sys.path.insert(0, SRC_DIR)
