/**
 * Pruebas de web/js/dom.js — construcción de nodos del panel.
 *
 * @vitest-environment jsdom
 *
 * El módulo evita innerHTML a propósito: usa createElement y textContent
 * para que ningún dato del backend pueda inyectar marcado en la página.
 * Varias de estas pruebas existen para proteger esa garantía.
 */
import { beforeEach, describe, expect, it } from 'vitest';
import {
  aviso, buscar, crear, reemplazar, tabla, tarjetaMetrica, vaciar,
} from '../web/js/dom.js';

beforeEach(() => {
  document.body.innerHTML = '';
});

describe('crear', () => {
  it('crea el elemento pedido', () => {
    expect(crear('section').tagName).toBe('SECTION');
  });

  it('asigna la clase', () => {
    expect(crear('div', { clase: 'panel' }).className).toBe('panel');
  });

  it('asigna el texto', () => {
    expect(crear('p', { texto: 'Teusaquillo' }).textContent).toBe('Teusaquillo');
  });

  it('convierte a texto los valores que no son cadena', () => {
    expect(crear('span', { texto: 18.5 }).textContent).toBe('18.5');
  });

  it('escribe el cero en lugar de tratarlo como ausente', () => {
    expect(crear('span', { texto: 0 }).textContent).toBe('0');
  });

  it('asigna atributos arbitrarios', () => {
    const nodo = crear('button', { attrs: { type: 'button', 'aria-label': 'Cerrar' } });

    expect(nodo.getAttribute('type')).toBe('button');
    expect(nodo.getAttribute('aria-label')).toBe('Cerrar');
  });

  it('agrega los hijos en orden', () => {
    const nodo = crear('ul', {}, [crear('li', { texto: 'a' }), crear('li', { texto: 'b' })]);

    expect(nodo.children).toHaveLength(2);
    expect(nodo.textContent).toBe('ab');
  });

  it('descarta los hijos nulos, para poder usar condicionales en línea', () => {
    const nodo = crear('div', {}, [crear('span'), null, undefined, false]);

    expect(nodo.children).toHaveLength(1);
  });

  it('funciona sin opciones ni hijos', () => {
    expect(crear('div').children).toHaveLength(0);
  });

  it('no interpreta el texto como marcado', () => {
    const nodo = crear('p', { texto: '<img src=x onerror=alert(1)>' });

    expect(nodo.children).toHaveLength(0);
    expect(nodo.textContent).toBe('<img src=x onerror=alert(1)>');
  });
});

describe('buscar', () => {
  it('encuentra el elemento', () => {
    document.body.appendChild(crear('div', { attrs: { id: 'panel' } }));

    expect(buscar('#panel').id).toBe('panel');
  });

  it('falla ruidosamente si no existe', () => {
    expect(() => buscar('#no-existe')).toThrow('No se encontró el elemento #no-existe');
  });

  it('acepta una raíz distinta de document', () => {
    const raiz = crear('div', {}, [crear('span', { clase: 'dato', texto: 'x' })]);

    expect(buscar('.dato', raiz).textContent).toBe('x');
  });
});

describe('vaciar', () => {
  it('elimina todos los hijos', () => {
    const nodo = crear('div', {}, [crear('span'), crear('span')]);

    vaciar(nodo);

    expect(nodo.children).toHaveLength(0);
  });

  it('devuelve el contenedor para poder encadenar', () => {
    const nodo = crear('div');

    expect(vaciar(nodo)).toBe(nodo);
  });

  it('no falla con un contenedor ya vacío', () => {
    expect(() => vaciar(crear('div'))).not.toThrow();
  });
});

describe('reemplazar', () => {
  it('sustituye el contenido anterior', () => {
    const nodo = crear('div', {}, [crear('span', { texto: 'viejo' })]);

    reemplazar(nodo, [crear('p', { texto: 'nuevo' })]);

    expect(nodo.children).toHaveLength(1);
    expect(nodo.textContent).toBe('nuevo');
  });

  it('descarta los nodos nulos', () => {
    const nodo = crear('div');

    reemplazar(nodo, [crear('p'), null, crear('p')]);

    expect(nodo.children).toHaveLength(2);
  });

  it('con una lista vacía deja el contenedor limpio', () => {
    const nodo = crear('div', {}, [crear('span')]);

    reemplazar(nodo, []);

    expect(nodo.children).toHaveLength(0);
  });
});

describe('tarjetaMetrica', () => {
  it('arma etiqueta y valor', () => {
    const nodo = tarjetaMetrica('Temperatura', '18,5 °C');

    expect(nodo.tagName).toBe('ARTICLE');
    expect(nodo.querySelector('.metrica__etiqueta').textContent).toBe('Temperatura');
    expect(nodo.querySelector('.metrica__valor').textContent).toBe('18,5 °C');
  });

  it('agrega el detalle cuando se pasa', () => {
    const nodo = tarjetaMetrica('Temperatura', '18,5 °C', 'hace 12 s');

    expect(nodo.querySelector('.metrica__detalle').textContent).toBe('hace 12 s');
  });

  it('omite el detalle cuando no se pasa', () => {
    expect(tarjetaMetrica('Temperatura', '18,5 °C').querySelector('.metrica__detalle')).toBeNull();
  });
});

describe('aviso', () => {
  it.each(['ok', 'aviso', 'error', 'info'])('refleja el nivel %s en la clase', (nivel) => {
    const nodo = aviso(nivel, 'mensaje');

    expect(nodo.className).toBe(`aviso aviso--${nivel}`);
    expect(nodo.textContent).toBe('mensaje');
  });
});

describe('tabla', () => {
  it('arma encabezados y filas', () => {
    const nodo = tabla(['Localidad', 'Temp'], [['Kennedy', '20,6'], ['Sumapaz', '10,2']]);

    expect(nodo.querySelectorAll('th')).toHaveLength(2);
    expect(nodo.querySelectorAll('tbody tr')).toHaveLength(2);
    expect(nodo.querySelectorAll('tbody td')[0].textContent).toBe('Kennedy');
  });

  it('envuelve la tabla para que pueda desplazarse', () => {
    const nodo = tabla(['a'], [['1']]);

    expect(nodo.className).toBe('tabla-scroll');
    expect(nodo.querySelector('table').className).toBe('tabla');
  });

  it('admite una tabla sin filas', () => {
    const nodo = tabla(['a', 'b'], []);

    expect(nodo.querySelectorAll('th')).toHaveLength(2);
    expect(nodo.querySelectorAll('tbody tr')).toHaveLength(0);
  });
});
