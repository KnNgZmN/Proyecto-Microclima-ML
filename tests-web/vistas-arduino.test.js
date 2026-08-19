/**
 * Pruebas de web/js/vistas/arduino.js — pestaña de control del colector.
 *
 * @vitest-environment jsdom
 *
 * Es la vista con más estado propio: recuerda el puerto elegido y si el
 * usuario lo escribió a mano. Ese estado vive a nivel de módulo, así que
 * cada prueba reimporta la vista en limpio.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../web/js/api.js', () => ({
  rutas: {
    colectorEstado: vi.fn(),
    colectorIniciar: vi.fn(),
    colectorDetener: vi.fn(),
    live: vi.fn(),
    actual: vi.fn(),
    serie: vi.fn(),
    ultimas: vi.fn(),
    urlCsv: vi.fn(() => '/api/dataset/csv'),
  },
}));

let vista;
let rutas;
let estado;
let raiz;

const LOCALIDADES = [
  { id: 8, nombre: 'Kennedy' },
  { id: 13, nombre: 'Teusaquillo' },
];

const DETENIDO = { activo: false, puertos: ['COM4', 'COM7'] };

const LIVE = {
  disponible: true,
  antiguedad_s: 8,
  lectura: {
    localidad: 'Kennedy',
    temperatura: 20.64,
    humedad: 64.4,
    luz: 646,
    ruido: 62,
  },
};

const ACTUAL = { prediccion: 20.24, delta: -0.4, luz_modelo: 900 };
const SERIE = { puntos: [{ timestamp: '2026-04-23 12:31:23', temperatura: 20.6, humedad: 64 }] };
const ULTIMAS = {
  columnas: ['timestamp', 'temperatura'],
  filas: [{ timestamp: '2026-04-23 12:31:23', temperatura: 20.64 }],
};

/** Deja las cinco llamadas de actualizar() devolviendo datos válidos. */
function respuestasNormales(cambios = {}) {
  rutas.colectorEstado.mockResolvedValue(cambios.colector ?? DETENIDO);
  rutas.live.mockResolvedValue(cambios.live ?? LIVE);
  rutas.actual.mockResolvedValue(cambios.actual ?? ACTUAL);
  rutas.serie.mockResolvedValue(cambios.serie ?? SERIE);
  rutas.ultimas.mockResolvedValue(cambios.ultimas ?? ULTIMAS);
}

/** Pulsa un botón por su texto. */
function pulsar(texto) {
  [...document.querySelectorAll('button')]
    .find((b) => b.textContent === texto)
    .dispatchEvent(new Event('click'));
}

beforeEach(async () => {
  vi.resetModules();
  // Los dobles conservan sus llamadas entre pruebas: sin esto,
  // mock.calls[0] leeria la invocacion de la prueba anterior.
  vi.clearAllMocks();
  document.body.innerHTML = '';
  raiz = document.createElement('div');
  document.body.appendChild(raiz);

  ({ rutas } = await import('../web/js/api.js'));
  estado = await import('../web/js/estado.js');
  ({ vista } = await import('../web/js/vistas/arduino.js'));

  estado.definirLocalidades(LOCALIDADES, 8);
  respuestasNormales();
});

describe('descripción de la vista', () => {
  it('se identifica para el enrutador', () => {
    expect(vista.id).toBe('arduino');
    expect(vista.titulo).toBe('Arduino en vivo');
  });
});

