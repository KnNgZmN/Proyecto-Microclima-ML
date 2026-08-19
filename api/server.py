"""Servidor HTTP del panel de Microclima, construido sobre la biblioteca estándar.

Sirve el front estático de web/ y la API REST bajo /api. No usa ningún
framework web: solo http.server, de modo que el proyecto se pueda analizar
como aplicación web clásica (HTML + CSS + JavaScript) en SonarQube.

Uso:
    python -m api.server --host 127.0.0.1 --puerto 8000
"""

import argparse
import json
import logging
import os
import posixpath
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from api import config, rutas
from api.rutas import Peticion, Respuesta
from api.servicios import SolicitudInvalida

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
_log = logging.getLogger("microclima")

TIPOS_MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".png": "image/png",
    ".webmanifest": "application/manifest+json",
}

ARCHIVO_INDICE = "index.html"


_catalogo_web = None


def _construir_catalogo() -> dict:
    """Mapa {ruta_url: ruta_absoluta} de todo lo publicable bajo web/.

    Se construye recorriendo el disco, nunca a partir de la peticion. Es la
    pieza que hace imposible el path traversal: si una ruta no esta en este
    catalogo, no se sirve, y el catalogo solo contiene archivos que ya estaban
    dentro de web/.
    """
    raiz = os.path.realpath(config.WEB_DIR)
    catalogo = {}
    for carpeta, _, archivos in os.walk(raiz):
        for nombre in archivos:
            absoluta = os.path.join(carpeta, nombre)
            relativa = os.path.relpath(absoluta, raiz).replace(os.sep, "/")
            catalogo["/" + relativa] = absoluta
    return catalogo


def _catalogo(recargar: bool = False) -> dict:
    """Catalogo cacheado; se recarga si aparecen archivos nuevos en desarrollo."""
    global _catalogo_web
    if _catalogo_web is None or recargar:
        _catalogo_web = _construir_catalogo()
    return _catalogo_web


def _clave_estatica(ruta_url: str) -> str:
    """Normaliza la ruta pedida a la forma que usa el catalogo."""
    ruta = posixpath.normpath(unquote(ruta_url))
    if ruta in ("/", "", "."):
        ruta = "/" + ARCHIVO_INDICE
    # Los segmentos vacios, "." y ".." se descartan: aunque llegaran, no
    # existe ninguna clave del catalogo que apunte fuera de web/.
    partes = [parte for parte in ruta.split("/") if parte not in ("", ".", "..")]
    return "/" + "/".join(partes)


def _ruta_estatica(ruta_url: str):
    """Traduce una ruta de URL a un archivo de web/, o None si no se sirve.

    Devuelve siempre un valor tomado del catalogo construido por el servidor,
    nunca una ruta armada con lo que envio el cliente.
    """
    clave = _clave_estatica(ruta_url)

    for candidata in (clave, clave.rstrip("/") + "/" + ARCHIVO_INDICE):
        destino = _catalogo().get(candidata)
        if destino is None:
            # El archivo pudo crearse despues de arrancar el servidor.
            destino = _catalogo(recargar=True).get(candidata)
        if destino is not None:
            return destino
    return None


