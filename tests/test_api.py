"""Pruebas del backend HTTP (paquete api/).

Ninguna prueba depende de data/raw/data.csv ni de models/model.pkl: el dataset
se construye en un directorio temporal y el modelo se sustituye por el doble
compartido en conftest.py, igual que hacen las pruebas de src/.
"""

import json
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta

import pandas as pd
import pytest

from api import colector, config, repositorio, rutas, server, servicios
from api.rutas import Peticion
from api.servicios import SolicitudInvalida

LOCALIDADES_PRUEBA = [(13, "Teusaquillo"), (1, "Usaquén")]
FILAS_POR_LOCALIDAD = 8


def _dataset() -> pd.DataFrame:
    """Dataset mínimo con dos localidades intercaladas."""
    marcas = pd.date_range("2025-03-10 08:00", periods=FILAS_POR_LOCALIDAD, freq="10min")
    filas = []
    for indice, marca in enumerate(marcas):
        for desplazamiento, (lid, nombre) in enumerate(LOCALIDADES_PRUEBA):
            filas.append({
                "timestamp": marca,
                "localidad_id": lid,
                "localidad": nombre,
                "temperatura": 12.0 + indice * 0.5 + desplazamiento,
                "humedad": 70.0 + indice,
                "luz": 100 + indice * 10,
                "ruido": 45 + indice,
            })
    return pd.DataFrame(filas)


@pytest.fixture
def entorno(tmp_path, monkeypatch, modelo_falso):
    """Aísla rutas de archivos, cachés y modelo para cada prueba."""
    csv = tmp_path / "data.csv"
    _dataset().to_csv(csv, index=False)

    metricas = tmp_path / "metrics.json"
    metricas.write_text(json.dumps({"mae_cv_mean": 1.0, "n_features": 19}), encoding="utf-8")

    live = tmp_path / "latest.json"

    monkeypatch.setattr(config, "DATA_PATH", str(csv))
    monkeypatch.setattr(config, "METRICS_PATH", str(metricas))
    monkeypatch.setattr(config, "LIVE_PATH", str(live))
    monkeypatch.setattr(config, "MODEL_PATH", str(tmp_path / "model.pkl"))

    repositorio._cache_dataset.update({"mtime": None, "df": None, "verificado_en": 0.0})
    repositorio._cache_modelo.update({"mtime": None, "modelo": None})

    monkeypatch.setattr(repositorio, "hay_modelo", lambda: True)
    monkeypatch.setattr(repositorio, "cargar_modelo", lambda: modelo_falso)

    return {"csv": csv, "live": live, "modelo": modelo_falso, "tmp": tmp_path}


def _escribir_live(ruta, segundos_atras: int = 2, localidad_id: int = 13, prediccion=14.0):
    """Publica un latest.json con la antigüedad indicada."""
    marca = datetime.now() - timedelta(seconds=segundos_atras)
    ruta.write_text(json.dumps({
        "timestamp": marca.strftime(config.FORMATO_TS),
        "localidad_id": localidad_id,
        "localidad": "Teusaquillo",
        "temperatura": 15.5,
        "humedad": 80.0,
        "luz": 120,
        "ruido": 50,
        "prediccion": prediccion,
    }), encoding="utf-8")


# ---------------------------------------------------------------------------
# servicios
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(("luz", "hora", "esperado"), [
    (100.0, 12, 350.0),   # diurno: escala por 3.5
    (100.0, 3, 100.0),    # nocturno: sin cambios
    (900.0, 10, 1000.0),  # tope máximo del rango exterior
])
def test_escalar_luz_interior(luz, hora, esperado):
    assert servicios.escalar_luz_interior(luz, hora) == esperado


def test_listar_localidades_devuelve_catalogo_ordenado():
    catalogo = servicios.listar_localidades()
    assert len(catalogo) == 20
    assert [loc["id"] for loc in catalogo] == sorted(loc["id"] for loc in catalogo)
    assert catalogo[0]["nombre"] == "Usaquén"


def test_obtener_localidad_sin_id_usa_la_de_defecto():
    assert servicios.obtener_localidad(None)["nombre"] == "Teusaquillo"


