// Que le decimos a la persona cuando una consulta de KPI falla, y en que estado esta el catalogo del editor.
// Puro y sin React -- ver kpiErrores.test.js.

/** Clave de traduccion del fallo de red (sin conexion, servidor caido): la lanza `api/client.js` en lugar del TypeError del navegador. */
export const ERROR_DE_RED = "errors.network";

/** Clave de traduccion del 403 "por alcance": el rol puede ver KPIs, pero solo de sus propios registros y este es de toda la empresa. */
export const ERROR_DE_ALCANCE = "errors.kpi_scope";

/** La clave que se muestra de un fallo al consultar un KPI.
 *
 * El backend manda el MOTIVO de un 403 en `meta.reason` (`routes/kpi.py`: `reason: 'scope'`), con la misma clave de error que un
 * permiso que falta; `api/client.js` lo conserva en `error.payload`. Con `scope` se dice otra cosa, porque lo que hay que
 * hacer es distinto (pedir acceso completo, no acceso a ese KPI). Cualquier otro fallo conserva su clave de siempre. */
export function claveDeErrorDeKpi(error) {
  if (error?.payload?.meta?.reason === "scope") return ERROR_DE_ALCANCE;
  return error?.message || "errors.request_failed";
}

/** Que se ve en el editor segun el catalogo de KPIs: `cargando`, `error` (no se pudo traer), `vacio` (cargo bien y la persona
 * no tiene KPIs) o `lista` (hay con que armar el grafico). Un catalogo que todavia no llega NO es un catalogo vacio. */
export function vistaDelCatalogo({ estado = "listo", total = 0 } = {}) {
  if (estado === "cargando") return "cargando";
  if (estado === "error") return "error";
  return total > 0 ? "lista" : "vacio";
}
