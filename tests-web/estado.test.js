/**
 * Pruebas de web/js/estado.js — estado compartido entre las vistas.
 *
 * El módulo mantiene estado a nivel de módulo (un singleton), así que cada
 * prueba lo reimporta en limpio con vi.resetModules() para no arrastrar
 * resultados de la anterior.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

let estado;

beforeEach(async () => {
  vi.resetModules();
  estado = await import('../web/js/estado.js');
});

const LOCALIDADES = [
  { id: 8, nombre: 'Kennedy' },
  { id: 13, nombre: 'Teusaquillo' },
  { id: 20, nombre: 'Sumapaz' },
];

describe('catálogo de localidades', () => {
  it('arranca con Teusaquillo como localidad por defecto', () => {
    expect(estado.localidadId()).toBe(13);
  });

  it('arranca sin catálogo cargado', () => {
    expect(estado.localidades()).toEqual([]);
    expect(estado.localidadActiva()).toBeNull();
  });

  it('guarda el catálogo recibido del backend', () => {
    estado.definirLocalidades(LOCALIDADES, 8);

    expect(estado.localidades()).toHaveLength(3);
    expect(estado.localidadId()).toBe(8);
  });

  it('vuelve a Teusaquillo si el backend no indica una por defecto', () => {
    estado.definirLocalidades(LOCALIDADES, 0);

    expect(estado.localidadId()).toBe(13);
  });

  it('resuelve los datos de la localidad activa', () => {
    estado.definirLocalidades(LOCALIDADES, 20);

    expect(estado.localidadActiva()).toEqual({ id: 20, nombre: 'Sumapaz' });
  });

  it('devuelve null si la localidad activa no está en el catálogo', () => {
    estado.definirLocalidades(LOCALIDADES, 99);

    expect(estado.localidadActiva()).toBeNull();
  });
});

describe('selección de localidad', () => {
  it('cambia la localidad y avisa a los suscriptores', () => {
    const aviso = vi.fn();
    estado.suscribir(aviso);

    estado.seleccionarLocalidad(8);

    expect(estado.localidadId()).toBe(8);
    expect(aviso).toHaveBeenCalledTimes(1);
  });

  it('acepta el id como texto, tal como llega de un <select>', () => {
    estado.seleccionarLocalidad('20');

    expect(estado.localidadId()).toBe(20);
  });

  it('no avisa si se elige la localidad que ya estaba activa', () => {
    const aviso = vi.fn();
    estado.suscribir(aviso);

    estado.seleccionarLocalidad(13);

    expect(aviso).not.toHaveBeenCalled();
  });

  it('ignora valores que no son numéricos', () => {
    estado.seleccionarLocalidad('no es un id');

    expect(estado.localidadId()).toBe(13);
  });
});

describe('suscripciones', () => {
  it('devuelve una función para cancelar la suscripción', () => {
    const aviso = vi.fn();
    const cancelar = estado.suscribir(aviso);

    cancelar();
    estado.seleccionarLocalidad(8);

    expect(aviso).not.toHaveBeenCalled();
  });

  it('notifica a todos los suscriptores registrados', () => {
    const uno = vi.fn();
    const dos = vi.fn();
    estado.suscribir(uno);
    estado.suscribir(dos);

    estado.definirEntornoInterior(true);

    expect(uno).toHaveBeenCalledTimes(1);
    expect(dos).toHaveBeenCalledTimes(1);
  });
});

describe('entorno interior', () => {
  it('arranca desactivado', () => {
    expect(estado.entornoInterior()).toBe(false);
  });

  it.each([
    [true, true],
    [1, true],
    ['si', true],
    [0, false],
    [null, false],
  ])('convierte %s a booleano %s', (entrada, esperado) => {
    estado.definirEntornoInterior(entrada);

    expect(estado.entornoInterior()).toBe(esperado);
  });
});

describe('historial de lecturas', () => {
  it('arranca vacío', () => {
    expect(estado.historial()).toEqual([]);
  });

  it('acumula las lecturas en orden', () => {
    estado.agregarAlHistorial({ temperatura: 18, humedad: 70 });
    estado.agregarAlHistorial({ temperatura: 19, humedad: 71 });

    expect(estado.historial()).toEqual([
      { temperatura: 18, humedad: 70 },
      { temperatura: 19, humedad: 71 },
    ]);
  });

  it('conserva solo las últimas 20 lecturas', () => {
    for (let i = 1; i <= 25; i += 1) {
      estado.agregarAlHistorial({ temperatura: i, humedad: 70 });
    }

    const acumulado = estado.historial();
    expect(acumulado).toHaveLength(20);
    expect(acumulado[0].temperatura).toBe(6);
    expect(acumulado[19].temperatura).toBe(25);
  });

  it('se puede vaciar', () => {
    estado.agregarAlHistorial({ temperatura: 18, humedad: 70 });

    estado.limpiarHistorial();

    expect(estado.historial()).toEqual([]);
  });
});
