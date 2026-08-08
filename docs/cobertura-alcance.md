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
| `src/arduino_collector.py` | 191 | Interpretación, validación y persistencia (ver 2.3) |

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

### 2.3 Resuelto — la dependencia de hardware ya no bloquea

En la primera iteración, `leer_serial()` y `simular()` quedaban sin cubrir
porque abrían un puerto serie y corrían bucles indefinidos. **Nunca se
agregaron a `omit`**: se contaron como no cubiertas para que la deuda quedara
visible en el porcentaje en lugar de esconderse tras una exclusión.

Esa deuda se saldó refactorizando el módulo, no ampliando las exclusiones:

| Cambio | Efecto sobre la testabilidad |
|---|---|
| Se extrajo `parsear_lectura()` | La interpretación de la línea CSV era lógica pura atrapada dentro del bucle de hardware; ahora se prueba con cadenas de texto |
| El puerto serie se inyecta (`conexion=`) | `leer_serial()` corre contra un doble, sin hardware |
| El bucle admite cota (`max_lecturas=`) | Deja de ser indefinido y termina de forma determinista |
| `sys.exit()` → `ColectorError` | Una función de librería ya no mata el proceso que la llama; el punto de entrada traduce la excepción a código de salida |
| Se extrajo `sintetizar_lectura()` | La física del modo simulación se verifica con un generador aleatorio sembrado |

> **Ambigüedad detectada al probar.** Los rangos que desambiguan una línea de
> dos valores se solapan: `"25,50"` satisface a la vez el criterio de
> temperatura/humedad y el de luz/ruido, y el resultado depende del orden de
> las ramas. No estaba documentado ni decidido de forma explícita. Hoy
> `test_ante_dos_valores_ambiguos_se_prefiere_temperatura_y_humedad` fija ese
> contrato para que un reordenamiento accidental no lo cambie en silencio.

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

### Primera iteración — 217 pruebas

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

Las 110 sentencias sin cubrir eran, casi en su totalidad, `leer_serial()` y
`simular()`.

### Segunda iteración — 260 pruebas, tras el refactor de la sección 2.3

```
Name                         Stmts   Miss Branch BrPart    Cover
--------------------------------------------------------------------
src/arduino_collector.py       191      0     48      0  100.00%
src/data_processing.py          18      0      6      0  100.00%
src/feature_engineering.py      60      0     10      0  100.00%
src/localidades.py               4      0      0      0  100.00%
src/predict.py                  22      0      6      0  100.00%
--------------------------------------------------------------------
TOTAL                          295      0     70      0  100.00%
```

| Indicador | Línea base | 1.ª iteración | 2.ª iteración |
|---|---|---|---|
| Pruebas automatizadas | 0 | 217 | **260** |
| Cobertura total (líneas + ramas) | 0.00 % | 57.72 % | **100.00 %** |
| Cobertura del núcleo lógico | 0.00 % | 100.00 % | **100.00 %** |
| Sentencias sin cubrir | 266 | 110 | **0** |
| Ramas parciales | 0 | 1 | **0** |

El total de sentencias sube de 266 a 295 porque el refactor introdujo funciones
nuevas (`parsear_lectura`, `abrir_puerto`, `sintetizar_lectura`). La cifra
crece **y** queda totalmente cubierta: no se alcanzó el 100 % reduciendo el
denominador.

---

## 4. Meta y ruta de mejora

Umbral vigente: `fail_under = 95` en `pyproject.toml`. La meta del módulo era
**80 %** y quedó superada en la segunda iteración.

El umbral se fija en 95 y no en 100 de forma deliberada: un umbral exactamente
igual a la cobertura actual rompe la build ante cualquier línea nueva, incluso
legítima, y empuja al equipo a desactivarlo. 95 deja margen de maniobra sin
permitir que la cobertura se desplome.

Trabajo restante, en orden de costo-beneficio:

1. Refactorizar los tres scripts de la sección 2.2 (`generate_dataset`,
   `train_model`, `visualization`) con guarda `__main__` e incorporarlos al
   alcance. Es la última deuda de testabilidad conocida.
2. Medir **complejidad ciclomática** con `radon`, métrica que la guía asocia a
   JaCoCo y que `coverage.py` no calcula.
3. Evaluar `streamlit.testing.v1.AppTest` para la capa de presentación.

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
> cambio comparando la rama contra su base, así que esa métrica no existe si se
> hace *commit* directo sobre `main`. Desde el inicio del módulo todos los
> cambios entran mediante *pull requests*, y `codecov.yml` exige un 80 % de
> cobertura sobre el código nuevo de cada uno (verificación `patch`).