class ManejadorMicroclima(BaseHTTPRequestHandler):
    """Enruta las peticiones entre la API JSON y los archivos estáticos."""

    server_version = "Microclima/1.0"
    protocol_version = "HTTP/1.1"

    def do_GET(self):  # noqa: N802 - nombre impuesto por BaseHTTPRequestHandler
        """Atiende peticiones de lectura de la API y del front estático."""
        url = urlparse(self.path)
        if url.path.startswith("/api/"):
            self._atender_api("GET", url)
        else:
            self._atender_estatico(url.path)

    def do_POST(self):  # noqa: N802 - nombre impuesto por BaseHTTPRequestHandler
        """Atiende predicciones y control del colector."""
        url = urlparse(self.path)
        if url.path.startswith("/api/"):
            self._atender_api("POST", url)
        else:
            self._error(HTTPStatus.NOT_FOUND, "Recurso no encontrado")

    def log_message(self, formato, *args):
        """Redirige el registro de acceso al logger del proyecto."""
        _log.info("%s - %s", self.address_string(), formato % args)

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    def _atender_api(self, metodo: str, url):
        """Resuelve la ruta, ejecuta el manejador y traduce errores a HTTP."""
        manejador = rutas.resolver(metodo, url.path)
        if manejador is None:
            self._error(HTTPStatus.NOT_FOUND, "Endpoint no encontrado")
            return

        try:
            cuerpo = self._leer_cuerpo() if metodo == "POST" else {}
            peticion = Peticion(metodo, url.path, _params(url.query), cuerpo)
            self._responder(manejador(peticion))
        except SolicitudInvalida as error:
            self._error(HTTPStatus.BAD_REQUEST, str(error))
        except FileNotFoundError as error:
            self._error(HTTPStatus.NOT_FOUND, str(error))
        except Exception:  # noqa: BLE001 - último recinto: nada debe tumbar el servidor
            _log.error("Fallo atendiendo %s\n%s", url.path, traceback.format_exc())
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Error interno del servidor")

    def _leer_cuerpo(self) -> dict:
        """Lee y valida el cuerpo JSON de la petición."""
        try:
            longitud = int(self.headers.get("Content-Length", 0))
        except ValueError as error:
            raise SolicitudInvalida("Content-Length inválido") from error

        if longitud <= 0:
            return {}
        if longitud > config.MAX_BODY_BYTES:
            raise SolicitudInvalida("Cuerpo de la petición demasiado grande")

        crudo = self.rfile.read(longitud)
        try:
            datos = json.loads(crudo.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as error:
            raise SolicitudInvalida("El cuerpo debe ser JSON válido") from error

        if not isinstance(datos, dict):
            raise SolicitudInvalida("El cuerpo debe ser un objeto JSON")
        return datos

    def _responder(self, respuesta: Respuesta):
        """Serializa una Respuesta de la capa de rutas."""
        if respuesta.binario is not None:
            cabeceras = {}
            if respuesta.descarga:
                cabeceras["Content-Disposition"] = f'attachment; filename="{respuesta.descarga}"'
            self._enviar(respuesta.estado, respuesta.binario, respuesta.tipo, cabeceras)
            return

        cuerpo = json.dumps(respuesta.datos, ensure_ascii=False).encode("utf-8")
        self._enviar(respuesta.estado, cuerpo, "application/json; charset=utf-8")

    # ------------------------------------------------------------------
    # Estáticos
    # ------------------------------------------------------------------
    def _atender_estatico(self, ruta_url: str):
        """Entrega un archivo de web/ o 404 si no existe."""
        archivo = _ruta_estatica(ruta_url)
        if archivo is None:
            self._error(HTTPStatus.NOT_FOUND, "Recurso no encontrado")
            return

        with open(archivo, "rb") as contenido:
            datos = contenido.read()
        extension = os.path.splitext(archivo)[1].lower()
        tipo = TIPOS_MIME.get(extension, "application/octet-stream")
        self._enviar(HTTPStatus.OK, datos, tipo, {"Cache-Control": "no-cache"})

    # ------------------------------------------------------------------
    # Utilidades de escritura
    # ------------------------------------------------------------------
    def _error(self, estado, mensaje: str):
        """Responde un error de la API en el mismo formato JSON que el resto."""
        cuerpo = json.dumps({"error": mensaje}, ensure_ascii=False).encode("utf-8")
        self._enviar(estado, cuerpo, "application/json; charset=utf-8")

    def _enviar(self, estado, cuerpo: bytes, tipo: str, cabeceras: dict = None):
        """Escribe la respuesta con las cabeceras de seguridad del panel."""
        self.send_response(int(estado))
        self.send_header("Content-Type", tipo or "application/octet-stream")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        for nombre, valor in (cabeceras or {}).items():
            self.send_header(nombre, valor)
        self.end_headers()
        self.wfile.write(cuerpo)


def _params(consulta: str) -> dict:
    """Aplana la cadena de consulta a un diccionario de un valor por clave."""
    return {clave: valores[0] for clave, valores in parse_qs(consulta).items() if valores}


def crear_servidor(host: str, puerto: int) -> ThreadingHTTPServer:
    """Construye el servidor sin arrancarlo (útil para pruebas)."""
    return ThreadingHTTPServer((host, puerto), ManejadorMicroclima)


def main(argv=None) -> int:
    """Punto de entrada de línea de comandos."""
    parser = argparse.ArgumentParser(description="Servidor del panel de Microclima Bogotá")
    parser.add_argument("--host", default="127.0.0.1", help="Interfaz de escucha")
    parser.add_argument("--puerto", type=int, default=8000, help="Puerto TCP")
    args = parser.parse_args(argv)

    servidor = crear_servidor(args.host, args.puerto)
    _log.info("Panel disponible en http://%s:%s", args.host, args.puerto)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        _log.info("Deteniendo el servidor…")
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
