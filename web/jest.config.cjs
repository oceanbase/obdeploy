const { createConfig } = require('@umijs/test');

const config = createConfig({
  jsTransformerOpts: { jsx: 'automatic' },
});

module.exports = {
  ...config,
  rootDir: __dirname,
  testEnvironment: 'node',
  moduleNameMapper: {
    ...config.moduleNameMapper,
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  // The repository pins ansi-regex 6 for production dependencies, while
  // Jest's bundled default reporter still expects ansi-regex 5's CommonJS
  // export. Keep the production pin and use a dependency-free reporter.
  reporters: ['<rootDir>/tests/JestReporter.cjs'],
  testMatch: ['<rootDir>/tests/**/*.test.ts?(x)'],
};
