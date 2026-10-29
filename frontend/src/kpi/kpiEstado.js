// En que estado esta lo que devolvio `/kpi_snapshot/query`: con datos, sin datos en el periodo o sin calcular.
// Puro y sin React -- ver kpiEstado.test.js.
//
// El servidor manda `n_filas` (filas de `kpi_snapshot` del rango) y `calculado` (el KPI tiene alguna fila, de
// cualquier fecha) junto al `total`. Sin ellos un `total` de 0 era igual para "0 calculado" y para "no hay filas".
// Un servidor que todavia no los manda cuenta como "con datos": se muestra lo de siempre.
export const CON_DATOS = "con_datos";
export const SIN_DATOS = "sin_datos";
export const NO_CALCULADO = "no_calculado";

export function estadoDeDatos(snapshots) {
  const rangos = (Array.isArray(snapshots) ? snapshots : [snapshots]).map((snapshot) => snapshot?.rango_a).filter(Boolean);
  if (rangos.length === 0) return CON_DATOS;
  if (rangos.every((rango) => rango.calculado === false)) return NO_CALCULADO;
  if (rangos.every((rango) => rango.calculado === false || rango.n_filas === 0)) return SIN_DATOS;
  return CON_DATOS;
}