describe('montar', () => {
  beforeEach(() => {
    vista.montar(raiz);
  });

  it('crea las cuatro secciones de la pestaña', () => {
    expect(raiz.querySelectorAll('.seccion')).toHaveLength(4);
  });

  it('propone COM3 como puerto por defecto', () => {
    expect(document.getElementById('ard-puerto').value).toBe('COM3');
  });

  it('ofrece solo las velocidades estándar del Arduino', () => {
    const opciones = [...document.getElementById('ard-baud').options].map((o) => o.value);
    expect(opciones).toEqual(['9600', '115200']);
  });

  it('enlaza el interruptor de entorno interior con el estado compartido', () => {
    const casilla = document.getElementById('ard-interior');
    expect(casilla.checked).toBe(false);

    casilla.checked = true;
    casilla.dispatchEvent(new Event('change'));

    expect(estado.entornoInterior()).toBe(true);
  });

  it('ofrece la descarga del dataset completo', () => {
    const enlace = raiz.querySelector('a.boton--enlace');
    expect(enlace.getAttribute('href')).toBe('/api/dataset/csv');
    expect(enlace.getAttribute('download')).toBe('microclima_bogota.csv');
  });
});

describe('control del colector', () => {
  beforeEach(() => {
    vista.montar(raiz);
  });

  it('inicia el Arduino real con el puerto y la velocidad del formulario', async () => {
    rutas.colectorIniciar.mockResolvedValue({ activo: true, pid: 4321, modo: 'real', puertos: [] });
    document.getElementById('ard-baud').value = '115200';

    pulsar('Iniciar Arduino real');
    await vi.waitFor(() => expect(rutas.colectorIniciar).toHaveBeenCalled());

    expect(rutas.colectorIniciar).toHaveBeenCalledWith({
      modo: 'real', puerto: 'COM3', baud: 115200, localidad_id: 8,
    });
  });

  it('inicia la simulación sin necesitar hardware', async () => {
    rutas.colectorIniciar.mockResolvedValue({
      activo: true, pid: 99, modo: 'simulacion', puertos: [],
    });

    pulsar('Iniciar simulación');
    await vi.waitFor(() => expect(rutas.colectorIniciar).toHaveBeenCalled());

    expect(rutas.colectorIniciar.mock.calls[0][0].modo).toBe('simulacion');
  });

  it('muestra la insignia de ejecución con el PID', async () => {
    rutas.colectorIniciar.mockResolvedValue({ activo: true, pid: 4321, modo: 'real', puertos: [] });

    pulsar('Iniciar Arduino real');
    await vi.waitFor(() => expect(raiz.querySelector('.insignia--vivo')).not.toBeNull());

    expect(raiz.querySelector('.insignia--vivo').textContent).toContain('4321');
  });

  it('muestra el mensaje si el colector no arranca', async () => {
    rutas.colectorIniciar.mockRejectedValue(new Error('Puerto serial no válido'));

    pulsar('Iniciar Arduino real');
    await vi.waitFor(() => expect(raiz.querySelector('.aviso--error')).not.toBeNull());

    expect(raiz.querySelector('.aviso--error').textContent).toBe('Puerto serial no válido');
  });

  it('detiene el colector y refleja el nuevo estado', async () => {
    rutas.colectorDetener.mockResolvedValue(DETENIDO);

    pulsar('Detener');
    await vi.waitFor(() => expect(rutas.colectorDetener).toHaveBeenCalled());

    expect(raiz.textContent).toContain('Colector detenido');
  });

  it('reporta el error que devuelve el backend en el estado', async () => {
    respuestasNormales({
      colector: { activo: false, error: 'El proceso terminó de forma inesperada', puertos: [] },
    });

    await vista.actualizar();

    expect(raiz.querySelector('.aviso--error').textContent)
      .toBe('El proceso terminó de forma inesperada');
  });
});

describe('puertos detectados', () => {
  beforeEach(() => {
    vista.montar(raiz);
  });

  it('lista los puertos que encontró el backend', async () => {
    await vista.actualizar();

    expect(raiz.querySelector('.contexto').textContent).toContain('COM4, COM7');
  });

  it('avisa cuando no hay ninguno conectado', async () => {
    respuestasNormales({ colector: { activo: false, puertos: [] } });

    await vista.actualizar();

    expect(raiz.querySelector('.contexto').textContent).toContain('No se detectaron puertos');
  });

  it('sugiere el primer puerto detectado si el usuario no escribió ninguno', async () => {
    await vista.actualizar();

    expect(document.getElementById('ard-puerto').value).toBe('COM4');
  });

  it('respeta el puerto que el usuario escribió a mano', async () => {
    const input = document.getElementById('ard-puerto');
    input.value = 'COM9';
    input.dispatchEvent(new Event('input'));

    await vista.actualizar();

    expect(input.value).toBe('COM9');
  });

  it('no cambia el puerto si el elegido ya está entre los detectados', async () => {
    respuestasNormales({ colector: { activo: false, puertos: ['COM7', 'COM3'] } });

    await vista.actualizar();

    expect(document.getElementById('ard-puerto').value).toBe('COM3');
  });
});

