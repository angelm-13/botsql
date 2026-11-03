// Cuando un documento tiene que traer fecha de vencimiento al cargarlo. Puro y sin React -- ver
// vencimientoDeDocumento.test.js.
//
// ESPEJO de `CATEGORIAS_VENCIMIENTO_OBLIGATORIO` / `CATEGORIAS_VENCIMIENTO_O_SIN_VENCIMIENTO` en
// backend/app/services/document_service.py, que es quien manda (responde 400 `documents.expiration_required`): aqui solo
// se evita el viaje. Si cambia la regla, se cambia en los dos lugares. Las llaves son el `code` de `document_category`.
//   * obligatorio: la fecha siempre (certification).
//   * o_sin_vencimiento: la fecha, o marcar "Sin vencimiento" (employee, supplier).
//   * opcional: cualquier otra categoria.
export const VENCIMIENTO_POR_CATEGORIA = {
  certification: "obligatorio",
  employee: "o_sin_vencimiento",
  supplier: "o_sin_vencimiento",
};

export function reglaDeVencimiento(codigoDeCategoria) {
  return VENCIMIENTO_POR_CATEGORIA[codigoDeCategoria] || "opcional";
}

/** El error del formulario de carga, o `null` si va bien: `"contradiccion"` (marcar "sin vencimiento" y dar una fecha),
 * `"obligatoria"` (la categoria exige fecha y no hay), `"orden"` (vence antes de emitirse). Las fechas son `YYYY-MM-DD`
 * (el valor de un `<input type="date">`), que se comparan como texto. */
export function errorDeVencimiento({ codigoDeCategoria, emision, vencimiento, sinVencimiento }) {
  const regla = reglaDeVencimiento(codigoDeCategoria);
  const sinMarca = regla === "o_sin_vencimiento" && Boolean(sinVencimiento);
  if (sinMarca && vencimiento) return "contradiccion";
  if (!vencimiento && !sinMarca && regla !== "opcional") return "obligatoria";
  if (emision && vencimiento && vencimiento < emision) return "orden";
  return null;
}
