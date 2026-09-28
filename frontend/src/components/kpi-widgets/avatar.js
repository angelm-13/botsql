/**
 * No existe ningun avatar/emoji real de usuario en todo el sistema (backend
 * ni frontend, confirmado buscando en ambos) -- este es el esquema nuevo:
 * iniciales sobre un color estable derivado de `id_user`.
 *
 * Paleta DELIBERADAMENTE distinta de `CATEGORICAL` (color por KPI, ver
 * Dashboard.jsx) y de `colores_categoria` (estado del material, backend):
 * tonos tierra/taller, ninguno repite un hex de esas dos paletas, para que
 * un avatar nunca se confunda con el color de un KPI o de una categoria.
 */
const PALETA_AVATAR = [
  "#8b5e3c", "#6d5847", "#7a6a53", "#5b6b5b",
  "#4a5a6a", "#6b5b73", "#7a5c5c", "#5a6b6b",
];

export function colorDeAvatar(idUsuario) {
  const indice = Math.abs(Number(idUsuario) || 0) % PALETA_AVATAR.length;
  return PALETA_AVATAR[indice];
}

export function inicialesDe(nombreCompleto) {
  const partes = String(nombreCompleto || "").trim().split(/\s+/).filter(Boolean);
  if (!partes.length) return "?";
  const primera = partes[0][0] || "";
  const ultima = partes.length > 1 ? partes[partes.length - 1][0] : "";
  return (primera + ultima).toUpperCase();
}
