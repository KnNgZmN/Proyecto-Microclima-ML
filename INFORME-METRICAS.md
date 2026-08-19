# Informe — Aplicación de métricas de ingeniería de software

**Proyecto:** Microclima Bogotá D.C. — Predicción de temperatura por localidad con ML + IoT
**Módulo:** Calidad y Métricas del Software — 8.º semestre
**Repositorio:** <https://github.com/KnNgZmN/Proyecto-Microclima-ML>

**Equipo:** María Alejandra Toro Ortiz · Mario Alejandro Peña Arenas · Yeisson Camilo Villamil Blandón · Omar Fernando Peña García · Iván Camilo García Urrego · Kevin Guzmán Acevedo

---

## 1. Resumen

Se tomó un proyecto funcional de 7.º semestre que **no tenía ninguna métrica de calidad aplicada** —ni pruebas automatizadas, ni análisis de seguridad, ni medición de complejidad— y se le implementaron tres de las siete áreas de la *Guía Integral de Métricas de Ingeniería y Herramientas*:

| # | Área de la guía | Herramientas |
|---|-----------------|--------------|
| 4 | Cobertura de pruebas | `coverage.py`, Vitest, Codecov |
| 5 | Seguridad del software (DevSecOps) | Snyk |
| 1 | Calidad de código y deuda técnica | SonarQube Cloud |

El resultado consolidado:

| Indicador | Antes | Ahora |
|-----------|------:|------:|
| Pruebas automatizadas | 0 | **635** |
| Cobertura del backend (líneas + ramas) | 0,00 % | **99,21 %** |
| Cobertura del front | sin medir | **98,93 %** |
| Vulnerabilidades en dependencias | 10 (8 altas) | **0** |
| Problemas en código propio (SAST) | 1 alta | **0** |
| Dependencias con versión fija | 0 | **52** |
| Complejidad ciclomática | sin medir | **524** |
| Deuda técnica | sin medir | **28 min** |
| Duplicación de código | sin medir | **0,0 %** |
| Verificaciones automáticas por cambio | 0 | **7** |

El proyecto pasó de 4 226 líneas de código sin verificar a tener **4 826 líneas de pruebas** que lo respaldan.

---

## 2. Punto de partida

El proyecto predice la temperatura a 30 minutos para las 20 localidades de Bogotá, combinando sensores Arduino con un modelo Random Forest. Funcionaba correctamente, pero:

- **No tenía una sola prueba automatizada.** Nadie podía saber qué parte del código estaba verificada.
- **Nunca se había auditado una dependencia.** Se declaraban 8 paquetes; el entorno real tenía 111.
- **No se había medido complejidad, duplicación ni deuda técnica.**

Es decir: un proyecto que *parecía* sano porque funcionaba, sin ninguna evidencia que lo respaldara.

### Criterio de selección de las métricas

Se evaluaron las siete áreas de la guía contra lo que el proyecto realmente tenía. Se descartaron las que no aplicaban: **DORA** (no hay despliegue continuo), **métricas ágiles** (no se trabaja con sprints formales) y **analítica de repositorios** (historial demasiado corto). Se escogió empezar por **cobertura de pruebas** porque era la única donde el equipo *produce* un artefacto verificable —la suite— en lugar de solo leer el tablero de una herramienta.

---

## 3. Métrica 4 — Cobertura de pruebas

### 3.1 Antes

Cero pruebas. Cero cobertura. 2 052 líneas de Python sin ninguna verificación automática.

### 3.2 La medición

Se midió la **línea base antes de escribir una sola prueba**, para poder documentar el cambio:

```
TOTAL   266 sentencias   266 sin cubrir   0.00%
```

Se activó cobertura de **ramas** además de líneas (`branch = true`), que es la métrica que exige la guía: un `if` cuyo `else` nunca se prueba cuenta como línea cubierta pero rama incompleta.

### 3.3 Errores hallados

**a) Tres módulos imposibles de importar.** `generate_dataset.py`, `train_model.py` y `visualization.py` ejecutan todo su cuerpo al importarse: les falta la guarda `if __name__ == "__main__"`.

> *Cómo afectaba:* una prueba que los importara dispararía la generación del dataset completo, un entrenamiento de varios minutos o la apertura de ventanas gráficas. No son módulos: son procedimientos disfrazados de módulos.

**b) Lógica de dominio atrapada tras el hardware.** La función `leer_serial()` mezclaba **siete responsabilidades**: abrir el puerto serie, leer, interpretar la línea CSV, validar rangos, guardar, predecir y esperar. La interpretación —decidir si dos números son temperatura/humedad o luz/ruido— es lógica pura, pero era inalcanzable porque vivía después de `serial.Serial()` dentro de un `while True`.

