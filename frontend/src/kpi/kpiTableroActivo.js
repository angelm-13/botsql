// El tablero que cada persona dejo abierto, para volver a el al recargar. Puro y sin React -- ver
// kpiTableroActivo.test.js.
//
// Vive en localStorage bajo una llave por id de usuario: el cierre de sesion solo borra `token`, `user` y
// `mfa_temp_token`, asi que esta llave sobrevive. Una conveniencia del navegador: toda lectura y escritura
// tolera un storage ausente o que lance (modo privado, cuota), y se cae al primer tablero.
export const PREFIJO_TABLERO_ACTIVO = "tyakxa-kpi-tablero:";

export function llaveDeTableroActivo(idUsuario) {
  if (idUsuario === null || idUsuario === undefined || idUsuario === "") return null;
  return `${PREFIJO_TABLERO_ACTIVO}${idUsuario}`;
}

/** El id guardado (texto) o `null`. */
export function leerTableroActivo(storage, idUsuario) {
  const llave = llaveDeTableroActivo(idUsuario);
  if (!llave) return null;
  try {
    return storage?.getItem(llave) || null;
  } catch {
    return null;
  }
}

export function guardarTableroActivo(storage, idUsuario, idTablero) {
  const llave = llaveDeTableroActivo(idUsuario);
  if (!llave || idTablero === null || idTablero === undefined) return;
  try {
    storage?.setItem(llave, String(idTablero));
  } catch {
    // Sin storage no se recuerda nada y ya.
  }
}

/** El tablero a abrir: el preferido (el que ya esta en pantalla o el que se pidio) si sigue en la lista; si no, el
 * guardado; si tampoco existe, el primero. Devuelve el id tal como viene en `items`, o `null` sin tableros. */
export function resolverTableroActivo(items, preferido, guardado) {
  const lista = Array.isArray(items) ? items : [];
  const existente = (id) => (id === null || id === undefined ? undefined : lista.find((item) => String(item.id_kpi_dashboard) === String(id)));
  const elegido = existente(preferido) || existente(guardado) || lista[0];
  return elegido ? elegido.id_kpi_dashboard : null;
}

/** El id del usuario con sesion, leido de `localStorage.user`; `null` si no hay o esta dañado. */
export function idDeUsuarioActual(storage) {
  try {
    const usuario = JSON.parse(storage?.getItem("user") || "null");
    return usuario?.id_user ?? null;
  } catch {
    return null;
  }
}
