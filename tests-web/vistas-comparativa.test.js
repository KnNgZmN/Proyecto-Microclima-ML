/**
 * Pruebas de web/js/vistas/comparativa.js — pestaña de comparación entre
 * localidades.
 *
 * @vitest-environment jsdom
 *
 * La API se sustituye por un doble: la vista se prueba contra respuestas
 * controladas, no contra el backend. Las gráficas se dibujan sobre canvas
 * que en jsdom no tienen tamaño, así que graficos.js sale temprano por su
 * propia guarda y no hace falta simular el contexto 2D aquí.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../web/js/api.js', () => ({
  rutas: { comparativa: vi.fn() },
}));

let vista;
let rutas;
let raiz;

const FILAS = [
  {
    localidad: 'Kennedy',
    zona: 'Occidente',
    altitud: 2570,
    temp_min: 12.4,
    temp_media: 20.64,
    temp_max: 26.1,
    humedad_med: 64.42,
  },
  {
    localidad: 'Sumapaz',
    zona: 'Rural-Páramo',
    altitud: 3150,
    temp_min: 3.2,
    temp_media: 10.21,
    temp_max: 15.8,
    humedad_med: 82.05,
  },
];

beforeEach(async () => {
  vi.resetModules();
  document.body.innerHTML = '';
  raiz = document.createElement('div');
  document.body.appendChild(raiz);

  ({ rutas } = await import('../web/js/api.js'));
  ({ vista } = await import('../web/js/vistas/comparativa.js'));
});

describe('descripción de la vista', () => {
  it('se identifica para el enrutador', () => {
    expect(vista.id).toBe('comparativa');
    expect(vista.titulo).toBe('Comparativa de localidades');
  });

  it('no se refresca sola: los datos históricos no cambian solos', () => {
    expect(vista.autoRefresco).toBe(false);
  });
});

describe('montar', () => {
  beforeEach(() => {
    vista.montar(raiz);
  });

  it('crea las tres secciones de la pestaña', () => {
    expect(raiz.querySelectorAll('.seccion')).toHaveLength(3);
  });

  it('deja listos los dos lienzos con su identificador', () => {
    expect(raiz.querySelector('#grafico-barras')).not.toBeNull();
    expect(raiz.querySelector('#grafico-dispersion')).not.toBeNull();
  });

  it('reemplaza el contenido previo de la raíz', () => {
    raiz.appendChild(document.createElement('p'));

    vista.montar(raiz);

    expect(raiz.querySelectorAll('p')).toHaveLength(0);
  });
});

describe('actualizar con datos', () => {
  beforeEach(async () => {
    rutas.comparativa.mockResolvedValue({ disponible: true, filas: FILAS });
    vista.montar(raiz);
    await vista.actualizar();
  });

  it('pinta una fila por localidad', () => {
    expect(raiz.querySelectorAll('tbody tr')).toHaveLength(2);
  });

  it('rotula las siete columnas de estadísticas', () => {
    expect(raiz.querySelectorAll('th')).toHaveLength(7);
  });

  it('formatea los valores con la convención es-CO', () => {
    const celdas = [...raiz.querySelectorAll('tbody tr')[0].querySelectorAll('td')]
      .map((td) => td.textContent);

    expect(celdas[0]).toBe('Kennedy');
    expect(celdas[2]).toBe('2.570');    // altitud, con separador de miles
    expect(celdas[4]).toBe('20,64');    // temperatura media, coma decimal
  });

  it('no muestra ningún aviso', () => {
    expect(raiz.querySelector('.aviso')).toBeNull();
  });
});

describe('actualizar sin datos utilizables', () => {
  it.each([
    ['el dataset no tiene columna de localidad', { disponible: false, filas: [] }],
    ['la comparativa viene vacía', { disponible: true, filas: [] }],
  ])('avisa cuando %s', async (_caso, respuesta) => {
    rutas.comparativa.mockResolvedValue(respuesta);
    vista.montar(raiz);

    await vista.actualizar();

    const nota = raiz.querySelector('.aviso');
    expect(nota).not.toBeNull();
    expect(nota.textContent).toContain('generate_dataset.py');
  });

  it('deja la tabla vacía en lugar de conservar datos viejos', async () => {
    rutas.comparativa.mockResolvedValue({ disponible: true, filas: FILAS });
    vista.montar(raiz);
    await vista.actualizar();
    expect(raiz.querySelectorAll('tbody tr')).toHaveLength(2);

    rutas.comparativa.mockResolvedValue({ disponible: false, filas: [] });
    await vista.actualizar();

    expect(raiz.querySelectorAll('tbody tr')).toHaveLength(0);
  });

  it('retira el aviso cuando los datos vuelven a estar disponibles', async () => {
    rutas.comparativa.mockResolvedValue({ disponible: false, filas: [] });
    vista.montar(raiz);
    await vista.actualizar();
    expect(raiz.querySelector('.aviso')).not.toBeNull();

    rutas.comparativa.mockResolvedValue({ disponible: true, filas: FILAS });
    await vista.actualizar();

    expect(raiz.querySelector('.aviso')).toBeNull();
  });
});

describe('gráficas', () => {
  it('no falla cuando todas las localidades tienen la misma media', async () => {
    const iguales = FILAS.map((fila) => ({ ...fila, temp_media: 18 }));
    rutas.comparativa.mockResolvedValue({ disponible: true, filas: iguales });
    vista.montar(raiz);

    await expect(vista.actualizar()).resolves.not.toThrow();
  });

  it('no falla si los lienzos no están en la página', async () => {
    rutas.comparativa.mockResolvedValue({ disponible: true, filas: FILAS });
    vista.montar(raiz);
    raiz.querySelector('#grafico-barras').remove();
    raiz.querySelector('#grafico-dispersion').remove();

    await expect(vista.actualizar()).resolves.not.toThrow();
  });
});
