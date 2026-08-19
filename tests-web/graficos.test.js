/**
 * Pruebas de web/js/graficos.js — gráficas dibujadas sobre <canvas>.
 *
 * @vitest-environment jsdom
 *
 * jsdom no implementa la API 2D del canvas, así que se inyecta un lienzo
 * falso cuyo contexto registra cada llamada de dibujo. No se comprueba
 * cómo se ve el resultado —eso no lo puede juzgar una prueba unitaria—
 * sino la lógica: que se dibuje una barra por dato, un punto por muestra,
 * y que no se dibuje nada cuando no hay qué dibujar.
 */
import { describe, expect, it } from 'vitest';
import { colorTermico, graficoBarras, graficoDispersion, graficoLineas } from '../web/js/graficos.js';

/** Contexto 2D falso que anota cada operación recibida. */
function contextoFalso() {
  const llamadas = [];
  const anotar = (nombre) => (...args) => llamadas.push({ nombre, args });

  return {
    llamadas,
    // Propiedades de estilo: el módulo las asigna, no las lee.
    font: '',
    fillStyle: '',
    strokeStyle: '',
    lineWidth: 0,
    lineJoin: '',
    textAlign: '',
    textBaseline: '',
    // Operaciones de dibujo.
    setTransform: anotar('setTransform'),
    clearRect: anotar('clearRect'),
    beginPath: anotar('beginPath'),
    moveTo: anotar('moveTo'),
    lineTo: anotar('lineTo'),
    stroke: anotar('stroke'),
    fill: anotar('fill'),
    fillRect: anotar('fillRect'),
    fillText: anotar('fillText'),
    arc: anotar('arc'),
  };
}

/** Lienzo falso con tamaño controlado. */
function canvasFalso({ ancho = 600, alto = 300 } = {}) {
  const ctx = contextoFalso();
  return {
    ctx,
    clientWidth: ancho,
    clientHeight: alto,
    width: 0,
    height: 0,
    getContext: () => ctx,
  };
}

/** Cuántas veces se invocó una operación. */
const veces = (ctx, nombre) => ctx.llamadas.filter((l) => l.nombre === nombre).length;
/** Textos escritos en el lienzo. */
const textos = (ctx) => ctx.llamadas.filter((l) => l.nombre === 'fillText').map((l) => l.args[0]);

const SERIE = {
  etiquetas: ['10:00', '10:10', '10:20', '10:30'],
  principal: [18.2, 18.9, 19.4, 19.1],
};

describe('colorTermico', () => {
  it.each([
    [0, 'rgb(61, 139, 253)'],
    [0.25, 'rgb(102, 129, 200)'],
    [0.5, 'rgb(143, 120, 148)'],
    [1, 'rgb(224, 100, 42)'],
  ])('interpola %s hacia %s', (proporcion, esperado) => {
    expect(colorTermico(proporcion)).toBe(esperado);
  });

  it.each([
    [-3, 'rgb(61, 139, 253)'],
    [7, 'rgb(224, 100, 42)'],
  ])('acota la proporción fuera de rango: %s', (proporcion, esperado) => {
    expect(colorTermico(proporcion)).toBe(esperado);
  });
});

describe('preparación del lienzo', () => {
  it('ajusta el tamaño interno a la densidad de pantalla', () => {
    const canvas = canvasFalso({ ancho: 600, alto: 300 });

    graficoLineas(canvas, SERIE);

    const escala = window.devicePixelRatio || 1;
    expect(canvas.width).toBe(Math.round(600 * escala));
    expect(canvas.height).toBe(Math.round(300 * escala));
  });

  it('limpia el lienzo antes de dibujar', () => {
    const canvas = canvasFalso();

    graficoLineas(canvas, SERIE);

    expect(veces(canvas.ctx, 'clearRect')).toBe(1);
  });

  it.each([
    ['sin ancho', { ancho: 0, alto: 300 }],
    ['sin alto', { ancho: 600, alto: 0 }],
  ])('no dibuja nada si el lienzo está %s', (_caso, tamano) => {
    const canvas = canvasFalso(tamano);

    graficoLineas(canvas, SERIE);

    expect(canvas.ctx.llamadas).toHaveLength(0);
  });
});

