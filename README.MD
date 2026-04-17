# 🌫️ Microclima Bogotá — Predicción con Machine Learning + IoT

Sistema de predicción de temperatura a **30 minutos** basado en datos de sensores ambientales, entrenado con patrones climáticos realistas de Bogotá y diseñado para integrarse con hardware Arduino.

---

## Índice

1. [Descripción del proyecto](#descripción-del-proyecto)
2. [Estructura del repositorio](#estructura-del-repositorio)
3. [Requisitos](#requisitos)
4. [Instalación](#instalación)
5. [Guía de uso paso a paso](#guía-de-uso-paso-a-paso)
6. [Dataset y variables](#dataset-y-variables)
7. [Feature engineering](#feature-engineering)
8. [Modelo de Machine Learning](#modelo-de-machine-learning)
9. [Integración con Arduino](#integración-con-arduino)
10. [Aplicación web (Streamlit)](#aplicación-web-streamlit)
11. [Flujo completo del sistema](#flujo-completo-del-sistema)
12. [Resultados esperados](#resultados-esperados)

---

## Descripción del proyecto

El microclima de Bogotá presenta patrones complejos: temperatura entre 7 °C y 19 °C con ciclos diarios marcados, temporadas lluviosas bimodales (abril-mayo y octubre-noviembre) y variaciones bruscas por lluvia. Este proyecto entrena un **Random Forest Regressor** sobre 180 días de datos sintéticos realistas y expone una interfaz de predicción que puede recibir lecturas en tiempo real desde un Arduino.

### Objetivo principal

Predecir la temperatura ambiental con 30 minutos de anticipación a partir de temperatura, humedad, luz y nivel de ruido actuales.

### Casos de uso

| Caso | Descripción |
|------|-------------|
| Simulación | Generar datos sintéticos y entrenar el modelo sin hardware |
| Predicción manual | Ingresar valores manualmente desde la UI web |
| Tiempo real | Conectar un Arduino y ver predicciones mientras llegan datos |
| Re-entrenamiento | Acumular lecturas reales del Arduino y re-entrenar con datos propios |

---

## Estructura del repositorio

```
ProyectoMicroclima/
│
├── data/
│   └── raw/
│       └── data.csv                # Dataset generado (25,920 filas, 180 días × 10 min)
│
├── models/
│   ├── model.pkl                   # Modelo entrenado (serializado con joblib)
│   └── metrics.json                # MAE y RMSE de validación cruzada
│
├── src/
│   ├── generate_dataset.py         # Generador de datos sintéticos realistas
│   ├── data_processing.py          # Carga, limpieza e interpolación de anomalías
│   ├── feature_engineering.py      # Ingeniería de features + constante FEATURE_COLS
│   ├── train_model.py              # Entrenamiento con TimeSeriesSplit y guardado de métricas
│   ├── predict.py                  # Función de predicción reutilizable
│   └── arduino_collector.py        # Colector de datos Serial desde Arduino (+ simulación)
│
├── app/
│   └── streamlit_app.py            # Interfaz web interactiva
│
├── requirements.txt
└── README.MD
```

---

## Requisitos

- Python 3.9 o superior
- (Opcional) Arduino con sensores DHT22, LDR y KY-038

### Dependencias Python

| Paquete | Uso |
|---------|-----|
| `pandas` | Manipulación de datos temporales |
| `numpy` | Cálculos numéricos y señales |
| `scikit-learn` | Random Forest, validación cruzada, métricas |
| `joblib` | Serialización del modelo |
| `matplotlib` | Visualización |
| `streamlit` | Interfaz web |
| `pyserial` | Comunicación con Arduino (solo para integración real) |

---

## Instalación

```bash
# 1. Clonar o descargar el proyecto
cd ProyectoMicroclima

# 2. Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# 3. Instalar dependencias
pip install -r requirements.txt
```

---

## Guía de uso paso a paso

### Paso 1 — Generar el dataset

```bash
python src/generate_dataset.py
```

Genera `data/raw/data.csv` con **25,920 registros** (180 días a intervalos de 10 minutos).
Incluye simulación de lluvias, días nublados, anomalías de sensor y deriva de hardware.

### Paso 2 — Entrenar el modelo

```bash
python src/train_model.py
```

- Realiza validación cruzada temporal con **5 folds** (`TimeSeriesSplit`)
- Imprime MAE y RMSE por fold y promedio
- Guarda el modelo en `models/model.pkl`
- Guarda las métricas en `models/metrics.json`

Salida de ejemplo:

```
  Fold 1: MAE=0.312 °C  RMSE=0.441 °C
  Fold 2: MAE=0.298 °C  RMSE=0.421 °C
  ...
📈 MAE promedio CV: 0.305 ± 0.018 °C
💾 Modelo guardado en models/model.pkl
```

### Paso 3 — Lanzar la aplicación web

```bash
streamlit run app/streamlit_app.py
```

Abre `http://localhost:8501` en el navegador.

### Paso 4 (opcional) — Conectar Arduino

```bash
# Con hardware real
python src/arduino_collector.py --port COM3 --predict

# Sin hardware (simulación)
python src/arduino_collector.py --simulate --predict
```

---

## Dataset y variables

### Variables del sensor (columnas en `data.csv`)

| Variable | Tipo | Unidad | Rango típico Bogotá | Descripción |
|----------|------|--------|----------------------|-------------|
| `timestamp` | datetime | — | — | Fecha y hora de la lectura |
| `temperatura` | float | °C | 7 – 19 | Temperatura ambiental |
| `humedad` | float | % HR | 50 – 95 | Humedad relativa |
| `luz` | int | lux | 0 – 1000 | Iluminancia (0 = noche/lluvia, 1000 = pleno sol) |
| `ruido` | int | dB | 30 – 90 | Nivel de ruido ambiental |

### Realismo del dataset sintético

El generador incorpora los siguientes efectos basados en el clima real de Bogotá:

| Efecto | Implementación |
|--------|----------------|
| Ciclo diario de temperatura | Función seno con pico a las 14:00 h |
| Lluvias por temporada | Probabilidad mensual (bimodal: abr-may / oct-nov) |
| Bajada de temperatura por lluvia | Reducción aleatoria de 3-6 °C durante el evento |
| Días nublados | Factor de nubosidad beta por día (reduce luz y temperatura) |
| Variación mensual | Offset por mes (temporadas secas más cálidas) |
| Deriva del sensor | +0.05 °C/mes acumulado (degradación real de hardware) |
| Anomalías de sensor | ~3 % de lecturas con spike de ±5-8 °C |

---

## Feature engineering

Los 15 features usados por el modelo se definen en `FEATURE_COLS` ([src/feature_engineering.py](src/feature_engineering.py)):

| Feature | Descripción | Por qué es útil |
|---------|-------------|-----------------|
| `temperatura` | Valor crudo del sensor | Base de la predicción |
| `humedad` | Valor crudo del sensor | Correlación inversa con temperatura |
| `luz` | Valor crudo del sensor | Indica hora del día e irradiación |
| `ruido` | Valor crudo del sensor | Proxy de actividad humana |
| `hora_sin` / `hora_cos` | Codificación cíclica de la hora | Evita discontinuidad 23 → 0 |
| `mes_sin` / `mes_cos` | Codificación cíclica del mes | Captura estacionalidad sin salto dic → ene |
| `es_dia` | 1 si 6 ≤ hora ≤ 18 | Separación de regímenes día/noche |
| `temp_prom_30m` | Promedio móvil 30 min (3 lecturas) | Suaviza ruido del sensor |
| `temp_prom_1h` | Promedio móvil 1 hora (6 lecturas) | Tendencia a corto plazo |
| `cambio_temp` | Δ temperatura en 10 min | Velocidad de cambio local |
| `tendencia_1h` | Δ temperatura en 1 hora | Tendencia de mediano plazo |
| `humedad_prom` | Promedio móvil humedad 30 min | Estabiliza ruido de humedad |
| `presion_vapor` | Fórmula Magnus: `(HR/100) × 6.1078 × exp(...)` | Variable física con alta correlación a temperatura |

> **Codificación cíclica**: la hora 23 y la hora 0 son contiguas en el mundo real pero distantes en un entero (23 vs 0). Codificar con `sin(2π·hora/24)` y `cos(2π·hora/24)` preserva esa continuidad para el modelo.

---

## Modelo de Machine Learning

### Arquitectmo

```
Entrada: 15 features de sensor + tiempo
    ↓
Random Forest Regressor
    • n_estimators = 150 árboles
    • max_depth    = 12 niveles
    • n_jobs       = -1 (todos los cores)
    ↓
Salida: temperatura estimada en t + 30 min (°C)
```

### Validación temporal

Se usa `TimeSeriesSplit` en lugar de `train_test_split` aleatorio para **nunca usar datos futuros en el entrenamiento**, respetando el orden temporal de las lecturas.

```
[train₁][test₁]
[train₁ + train₂][test₂]
[train₁ + train₂ + train₃][test₃]
...
```

### Por qué Random Forest

- No requiere normalización ni escalado de features
- Maneja bien las no-linealidades (ciclos día/noche, eventos de lluvia)
- Robusto frente a las anomalías que quedaron tras la limpieza
- Soporta importancia de features para inspección del modelo
- Inferencia rápida (~1 ms por predicción) — adecuado para tiempo real

---

## Integración con Arduino

### Esquema de sensores recomendado

| Sensor | Variable medida | Pin sugerido |
|--------|----------------|-------------|
| DHT22 | Temperatura + Humedad | D2 |
| LDR + resistencia 10 kΩ | Luz (lux aproximado) | A0 |
| KY-038 | Nivel de ruido (dB aproximado) | A1 |

### Formato Serial esperado

El Arduino debe enviar **una línea CSV por lectura** terminada en `\n`:

```
18.50,72.30,850,45
```

Orden: `temperatura,humedad,luz,ruido`

### Obtener el sketch de referencia

```bash
python src/arduino_collector.py --sketch
```

El sketch generado usa la biblioteca `DHT.h` y envía una lectura cada 10 segundos.

### Comandos del colector

```bash
# Recolectar datos (guarda en data/raw/data.csv)
python src/arduino_collector.py --port COM3

# Recolectar + mostrar predicción T+30min en consola
python src/arduino_collector.py --port COM3 --predict

# Especificar baud rate diferente
python src/arduino_collector.py --port /dev/ttyUSB0 --baud 115200

# Simulación sin hardware (100 lecturas)
python src/arduino_collector.py --simulate --lecturas 100 --predict

# Ajustar intervalo entre lecturas simuladas (segundos)
python src/arduino_collector.py --simulate --intervalo 2
```

### Flujo re-entrenamiento con datos reales

Después de acumular lecturas reales del Arduino:

```bash
# Los datos ya fueron guardados por arduino_collector.py en data/raw/data.csv
# Re-entrenar el modelo con los datos reales acumulados:
python src/train_model.py
```

El modelo se actualiza automáticamente con la mezcla de datos sintéticos y reales.

---

## Aplicación web (Streamlit)

La app tiene tres pestañas:

| Pestaña | Contenido |
|---------|-----------|
| **Datos históricos** | Métricas generales, últimas 10 lecturas, gráfica 24h, temperatura vs humedad |
| **Predicción manual** | Formulario de entrada manual, predicción T+30min, historial de sesión para promedios reales |
| **Modo Arduino** | Guía de comandos, estado de la última lectura, tabla de sensores |

Las métricas del modelo (MAE, RMSE) se muestran en el **sidebar** y se actualizan automáticamente tras cada re-entrenamiento.

---

## Flujo completo del sistema

```
┌─────────────────────────────────────────────────────────┐
│  FASE 1 — DATOS SINTÉTICOS (sin hardware)               │
│                                                         │
│  generate_dataset.py                                    │
│      ↓  25,920 registros, 180 días                      │
│  data/raw/data.csv                                      │
│      ↓                                                  │
│  data_processing.py (limpieza + interpolación)          │
│      ↓                                                  │
│  feature_engineering.py (15 features)                   │
│      ↓                                                  │
│  train_model.py (RandomForest + TimeSeriesSplit)        │
│      ↓                                                  │
│  models/model.pkl  +  models/metrics.json               │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  FASE 2 — DATOS REALES (con Arduino)                    │
│                                                         │
│  Arduino (DHT22 + LDR + KY-038)                         │
│      ↓  Serial: "18.5,72.3,850,45\n"                   │
│  arduino_collector.py                                   │
│      ├─ Valida rangos por sensor                        │
│      ├─ Guarda en data/raw/data.csv (append)            │
│      └─ Predicción en vivo (opcional)                   │
│                                                         │
│  [Re-entrenar] → python src/train_model.py              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  INTERFAZ                                               │
│                                                         │
│  streamlit run app/streamlit_app.py                     │
│      ├─ Visualización histórica                         │
│      ├─ Predicción manual con historial de sesión       │
│      └─ Guía de integración Arduino                     │
└─────────────────────────────────────────────────────────┘
```

---

## Resultados esperados

Con el dataset sintético de 180 días, el modelo típicamente alcanza:

| Métrica | Valor esperado |
|---------|---------------|
| MAE (validación cruzada) | 0.25 – 0.45 °C |
| RMSE (validación cruzada) | 0.35 – 0.60 °C |

Un MAE de ~0.35 °C es excelente para predicción de temperatura a 30 minutos; el error humano de percepción de temperatura en interiores es de ~0.5 °C.

Con datos reales del Arduino, el modelo mejora progresivamente al capturar las particularidades del microambiente específico donde están instalados los sensores.