> *Cómo afectaba:* `arduino_collector.py` quedó al **30,81 %**. Y esa lógica es la que decide cómo se interpretan los datos que alimentan el modelo.

**c) Una ambigüedad real, descubierta al intentar probar.** Los rangos que desambiguan una línea de dos valores **se solapan**: la entrada `"25,50"` satisface a la vez el criterio de temperatura/humedad y el de luz/ruido. El resultado dependía del orden de los `if`, sin que estuviera documentado ni decidido.

**d) Un fallo que solo aparecía en el servidor.** `pyproject.toml` declaraba `pythonpath = ["src"]` sin la raíz del proyecto. En las máquinas del equipo funcionaba porque `python -m pytest` agrega el directorio actual al `sys.path`; el ejecutable `pytest` que corre en CI **no lo hace**, y fallaba con `ModuleNotFoundError: No module named 'api'`.

### 3.4 Cómo se mejoró

La deuda del colector **no se saldó ampliando las exclusiones, sino refactorizando**:

| Cambio | Efecto |
|--------|--------|
| Extraer `parsear_lectura()` | La interpretación de la línea sale del bucle y pasa a ser una función pura |
| Inyectar el puerto serie como parámetro | Se puede sustituir por un doble en pruebas |
| Acotar el bucle (`max_lecturas`) | Deja de ser infinito |
| `sys.exit()` → `ColectorError` | Una función de librería no debe matar el proceso que la llama |
| Extraer `sintetizar_lectura()` | La física del modo simulación se vuelve verificable |

El detalle que importa: las sentencias medidas **subieron de 266 a 295** y aun así se llegó al 100 %. No se llegó ahí reduciendo el denominador.

La ambigüedad de la entrada `"25,50"` quedó fijada por una prueba que documenta explícitamente cuál de las dos interpretaciones gana.

Después se sumó el **front web** (JavaScript), que estaba completamente fuera de la medición. Se cubrió con Vitest en tres iteraciones: 9,05 % → 46,71 % → **98,93 %**.

### 3.5 Después

| | Backend (Python) | Front (JavaScript) |
|---|---:|---:|
| Pruebas | 376 | 259 |
| Cobertura | **99,21 %** | **98,93 %** |
| Sentencias medidas | 825 | 563 |

**Umbrales de regresión.** `fail_under` en `pyproject.toml` y `thresholds` en `vitest.config.js` rompen la build si la cobertura cae. El criterio: **el umbral va por debajo de la cifra real y solo sube cuando la cobertura ya lo superó de forma estable**. Historial: 55 → 95 → 99.

Cada umbral se **verificó rompiéndolo a propósito** antes de darlo por bueno.

---

## 4. Métrica 5 — Seguridad del software (Snyk)

### 4.1 Antes

Ninguna dependencia se había auditado nunca. El manifiesto declaraba 8 paquetes; el entorno tenía 111.

### 4.2 La medición

Los **dos primeros escaneos fallaron**, antes de ver un solo hallazgo:

```
ERROR  Missing required packages (SNYK-OS-PYTHON-0013)
Status: 422 Unprocessable Entity
```

### 4.3 Errores hallados

**a) No se podía auditar nada.** Todas las dependencias estaban declaradas con rango abierto (`pandas>=1.5.0`). Sin versiones exactas no hay un árbol determinista que comparar contra la base de CVE.

> *Cómo afectaba:* dos integrantes del equipo podían estar ejecutando versiones distintas del mismo paquete sin saberlo. **No se puede auditar lo que no está fijado.**

**b) El entorno no coincidía con el manifiesto.** `streamlit`, `streamlit-autorefresh` y `pyserial` estaban declarados pero **no instalados**: la aplicación web no podía ejecutarse. Al instalarlos, el árbol pasó de 18 a **52 paquetes**, casi el triple de superficie de ataque de la que se veía al empezar.

**c) Diez vulnerabilidades, ocho de severidad alta**, todas en `pillow@12.2.0`:

| Tipo | Cantidad | Qué permite |
|------|---------:|-------------|
| Memory Allocation with Excessive Size Value | 4 | Una imagen manipulada pide memoria sin límite |
| Out-of-bounds Write | 2 | Escribir fuera del espacio reservado |
| Out-of-bounds Read | 1 | Leer memoria que no corresponde |
| Allocation of Resources Without Limits | 1 | Agotar los recursos de la máquina |
| Infinite loop | 1 | Una imagen que nunca termina de procesarse |
| Command Injection | 1 | Ejecutar comandos del sistema |

