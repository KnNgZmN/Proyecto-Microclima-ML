/**
 * Pestaña "Comparativa de localidades": temperatura media por localidad,
 * relación con la altitud y tabla de estadísticas.
 */

import { rutas } from '../api.js';
import { aviso, crear, reemplazar, tabla } from '../dom.js';
import { bloqueGrafico, seccion } from '../componentes.js';
import * as formato from '../formato.js';
import { graficoBarras, graficoDispersion } from '../graficos.js';

const ENCABEZADOS = [
  'Localidad', 'Zona', 'Altitud (m)', 'Temp. mín °C',
  'Temp. media °C', 'Temp. máx °C', 'Humedad media %',
];

const refs = {};

/** Construye la estructura fija de la pestaña. */
function montar(raiz) {
  refs.mensaje = crear('div', {});
  refs.tabla = crear('div', {});

  reemplazar(raiz, [
    refs.mensaje,
    seccion('Temperatura media por localidad', [
      bloqueGrafico('Cada barra representa una localidad', 'grafico-barras', 'grafico__lienzo--alto'),
    ]),
    seccion('Temperatura media frente a altitud', [
      bloqueGrafico('El color indica la temperatura relativa', 'grafico-dispersion'),
    ]),
    seccion('Estadísticas por localidad', [refs.tabla]),
  ]);
}

/**
 * Normaliza un valor dentro del rango observado.
 * @param {number} valor
 * @param {number} minimo
 * @param {number} maximo
 * @returns {number} Proporción entre 0 y 1.
 */
function proporcion(valor, minimo, maximo) {
  return maximo === minimo ? 0.5 : (valor - minimo) / (maximo - minimo);
}

/**
 * Dibuja las dos gráficas de la pestaña.
 * @param {Array<Object>} filas
 */
function pintarGraficos(filas) {
  const medias = filas.map((fila) => fila.temp_media);
  const minimo = Math.min(...medias);
  const maximo = Math.max(...medias);

  const barras = document.getElementById('grafico-barras');
  if (barras) {
    graficoBarras(barras, {
      items: filas.map((fila) => ({ etiqueta: fila.localidad, valor: fila.temp_media })),
    });
  }

  const dispersion = document.getElementById('grafico-dispersion');
  if (dispersion) {
    graficoDispersion(dispersion, {
      puntos: filas.map((fila) => ({
        x: fila.altitud,
        y: fila.temp_media,
        etiqueta: fila.localidad,
        intensidad: proporcion(fila.temp_media, minimo, maximo),
      })),
      tituloX: 'Altitud (m)',
    });
  }
}

/**
 * Pinta la tabla de estadísticas.
 * @param {Array<Object>} filas
 */
function pintarTabla(filas) {
  reemplazar(refs.tabla, [tabla(ENCABEZADOS, filas.map((fila) => [
    fila.localidad,
    fila.zona,
    formato.entero(fila.altitud),
    formato.numero(fila.temp_min, 2),
    formato.numero(fila.temp_media, 2),
    formato.numero(fila.temp_max, 2),
    formato.numero(fila.humedad_med, 2),
  ]))]);
}

/** Descarga la comparativa y actualiza gráficas y tabla. */
async function actualizar() {
  const datos = await rutas.comparativa();
  if (!datos.disponible || datos.filas.length === 0) {
    reemplazar(refs.mensaje, [aviso(
      'aviso',
      'El dataset actual no tiene columna de localidad. Regenéralo con generate_dataset.py.',
    )]);
    reemplazar(refs.tabla, []);
    return;
  }

  reemplazar(refs.mensaje, []);
  pintarGraficos(datos.filas);
  pintarTabla(datos.filas);
}

export const vista = {
  id: 'comparativa',
  titulo: 'Comparativa de localidades',
  montar,
  actualizar,
  autoRefresco: false,
};
