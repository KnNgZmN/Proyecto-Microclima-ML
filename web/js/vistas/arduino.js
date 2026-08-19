/**
 * Pestaña "Arduino en vivo": control del colector, lectura publicada en
 * latest.json, historial reciente y descarga del dataset.
 */

import { rutas } from '../api.js';
import { aviso, crear, reemplazar, tabla } from '../dom.js';
import {
  bloqueGrafico, boton, insignia, rejillaMetricas, seccion, selectorLocalidad,
  sincronizarSelector,
} from '../componentes.js';
import * as estado from '../estado.js';
import * as formato from '../formato.js';
import { graficoLineas } from '../graficos.js';

const BAUDIOS = [9600, 115200];
const PUNTOS_RECIENTES = 120;
const FILAS_TABLA = 10;
const ID_SELECTOR = 'selector-arduino';

const refs = {};
let puertoElegido = 'COM3';
let puertoEditado = false;
let puertosConocidos = [];

/** Campo de texto para el puerto serie. */
function campoPuerto() {
  const input = crear('input', {
    clase: 'campo__control',
    attrs: { type: 'text', id: 'ard-puerto', value: puertoElegido },
  });
  input.addEventListener('input', () => {
    puertoElegido = input.value.trim();
    puertoEditado = true;
  });
  return crear('label', { clase: 'campo', attrs: { for: 'ard-puerto' } }, [
    crear('span', { clase: 'campo__etiqueta', texto: 'Puerto serial' }),
    input,
  ]);
}

/** Desplegable de velocidad del puerto. */
function campoBaudios() {
  const select = crear('select', { clase: 'campo__control', attrs: { id: 'ard-baud' } });
  BAUDIOS.forEach((baud) => {
    select.appendChild(crear('option', { texto: String(baud), attrs: { value: baud } }));
  });
  return crear('label', { clase: 'campo', attrs: { for: 'ard-baud' } }, [
    crear('span', { clase: 'campo__etiqueta', texto: 'Baud rate' }),
    select,
  ]);
}

/** Interruptor del modo de entorno interior. */
function campoInterior() {
  const input = crear('input', { attrs: { type: 'checkbox', id: 'ard-interior' } });
  input.checked = estado.entornoInterior();
  input.addEventListener('change', () => estado.definirEntornoInterior(input.checked));

  return crear('label', { clase: 'campo campo--interruptor', attrs: { for: 'ard-interior' } }, [
    input,
    crear('span', { clase: 'campo__etiqueta', texto: 'Entorno interior' }),
    crear('span', {
      clase: 'campo__ayuda',
      texto: 'Escala la luz del sensor al rango exterior que espera el modelo.',
    }),
  ]);
}

/** Construye la estructura fija de la pestaña. */
function montar(raiz) {
  refs.puertos = crear('p', { clase: 'contexto' });
  refs.estadoColector = crear('div', {});
  refs.live = crear('div', {});
  refs.tabla = crear('div', {});
  refs.descarga = crear('div', { clase: 'acciones' });
  refs.selector = crear('div', {});

  const controles = crear('div', { clase: 'formulario' }, [
    campoPuerto(),
    refs.selector,
    campoBaudios(),
    campoInterior(),
  ]);

  const acciones = crear('div', { clase: 'acciones' }, [
    boton('Iniciar Arduino real', () => iniciar('real'), { primario: true }),
    boton('Iniciar simulación', () => iniciar('simulacion')),
    boton('Detener', detener),
  ]);

  reemplazar(raiz, [
    seccion('Control del colector', [refs.puertos, controles, acciones, refs.estadoColector]),
    seccion('Lectura en vivo', [refs.live]),
    seccion('Historial reciente', [
      bloqueGrafico('Temperatura y humedad de la localidad activa', 'grafico-arduino'),
      refs.tabla,
    ]),
    seccion('Dataset completo', [refs.descarga]),
  ]);

  reemplazar(refs.selector, [selectorLocalidad('Localidad del Arduino', ID_SELECTOR)]);
  reemplazar(refs.descarga, [
    crear('a', {
      clase: 'boton boton--enlace',
      texto: 'Descargar dataset (CSV)',
      attrs: { href: rutas.urlCsv(), download: 'microclima_bogota.csv' },
    }),
  ]);
}

/**
 * Lanza el colector en el modo indicado.
 * @param {'real'|'simulacion'} modo
 */
async function iniciar(modo) {
  const baud = Number(document.getElementById('ard-baud').value);
  try {
    const respuesta = await rutas.colectorIniciar({
      modo,
      puerto: puertoElegido,
      baud,
      localidad_id: estado.localidadId(),
    });
    pintarEstadoColector(respuesta);
  } catch (error) {
    reemplazar(refs.estadoColector, [aviso('error', error.message)]);
  }
}

/** Detiene el colector en ejecución. */
async function detener() {
  pintarEstadoColector(await rutas.colectorDetener());
}

/**
 * Pinta el estado del subproceso colector.
 * @param {Object} estadoColector
 */
