// Vista previa con datos de EJEMPLO. Logica pura y sin React -- ver kpi.test.js. Los numeros salen de
// `datosDeEjemplo.js`; aqui solo se decide CUANDO se ofrece.
//
// Un rol solo ve los KPIs que tiene permitidos, y de esos solo hay un caso de ejemplo: un KPI PERMITIDO cuyo
// rango vuelve vacio (`ofreceVerEjemplo`, «Ver ejemplo»). El ejemplo es solo de pantalla: el borrador sigue
// siendo el KPI real, asi que no hay ids de ejemplo, ni guardas de guardado o de mezcla.

import { rangoVacio } from "./datosDeEjemplo.js";

/** Si la vista previa del editor ofrece «Ver ejemplo»: deteccion perezosa de un KPI REAL (permitido) cuya consulta del
 * rango volvio vacia. Solo con UN KPI real elegido, ya cargado y sin errores; las tablas en vivo no lo ofrecen
 * (no tienen "rango vacio"). */
export function ofreceVerEjemplo({ kpiReal, esTablaVivo, loading, pendiente, error, snapshots }) {
  return Boolean(
    kpiReal && !esTablaVivo && !loading && !pendiente && !error
    && snapshots?.length === 1 && rangoVacio(snapshots[0]),
  );
}
