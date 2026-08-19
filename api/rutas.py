"""Tabla de rutas de la API y traducción de parámetros HTTP a servicios."""

from api import colector, config, servicios


class Peticion:
    """Datos ya normalizados de una petición HTTP."""

    def __init__(self, metodo: str, ruta: str, params: dict, cuerpo: dict):
        self.metodo = metodo
        self.ruta = ruta
        self.params = params
        self.cuerpo = cuerpo

    def entero(self, clave: str, defecto=None):
        """Parámetro de consulta convertido a entero, con validación."""
        crudo = self.params.get(clave)
        if crudo is None or crudo == "":
            return defecto
        try:
            return int(crudo)
        except ValueError as error:
            raise servicios.SolicitudInvalida(f"{clave} debe ser un entero") from error

    def booleano(self, clave: str) -> bool:
        """Parámetro de consulta interpretado como bandera booleana."""
        return str(self.params.get(clave, "")).lower() in ("1", "true", "si", "sí")

    def acotado(self, clave: str, defecto: int, maximo: int) -> int:
        """Entero positivo limitado a un máximo, para evitar respuestas gigantes."""
        valor = self.entero(clave, defecto)
        if valor < 1:
            raise servicios.SolicitudInvalida(f"{clave} debe ser mayor que cero")
        return min(valor, maximo)


class Respuesta:
    """Respuesta de la API: datos JSON o contenido binario con su tipo MIME."""

    def __init__(self, datos=None, estado: int = 200, binario: bytes = None,
                 tipo: str = None, descarga: str = None):
        self.datos = datos
        self.estado = estado
        self.binario = binario
        self.tipo = tipo
        self.descarga = descarga


def _localidad(peticion: Peticion):
    """Identificador de localidad pedido, validado contra el catálogo."""
    loc_id = peticion.entero("localidad_id")
    if loc_id is not None:
        servicios.obtener_localidad(loc_id)
    return loc_id


def _salud(_peticion: Peticion) -> Respuesta:
    return Respuesta({"estado": "ok"})


def _localidades(_peticion: Peticion) -> Respuesta:
    return Respuesta({"localidades": servicios.listar_localidades(),
                      "defecto": config.LOCALIDAD_DEFECTO})


def _metricas(_peticion: Peticion) -> Respuesta:
    return Respuesta(servicios.metricas_modelo())


def _resumen(peticion: Peticion) -> Respuesta:
    return Respuesta(servicios.resumen_dataset(_localidad(peticion)))


def _serie(peticion: Peticion) -> Respuesta:
    limite = peticion.acotado("limite", 144, 2000)
    return Respuesta(servicios.serie_temporal(_localidad(peticion), limite))


def _ultimas(peticion: Peticion) -> Respuesta:
    cantidad = peticion.acotado("cantidad", 12, 200)
    return Respuesta(servicios.ultimas_lecturas(_localidad(peticion), cantidad))


def _actual(peticion: Peticion) -> Respuesta:
    return Respuesta(servicios.lectura_actual(_localidad(peticion),
                                              peticion.booleano("entorno_interior")))


def _live(peticion: Peticion) -> Respuesta:
    return Respuesta(servicios.estado_live(_localidad(peticion)))


def _comparativa(_peticion: Peticion) -> Respuesta:
    return Respuesta(servicios.comparativa())


def _csv(_peticion: Peticion) -> Respuesta:
    return Respuesta(binario=servicios.dataset_csv(), tipo="text/csv; charset=utf-8",
                     descarga="microclima_bogota.csv")


def _predecir(peticion: Peticion) -> Respuesta:
    return Respuesta(servicios.predecir(peticion.cuerpo))


def _colector_estado(_peticion: Peticion) -> Respuesta:
    return Respuesta(colector.estado())


def _colector_iniciar(peticion: Peticion) -> Respuesta:
    cuerpo = peticion.cuerpo
    return Respuesta(colector.iniciar(
        modo=str(cuerpo.get("modo", colector.MODO_SIMULACION)),
        puerto=str(cuerpo.get("puerto", "COM3")),
        baud=int(cuerpo.get("baud", 9600)),
        localidad_id=int(cuerpo.get("localidad_id", config.LOCALIDAD_DEFECTO)),
    ))


def _colector_detener(_peticion: Peticion) -> Respuesta:
    return Respuesta(colector.detener())


RUTAS = {
    ("GET", "/api/salud"): _salud,
    ("GET", "/api/localidades"): _localidades,
    ("GET", "/api/metricas"): _metricas,
    ("GET", "/api/dataset/resumen"): _resumen,
    ("GET", "/api/dataset/serie"): _serie,
    ("GET", "/api/dataset/ultimas"): _ultimas,
    ("GET", "/api/dataset/csv"): _csv,
    ("GET", "/api/lectura/actual"): _actual,
    ("GET", "/api/lectura/live"): _live,
    ("GET", "/api/comparativa"): _comparativa,
    ("POST", "/api/prediccion"): _predecir,
    ("GET", "/api/colector/estado"): _colector_estado,
    ("POST", "/api/colector/iniciar"): _colector_iniciar,
    ("POST", "/api/colector/detener"): _colector_detener,
}


def resolver(metodo: str, ruta: str):
    """Devuelve el manejador registrado para el par método/ruta, o None."""
    return RUTAS.get((metodo, ruta))
