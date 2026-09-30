import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import ErrorBoundary from "./components/ErrorBoundary";

// El limite de error va por FUERA de todo lo demas (router, sesion, menu):
// si algo de lo que hay adentro falla al dibujar, se ve el mensaje en pantalla
// en vez de un fondo vacio.
createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
