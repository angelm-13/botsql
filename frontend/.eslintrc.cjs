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
  overrides: [
    {
      // Usar un `const`/`let` antes de su declaracion NO falla al compilar ni al
      // hacer el build: lanza ReferenceError (zona muerta temporal) solo cuando
      // esa linea se ejecuta, y en un componente eso desmonta la app entera. Se
      // exige en el codigo del Dashboard de KPIs y sus vecinos; el resto del
      // proyecto aun no se ha revisado con esta regla.
      files: [
        'src/main.jsx',
        'src/pages/Dashboard.jsx',
        'src/pages/DashboardPreviewPage.jsx',
        'src/components/ErrorBoundary.jsx',
        'src/components/FormularioPlegable.jsx',
        'src/components/kpi-widgets/**/*.{js,jsx}',
        'src/kpi/**/*.js',
      ],
      rules: {
        // variables: true -> tambien dentro de un mismo ambito (la trampa real);
        // functions: true -> una funcion declarada con `function` se puede llamar
        // antes, pero se pide el mismo orden para leerse de arriba hacia abajo.
        'no-use-before-define': ['error', { functions: true, classes: true, variables: true }],
      },
    },
  ],
}
