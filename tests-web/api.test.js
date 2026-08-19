/**
 * Pruebas de web/js/api.js — cliente REST del panel.
 *
 * fetch se sustituye por un doble: aquí se verifica cómo se arma la
 * petición y cómo se interpreta la respuesta, no el servidor real.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ErrorApi, enviar, obtener, rutas } from '../web/js/api.js';

/** Construye una respuesta como la que devolvería fetch. */
function respuesta({ ok = true, status = 200, cuerpo = {}, roto = false } = {}) {
  return {
    ok,
    status,
    json: roto
      ? () => Promise.reject(new SyntaxError('respuesta sin JSON'))
      : () => Promise.resolve(cuerpo),
  };
}

beforeEach(() => {
  globalThis.fetch = vi.fn(() => Promise.resolve(respuesta()));
});

afterEach(() => {
  vi.restoreAllMocks();
});

/** Devuelve la URL con la que se llamó a fetch. */
const urlLlamada = () => globalThis.fetch.mock.calls[0][0];
/** Devuelve las opciones con las que se llamó a fetch. */
const opcionesLlamada = () => globalThis.fetch.mock.calls[0][1];

describe('obtener', () => {
  it('antepone el prefijo /api a la ruta', async () => {
    await obtener('/localidades');

    expect(urlLlamada()).toBe('/api/localidades');
  });

  it('pide JSON de forma explícita', async () => {
    await obtener('/localidades');

    expect(opcionesLlamada().headers.Accept).toBe('application/json');
  });

  it('devuelve el cuerpo ya deserializado', async () => {
    globalThis.fetch = vi.fn(() => Promise.resolve(
      respuesta({ cuerpo: { localidades: [{ id: 13 }] } }),
    ));

    await expect(obtener('/localidades')).resolves.toEqual({ localidades: [{ id: 13 }] });
  });
});

describe('serialización de parámetros', () => {
  it('arma la cadena de consulta', async () => {
    await obtener('/dataset/serie', { localidad_id: 13, limite: 50 });

    expect(urlLlamada()).toBe('/api/dataset/serie?localidad_id=13&limite=50');
  });

  it.each([
    ['nulos', { a: 1, b: null }],
    ['indefinidos', { a: 1, b: undefined }],
    ['cadenas vacías', { a: 1, b: '' }],
  ])('descarta los valores %s', async (_caso, params) => {
    await obtener('/x', params);

    expect(urlLlamada()).toBe('/api/x?a=1');
  });

  it('conserva el cero, que sí es un valor válido', async () => {
    await obtener('/x', { limite: 0 });

    expect(urlLlamada()).toBe('/api/x?limite=0');
  });

  it('no agrega el signo de interrogación si no quedan parámetros', async () => {
    await obtener('/x', { a: null });

    expect(urlLlamada()).toBe('/api/x');
  });

  it('funciona sin parámetros', async () => {
    await obtener('/x');

    expect(urlLlamada()).toBe('/api/x');
  });
});

describe('enviar', () => {
  it('usa POST con el cuerpo serializado', async () => {
    await enviar('/prediccion', { temperatura: 18.5 });

    const opciones = opcionesLlamada();
    expect(opciones.method).toBe('POST');
    expect(opciones.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(opciones.body)).toEqual({ temperatura: 18.5 });
  });

  it('envía un objeto vacío si no se pasa cuerpo', async () => {
    await enviar('/colector/detener');

    expect(JSON.parse(opcionesLlamada().body)).toEqual({});
  });
});

describe('manejo de errores', () => {
  it('lanza ErrorApi con el mensaje del backend', async () => {
    globalThis.fetch = vi.fn(() => Promise.resolve(
      respuesta({ ok: false, status: 400, cuerpo: { error: 'Localidad no válida' } }),
    ));

    await expect(obtener('/x')).rejects.toThrowError(
      expect.objectContaining({ name: 'ErrorApi', message: 'Localidad no válida', estado: 400 }),
    );
  });

  it('usa un mensaje genérico si el backend no explica el error', async () => {
    globalThis.fetch = vi.fn(() => Promise.resolve(
      respuesta({ ok: false, status: 500, cuerpo: {} }),
    ));

    await expect(obtener('/x')).rejects.toThrow('Error HTTP 500');
  });

  it('sobrevive a una respuesta que no es JSON', async () => {
    globalThis.fetch = vi.fn(() => Promise.resolve(
      respuesta({ ok: false, status: 502, roto: true }),
    ));

    await expect(obtener('/x')).rejects.toThrow('Error HTTP 502');
  });

  it('devuelve null si una respuesta correcta viene sin cuerpo', async () => {
    globalThis.fetch = vi.fn(() => Promise.resolve(respuesta({ roto: true })));

    await expect(obtener('/x')).resolves.toBeNull();
  });

  it('ErrorApi conserva el código de estado', () => {
    const error = new ErrorApi('roto', 503);

    expect(error).toBeInstanceOf(Error);
    expect(error.estado).toBe(503);
  });
});

describe('catálogo de rutas', () => {
  it.each([
    ['localidades', () => rutas.localidades(), '/api/localidades'],
    ['metricas', () => rutas.metricas(), '/api/metricas'],
    ['comparativa', () => rutas.comparativa(), '/api/comparativa'],
    ['resumen', () => rutas.resumen(8), '/api/dataset/resumen?localidad_id=8'],
    ['live', () => rutas.live(13), '/api/lectura/live?localidad_id=13'],
    ['colectorEstado', () => rutas.colectorEstado(), '/api/colector/estado'],
  ])('%s llama a %s', async (_nombre, llamada, esperado) => {
    await llamada();

    expect(urlLlamada()).toBe(esperado);
  });

  it('traduce el entorno interior a un indicador que el backend entiende', async () => {
    await rutas.actual(13, true);

    expect(urlLlamada()).toBe('/api/lectura/actual?localidad_id=13&entorno_interior=1');
  });

  it('omite el entorno interior cuando está desactivado', async () => {
    await rutas.actual(13, false);

    expect(urlLlamada()).toBe('/api/lectura/actual?localidad_id=13');
  });

  it('expone la URL de descarga del CSV sin hacer petición', () => {
    expect(rutas.urlCsv()).toBe('/api/dataset/csv');
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });
});