describe('graficoLineas', () => {
  it('traza la serie principal', () => {
    const canvas = canvasFalso();

    graficoLineas(canvas, SERIE);

    expect(veces(canvas.ctx, 'lineTo')).toBeGreaterThan(0);
    expect(veces(canvas.ctx, 'stroke')).toBeGreaterThan(0);
  });

  it('escribe las etiquetas del eje horizontal', () => {
    const canvas = canvasFalso();

    graficoLineas(canvas, SERIE);

    expect(textos(canvas.ctx)).toContain('10:00');
  });

  it('dibuja más trazos cuando hay una segunda serie', () => {
    const soloUna = canvasFalso();
    const conDos = canvasFalso();

    graficoLineas(soloUna, SERIE);
    graficoLineas(conDos, { ...SERIE, secundaria: [70, 71, 69, 72] });

    expect(veces(conDos.ctx, 'stroke')).toBeGreaterThan(veces(soloUna.ctx, 'stroke'));
  });

  it('ignora una segunda serie vacía', () => {
    const soloUna = canvasFalso();
    const conVacia = canvasFalso();

    graficoLineas(soloUna, SERIE);
    graficoLineas(conVacia, { ...SERIE, secundaria: [] });

    expect(veces(conVacia.ctx, 'stroke')).toBe(veces(soloUna.ctx, 'stroke'));
  });

  it('sin datos limpia el lienzo pero no traza', () => {
    const canvas = canvasFalso();

    graficoLineas(canvas, { etiquetas: [], principal: [] });

    expect(veces(canvas.ctx, 'clearRect')).toBe(1);
    expect(veces(canvas.ctx, 'lineTo')).toBe(0);
  });

  it('sobrevive a una serie de un solo punto', () => {
    const canvas = canvasFalso();

    expect(() => graficoLineas(canvas, { etiquetas: ['10:00'], principal: [18.2] })).not.toThrow();
  });

  it('sobrevive a una serie constante, sin amplitud', () => {
    const canvas = canvasFalso();

    expect(() => graficoLineas(canvas, {
      etiquetas: ['a', 'b', 'c'], principal: [18, 18, 18],
    })).not.toThrow();
  });
});

describe('graficoBarras', () => {
  const ITEMS = {
    items: [
      { etiqueta: 'Kennedy', valor: 20.64 },
      { etiqueta: 'Teusaquillo', valor: 18.30 },
      { etiqueta: 'Sumapaz', valor: 10.21 },
    ],
  };

  it('dibuja una barra por elemento', () => {
    const canvas = canvasFalso();

    graficoBarras(canvas, ITEMS);

    expect(veces(canvas.ctx, 'fillRect')).toBe(3);
  });

  it('escribe la etiqueta y el valor de cada barra', () => {
    const canvas = canvasFalso();

    graficoBarras(canvas, ITEMS);

    const escritos = textos(canvas.ctx);
    expect(escritos).toContain('Kennedy');
    expect(escritos).toContain('20.64');
  });

  it('sin elementos no dibuja barras', () => {
    const canvas = canvasFalso();

    graficoBarras(canvas, { items: [] });

    expect(veces(canvas.ctx, 'fillRect')).toBe(0);
  });

  it('admite valores todos iguales, sin rango que escalar', () => {
    const canvas = canvasFalso();

    expect(() => graficoBarras(canvas, {
      items: [{ etiqueta: 'a', valor: 15 }, { etiqueta: 'b', valor: 15 }],
    })).not.toThrow();
    expect(veces(canvas.ctx, 'fillRect')).toBe(2);
  });

  it('admite valores negativos', () => {
    const canvas = canvasFalso();

    expect(() => graficoBarras(canvas, {
      items: [{ etiqueta: 'a', valor: -2.5 }, { etiqueta: 'b', valor: 4 }],
    })).not.toThrow();
  });
});

describe('graficoDispersion', () => {
  const NUBE = {
    tituloX: 'Altitud (m)',
    tituloY: 'Temperatura (°C)',
    puntos: [
      { x: 2570, y: 20.6, etiqueta: 'Kennedy', intensidad: 1 },
      { x: 2600, y: 18.3, etiqueta: 'Teusaquillo', intensidad: 0.5 },
      { x: 3150, y: 10.2, etiqueta: 'Sumapaz', intensidad: 0 },
    ],
  };

  it('dibuja un punto por muestra', () => {
    const canvas = canvasFalso();

    graficoDispersion(canvas, NUBE);

    expect(veces(canvas.ctx, 'arc')).toBe(3);
    expect(veces(canvas.ctx, 'fill')).toBe(3);
  });

  it('rotula cada punto y el eje horizontal', () => {
    const canvas = canvasFalso();

    graficoDispersion(canvas, NUBE);

    const escritos = textos(canvas.ctx);
    expect(escritos).toContain('Sumapaz');
    expect(escritos).toContain('Altitud (m)');
  });

  it('sin puntos no dibuja nada', () => {
    const canvas = canvasFalso();

    graficoDispersion(canvas, { ...NUBE, puntos: [] });

    expect(veces(canvas.ctx, 'arc')).toBe(0);
  });

  it('sobrevive a un único punto', () => {
    const canvas = canvasFalso();

    expect(() => graficoDispersion(canvas, {
      ...NUBE,
      puntos: [{ x: 2600, y: 18, etiqueta: 'Teusaquillo', intensidad: 0.5 }],
    })).not.toThrow();
  });
});
