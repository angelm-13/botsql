module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    // El proyecto es React 18 con Vite, que usa el runtime automatico de JSX:
    // no hace falta tener React en ambito para escribir JSX. Sin esto,
    // `react/react-in-jsx-scope` disparaba 5 501 errores en ~50 pantallas -mas
    // del 97% de todo lo que reportaba el lint- y ahogaba los hallazgos de
    // verdad: 159 variables sin usar y 19 componentes sin PropTypes quedaban
    // sepultados en el ruido.
    'plugin:react/jsx-runtime',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs'],
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  settings: { react: { version: '18.2' } },
  plugins: ['react-refresh'],
  rules: {
    'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
  },
}
