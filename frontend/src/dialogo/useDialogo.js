import { crearControlador } from "./dialogoControl.js";

// Un solo controlador para toda la app: <DialogoHost /> (montado una vez en
// main.jsx) dibuja lo que éste tenga abierto.
export const controlador = crearControlador();

const api = {
  confirmar: controlador.confirmar,
  pedirTexto: controlador.pedirTexto,
  avisar: controlador.avisar,
};

// { confirmar(mensaje) -> boolean, pedirTexto(titulo, valorInicial?) -> string|null, avisar(mensaje) }
export function useDialogo() {
  return api;
}
