/**
 * Punto de entrada del panel: carga el catálogo de localidades, monta las
 * pestañas y coordina el refresco automático.
 */

import { rutas } from './api.js';
import { aviso, buscar, crear, reemplazar, vaciar } from './dom.js';
import { insignia } from './componentes.js';
import * as estado from './estado.js';
import * as formato from './formato.js';
import { vista as vistaHistoricos } from './vistas/historicos.js';
import { vista as vistaPrediccion } from './vistas/prediccion.js';
import { vista as vistaComparativa } from './vistas/comparativa.js';
import { vista as vistaArduino } from './vistas/arduino.js';

const VISTAS = [vistaHistoricos, vistaPrediccion, vistaComparativa, vistaArduino];
const INTERVALO_REFRESCO_MS = 5000;
const RETARDO_REDIMENSION_MS = 200;

const contenedores = new Map();
let vistaActiva = VISTAS[0];
let temporizadorRedimension = null;

/**
 * Muestra un mensaje de error global, o lo oculta si no hay mensaje.
 * @param {string|null} mensaje
 */
function mostrarError(mensaje) {
  const zona = buscar('#aviso-global');
  if (!mensaje) {
    vaciar(zona);
    return;
  }
  reemplazar(zona, [aviso('error', mensaje)]);
}

/**
 * Activa una pestaña y refresca su contenido.
 * @param {string} id
 */
function activar(id) {
  const destino = VISTAS.find((vista) => vista.id === id);
  if (!destino) {
    return;
  }
  vistaActiva = destino;

  contenedores.forEach((contenedor, clave) => {
    contenedor.hidden = clave !== id;
  });
  document.querySelectorAll('.pestana').forEach((boton) => {
    const activa = boton.dataset.vista === id;
    boton.classList.toggle('pestana--activa', activa);
    boton.setAttribute('aria-selected', String(activa));
  });

  refrescar();
}

/** Construye la barra de pestañas. */
function montarPestanas() {
  const barra = buscar('#pestanas');
  reemplazar(barra, VISTAS.map((vista) => {
    const boton = crear('button', {
      clase: 'pestana',
      texto: vista.titulo,
      attrs: { type: 'button', role: 'tab', 'aria-selected': 'false' },
    });
    boton.dataset.vista = vista.id;
    boton.addEventListener('click', () => activar(vista.id));
    return boton;
  }));
}

/** Crea el contenedor de cada vista y la monta una sola vez. */
function montarVistas() {
  const raiz = buscar('#contenido');
  vaciar(raiz);
  VISTAS.forEach((vista) => {
    const contenedor = crear('section', {
      clase: 'vista',
      attrs: { id: `vista-${vista.id}`, role: 'tabpanel' },
    });
    contenedor.hidden = true;
    raiz.appendChild(contenedor);
    contenedores.set(vista.id, contenedor);
    vista.montar(contenedor);
  });
}

/**
 * Pinta el panel lateral con las métricas del modelo.
 * @param {Object} datos Respuesta de /api/metricas.
 */
function pintarPanelModelo(datos) {
  const zona = buscar('#panel-modelo');
  const metricas = datos.metricas;
  if (!metricas) {
    reemplazar(zona, [aviso('aviso', 'Ejecuta train_model.py para ver las métricas.')]);
    return;
  }

  reemplazar(zona, [
    crear('dl', { clase: 'lista-datos' }, [
      crear('dt', { texto: 'MAE (CV)' }),
      crear('dd', {
        texto: `${formato.numero(metricas.mae_cv_mean, 3)} ± ${formato.numero(metricas.mae_cv_std, 3)} °C`,
      }),
      crear('dt', { texto: 'RMSE (CV)' }),
      crear('dd', {
        texto: `${formato.numero(metricas.rmse_cv_mean, 3)} ± ${formato.numero(metricas.rmse_cv_std, 3)} °C`,
      }),
      crear('dt', { texto: 'Features' }),
      crear('dd', { texto: formato.entero(metricas.n_features) }),
      crear('dt', { texto: 'Registros' }),
      crear('dd', { texto: formato.entero(metricas.n_registros) }),
      crear('dt', { texto: 'Localidades' }),
      crear('dd', { texto: formato.entero(metricas.n_localidades) }),
    ]),
  ]);
}

/**
 * Pinta el indicador de estado del colector en el panel lateral.
 * @param {Object} live Respuesta de /api/lectura/live.
 */
function pintarPanelLive(live) {
  const zona = buscar('#panel-live');
  if (!live.disponible) {
    reemplazar(zona, [aviso('info', 'Sin lecturas del Arduino.')]);
    return;
  }
  reemplazar(zona, [insignia(
    formato.nivelFrescura(live.antiguedad_s),
    `${live.lectura.localidad} · ${formato.antiguedad(live.antiguedad_s)}`,
  )]);
}

/** Actualiza el panel lateral con datos independientes de la pestaña. */
async function refrescarPanel() {
  const [metricas, live] = await Promise.all([rutas.metricas(), rutas.live()]);
  pintarPanelModelo(metricas);
  pintarPanelLive(live);
}

/** Refresca el panel lateral y la vista activa, capturando errores. */
async function refrescar() {
  try {
    await Promise.all([refrescarPanel(), vistaActiva.actualizar()]);
    mostrarError(null);
  } catch (error) {
    mostrarError(error.message);
  }
}

/** Programa el refresco periódico de la vista activa. */
function iniciarRefrescoAutomatico() {
  window.setInterval(() => {
    if (document.visibilityState === 'visible' && vistaActiva.autoRefresco !== false) {
      refrescar();
    }
  }, INTERVALO_REFRESCO_MS);
}

/** Vuelve a dibujar al cambiar el tamaño de la ventana (con retardo). */
function escucharRedimension() {
  window.addEventListener('resize', () => {
    window.clearTimeout(temporizadorRedimension);
    temporizadorRedimension = window.setTimeout(refrescar, RETARDO_REDIMENSION_MS);
  });
}

/** Arranca la aplicación. */
async function iniciar() {
  try {
    const catalogo = await rutas.localidades();
    estado.definirLocalidades(catalogo.localidades, catalogo.defecto);
  } catch (error) {
    mostrarError(`No se pudo cargar el catálogo de localidades: ${error.message}`);
    return;
  }

  montarPestanas();
  montarVistas();
  estado.suscribir(refrescar);
  document.addEventListener('microclima:navegar', (evento) => activar(evento.detail.id));
  escucharRedimension();
  iniciarRefrescoAutomatico();
  activar(VISTAS[0].id);
}

document.addEventListener('DOMContentLoaded', iniciar);
