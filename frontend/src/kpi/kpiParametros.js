// Del borrador del editor (panelState en Dashboard.jsx) a los `parametros` que
// se guardan en el widget, y de vuelta. Puro y sin React -- ver kpi.test.js.
//
// Lo que se guarda es lo mismo que antes armaba handleSubmit en
// KpiWidgetPanel; se saco a un modulo para que la vista previa del editor
// consulte EXACTAMENTE lo que se va a guardar, no una copia que se
// desincronice.
import {
  RANGO_PERSONALIZADO, RANGO_RELATIVO_POR_OMISION, esRangoRelativoVigente,
  fechaLocalIso, periodoAnterior, rangoDesfasado, resolverRangoRelativo,
} from "./kpiRango.js";

/** Los `parametros` de un widget a partir del borrador del editor.
 *
 * - `esTabla`: un widget de tabla (KPI "vivo") son datos de "ahora": no guarda
 *   periodo, filtros ni colores.
 * - `tieneBajoStock`: el umbral solo se guarda si el KPI "articulos_bajo_stock"
 *   esta entre los elegidos (se captura en el widget, no en una columna).
 */
export function armarParametros(estado, { esTabla = false, tieneBajoStock = false, hoy = new Date() } = {}) {
  if (esTabla) return {};
  // Con un chip de rango relativo se guarda la INSTRUCCION (`rango_relativo`)
  // y, ademas, la foto de las fechas de hoy: quien no conozca el campo sigue
  // leyendo fechas absolutas de siempre. Sin chip ("personalizado") el
  // resultado es identico al de antes de que existieran los rangos relativos.
  const relativo = esRangoRelativoVigente(estado.rangoRelativo);
  const rangoA = relativo
    ? resolverRangoRelativo(estado.rangoRelativo, hoy)
    : { fecha_inicio: estado.fechaInicio, fecha_fin: estado.fechaFin };
  const parametros = { ...rangoA };
  if (relativo) parametros.rango_relativo = estado.rangoRelativo;
  if (estado.comparar) {
    if (relativo) {
      // Un rango B tecleado a mano se quedaria viejo en cuanto pasara un dia:
      // con un chip se compara contra el periodo inmediatamente anterior, o
      // contra el mismo rango N dias atras (`desfaseComparacion`).
      if (estado.desfaseComparacion) {
        parametros.comparar_desfase_dias = Number(estado.desfaseComparacion);
        Object.assign(parametros, rangoDesfasado(rangoA, Number(estado.desfaseComparacion)));
      } else {
        parametros.comparar_anterior = true;
        Object.assign(parametros, periodoAnterior(rangoA));
      }
    } else {
      parametros.fecha_inicio_b = estado.fechaInicioB;
      parametros.fecha_fin_b = estado.fechaFinB;
    }
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

/** El borrador del editor para un widget ya guardado (lo inverso de
 * armarParametros): lo que se carga al pulsar el lapiz de una tarjeta. Un
 * widget de antes de los rangos relativos entra como "personalizado", con sus
 * fechas absolutas intactas. */
export function estadoDeWidget(widget, kpiCatalog, hoy = new Date()) {
  const ids = Array.isArray(widget.ids_kpi_definition) ? widget.ids_kpi_definition.map(String) : [];
  const primerKpi = kpiCatalog.find((kpi) => String(kpi.id_kpi_definition) === ids[0]);
  const guardados = widget.parametros || {};
  const relativo = esRangoRelativoVigente(guardados.rango_relativo);
  const parametros = relativo ? { ...guardados, ...resolverRangoRelativo(guardados.rango_relativo, hoy) } : guardados;
  return {
    editingWidgetId: widget.id_kpi_dashboard_widget,
    paso: 0,
    idsKpiSeleccionados: ids,
    categoriaKpi: primerKpi?.modulo || "",
    tipoGrafica: widget.tipo_grafica || "numero",
    rangoRelativo: relativo ? guardados.rango_relativo : RANGO_PERSONALIZADO,
    fechaInicio: parametros.fecha_inicio || fechaLocalIso(new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - 29)),
    fechaFin: parametros.fecha_fin || fechaLocalIso(hoy),
    comparar: Boolean(parametros.fecha_inicio_b && parametros.fecha_fin_b),
    desfaseComparacion: Number(parametros.comparar_desfase_dias) > 0 ? Number(parametros.comparar_desfase_dias) : null,
    fechaInicioB: parametros.fecha_inicio_b || "",
    fechaFinB: parametros.fecha_fin_b || "",
    empleadosSeleccionados: Array.isArray(parametros.empleados) ? parametros.empleados.map(String) : [],
    departamentosSeleccionados: Array.isArray(parametros.id_departments) ? parametros.id_departments.map(String) : [],
    // Las llaves de `colores_kpi` ya llegan como string desde el JSON
    // guardado -- se copian tal cual, sin volver a tocar el tipo.
    coloresKpi: parametros.colores_kpi && typeof parametros.colores_kpi === "object" ? { ...parametros.colores_kpi } : {},
    agruparPor: parametros.agrupar_por === "periodo" ? "periodo" : "entidad",
    umbralBajoStock: parametros.umbral_bajo_stock != null ? String(parametros.umbral_bajo_stock) : "",
  };
}

/** El rango con el que arranca un borrador nuevo: los ultimos 30 dias. */
export function rangoInicialDelBorrador(hoy = new Date()) {
  const rango = resolverRangoRelativo(RANGO_RELATIVO_POR_OMISION, hoy);
  return { rangoRelativo: RANGO_RELATIVO_POR_OMISION, fechaInicio: rango.fecha_inicio, fechaFin: rango.fecha_fin };
}

/** Tipos de grafica que admiten TODOS los KPIs elegidos a la vez (interseccion de
 * sus `graficas_permitidas`). Sin KPI elegido, todos menos "tabla". "Tabla" solo
 * se ofrece si TODOS los KPIs son "vivos": aunque el registry liste "tabla" entre
 * las graficas de un KPI de serie (ej. material_por_estado), no hay renderer de
 * tabla para snapshots todavia y el widget saldria como "proximamente". Un KPI
 * sin lista no restringe nada. */
export function tiposDeGraficaPermitidos(kpiInfos, todosLosTipos) {
  const sinTabla = todosLosTipos.filter((tipo) => tipo !== "tabla");
  if (kpiInfos.length === 0) return sinTabla;
  const permitidos = kpiInfos.reduce((restantes, info) => {
    const lista = Array.isArray(info.graficas_permitidas) && info.graficas_permitidas.length ? info.graficas_permitidas : sinTabla;
    return restantes.filter((tipo) => lista.includes(tipo));
  }, todosLosTipos);
  const todosVivos = kpiInfos.every((info) => info.modo === "vivo");
  return todosVivos ? permitidos : permitidos.filter((tipo) => tipo !== "tabla");
}

/** La unidad con la que se mide un KPI. Sin unidad declarada, "numero" (igual
 * que unidadInfo en kpiDatos.js). */
export function unidadDeKpi(info) {
  return info?.unidad || "numero";
}

/** Si el grafico ya mezcla unidades distintas (un widget guardado antes de la
 * regla de unidades). Solo informativo: esos widgets se siguen viendo igual. */
export function mezclaUnidades(kpiInfos) {
  return new Set(kpiInfos.map(unidadDeKpi)).size > 1;
}

/** Por que `candidato` NO se puede sumar a un grafico que ya lleva
 * `seleccionados`, o null si se puede.
 *
 * - "unidad": otra unidad. Dos KPIs con unidades distintas (un porcentaje y una
 *   cantidad) comparten el eje Y del grafico y el de escala menor queda
 *   invisible.
 * - "modo": un KPI en vivo (tabla) y uno de serie no comparten ninguna grafica.
 */
export function motivoParaNoCombinar(seleccionados, candidato) {
  if (!seleccionados.length) return null;
  const esVivo = candidato.modo === "vivo";
  if (seleccionados.some((info) => (info.modo === "vivo") !== esVivo)) return "modo";
  const unidad = unidadDeKpi(candidato);
  if (seleccionados.some((info) => unidadDeKpi(info) !== unidad)) return "unidad";
  return null;
}
