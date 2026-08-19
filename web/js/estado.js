/**
 * Estado compartido entre pestañas: catálogo de localidades, selección activa,
 * modo de entorno interior e historial de predicciones de la sesión.
 */

const LOCALIDAD_DEFECTO = 13;
const MAX_HISTORIAL = 20;

const suscriptores = new Set();

const estado = {
  localidades: [],
  localidadId: LOCALIDAD_DEFECTO,
  entornoInterior: false,
  historial: [],
};

/**
 * Registra un observador que se ejecuta cuando cambia el estado compartido.
 * @param {() => void} callback
 * @returns {() => void} Función para cancelar la suscripción.
 */
export function suscribir(callback) {
  suscriptores.add(callback);
  return () => suscriptores.delete(callback);
}

/** Notifica a todos los observadores registrados. */
function notificar() {
  suscriptores.forEach((callback) => callback());
}

/**
 * Guarda el catálogo de localidades recibido del backend.
 * @param {Array<Object>} localidades
 * @param {number} defecto
 */
export function definirLocalidades(localidades, defecto) {
  estado.localidades = localidades;
  estado.localidadId = defecto || LOCALIDAD_DEFECTO;
  notificar();
}

/** @returns {Array<Object>} Catálogo completo de localidades. */
export function localidades() {
  return estado.localidades;
}

/** @returns {number} Identificador de la localidad seleccionada. */
export function localidadId() {
  return estado.localidadId;
}

/**
 * Datos de la localidad activa, o null si el catálogo aún no cargó.
 * @returns {Object|null}
 */
export function localidadActiva() {
  return estado.localidades.find((loc) => loc.id === estado.localidadId) || null;
}

/**
 * Cambia la localidad seleccionada y avisa a las vistas.
 * @param {number} id
 */
export function seleccionarLocalidad(id) {
  const nuevo = Number(id);
  if (Number.isNaN(nuevo) || nuevo === estado.localidadId) {
    return;
  }
  estado.localidadId = nuevo;
  notificar();
}

/** @returns {boolean} Si el modo de entorno interior está activo. */
export function entornoInterior() {
  return estado.entornoInterior;
}

/**
 * Activa o desactiva el escalado de luz para entornos cerrados.
 * @param {boolean} activo
 */
export function definirEntornoInterior(activo) {
  estado.entornoInterior = Boolean(activo);
  notificar();
}

/**
 * Agrega una lectura al historial de la sesión (ventana móvil del modelo).
 * @param {{temperatura: number, humedad: number}} lectura
 */
export function agregarAlHistorial(lectura) {
  estado.historial = [...estado.historial, lectura].slice(-MAX_HISTORIAL);
}

/** @returns {Array<{temperatura: number, humedad: number}>} Historial de la sesión. */
export function historial() {
  return estado.historial;
}

/** Vacía el historial acumulado en la sesión. */
export function limpiarHistorial() {
  estado.historial = [];
}
