import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['tests-web/**/*.test.js'],
    // Por defecto sin DOM; los módulos que lo necesiten piden jsdom
    // con el comentario "@vitest-environment jsdom" en su archivo.
    environment: 'node',

    coverage: {
      provider: 'v8',
      // Se mide todo web/js, incluido main.js. No se excluye nada para
      // maquillar la cifra: el mismo criterio aplicado a arduino_collector.
      include: ['web/js/**/*.js'],
      all: true,
      reporter: ['text', 'lcov', 'html'],
      reportsDirectory: 'coverage-web',

      // Mismo criterio que fail_under en Python: el umbral se fija por
      // debajo de la cobertura real para que proteja lo ganado sin ser
      // fragil, y solo sube cuando la cifra real ya lo supera.
      // Historial: 0 % (linea base) -> 9.05 % -> 24.51 % -> 46.71 %.
      thresholds: {
        statements: 45,
        branches: 55,
        functions: 47,
        lines: 45,
      },
    },
  },
});
