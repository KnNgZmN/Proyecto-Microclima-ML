/**
 * Pestaña "Datos históricos": resumen del dataset, lectura vigente,
 * predicción a 30 minutos y evolución reciente de la localidad activa.
 */

import { rutas } from '../api.js';
import { aviso, crear, reemplazar, tabla } from '../dom.js';
import {
  bloqueGrafico, insignia, rejillaMetricas, seccion, selectorLocalidad, sincronizarSelector,
} from '../componentes.js';
import * as estado from '../estado.js';
import * as formato from '../formato.js';
import { graficoLineas } from '../graficos.js';

const PUNTOS_SERIE = 144;
const FILAS_TABLA = 12;
const ID_SELECTOR = 'selector-historicos';

const refs = {};

/**
 * Construye la estructura fija de la pestaña.
 * @param {HTMLElement} raiz
 */
function montar(raiz) {
  refs.selector = crear('div', { clase: 'barra-filtros' }, [
    selectorLocalidad('Localidad de Bogotá', ID_SELECTOR),
  ]);
  refs.resumen = crear('div', {});
  refs.contexto = crear('p', { clase: 'contexto' });
  refs.actual = crear('div', {});
  refs.tabla = crear('div', {});
  refs.graficos = crear('div', { clase: 'rejilla-graficos' }, [
    bloqueGrafico('Temperatura y humedad — últimas 24 h', 'grafico-historico'),
  ]);

  reemplazar(raiz, [
    refs.selector,
    refs.resumen,
    refs.contexto,
    seccion('Lectura vigente', [refs.actual]),
    seccion('Últimas lecturas', [refs.tabla]),
    seccion('Evolución reciente', [refs.graficos]),
  ]);
}

/**
 * Pinta las métricas globales del dataset.
 * @param {Object} resumen
 */
function pintarResumen(resumen) {
  reemplazar(refs.resumen, [rejillaMetricas([
    { etiqueta: 'Registros totales', valor: formato.entero(resumen.registros) },
    { etiqueta: 'Temp. promedio global', valor: `${formato.numero(resumen.temp_media, 1)} °C` },
    { etiqueta: 'Humedad promedio', valor: `${formato.numero(resumen.humedad_media, 0)} %` },
    {
      etiqueta: resumen.tiene_localidades ? 'Localidades' : 'Días cubiertos',
      valor: formato.entero(resumen.tiene_localidades ? resumen.localidades : resumen.dias),
      detalle: `${formato.entero(resumen.registros_localidad)} registros en la localidad`,
    },
  ])]);
}

/** Muestra altitud, densidad y zona de la localidad activa. */
function pintarContexto() {
  const loc = estado.localidadActiva();
  refs.contexto.textContent = loc
    ? `${loc.nombre} · Altitud ${formato.entero(loc.altitud)} m · `
      + `Densidad urbana ${formato.porcentaje(loc.densidad_urbana)} · Zona ${loc.zona}`
    : '';
}

/**
 * Traduce el origen de la lectura a una insignia de estado.
 * @param {Object} actual
 * @returns {HTMLElement}
 */
function insigniaOrigen(actual) {
  if (actual.origen === 'arduino') {
    return insignia('vivo', 'Datos en vivo desde el Arduino');
  }
  const nivel = actual.antiguedad_min < 10 ? 'atrasado' : 'caido';
  return insignia(nivel, `Última lectura del dataset · hace ${formato.entero(actual.antiguedad_min)} min`);
}

/**
 * Pinta la lectura vigente y la predicción asociada.
 * @param {Object} actual
 */
function pintarActual(actual) {
  if (!actual.lectura) {
    reemplazar(refs.actual, [aviso('aviso', 'No hay lecturas para esta localidad todavía.')]);
    return;
  }

  const { lectura } = actual;
  const metricas = [
    { etiqueta: 'Temperatura', valor: `${formato.numero(lectura.temperatura, 2)} °C` },
    { etiqueta: 'Humedad', valor: `${formato.numero(lectura.humedad, 1)} %` },
    { etiqueta: 'Luz', valor: `${formato.numero(lectura.luz, 0)} lux` },
    { etiqueta: 'Ruido', valor: `${formato.numero(lectura.ruido, 0)} dB` },
  ];

  const bloques = [insigniaOrigen(actual), rejillaMetricas(metricas)];
  if (actual.prediccion !== null) {
    bloques.push(rejillaMetricas([
      {
        etiqueta: 'Predicción T+30 min',
        valor: `${formato.numero(actual.prediccion, 2)} °C`,
        detalle: `Medida a las ${formato.hora(lectura.timestamp)}`,
      },
      {
        etiqueta: 'Cambio esperado',
        valor: `${formato.conSigno(actual.delta, 2)} °C`,
      },
    ]));
  } else {
    bloques.push(aviso('info', 'Modelo no disponible: ejecuta train_model.py para ver predicciones.'));
  }
  reemplazar(refs.actual, bloques);
}

/**
 * Pinta la tabla de últimas lecturas.
 * @param {Object} datos
 */
function pintarTabla(datos) {
  if (datos.filas.length === 0) {
    reemplazar(refs.tabla, [aviso('info', 'Sin registros para mostrar.')]);
    return;
  }
  const filas = datos.filas.map((fila) => datos.columnas.map((col) => String(fila[col])));
  reemplazar(refs.tabla, [tabla(datos.columnas, filas)]);
}

/**
 * Dibuja la serie temporal de temperatura y humedad.
 * @param {Object} serie
 */
function pintarGrafico(serie) {
  const canvas = document.getElementById('grafico-historico');
  if (!canvas) {
    return;
  }
  graficoLineas(canvas, {
    etiquetas: serie.puntos.map((punto) => formato.hora(punto.timestamp)),
    principal: serie.puntos.map((punto) => punto.temperatura),
    secundaria: serie.puntos.map((punto) => punto.humedad),
  });
}

/** Descarga y pinta todos los datos de la pestaña. */
async function actualizar() {
  sincronizarSelector(ID_SELECTOR);
  pintarContexto();

  const localidad = estado.localidadId();
  const [resumen, actual, ultimas, serie] = await Promise.all([
    rutas.resumen(localidad),
    rutas.actual(localidad, estado.entornoInterior()),
    rutas.ultimas(localidad, FILAS_TABLA),
    rutas.serie(localidad, PUNTOS_SERIE),
  ]);

  pintarResumen(resumen);
  pintarActual(actual);
  pintarTabla(ultimas);
  pintarGrafico(serie);
}

export const vista = {
  id: 'historicos',
  titulo: 'Datos históricos',
  montar,
  actualizar,
};
