# Front web sin framework (HTML + CSS + JavaScript)

Este documento describe la interfaz web del proyecto construida **sin Streamlit
y sin ningún framework de frontend**, pensada para que SonarQube pueda analizar
el código de la capa de presentación (HTML, CSS y JavaScript) además del Python.

La aplicación de Streamlit (`app/streamlit_app.py`) sigue funcionando; esta
interfaz es una alternativa equivalente que expone la misma funcionalidad.

---

## 1. Por qué existe

SonarQube analiza el código fuente por lenguaje. Con Streamlit, toda la interfaz
está escrita en Python mediante llamadas a la librería, así que **no hay HTML,
CSS ni JavaScript que medir**: el analizador no puede reportar métricas de la
capa web (accesibilidad, complejidad del DOM, reglas de JS, CSS sin usar…).

Al separar el proyecto en dos piezas:

| Capa | Tecnología | Qué analiza SonarQube |
|------|-----------|------------------------|
| `api/` | Python estándar (`http.server`) | Complejidad, duplicación, code smells, seguridad |
| `web/` | HTML5, CSS3, JavaScript ES2020 | Reglas de JS/CSS/HTML, accesibilidad, duplicación |

…se obtiene un proyecto multi-lenguaje analizable de punta a punta.

---

## 2. Arquitectura

```
Navegador (web/)                       Servidor (api/)                 Proyecto existente (src/)
┌──────────────────────┐   fetch()    ┌──────────────────────┐        ┌────────────────────────┐
│ index.html           │ ───────────► │ server.py            │        │ data_processing.py     │
│ css/estilos.css      │              │  ├── rutas.py        │ ─────► │ feature_engineering.py │
│ js/main.js           │ ◄─────────── │  ├── servicios.py    │        │ localidades.py         │
│ js/vistas/*.js       │    JSON      │  ├── repositorio.py  │        │ arduino_collector.py   │
│ js/graficos.js       │              │  └── colector.py     │        └────────────────────────┘
└──────────────────────┘              └──────────────────────┘
```

- **Sin dependencias nuevas**: el servidor usa solo `http.server`, `json` y
  `argparse` de la biblioteca estándar. No se instala FastAPI, Flask ni Django.
- **Sin librerías de frontend**: no hay React, Vue, jQuery, Chart.js ni CDN.
  Las gráficas se dibujan con la API `<canvas>` 2D del navegador
  (`web/js/graficos.js`), reemplazando a las figuras de matplotlib.
- **Reutilización total**: la lógica de ML no se duplicó; `api/servicios.py`
  importa los módulos de `src/` exactamente igual que lo hacía Streamlit.

### Módulos del backend

| Archivo | Responsabilidad |
|---------|-----------------|
| `api/config.py` | Rutas de archivos, constantes y registro de `src/` en `sys.path` |
| `api/repositorio.py` | Lectura y caché del dataset, el modelo, las métricas y `latest.json` |
| `api/servicios.py` | Agregaciones, lectura vigente, comparativa y predicción |
| `api/colector.py` | Arranque, parada y estado del subproceso `arduino_collector.py` |
| `api/rutas.py` | Tabla de endpoints y validación de parámetros |
| `api/server.py` | Servidor HTTP, archivos estáticos y traducción de errores |

### Módulos del frontend

| Archivo | Responsabilidad |
|---------|-----------------|
| `web/js/main.js` | Arranque, pestañas, refresco automático y panel lateral |
| `web/js/api.js` | Cliente REST con manejo unificado de errores |
| `web/js/estado.js` | Estado compartido (localidad activa, entorno interior, historial) |
| `web/js/dom.js` | Construcción de DOM con `createElement`/`textContent` |
| `web/js/componentes.js` | Campos, botones, tarjetas de métrica e insignias reutilizables |
| `web/js/graficos.js` | Gráficas de líneas, barras y dispersión sobre `<canvas>` |
| `web/js/vistas/*.js` | Una pestaña por archivo (históricos, predicción, comparativa, Arduino) |

---

## 3. Cómo ejecutarlo