def test_obtener_localidad_invalida_es_solicitud_invalida():
    with pytest.raises(SolicitudInvalida):
        servicios.obtener_localidad(99)


def test_metricas_modelo_expone_disponibilidad(entorno):
    datos = servicios.metricas_modelo()
    assert datos["metricas"]["n_features"] == 19
    assert datos["hay_dataset"] is True


def test_resumen_dataset_cuenta_global_y_por_localidad(entorno):
    resumen = servicios.resumen_dataset(13)
    assert resumen["registros"] == FILAS_POR_LOCALIDAD * len(LOCALIDADES_PRUEBA)
    assert resumen["registros_localidad"] == FILAS_POR_LOCALIDAD
    assert resumen["localidades"] == 2
    assert resumen["tiene_localidades"] is True


def test_serie_temporal_respeta_el_limite(entorno):
    serie = servicios.serie_temporal(13, limite=3)
    assert len(serie["puntos"]) == 3
    assert set(serie["puntos"][0]) == {"timestamp", "temperatura", "humedad", "luz", "ruido"}


def test_ultimas_lecturas_van_de_la_mas_nueva_a_la_mas_antigua(entorno):
    datos = servicios.ultimas_lecturas(13, cantidad=3)
    marcas = [fila["timestamp"] for fila in datos["filas"]]
    assert marcas == sorted(marcas, reverse=True)
    assert "localidad" in datos["columnas"]


def test_comparativa_ordena_por_temperatura_media(entorno):
    datos = servicios.comparativa()
    medias = [fila["temp_media"] for fila in datos["filas"]]
    assert datos["disponible"] is True
    assert medias == sorted(medias)


def test_comparativa_sin_columna_de_localidad(entorno, monkeypatch):
    sin_localidad = _dataset().drop(columns=["localidad_id", "localidad"])
    monkeypatch.setattr(repositorio, "cargar_dataset", lambda: sin_localidad)
    assert servicios.comparativa() == {"disponible": False, "filas": []}


def test_lectura_actual_usa_el_dataset_cuando_no_hay_live(entorno):
    actual = servicios.lectura_actual(13)
    assert actual["origen"] == "dataset"
    assert actual["prediccion"] == pytest.approx(entorno["modelo"].valor)


def test_lectura_actual_prefiere_el_arduino_reciente(entorno):
    _escribir_live(entorno["live"])
    actual = servicios.lectura_actual(13)
    assert actual["origen"] == "arduino"
    assert actual["prediccion"] == 14.0  # la publicada por el colector


def test_lectura_actual_recalcula_en_entorno_interior(entorno):
    _escribir_live(entorno["live"])
    actual = servicios.lectura_actual(13, entorno_interior=True)
    assert actual["prediccion"] == pytest.approx(entorno["modelo"].valor)
    assert actual["luz_modelo"] >= 120


def test_lectura_actual_sin_datos_para_la_localidad(entorno):
    actual = servicios.lectura_actual(20)
    assert actual["origen"] == "sin_datos"
    assert actual["lectura"] is None


def test_estado_live_marca_como_no_vigente_lo_antiguo(entorno):
    _escribir_live(entorno["live"], segundos_atras=config.FRESCURA_LIVE_S + 30)
    estado = servicios.estado_live(13)
    assert estado["disponible"] is True
    assert estado["vigente"] is False


def test_estado_live_sin_archivo(entorno):
    assert servicios.estado_live() == {
        "disponible": False, "lectura": None, "antiguedad_s": None, "vigente": False,
    }


def test_predecir_devuelve_delta_frente_a_la_temperatura_actual(entorno):
    resultado = servicios.predecir({
        "temperatura": 13.5, "humedad": 72, "luz": 600, "ruido": 45,
        "hora": 14, "mes": 8, "localidad_id": 13,
    })
    assert resultado["prediccion"] == pytest.approx(entorno["modelo"].valor)
    assert resultado["delta"] == pytest.approx(entorno["modelo"].valor - 13.5)
    assert resultado["localidad"] == "Teusaquillo"


