/**
 * Cliente de la API REST del panel.
 * Todas las llamadas pasan por aquí para unificar el manejo de errores.
 */

const BASE = '/api';

/** Error de la API con el mensaje devuelto por el backend. */
export class ErrorApi extends Error {
  /**
   * @param {string} mensaje
   * @param {number} estado Código HTTP recibido.
   */
  constructor(mensaje, estado) {
    super(mensaje);
    this.name = 'ErrorApi';
    this.estado = estado;
  }
}

/**
 * Serializa parámetros ignorando valores nulos o vacíos.
 * @param {Object} params
 * @returns {string} Cadena de consulta con "?" inicial, o vacía.
 */
function consulta(params) {
  const partes = new URLSearchParams();
  Object.entries(params || {}).forEach(([clave, valor]) => {
    if (valor !== null && valor !== undefined && valor !== '') {
      partes.append(clave, String(valor));
    }
  });
  const texto = partes.toString();
  return texto ? `?${texto}` : '';
}

/**
 * Interpreta la respuesta HTTP y lanza ErrorApi si el estado no es 2xx.
 * @param {Response} respuesta
 * @returns {Promise<Object>}
 */
async function interpretar(respuesta) {
  let datos = null;
  try {
    datos = await respuesta.json();
  } catch {
    datos = null;
  }
  if (!respuesta.ok) {
    const mensaje = datos && datos.error ? datos.error : `Error HTTP ${respuesta.status}`;
    throw new ErrorApi(mensaje, respuesta.status);
  }
  return datos;
}

/**
 * Petición GET a la API.
 * @param {string} ruta
 * @param {Object} [params]
 * @returns {Promise<Object>}
 */
export async function obtener(ruta, params) {
  const respuesta = await fetch(`${BASE}${ruta}${consulta(params)}`, {
    headers: { Accept: 'application/json' },
  });
  return interpretar(respuesta);
}

/**
 * Petición POST con cuerpo JSON.
 * @param {string} ruta
 * @param {Object} cuerpo
 * @returns {Promise<Object>}
 */
export async function enviar(ruta, cuerpo) {
  const respuesta = await fetch(`${BASE}${ruta}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(cuerpo || {}),
  });
  return interpretar(respuesta);
}

export const rutas = {
  localidades: () => obtener('/localidades'),
  metricas: () => obtener('/metricas'),
  resumen: (localidadId) => obtener('/dataset/resumen', { localidad_id: localidadId }),
  serie: (localidadId, limite) => obtener('/dataset/serie', { localidad_id: localidadId, limite }),
  ultimas: (localidadId, cantidad) => obtener('/dataset/ultimas', {
    localidad_id: localidadId,
    cantidad,
  }),
  actual: (localidadId, interior) => obtener('/lectura/actual', {
    localidad_id: localidadId,
    entorno_interior: interior ? '1' : '',
  }),
  live: (localidadId) => obtener('/lectura/live', { localidad_id: localidadId }),
  comparativa: () => obtener('/comparativa'),
  prediccion: (cuerpo) => enviar('/prediccion', cuerpo),
  colectorEstado: () => obtener('/colector/estado'),
  colectorIniciar: (cuerpo) => enviar('/colector/iniciar', cuerpo),
  colectorDetener: () => enviar('/colector/detener', {}),
  urlCsv: () => `${BASE}/dataset/csv`,
};
