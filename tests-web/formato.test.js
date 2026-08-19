/**
 * Pruebas de web/js/formato.js — presentación de valores en la interfaz.
 *
 * Las cadenas esperadas usan la convención es-CO: punto para miles y
 * coma para decimales.
 */
import { describe, expect, it } from 'vitest';
import {
  antiguedad, conSigno, entero, hora, nivelFrescura, numero, porcentaje,
} from '../web/js/formato.js';

describe('numero', () => {
  it('usa un decimal por defecto', () => {
    expect(numero(18.456)).toBe('18,5');
  });

  it('respeta la cantidad de decimales pedida', () => {
    expect(numero(18.456, 2)).toBe('18,46');
  });

  it('separa los miles con punto', () => {
    expect(numero(1234.5)).toBe('1.234,5');
  });

  it.each([null, undefined, NaN, 'no es un numero'])(
    'devuelve un guion cuando no hay dato: %s',
    (valor) => {
      expect(numero(valor)).toBe('—');
    },
  );
});

describe('entero', () => {
  it('no muestra decimales', () => {
    expect(entero(646.7)).toBe('647');
  });

  it('separa los miles', () => {
    expect(entero(1234)).toBe('1.234');
  });
});

describe('conSigno', () => {
  it('antepone el signo mas a los positivos', () => {
    expect(conSigno(2.5)).toBe('+2,50');
  });

  it('conserva el signo menos de los negativos', () => {
    expect(conSigno(-2.5)).toBe('-2,50');
  });

  it('trata el cero como positivo', () => {
    expect(conSigno(0)).toBe('+0,00');
  });

  it('devuelve un guion sin dato', () => {
    expect(conSigno(null)).toBe('—');
  });
});

describe('porcentaje', () => {
  it('convierte una proporcion 0-1 en porcentaje entero', () => {
    expect(porcentaje(0.87)).toBe('87 %');
  });

  it('redondea al entero mas cercano', () => {
    expect(porcentaje(0.876)).toBe('88 %');
  });
});

describe('hora', () => {
  it('extrae hora y minutos de una marca completa', () => {
    expect(hora('2026-04-23 12:31:23')).toBe('12:31');
  });

  it('descarta cadenas demasiado cortas', () => {
    expect(hora('2026-04-23')).toBe('—');
  });

  it.each([null, undefined, 42])('descarta valores no textuales: %s', (valor) => {
    expect(hora(valor)).toBe('—');
  });
});

describe('antiguedad', () => {
  it('avisa cuando no hay dato', () => {
    expect(antiguedad(null)).toBe('sin datos');
  });

  it('muestra segundos por debajo del minuto', () => {
    expect(antiguedad(12.4)).toBe('hace 12 s');
  });

  it('nunca muestra segundos negativos', () => {
    expect(antiguedad(-5)).toBe('hace 0 s');
  });

  it('cambia a minutos a partir del minuto', () => {
    expect(antiguedad(60)).toBe('hace 1 min');
  });

  it('cambia a horas a partir de la hora', () => {
    expect(antiguedad(3600)).toBe('hace 1 h');
  });
});

describe('nivelFrescura', () => {
  it.each([
    [null, 'caido'],
    [0, 'vivo'],
    [14.9, 'vivo'],
    [15, 'atrasado'],
    [59.9, 'atrasado'],
    [60, 'caido'],
  ])('con %s segundos el estado es %s', (segundos, esperado) => {
    expect(nivelFrescura(segundos)).toBe(esperado);
  });
});
