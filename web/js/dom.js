/**
 * Utilidades mínimas de construcción de DOM.
 * Se usa createElement/textContent en lugar de innerHTML para que ningún
 * dato del backend pueda inyectar marcado en la página.
 */

/**
 * Crea un elemento con clases, atributos, texto e hijos.
 * @param {string} etiqueta Nombre de la etiqueta HTML.
 * @param {{clase?: string, texto?: string, attrs?: Object<string,string>}} opciones
 * @param {Array<Node>} hijos
 * @returns {HTMLElement}
 */
export function crear(etiqueta, opciones = {}, hijos = []) {
  const nodo = document.createElement(etiqueta);
  if (opciones.clase) {
    nodo.className = opciones.clase;
  }
  if (opciones.texto !== undefined) {
    nodo.textContent = String(opciones.texto);
  }
  Object.entries(opciones.attrs || {}).forEach(([nombre, valor]) => {
    nodo.setAttribute(nombre, String(valor));
  });
  hijos.filter(Boolean).forEach((hijo) => nodo.appendChild(hijo));
  return nodo;
}

/**
 * Busca un elemento por selector y falla ruidosamente si no existe.
 * @param {string} selector
 * @param {ParentNode} raiz
 * @returns {HTMLElement}
 */
export function buscar(selector, raiz = document) {
  const nodo = raiz.querySelector(selector);
  if (!nodo) {
    throw new Error(`No se encontró el elemento ${selector}`);
  }
  return nodo;
}

/**
 * Elimina todos los hijos de un contenedor.
 * @param {HTMLElement} contenedor
 * @returns {HTMLElement} el mismo contenedor, para encadenar.
 */
export function vaciar(contenedor) {
  while (contenedor.firstChild) {
    contenedor.removeChild(contenedor.firstChild);
  }
  return contenedor;
}

/**
 * Reemplaza el contenido de un contenedor por los nodos indicados.
 * @param {HTMLElement} contenedor
 * @param {Array<Node>} nodos
 */
export function reemplazar(contenedor, nodos) {
  vaciar(contenedor);
  nodos.filter(Boolean).forEach((nodo) => contenedor.appendChild(nodo));
}

/**
 * Tarjeta de métrica: etiqueta, valor grande y detalle opcional.
 * @param {string} etiqueta
 * @param {string} valor
 * @param {string} [detalle]
 * @returns {HTMLElement}
 */
export function tarjetaMetrica(etiqueta, valor, detalle) {
  return crear('article', { clase: 'metrica' }, [
    crear('span', { clase: 'metrica__etiqueta', texto: etiqueta }),
    crear('strong', { clase: 'metrica__valor', texto: valor }),
    detalle ? crear('span', { clase: 'metrica__detalle', texto: detalle }) : null,
  ]);
}

/**
 * Bloque de aviso con nivel semántico.
 * @param {'ok'|'aviso'|'error'|'info'} nivel
 * @param {string} mensaje
 * @returns {HTMLElement}
 */
export function aviso(nivel, mensaje) {
  return crear('p', { clase: `aviso aviso--${nivel}`, texto: mensaje });
}

/**
 * Construye una tabla a partir de encabezados y filas de texto.
 * @param {Array<string>} encabezados
 * @param {Array<Array<string>>} filas
 * @returns {HTMLElement}
 */
export function tabla(encabezados, filas) {
  const cabecera = crear('thead', {}, [
    crear('tr', {}, encabezados.map((titulo) => crear('th', { texto: titulo }))),
  ]);
  const cuerpo = crear('tbody', {}, filas.map(
    (fila) => crear('tr', {}, fila.map((celda) => crear('td', { texto: celda }))),
  ));
  return crear('div', { clase: 'tabla-scroll' }, [crear('table', { clase: 'tabla' }, [cabecera, cuerpo])]);
}