describe('lectura en vivo', () => {
  beforeEach(() => {
    vista.montar(raiz);
  });

  it('muestra las magnitudes y la antigüedad de la lectura', async () => {
    await vista.actualizar();

    const valores = [...raiz.querySelectorAll('.metrica__valor')].map((n) => n.textContent);
    expect(valores).toContain('20,64 °C');
    expect(valores).toContain('646 lux');
    expect(raiz.querySelector('.insignia--vivo').textContent).toContain('hace 8 s');
  });

  it('degrada la insignia cuando la lectura envejece', async () => {
    respuestasNormales({ live: { ...LIVE, antiguedad_s: 90 } });

    await vista.actualizar();

    expect(raiz.querySelector('.insignia--caido')).not.toBeNull();
  });

  it('muestra la predicción cuando el modelo está disponible', async () => {
    await vista.actualizar();

    const valores = [...raiz.querySelectorAll('.metrica__valor')].map((n) => n.textContent);
    expect(valores).toContain('20,24 °C');
    expect(valores).toContain('-0,40 °C');
  });

  it('omite la predicción si el modelo no está entrenado', async () => {
    respuestasNormales({ actual: { ...ACTUAL, prediccion: null } });

    await vista.actualizar();

    const etiquetas = [...raiz.querySelectorAll('.metrica__etiqueta')].map((n) => n.textContent);
    expect(etiquetas).not.toContain('Predicción T+30 min');
  });

  it('muestra la luz corregida solo en modo entorno interior', async () => {
    estado.definirEntornoInterior(true);

    await vista.actualizar();

    const detalles = [...raiz.querySelectorAll('.metrica__detalle')].map((n) => n.textContent);
    expect(detalles).toContain('Modelo: 900 lux');
  });

  it('avisa cuando el colector aún no publicó nada', async () => {
    respuestasNormales({ live: { disponible: false } });

    await vista.actualizar();

    expect(raiz.textContent).toContain('Sin datos en vivo todavía');
  });
});

describe('enviar la lectura a la pestaña de predicción', () => {
  it('emite los dos eventos: precargar y navegar', async () => {
    vista.montar(raiz);
    await vista.actualizar();

    const precargar = vi.fn();
    const navegar = vi.fn();
    document.addEventListener('microclima:precargar', precargar);
    document.addEventListener('microclima:navegar', navegar);

    pulsar('Usar esta lectura en la pestaña de predicción');

    expect(precargar.mock.calls[0][0].detail.temperatura).toBe(20.64);
    expect(navegar.mock.calls[0][0].detail).toEqual({ id: 'prediccion' });
  });
});

describe('historial reciente', () => {
  beforeEach(() => {
    vista.montar(raiz);
  });

  it('pinta la tabla de últimas lecturas', async () => {
    await vista.actualizar();

    expect(raiz.querySelectorAll('tbody tr')).toHaveLength(1);
  });

  it('avisa cuando la localidad no tiene registros', async () => {
    respuestasNormales({ ultimas: { columnas: [], filas: [] } });

    await vista.actualizar();

    expect(raiz.textContent).toContain('No hay registros para esta localidad');
  });

  it('no falla si el lienzo no está en la página', async () => {
    document.getElementById('grafico-arduino').remove();

    await expect(vista.actualizar()).resolves.not.toThrow();
  });
});