def test_predecir_usa_el_historial_enviado_por_el_front(entorno):
    servicios.predecir({
        "temperatura": 13.5, "humedad": 72, "luz": 600, "ruido": 45,
        "historia": [{"temperatura": 12.0, "humedad": 70.0},
                     {"temperatura": 12.5, "humedad": 71.0}],
    })
    features = entorno["modelo"].X_recibido
    assert features["temp_prom_30m"].iloc[0] != 13.5


def test_predecir_usa_el_historial_del_dataset(entorno):
    servicios.predecir({
        "temperatura": 13.5, "humedad": 72, "luz": 600, "ruido": 45,
        "localidad_id": 13, "usar_historial_dataset": True,
    })
    assert entorno["modelo"].n_llamadas == 1


def test_predecir_escala_la_luz_en_entorno_interior(entorno):
    resultado = servicios.predecir({
        "temperatura": 13.5, "humedad": 72, "luz": 100, "ruido": 45,
        "hora": 12, "entorno_interior": True,
    })
    assert resultado["luz_modelo"] == 350


@pytest.mark.parametrize("datos", [
    {"humedad": 72, "luz": 600, "ruido": 45},                       # falta temperatura
    {"temperatura": 99, "humedad": 72, "luz": 600, "ruido": 45},    # fuera de rango
    {"temperatura": "x", "humedad": 72, "luz": 600, "ruido": 45},   # no numérico
])
def test_predecir_rechaza_entradas_invalidas(entorno, datos):
    with pytest.raises(SolicitudInvalida):
        servicios.predecir(datos)


def test_predecir_sin_modelo_entrenado(entorno, monkeypatch):
    monkeypatch.setattr(repositorio, "hay_modelo", lambda: False)
    with pytest.raises(SolicitudInvalida):
        servicios.predecir({"temperatura": 13.5, "humedad": 72, "luz": 600, "ruido": 45})


def test_dataset_csv_incluye_encabezado(entorno):
    contenido = servicios.dataset_csv().decode("utf-8")
    assert contenido.splitlines()[0].startswith("timestamp")


# ---------------------------------------------------------------------------
# repositorio
# ---------------------------------------------------------------------------

def test_cargar_dataset_reutiliza_la_cache(entorno):
    primero = repositorio.cargar_dataset()
    assert repositorio.cargar_dataset() is primero


def test_cargar_dataset_relee_cuando_cambia_el_csv(entorno, monkeypatch):
    repositorio.cargar_dataset()
    repositorio._cache_dataset["verificado_en"] = 0.0  # fuerza la comprobación de mtime
    monkeypatch.setattr(repositorio, "_mtime", lambda _ruta: 1.0)
    assert len(repositorio.cargar_dataset()) == FILAS_POR_LOCALIDAD * len(LOCALIDADES_PRUEBA)


def test_cargar_dataset_sin_archivo(entorno, monkeypatch):
    monkeypatch.setattr(config, "DATA_PATH", str(entorno["tmp"] / "inexistente.csv"))
    with pytest.raises(FileNotFoundError):
        repositorio.cargar_dataset()


def test_cargar_modelo_sin_archivo(entorno, monkeypatch):
    monkeypatch.undo()
    monkeypatch.setattr(config, "MODEL_PATH", str(entorno["tmp"] / "sin_modelo.pkl"))
    with pytest.raises(FileNotFoundError):
        repositorio.cargar_modelo()


def test_leer_json_corrupto_devuelve_none(entorno):
    entorno["live"].write_text("{ esto no es json", encoding="utf-8")
    assert repositorio.leer_live() is None


def test_segundos_desde_calcula_la_antiguedad():
    hace_un_minuto = (datetime.now() - timedelta(seconds=60)).strftime(config.FORMATO_TS)
    assert repositorio.segundos_desde(hace_un_minuto) >= 59


# ---------------------------------------------------------------------------
# colector
# ---------------------------------------------------------------------------

class ProcesoFalso:
    """Doble de subprocess.Popen que no lanza ningún proceso real."""

    def __init__(self, comando, stdout=None, stderr=None):
        self.comando = comando
        self.pid = 4321
        self.terminado = False
        self.codigo = None
        self.stderr = None

    def poll(self):
        return self.codigo

    def terminate(self):
        self.terminado = True
        self.codigo = 0


