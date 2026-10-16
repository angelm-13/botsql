// Vista previa con datos de EJEMPLO. Logica pura y sin React -- ver kpi.test.js. Los numeros salen de
// `datosDeEjemplo.js`; aqui solo se decide COMO conviven con el catalogo real y por que un ejemplo nunca se
// puede guardar ni mezclar.
//
// Un rol solo ve los KPIs que tiene permitidos: un KPI SIN PERMISO ya no se ofrece como ejemplo (ni el backend
// lo manda). Quedan dos casos: un KPI PERMITIDO cuyo rango vuelve vacio (`ofreceVerEjemplo`, «Ver ejemplo») y,
// detras de dos candados apagados, uno de un modulo fuera del plan (`modulo_no_habilitado`).

import { rangoVacio } from "./datosDeEjemplo.js";

/** Prefijo del `id_kpi_definition` de un KPI de ejemplo: nunca choca con un id numerico real. */
export const PREFIJO_EJEMPLO = "ejemplo:";

// Un backend viejo mandaba este motivo; ya no se ofrece como ejemplo (ver `catalogoConEjemplos`).
const MOTIVO_SIN_PERMISO_RETIRADO = "sin_permiso";
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
    motivo: motivo || kpi.motivo || MOTIVO_MODULO_NO_HABILITADO,
  };
}

/** El catalogo real mas los KPIs de modulos fuera del plan como ejemplos. Un KPI que ya esta en el catalogo real
 * (el usuario SI puede usarlo) nunca se duplica como ejemplo, y uno SIN PERMISO nunca se ofrece: el selector
 * de un rol trae solo lo que tiene permitido. */
export function catalogoConEjemplos(catalogoReal, noDisponibles) {
  const reales = new Set((catalogoReal || []).map((kpi) => kpi.clave));
  const ejemplos = (noDisponibles || [])
    .filter((kpi) => kpi?.clave && !reales.has(kpi.clave) && kpi.motivo !== MOTIVO_SIN_PERMISO_RETIRADO)
    .map((kpi) => kpiDeEjemplo(kpi));
  return [...(catalogoReal || []), ...ejemplos];
}

/** Si la vista previa del editor ofrece «Ver ejemplo»: deteccion perezosa de un KPI REAL (permitido) cuya consulta del
 * rango volvio vacia. Solo con UN KPI real elegido, ya cargado y sin errores; ni los de ejemplo ni las tablas en
 * vivo (que no tienen "rango vacio") lo ofrecen. */
export function ofreceVerEjemplo({ kpiReal, esEjemplo, esTablaVivo, loading, pendiente, error, snapshots }) {
  return Boolean(
    kpiReal && !esEjemplo && !esTablaVivo && !loading && !pendiente && !error
    && snapshots?.length === 1 && rangoVacio(snapshots[0]),
  );
}

/** Si entre los ids elegidos hay un KPI de ejemplo. */
export const hayEjemploEnSeleccion = (ids) => (ids || []).some(esIdDeEjemplo);

/** Un borrador solo se guarda si TODOS sus ids son numeros reales: un ejemplo nunca llega a la API. */
export const sePuedeGuardar = (ids) => (ids || []).length > 0
  && (ids || []).every((id) => !esIdDeEjemplo(id) && Number.isFinite(Number(id)));
