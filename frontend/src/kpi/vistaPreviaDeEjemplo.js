// Vista previa de KPIs NO disponibles (sin permiso o sin datos) con datos de EJEMPLO. Logica pura y sin React
// -- ver kpi.test.js. Los numeros salen de `datosDeEjemplo.js`; aqui solo se decide COMO conviven con el
// catalogo real y por que un ejemplo nunca se puede guardar ni mezclar.

/** Prefijo del `id_kpi_definition` de un KPI de ejemplo: nunca choca con un id numerico real. */
export const PREFIJO_EJEMPLO = "ejemplo:";

export const MOTIVO_SIN_PERMISO = "sin_permiso";
export const MOTIVO_SIN_DATOS = "sin_datos";
export const MOTIVO_MODULO_NO_HABILITADO = "modulo_no_habilitado";

export const esIdDeEjemplo = (id) => String(id ?? "").startsWith(PREFIJO_EJEMPLO);
export const esKpiDeEjemplo = (kpi) => Boolean(kpi?.esEjemplo);

/** Un KPI de `GET /kpi_definition/no_disponibles` (o uno real sin datos) como opcion de ejemplo del selector. */
export function kpiDeEjemplo(kpi, motivo) {
  return {
    ...kpi,
    id_kpi_definition: `${PREFIJO_EJEMPLO}${kpi.clave}`,
    esEjemplo: true,
    motivo: motivo || kpi.motivo || MOTIVO_SIN_PERMISO,
  };
}

/** El catalogo real mas los KPIs no disponibles como ejemplos. Un KPI que ya esta en el catalogo real (el
 * usuario SI puede usarlo) nunca se duplica como ejemplo. */
export function catalogoConEjemplos(catalogoReal, noDisponibles) {
  const reales = new Set((catalogoReal || []).map((kpi) => kpi.clave));
  const ejemplos = (noDisponibles || [])
    .filter((kpi) => kpi?.clave && !reales.has(kpi.clave))
    .map((kpi) => kpiDeEjemplo(kpi));
  return [...(catalogoReal || []), ...ejemplos];
}

/** Si entre los ids elegidos hay un KPI de ejemplo. */
export const hayEjemploEnSeleccion = (ids) => (ids || []).some(esIdDeEjemplo);

/** Un borrador solo se guarda si TODOS sus ids son numeros reales: un ejemplo nunca llega a la API. */
export const sePuedeGuardar = (ids) => (ids || []).length > 0
  && (ids || []).every((id) => !esIdDeEjemplo(id) && Number.isFinite(Number(id)));
