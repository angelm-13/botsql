// Vista previa con datos de EJEMPLO. Logica pura y sin React -- ver kpi.test.js. Los numeros salen de
// `datosDeEjemplo.js`; aqui solo se decide CUANDO se ofrece.
//
// Un rol solo ve los KPIs que tiene permitidos, y de esos solo hay un caso de ejemplo: un KPI PERMITIDO cuyo
// rango vuelve vacio (`ofreceVerEjemplo`: el ejemplo sale solo y se puede ocultar). El ejemplo es solo de pantalla: el borrador sigue
// siendo el KPI real, asi que no hay ids de ejemplo, ni guardas de guardado o de mezcla.

import { datosDeEjemplo, rangoVacio } from "./datosDeEjemplo.js";

/** Si la vista previa del editor muestra el ejemplo SOLA: TODOS los indicadores elegidos son reales (permitidos), ya
 * cargaron, sin errores, y la consulta de TODOS volvio vacia. Con uno o varios indicadores. Si alguno trae datos, se ve
 * lo real. Las tablas en vivo no lo ofrecen (no tienen "rango vacio"). */
export function ofreceVerEjemplo({ kpiInfos, esTablaVivo, loading, pendiente, error, snapshots }) {
  return Boolean(
    Array.isArray(kpiInfos) && kpiInfos.length > 0 && kpiInfos.every(Boolean)
    && !esTablaVivo && !loading && !pendiente && !error
    && Array.isArray(snapshots) && snapshots.length === kpiInfos.length
    && snapshots.every((snapshot) => rangoVacio(snapshot)),
  );
}

/** Un snapshot de ejemplo por indicador, en el mismo orden que `kpiInfos` (la forma de `/kpi_snapshot/query`). */
export function snapshotsDeEjemplo(kpiInfos, opciones) {
  return kpiInfos.map((kpi) => datosDeEjemplo(kpi, opciones));
}