@pytest.fixture
def colector_limpio(monkeypatch):
    """Reinicia el estado del colector y evita lanzar procesos reales."""
    colector._estado.update({"proceso": None, "modo": None, "localidad_id": None, "error": None})
    monkeypatch.setattr(colector, "listar_puertos", list)
    creados = []

    def popen_falso(comando, stdout=None, stderr=None):
        proceso = ProcesoFalso(comando, stdout, stderr)
        creados.append(proceso)
        return proceso

    monkeypatch.setattr(colector.subprocess, "Popen", popen_falso)
    yield creados
    colector._estado.update({"proceso": None, "modo": None, "localidad_id": None, "error": None})


def test_iniciar_simulacion_arma_el_comando_esperado(colector_limpio):
    estado = colector.iniciar(colector.MODO_SIMULACION, "COM3", 9600, 13)
    comando = colector_limpio[0].comando
    assert estado["activo"] is True
    assert "--simulate" in comando
    assert "--predict" in comando
    assert "--port" not in comando


def test_iniciar_modo_real_pasa_puerto_y_baudios(colector_limpio):
    colector.iniciar(colector.MODO_REAL, "COM7", 115200, 1)
    comando = colector_limpio[0].comando
    assert comando[comando.index("--port") + 1] == "COM7"
    assert comando[comando.index("--baud") + 1] == "115200"


def test_iniciar_dos_veces_es_solicitud_invalida(colector_limpio):
    colector.iniciar(colector.MODO_SIMULACION, "COM3", 9600, 13)
    with pytest.raises(SolicitudInvalida):
        colector.iniciar(colector.MODO_SIMULACION, "COM3", 9600, 13)


def test_iniciar_con_modo_desconocido(colector_limpio):
    with pytest.raises(SolicitudInvalida):
        colector.iniciar("otro", "COM3", 9600, 13)


def test_iniciar_rechaza_puerto_no_detectado(colector_limpio, monkeypatch):
    monkeypatch.setattr(colector, "listar_puertos", lambda: ["COM5"])
    with pytest.raises(SolicitudInvalida):
        colector.iniciar(colector.MODO_REAL, "COM3", 9600, 13)


def test_detener_libera_el_proceso(colector_limpio):
    colector.iniciar(colector.MODO_SIMULACION, "COM3", 9600, 13)
    estado = colector.detener()
    assert estado["activo"] is False
    assert colector_limpio[0].terminado is True


def test_estado_reporta_error_de_proceso_caido(colector_limpio):
    colector.iniciar(colector.MODO_REAL, "COM3", 9600, 13)
    colector_limpio[0].codigo = 1
    estado = colector.estado()
    assert estado["activo"] is False
    assert "código 1" in estado["error"]


def test_listar_puertos_tolera_ausencia_de_pyserial(monkeypatch):
    assert isinstance(colector.listar_puertos(), list)


# ---------------------------------------------------------------------------
# rutas
# ---------------------------------------------------------------------------

def test_peticion_entero_valido_e_invalido():
    peticion = Peticion("GET", "/api/x", {"n": "5", "malo": "abc"}, {})
    assert peticion.entero("n") == 5
    assert peticion.entero("ausente", 7) == 7
    with pytest.raises(SolicitudInvalida):
        peticion.entero("malo")


@pytest.mark.parametrize(("valor", "esperado"), [("1", True), ("true", True),
                                                 ("sí", True), ("0", False), ("", False)])
def test_peticion_booleano(valor, esperado):
    assert Peticion("GET", "/api/x", {"f": valor}, {}).booleano("f") is esperado


def test_peticion_acotado_limita_el_maximo():
    peticion = Peticion("GET", "/api/x", {"limite": "9999"}, {})
    assert peticion.acotado("limite", 10, 100) == 100
    with pytest.raises(SolicitudInvalida):
        Peticion("GET", "/api/x", {"limite": "0"}, {}).acotado("limite", 10, 100)


def test_resolver_devuelve_none_para_rutas_desconocidas():
    assert rutas.resolver("GET", "/api/inexistente") is None
    assert rutas.resolver("GET", "/api/salud") is not None


