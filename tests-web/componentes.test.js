/**
 * Pruebas de web/js/componentes.js — piezas reutilizables de la interfaz.
 *
 * @vitest-environment jsdom
 *
 * Varios componentes leen y escriben el estado compartido, así que el
 * módulo se reimporta en limpio en cada prueba.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

let componentes;
let estado;

const LOCALIDADES = [
  { id: 8, nombre: 'Kennedy' },
  { id: 13, nombre: 'Teusaquillo' },
  { id: 20, nombre: 'Sumapaz' },
];

beforeEach(async () => {
  vi.resetModules();
  document.body.innerHTML = '';
  estado = await import('../web/js/estado.js');
  componentes = await import('../web/js/componentes.js');
});

describe('seccion', () => {
  it('pone el título y conserva los hijos', () => {
    const nodo = componentes.seccion('Históricos', [
      document.createElement('p'),
      document.createElement('p'),
    ]);

    expect(nodo.querySelector('.seccion__titulo').textContent).toBe('Históricos');
    expect(nodo.querySelectorAll('p')).toHaveLength(2);
  });

  it('admite una sección sin contenido', () => {
    expect(componentes.seccion('Vacía', []).children).toHaveLength(1);
  });
});

describe('rejillaMetricas', () => {
  it('crea una tarjeta por elemento', () => {
    const nodo = componentes.rejillaMetricas([
      { etiqueta: 'Temp', valor: '18,5 °C' },
      { etiqueta: 'Humedad', valor: '70 %', detalle: 'hace 12 s' },
    ]);

    expect(nodo.querySelectorAll('.metrica')).toHaveLength(2);
    expect(nodo.querySelectorAll('.metrica__detalle')).toHaveLength(1);
  });

  it('admite una rejilla vacía', () => {
    expect(componentes.rejillaMetricas([]).children).toHaveLength(0);
  });
});

describe('selectorLocalidad', () => {
  beforeEach(() => {
    estado.definirLocalidades(LOCALIDADES, 13);
  });

  it('crea una opción por localidad', () => {
    const nodo = componentes.selectorLocalidad('Localidad', 'sel-loc');

    expect(nodo.querySelectorAll('option')).toHaveLength(3);
    expect(nodo.querySelector('option').textContent).toBe('Kennedy');
  });

  it('preselecciona la localidad activa', () => {
    const nodo = componentes.selectorLocalidad('Localidad', 'sel-loc');

    expect(nodo.querySelector('select').value).toBe('13');
  });

  it('enlaza la etiqueta con el control por accesibilidad', () => {
    const nodo = componentes.selectorLocalidad('Localidad', 'sel-loc');

    expect(nodo.getAttribute('for')).toBe('sel-loc');
    expect(nodo.querySelector('select').id).toBe('sel-loc');
  });

  it('actualiza el estado cuando el usuario cambia de localidad', () => {
    const nodo = componentes.selectorLocalidad('Localidad', 'sel-loc');
    const select = nodo.querySelector('select');

    select.value = '20';
    select.dispatchEvent(new Event('change'));

    expect(estado.localidadId()).toBe(20);
  });
});

describe('sincronizarSelector', () => {
  it('alinea un selector ya montado con la localidad activa', () => {
    estado.definirLocalidades(LOCALIDADES, 13);
    document.body.appendChild(componentes.selectorLocalidad('Localidad', 'sel-loc'));

    estado.seleccionarLocalidad(8);
    componentes.sincronizarSelector('sel-loc');

    expect(document.getElementById('sel-loc').value).toBe('8');
  });

  it('no falla si el selector no está en la página', () => {
    expect(() => componentes.sincronizarSelector('no-existe')).not.toThrow();
  });
});

describe('campoNumero', () => {
  it('traslada la configuración a los atributos del input', () => {
    const nodo = componentes.campoNumero({
      id: 'temp', etiqueta: 'Temperatura', valor: 18.5, min: -2, max: 30, paso: 0.1,
    });
    const input = nodo.querySelector('input');

    expect(input.type).toBe('number');
    expect(input.getAttribute('value')).toBe('18.5');
    expect(input.getAttribute('min')).toBe('-2');
    expect(input.getAttribute('max')).toBe('30');
    expect(input.getAttribute('step')).toBe('0.1');
    expect(nodo.querySelector('.campo__etiqueta').textContent).toBe('Temperatura');
  });
});

describe('campoDeslizador', () => {
  it('muestra el valor inicial junto a la etiqueta', () => {
    const nodo = componentes.campoDeslizador({
      id: 'luz', etiqueta: 'Luz', valor: 600, min: 0, max: 1100,
    });

    expect(nodo.querySelector('output').textContent).toBe('600');
    expect(nodo.querySelector('input').type).toBe('range');
  });

  it('actualiza la lectura mientras se arrastra', () => {
    const nodo = componentes.campoDeslizador({
      id: 'luz', etiqueta: 'Luz', valor: 600, min: 0, max: 1100,
    });
    const input = nodo.querySelector('input');

    input.value = '850';
    input.dispatchEvent(new Event('input'));

    expect(nodo.querySelector('output').textContent).toBe('850');
  });
});

describe('bloqueGrafico', () => {
  it('crea el lienzo con su identificador', () => {
    const nodo = componentes.bloqueGrafico('Serie', 'gr-serie');

    expect(nodo.querySelector('figcaption').textContent).toBe('Serie');
    expect(nodo.querySelector('canvas').id).toBe('gr-serie');
  });

  it('sin modificador no deja espacios sueltos en la clase', () => {
    const canvas = componentes.bloqueGrafico('Serie', 'gr').querySelector('canvas');

    expect(canvas.className).toBe('grafico__lienzo');
  });

  it('aplica el modificador cuando se pasa', () => {
    const canvas = componentes.bloqueGrafico('Serie', 'gr', 'grafico__lienzo--alto')
      .querySelector('canvas');

    expect(canvas.className).toBe('grafico__lienzo grafico__lienzo--alto');
  });
});

describe('boton', () => {
  it('es de tipo button para no enviar formularios sin querer', () => {
    expect(componentes.boton('Iniciar', () => {}).getAttribute('type')).toBe('button');
  });

  it('ejecuta la acción al pulsarlo', () => {
    const accion = vi.fn();
    const nodo = componentes.boton('Iniciar', accion);

    nodo.dispatchEvent(new Event('click'));

    expect(accion).toHaveBeenCalledTimes(1);
  });

  it('marca el botón primario', () => {
    expect(componentes.boton('Iniciar', () => {}, { primario: true }).className)
      .toBe('boton boton--primario');
  });

  it('puede nacer deshabilitado', () => {
    expect(componentes.boton('Iniciar', () => {}, { deshabilitado: true }).disabled).toBe(true);
  });

  it('por defecto está habilitado y no es primario', () => {
    const nodo = componentes.boton('Iniciar', () => {});

    expect(nodo.disabled).toBe(false);
    expect(nodo.className).toBe('boton');
  });
});

describe('insignia', () => {
  it.each(['vivo', 'atrasado', 'caido'])('refleja el nivel %s', (nivel) => {
    const nodo = componentes.insignia(nivel, 'En vivo');

    expect(nodo.className).toBe(`insignia insignia--${nivel}`);
    expect(nodo.querySelector('.insignia__punto')).not.toBeNull();
    expect(nodo.textContent).toBe('En vivo');
  });
});