> **El hallazgo más importante del proyecto:** `pillow` **no estaba en `requirements.txt`**. Lo arrastra `matplotlib`, que declara `pillow>=9`. Se pidió una librería de gráficas y llegó, sin que nadie lo eligiera, un decodificador de imágenes con ocho vulnerabilidades altas. De las 52 dependencias, solo **8 fueron decisión del equipo**; las otras 44 son heredadas.

**d) Un falso positivo de severidad alta.** Snyk Code reportó un *Path Traversal* en el servidor de archivos estáticos. La sanitización era correcta —normalizaba, descartaba `..`, resolvía con `realpath` y exigía contención—; se probaron **10 payloads** (codificados, con separadores de Windows, con puntos duplicados, saliendo desde subdirectorios válidos) y los 10 quedaron bloqueados. El analizador no sabe seguir una comprobación basada en `realpath()` + `startswith()`.

**e) El CI fallaba por dos razones distintas.** Primero, el token registrado no tenía permiso para Snyk Code (403 `Forbidden`) aunque sí autenticaba para dependencias. Segundo, **Snyk inspecciona el entorno instalado, no el archivo declarado**: en el servidor no había nada instalado y reaparecía el error del paso 4.2.

### 4.4 Cómo se mejoró

**Se generó `requirements.lock`** con el cierre transitivo resuelto y versiones exactas. `requirements.txt` sigue siendo el manifiesto editable; el `.lock` es lo que se audita.

**Se corrigió `pillow` y se fijó la restricción en el manifiesto:**

```
# pillow lo introduce matplotlib (pillow>=9). La 12.2.0 acumulaba
# 10 CVE, 8 de severidad alta. Corregidas en 12.3.0.
pillow>=12.3.0
```

Actualizar el paquete arregla el problema de hoy; fijarlo evita que vuelva mañana. Sin esa restricción, una instalación futura podría volver a resolver la versión vulnerable. **Se fija una dependencia que el proyecto no usa directamente, solo por seguridad.**

**El falso positivo no se silenció: se eliminó la causa.** Primero se intentó declararlo en `.snyk`, pero ese archivo solo aplica a Snyk Open Source —Snyk Code lo ignoró por completo (`Ignored issues: 0`)—. Las alternativas restantes (bajar el umbral, excluir el archivo, tapar la salida) debilitaban el control para *todo* el código.

Se reescribió la resolución de archivos estáticos: ahora se sirven desde un **catálogo** `{ruta_url → ruta_absoluta}` que el servidor construye recorriendo el directorio. La ruta que llega a `open()` sale siempre de ese catálogo, nunca de la petición. El *path traversal* deja de ser algo que *se comprueba* y pasa a ser **imposible por construcción**. La cobertura incluso subió con el cambio: 98,99 % → 99,21 %.

### 4.5 Después

```
snyk test --file=requirements.lock   →  52 dependencias, 0 vulnerabilidades
snyk code test                       →  Total issues: 0
```

El análisis corre en cada cambio **y todos los lunes**: un CVE puede publicarse sin que el código cambie, así que debe repetirse por calendario. El proyecto está además en monitoreo continuo con aviso por correo.

---

## 5. Métrica 1 — Calidad de código y deuda técnica (SonarQube)

### 5.1 Antes

Nunca se había medido complejidad, duplicación ni deuda técnica. Era además el hueco declarado desde la primera exposición: la guía asocia la **complejidad ciclomática** a JaCoCo, y `coverage.py` no la calcula.

### 5.2 La medición

Primer análisis: **12 vulnerabilidades** y calificación de seguridad **C**, con mantenibilidad y fiabilidad en A.

### 5.3 Errores hallados

**a) Doce vulnerabilidades.** Eran variantes del mismo flujo de *path traversal* que Snyk había señalado, detectadas con reglas distintas.

**b) Cobertura reportada incoherente.** Sonar decía **88,7 %** donde `pytest` y Vitest reportaban ~99 %. La causa: `sonar.sources` incluía los tres scripts sin guarda `__main__` que `coverage.py` omite por no ser importables, y los contaba como no cubiertos.

> *Cómo afectaba:* dos herramientas reportando cifras distintas sobre el mismo código, sin que nadie supiera cuál creer.

**c) Dos trampas de configuración.** La clave de la organización va en minúsculas (`knngzmn`) pero la del proyecto conserva las mayúsculas (`KnNgZmN_...`); equivocarlas rompe el análisis. Y el «Automatic Analysis» viene activo por defecto y **choca** con el análisis lanzado desde CI, que falla mientras ambos coexistan.