def test_ruta_de_localidad_valida_el_identificador(entorno):
    with pytest.raises(SolicitudInvalida):
        rutas.resolver("GET", "/api/dataset/resumen")(
            Peticion("GET", "/api/dataset/resumen", {"localidad_id": "77"}, {}),
        )


# ---------------------------------------------------------------------------
# server
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ruta", ["/../pyproject.toml", "/..%2fpyproject.toml", "/no-existe.html"])
def test_ruta_estatica_rechaza_salidas_del_directorio_web(ruta):
    assert server._ruta_estatica(ruta) is None


def test_ruta_estatica_resuelve_el_indice():
    assert server._ruta_estatica("/").endswith("index.html")


def test_params_aplana_la_cadena_de_consulta():
    assert server._params("a=1&b=2&b=3") == {"a": "1", "b": "2"}


@pytest.fixture
def servidor(entorno):
    """Levanta el servidor real en un puerto libre durante la prueba."""
    instancia = server.crear_servidor("127.0.0.1", 0)
    hilo = threading.Thread(target=instancia.serve_forever, daemon=True)
    hilo.start()
    yield f"http://127.0.0.1:{instancia.server_address[1]}"
    instancia.shutdown()
    instancia.server_close()
    hilo.join(timeout=5)


def _get(base: str, ruta: str):
    with urllib.request.urlopen(f"{base}{ruta}") as respuesta:  # noqa: S310 - URL local
        return respuesta.status, json.loads(respuesta.read().decode("utf-8"))