function pintarEstadoColector(estadoColector) {
  puertosConocidos = estadoColector.puertos || [];
  refs.puertos.textContent = puertosConocidos.length > 0
    ? `Puertos detectados: ${puertosConocidos.join(', ')}`
    : 'No se detectaron puertos COM. Conecta el Arduino antes de iniciar.';

  const bloques = [];
  if (estadoColector.activo) {
    bloques.push(insignia('vivo', `Colector en ejecución (PID ${estadoColector.pid}) · modo ${estadoColector.modo}`));
  } else if (estadoColector.error) {
    bloques.push(aviso('error', estadoColector.error));
  } else {
    bloques.push(aviso('info', 'Colector detenido. Inicia el Arduino real o la simulación.'));
  }
  reemplazar(refs.estadoColector, bloques);
}

/**
 * Pinta la lectura publicada por el colector.
 * @param {Object} live
 * @param {Object} actual
 */
function pintarLive(live, actual) {
  if (!live.disponible) {
    reemplazar(refs.live, [aviso('info', 'Sin datos en vivo todavía. Inicia el colector.')]);
    return;
  }

  const lectura = live.lectura;
  const bloques = [
    insignia(formato.nivelFrescura(live.antiguedad_s),
      `Actualizado ${formato.antiguedad(live.antiguedad_s)} · ${lectura.localidad}`),
    rejillaMetricas([
      { etiqueta: 'Temperatura', valor: `${formato.numero(lectura.temperatura, 2)} °C` },
      { etiqueta: 'Humedad', valor: `${formato.numero(lectura.humedad, 1)} %` },
      {
        etiqueta: 'Luz',
        valor: `${formato.numero(lectura.luz, 0)} lux`,
        detalle: estado.entornoInterior()
          ? `Modelo: ${formato.numero(actual.luz_modelo, 0)} lux`
          : undefined,
      },
      { etiqueta: 'Ruido', valor: `${formato.numero(lectura.ruido, 0)} dB` },
    ]),
  ];

  if (actual.prediccion !== null && actual.prediccion !== undefined) {
    bloques.push(rejillaMetricas([
      { etiqueta: 'Predicción T+30 min', valor: `${formato.numero(actual.prediccion, 2)} °C` },
      { etiqueta: 'Cambio esperado', valor: `${formato.conSigno(actual.delta, 2)} °C` },
    ]));
  }

  bloques.push(crear('div', { clase: 'acciones' }, [
    boton('Usar esta lectura en la pestaña de predicción', () => enviarAPrediccion(lectura)),
  ]));

  reemplazar(refs.live, bloques);
}

/**
 * Copia la lectura viva al formulario de predicción y cambia de pestaña.
 * @param {Object} lectura
 */
function enviarAPrediccion(lectura) {
  document.dispatchEvent(new CustomEvent('microclima:precargar', { detail: lectura }));
  document.dispatchEvent(new CustomEvent('microclima:navegar', { detail: { id: 'prediccion' } }));
}

/**
 * Dibuja la serie reciente y la tabla de lecturas.
 * @param {Object} serie
 * @param {Object} ultimas
 */
function pintarHistorial(serie, ultimas) {
  const canvas = document.getElementById('grafico-arduino');
  if (canvas) {
    graficoLineas(canvas, {
      etiquetas: serie.puntos.map((punto) => formato.hora(punto.timestamp)),
      principal: serie.puntos.map((punto) => punto.temperatura),
      secundaria: serie.puntos.map((punto) => punto.humedad),
    });
  }

  if (ultimas.filas.length === 0) {
    reemplazar(refs.tabla, [aviso('info', 'No hay registros para esta localidad todavía.')]);
    return;
  }
  reemplazar(refs.tabla, [tabla(
    ultimas.columnas,
    ultimas.filas.map((fila) => ultimas.columnas.map((col) => String(fila[col]))),
  )]);
}

/** Propone el primer puerto detectado mientras el usuario no escriba uno. */
function sugerirPuerto() {
  const input = document.getElementById('ard-puerto');
  const sugerible = !puertoEditado && puertosConocidos.length > 0
    && !puertosConocidos.includes(puertoElegido);
  if (input && sugerible) {
    [puertoElegido] = puertosConocidos;
    input.value = puertoElegido;
  }
}

/** Descarga y pinta todos los datos de la pestaña. */
async function actualizar() {
  sincronizarSelector(ID_SELECTOR);
  const localidad = estado.localidadId();
  const [estadoColector, live, actual, serie, ultimas] = await Promise.all([
    rutas.colectorEstado(),
    rutas.live(localidad),
    rutas.actual(localidad, estado.entornoInterior()),
    rutas.serie(localidad, PUNTOS_RECIENTES),
    rutas.ultimas(localidad, FILAS_TABLA),
  ]);

  pintarEstadoColector(estadoColector);
  sugerirPuerto();
  pintarLive(live, actual);
  pintarHistorial(serie, ultimas);
}

export const vista = {
  id: 'arduino',
  titulo: 'Arduino en vivo',
  montar,
  actualizar,
};
