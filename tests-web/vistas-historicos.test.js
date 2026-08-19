/**
 * Pruebas de web/js/vistas/historicos.js — pestaña de datos históricos.
 *
 * @vitest-environment jsdom
 *
 * La vista combina cuatro llamadas a la API en paralelo, así que el doble
 * devuelve las cuatro respuestas y aquí se verifica cómo se traducen a la
 * página: métricas, insignia de origen, tabla y contexto de la localidad.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../web/js/api.js', () => ({
  rutas: {
    resumen: vi.fn(),
    actual: vi.fn(),
    ultimas: vi.fn(),
    serie: vi.fn(),
  },
}));

let vista;
let rutas;
let estado;
let raiz;

const LOCALIDADES = [
  {
    id: 8, nombre: 'Kennedy', altitud: 2570, densidad_urbana: 0.88, zona: 'Occidente',
  },
  {
    id: 13, nombre: 'Teusaquillo', altitud: 2600, densidad_urbana: 0.87, zona: 'Centro',
  },
];

const RESUMEN = {
  registros: 259140,
  temp_media: 14.32,
  humedad_media: 72.4,
  tiene_localidades: true,
  localidades: 20,
  dias: 90,
  registros_localidad: 12957,
};

const ACTUAL = {
  origen: 'dataset',
  antiguedad_min: 4,
  lectura: {
    timestamp: '2026-04-23 12:31:23',
    temperatura: 20.64,
    humedad: 64.4,
    luz: 646,
    ruido: 62,
  },
  prediccion: 20.24,
  delta: -0.4,
};

const ULTIMAS = {
  columnas: ['timestamp', 'temperatura', 'humedad'],
  filas: [
    { timestamp: '2026-04-23 12:31:23', temperatura: 20.64, humedad: 64.4 },
    { timestamp: '2026-04-23 12:21:23', temperatura: 20.1, humedad: 65.0 },
  ],
};

const SERIE = {
  puntos: [
    { timestamp: '2026-04-23 12:21:23', temperatura: 20.1, humedad: 65.0 },
    { timestamp: '2026-04-23 12:31:23', temperatura: 20.64, humedad: 64.4 },
  ],
};

/** Deja las cuatro llamadas devolviendo datos válidos. */
function respuestasNormales(cambios = {}) {
  rutas.resumen.mockResolvedValue(cambios.resumen ?? RESUMEN);
  rutas.actual.mockResolvedValue(cambios.actual ?? ACTUAL);
  rutas.ultimas.mockResolvedValue(cambios.ultimas ?? ULTIMAS);
  rutas.serie.mockResolvedValue(cambios.serie ?? SERIE);
}

beforeEach(async () => {
  vi.resetModules();
  document.body.innerHTML = '';
  raiz = document.createElement('div');
  document.body.appendChild(raiz);

  ({ rutas } = await import('../web/js/api.js'));
  estado = await import('../web/js/estado.js');
  ({ vista } = await import('../web/js/vistas/historicos.js'));

  estado.definirLocalidades(LOCALIDADES, 8);
  respuestasNormales();
});

describe('descripción de la vista', () => {
  it('se identifica para el enrutador', () => {
    expect(vista.id).toBe('historicos');
    expect(vista.titulo).toBe('Datos históricos');
  });
});

describe('montar', () => {
  it('crea las tres secciones y el selector de localidad', () => {
    vista.montar(raiz);

    expect(raiz.querySelectorAll('.seccion')).toHaveLength(3);
    expect(raiz.querySelector('#selector-historicos')).not.toBeNull();
  });

  it('deja listo el lienzo de la serie', () => {
    vista.montar(raiz);

    expect(raiz.querySelector('#grafico-historico')).not.toBeNull();
  });
});

describe('consulta a la API', () => {
  it('pide los datos de la localidad activa', async () => {
    vista.montar(raiz);

    await vista.actualizar();

    expect(rutas.resumen).toHaveBeenCalledWith(8);
    expect(rutas.serie).toHaveBeenCalledWith(8, 144);
    expect(rutas.ultimas).toHaveBeenCalledWith(8, 12);
  });

  it('traslada el modo de entorno interior a la consulta', async () => {
    estado.definirEntornoInterior(true);
    vista.montar(raiz);

    await vista.actualizar();

    expect(rutas.actual).toHaveBeenCalledWith(8, true);
  });

  it('sigue la localidad cuando el usuario la cambia', async () => {
    vista.montar(raiz);
    estado.seleccionarLocalidad(13);

    await vista.actualizar();

    expect(rutas.resumen).toHaveBeenCalledWith(13);
  });
});

