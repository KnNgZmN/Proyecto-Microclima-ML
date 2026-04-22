# Microclima Bogotá D.C. — Predicción por Localidad con ML + IoT

Sistema de predicción de temperatura a **30 minutos** para las **20 localidades de Bogotá D.C.**, basado en sensores ambientales IoT (Arduino) y un modelo de Machine Learning calibrado con física real del clima bogotano: corrección altitudinal, isla de calor urbana y patrón bimodal de lluvias.

---

## Índice

1. [Descripción del proyecto](#1-descripción-del-proyecto)
2. [Las 20 localidades de Bogotá](#2-las-20-localidades-de-bogotá)
3. [Estructura del repositorio](#3-estructura-del-repositorio)
4. [Requisitos del sistema](#4-requisitos-del-sistema)
5. [Instalación paso a paso](#5-instalación-paso-a-paso)
6. [Uso completo del sistema](#6-uso-completo-del-sistema)
7. [Dataset y variables](#7-dataset-y-variables)
8. [Física del modelo climático](#8-física-del-modelo-climático)
9. [Feature engineering](#9-feature-engineering)
10. [Modelo de Machine Learning](#10-modelo-de-machine-learning)
11. [Integración con Arduino](#11-integración-con-arduino)
12. [Aplicación web (Streamlit)](#12-aplicación-web-streamlit)
13. [Flujo completo del sistema](#13-flujo-completo-del-sistema)
14. [Resultados del modelo](#14-resultados-del-modelo)
15. [Solución de problemas frecuentes](#15-solución-de-problemas-frecuentes)

---

## 1. Descripción del proyecto

El microclima de Bogotá varía significativamente entre localidades: Sumapaz (páramo, 3 150 m) puede estar hasta **5 °C más fría** que Kennedy (zona plana densa, 2 570 m) en el mismo instante. Este proyecto modela esas diferencias de forma física y entrena un **Random Forest Regressor** sobre **259 200 registros** (20 localidades × 90 días × lecturas cada 10 min).

### Objetivo principal

> Predecir la temperatura ambiental con **30 minutos de anticipación** en cualquier localidad de Bogotá, usando temperatura, humedad, luz, ruido y geolocalización como entradas.

### Casos de uso

| Caso | Descripción |
|------|-------------|
| Simulación | Generar datos sintéticos y entrenar sin hardware |
| Predicción manual | Ingresar valores en la UI y obtener predicción para la localidad elegida |
| Tiempo real | Conectar Arduino y ver predicciones mientras llegan datos |
| Comparativa | Comparar temperatura media, rango y humedad entre las 20 localidades |
| Re-entrenamiento | Acumular lecturas reales del Arduino y mejorar el modelo |

---

## 2. Las 20 localidades de Bogotá

El sistema incluye las 20 localidades oficiales de Bogotá D.C. con sus coordenadas, altitud y densidad urbana reales (fuentes: IDECA, DANE Censo 2018, IDEAM).

| ID | Localidad | Altitud (m) | Densidad urbana | Zona |
|----|-----------|-------------|-----------------|------|
| 1 | Usaquén | 2 600 | 70 % | Norte |
| 2 | Chapinero | 2 610 | 82 % | Norte-Centro |
| 3 | Santa Fe | 2 620 | 75 % | Centro |
| 4 | San Cristóbal | 2 720 | 65 % | Sur-Oriente |
| 5 | Usme | 2 790 | 45 % | Sur |
| 6 | Tunjuelito | 2 600 | 72 % | Sur |
| 7 | Bosa | 2 565 | 78 % | Sur-Occidente |
| 8 | Kennedy | 2 570 | 88 % | Occidente |
| 9 | Fontibón | 2 558 | 76 % | Occidente |
| 10 | Engativá | 2 565 | 82 % | Occidente |
| 11 | Suba | 2 580 | 72 % | Norte-Occidente |
| 12 | Barrios Unidos | 2 590 | 88 % | Centro-Norte |
| **13** | **Teusaquillo** ⭐ | **2 600** | **87 %** | **Centro** |
| 14 | Los Mártires | 2 598 | 86 % | Centro |
| 15 | Antonio Nariño | 2 592 | 82 % | Sur-Centro |
| 16 | Puente Aranda | 2 580 | 83 % | Occidente |
| 17 | La Candelaria | 2 625 | 70 % | Centro-Histórico |
| 18 | Rafael Uribe Uribe | 2 617 | 72 % | Sur |
| 19 | Ciudad Bolívar | 2 750 | 52 % | Sur |
| 20 | Sumapaz | 3 150 | 5 % | Rural-Páramo |

> ⭐ Localidad de despliegue universitario — seleccionada por defecto en la aplicación y el recolector Arduino.

---

## 3. Estructura del repositorio

```
ProyectoMicroclima/
│
├── data/
│   └── raw/
│       └── data.csv              # Dataset multi-localidad (259 200 filas)
│
├── models/
│   ├── model.pkl                 # Modelo entrenado (Random Forest, ~40 MB)
│   └── metrics.json              # MAE, RMSE y lista de features del modelo
│
├── src/
│   ├── localidades.py            # Catálogo de las 20 localidades (lat, lon, altitud, densidad)
│   ├── generate_dataset.py       # Generador de datos sintéticos por localidad
│   ├── data_processing.py        # Carga, limpieza e interpolación de anomalías
│   ├── feature_engineering.py    # 19 features + función features_from_raw()
│   ├── train_model.py            # Entrenamiento con TimeSeriesSplit
│   ├── predict.py                # API de predicción (acepta localidad_id)
│   ├── arduino_collector.py      # Recolector serial desde Arduino (+ simulación)
│   └── visualization.py          # Gráficas de diagnóstico del modelo
│
├── app/
│   └── streamlit_app.py          # Interfaz web interactiva (4 pestañas)
│
├── requirements.txt
└── README.MD
```

---

## 4. Requisitos del sistema

### Software

| Requisito | Versión mínima | Notas |
|-----------|---------------|-------|
| Python | 3.9 | 3.10, 3.11 o 3.12 también funcionan |
| pip | Incluido con Python | Se usa para instalar dependencias |
| Git | Cualquiera | Solo si clonas el repositorio |
| Navegador web | Chrome, Firefox, Edge | Para la app Streamlit |

### Hardware (opcional)

| Componente | Función |
|------------|---------|
| Arduino Uno / Nano / Mega | Microcontrolador principal |
| Sensor DHT22 | Temperatura y humedad |
| LDR + resistencia 10 kΩ | Nivel de luz (lux aproximado) |
| Módulo KY-038 | Nivel de ruido (dB aproximado) |
| Cable USB tipo B | Conexión Arduino → PC |

### Dependencias Python

| Paquete | Versión recomendada | Uso |
|---------|---------------------|-----|
| `pandas` | ≥ 1.5 | Manipulación de datos temporales |
| `numpy` | ≥ 1.23 | Cálculos numéricos y señales |
| `scikit-learn` | ≥ 1.2 | Random Forest, TimeSeriesSplit, métricas |
| `joblib` | ≥ 1.2 | Serialización del modelo |
| `matplotlib` | ≥ 3.6 | Gráficas de diagnóstico |
| `streamlit` | ≥ 1.20 | Interfaz web |
| `pyserial` | ≥ 3.5 | Comunicación con Arduino (solo integración real) |

---

## 5. Instalación paso a paso

Sigue estas instrucciones desde cero en cualquier computador. Los comandos son los mismos en Windows (PowerShell o CMD), macOS y Linux (Terminal).

---

### Paso 5.1 — Verificar Python

Abre una terminal y ejecuta:

```bash
python --version
```

Si el comando no se reconoce, prueba:

```bash
python3 --version
```

Debes ver algo como `Python 3.9.x` o superior. Si no tienes Python instalado:

- **Windows**: descarga el instalador desde [python.org/downloads](https://www.python.org/downloads/) y marca la casilla **"Add Python to PATH"** durante la instalación.
- **macOS**: ejecuta `brew install python` (requiere Homebrew) o descarga desde python.org.
- **Linux (Ubuntu/Debian)**: ejecuta `sudo apt update && sudo apt install python3 python3-pip python3-venv`.

Verifica que pip también esté disponible:

```bash
pip --version
# o
pip3 --version
```

---

### Paso 5.2 — Obtener el proyecto

**Opción A — Clonar con Git:**

```bash
git clone <https://github.com/KnNgZmN/Proyecto-Microclima-ML>

```

### Paso 5.3 — Crear entorno virtual

Un entorno virtual aisla las dependencias del proyecto del resto del sistema. Es una buena práctica y evita conflictos con otros proyectos Python.

```bash
# Crear el entorno virtual (se crea una carpeta llamada "venv")
python -m venv venv
```

Si el comando falla, prueba con `python3`:

```bash
python3 -m venv venv
```

**Activar el entorno virtual:**

```bash
# Windows (PowerShell)
venv\Scripts\Activate.ps1

# Windows (CMD)
venv\Scripts\activate.bat

# macOS / Linux
source venv/bin/activate
```

Sabrás que el entorno está activo porque el prompt de la terminal mostrará `(venv)` al inicio:

```
(venv) C:\Users\TuUsuario\ProyectoMicroclima>
```

> **Importante**: cada vez que abras una nueva terminal debes activar el entorno virtual antes de ejecutar cualquier script del proyecto.

---

### Paso 5.4 — Instalar dependencias

Con el entorno virtual activo, instala todas las dependencias:

```bash
pip install -r requirements.txt
```

La instalación descarga e instala automáticamente todos los paquetes necesarios. Puede tardar 1-3 minutos dependiendo de tu conexión a internet.

**Verificar que todo se instaló correctamente:**

```bash
python -c "import pandas, numpy, sklearn, joblib, matplotlib, streamlit; print('OK — todas las dependencias instaladas')"
```

Si ves `OK — todas las dependencias instaladas`, estás listo para continuar.

---

### Paso 5.5 — Verificar la estructura del proyecto

Confirma que todos los archivos fuente están presentes:

```bash
# Windows
dir src\

# macOS / Linux
ls src/
```

Debes ver: `localidades.py`, `generate_dataset.py`, `data_processing.py`, `feature_engineering.py`, `train_model.py`, `predict.py`, `arduino_collector.py`, `visualization.py`.

---

## 6. Uso completo del sistema

Una vez instalado el proyecto, el flujo de uso es siempre el mismo: **generar datos → entrenar → usar la app**. Solo es necesario hacer los pasos 6.1 y 6.2 la primera vez (o cuando quieras regenerar datos frescos).

> Todos los comandos deben ejecutarse desde la **carpeta raíz del proyecto** (`ProyectoMicroclima/`) con el **entorno virtual activo**.

---

### Paso 6.1 — Generar el dataset

```bash
python src/generate_dataset.py
```

Este script genera `data/raw/data.csv` con **259 200 registros** (20 localidades × 90 días × 144 lecturas/día a intervalos de 10 min).

**Salida esperada en consola:**

```
Generando datos para 20 localidades x 90 dias...
  OK Usaquen                    alt=2600m  densidad=0.7
  OK Chapinero                  alt=2610m  densidad=0.82
  ...
  OK Sumapaz                    alt=3150m  densidad=0.05

Dataset multi-localidad generado con exito
Guardado en: .../data/raw/data.csv
Registros totales: 259,200
```

**¿Qué hace internamente?**

- Genera un ciclo diario de temperatura con pico a las 14:00 h para cada localidad.
- Aplica corrección altitudinal: localidades más altas son más frías (−6.5 °C por cada 1 000 m).
- Simula isla de calor urbana: zonas densas son más cálidas (hasta +2.5 °C de noche).
- Genera eventos de lluvia con probabilidad bimodal (más lluvia en abril-mayo y octubre-noviembre).
- Las localidades del oriente (más altas) tienen mayor probabilidad de lluvia.
- Agrega ruido de sensor, deriva de hardware y anomalías realistas (~3 % de lecturas).

---

### Paso 6.2 — Entrenar el modelo

```bash
python src/train_model.py
```

Puede tardar **3-8 minutos** dependiendo de tu CPU (el dataset tiene 259 000 filas y se entrena con 5 folds de validación cruzada).

**Salida esperada:**

```
[*] Registros para entrenamiento: 259,140  (20 localidades)
[F] Features (19): ['temperatura', 'humedad', ..., 'altitud', 'latitud', 'longitud', 'densidad_urbana']
  Fold 1: MAE=0.965 C  RMSE=1.519 C
  Fold 2: MAE=0.979 C  RMSE=1.519 C
  Fold 3: MAE=0.976 C  RMSE=1.538 C
  Fold 4: MAE=1.034 C  RMSE=1.603 C
  Fold 5: MAE=0.981 C  RMSE=1.544 C

[CV] MAE promedio CV:  0.987 +/- 0.024 C
[CV] RMSE promedio CV: 1.545 +/- 0.031 C

[>] Importancia de features (top 10):
temp_prom_30m      0.8706
temp_prom_1h       0.0559
hora_sin           0.0453
altitud            0.0026
densidad_urbana    0.0021
...

[OK] Modelo guardado en models/model.pkl
[OK] Metricas guardadas en models/metrics.json
```

---

### Paso 6.3 — Lanzar la aplicación web

```bash
streamlit run app/streamlit_app.py
```

La aplicación se abre automáticamente en el navegador en `http://localhost:8501`.

Si el navegador no se abre solo, copia la URL y pégala manualmente.

**Para detener la aplicación:** presiona `Ctrl + C` en la terminal.

---

### Paso 6.4 — Ver gráficas de diagnóstico (opcional)

```bash
python src/visualization.py
```

Genera tres gráficas del modelo para la localidad de Teusaquillo:
1. Predicción vs. valor real (primeras 200 muestras del test)
2. Error de predicción en el tiempo
3. Serie de temperatura + bandas de error

---

### Paso 6.5 — Conectar Arduino (opcional, cuando el hardware esté disponible)

**Simulación sin hardware (para probar antes de tener el Arduino):**

```bash
python src/arduino_collector.py --simulate --predict
```

Esto genera lecturas sintéticas realistas para Teusaquillo y muestra la predicción en tiempo real.

**Con Arduino real conectado al PC:**

```bash
# Windows — reemplaza COM3 con el puerto que aparece en el Administrador de dispositivos
python src/arduino_collector.py --port COM3 --predict

# Linux / macOS
python src/arduino_collector.py --port /dev/ttyUSB0 --predict
```

El script guarda automáticamente cada lectura en `data/raw/data.csv` y muestra la predicción para los próximos 30 minutos.

**Después de acumular datos reales, re-entrenar el modelo:**

```bash
python src/train_model.py
```

---

## 7. Dataset y variables

### Columnas del archivo `data/raw/data.csv`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `timestamp` | datetime | Fecha y hora de la lectura (`YYYY-MM-DD HH:MM:SS`) |
| `localidad_id` | int | ID de la localidad (1-20) |
| `localidad` | str | Nombre de la localidad |
| `latitud` | float | Latitud geográfica del centroide (grados decimales) |
| `longitud` | float | Longitud geográfica del centroide (grados decimales) |
| `altitud` | float | Altitud sobre el nivel del mar (metros) |
| `densidad_urbana` | float | Densidad urbana normalizada (0 = rural, 1 = muy denso) |
| `temperatura` | float | Temperatura ambiental (°C) |
| `humedad` | float | Humedad relativa (%) |
| `luz` | int | Nivel de luz (lux, 0-1000) |
| `ruido` | int | Nivel de ruido (dB, 30-100) |

### Rangos típicos por localidad

| Variable | Sumapaz (páramo) | Teusaquillo (centro) | Kennedy (urbano) |
|----------|-----------------|----------------------|-----------------|
| Temperatura media | ~9.4 °C | ~14.4 °C | ~14.7 °C |
| Temperatura mínima | −5 °C | −1 °C | 0 °C |
| Temperatura máxima | +25 °C | +30 °C | +30 °C |
| Humedad media | ~79 % | ~72 % | ~72 % |

---

## 8. Física del modelo climático

El dataset sintético incorpora efectos físicos reales del clima bogotano.

### 8.1 Corrección altitudinal

Bogotá tiene un rango de altitudes de ~600 m entre sus localidades (2 558 m en Fontibón — 3 150 m en Sumapaz). La temperatura disminuye con la altura siguiendo la **tasa de caída ambiental estándar ICAO/WMO**:

```
ΔT = (2 625 − altitud_localidad) × 0.0065  °C/m
```

Ejemplos:
- Sumapaz (3 150 m): ΔT = (2 625 − 3 150) × 0.0065 = **−3.4 °C** respecto al centro
- Kennedy (2 570 m): ΔT = (2 625 − 2 570) × 0.0065 = **+0.4 °C** respecto al centro

### 8.2 Isla de calor urbana (UHI)

Las zonas densamente urbanizadas acumulan y retienen calor (pavimento, edificios, actividad humana). El efecto es más pronunciado de noche:

```
UHI_día   = (densidad − 0.5) × 1.0 °C
UHI_noche = (densidad − 0.5) × 2.5 °C
```

Ejemplos:
- Kennedy (densidad 0.88): +0.38 °C de día, +0.95 °C de noche
- Sumapaz (densidad 0.05): −0.45 °C de día, −1.13 °C de noche

### 8.3 Patrón de lluvias de Bogotá

Temporadas bimodales calibradas con datos históricos IDEAM:

| Mes | Prob. lluvia (centro) | Obs. |
|-----|----------------------|------|
| Enero | 12 % | Temporada seca |
| Marzo | 28 % | Inicio temporada húmeda |
| Abril | 45 % | Pico lluvias primer semestre |
| Mayo | 48 % | Pico lluvias primer semestre |
| Julio | 18 % | Temporada seca mitad de año |
| Octubre | 46 % | Pico lluvias segundo semestre |
| Noviembre | 44 % | Pico lluvias segundo semestre |

Las localidades del oriente (San Cristóbal, Usme, Ciudad Bolívar) tienen mayor probabilidad de lluvia por su mayor altitud y cercanía a los cerros.

### 8.4 Otros efectos simulados

| Efecto | Implementación |
|--------|----------------|
| Ciclo diario | Función seno con pico a las 14:00 h |
| Días nublados | Factor de nubosidad beta por día (reduce luz y temperatura) |
| Lluvia: bajada brusca | Reducción aleatoria de 3-6 °C durante el evento |
| Deriva del sensor | +0.05 °C/mes acumulado (degradación de hardware) |
| Anomalías de sensor | ~3 % de lecturas con spike de ±5-8 °C |
| Ruido diferenciado | Más ruido en zonas densas; picos en horas punta (7-9 h, 17-19 h) |
| Humedad por altitud | Mayor humedad en zonas altas y rurales |

---

## 9. Feature engineering

Los **19 features** usados por el modelo se definen en `FEATURE_COLS` ([src/feature_engineering.py](src/feature_engineering.py)):

### Features sensoriales (4)

| Feature | Unidad | Descripción |
|---------|--------|-------------|
| `temperatura` | °C | Lectura cruda del sensor DHT22 |
| `humedad` | % | Lectura cruda del sensor DHT22 |
| `luz` | lux | Lectura cruda del LDR |
| `ruido` | dB | Lectura cruda del KY-038 |

### Features temporales (5)

| Feature | Descripción | Por qué es útil |
|---------|-------------|-----------------|
| `hora_sin` | `sin(2π × hora / 24)` | Codificación cíclica de la hora |
| `hora_cos` | `cos(2π × hora / 24)` | Evita discontinuidad 23 → 0 |
| `mes_sin` | `sin(2π × mes / 12)` | Codificación cíclica del mes |
| `mes_cos` | `cos(2π × mes / 12)` | Evita discontinuidad dic → ene |
| `es_dia` | 1 si 6 ≤ hora ≤ 18 | Separación régimen día/noche |

> **¿Por qué codificación cíclica?** La hora 23 y la hora 0 son contiguas en el tiempo pero distantes como entero (23 vs 0). `sin` y `cos` representan esa continuidad correctamente para el modelo.

### Features derivadas de temperatura (4)

| Feature | Ventana | Descripción |
|---------|---------|-------------|
| `temp_prom_30m` | 3 lecturas (30 min) | Promedio móvil — suaviza ruido del sensor |
| `temp_prom_1h` | 6 lecturas (60 min) | Tendencia a corto plazo |
| `cambio_temp` | 1 lectura (10 min) | Velocidad de cambio local (°C/10 min) |
| `tendencia_1h` | 6 lecturas (60 min) | Tendencia de mediano plazo |

### Features de humedad y física (2)

| Feature | Descripción |
|---------|-------------|
| `humedad_prom` | Promedio móvil 30 min de humedad |
| `presion_vapor` | Presión de vapor (fórmula Magnus): `(HR/100) × 6.1078 × exp(17.27 × T / (237.3 + T))` |

### Features de geolocalización (4)

| Feature | Descripción | Rango en Bogotá |
|---------|-------------|-----------------|
| `altitud` | Altitud de la localidad (m) | 2 558 – 3 150 m |
| `latitud` | Latitud del centroide (grados) | 4.33 – 4.74 ° |
| `longitud` | Longitud del centroide (grados) | −74.03 – −74.32 ° |
| `densidad_urbana` | Densidad urbana normalizada | 0.05 – 0.88 |

> **Nota sobre las ventanas móviles**: cuando el dataset contiene múltiples localidades, los promedios móviles y deltas se calculan **dentro de cada localidad** (usando `groupby`), evitando que el final de una localidad contamine el inicio de otra.

---

## 10. Modelo de Machine Learning

### Arquitectura

```
Entradas: 19 features (sensor + tiempo + geolocalización)
    ↓
Random Forest Regressor
    n_estimators = 150 árboles
    max_depth    = 12 niveles
    n_jobs       = -1  (usa todos los núcleos del CPU)
    ↓
Salida: temperatura estimada en t + 30 min  (°C)
```

### Validación temporal (TimeSeriesSplit)

Se usa `TimeSeriesSplit` en lugar de `train_test_split` aleatorio para **nunca usar datos futuros en el entrenamiento**. El dataset está ordenado por `[timestamp, localidad_id]`, de modo que cada fold agrega un bloque temporal posterior:

```
Fold 1:  [train₁──────────────────][test₁──]
Fold 2:  [train₁────────────────────────────][test₂──]
Fold 3:  [train₁──────────────────────────────────────][test₃──]
...
```

### Por qué Random Forest

| Ventaja | Importancia para este proyecto |
|---------|-------------------------------|
| No requiere normalización | Las features tienen unidades muy distintas (°C, lux, dB, m) |
| Maneja no-linealidades | Ciclos día/noche, eventos de lluvia, isla de calor |
| Robusto frente a anomalías | El dataset tiene ~3 % de lecturas erróneas |
| Importancia de features | Permite verificar qué variables explican más la predicción |
| Inferencia rápida | ~1 ms por predicción — adecuado para tiempo real con Arduino |

---

## 11. Integración con Arduino

### Esquema de conexión

| Sensor | Variable | Pin Arduino |
|--------|----------|-------------|
| DHT22 | Temperatura + Humedad | D2 |
| LDR + resistencia 10 kΩ a GND | Luz (lux aproximado) | A0 |
| Módulo KY-038 (salida analógica) | Ruido (dB aproximado) | A1 |

### Obtener el sketch de referencia

```bash
python src/arduino_collector.py --sketch
```

Imprime el código Arduino completo listo para copiar a tu IDE. El sketch usa la librería `DHT.h` y envía una lectura cada 10 segundos.

### Formato Serial que espera el recolector

El Arduino debe enviar **una línea CSV por lectura**, terminada en `\n`:

```
18.50,72.30,850,45
```

Orden: `temperatura(°C), humedad(%), luz(lux), ruido(dB)`

### Comandos del recolector

```bash
# Colectar datos en Teusaquillo (defecto) con predicción en vivo
python src/arduino_collector.py --port COM3 --predict

# Especificar otra localidad (ej. Kennedy = ID 8)
python src/arduino_collector.py --port COM3 --predict --localidad 8

# Puerto diferente (Linux/macOS)
python src/arduino_collector.py --port /dev/ttyUSB0 --predict

# Baud rate diferente (si el sketch usa 115200)
python src/arduino_collector.py --port COM3 --baud 115200 --predict

# Simulación sin hardware — genera lecturas realistas para Teusaquillo
python src/arduino_collector.py --simulate --predict

# Simulación en otra localidad con más lecturas
python src/arduino_collector.py --simulate --lecturas 200 --intervalo 2 --localidad 20

# Ver sketch de referencia
python src/arduino_collector.py --sketch
```

### Cómo encontrar el puerto COM (Windows)

1. Conecta el Arduino por USB.
2. Abre el **Administrador de dispositivos** (tecla Windows → busca "Administrador de dispositivos").
3. Expande la sección **Puertos (COM y LPT)**.
4. Busca "Arduino" o "USB Serial Device" — el número al lado es tu puerto (ej. `COM4`).

### Cómo encontrar el puerto en Linux/macOS

```bash
# Linux
ls /dev/tty*
# Busca /dev/ttyUSB0 o /dev/ttyACM0

# macOS
ls /dev/tty.*
# Busca /dev/tty.usbmodem o /dev/tty.usbserial
```

### Flujo de re-entrenamiento con datos reales

```bash
# 1. El arduino_collector guarda lecturas en data/raw/data.csv automáticamente
# 2. Cuando quieras re-entrenar con los datos reales acumulados:
python src/train_model.py
# El modelo nuevo se guarda en models/model.pkl y la app lo recarga automáticamente
```

---

## 12. Aplicación web (Streamlit)

La app tiene **cuatro pestañas**:

### Pestaña 1 — Datos históricos

- Métricas globales: total de registros, temperatura promedio, humedad, número de localidades.
- Selector de localidad con información de altitud, densidad y zona.
- Tabla con las últimas 12 lecturas.
- Gráfica de temperatura de las últimas 24 horas.
- Gráfica combinada temperatura + humedad.

### Pestaña 2 — Predicción por localidad

- Selector de localidad con tarjeta de metadata (altitud, densidad, coordenadas).
- Formulario de entrada: temperatura, humedad, luz, ruido, hora, mes.
- Predicción de temperatura en **t + 30 minutos**.
- Delta esperado respecto a la temperatura actual.
- Historial de sesión para promedios móviles reales (mejora la precisión).

### Pestaña 3 — Comparativa de localidades

- Gráfica de barras de temperatura media por localidad (escala de colores por temperatura).
- Diagrama de dispersión: temperatura media vs. altitud, coloreado por humedad.
- Tabla completa de estadísticas (mín, media, máx, humedad) para las 20 localidades.

### Pestaña 4 — Modo Arduino

- Tabla de IDs y parámetros de todas las localidades.
- Guía de comandos para recolección y simulación.
- Estado de la última lectura guardada en el dataset.

### Sidebar

- MAE y RMSE de validación cruzada del modelo actual.
- Número de features, registros y localidades del modelo.
- Comandos rápidos de referencia.

---

## 13. Flujo completo del sistema

```
╔══════════════════════════════════════════════════════════════╗
║  FASE 1 — DATOS SINTÉTICOS (sin hardware)                    ║
║                                                              ║
║  generate_dataset.py                                         ║
║      ↓  259 200 registros (20 localidades × 90 días)         ║
║  data/raw/data.csv  [timestamp, localidad_id, localidad,     ║
║                      latitud, longitud, altitud,             ║
║                      densidad_urbana, temp, hum, luz, ruido] ║
║      ↓                                                       ║
║  data_processing.py  (validación de rangos, interpolación)   ║
║      ↓                                                       ║
║  feature_engineering.py  (19 features, rolling por localidad)║
║      ↓                                                       ║
║  train_model.py  (RandomForest + TimeSeriesSplit × 5 folds)  ║
║      ↓                                                       ║
║  models/model.pkl  +  models/metrics.json                    ║
╚══════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════╗
║  FASE 2 — DATOS REALES (con Arduino, cuando esté disponible) ║
║                                                              ║
║  Arduino (DHT22 + LDR + KY-038)                              ║
║      ↓  Serial: "18.5,72.3,850,45\n"                        ║
║  arduino_collector.py --port COM3 --predict --localidad 13   ║
║      ├─ Valida rangos de sensor                              ║
║      ├─ Guarda en data/raw/data.csv (modo append)            ║
║      └─ Muestra predicción T+30min en consola                ║
║                                                              ║
║  [Actualizar modelo] → python src/train_model.py             ║
╚══════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════╗
║  INTERFAZ                                                    ║
║                                                              ║
║  streamlit run app/streamlit_app.py  →  http://localhost:8501║
║      ├─ Tab 1: Histórico filtrado por localidad              ║
║      ├─ Tab 2: Predicción con selector de localidad          ║
║      ├─ Tab 3: Comparativa de las 20 localidades             ║
║      └─ Tab 4: Guía de integración Arduino                   ║
╚══════════════════════════════════════════════════════════════╝
```

---

## 14. Resultados del modelo

Resultados reales obtenidos con el dataset multi-localidad (259 200 registros, 20 localidades):

| Métrica | Valor | Desviación estándar |
|---------|-------|---------------------|
| MAE (validación cruzada) | **0.987 °C** | ± 0.024 °C |
| RMSE (validación cruzada) | **1.545 °C** | ± 0.031 °C |

Comparación con el modelo anterior (dataset de una sola localidad, 25 920 registros):

| Versión | MAE | RMSE | Datos |
|---------|-----|------|-------|
| v1 (sin localidades) | 1.127 °C | 1.681 °C | 25 920 registros |
| **v2 (multi-localidad)** | **0.987 °C** | **1.545 °C** | **259 200 registros** |

El modelo mejoró gracias al mayor volumen de datos de entrenamiento y a las nuevas features de geolocalización (`altitud`, `densidad_urbana`) que le permiten aprender diferencias físicas entre localidades.

### Importancia de features (top 10)

| Feature | Importancia | Interpretación |
|---------|-------------|----------------|
| `temp_prom_30m` | 87.1 % | La temperatura reciente es el mejor predictor |
| `temp_prom_1h` | 5.6 % | Tendencia de la última hora |
| `hora_sin` | 4.5 % | Ciclo diario de temperatura |
| `hora_cos` | 0.55 % | Complemento del ciclo diario |
| `altitud` | 0.26 % | Diferencia térmica entre localidades |
| `humedad` | 0.24 % | Correlación física con temperatura |
| `densidad_urbana` | 0.21 % | Isla de calor urbana |
| `tendencia_1h` | 0.19 % | Velocidad de cambio a mediano plazo |
| `temperatura` | 0.23 % | Valor puntual actual |
| `humedad_prom` | 0.22 % | Humedad suavizada |

---

## 15. Solución de problemas frecuentes

### "No module named 'streamlit'" (u otro paquete)

El entorno virtual no está activo o no se instalaron las dependencias. Solución:

```bash
# Activar entorno virtual primero
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate.bat       # Windows CMD
venv\Scripts\Activate.ps1       # Windows PowerShell

# Luego instalar
pip install -r requirements.txt
```

### "No se encontró data.csv" en la app web

El dataset no ha sido generado. Ejecuta:

```bash
python src/generate_dataset.py
```

### "Modelo no encontrado" en la app web

El modelo no ha sido entrenado. Ejecuta:

```bash
python src/train_model.py
```

### La app web muestra métricas desactualizadas

Tras re-entrenar el modelo, recarga la página del navegador (`F5` o `Ctrl + R`).

### Error de puerto serial en Windows: "could not open port COM3"

- Verifica el puerto correcto en el Administrador de dispositivos.
- Asegúrate de que el IDE de Arduino no esté usando el puerto al mismo tiempo.
- Prueba desconectando y reconectando el cable USB.

### Error de puerto serial en Linux: "Permission denied /dev/ttyUSB0"

```bash
sudo usermod -a -G dialout $USER
# Luego cierra sesión y vuelve a entrar al sistema
```

### La app Streamlit no abre el navegador automáticamente

Copia manualmente la URL que aparece en la terminal (`http://localhost:8501`) y pégala en tu navegador.

### "UnicodeEncodeError" al ejecutar scripts en Windows

Algunos terminales de Windows (CMD clásico) no soportan caracteres especiales. Usa **PowerShell** o **Windows Terminal** en lugar de CMD. Alternativamente:

```bash
set PYTHONUTF8=1
python src/train_model.py
```

### El entrenamiento tarda demasiado

El dataset completo (259 200 filas) puede tardar 5-10 min en un CPU de 2 núcleos. El flag `n_jobs=-1` usa todos los núcleos disponibles. Mientras tanto, puedes seguir usando la aplicación con el modelo anterior.

---

*Proyecto desarrollado para el curso de IoT — 7.º semestre.*
*Universitaria de Colombia, Bogotá D.C.*