```bash
# 1. Entorno virtual activado y dependencias instaladas
venv\Scripts\activate

# 2. Dataset y modelo generados (igual que para Streamlit)
python src/generate_dataset.py
python src/train_model.py

# 3. Levantar el panel
python -m api.server
```

Abrir <http://127.0.0.1:8000>.

Opciones disponibles:

```bash
python -m api.server --host 0.0.0.0 --puerto 8080
```

---

## 4. Endpoints de la API

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/salud` | Comprobación de vida del servicio |
| GET | `/api/localidades` | Catálogo de las 20 localidades |
| GET | `/api/metricas` | MAE/RMSE del modelo y disponibilidad de artefactos |
| GET | `/api/dataset/resumen?localidad_id=` | Totales del dataset |
| GET | `/api/dataset/serie?localidad_id=&limite=` | Serie temporal para graficar |
| GET | `/api/dataset/ultimas?localidad_id=&cantidad=` | Últimas lecturas en tabla |
| GET | `/api/dataset/csv` | Descarga del dataset limpio |
| GET | `/api/lectura/actual?localidad_id=&entorno_interior=` | Lectura vigente + predicción |
| GET | `/api/lectura/live?localidad_id=` | Contenido y frescura de `latest.json` |
| GET | `/api/comparativa` | Estadísticas agregadas por localidad |
| POST | `/api/prediccion` | Predicción T+30 min desde valores del sensor |
| GET | `/api/colector/estado` | Estado del colector y puertos COM detectados |
| POST | `/api/colector/iniciar` | Arranca el colector (`real` o `simulacion`) |
| POST | `/api/colector/detener` | Detiene el colector |

Ejemplo de predicción:

```bash
curl -X POST http://127.0.0.1:8000/api/prediccion ^
  -H "Content-Type: application/json" ^
  -d "{\"temperatura\":13.5,\"humedad\":72,\"luz\":600,\"ruido\":45,\"localidad_id\":13}"
```

```json
{"localidad_id": 13, "localidad": "Teusaquillo", "temperatura_actual": 13.5,
 "luz_modelo": 600.0, "prediccion": 9.13, "delta": -4.37}
```

Todos los errores se devuelven con el mismo contrato:

```json
{"error": "humedad debe estar entre 30.0 y 100.0"}
```

- `400` — parámetro fuera de rango o cuerpo mal formado
- `404` — endpoint inexistente, o dataset/modelo no generados
- `500` — fallo inesperado (el detalle se registra en el log, no se expone)

---

## 5. Decisiones relevantes para el análisis estático

- **Sin `innerHTML`**: todo el DOM se construye con `createElement` y
  `textContent`, de modo que ningún dato de la API pueda inyectar marcado
  (evita los *security hotspots* de inyección en el cliente).
- **Sin `var` ni globales**: módulos ES con `import`/`export` y `const`/`let`.
- **Sin CSS ni JS embebidos** en el HTML: SonarQube analiza cada archivo por
  su lenguaje real.
- **Path traversal controlado**: `api/server.py` normaliza la ruta pedida y
  rechaza cualquier destino que salga de `web/`.
- **Límite de cuerpo**: las peticiones POST mayores a 64 KB se rechazan.
- **Cabeceras de seguridad**: `X-Content-Type-Options`, `X-Frame-Options` y
  `Referrer-Policy` en todas las respuestas.
- **Caché con TTL**: el dataset (259 200 filas) se relee solo si el CSV cambió
  y, como máximo, una vez cada 10 segundos, para que las escrituras continuas
  del colector no degraden el servidor.

---

## 6. Configuración de SonarQube

El archivo `sonar-project.properties` en la raíz declara:

```properties
sonar.sources=api,src,web
sonar.tests=tests
sonar.python.version=3.12
sonar.python.coverage.reportPaths=coverage.xml
sonar.exclusions=venv/**,models/**,data/**,htmlcov/**,**/__pycache__/**,docs/**
```

Para generar el reporte de cobertura antes del análisis:

```bash
pytest --cov --cov-report=xml
sonar-scanner
```

`app/streamlit_app.py` queda fuera de `sonar.sources` por ser el prototipo
sustituido por esta interfaz; basta con añadir `app` a la lista si se quiere
medir también.
