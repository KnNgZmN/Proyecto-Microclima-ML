# Microclima Bogotá D.C. — Predicción por Localidad con ML + IoT

Sistema de predicción de temperatura a **30 minutos** para las **20 localidades de Bogotá D.C.**, combinando sensores ambientales IoT (Arduino) con Machine Learning calibrado sobre física real del clima bogotano.

[![Pruebas y Cobertura](https://github.com/KnNgZmN/Proyecto-Microclima-ML/actions/workflows/tests.yml/badge.svg)](https://github.com/KnNgZmN/Proyecto-Microclima-ML/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/KnNgZmN/Proyecto-Microclima-ML/branch/main/graph/badge.svg)](https://codecov.io/gh/KnNgZmN/Proyecto-Microclima-ML)
![Pruebas](https://img.shields.io/badge/pruebas-217%20passed-brightgreen)

---

## Índice

### Parte 1 — Qué es y cómo funciona
1. [El problema: microclima en Bogotá](#1-el-problema-microclima-en-bogotá)
2. [Solución: IoT + Machine Learning](#2-solución-iot--machine-learning)
3. [Las 20 localidades de Bogotá](#3-las-20-localidades-de-bogotá)
4. [Física del modelo climático](#4-física-del-modelo-climático)
5. [El dataset — qué datos usamos y por qué](#5-el-dataset--qué-datos-usamos-y-por-qué)
6. [Feature engineering — las 19 variables del modelo](#6-feature-engineering--las-19-variables-del-modelo)
7. [Modelo de Machine Learning — Random Forest](#7-modelo-de-machine-learning--random-forest)
8. [Flujo completo del sistema](#8-flujo-completo-del-sistema)
9. [Resultados del modelo](#9-resultados-del-modelo)
10. [Aplicación web (Streamlit)](#10-aplicación-web-streamlit)
11. [Integración con Arduino](#11-integración-con-arduino)

### Parte 2 — Guía paso a paso (desde cero en Windows)
12. [Estructura del repositorio](#12-estructura-del-repositorio)
13. [Requisitos del sistema](#13-requisitos-del-sistema)
14. [Paso 1 — Verificar Python](#paso-1--verificar-python)
15. [Paso 2 — Obtener el proyecto](#paso-2--obtener-el-proyecto)
16. [Paso 3 — Crear entorno virtual](#paso-3--crear-entorno-virtual)
17. [Paso 4 — Instalar dependencias](#paso-4--instalar-dependencias)
18. [Paso 5 — Generar el dataset](#paso-5--generar-el-dataset)
19. [Paso 6 — Entrenar el modelo](#paso-6--entrenar-el-modelo)
20. [Paso 7 — Lanzar la aplicación web](#paso-7--lanzar-la-aplicación-web)
21. [Paso 8 — Simular el Arduino (sin hardware)](#paso-8--simular-el-arduino-sin-hardware)
22. [Paso 9 — Conectar Arduino real (cuando esté disponible)](#paso-9--conectar-arduino-real-cuando-esté-disponible)
23. [Solución de problemas frecuentes](#23-solución-de-problemas-frecuentes)

### Parte 3 — Calidad y métricas del software (8.º semestre)
24. [Pruebas automatizadas y cobertura](#24-pruebas-automatizadas-y-cobertura)
25. [Integración continua (GitHub Actions)](#25-integración-continua-github-actions)

---

# Parte 1 — Qué es y cómo funciona

---

## 1. El problema: microclima en Bogotá

Bogotá D.C. no tiene un solo clima — tiene **20 microclimas distintos**.

Las 20 localidades de Bogotá están distribuidas entre los **2 558 m** de altitud (Fontibón) y los **3 150 m** (Sumapaz), una diferencia de casi 600 metros dentro de la misma ciudad. Aplicando la tasa de caída de temperatura estándar de la atmósfera (6.5 °C por cada 1 000 m de altura — estándar ICAO/WMO), eso se traduce en una diferencia de hasta **5 °C** entre localidades en el mismo instante.

A esto se suma el **efecto de isla de calor urbana (UHI)**: Kennedy o Teusaquillo, con densidades urbanas del 87-88%, pueden estar casi 1 °C más calientes de noche que lo que su altitud sola explicaría, mientras que Sumapaz (5% de densidad urbana, zona páramo) se comporta como campo abierto.

**¿Por qué importa predecir esto?**  
Un sistema que predice temperatura con 30 minutos de anticipación — específicamente para la localidad donde está el usuario — permite:
- Tomar decisiones sobre ropa, salidas y actividades
- Monitorear condiciones de confort en espacios físicos
- Acumular datos locales reales para mejorar el modelo continuamente

**El reto técnico:**  
No existe una estación meteorológica por localidad. El IDEAM tiene cobertura limitada. Los modelos climáticos generales no capturan diferencias de microclima a nivel de barrio. Este proyecto llena ese vacío con sensores IoT de bajo costo y Machine Learning.

---

## 2. Solución: IoT + Machine Learning

La arquitectura del sistema combina dos tecnologías:

### IoT (Internet of Things) — Los sensores

Un Arduino equipado con tres sensores mide el ambiente cada 10 minutos:

| Sensor | Variable medida | Unidad |
|--------|----------------|--------|
| DHT22 | Temperatura y humedad | °C y % |
| LDR + resistencia 10kΩ | Nivel de luz (luminosidad) | lux |
| Módulo KY-038 | Nivel de ruido (actividad urbana) | dB |

El Arduino envía los datos por USB al computador en formato CSV (`18.50,72.30,850,45\n`).

### Machine Learning — El modelo predictivo

Un **Random Forest Regressor** aprende de 259 200 lecturas históricas (20 localidades × 90 días × 144 lecturas/día) la relación entre las condiciones actuales y la temperatura que habrá 30 minutos después.

El modelo recibe **19 variables de entrada** (features) y produce **1 predicción**: la temperatura en t + 30 min.

### La aplicación web

Una interfaz construida con Streamlit muestra en tiempo real los datos del Arduino, las predicciones, comparativas entre localidades y controles del sistema — accesible desde cualquier navegador.

---

## 3. Las 20 localidades de Bogotá

El sistema modela las 20 localidades oficiales de Bogotá D.C. con sus datos reales de altitud, coordenadas y densidad urbana (fuentes: IDECA, DANE Censo 2018).

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
| **13** | **Teusaquillo ⭐** | **2 600** | **87 %** | **Centro** |
| 14 | Los Mártires | 2 598 | 86 % | Centro |
| 15 | Antonio Nariño | 2 592 | 82 % | Sur-Centro |
| 16 | Puente Aranda | 2 580 | 83 % | Occidente |
| 17 | La Candelaria | 2 625 | 70 % | Centro-Histórico |
| 18 | Rafael Uribe Uribe | 2 617 | 72 % | Sur |
| 19 | Ciudad Bolívar | 2 750 | 52 % | Sur |
| 20 | Sumapaz | 3 150 | 5 % | Rural-Páramo |

> ⭐ Localidad de despliegue universitario — seleccionada por defecto en la aplicación y en el recolector Arduino.

**Diferencias de temperatura entre extremos:**
- Sumapaz (3 150 m, páramo) puede estar hasta **5 °C más fría** que Kennedy (2 570 m, muy urbanizada) en el mismo momento.

---

## 4. Física del modelo climático

El dataset sintético no es aleatorio: incorpora efectos físicos reales y documentados del clima bogotano.

### 4.1 Corrección altitudinal (estándar ICAO/WMO)

La temperatura disminuye con la altitud a una tasa de **6.5 °C por cada 1 000 metros** — la tasa de caída ambiental estándar definida por la ICAO y adoptada por la WMO.

```
ΔT = (2 625 − altitud_localidad) × 0.0065   [°C]

Donde 2 625 m = altitud de La Candelaria (punto de referencia)
      0.0065 °C/m = 6.5 °C / 1000 m
```

| Localidad | Altitud | ΔT respecto al centro |
|-----------|---------|----------------------|
| Kennedy | 2 570 m | +0.36 °C (más caliente) |
| Teusaquillo | 2 600 m | +0.16 °C |
| San Cristóbal | 2 720 m | −0.62 °C |
| Ciudad Bolívar | 2 750 m | −0.81 °C |
| Sumapaz | 3 150 m | −3.41 °C (mucho más frío) |

### 4.2 Isla de calor urbana (Urban Heat Island — UHI)

Las zonas densamente urbanizadas acumulan y retienen calor (pavimento, edificios, vehículos, actividad humana). El efecto es **más pronunciado de noche** porque la ciudad no se enfría tan rápido como el campo.

```
UHI_día   = (densidad_urbana − 0.5) × 1.0   [°C]
UHI_noche = (densidad_urbana − 0.5) × 2.5   [°C]
```

| Localidad | Densidad | UHI de día | UHI de noche |
|-----------|----------|-----------|--------------|
| Kennedy | 0.88 | +0.38 °C | +0.95 °C |
| Teusaquillo | 0.87 | +0.37 °C | +0.93 °C |
| Ciudad Bolívar | 0.52 | +0.02 °C | +0.05 °C |
| Sumapaz | 0.05 | −0.45 °C | −1.13 °C |

### 4.3 Patrón de lluvias de Bogotá (datos IDEAM)

Bogotá tiene un régimen bimodal de lluvias (dos temporadas húmedas al año), calibrado con históricos del IDEAM:

| Mes | Prob. lluvia | Temporada |
|-----|-------------|-----------|
| Enero | 12 % | Seca |
| Abril–Mayo | 45–48 % | Húmeda (1er semestre) |
| Julio | 18 % | Seca |
| Octubre–Noviembre | 44–46 % | Húmeda (2do semestre) |

Las localidades del oriente (San Cristóbal, Usme, Ciudad Bolívar) tienen mayor probabilidad de lluvia por su altitud y cercanía a los cerros orientales.

### 4.4 Otros efectos físicos simulados

| Efecto | Implementación |
|--------|---------------|
| Ciclo diario de temperatura | Función seno con pico a las 14:00 h |
| Lluvia: bajada brusca | Reducción de 3-6 °C durante eventos de lluvia |
| Deriva del sensor | +0.05 °C/mes acumulado (degradación de hardware) |
| Anomalías de sensor | ~3% de lecturas con spike de ±5-8 °C |
| Ruido diferenciado | Más ruido en zonas densas; picos en horas punta (7-9h, 17-19h) |

---

## 5. El dataset — qué datos usamos y por qué

### ¿Qué es el dataset?

Un dataset es la colección de datos históricos sobre la que el modelo aprende. Es como el "libro de texto" del modelo: cuantos más ejemplos variados tenga, mejor aprende.

### Dimensiones

```
259 200 filas = 20 localidades × 90 días × 144 lecturas/día (cada 10 min)
```

### Columnas del archivo `data/raw/data.csv`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `timestamp` | datetime | Fecha y hora de la lectura (`YYYY-MM-DD HH:MM:SS`) |
| `localidad_id` | int | ID de la localidad (1-20) |
| `localidad` | str | Nombre de la localidad |
| `latitud` | float | Latitud geográfica del centroide (grados decimales) |
| `longitud` | float | Longitud geográfica del centroide (grados decimales) |
| `altitud` | float | Altitud sobre el nivel del mar (metros) |
| `densidad_urbana` | float | Densidad urbana (0 = rural, 1 = muy denso) |
| `temperatura` | float | Temperatura ambiental (°C) — variable principal |
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

### Datos sintéticos vs. datos reales

El dataset fue generado matemáticamente usando la física descrita en la sección anterior. Cuando el Arduino se conecta, sus lecturas reales se agregan al mismo CSV para que el modelo pueda re-entrenarse con datos del mundo real y mejorar progresivamente.

---

## 6. Feature engineering — las 19 variables del modelo

Feature engineering es el proceso de transformar las columnas crudas del dataset en las variables que el modelo puede aprender. Algunos features vienen directos del sensor; otros se calculan matemáticamente para capturar patrones que el sensor no mide directamente.

### Categoría 1 — Lecturas crudas del sensor (4 features)

| Feature | Sensor | Unidad |
|---------|--------|--------|
| `temperatura` | DHT22 | °C |
| `humedad` | DHT22 | % |
| `luz` | LDR | lux |
| `ruido` | KY-038 | dB |

### Categoría 2 — Tiempo codificado cíclicamente (5 features)

El modelo necesita saber "qué hora es", pero el número entero de hora (0 a 23) tiene una discontinuidad: el modelo pensaría que las 23h y las 0h están muy alejadas (diferencia de 23), cuando en realidad están a 1 hora de distancia. La solución es codificar la hora como un punto en un círculo usando seno y coseno:

```
hora_sin = sin(2π × hora / 24)    →  captura el momento en el ciclo diario
hora_cos = cos(2π × hora / 24)    →  necesario para distinguir horas simétricas
mes_sin  = sin(2π × mes  / 12)    →  ciclo estacional
mes_cos  = cos(2π × mes  / 12)    →  necesario para distinguir meses simétricos
es_dia   = 1 si 6h ≤ hora ≤ 18h  →  separación régimen día/noche
```

Con seno Y coseno juntos, cada hora tiene una combinación única de valores — ninguna ambigüedad.

### Categoría 3 — Promedios móviles y tasas de cambio (5 features)

La temperatura futura depende no solo del valor actual sino de la tendencia reciente. Estas variables capturan "de dónde venimos":

| Feature | Ventana temporal | Lo que captura |
|---------|-----------------|---------------|
| `temp_prom_30m` | Últimas 3 lecturas (30 min) | Temperatura promedio reciente — suaviza ruido del sensor |
| `temp_prom_1h` | Últimas 6 lecturas (60 min) | Tendencia a corto plazo |
| `cambio_temp` | 1 lectura (10 min) | Velocidad de cambio: ¿subiendo o bajando? |
| `tendencia_1h` | 6 lecturas (60 min) | Cambio acumulado en la última hora |
| `humedad_prom` | Últimas 3 lecturas (30 min) | Humedad promedio suavizada |

**Importante — Rolling por localidad:**  
Cuando el dataset tiene 20 localidades concatenadas, los promedios móviles se calculan **dentro de cada localidad** para evitar que el final de los datos de Usaquén "contamine" el inicio de los datos de Chapinero:

```python
df["temp_prom_30m"] = df.groupby("localidad_id")["temperatura"].transform(
    lambda x: x.rolling(3, min_periods=1).mean()
)
```

### Categoría 4 — Física y geolocalización (5 features)

| Feature | Descripción |
|---------|-------------|
| `presion_vapor` | `(HR/100) × 6.1078 × exp(17.27 × T / (237.3 + T))` — energía latente del aire |
| `altitud` | Altitud de la localidad en metros (2 558 – 3 150 m en Bogotá) |
| `latitud` | Latitud geográfica del centroide |
| `longitud` | Longitud geográfica del centroide |
| `densidad_urbana` | Densidad urbana normalizada (0.05 – 0.88 en Bogotá) |

Las variables de geolocalización le dicen al modelo "en qué tipo de lugar está" y le permiten aplicar implícitamente las correcciones de altitud e isla de calor que aprendió del dataset.

---

## 7. Modelo de Machine Learning — Random Forest

### ¿Qué predice el modelo?

La temperatura ambiental en los próximos **30 minutos** (3 lecturas × 10 min), llamada `temp_futura` en el código.

```python
# create_target en feature_engineering.py
df["temp_futura"] = df.groupby("localidad_id")["temperatura"].transform(
    lambda x: x.shift(-3)   # 3 pasos × 10 min = 30 min adelante
)
```

### ¿Cómo funciona Random Forest?

Un árbol de decisión hace preguntas sobre los features para llegar a una predicción. El problema con un solo árbol es que se "memoriza" el dataset y falla con datos nuevos (sobreajuste).

Random Forest entrena **150 árboles distintos** (en este proyecto), donde cada árbol se entrena con una muestra aleatoria del dataset y un subconjunto aleatorio de features. La predicción final es el **promedio** de los 150 árboles — los errores individuales se cancelan entre sí.

```
Árbol 1  →  15.1 °C
Árbol 2  →  14.8 °C
Árbol 3  →  15.4 °C
  ...
Árbol 150 → 15.0 °C
─────────────────────
Promedio  → 15.1 °C  ✓
```

### Arquitectura del modelo

```
Entradas: 19 features (sensor + tiempo + geolocalización)
    ↓
Random Forest Regressor
    n_estimators = 150 árboles
    max_depth    = 12 niveles por árbol
    n_jobs       = -1 (todos los núcleos del CPU)
    ↓
Salida: temperatura estimada en t + 30 min  (°C)
```

### ¿Por qué Random Forest y no otro algoritmo?

| Ventaja | Por qué importa en este proyecto |
|---------|----------------------------------|
| No requiere normalización | Los features tienen unidades muy distintas: °C, lux, dB, metros |
| Maneja no-linealidades | El ciclo día/noche y los eventos de lluvia no son relaciones lineales |
| Robusto frente a anomalías | El dataset tiene ~3% de lecturas erróneas de sensor |
| Importancia de features | Muestra qué variables explican más la predicción |
| Predicción rápida | ~1 ms por predicción — apto para tiempo real con Arduino |

### Validación temporal — TimeSeriesSplit

Para datos ordenados en el tiempo NO se puede usar validación aleatoria (`train_test_split`) porque el modelo podría "ver el futuro" durante el entrenamiento y dar resultados artificialmente buenos.

Se usa **TimeSeriesSplit** con 5 folds, donde el set de prueba siempre está temporalmente DESPUÉS del set de entrenamiento:

```
Fold 1:  [── train (días 1–54) ──────────────────────][test (días 55–63)]
Fold 2:  [── train (días 1–63) ──────────────────────────][test (días 64–72)]
Fold 3:  [── train (días 1–72) ────────────────────────────][test (días 73–81)]
Fold 4:  [── train (días 1–81) ──────────────────────────────][test (días 82–87)]
Fold 5:  [── train (días 1–87) ────────────────────────────────][test (días 88–90)]
```

El MAE y RMSE se calculan en cada fold y se promedian → resultado confiable y realista.

---

## 8. Flujo completo del sistema

```
╔══════════════════════════════════════════════════════════════╗
║  FASE 1 — DATOS SINTÉTICOS (sin hardware)                    ║
║                                                              ║
║  generate_dataset.py                                         ║
║      ↓  259 200 registros (20 localidades × 90 días)         ║
║  data/raw/data.csv                                           ║
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
║      ├─ Valida rangos del sensor                             ║
║      ├─ Guarda en data/raw/data.csv (modo append)            ║
║      ├─ Escribe data/live/latest.json (Streamlit lo lee)     ║
║      └─ Muestra predicción T+30min en consola                ║
║                                                              ║
║  [Re-entrenar] → python src/train_model.py                   ║
╚══════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════╗
║  INTERFAZ                                                    ║
║                                                              ║
║  streamlit run app/streamlit_app.py → http://localhost:8501  ║
║      ├─ Tab 1: Histórico + lectura en vivo                   ║
║      ├─ Tab 2: Predicción manual por localidad               ║
║      ├─ Tab 3: Comparativa de las 20 localidades             ║
║      └─ Tab 4: Arduino en vivo (control + live + dataset)    ║
╚══════════════════════════════════════════════════════════════╝
```

---

## 9. Resultados del modelo

Resultados reales obtenidos con el dataset multi-localidad (259 200 registros):

| Métrica | Valor | Desviación estándar |
|---------|-------|---------------------|
| MAE (validación cruzada) | **0.987 °C** | ± 0.024 °C |
| RMSE (validación cruzada) | **1.545 °C** | ± 0.031 °C |

**Interpretación:**  
El modelo se equivoca en promedio menos de 1 °C. Para Bogotá, donde el rango diario típico es de 10-12 °C, un error de ~1 °C representa una precisión del ~90% del rango total.

**Comparación con la versión anterior:**

| Versión | MAE | RMSE | Registros de entrenamiento |
|---------|-----|------|--------------------------|
| v1 (sin localidades, sin geolocalización) | 1.127 °C | 1.681 °C | 25 920 |
| **v2 (multi-localidad con geo)** | **0.987 °C** | **1.545 °C** | **259 200** |

La mejora proviene de dos factores: 10× más datos de entrenamiento y las 4 features de geolocalización que permiten al modelo diferenciar microclimas por altitud y densidad urbana.

**Importancia de features (top 10):**

| Feature | Importancia | Qué captura |
|---------|-------------|-------------|
| `temp_prom_30m` | 87.1 % | Temperatura media reciente — el mejor predictor |
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

## 10. Aplicación web (Streamlit)

La app tiene **4 pestañas** y se refresca automáticamente cada 5 segundos para mostrar datos del Arduino en vivo.

### Pestaña 1 — Datos históricos

- Métricas globales: total de registros, temperatura promedio, humedad, número de localidades
- Selector de localidad con información de altitud, densidad y zona
- Lectura en tiempo real del Arduino (si está activo) o del último registro del CSV
- Predicción automática de T+30 min
- Tabla con las últimas 12 lecturas y gráficas de temperatura de las últimas 24 h

### Pestaña 2 — Predicción por localidad

- Selector de localidad con tarjeta de metadatos (altitud, densidad, coordenadas)
- Formulario de entrada: temperatura, humedad, luz, ruido, hora, mes
- Predicción de temperatura en **t + 30 minutos** — el resultado persiste entre refrescos
- Delta esperado respecto a la temperatura actual

### Pestaña 3 — Comparativa de localidades

- Gráfica de barras de temperatura media por localidad
- Diagrama de dispersión: temperatura vs. altitud, coloreado por humedad
- Tabla completa de estadísticas (mín, media, máx, humedad) para las 20 localidades

### Pestaña 4 — Arduino en vivo

- Botones para iniciar Arduino real, iniciar simulación o detener el colector
- Lectura en vivo con indicador de frescura (🟢 < 15 s / 🟡 < 60 s / 🔴 desconectado)
- Historial reciente y predicción manual con valores pre-rellenados del Arduino
- Botón para descargar el dataset completo

### Sidebar

- MAE y RMSE del modelo actual
- Indicador de estado del Arduino
- Comandos rápidos de referencia

---

## 11. Integración con Arduino

### Esquema de conexión

| Sensor | Variable | Pin Arduino |
|--------|----------|-------------|
| DHT22 | Temperatura + Humedad | D2 |
| LDR + resistencia 10kΩ a GND | Luz | A0 |
| Módulo KY-038 (salida analógica) | Ruido | A1 |

### Formato de comunicación serial

El Arduino envía una línea CSV por lectura, terminada en `\n`:

```
18.50,72.30,850,45
```

Orden: `temperatura(°C), humedad(%), luz(lux), ruido(dB)`

El script Python `arduino_collector.py` lee ese formato, construye los 19 features, llama al modelo y guarda la predicción.

---

# Parte 2 — Guía paso a paso (desde cero en Windows)

---

## 12. Estructura del repositorio

```
ProyectoMicroclima/
│
├── data/
│   ├── raw/
│   │   └── data.csv              # Dataset multi-localidad (259 200 filas) ← se genera
│   └── live/
│       └── latest.json           # Última lectura del Arduino ← se genera al conectar
│
├── models/
│   ├── model.pkl                 # Modelo entrenado (~40 MB) ← se genera
│   └── metrics.json              # MAE, RMSE y lista de features ← se genera
│
├── src/
│   ├── localidades.py            # Catálogo de las 20 localidades (lat, lon, altitud, densidad)
│   ├── generate_dataset.py       # Generador de datos sintéticos por localidad
│   ├── data_processing.py        # Carga, limpieza e interpolación
│   ├── feature_engineering.py    # 19 features + función features_from_raw()
│   ├── train_model.py            # Entrenamiento con TimeSeriesSplit
│   ├── predict.py                # API de predicción (acepta localidad_id)
│   ├── arduino_collector.py      # Recolector serial desde Arduino (+ simulación)
│   └── visualization.py          # Gráficas de diagnóstico del modelo
│
├── app/
│   └── streamlit_app.py          # Interfaz web interactiva (4 pestañas)
│
├── tests/                        # Suite de pruebas — 217 casos
│   ├── conftest.py               # Fixtures compartidas y doble del modelo
│   ├── test_data_processing.py   # Saneamiento e interpolación
│   ├── test_feature_engineering.py  # Features, ciclos y aislamiento por localidad
│   ├── test_localidades.py       # Integridad del catálogo de 20 localidades
│   ├── test_predict.py           # Inferencia con modelo simulado
│   └── test_arduino_collector.py # Validación de rangos y persistencia
│
├── docs/
│   └── cobertura-alcance.md      # Alcance de la medición y exclusiones
│
├── .github/
│   └── workflows/
│       └── tests.yml             # CI: pytest + cobertura en cada push y PR
│
├── pyproject.toml                # Configuración de pytest y coverage
├── requirements.txt              # Dependencias de ejecución
├── requirements-dev.txt          # Dependencias de desarrollo y pruebas
├── CONTEXTO_EXPOSICION.md        # Glosario técnico para la exposición
└── README.MD                     # Este archivo
```

---

## 13. Requisitos del sistema

### Software

| Requisito | Versión mínima | Notas |
|-----------|---------------|-------|
| Python | 3.9 | 3.10, 3.11 o 3.12 también funcionan |
| pip | Incluido con Python | Instalador de paquetes |
| Git | Cualquiera | Solo si clonas el repositorio |
| Navegador web | Chrome, Firefox, Edge | Para la app Streamlit |

### Hardware (opcional — solo para fase real)

| Componente | Función |
|------------|---------|
| Arduino Uno / Nano / Mega | Microcontrolador principal |
| Sensor DHT22 | Temperatura y humedad |
| LDR + resistencia 10 kΩ | Nivel de luz |
| Módulo KY-038 | Nivel de ruido |
| Cable USB tipo B | Conexión Arduino → PC |

### Dependencias Python (se instalan automáticamente)

| Paquete | Uso |
|---------|-----|
| `pandas` | Manipulación de datos temporales |
| `numpy` | Cálculos numéricos y señales |
| `scikit-learn` | Random Forest, TimeSeriesSplit, métricas |
| `joblib` | Serialización del modelo |
| `matplotlib` | Gráficas de diagnóstico |
| `streamlit` | Interfaz web |
| `pyserial` | Comunicación con Arduino (solo integración real) |

### Dependencias de desarrollo (`requirements-dev.txt`)

Solo hacen falta para ejecutar las pruebas. No son necesarias para usar la aplicación.

| Paquete | Uso |
|---------|-----|
| `pytest` | Ejecución de la suite de pruebas |
| `pytest-cov` | Integración de la medición de cobertura con pytest |
| `coverage[toml]` | Motor de cobertura de líneas y ramas |

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

---

## Paso 1 — Verificar Python

Abre **PowerShell** o **CMD** y ejecuta:

```bash
python --version
```

Debes ver algo como `Python 3.9.x` o superior. Si el comando no se reconoce:

1. Descarga el instalador desde [python.org/downloads](https://www.python.org/downloads/)
2. Durante la instalación, **marca la casilla "Add Python to PATH"** — esto es crítico
3. Cierra y vuelve a abrir la terminal
4. Vuelve a ejecutar `python --version`

Verifica también que pip esté disponible:

```bash
pip --version
```

---

## Paso 2 — Obtener el proyecto

**Opción A — Clonar con Git:**

```bash
git clone https://github.com/KnNgZmN/Proyecto-Microclima-ML
cd Proyecto-Microclima-ML
```

**Opción B — Descargar ZIP:**

1. Ve al repositorio en GitHub
2. Haz clic en el botón verde "Code" → "Download ZIP"
3. Extrae el ZIP en una carpeta de tu elección
4. Abre una terminal en esa carpeta

Para abrir una terminal en una carpeta específica en Windows:
- Navega a la carpeta en el Explorador de archivos
- Haz clic en la barra de direcciones, escribe `powershell` y presiona Enter

---

## Paso 3 — Crear entorno virtual

Un entorno virtual aísla las dependencias del proyecto para no interferir con otros proyectos Python del sistema.

```bash
# Crear el entorno virtual (crea una carpeta llamada "venv")
python -m venv venv
```

**Activar el entorno virtual en Windows:**

```bash
# PowerShell
venv\Scripts\Activate.ps1

# CMD
venv\Scripts\activate.bat
```

Sabrás que está activo porque el prompt mostrará `(venv)` al inicio:

```
(venv) C:\Users\TuUsuario\ProyectoMicroclima>
```

> **Importante:** cada vez que abras una nueva terminal debes activar el entorno virtual antes de ejecutar cualquier script del proyecto.

**Si PowerShell bloquea la ejecución del script:**

```bash
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Luego vuelve a ejecutar `venv\Scripts\Activate.ps1`.

---

## Paso 4 — Instalar dependencias

Con el entorno virtual activo, instala todas las dependencias de una sola vez:

```bash
pip install -r requirements.txt
```

La descarga puede tardar 1-3 minutos según tu conexión. Al finalizar, verifica que todo esté correcto:

```bash
python -c "import pandas, numpy, sklearn, joblib, matplotlib, streamlit; print('OK — todas las dependencias instaladas')"
```

Si ves `OK — todas las dependencias instaladas`, continúa. Si hay un error, verifica que el entorno virtual esté activo y vuelve a ejecutar el pip install.

---

## Paso 5 — Generar el dataset

Este paso genera el "libro de texto" del modelo: 259 200 registros de temperatura y variables ambientales para las 20 localidades de Bogotá durante 90 días.

```bash
python src/generate_dataset.py
```

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

El script puede tardar 30-60 segundos. Al terminar, el archivo `data/raw/data.csv` estará disponible.

---

## Paso 6 — Entrenar el modelo

Este paso analiza el dataset completo, construye los 19 features, valida el modelo con 5 folds temporales y entrena el modelo final.

```bash
python src/train_model.py
```

**Puede tardar entre 3 y 10 minutos** dependiendo de tu CPU (el dataset tiene 259 000 filas y el proceso se repite 5 veces para la validación cruzada).

**Salida esperada:**

```
[*] Registros para entrenamiento: 259,140  (20 localidades)
[F] Features (19): ['temperatura', 'humedad', 'luz', 'ruido', ...]

  Fold 1: MAE=0.965 °C  RMSE=1.519 °C
  Fold 2: MAE=0.979 °C  RMSE=1.519 °C
  Fold 3: MAE=0.976 °C  RMSE=1.538 °C
  Fold 4: MAE=1.034 °C  RMSE=1.603 °C
  Fold 5: MAE=0.981 °C  RMSE=1.544 °C

[CV] MAE promedio CV:  0.987 ± 0.024 °C
[CV] RMSE promedio CV: 1.545 ± 0.031 °C

[>] Importancia de features (top 10):
temp_prom_30m      0.8706
temp_prom_1h       0.0559
hora_sin           0.0453
...

[OK] Modelo guardado en models/model.pkl
[OK] Métricas guardadas en models/metrics.json
```

Al terminar, el archivo `models/model.pkl` contiene el modelo listo para predecir.

---

## Paso 7 — Lanzar la aplicación web

```bash
streamlit run app/streamlit_app.py
```

La aplicación se abre automáticamente en el navegador en:

```
http://localhost:8501
```

Si el navegador no se abre solo, copia esa URL y pégala manualmente en Chrome, Firefox o Edge.

**Para detener la aplicación:** presiona `Ctrl + C` en la terminal.

**Qué hacer en la app:**
1. En la **Pestaña 1** verás los datos históricos del dataset y una predicción automática para Teusaquillo
2. En la **Pestaña 2** puedes seleccionar cualquier localidad, ingresar valores manualmente y obtener la predicción
3. En la **Pestaña 3** compara temperatura y humedad entre las 20 localidades
4. En la **Pestaña 4** controlas el Arduino y ves los datos en vivo

---

## Paso 8 — Simular el Arduino (sin hardware)

Puedes probar el sistema completo de tiempo real sin necesitar el Arduino físico:

```bash
# Simular lecturas de Teusaquillo (localidad por defecto)
python src/arduino_collector.py --simulate --predict
```

**Salida en consola:**

```
[SIM] Localidad: Teusaquillo (ID=13) | alt=2600m | densidad=0.87
[SIM] Lectura  1: temp=15.3°C  hum=72%  luz=580lux  ruido=54dB
      → Predicción T+30min: 15.7 °C
[SIM] Lectura  2: temp=15.4°C  hum=71%  luz=620lux  ruido=52dB
      → Predicción T+30min: 15.8 °C
...
```

Mientras este script corre, abre la app web (Paso 7) en otra terminal y ve a la **Pestaña 4 (Arduino en vivo)** — verás los datos actualizándose en tiempo real.

**Simular otra localidad:**

```bash
# Simular Sumapaz (localidad 20, páramo)
python src/arduino_collector.py --simulate --predict --localidad 20

# Simular Kennedy (localidad 8, zona urbana densa)
python src/arduino_collector.py --simulate --predict --localidad 8
```

**Parámetros adicionales de simulación:**

```bash
# Más lecturas y más rápido (para llenar el historial)
python src/arduino_collector.py --simulate --lecturas 200 --intervalo 2 --localidad 13

# Ver el código Arduino de referencia
python src/arduino_collector.py --sketch
```

---

## Paso 9 — Conectar Arduino real (cuando esté disponible)

### 1. Subir el sketch al Arduino

```bash
# Ver el código a cargar al Arduino
python src/arduino_collector.py --sketch
```

Copia ese código, abre el **Arduino IDE**, pégalo y súbelo al Arduino.

### 2. Identificar el puerto COM en Windows

1. Conecta el Arduino por USB
2. Abre el **Administrador de dispositivos** (tecla Windows → busca "Administrador de dispositivos")
3. Expande la sección **Puertos (COM y LPT)**
4. Busca "Arduino Uno" o "USB Serial Device" — el número es tu puerto (ej. `COM4`)

### 3. Iniciar el recolector

```bash
# Reemplaza COM3 con tu puerto real
python src/arduino_collector.py --port COM3 --predict

# Si tu localidad es diferente a Teusaquillo (ej. Kennedy = ID 8)
python src/arduino_collector.py --port COM3 --predict --localidad 8

# Si el Arduino usa baud rate 115200
python src/arduino_collector.py --port COM3 --baud 115200 --predict
```

El recolector guarda cada lectura en `data/raw/data.csv` automáticamente.

### 4. Re-entrenar con datos reales

Después de acumular suficientes lecturas reales:

```bash
python src/train_model.py
```

El modelo nuevo se guarda en `models/model.pkl` y la app lo recarga automáticamente.

---

## 23. Solución de problemas frecuentes

### "No module named 'streamlit'" (u otro paquete)

El entorno virtual no está activo. En PowerShell:

```bash
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### "No se encontró data.csv"

El dataset no fue generado. Ejecuta:

```bash
python src/generate_dataset.py
```

### "Modelo no encontrado"

El modelo no fue entrenado. Ejecuta:

```bash
python src/train_model.py
```

### La app muestra métricas desactualizadas

Tras re-entrenar el modelo, recarga la página del navegador (`F5`).

### Error "could not open port COM3" en Windows

- Verifica el puerto correcto en el Administrador de dispositivos
- Cierra el IDE de Arduino si está abierto (no pueden usar el mismo puerto simultáneamente)
- Desconecta y reconecta el cable USB

### PowerShell bloquea la activación del entorno virtual

```bash
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### "UnicodeEncodeError" al ejecutar scripts

Usa PowerShell o Windows Terminal en lugar de CMD clásico. Alternativamente:

```bash
set PYTHONUTF8=1
python src/train_model.py
```

### El entrenamiento tarda demasiado

Normal con CPUs de 2 núcleos: puede tardar 8-10 minutos. El flag `n_jobs=-1` ya usa todos los núcleos disponibles. Mientras tanto, puedes usar la aplicación con el modelo anterior.

### La app no muestra datos en la Pestaña 4

El archivo `data/live/latest.json` aún no existe. Inicia la simulación desde la misma Pestaña 4 (botón "Iniciar simulación") o desde la terminal:

```bash
python src/arduino_collector.py --simulate --predict
```

### El resultado de predicción desaparece en la app

La app se refresca cada 5 segundos. Los resultados de predicción (Tab 2 y Tab 4) se almacenan en sesión y persisten entre refrescos automáticos. Solo desaparecen si recargas la página manualmente (F5) o cierras la pestaña.

---

# Parte 3 — Calidad y métricas del software (8.º semestre)

---

## 24. Pruebas automatizadas y cobertura

Esta parte corresponde al módulo de **Calidad y Métricas del Software**, que retoma este mismo proyecto. De las siete áreas de la *Guía Integral de Métricas de Ingeniería y Herramientas*, el equipo escogió la **sección 4 — Cobertura de Pruebas**.

### ¿Qué es la cobertura de pruebas?

Es el porcentaje de código fuente que se ejecuta cuando corre la suite de pruebas automatizadas. Si una línea nunca se ejecuta durante las pruebas, nadie está verificando que funcione: puede romperse sin que nada avise.

Se miden dos cosas distintas:

| Métrica | Qué responde |
|---------|--------------|
| **Cobertura de líneas** | ¿Se ejecutó esta línea alguna vez? |
| **Cobertura de ramas** | En un `if`, ¿se probaron **ambos** caminos (verdadero y falso)? |

La cobertura de ramas es la más estricta y es la que exige la guía. Un `if` cuyo `else` nunca se prueba cuenta como línea cubierta pero rama incompleta.

### Herramientas utilizadas

La guía de la docente lista JaCoCo (Java) e Istanbul/c8 (JavaScript), que no aplican a un proyecto Python. Las equivalencias adoptadas son:

| Herramienta de la guía | Equivalente adoptado | Función |
|------------------------|----------------------|---------|
| JaCoCo / Istanbul | `coverage.py` + `pytest-cov` | Motor de medición de líneas y ramas |
| Codecov | Codecov | Histórico y *diff coverage* de cada PR |

### Cómo ejecutar las pruebas

```bash
# Instalar las dependencias de desarrollo (solo la primera vez)
pip install -r requirements.txt -r requirements-dev.txt

# Ejecutar toda la suite
pytest

# Ejecutar con reporte de cobertura en la terminal
pytest --cov --cov-branch --cov-report=term-missing

# Generar el reporte HTML navegable
pytest --cov --cov-report=html
```

El reporte HTML queda en `htmlcov/index.html`. Ábrelo en el navegador: muestra el código fuente coloreado, en verde lo cubierto y en rojo lo que ninguna prueba ejecuta.

Las pruebas **no dependen del dataset ni del modelo entrenado**. `data/raw/data.csv` y `models/model.pkl` se generan localmente y están en `.gitignore`, así que no existen en el servidor de integración continua. La suite sustituye el modelo por un doble de prueba y redirige las escrituras a directorios temporales, por lo que corre en una copia recién clonada del repositorio.

### Resultados actuales

Línea base medida **antes** de escribir cualquier prueba, para poder documentar el antes y el después:

| Indicador | Antes | Ahora |
|-----------|-------|-------|
| Pruebas automatizadas | 0 | **217** |
| Cobertura total (líneas + ramas) | 0.00 % | **57.72 %** |
| Cobertura del núcleo lógico | 0.00 % | **100.00 %** |
| Sentencias sin cubrir | 266 | 110 |

Desglose por módulo:

| Módulo | Sentencias | Sin cubrir | Cobertura |
|--------|-----------:|-----------:|----------:|
| `src/data_processing.py` | 18 | 0 | **100.00 %** |
| `src/feature_engineering.py` | 60 | 0 | **100.00 %** |
| `src/localidades.py` | 4 | 0 | **100.00 %** |
| `src/predict.py` | 22 | 0 | **100.00 %** |
| `src/arduino_collector.py` | 162 | 110 | 30.81 % |
| **TOTAL** | **266** | **110** | **57.72 %** |

### Qué cubre cada archivo de pruebas

| Archivo | Casos | Qué verifica |
|---------|------:|--------------|
| `test_localidades.py` | 107 | Que las 20 localidades tengan todos sus campos, coordenadas dentro de Bogotá, densidad normalizada y altitudes plausibles |
| `test_feature_engineering.py` | 39 | Las 19 features, la codificación cíclica de hora y mes, la fórmula de presión de vapor y que los promedios móviles **no se contaminen entre localidades** |
| `test_predict.py` | 31 | La inferencia para las 20 localidades, el fallback ante una localidad desconocida y la carga perezosa del modelo |
| `test_arduino_collector.py` | 25 | La validación de rangos del sensor y la escritura correcta del CSV y del JSON en vivo |
| `test_data_processing.py` | 15 | La detección de valores fuera de rango y su interpolación lineal |

### Alcance de la medición y deuda conocida

El 30.81 % de `arduino_collector.py` no es un descuido. Las 110 sentencias sin cubrir son casi todas `leer_serial()` y `simular()`, que abren un puerto serie físico y ejecutan bucles indefinidos. **No se excluyeron de la medición**: se dejan contabilizadas a propósito para que la deuda quede visible en la métrica en lugar de esconderse tras una exclusión.

Sí están excluidos tres scripts (`generate_dataset.py`, `train_model.py` y `visualization.py`) porque ejecutan todo su contenido al importarse: no tienen la guarda `if __name__ == "__main__"`. Importarlos desde una prueba dispararía la generación del dataset completo, el entrenamiento del modelo o la apertura de ventanas de matplotlib. Es un hallazgo de testabilidad documentado como deuda técnica a refactorizar.

El detalle completo del alcance, las exclusiones y su justificación está en **[docs/cobertura-alcance.md](docs/cobertura-alcance.md)**.

**Meta declarada: 80 %.** El mayor avance disponible es sustituir `pyserial` por un doble de prueba para cubrir `leer_serial()`.

---

## 25. Integración continua (GitHub Actions)

Cada `push` y cada Pull Request hacia `main` dispara automáticamente el flujo definido en `.github/workflows/tests.yml`:

1. Descarga el repositorio con su historial completo (Codecov lo necesita para el *diff coverage*)
2. Instala Python 3.13 y las dependencias de desarrollo
3. Ejecuta las 217 pruebas midiendo líneas y ramas
4. Publica el resultado en Codecov
5. Adjunta el reporte HTML como artefacto descargable (30 días)
6. Escribe un resumen de cobertura en la pestaña **Summary** de la ejecución

### Umbral de regresión

`pyproject.toml` define `fail_under = 55`. Si un cambio hace caer la cobertura por debajo del 55 %, **la build falla**. Es la alerta por caída de porcentaje que menciona la guía, y evita que se agregue código sin pruebas sin que nadie lo note.

### Consultar los resultados

- **Pestaña Actions** del repositorio → última ejecución → *Summary* para la tabla de cobertura
- **Artefacto `reporte-cobertura-html`** → descargar y abrir `index.html` para el detalle línea por línea

### Integración con Codecov

El secreto `CODECOV_TOKEN` ya está registrado y la subida de informes está verificada, así que el histórico de cobertura se acumula desde cada ejecución en `main`.

El comportamiento de Codecov se configura en `codecov.yml`:

| Verificación | Umbral | Qué controla |
|--------------|--------|--------------|
| `project` | Caída máxima de 1 punto | Que la cobertura global no retroceda |
| `patch` | 80 % | Que el **código nuevo** de cada PR venga cubierto |

La verificación `patch` es el *diff coverage* que menciona la guía: no exige cubrir todo el pasado, pero sí que lo que se agregue de aquí en adelante llegue con pruebas.

### Por qué Codecov y `pytest` reportan cifras distintas

No es un error de configuración. Miden el mismo código con fórmulas diferentes:

| Herramienta | Cifra | Fórmula |
|-------------|-------|---------|
| `coverage.py` | **57,72 %** | Incluye las **ramas** en el denominador junto a las sentencias |
| Codecov | 58,27 % | `hits / (hits + misses + partials)` — solo sobre líneas |

**La cifra oficial del proyecto es la de `coverage.py` (57,72 %)**, porque incluye cobertura de ramas, que es la métrica que exige la sección 4 de la guía. La de Codecov se usa para leer la evolución temporal, no para reportar el nivel alcanzado.

---

*Proyecto desarrollado para el curso de IoT — 7.º semestre.*  
*Continuado en el módulo de Calidad y Métricas del Software — 8.º semestre.*  
*Universitaria de Colombia, Bogotá D.C.*
