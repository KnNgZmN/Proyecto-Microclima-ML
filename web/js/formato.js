/**
 * Formateo de valores numéricos y de fecha para la interfaz.
 * Centralizado aquí para que las vistas no repitan reglas de presentación.
 */

const LOCALE = 'es-CO';

/**
 * Formatea un número con una cantidad fija de decimales.
 * @param {number|null|undefined} valor
 * @param {number} decimales
 * @returns {string} Valor formateado, o un guion si no hay dato.
 */
export function numero(valor, decimales = 1) {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
    return '—';
  }
  return Number(valor).toLocaleString(LOCALE, {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  });
}

/**
 * Formatea un entero con separadores de miles.
 * @param {number|null|undefined} valor
 * @returns {string}
 */
export function entero(valor) {
  return numero(valor, 0);
}

/**
 * Añade signo explícito al valor, útil para mostrar variaciones.
 * @param {number|null|undefined} valor
 * @param {number} decimales
 * @returns {string}
 */
export function conSigno(valor, decimales = 2) {
  if (valor === null || valor === undefined) {
    return '—';
  }
  const signo = Number(valor) >= 0 ? '+' : '';
  return signo + numero(valor, decimales);
}

/**
 * Convierte una proporción 0-1 en porcentaje legible.
 * @param {number} valor
 * @returns {string}
 */
export function porcentaje(valor) {
  return `${numero(Number(valor) * 100, 0)} %`;
}

/**
 * Extrae la parte de hora de una marca de tiempo "YYYY-MM-DD HH:MM:SS".
 * @param {string} ts
 * @returns {string}
 */
export function hora(ts) {
  return typeof ts === 'string' && ts.length >= 16 ? ts.slice(11, 16) : '—';
}

/**
 * Traduce una antigüedad en segundos a un texto corto.
 * @param {number|null} segundos
 * @returns {string}
 */
export function antiguedad(segundos) {
  if (segundos === null || segundos === undefined) {
    return 'sin datos';
  }
  if (segundos < 60) {
    return `hace ${Math.max(0, Math.round(segundos))} s`;
  }
  const minutos = Math.floor(segundos / 60);
  if (minutos < 60) {
    return `hace ${minutos} min`;
  }
  return `hace ${Math.floor(minutos / 60)} h`;
}

/**
 * Etiqueta de estado según la antigüedad de la última lectura.
 * @param {number|null} segundos
 * @returns {'vivo'|'atrasado'|'caido'}
 */
export function nivelFrescura(segundos) {
  if (segundos === null || segundos === undefined) {
    return 'caido';
  }
  if (segundos < 15) {
    return 'vivo';
  }
  return segundos < 60 ? 'atrasado' : 'caido';
}
