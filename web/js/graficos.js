/**
 * Gráficas dibujadas sobre <canvas> con la API 2D del navegador.
 * Sustituyen a las figuras de matplotlib que generaba la versión Streamlit,
 * sin depender de ninguna librería externa.
 */

export const PALETA = {
  temperatura: '#e0642a',
  humedad: '#3d8bfd',
  rejilla: 'rgba(148, 163, 184, 0.22)',
  texto: '#94a3b8',
  frio: '#3d8bfd',
  calor: '#e0642a',
};

const MARGEN = { arriba: 18, derecha: 56, abajo: 30, izquierda: 52 };
const TICKS_Y = 4;

/**
 * Prepara el contexto 2D ajustado a la densidad de pantalla.
 * @param {HTMLCanvasElement} canvas
 * @returns {{ctx: CanvasRenderingContext2D, ancho: number, alto: number}|null}
 */
function preparar(canvas) {
  const ancho = canvas.clientWidth;
  const alto = canvas.clientHeight;
  if (ancho === 0 || alto === 0) {
    return null;
  }
  const escala = window.devicePixelRatio || 1;
  canvas.width = Math.round(ancho * escala);
  canvas.height = Math.round(alto * escala);

  const ctx = canvas.getContext('2d');
  ctx.setTransform(escala, 0, 0, escala, 0, 0);
  ctx.clearRect(0, 0, ancho, alto);
  ctx.font = '11px system-ui, sans-serif';
  return { ctx, ancho, alto };
}

/**
 * Área útil de dibujo dentro del lienzo.
 * @param {number} ancho
 * @param {number} alto
 * @param {{izquierda?: number, derecha?: number}} extra
 */
function area(ancho, alto, extra = {}) {
  const izquierda = extra.izquierda ?? MARGEN.izquierda;
  const derecha = extra.derecha ?? MARGEN.derecha;
  return {
    x0: izquierda,
    y0: MARGEN.arriba,
    x1: ancho - derecha,
    y1: alto - MARGEN.abajo,
    ancho: ancho - izquierda - derecha,
    alto: alto - MARGEN.arriba - MARGEN.abajo,
  };
}

/**
 * Crea una función de escala lineal entre un dominio y un rango.
 * @param {[number, number]} dominio
 * @param {[number, number]} rango
 * @returns {(valor: number) => number}
 */
function escalaLineal([min, max], [inicio, fin]) {
  const amplitud = max - min || 1;
  return (valor) => inicio + ((valor - min) / amplitud) * (fin - inicio);
}

/**
 * Extremos de una lista de números con un margen del 5 %.
 * @param {Array<number>} valores
 * @returns {[number, number]}
 */
function extremos(valores) {
  const min = Math.min(...valores);
  const max = Math.max(...valores);
  const holgura = (max - min) * 0.08 || 1;
  return [min - holgura, max + holgura];
}

/**
 * Dibuja la rejilla horizontal y las etiquetas del eje vertical.
 * @param {CanvasRenderingContext2D} ctx
 * @param {Object} caja
 * @param {[number, number]} dominio
 * @param {string} color
 * @param {'izquierda'|'derecha'} lado
 */
function ejeVertical(ctx, caja, dominio, color, lado) {
  const escala = escalaLineal(dominio, [caja.y1, caja.y0]);
  ctx.strokeStyle = PALETA.rejilla;
  ctx.fillStyle = color;
  ctx.textBaseline = 'middle';
  ctx.textAlign = lado === 'izquierda' ? 'right' : 'left';

  for (let i = 0; i <= TICKS_Y; i += 1) {
    const valor = dominio[0] + ((dominio[1] - dominio[0]) * i) / TICKS_Y;
    const y = escala(valor);
    if (lado === 'izquierda') {
      ctx.beginPath();
      ctx.moveTo(caja.x0, y);
      ctx.lineTo(caja.x1, y);
      ctx.stroke();
      ctx.fillText(valor.toFixed(1), caja.x0 - 8, y);
    } else {
      ctx.fillText(valor.toFixed(0), caja.x1 + 8, y);
    }
  }
  return escala;
}

/**
 * Escribe las etiquetas del eje horizontal repartidas de forma uniforme.
 * @param {CanvasRenderingContext2D} ctx
 * @param {Object} caja
 * @param {Array<string>} etiquetas
 */
function ejeHorizontal(ctx, caja, etiquetas) {
  if (etiquetas.length === 0) {
    return;
  }
  const maximo = Math.min(6, etiquetas.length);
  const paso = Math.max(1, Math.floor(etiquetas.length / maximo));
  ctx.fillStyle = PALETA.texto;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';

  for (let i = 0; i < etiquetas.length; i += paso) {
    const x = caja.x0 + (caja.ancho * i) / Math.max(1, etiquetas.length - 1);
    ctx.fillText(etiquetas[i], x, caja.y1 + 8);
  }
}

/**
 * Traza una serie como polilínea.
 * @param {CanvasRenderingContext2D} ctx
 * @param {Object} caja
 * @param {Array<number>} valores
 * @param {(v: number) => number} escalaY
 * @param {string} color
 * @param {number} grosor
 */