describe('contexto de la localidad', () => {
  it('describe altitud, densidad y zona', async () => {
    vista.montar(raiz);

    await vista.actualizar();

    const texto = raiz.querySelector('.contexto').textContent;
    expect(texto).toContain('Kennedy');
    expect(texto).toContain('2.570 m');
    expect(texto).toContain('88 %');
    expect(texto).toContain('Occidente');
  });

  it('queda vacío si el catálogo aún no cargó', async () => {
    vi.resetModules();
    estado = await import('../web/js/estado.js');
    ({ vista } = await import('../web/js/vistas/historicos.js'));
    respuestasNormales();
    vista.montar(raiz);

    await vista.actualizar();

    expect(raiz.querySelector('.contexto').textContent).toBe('');
  });
});

describe('resumen del dataset', () => {
  it('muestra los totales con separador de miles', async () => {
    vista.montar(raiz);

    await vista.actualizar();

    const valores = [...raiz.querySelectorAll('.metrica__valor')].map((n) => n.textContent);
    expect(valores).toContain('259.140');
    expect(valores).toContain('14,3 °C');
  });

  it('rotula "Localidades" cuando el dataset las distingue', async () => {
    vista.montar(raiz);

    await vista.actualizar();

    const etiquetas = [...raiz.querySelectorAll('.metrica__etiqueta')].map((n) => n.textContent);
    expect(etiquetas).toContain('Localidades');
  });

  it('rotula "Días cubiertos" cuando el dataset no las distingue', async () => {
    respuestasNormales({ resumen: { ...RESUMEN, tiene_localidades: false } });
    vista.montar(raiz);

    await vista.actualizar();

    const etiquetas = [...raiz.querySelectorAll('.metrica__etiqueta')].map((n) => n.textContent);
    expect(etiquetas).toContain('Días cubiertos');
  });
});

describe('lectura vigente', () => {
  it('muestra las cuatro magnitudes del sensor', async () => {
    vista.montar(raiz);

    await vista.actualizar();

    const valores = [...raiz.querySelectorAll('.metrica__valor')].map((n) => n.textContent);
    expect(valores).toContain('20,64 °C');
    expect(valores).toContain('64,4 %');
    expect(valores).toContain('646 lux');
    expect(valores).toContain('62 dB');
  });

  it('marca la lectura como en vivo si viene del Arduino', async () => {
    respuestasNormales({ actual: { ...ACTUAL, origen: 'arduino' } });
    vista.montar(raiz);

    await vista.actualizar();

    const marca = raiz.querySelector('.insignia');
    expect(marca.className).toContain('insignia--vivo');
    expect(marca.textContent).toContain('en vivo');
  });

  it.each([
    ['reciente', 4, 'insignia--atrasado'],
    ['vieja', 45, 'insignia--caido'],
  ])('marca como %s una lectura del dataset de hace %s min', async (_caso, minutos, clase) => {
    respuestasNormales({ actual: { ...ACTUAL, antiguedad_min: minutos } });
    vista.montar(raiz);

    await vista.actualizar();

    expect(raiz.querySelector('.insignia').className).toContain(clase);
  });

  it('muestra la predicción y el cambio esperado con signo', async () => {
    vista.montar(raiz);

    await vista.actualizar();

    const valores = [...raiz.querySelectorAll('.metrica__valor')].map((n) => n.textContent);
    expect(valores).toContain('20,24 °C');
    expect(valores).toContain('-0,40 °C');
  });

  it('avisa que falta entrenar el modelo si no hay predicción', async () => {
    respuestasNormales({ actual: { ...ACTUAL, prediccion: null } });
    vista.montar(raiz);

    await vista.actualizar();

    expect(raiz.querySelector('.aviso').textContent).toContain('train_model.py');
  });

  it('avisa cuando la localidad no tiene lecturas', async () => {
    respuestasNormales({ actual: { ...ACTUAL, lectura: null } });
    vista.montar(raiz);

    await vista.actualizar();

    expect(raiz.querySelector('.aviso').textContent).toContain('No hay lecturas');
  });
});

describe('tabla de últimas lecturas', () => {
  it('pinta una fila por registro', async () => {
    vista.montar(raiz);

    await vista.actualizar();

    expect(raiz.querySelectorAll('tbody tr')).toHaveLength(2);
    expect(raiz.querySelectorAll('th')).toHaveLength(3);
  });

  it('avisa cuando no hay registros', async () => {
    respuestasNormales({ ultimas: { columnas: [], filas: [] } });
    vista.montar(raiz);

    await vista.actualizar();

    const avisos = [...raiz.querySelectorAll('.aviso')].map((n) => n.textContent);
    expect(avisos).toContain('Sin registros para mostrar.');
  });
});

describe('gráfica de la serie', () => {
  it('no falla si el lienzo no está en la página', async () => {
    vista.montar(raiz);
    raiz.querySelector('#grafico-historico').remove();

    await expect(vista.actualizar()).resolves.not.toThrow();
  });

  it('no falla con una serie vacía', async () => {
    respuestasNormales({ serie: { puntos: [] } });
    vista.montar(raiz);

    await expect(vista.actualizar()).resolves.not.toThrow();
  });
});
