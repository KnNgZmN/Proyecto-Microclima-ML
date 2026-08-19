/**
 * Pruebas de web/js/vistas/prediccion.js — pestaña de predicción manual.
 *
 * @vitest-environment jsdom
 *
 * Es la vista con más interacción: un formulario, dos botones y un evento
 * que la conecta con la pestaña del Arduino. Aquí se verifica qué se envía
 * al backend, qué se pinta con la respuesta y qué pasa cuando falla.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../web/js/api.js', () => ({
  rutas: { prediccion: vi.fn() },
}));

let vista;
let rutas;
let estado;
let raiz;

const LOCALIDADES = [
  {
    id: 8, nombre: 'Kennedy', altitud: 2570, densidad_urbana: 0.88, lat: 4.6278, lon: -74.1647,
  },
  {
    id: 13, nombre: 'Teusaquillo', altitud: 2600, densidad_urbana: 0.87, lat: 4.6321, lon: -74.0871,
  },
];

const RESULTADO = {
  localidad: 'Kennedy',
  prediccion: 20.24,
  delta: -0.4,
  temperatura_actual: 20.64,
};

/** Escribe un valor en un campo del formulario. */
function escribir(id, valor) {
  document.getElementById(id).value = String(valor);
}

/** Pulsa un botón por su texto. */
function pulsar(texto) {
  const boton = [...raiz.querySelectorAll('button')].find((b) => b.textContent === texto);
  boton.dispatchEvent(new Event('click'));
  return boton;
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
  ({ vista } = await import('../web/js/vistas/prediccion.js'));

  estado.definirLocalidades(LOCALIDADES, 8);
  rutas.prediccion.mockResolvedValue(RESULTADO);
});

describe('descripción de la vista', () => {
  it('se identifica para el enrutador y no se refresca sola', () => {
    expect(vista.id).toBe('prediccion');
    expect(vista.autoRefresco).toBe(false);
  });
});

describe('montar', () => {
  beforeEach(() => {
    vista.montar(raiz);
  });

  it('crea los cuatro campos numéricos del sensor', () => {
    ['pred-temperatura', 'pred-humedad', 'pred-luz', 'pred-ruido'].forEach((id) => {
      expect(document.getElementById(id)).not.toBeNull();
    });
  });

  it('crea los deslizadores de hora y mes', () => {
    expect(document.getElementById('pred-hora').type).toBe('range');
    expect(document.getElementById('pred-mes').type).toBe('range');
  });

  it('arranca invitando a usar el formulario', () => {
    expect(raiz.querySelector('.aviso').textContent).toContain('Predecir');
  });

  it('arranca con el historial vacío', () => {
    const avisos = [...raiz.querySelectorAll('.aviso')].map((n) => n.textContent);
    expect(avisos.some((t) => t.includes('Aún no se han registrado'))).toBe(true);
  });
});

describe('ejecutar la predicción', () => {
  beforeEach(() => {
    vista.montar(raiz);
  });

  it('envía los valores del formulario y la localidad activa', async () => {
    escribir('pred-temperatura', 20.64);
    escribir('pred-humedad', 64.4);
    escribir('pred-luz', 646);
    escribir('pred-ruido', 62);

    pulsar('Predecir temperatura T+30 min');
    await vi.waitFor(() => expect(rutas.prediccion).toHaveBeenCalled());

    expect(rutas.prediccion).toHaveBeenCalledWith(expect.objectContaining({
      temperatura: 20.64,
      humedad: 64.4,
      luz: 646,
      ruido: 62,
      localidad_id: 8,
      entorno_interior: false,
    }));
  });

  it('envía los valores como números, no como texto', async () => {
    pulsar('Predecir temperatura T+30 min');
    await vi.waitFor(() => expect(rutas.prediccion).toHaveBeenCalled());

    const enviado = rutas.prediccion.mock.calls[0][0];
    expect(typeof enviado.temperatura).toBe('number');
    expect(typeof enviado.hora).toBe('number');
  });

  it('pinta la temperatura estimada y el cambio esperado', async () => {
    pulsar('Predecir temperatura T+30 min');
    await vi.waitFor(() => {
      expect(raiz.textContent).toContain('20,24 °C');
    });

    const valores = [...raiz.querySelectorAll('.metrica__valor')].map((n) => n.textContent);
    expect(valores).toContain('20,24 °C');
    expect(valores).toContain('-0,40 °C');
  });

  it('acumula la lectura en el historial de la sesión', async () => {
    escribir('pred-temperatura', 20.64);
    escribir('pred-humedad', 64.4);

    pulsar('Predecir temperatura T+30 min');
    await vi.waitFor(() => expect(estado.historial()).toHaveLength(1));

    expect(estado.historial()[0]).toEqual({ temperatura: 20.64, humedad: 64.4 });
  });

  it('muestra el mensaje del backend si la predicción falla', async () => {
    rutas.prediccion.mockRejectedValue(new Error('Modelo no entrenado'));

    pulsar('Predecir temperatura T+30 min');
    await vi.waitFor(() => {
      expect(raiz.querySelector('.aviso--error')).not.toBeNull();
    });

    expect(raiz.querySelector('.aviso--error').textContent).toBe('Modelo no entrenado');
  });

  it('no registra la lectura si la predicción falló', async () => {
    rutas.prediccion.mockRejectedValue(new Error('Modelo no entrenado'));

    pulsar('Predecir temperatura T+30 min');
    await vi.waitFor(() => expect(raiz.querySelector('.aviso--error')).not.toBeNull());

    expect(estado.historial()).toHaveLength(0);
  });
});

