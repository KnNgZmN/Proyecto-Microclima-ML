/**
 * Pruebas de web/js/main.js — punto de entrada del panel.
 *
 * @vitest-environment jsdom
 *
 * main.js no exporta nada: se engancha a DOMContentLoaded. Cada prueba
 * levanta el esqueleto de index.html, reimporta el módulo y dispara el
 * evento, que es exactamente lo que hace el navegador al abrir la página.
 *
 * Las vistas NO se sustituyen por dobles: se ejercitan de verdad contra la
 * API simulada, así que estas pruebas también verifican que las cuatro se
 * montan e integran bien entre sí.
 */
import {
  afterEach, beforeEach, describe, expect, it, vi,
} from 'vitest';

vi.mock('../web/js/api.js', () => ({
  rutas: {
    localidades: vi.fn(),
    metricas: vi.fn(),
    live: vi.fn(),
    resumen: vi.fn(),
    actual: vi.fn(),
    serie: vi.fn(),
    ultimas: vi.fn(),
    comparativa: vi.fn(),
    prediccion: vi.fn(),
    colectorEstado: vi.fn(),
    colectorIniciar: vi.fn(),
    colectorDetener: vi.fn(),
    urlCsv: vi.fn(() => '/api/dataset/csv'),
  },
}));

let rutas;

/** Esqueleto mínimo de index.html que main.js espera encontrar. */
const ESQUELETO = `
  <div id="panel-modelo"></div>
  <div id="panel-live"></div>
  <nav id="pestanas"></nav>
  <div id="aviso-global"></div>
  <div id="contenido"></div>
`;

const CATALOGO = {
  defecto: 8,
  localidades: [
    {
      id: 8, nombre: 'Kennedy', altitud: 2570, densidad_urbana: 0.88, zona: 'Occidente', lat: 4.6278, lon: -74.1647,
    },
    {
      id: 13, nombre: 'Teusaquillo', altitud: 2600, densidad_urbana: 0.87, zona: 'Centro', lat: 4.6321, lon: -74.0871,
    },
  ],
};

const METRICAS = {
  metricas: {
    mae_cv_mean: 0.9869,
    mae_cv_std: 0.0244,
    rmse_cv_mean: 1.5446,
    rmse_cv_std: 0.0311,
    n_features: 19,
    n_registros: 259140,
    n_localidades: 20,
  },
};

const LIVE = {
  disponible: true,
  antiguedad_s: 8,
  lectura: { localidad: 'Kennedy', temperatura: 20.64, humedad: 64.4, luz: 646, ruido: 62 },
};

/** Respuestas válidas para todas las llamadas que hace el panel. */
function respuestasNormales(cambios = {}) {
  rutas.localidades.mockResolvedValue(cambios.catalogo ?? CATALOGO);
  rutas.metricas.mockResolvedValue(cambios.metricas ?? METRICAS);
  rutas.live.mockResolvedValue(cambios.live ?? LIVE);
  rutas.resumen.mockResolvedValue({
    registros: 259140, temp_media: 14.3, humedad_media: 72, tiene_localidades: true, localidades: 20, dias: 90, registros_localidad: 12957,
  });
  rutas.actual.mockResolvedValue({
    origen: 'dataset', antiguedad_min: 4, lectura: LIVE.lectura, prediccion: 20.24, delta: -0.4, luz_modelo: 900,
  });
  rutas.serie.mockResolvedValue({ puntos: [] });
  rutas.ultimas.mockResolvedValue({ columnas: [], filas: [] });
  rutas.comparativa.mockResolvedValue({ disponible: true, filas: [] });
  rutas.colectorEstado.mockResolvedValue({ activo: false, puertos: [] });
}

/** Arranca el panel como lo haría el navegador y espera a que asiente. */
async function arrancar() {
  await import('../web/js/main.js');
  document.dispatchEvent(new Event('DOMContentLoaded'));
  await vi.waitFor(() => {
    expect(rutas.localidades).toHaveBeenCalled();
  });
}

/**
 * Arranca el panel con el reloj falso YA instalado.
 *
 * El orden importa: setInterval y setTimeout se registran durante el
 * arranque, asi que instalar los temporizadores falsos despues dejaria
 * corriendo los reales y el reloj simulado no dispararia nada.
 */
