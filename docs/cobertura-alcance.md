# Cobertura de Pruebas — Definición de Alcance y Línea Base

Documento de referencia para el módulo de **Calidad y Métricas del Software**.
Corresponde a la **sección 4 (Cobertura de Pruebas)** de la *Guía Integral de
Métricas de Ingeniería y Herramientas*.

Fecha de la medición inicial: **2026-07-28**

---

## 1. Mapeo de herramientas

La tabla de la sección 4 de la guía lista JaCoCo (Java/JVM), Istanbul/c8
(JS/TS), Codecov y Coveralls. El proyecto está escrito en **Python 3.13**, por
lo que las dos primeras no aplican. Equivalencias adoptadas:

| Herramienta de la guía | Equivalente adoptado | Rol |
|---|---|---|
| JaCoCo / Istanbul | `coverage.py` + `pytest-cov` | Motor de medición local (líneas y ramas) |
| Codecov | Codecov | Histórico, *diff coverage* e impacto de PRs |
| Coveralls | *(alternativa a Codecov, no usada)* | — |

Métricas producidas, alineadas con las que nombra la guía:

- **Cobertura de líneas** (*statements*)
- **Cobertura de ramas** (*branches*) — activada con `branch = true`
- **Cobertura histórica** y **diff coverage** — vía Codecov sobre los PRs
- **Alerta por caída** — `fail_under` en `pyproject.toml` rompe la build

---

## 2. Alcance de medición

`source = ["src"]` en `pyproject.toml`. La aplicación Streamlit y los scripts
de ejecución quedan fuera. Justificación de cada exclusión:

### 2.1 Dentro del alcance

| Módulo | Sentencias | Justificación |
|---|---|---|
| `src/data_processing.py` | 18 | Funciones puras de saneamiento |
| `src/feature_engineering.py` | 60 | Lógica de derivación de features del modelo |
| `src/localidades.py` | 4 | Catálogo de datos; se valida su integridad |
| `src/predict.py` | 22 | Inferencia; el modelo se sustituye por un doble |
| `src/arduino_collector.py` | 162 | Validación y persistencia (parcial, ver 2.3) |

### 2.2 Excluido — scripts de ejecución (`omit` en `pyproject.toml`)

`generate_dataset.py`, `train_model.py` y `visualization.py` **ejecutan todo su
cuerpo a nivel de módulo**: no tienen guarda `if __name__ == "__main__"`. Basta
con importarlos desde una prueba para que se dispare, respectivamente, la
generación del dataset completo (20 localidades × 90 días), el entrenamiento de
un RandomForest con validación cruzada, o la apertura de ventanas de
matplotlib.

> **Hallazgo de testabilidad.** Esta es una deuda técnica real que el ejercicio
> de cobertura hizo visible. Refactorizar cada script a `def main():` + guarda
> `__main__` los volvería importables y permitiría probar sus funciones
> internas — en particular `_generar_localidad()`, que es determinista
> (`RandomState(42 + localidad_id)`) y por tanto perfectamente testeable.

### 2.3 Excluido de facto — dependencia de hardware

Dentro de `arduino_collector.py`, las funciones `leer_serial()` (líneas
140-242) y `simular()` (250-302) abren un puerto serie y corren bucles
indefinidos. **No están en la lista `omit`**: se cuentan como no cubiertas y
penalizan el porcentaje deliberadamente, para que la deuda quede visible en la
métrica en lugar de esconderse tras una exclusión.

### 2.4 Excluido — capa de presentación

`app/streamlit_app.py` (828 líneas) es interfaz de usuario. Cubrirla exigiría
`streamlit.testing.v1.AppTest`, cuyo costo excede el alcance del módulo.

---

## 3. Línea base

### Antes de la intervención

Medición con **cero pruebas** en el repositorio:

```
Name                         Stmts   Miss Branch BrPart  Cover
------------------------------------------------------------------
src/arduino_collector.py       162    162     36      0   0.00%
src/data_processing.py          18     18      6      0   0.00%
src/feature_engineering.py      60     60     10      0   0.00%
src/localidades.py               4      4      0      0   0.00%
src/predict.py                  22     22      6      0   0.00%
------------------------------------------------------------------
TOTAL                          266    266     58      0   0.00%
```

### Después de la primera iteración — 217 pruebas

```
Name                         Stmts   Miss Branch BrPart   Cover
-------------------------------------------------------------------
src/arduino_collector.py       162    110     36      1  30.81%
src/data_processing.py          18      0      6      0 100.00%
src/feature_engineering.py      60      0     10      0 100.00%
src/localidades.py               4      0      0      0 100.00%
src/predict.py                  22      0      6      0 100.00%
-------------------------------------------------------------------
TOTAL                          266    110     58      1  57.72%
```

| Indicador | Antes | Después |
|---|---|---|
| Pruebas automatizadas | 0 | 217 |
| Cobertura total (líneas + ramas) | 0.00 % | **57.72 %** |
| Cobertura del núcleo lógico | 0.00 % | **100.00 %** |
| Sentencias sin cubrir | 266 | 110 |

Las 110 sentencias sin cubrir son, casi en su totalidad, `leer_serial()` y
`simular()`.

---

## 4. Meta y ruta de mejora

Umbral vigente: `fail_under = 55` en `pyproject.toml`. **Meta del módulo: 80 %.**

Para alcanzarla, en orden de costo-beneficio:

1. Sustituir `pyserial` por un doble e invocar `leer_serial()` con un flujo de
   líneas simuladas → recupera ~100 sentencias, el mayor salto disponible.
2. Cubrir `simular()` acotando `n_lecturas` e inyectando el intervalo.
3. Refactorizar los tres scripts de la sección 2.2 e incorporarlos al alcance.
4. Elevar `fail_under` tras cada avance para que la métrica no retroceda.

---

## 5. Ejecución

```bash
pip install -r requirements-dev.txt

pytest                                   # solo pruebas
pytest --cov --cov-report=term-missing   # cobertura en consola
pytest --cov --cov-report=html           # reporte navegable en htmlcov/
```

En cada `push` y cada *pull request* a `main`, el workflow
`.github/workflows/tests.yml` repite la medición, publica el resultado en
Codecov y adjunta el HTML como artefacto.

> **Requisito para el *diff coverage*.** Codecov calcula el impacto de un
> cambio comparando la rama contra su base. El equipo venía haciendo *commit*
> directo sobre `main`, donde esa métrica no existe. Para que la sección 4 se
> pueda reportar completa, los cambios del módulo deben entrar mediante *pull
> requests*.
