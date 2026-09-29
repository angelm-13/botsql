// Del borrador del editor (panelState en Dashboard.jsx) a los `parametros` que
// se guardan en el widget, y de vuelta. Puro y sin React -- ver kpi.test.js.
//
// Lo que se guarda es lo mismo que antes armaba handleSubmit en
// KpiWidgetPanel; se saco a un modulo para que la vista previa del editor
// consulte EXACTAMENTE lo que se va a guardar, no una copia que se
// desincronice.

/** Los `parametros` de un widget a partir del borrador del editor.
 *
 * - `esTabla`: un widget de tabla (KPI "vivo") son datos de "ahora": no guarda
 *   periodo, filtros ni colores.
 * - `tieneBajoStock`: el umbral solo se guarda si el KPI "articulos_bajo_stock"
 *   esta entre los elegidos (se captura en el widget, no en una columna).
 */
export function armarParametros(estado, { esTabla = false, tieneBajoStock = false } = {}) {
  if (esTabla) return {};
  const parametros = { fecha_inicio: estado.fechaInicio, fecha_fin: estado.fechaFin };
  if (estado.comparar) {
    parametros.fecha_inicio_b = estado.fechaInicioB;
    parametros.fecha_fin_b = estado.fechaFinB;
  }
  if (estado.empleadosSeleccionados.length) parametros.empleados = estado.empleadosSeleccionados.map(Number);
  if (estado.departamentosSeleccionados.length) parametros.id_departments = estado.departamentosSeleccionados.map(Number);
  // Solo los overrides de KPIs que siguen seleccionados -- un KPI que se
  // quito de la seleccion no debe dejar un color huerfano guardado.
  const coloresVigentes = Object.fromEntries(
    estado.idsKpiSeleccionados.filter((id) => estado.coloresKpi[id]).map((id) => [id, estado.coloresKpi[id]]),
  );
  if (Object.keys(coloresVigentes).length) parametros.colores_kpi = coloresVigentes;
  if (estado.agruparPor === "periodo") parametros.agrupar_por = "periodo";
  if (tieneBajoStock && estado.umbralBajoStock !== "" && Number.isFinite(Number(estado.umbralBajoStock))) {
    parametros.umbral_bajo_stock = Number(estado.umbralBajoStock);
  }
  return parametros;
}

/** El widget que representa un borrador (lo que consulta la vista previa). */
export function widgetDeBorrador(estado, opciones) {
  return {
    tipo_grafica: estado.tipoGrafica,
    ids_kpi_definition: estado.idsKpiSeleccionados.map(Number),
    parametros: armarParametros(estado, opciones),
  };
}