async function arrancarConReloj() {
  vi.useFakeTimers();
  await import('../web/js/main.js');
  document.dispatchEvent(new Event('DOMContentLoaded'));
  // Vacia la cola de microtareas sin mover el reloj.
  for (let i = 0; i < 8; i += 1) {
    await vi.advanceTimersByTimeAsync(0);
  }
}

/** Botones de la barra de pestañas. */
const pestanas = () => [...document.querySelectorAll('.pestana')];
/** Identificador de la pestaña visible. */
const visible = () => [...document.querySelectorAll('.vista')].find((v) => !v.hidden)?.id;

beforeEach(async () => {
  vi.resetModules();
  vi.clearAllMocks();
  document.body.innerHTML = ESQUELETO;

  ({ rutas } = await import('../web/js/api.js'));
  respuestasNormales();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('arranque', () => {
  it('pide el catálogo de localidades antes que nada', async () => {
    await arrancar();

    expect(rutas.localidades).toHaveBeenCalledTimes(1);
  });

  it('crea una pestaña por vista', async () => {
    await arrancar();

    expect(pestanas().map((b) => b.textContent)).toEqual([
      'Datos históricos',
      'Predicción por localidad',
      'Comparativa de localidades',
      'Arduino en vivo',
    ]);
  });

  it('monta las cuatro vistas en su propio contenedor', async () => {
    await arrancar();

    expect(document.querySelectorAll('.vista')).toHaveLength(4);
  });

  it('abre la primera pestaña', async () => {
    await arrancar();

    await vi.waitFor(() => expect(visible()).toBe('vista-historicos'));
    expect(pestanas()[0].getAttribute('aria-selected')).toBe('true');
  });

  it('aborta y avisa si el catálogo no carga', async () => {
    rutas.localidades.mockRejectedValue(new Error('Backend caído'));

    await arrancar();

    await vi.waitFor(() => {
      expect(document.querySelector('#aviso-global .aviso--error')).not.toBeNull();
    });
    expect(document.querySelector('#aviso-global').textContent)
      .toContain('No se pudo cargar el catálogo');
    expect(pestanas()).toHaveLength(0);
  });
});

describe('navegación entre pestañas', () => {
  beforeEach(async () => {
    await arrancar();
    await vi.waitFor(() => expect(visible()).toBe('vista-historicos'));
  });

  it('cambia de vista al pulsar una pestaña', async () => {
    pestanas()[2].dispatchEvent(new Event('click'));

    await vi.waitFor(() => expect(visible()).toBe('vista-comparativa'));
  });

  it('marca como seleccionada solo la pestaña activa', async () => {
    pestanas()[2].dispatchEvent(new Event('click'));

    await vi.waitFor(() => {
      const marcadas = pestanas().filter((b) => b.getAttribute('aria-selected') === 'true');
      expect(marcadas).toHaveLength(1);
      expect(marcadas[0].textContent).toBe('Comparativa de localidades');
    });
  });

  it('responde al evento de navegación que emite la vista del Arduino', async () => {
    document.dispatchEvent(new CustomEvent('microclima:navegar', {
      detail: { id: 'prediccion' },
    }));

    await vi.waitFor(() => expect(visible()).toBe('vista-prediccion'));
  });

  it('ignora una vista que no existe', async () => {
    document.dispatchEvent(new CustomEvent('microclima:navegar', {
      detail: { id: 'no-existe' },
    }));

    expect(visible()).toBe('vista-historicos');
  });
});

describe('panel lateral del modelo', () => {
  it('muestra las métricas de validación cruzada', async () => {
    await arrancar();

    await vi.waitFor(() => {
      expect(document.querySelector('#panel-modelo dl')).not.toBeNull();
    });
    const texto = document.querySelector('#panel-modelo').textContent;
    expect(texto).toContain('0,987 ± 0,024 °C');
    expect(texto).toContain('259.140');
  });

  it('invita a entrenar el modelo si no hay métricas', async () => {
    respuestasNormales({ metricas: { metricas: null } });

    await arrancar();

    await vi.waitFor(() => {
      expect(document.querySelector('#panel-modelo').textContent).toContain('train_model.py');
    });
  });
});

describe('panel lateral del colector', () => {
  it('muestra la frescura de la última lectura', async () => {
    await arrancar();

    await vi.waitFor(() => {
      expect(document.querySelector('#panel-live .insignia')).not.toBeNull();
    });
    const marca = document.querySelector('#panel-live .insignia');
    expect(marca.className).toContain('insignia--vivo');
    expect(marca.textContent).toContain('Kennedy');
  });

  it('avisa cuando el Arduino no ha publicado nada', async () => {
    respuestasNormales({ live: { disponible: false } });

    await arrancar();

    await vi.waitFor(() => {
      expect(document.querySelector('#panel-live').textContent).toContain('Sin lecturas');
    });
  });
});

describe('manejo de errores durante el refresco', () => {
  it('muestra el mensaje si una llamada falla', async () => {
    await arrancar();
    await vi.waitFor(() => expect(visible()).toBe('vista-historicos'));

    rutas.metricas.mockRejectedValue(new Error('Servicio no disponible'));
    document.dispatchEvent(new CustomEvent('microclima:navegar', { detail: { id: 'comparativa' } }));

    await vi.waitFor(() => {
      expect(document.querySelector('#aviso-global').textContent).toContain('Servicio no disponible');
    });
  });

  it('retira el aviso cuando el refresco vuelve a funcionar', async () => {
    await arrancar();
    rutas.metricas.mockRejectedValue(new Error('Servicio no disponible'));
    document.dispatchEvent(new CustomEvent('microclima:navegar', { detail: { id: 'comparativa' } }));
    await vi.waitFor(() => {
      expect(document.querySelector('#aviso-global').textContent).toContain('Servicio no disponible');
    });

    rutas.metricas.mockResolvedValue(METRICAS);
    document.dispatchEvent(new CustomEvent('microclima:navegar', { detail: { id: 'historicos' } }));

    await vi.waitFor(() => {
      expect(document.querySelector('#aviso-global').textContent).toBe('');
    });
  });
});

describe('refresco automático', () => {
  it('vuelve a consultar mientras la pestaña está visible', async () => {
    await arrancarConReloj();
    const antes = rutas.metricas.mock.calls.length;
    expect(antes).toBeGreaterThan(0);

    await vi.advanceTimersByTimeAsync(5000);

    expect(rutas.metricas.mock.calls.length).toBeGreaterThan(antes);
  });

  it('no consulta si la pestaña del navegador está oculta', async () => {
    await arrancarConReloj();
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden');
    const antes = rutas.metricas.mock.calls.length;

    await vi.advanceTimersByTimeAsync(5000);

    expect(rutas.metricas.mock.calls.length).toBe(antes);
  });

  it('no refresca las vistas que declaran no necesitarlo', async () => {
    await arrancarConReloj();
    document.dispatchEvent(new CustomEvent('microclima:navegar', { detail: { id: 'comparativa' } }));
    for (let i = 0; i < 8; i += 1) {
      await vi.advanceTimersByTimeAsync(0);
    }
    const antes = rutas.metricas.mock.calls.length;

    await vi.advanceTimersByTimeAsync(5000);

    // La comparativa declara autoRefresco: false.
    expect(rutas.metricas.mock.calls.length).toBe(antes);
  });
});

describe('redimensión de la ventana', () => {
  it('espera a que la redimensión termine antes de redibujar', async () => {
    await arrancarConReloj();
    const antes = rutas.metricas.mock.calls.length;

    window.dispatchEvent(new Event('resize'));
    window.dispatchEvent(new Event('resize'));
    window.dispatchEvent(new Event('resize'));
    await vi.advanceTimersByTimeAsync(150);

    // Todavia no: el retardo es de 200 ms y cada señal reinicia la cuenta.
    expect(rutas.metricas.mock.calls.length).toBe(antes);

    await vi.advanceTimersByTimeAsync(100);

    expect(rutas.metricas.mock.calls.length).toBeGreaterThan(antes);
  });
});