def _post(base: str, ruta: str, cuerpo: dict):
    peticion = urllib.request.Request(
        f"{base}{ruta}", data=json.dumps(cuerpo).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(peticion) as respuesta:  # noqa: S310 - URL local
        return respuesta.status, json.loads(respuesta.read().decode("utf-8"))


def test_endpoint_de_salud(servidor):
    assert _get(servidor, "/api/salud") == (200, {"estado": "ok"})


def test_endpoint_de_localidades(servidor):
    _, datos = _get(servidor, "/api/localidades")
    assert len(datos["localidades"]) == 20
    assert datos["defecto"] == config.LOCALIDAD_DEFECTO


def test_endpoints_de_lectura_y_comparativa(servidor):
    _, resumen = _get(servidor, "/api/dataset/resumen?localidad_id=13")
    _, actual = _get(servidor, "/api/lectura/actual?localidad_id=13")
    _, comparativa = _get(servidor, "/api/comparativa")
    assert resumen["registros_localidad"] == FILAS_POR_LOCALIDAD
    assert actual["localidad"] == "Teusaquillo"
    assert len(comparativa["filas"]) == 2


def test_endpoint_de_prediccion(servidor):
    estado, datos = _post(servidor, "/api/prediccion", {
        "temperatura": 13.5, "humedad": 72, "luz": 600, "ruido": 45,
    })
    assert estado == 200
    assert "prediccion" in datos


def test_prediccion_invalida_responde_400(servidor):
    with pytest.raises(urllib.error.HTTPError) as fallo:
        _post(servidor, "/api/prediccion", {"temperatura": 500})
    assert fallo.value.code == 400
    assert "error" in json.loads(fallo.value.read().decode("utf-8"))


def test_cuerpo_no_json_responde_400(servidor):
    peticion = urllib.request.Request(
        f"{servidor}/api/prediccion", data=b"no soy json",
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as fallo:
        urllib.request.urlopen(peticion)  # noqa: S310 - URL local
    assert fallo.value.code == 400


def test_endpoint_desconocido_responde_404(servidor):
    with pytest.raises(urllib.error.HTTPError) as fallo:
        _get(servidor, "/api/no-existe")
    assert fallo.value.code == 404


def test_post_fuera_de_la_api_responde_404(servidor):
    with pytest.raises(urllib.error.HTTPError) as fallo:
        _post(servidor, "/index.html", {})
    assert fallo.value.code == 404


def test_descarga_del_csv_declara_el_adjunto(servidor):
    with urllib.request.urlopen(f"{servidor}/api/dataset/csv") as respuesta:  # noqa: S310
        assert "attachment" in respuesta.headers["Content-Disposition"]
        assert respuesta.read().decode("utf-8").startswith("timestamp")


def test_archivos_estaticos_con_cabeceras_de_seguridad(servidor):
    with urllib.request.urlopen(f"{servidor}/") as respuesta:  # noqa: S310 - URL local
        assert respuesta.headers["Content-Type"].startswith("text/html")
        assert respuesta.headers["X-Content-Type-Options"] == "nosniff"


def test_recurso_estatico_inexistente_responde_404(servidor):
    with pytest.raises(urllib.error.HTTPError) as fallo:
        urllib.request.urlopen(f"{servidor}/no-existe.css")  # noqa: S310 - URL local
    assert fallo.value.code == 404


def test_control_del_colector_por_http(servidor, colector_limpio):
    _, iniciado = _post(servidor, "/api/colector/iniciar",
                        {"modo": "simulacion", "localidad_id": 13})
    _, estado = _get(servidor, "/api/colector/estado")
    _, detenido = _post(servidor, "/api/colector/detener", {})
    assert iniciado["activo"] is True
    assert estado["activo"] is True
    assert detenido["activo"] is False


# ---------------------------------------------------------------------------
# Rutas de error y caminos poco frecuentes
# ---------------------------------------------------------------------------

def test_registrar_src_en_path_es_idempotente(monkeypatch):
    monkeypatch.setattr(config.sys, "path", [p for p in config.sys.path if p != config.SRC_DIR])
    config.registrar_src_en_path()
    config.registrar_src_en_path()
    assert config.sys.path.count(config.SRC_DIR) == 1


def test_mtime_de_archivo_inexistente_es_none():
    assert repositorio._mtime("ruta/que/no/existe.csv") is None


def test_cargar_modelo_lee_el_pkl_una_sola_vez(entorno, monkeypatch):
    monkeypatch.undo()
    ruta = entorno["tmp"] / "modelo.pkl"
    repositorio.joblib.dump({"tipo": "doble"}, ruta)
    monkeypatch.setattr(config, "MODEL_PATH", str(ruta))
    repositorio._cache_modelo.update({"mtime": None, "modelo": None})

    primero = repositorio.cargar_modelo()
    assert primero == {"tipo": "doble"}
    assert repositorio.cargar_modelo() is primero


def test_servicios_sin_localidad_operan_sobre_todo_el_dataset(entorno):
    total = FILAS_POR_LOCALIDAD * len(LOCALIDADES_PRUEBA)
    assert servicios.resumen_dataset()["registros_localidad"] == total
    assert len(servicios.ultimas_lecturas(cantidad=total)["filas"]) == total


def test_predecir_ignora_un_historial_sin_columnas_utiles(entorno):
    resultado = servicios.predecir({
        "temperatura": 13.5, "humedad": 72, "luz": 600, "ruido": 45,
        "historia": [{"otro": 1}],
    })
    assert resultado["prediccion"] == pytest.approx(entorno["modelo"].valor)


def test_predecir_sin_registros_de_la_localidad_no_usa_historial(entorno):
    servicios.predecir({
        "temperatura": 13.5, "humedad": 72, "luz": 600, "ruido": 45,
        "localidad_id": 20, "usar_historial_dataset": True,
    })
    assert entorno["modelo"].X_recibido["temp_prom_30m"].iloc[0] == 13.5


def test_lectura_actual_sin_dataset_generado(entorno, monkeypatch):
    monkeypatch.setattr(repositorio, "hay_dataset", lambda: False)
    assert servicios.lectura_actual(13)["origen"] == "sin_datos"


def test_todos_los_endpoints_get_responden(entorno):
    for (metodo, ruta), manejador in rutas.RUTAS.items():
        if metodo != "GET":
            continue
        respuesta = manejador(Peticion(metodo, ruta, {}, {}))
        assert respuesta.estado == 200
        assert respuesta.datos is not None or respuesta.binario is not None


def test_ruta_estatica_de_un_directorio_sin_indice():
    assert server._ruta_estatica("/css") is None


def test_ruta_estatica_de_un_archivo_real():
    assert server._ruta_estatica("/css/estilos.css").endswith("estilos.css")


def test_cuerpo_demasiado_grande_responde_400(servidor):
    grande = {"relleno": "x" * (config.MAX_BODY_BYTES + 10)}
    with pytest.raises(urllib.error.HTTPError) as fallo:
        _post(servidor, "/api/prediccion", grande)
    assert fallo.value.code == 400


def test_content_length_invalido_responde_400(servidor):
    import socket
    from urllib.parse import urlparse

    destino = urlparse(servidor)
    peticion = (
        "POST /api/prediccion HTTP/1.1\r\n"
        f"Host: {destino.netloc}\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: abc\r\n"
        "Connection: close\r\n\r\n"
    )
    with socket.create_connection((destino.hostname, destino.port), timeout=5) as conexion:
        conexion.sendall(peticion.encode("ascii"))
        respuesta = conexion.recv(1024).decode("utf-8", errors="ignore")
    assert "400" in respuesta.splitlines()[0]


def test_cuerpo_que_no_es_objeto_responde_400(servidor):
    peticion = urllib.request.Request(
        f"{servidor}/api/prediccion", data=b"[1, 2, 3]",
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as fallo:
        urllib.request.urlopen(peticion)  # noqa: S310 - URL local
    assert fallo.value.code == 400


def test_post_sin_cuerpo_usa_diccionario_vacio(servidor, colector_limpio):
    peticion = urllib.request.Request(
        f"{servidor}/api/colector/iniciar", data=b"",
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(peticion) as respuesta:  # noqa: S310 - URL local
        assert json.loads(respuesta.read().decode("utf-8"))["modo"] == "simulacion"


def test_fallo_inesperado_responde_500(servidor, monkeypatch):
    def estalla(_peticion):
        raise RuntimeError("fallo simulado")

    monkeypatch.setitem(rutas.RUTAS, ("GET", "/api/salud"), estalla)
    with pytest.raises(urllib.error.HTTPError) as fallo:
        _get(servidor, "/api/salud")
    assert fallo.value.code == 500
    assert "fallo simulado" not in fallo.value.read().decode("utf-8")


def test_dataset_ausente_responde_404(servidor, entorno, monkeypatch):
    monkeypatch.setattr(config, "DATA_PATH", str(entorno["tmp"] / "no-existe.csv"))
    repositorio._cache_dataset.update({"mtime": None, "df": None, "verificado_en": 0.0})
    with pytest.raises(urllib.error.HTTPError) as fallo:
        _get(servidor, "/api/dataset/resumen")
    assert fallo.value.code == 404


class ServidorFalso:
    """Doble del ThreadingHTTPServer para probar el punto de entrada."""

    def __init__(self):
        self.cerrado = False

    def serve_forever(self):
        raise KeyboardInterrupt

    def server_close(self):
        self.cerrado = True


def test_main_cierra_el_servidor_al_interrumpir(monkeypatch):
    instancia = ServidorFalso()
    monkeypatch.setattr(server, "crear_servidor", lambda host, puerto: instancia)
    assert server.main(["--host", "127.0.0.1", "--puerto", "0"]) == 0
    assert instancia.cerrado is True


class SalidaFalsa:
    """Flujo de error de un proceso terminado."""

    def __init__(self, texto: str):
        self.texto = texto

    def read(self) -> bytes:
        return self.texto.encode("utf-8")


def test_estado_traduce_un_error_de_puerto_serial(colector_limpio):
    colector.iniciar(colector.MODO_REAL, "COM3", 9600, 13)
    colector_limpio[0].codigo = 2
    colector_limpio[0].stderr = SalidaFalsa("serial.SerialException: No se pudo abrir el puerto")
    assert "puerto serial" in colector.estado()["error"]


def test_estado_informa_salida_inesperada_sin_detalle(colector_limpio):
    colector.iniciar(colector.MODO_SIMULACION, "COM3", 9600, 13)
    colector_limpio[0].codigo = 3
    colector_limpio[0].stderr = SalidaFalsa("   ")
    assert "inesperadamente" in colector.estado()["error"]


def test_estado_sin_proceso_previo(colector_limpio):
    assert colector.estado()["activo"] is False


def test_listar_puertos_sin_pyserial(monkeypatch):
    monkeypatch.setitem(colector.sys.modules, "serial.tools.list_ports", None)
    assert colector.listar_puertos() == []