function trazarSerie(ctx, caja, valores, escalaY, color, grosor) {
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = grosor;
  ctx.lineJoin = 'round';
  valores.forEach((valor, indice) => {
    const x = caja.x0 + (caja.ancho * indice) / Math.max(1, valores.length - 1);
    const y = escalaY(valor);
    if (indice === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();
}

/**
 * Gráfica de líneas con eje secundario opcional.
 * @param {HTMLCanvasElement} canvas
 * @param {{etiquetas: Array<string>, principal: Array<number>,
 *          secundaria?: Array<number>}} datos
 */
export function graficoLineas(canvas, datos) {
  const lienzo = preparar(canvas);
  if (!lienzo || datos.principal.length === 0) {
    return;
  }
  const { ctx, ancho, alto } = lienzo;
  const tieneSecundaria = Array.isArray(datos.secundaria) && datos.secundaria.length > 0;
  const caja = area(ancho, alto, tieneSecundaria ? {} : { derecha: 18 });

  const escalaIzq = ejeVertical(ctx, caja, extremos(datos.principal), PALETA.temperatura, 'izquierda');
  trazarSerie(ctx, caja, datos.principal, escalaIzq, PALETA.temperatura, 1.8);

  if (tieneSecundaria) {
    const escalaDer = ejeVertical(ctx, caja, extremos(datos.secundaria), PALETA.humedad, 'derecha');
    trazarSerie(ctx, caja, datos.secundaria, escalaDer, PALETA.humedad, 1.2);
  }

  ejeHorizontal(ctx, caja, datos.etiquetas);
}

/**
 * Interpola entre el azul frío y el naranja cálido según la posición 0-1.
 * @param {number} proporcion
 * @returns {string} Color CSS.
 */
export function colorTermico(proporcion) {
  const t = Math.min(1, Math.max(0, proporcion));
  const canal = (frio, calor) => Math.round(frio + (calor - frio) * t);
  return `rgb(${canal(61, 224)}, ${canal(139, 100)}, ${canal(253, 42)})`;
}

/**
 * Gráfica de barras horizontales, una por categoría.
 * @param {HTMLCanvasElement} canvas
 * @param {{items: Array<{etiqueta: string, valor: number}>}} datos
 */
export function graficoBarras(canvas, datos) {
  const lienzo = preparar(canvas);
  if (!lienzo || datos.items.length === 0) {
    return;
  }
  const { ctx, ancho, alto } = lienzo;
  const caja = area(ancho, alto, { izquierda: 132, derecha: 44 });

  const valores = datos.items.map((item) => item.valor);
  const minimo = Math.min(...valores);
  const maximo = Math.max(...valores);
  const escalaX = escalaLineal([Math.min(0, minimo * 0.98), maximo * 1.02], [caja.x0, caja.x1]);
  const altoBarra = caja.alto / datos.items.length;

  ctx.textBaseline = 'middle';
  datos.items.forEach((item, indice) => {
    const y = caja.y0 + altoBarra * indice;
    const proporcion = maximo === minimo ? 0.5 : (item.valor - minimo) / (maximo - minimo);
    ctx.fillStyle = colorTermico(proporcion);
    ctx.fillRect(caja.x0, y + altoBarra * 0.15, escalaX(item.valor) - caja.x0, altoBarra * 0.7);

    ctx.fillStyle = PALETA.texto;
    ctx.textAlign = 'right';
    ctx.fillText(item.etiqueta, caja.x0 - 8, y + altoBarra / 2);
    ctx.textAlign = 'left';
    ctx.fillText(item.valor.toFixed(2), escalaX(item.valor) + 6, y + altoBarra / 2);
  });
}

/**
 * Gráfica de dispersión con etiqueta junto a cada punto.
 * @param {HTMLCanvasElement} canvas
 * @param {{puntos: Array<{x: number, y: number, etiqueta: string, intensidad: number}>,
 *          tituloX: string, tituloY: string}} datos
 */
export function graficoDispersion(canvas, datos) {
  const lienzo = preparar(canvas);
  if (!lienzo || datos.puntos.length === 0) {
    return;
  }
  const { ctx, ancho, alto } = lienzo;
  const caja = area(ancho, alto, { derecha: 24 });

  const escalaX = escalaLineal(extremos(datos.puntos.map((p) => p.x)), [caja.x0, caja.x1]);
  const escalaY = ejeVertical(ctx, caja, extremos(datos.puntos.map((p) => p.y)),
    PALETA.texto, 'izquierda');

  datos.puntos.forEach((punto) => {
    const x = escalaX(punto.x);
    const y = escalaY(punto.y);
    ctx.beginPath();
    ctx.fillStyle = colorTermico(punto.intensidad);
    ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = PALETA.texto;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'bottom';
    ctx.fillText(punto.etiqueta, x + 7, y - 2);
  });

  ctx.fillStyle = PALETA.texto;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  ctx.fillText(datos.tituloX, (caja.x0 + caja.x1) / 2, caja.y1 + 10);
}
