/**
 * No existe ningun avatar/emoji real de usuario en todo el sistema (backend
 * ni frontend, confirmado buscando en ambos) -- este es el esquema nuevo:
 * iniciales sobre un color estable derivado de `id_user`.
 *
 * Paleta DELIBERADAMENTE distinta de `CATEGORICAL` (color por KPI, ver
 * kpi/kpiDatos.js) y de `colores_categoria` (estado del material, backend):
 * mismos tonos vivos pero un escalon mas saturado, ninguno repite un hex de
 * esas dos paletas, para que un avatar nunca se confunda con el color de un
 * KPI o de una categoria. Sin marrones, grafitos ni vinos.
 */
const PALETA_AVATAR = [
  "#3b82f6", "#f97316", "#10b981", "#ec4899",
  "#06b6d4", "#8b5cf6", "#f59e0b", "#ef4444",
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
