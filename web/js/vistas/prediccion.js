/**
 * Pestaña "Predicción por localidad": formulario manual de sensores y
 * resultado del modelo a 30 minutos, con historial de la sesión.
 */

import { rutas } from '../api.js';
import { aviso, crear, reemplazar, tabla } from '../dom.js';
import {
  boton, campoDeslizador, campoNumero, rejillaMetricas, seccion, selectorLocalidad,
  sincronizarSelector,
} from '../componentes.js';
import * as estado from '../estado.js';
import * as formato from '../formato.js';

const ahora = new Date();
const ID_SELECTOR = 'selector-prediccion';

const CAMPOS = [
  { id: 'pred-temperatura', etiqueta: 'Temperatura actual (°C)', valor: 13.5, min: -5, max: 30, paso: 0.1 },
  { id: 'pred-humedad', etiqueta: 'Humedad (%)', valor: 72, min: 30, max: 100, paso: 0.5 },
  { id: 'pred-luz', etiqueta: 'Luz (lux)', valor: 600, min: 0, max: 1100, paso: 10 },
  { id: 'pred-ruido', etiqueta: 'Ruido (dB)', valor: 45, min: 20, max: 110, paso: 1 },
];

const refs = {};

/**
 * Lee un campo del formulario como número.
 * @param {string} id
 * @returns {number}
 */
function valorDe(id) {
  return Number(document.getElementById(id).value);
}

/** Construye la estructura fija de la pestaña. */
function montar(raiz) {
  refs.selector = crear('div', { clase: 'barra-filtros' }, [
    selectorLocalidad('Localidad de Bogotá', ID_SELECTOR),
  ]);
  refs.contexto = crear('div', {});
  refs.resultado = crear('div', {});
  refs.historial = crear('div', {});

  const formulario = crear('div', { clase: 'formulario' }, [
    ...CAMPOS.map((campo) => campoNumero(campo)),
    campoDeslizador({ id: 'pred-hora', etiqueta: 'Hora del día', valor: ahora.getHours(), min: 0, max: 23 }),
    campoDeslizador({ id: 'pred-mes', etiqueta: 'Mes', valor: ahora.getMonth() + 1, min: 1, max: 12 }),
  ]);

  const acciones = crear('div', { clase: 'acciones' }, [
    boton('Predecir temperatura T+30 min', ejecutarPrediccion, { primario: true }),
    boton('Limpiar historial', () => {
      estado.limpiarHistorial();
      pintarHistorial();
    }),
  ]);

  reemplazar(raiz, [
    refs.selector,
    refs.contexto,
    seccion('Valores del sensor', [formulario, acciones]),
    seccion('Resultado', [refs.resultado]),
    seccion('Historial de la sesión', [refs.historial]),
  ]);

  pintarResultado(null);
  pintarHistorial();
  document.addEventListener('microclima:precargar', (evento) => precargar(evento.detail));
}

/**
 * Rellena el formulario con una lectura del Arduino.
 * @param {{temperatura: number, humedad: number, luz: number, ruido: number}} lectura
 */
function precargar(lectura) {
  const mapa = {
    'pred-temperatura': lectura.temperatura,
    'pred-humedad': lectura.humedad,
    'pred-luz': lectura.luz,
    'pred-ruido': lectura.ruido,
  };
  Object.entries(mapa).forEach(([id, valor]) => {
    const campo = document.getElementById(id);
    if (campo && valor !== undefined && valor !== null) {
      campo.value = String(valor);
    }
  });
}

/** Muestra los metadatos geográficos de la localidad seleccionada. */
function pintarContexto() {
  const loc = estado.localidadActiva();
  if (!loc) {
    return;
  }
  reemplazar(refs.contexto, [rejillaMetricas([
    { etiqueta: 'Altitud', valor: `${formato.entero(loc.altitud)} m` },
    { etiqueta: 'Densidad urbana', valor: formato.porcentaje(loc.densidad_urbana) },
    { etiqueta: 'Latitud', valor: `${formato.numero(loc.lat, 4)}°` },
    { etiqueta: 'Longitud', valor: `${formato.numero(loc.lon, 4)}°` },
  ])]);
}

/**
 * Pinta el resultado del modelo o un mensaje de espera.
 * @param {Object|null} resultado
 * @param {string} [error]
 */
function pintarResultado(resultado, error) {
  if (error) {
    reemplazar(refs.resultado, [aviso('error', error)]);
    return;
  }
  if (!resultado) {
    reemplazar(refs.resultado, [
      aviso('info', 'Ajusta los valores del sensor y pulsa "Predecir" para estimar la temperatura.'),
    ]);
    return;
  }
  reemplazar(refs.resultado, [rejillaMetricas([
    {
      etiqueta: `Temperatura estimada en ${resultado.localidad}`,
      valor: `${formato.numero(resultado.prediccion, 2)} °C`,
      detalle: 'Horizonte de 30 minutos',
    },
    {
      etiqueta: 'Cambio esperado',
      valor: `${formato.conSigno(resultado.delta, 2)} °C`,
      detalle: `Desde ${formato.numero(resultado.temperatura_actual, 2)} °C`,
    },
  ])]);
}

/** Pinta la tabla con las lecturas acumuladas en la sesión. */
function pintarHistorial() {
  const filas = estado.historial();
  if (filas.length === 0) {
    reemplazar(refs.historial, [aviso('info', 'Aún no se han registrado lecturas en esta sesión.')]);
    return;
  }
  reemplazar(refs.historial, [tabla(
    ['#', 'Temperatura (°C)', 'Humedad (%)'],
    filas.map((fila, indice) => [
      String(filas.length - indice),
      formato.numero(fila.temperatura, 2),
      formato.numero(fila.humedad, 1),
    ]).reverse(),
  )]);
}

/** Envía el formulario al backend y muestra la predicción. */
async function ejecutarPrediccion() {
  const lectura = {
    temperatura: valorDe('pred-temperatura'),
    humedad: valorDe('pred-humedad'),
    luz: valorDe('pred-luz'),
    ruido: valorDe('pred-ruido'),
    hora: valorDe('pred-hora'),
    mes: valorDe('pred-mes'),
    localidad_id: estado.localidadId(),
    entorno_interior: estado.entornoInterior(),
    historia: estado.historial(),
  };

  try {
    const resultado = await rutas.prediccion(lectura);
    estado.agregarAlHistorial({ temperatura: lectura.temperatura, humedad: lectura.humedad });
    pintarResultado(resultado);
    pintarHistorial();
  } catch (error) {
    pintarResultado(null, error.message);
  }
}

/** Refresca únicamente lo que depende del estado compartido. */
function actualizar() {
  sincronizarSelector(ID_SELECTOR);
  pintarContexto();
}

export const vista = {
  id: 'prediccion',
  titulo: 'Predicción por localidad',
  montar,
  actualizar,
  autoRefresco: false,
};
