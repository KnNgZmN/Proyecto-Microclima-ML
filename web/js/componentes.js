/**
 * Componentes de interfaz reutilizados por varias pestañas.
 */

import { crear, tarjetaMetrica } from './dom.js';
import * as estado from './estado.js';

/**
 * Sección con título y contenido.
 * @param {string} titulo
 * @param {Array<Node>} hijos
 * @returns {HTMLElement}
 */
export function seccion(titulo, hijos) {
  return crear('section', { clase: 'seccion' }, [
    crear('h2', { clase: 'seccion__titulo', texto: titulo }),
    ...hijos,
  ]);
}

/**
 * Rejilla de tarjetas de métrica.
 * @param {Array<{etiqueta: string, valor: string, detalle?: string}>} items
 * @returns {HTMLElement}
 */
export function rejillaMetricas(items) {
  return crear(
    'div',
    { clase: 'rejilla-metricas' },
    items.map((item) => tarjetaMetrica(item.etiqueta, item.valor, item.detalle)),
  );
}

/**
 * Desplegable de localidades enlazado al estado compartido.
 * @param {string} etiqueta Texto visible del campo.
 * @param {string} id Identificador del <select>, usado para sincronizarlo.
 * @returns {HTMLElement}
 */
export function selectorLocalidad(etiqueta, id) {
  const select = crear('select', { clase: 'campo__control', attrs: { id } });
  estado.localidades().forEach((loc) => {
    select.appendChild(crear('option', { texto: loc.nombre, attrs: { value: loc.id } }));
  });
  select.value = String(estado.localidadId());
  select.addEventListener('change', () => estado.seleccionarLocalidad(select.value));

  return crear('label', { clase: 'campo', attrs: { for: id } }, [
    crear('span', { clase: 'campo__etiqueta', texto: etiqueta }),
    select,
  ]);
}

/**
 * Alinea un selector ya montado con la localidad activa, sin recrearlo.
 * @param {string} id Identificador del <select>.
 */
export function sincronizarSelector(id) {
  const select = document.getElementById(id);
  if (select) {
    select.value = String(estado.localidadId());
  }
}

/**
 * Campo numérico con rango y paso.
 * @param {{id: string, etiqueta: string, valor: number, min: number,
 *          max: number, paso: number}} config
 * @returns {HTMLElement}
 */
export function campoNumero(config) {
  const input = crear('input', {
    clase: 'campo__control',
    attrs: {
      type: 'number',
      id: config.id,
      value: config.valor,
      min: config.min,
      max: config.max,
      step: config.paso,
    },
  });
  return crear('label', { clase: 'campo', attrs: { for: config.id } }, [
    crear('span', { clase: 'campo__etiqueta', texto: config.etiqueta }),
    input,
  ]);
}

/**
 * Deslizador con lectura del valor actual.
 * @param {{id: string, etiqueta: string, valor: number, min: number, max: number}} config
 * @returns {HTMLElement}
 */
export function campoDeslizador(config) {
  const salida = crear('output', { clase: 'campo__salida', texto: config.valor });
  const input = crear('input', {
    clase: 'campo__control campo__control--rango',
    attrs: {
      type: 'range',
      id: config.id,
      value: config.valor,
      min: config.min,
      max: config.max,
      step: 1,
    },
  });
  input.addEventListener('input', () => {
    salida.textContent = input.value;
  });

  return crear('label', { clase: 'campo', attrs: { for: config.id } }, [
    crear('span', { clase: 'campo__etiqueta' }, [
      crear('span', { texto: config.etiqueta }),
      salida,
    ]),
    input,
  ]);
}

/**
 * Contenedor de gráfica con su lienzo.
 * @param {string} titulo
 * @param {string} id Identificador del canvas.
 * @param {string} [modificador] Clase extra para ajustar la altura.
 * @returns {HTMLElement}
 */
export function bloqueGrafico(titulo, id, modificador = '') {
  return crear('figure', { clase: 'grafico' }, [
    crear('figcaption', { clase: 'grafico__titulo', texto: titulo }),
    crear('canvas', {
      clase: `grafico__lienzo ${modificador}`.trim(),
      attrs: { id },
    }),
  ]);
}

/**
 * Botón de acción.
 * @param {string} texto
 * @param {() => void} alPulsar
 * @param {{primario?: boolean, deshabilitado?: boolean}} [opciones]
 * @returns {HTMLButtonElement}
 */
export function boton(texto, alPulsar, opciones = {}) {
  const clase = opciones.primario ? 'boton boton--primario' : 'boton';
  const elemento = crear('button', { clase, texto, attrs: { type: 'button' } });
  if (opciones.deshabilitado) {
    elemento.disabled = true;
  }
  elemento.addEventListener('click', alPulsar);
  return elemento;
}

/**
 * Indicador de estado con punto de color.
 * @param {'vivo'|'atrasado'|'caido'} nivel
 * @param {string} texto
 * @returns {HTMLElement}
 */
export function insignia(nivel, texto) {
  return crear('span', { clase: `insignia insignia--${nivel}` }, [
    crear('span', { clase: 'insignia__punto' }),
    crear('span', { texto }),
  ]);
}