### 5.4 Cómo se mejoró

**Las 12 vulnerabilidades se cerraron de golpe** con el refactor del servidor de estáticos hecho para Snyk. No hubo que revisarlas una por una, y la calificación de seguridad subió de **C a A**.

> Es un buen argumento a favor de tener varias herramientas midiendo: Snyk y SonarQube aplican reglas distintas sobre el mismo código, pero una sola corrección estructural resolvió lo que ambas señalaban.

**Se alinearon los alcances.** `sonar.coverage.exclusions` pasó a coincidir con el bloque `omit` de `pyproject.toml`: los tres scripts se siguen **analizando** —sus *code smells* y su complejidad sí cuentan— pero no se les exige cobertura. La cifra pasó de 88,7 % a **99,0 %**, coherente con las herramientas propias.

### 5.5 Después

| Métrica | Valor | Calificación |
|---------|------:|:------------:|
| Líneas analizadas | 3 251 | — |
| Bugs | **0** | **A** |
| Vulnerabilidades | **0** | **A** |
| Puntos calientes de seguridad | **0** | — |
| *Code smells* | 3 | **A** |
| Deuda técnica | 28 min | — |
| Duplicación | **0,0 %** | — |
| Complejidad ciclomática | 524 | — |
| Complejidad cognitiva | 303 | — |
| Cobertura | 99,0 % | — |

---

## 6. Automatización

Ninguna de las tres métricas depende de que alguien recuerde ejecutarla. Cada cambio dispara **siete verificaciones**:

| Verificación | Qué controla |
|--------------|--------------|
| `pytest + coverage` | 376 pruebas, umbral 99 % |
| `vitest + coverage` | 259 pruebas, umbral 98 % |
| `SonarQube Cloud` | Calidad, complejidad y deuda |
| `Snyk Open Source` | CVE en las 52 dependencias |
| `Snyk Code` | Análisis estático del código propio |
| `Codecov` | Histórico y *diff coverage* |
| `GitGuardian` | Fugas de credenciales |

Si alguna falla, el Pull Request queda bloqueado.

---

## 7. Lecciones

**No se puede auditar lo que no está fijado.** Con dependencias en rango abierto, Snyk no pudo ni empezar. El primer obstáculo llegó antes que cualquier hallazgo.

**El riesgo está en lo que no elegiste.** Las 10 vulnerabilidades estaban en un paquete que nadie escribió jamás en el manifiesto. De 52 dependencias, 44 son heredadas y nadie las revisa manualmente.

**Medir cobertura revela problemas de diseño.** Cuando algo es difícil de probar, casi siempre es porque mezcla responsabilidades. La cobertura no solo mide: funciona como detector de acoplamiento.

**Una prueba verde puede no verificar nada.** Ocurrió dos veces: un doble que conservaba llamadas entre pruebas hacía pasar una aserción sobre la invocación equivocada, y unos temporizadores falsos instalados después del arranque dejaban la prueba del refresco automático sin ejercitar el intervalo.

**Un falso positivo no se ignora ni se obedece: se verifica.** Ante el *path traversal*, la respuesta profesional no fue silenciarlo ni «arreglar» a ciegas, sino comprobar con 10 payloads y luego eliminar la causa de raíz.

**Configurar un control no es lo mismo que verificarlo.** Cada umbral se comprobó rompiéndolo a propósito antes de darlo por bueno.

**Las herramientas deben medir el mismo alcance.** Codecov y `coverage.py` primero, SonarQube y `pyproject.toml` después: cada vez que dos herramientas midieron alcances distintos, las cifras dejaron de ser comparables.

---

## 8. Cómo reproducir las mediciones

```bash
# Cobertura — backend
pip install -r requirements.txt -r requirements-dev.txt
pytest --cov --cov-branch --cov-report=term-missing

# Cobertura — front
npm install
npm run coverage

# Seguridad
snyk auth
snyk test --file=requirements.lock --package-manager=pip
snyk code test
```

**Paneles públicos:**

- Cobertura: <https://codecov.io/gh/KnNgZmN/Proyecto-Microclima-ML>
- Calidad: <https://sonarcloud.io/summary/new_code?id=KnNgZmN_Proyecto-Microclima-ML>

La documentación técnica completa está en el [README](README.MD), secciones 24 a 28, y el alcance detallado de la medición en [docs/cobertura-alcance.md](docs/cobertura-alcance.md).