describe('historial de la sesión', () => {
  beforeEach(() => {
    vista.montar(raiz);
  });

  it('lista las lecturas de la más reciente a la más antigua', async () => {
    escribir('pred-temperatura', 18);
    pulsar('Predecir temperatura T+30 min');
    await vi.waitFor(() => expect(estado.historial()).toHaveLength(1));

    escribir('pred-temperatura', 19);
    pulsar('Predecir temperatura T+30 min');
    await vi.waitFor(() => expect(estado.historial()).toHaveLength(2));

    const filas = raiz.querySelectorAll('tbody tr');
    // La numeración cuenta desde la más reciente: 1 es la última lectura.
    expect([...filas[0].querySelectorAll('td')].map((td) => td.textContent))
      .toEqual(['1', '19,00', '72,0']);
    expect([...filas[1].querySelectorAll('td')].map((td) => td.textContent))
      .toEqual(['2', '18,00', '72,0']);
  });

  it('el botón de limpiar vacía el historial', async () => {
    pulsar('Predecir temperatura T+30 min');
    await vi.waitFor(() => expect(raiz.querySelector('tbody tr')).not.toBeNull());

    pulsar('Limpiar historial');

    expect(estado.historial()).toHaveLength(0);
    expect(raiz.querySelector('tbody tr')).toBeNull();
  });
});

describe('precarga desde la pestaña del Arduino', () => {
  beforeEach(() => {
    vista.montar(raiz);
  });

  it('rellena el formulario con la lectura recibida', () => {
    document.dispatchEvent(new CustomEvent('microclima:precargar', {
      detail: {
        temperatura: 21.5, humedad: 66, luz: 700, ruido: 58,
      },
    }));

    expect(document.getElementById('pred-temperatura').value).toBe('21.5');
    expect(document.getElementById('pred-luz').value).toBe('700');
  });

  it('conserva el valor anterior si la lectura trae un hueco', () => {
    escribir('pred-ruido', 45);

    document.dispatchEvent(new CustomEvent('microclima:precargar', {
      detail: { temperatura: 21.5, ruido: null },
    }));

    expect(document.getElementById('pred-temperatura').value).toBe('21.5');
    expect(document.getElementById('pred-ruido').value).toBe('45');
  });
});

describe('actualizar', () => {
  it('muestra los metadatos geográficos de la localidad activa', () => {
    vista.montar(raiz);

    vista.actualizar();

    const valores = [...raiz.querySelectorAll('.metrica__valor')].map((n) => n.textContent);
    expect(valores).toContain('2.570 m');
    expect(valores).toContain('88 %');
    expect(valores).toContain('4,6278°');
  });

  it('sigue la localidad cuando el usuario la cambia', () => {
    vista.montar(raiz);

    estado.seleccionarLocalidad(13);
    vista.actualizar();

    const valores = [...raiz.querySelectorAll('.metrica__valor')].map((n) => n.textContent);
    expect(valores).toContain('2.600 m');
  });

  it('no pinta contexto si el catálogo aún no cargó', async () => {
    vi.resetModules();
    estado = await import('../web/js/estado.js');
    ({ vista } = await import('../web/js/vistas/prediccion.js'));
    vista.montar(raiz);

    expect(() => vista.actualizar()).not.toThrow();
  });
});
