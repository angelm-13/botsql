/* eslint-disable react/prop-types */
import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  ArrowDown, ArrowUp, AreaChart as AreaChartIcon, BarChart2, ClipboardList, Hash,
  LineChart as LineChartIcon, Pencil, PieChart as PieChartIcon, Plus, Receipt,
  RefreshCw, SlidersHorizontal, Trash2, User, X,
} from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, LineChart, Line, AreaChart, Area,
  PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from "recharts";
import { useI18n } from "../i18n";
import {
  getAllKpiDashboard, createKpiDashboard, updateKpiDashboard, deleteKpiDashboard,
  getAllKpiDashboardWidget, createKpiDashboardWidget, updateKpiDashboardWidget, deleteKpiDashboardWidget,
  getAllKpiDefinition, queryKpiSnapshot, getAllUser,
} from "../api";
import "../styles/kpi-dashboard.css";
import PageHeader from "../components/PageHeader.jsx";

const CHART_TYPES = [
  { value: "numero", label: "Número" },
  { value: "barras", label: "Barras" },
  { value: "linea", label: "Línea" },
  { value: "area", label: "Área" },
  { value: "dona", label: "Dona" },
];

// Un icono fijo por tipo de grafica, en vez de un <select> oculto -- se eligen
// a simple vista, igual que se hace con el tipo de grafica en el resto del
// proyecto.
const CHART_TYPE_ICONS = {
  numero: Hash,
  barras: BarChart2,
  linea: LineChartIcon,
  area: AreaChartIcon,
  dona: PieChartIcon,
};

// Mismo icono que ya usa el menu lateral para cada modulo (`groupIcons` en
// `layouts/Shell.jsx`, que a su vez viene del icono real de cada `Modulo` en
// `app/modules/registry.py` del backend): no se inventa un dibujo nuevo para
// la categoria del KPI, se reutiliza el que el usuario ya asocia con ese
// modulo en el menu. Un modulo de KPI que todavia no este aqui cae en el
// icono generico, no revienta.
const KPI_MODULE_META = {
  facturacion: { icon: Receipt, label: "Facturación" },
  operaciones: { icon: ClipboardList, label: "Operaciones" },
};
const DEFAULT_MODULE_ICON = SlidersHorizontal;

function kpiModuleMeta(modulo) {
  return KPI_MODULE_META[modulo] || {
    icon: DEFAULT_MODULE_ICON,
    label: modulo ? modulo.charAt(0).toUpperCase() + modulo.slice(1) : "",
  };
}

// Numero MINIMO de espacios "de fabrica" que se muestran en un tablero nuevo:
// sin esto, un tablero recien creado se ve como una pantalla rota en vez de
// una invitacion a llenarlo. No es un tope -- con mas widgets la cuadricula
// simplemente crece. El total real que se muestra se redondea hacia arriba al
// multiplo de columnas mas cercano (ver `useCompleteGridPlaceholders`), asi
// que puede terminar siendo mayor a este minimo.
const WIDGET_GRID_MIN_SLOTS = 6;

// Tamano del lote de sondeo: lo bastante grande para que ninguna pantalla
// real (tarjetas de 340px minimo) alcance a llenarlo en una sola fila. Se usa
// SOLO para medir sin ambiguedad cuantas columnas hay -- ver el comentario de
// `useCompleteGridPlaceholders`. Un monitor necesitaria mas de 11000px de
// ancho de contenido para llenarlo entero, asi que en la practica siempre
// desborda a una segunda fila.
const WIDGET_GRID_PROBE_SIZE = 24;

/** Cuenta cuantos hijos de `nodo` comparten el `offsetTop` del primero.
 *
 * Con la disposicion por filas de un grid normal (sin `order` ni ubicacion
 * manual, que es como esta armado `.kpi-widget-grid`), los hijos quedan en el
 * DOM en el mismo orden en que se ven. Todos los que caen en la primera fila
 * comparten el mismo `offsetTop`; el primero que tenga uno distinto ya esta
 * en la segunda fila. Es literalmente cuantas columnas decidio el navegador,
 * sin reproducir ninguna formula de `auto-fill`/`minmax`.
 */
function contarColumnasDeLaPrimeraFila(nodo) {
  const hijos = Array.from(nodo.children);
  if (hijos.length === 0) return 1;
  const primerTop = hijos[0].offsetTop;
  let columnas = 0;
  for (const hijo of hijos) {
    if (hijo.offsetTop !== primerTop) break;
    columnas += 1;
  }
  return columnas;
}

/** Cuantos placeholders "+" hacen falta para que la cuadricula no deje
 * ninguna fila a medias, midiendo las columnas REALES que el navegador ya
 * decidio -- no adivinandolas.
 *
 * Por que no se replica la formula de `auto-fill`/`minmax`
 * ------------------------------------------------------
 * Una version anterior reproducia a mano `floor((ancho + gap) / (minimo +
 * gap))` para adivinar cuantas columnas iba a pintar el grid. En la practica
 * quedo desincronizada del `auto-fill` real del navegador (caja, scrollbar,
 * redondeo de subpixeles -- cualquier diferencia de un par de pixeles corre
 * el resultado), y en una prueba real con 4 columnas visibles genero solo 6
 * espacios (fila de 4 + fila de 2) en vez de los 8 que hacian falta.
 *
 * Por que se sondea con un lote grande, no incrementando de a uno
 * -----------------------------------------------------------------
 * Si todos los hijos renderizados caben en una sola fila no se puede saber
 * si esa es la cuenta real de columnas o si sencillamente no habia hijos de
 * sobra para desbordar a una segunda fila. Una primera version resolvia esto
 * agregando un placeholder a la vez hasta desbordar -- pero eso puede
 * oscilar para siempre: si el objetivo final calculado (el minimo redondeado
 * al multiplo de columnas) coincide justo con las columnas reales -caso
 * nada raro, el minimo de fabrica es multiplo de 2, 3 y 6-, ese objetivo
 * vuelve a caber entero en una fila, se vuelve a ver "ambiguo", se vuelve a
 * incrementar, y el resultado se vuelve a achicar al medir de nuevo: un
 * ciclo sin fin que en la practica tumbaba el componente entero (React corta
 * la cadena de renders con "Maximum update depth exceeded"). En vez de eso,
 * cuando hace falta sondear se renderiza de una vez un lote fijo y
 * deliberadamente grande (`WIDGET_GRID_PROBE_SIZE`), se mide una sola vez sin
 * ambiguedad, y se salta directo al objetivo final -- nunca se vuelve a medir
 * el resultado ya ajustado (ver mas abajo), asi que no hay como oscilar.
 *
 * Por que no hace loop infinito
 * ------------------------------
 * Las columnas medidas (`columnas`) quedan guardadas en estado y el efecto
 * solo vuelve a sondear (`columnas === null`) cuando algo pudo haber cambiado
 * el ancho real -- un resize del contenedor. Una vez que `columnas` tiene un
 * valor, calcular el objetivo a partir de el es determinista y no requiere
 * volver a medir el DOM, asi que un cambio de `widgetCount` nunca dispara un
 * sondeo nuevo ni una nueva medicion que se pueda malinterpretar.
 *
 * Por que igual hace falta un ResizeObserver
 * -------------------------------------------
 * El efecto solo se vuelve a correr cuando cambian sus propias dependencias
 * -- un resize de la ventana no es ninguna de esas por si solo, asi que sin
 * nada mas las columnas conocidas se quedarian pegadas al ancho que tenia la
 * primera vez que se midieron. El observer no calcula columnas (eso lo sigue
 * haciendo la medicion real de arriba): solo invalida lo que se sabia
 * (`columnas = null`) para forzar un sondeo fresco.
 */
function useCompleteGridPlaceholders(widgetCount) {
  // El nodo del grid en ESTADO, no en un ref de objeto: `.kpi-widget-grid`
  // solo se monta cuando `activeDashboard` ya cargo (es condicional, ver el
  // render mas abajo), asi que en el primer render de este componente el
  // contenedor todavia no existe. Un `useRef` normal no avisa a ningun efecto
  // cuando su `.current` pasa de `null` al nodo real despues -- los refs
  // quedan fuera del sistema de dependencias de React a proposito, asi que
  // cualquier efecto con `[miRef]` en su arreglo de dependencias solo corre
  // una vez, con el nodo todavia en `null`, y nunca se entera de que el grid
  // ya aparecio. Guardar el nodo en estado (via un callback ref) hace que su
  // aparicion SI dispare un re-render y, con el, los efectos que dependen de
  // el.
  const [nodo, setNodo] = useState(null);
  const gridRef = useCallback((nodoActual) => setNodo(nodoActual), []);

  const [columnas, setColumnas] = useState(null); // null = hay que sondear
  const [placeholderCount, setPlaceholderCount] = useState(
    () => Math.max(0, WIDGET_GRID_MIN_SLOTS - widgetCount),
  );

  useEffect(() => {
    if (!nodo) return undefined;
    const observer = new ResizeObserver(() => setColumnas(null));
    observer.observe(nodo);
    return () => observer.disconnect();
  }, [nodo]);

  useLayoutEffect(() => {
    if (!nodo) return;

    if (columnas === null) {
      const objetivoDeSondeo = Math.max(0, WIDGET_GRID_PROBE_SIZE - widgetCount);
      if (placeholderCount !== objetivoDeSondeo) {
        setPlaceholderCount(objetivoDeSondeo);
        return; // esperar al proximo render, ya con el lote de sondeo pintado
      }
      setColumnas(contarColumnasDeLaPrimeraFila(nodo));
      return;
    }

    const minimo = Math.max(WIDGET_GRID_MIN_SLOTS, widgetCount);
    const totalObjetivo = Math.ceil(minimo / columnas) * columnas;
    const placeholdersObjetivo = Math.max(0, totalObjetivo - widgetCount);

    if (placeholdersObjetivo !== placeholderCount) {
      setPlaceholderCount(placeholdersObjetivo);
    }
  }, [nodo, widgetCount, placeholderCount, columnas]);

  return [placeholderCount, gridRef];
}

// Orden categorico validado (dataviz skill): identidad, nunca ciclado.
const CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"];
const COLOR_A = CATEGORICAL[0];
const COLOR_B = CATEGORICAL[1];
const COLOR_OTHERS = "#898781";
const AXIS_TICK = { fontSize: 11, fill: "#898781" };

// Avatar por omision para un empleado: no hay fotos de perfil reales, asi que
// este icono neutro sobre fondo circular es el placeholder en todos lados
// donde se muestra un nombre de empleado.
function EmployeeAvatar({ size = "regular" }) {
  return (
    <span className={`kpi-avatar ${size === "small" ? "small" : ""}`}>
      <User size={size === "small" ? 10 : 13} />
    </span>
  );
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgoIso(n) {
  const fecha = new Date();
  fecha.setDate(fecha.getDate() - n);
  return fecha.toISOString().slice(0, 10);
}

function listOf(data) {
  return Array.isArray(data) ? data : data?.items || [];
}

function localeFor(lang) {
  return lang === "ja" ? "ja-JP" : lang === "en" ? "en-US" : lang === "pt" ? "pt-BR" : lang === "de" ? "de-DE" : "es-MX";
}

function buildSeriesData(snapshot, userLabel, empleadosFiltro) {
  const porA = snapshot?.rango_a?.por_empleado || {};
  const porB = snapshot?.rango_b?.por_empleado || {};
  let ids = Array.from(new Set([...Object.keys(porA), ...Object.keys(porB)]));
  if (Array.isArray(empleadosFiltro) && empleadosFiltro.length) {
    const orden = empleadosFiltro.map(String);
    ids = orden.filter((id) => ids.includes(id));
  } else {
    ids.sort((x, y) => (porA[y] ?? 0) - (porA[x] ?? 0));
  }
  return ids.map((id) => ({
    name: userLabel(id),
    a: porA[id] ?? 0,
    b: id in porB ? porB[id] : undefined,
  }));
}

function buildPieData(snapshot, userLabel, othersLabel) {
  const porA = snapshot?.rango_a?.por_empleado || {};
  const entradas = Object.entries(porA).sort((x, y) => y[1] - x[1]);
  const principales = entradas.slice(0, CATEGORICAL.length);
  const restoTotal = entradas.slice(CATEGORICAL.length).reduce((suma, [, valor]) => suma + valor, 0);
  const data = principales.map(([id, valor]) => ({ name: userLabel(id), value: valor }));
  if (restoTotal > 0) data.push({ name: othersLabel, value: restoTotal });
  return data;
}

export default function Dashboard() {
  const { lang, t } = useI18n();
  const tx = useCallback((key, fallback) => t(`kpi_dashboard.${key}`, fallback), [t]);
  const locale = localeFor(lang);
  const formatNumber = useCallback((value) => new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(value || 0), [locale]);

  const [dashboards, setDashboards] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [loadingDashboards, setLoadingDashboards] = useState(true);
  const [dashboardsError, setDashboardsError] = useState("");

  const [widgets, setWidgets] = useState([]);
  const [loadingWidgets, setLoadingWidgets] = useState(false);
  const [widgetsError, setWidgetsError] = useState("");

  const [kpiCatalog, setKpiCatalog] = useState([]);
  const [users, setUsers] = useState([]);

  const [widgetForm, setWidgetForm] = useState(null);

  const [placeholderCount, widgetGridRef] = useCompleteGridPlaceholders(widgets.length);

  const loadDashboards = useCallback(async (preferredId) => {
    setLoadingDashboards(true);
    setDashboardsError("");
    try {
      const data = await getAllKpiDashboard({ per_page: 200 });
      const items = listOf(data);
      setDashboards(items);
      setActiveId((current) => {
        const target = preferredId !== undefined ? preferredId : current;
        if (target && items.some((item) => item.id_kpi_dashboard === target)) return target;
        return items[0]?.id_kpi_dashboard ?? null;
      });
    } catch (error) {
      setDashboardsError(error.message || "errors.request_failed");
    } finally {
      setLoadingDashboards(false);
    }
  }, []);

  const loadWidgets = useCallback(async (dashboardId) => {
    if (!dashboardId) { setWidgets([]); return; }
    setLoadingWidgets(true);
    setWidgetsError("");
    try {
      const data = await getAllKpiDashboardWidget(dashboardId);
      setWidgets(listOf(data));
    } catch (error) {
      setWidgetsError(error.message || "errors.request_failed");
      setWidgets([]);
    } finally {
      setLoadingWidgets(false);
    }
  }, []);

  useEffect(() => { loadDashboards(); }, [loadDashboards]);
  useEffect(() => { loadWidgets(activeId); }, [activeId, loadWidgets]);

  useEffect(() => {
    let cancelado = false;
    getAllKpiDefinition().then((data) => { if (!cancelado) setKpiCatalog(listOf(data)); }).catch(() => { if (!cancelado) setKpiCatalog([]); });
    getAllUser({ per_page: 500 }).then((data) => { if (!cancelado) setUsers(listOf(data)); }).catch(() => { if (!cancelado) setUsers([]); });
    return () => { cancelado = true; };
  }, []);

  const userLabel = useCallback((idUser) => {
    const found = users.find((user) => String(user.id_user) === String(idUser));
    return found?.full_name || found?.username || `#${idUser}`;
  }, [users]);

  function notifyError(error) {
    window.alert(t(error.message || "errors.request_failed", error.message || "errors.request_failed"));
  }

  async function handleCreateDashboard() {
    const nombre = window.prompt(tx("new_dashboard_prompt", "Nombre del nuevo tablero"));
    if (nombre === null) return;
    const trimmed = nombre.trim();
    if (!trimmed) return;
    try {
      const created = await createKpiDashboard({ nombre: trimmed });
      await loadDashboards(created.id_kpi_dashboard);
    } catch (error) {
      notifyError(error);
    }
  }

  async function handleRenameDashboard(dashboard) {
    const nombre = window.prompt(tx("rename_dashboard_prompt", "Nuevo nombre del tablero"), dashboard.nombre);
    if (nombre === null) return;
    const trimmed = nombre.trim();
    if (!trimmed || trimmed === dashboard.nombre) return;
    try {
      await updateKpiDashboard(dashboard.id_kpi_dashboard, { nombre: trimmed });
      await loadDashboards(activeId);
    } catch (error) {
      notifyError(error);
    }
  }

  async function handleDeleteDashboard(dashboard) {
    const pregunta = tx("delete_dashboard_confirm", `¿Eliminar el tablero "${dashboard.nombre}"? Esta acción no se puede deshacer.`);
    if (!window.confirm(pregunta)) return;
    try {
      await deleteKpiDashboard(dashboard.id_kpi_dashboard);
      await loadDashboards();
    } catch (error) {
      notifyError(error);
    }
  }

  async function handleDeleteWidget(widget) {
    if (!window.confirm(tx("delete_widget_confirm", "¿Quitar este gráfico del tablero?"))) return;
    try {
      await deleteKpiDashboardWidget(widget.id_kpi_dashboard_widget);
      await loadWidgets(activeId);
    } catch (error) {
      notifyError(error);
    }
  }

  async function handleSaveWidget(payload, editingWidget) {
    if (editingWidget) {
      await updateKpiDashboardWidget(editingWidget.id_kpi_dashboard_widget, payload);
    } else {
      await createKpiDashboardWidget(activeId, payload);
    }
    setWidgetForm(null);
    await loadWidgets(activeId);
  }

  const activeDashboard = useMemo(
    () => dashboards.find((item) => item.id_kpi_dashboard === activeId) || null,
    [dashboards, activeId],
  );

  return (
    <section className="dashboard kpi-dashboard">
      <PageHeader
        eyebrow={t("common.dashboard")}
        titulo={tx("title", "Tableros de KPIs")}
      >
        <button className="button ghost" onClick={() => loadDashboards()} disabled={loadingDashboards}>
        <RefreshCw size={16} />{loadingDashboards ? t("common.loading") : t("common.refresh")}
        </button>
      </PageHeader>

      {dashboardsError && <div className="alert error">{t(dashboardsError, dashboardsError)}</div>}

      {!loadingDashboards && dashboards.length > 0 && (
        <div className="kpi-tabs" role="tablist">
          {dashboards.map((dashboard) => (
            <div className={`kpi-tab ${dashboard.id_kpi_dashboard === activeId ? "active" : ""}`} key={dashboard.id_kpi_dashboard}>
              <button
                type="button"
                role="tab"
                aria-selected={dashboard.id_kpi_dashboard === activeId}
                className="kpi-tab-label"
                onClick={() => setActiveId(dashboard.id_kpi_dashboard)}
                title={dashboard.nombre}
              >
                {dashboard.nombre}
              </button>
              <button type="button" className="kpi-tab-icon" title={t("common.edit")} onClick={() => handleRenameDashboard(dashboard)}>
                <Pencil size={13} />
              </button>
              <button type="button" className="kpi-tab-icon danger" title={t("common.delete")} onClick={() => handleDeleteDashboard(dashboard)}>
                <Trash2 size={13} />
              </button>
            </div>
          ))}
          <button type="button" className="kpi-tab-add" onClick={handleCreateDashboard} title={tx("new_dashboard", "Nuevo tablero")}>
            <Plus size={16} />
          </button>
        </div>
      )}

      {!loadingDashboards && dashboards.length === 0 && !dashboardsError && (
        <div className="empty">
          <strong>{tx("empty_dashboards_title", "Todavía no tienes tableros")}</strong>
          <p>{tx("empty_dashboards_body", "Crea tu primer tablero para empezar a armar tus gráficos de KPIs.")}</p>
          <button className="button primary" onClick={handleCreateDashboard}><Plus size={16} />{tx("new_dashboard", "Nuevo tablero")}</button>
        </div>
      )}

      {activeDashboard && (
        <div className="kpi-dashboard-body">
          <div className="kpi-dashboard-toolbar">
            <button className="button primary" onClick={() => setWidgetForm({ editing: null })}>
              <Plus size={16} />{tx("add_widget", "Agregar gráfico")}
            </button>
          </div>

          {widgetsError && <div className="alert error">{t(widgetsError, widgetsError)}</div>}
          {loadingWidgets && <div className="alert">{t("common.loading")}</div>}

          {!loadingWidgets && !widgetsError && (
            <div className="kpi-widget-grid" ref={widgetGridRef}>
              {widgets.map((widget) => (
                <KpiWidgetCard
                  key={widget.id_kpi_dashboard_widget}
                  widget={widget}
                  kpiCatalog={kpiCatalog}
                  userLabel={userLabel}
                  formatNumber={formatNumber}
                  onEdit={() => setWidgetForm({ editing: widget })}
                  onDelete={() => handleDeleteWidget(widget)}
                  t={t}
                  tx={tx}
                />
              ))}
              {/* Espacios "de fabrica": llenan un tablero nuevo hasta el minimo
                  visual, redondeado hacia arriba al multiplo de columnas
                  REALES ya renderizadas por el navegador, para que ninguna
                  fila quede incompleta (ver useCompleteGridPlaceholders). No
                  son un tope -- si ya hay mas widgets que el minimo, el
                  redondeo se aplica sobre esa cantidad. */}
              {Array.from({ length: placeholderCount }).map((_, index) => (
                <button
                  type="button"
                  key={`kpi-widget-placeholder-${index}`}
                  className="kpi-widget-placeholder"
                  onClick={() => setWidgetForm({ editing: null })}
                  title={tx("add_widget", "Agregar gráfico")}
                >
                  <Plus size={22} />
                  <span>{tx("add_widget", "Agregar gráfico")}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {widgetForm && (
        <KpiWidgetFormModal
          editing={widgetForm.editing}
          kpiCatalog={kpiCatalog}
          users={users}
          onCancel={() => setWidgetForm(null)}
          onSave={handleSaveWidget}
          t={t}
          tx={tx}
        />
      )}
    </section>
  );
}

function KpiWidgetCard({ widget, kpiCatalog, userLabel, formatNumber, onEdit, onDelete, t, tx }) {
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // El backend ahora guarda una lista (`ids_kpi_definition`) para poder
  // mostrar varios KPIs en un mismo widget mas adelante, pero por ahora cada
  // widget sigue teniendo uno solo en la practica -- basta con el primero.
  // Defensivo por si llegara vacia: no deberia pasar, pero que no rompa la
  // pantalla si pasa.
  const idKpiDefinition = Array.isArray(widget.ids_kpi_definition) ? widget.ids_kpi_definition[0] : undefined;
  const kpiInfo = kpiCatalog.find((kpi) => kpi.id_kpi_definition === idKpiDefinition);
  const parametros = widget.parametros || {};
  const fechaInicio = parametros.fecha_inicio;
  const fechaFin = parametros.fecha_fin;
  const fechaInicioB = parametros.fecha_inicio_b;
  const fechaFinB = parametros.fecha_fin_b;
  const empleadosKey = Array.isArray(parametros.empleados) ? parametros.empleados.join(",") : "";

  useEffect(() => {
    let cancelado = false;
    async function cargar() {
      if (!fechaInicio || !fechaFin) {
        setLoading(false);
        setSnapshot(null);
        setError("missing_range");
        return;
      }
      setLoading(true);
      setError("");
      try {
        const params = { id_kpi_definition: idKpiDefinition, fecha_inicio: fechaInicio, fecha_fin: fechaFin };
        if (fechaInicioB && fechaFinB) {
          params.fecha_inicio_b = fechaInicioB;
          params.fecha_fin_b = fechaFinB;
        }
        if (empleadosKey) params.empleados = empleadosKey;
        const data = await queryKpiSnapshot(params);
        if (!cancelado) setSnapshot(data);
      } catch (err) {
        if (!cancelado) { setError(err.message || "errors.request_failed"); setSnapshot(null); }
      } finally {
        if (!cancelado) setLoading(false);
      }
    }
    cargar();
    return () => { cancelado = true; };
  }, [idKpiDefinition, fechaInicio, fechaFin, fechaInicioB, fechaFinB, empleadosKey]);

  const chartTypeLabel = CHART_TYPES.find((opt) => opt.value === widget.tipo_grafica)?.label || widget.tipo_grafica;
  const rangoTexto = fechaInicio && fechaFin ? `${fechaInicio} → ${fechaFin}` : tx("missing_range", "Sin rango de fechas configurado");
  const rangoBTexto = fechaInicioB && fechaFinB ? `${fechaInicioB} → ${fechaFinB}` : "";

  return (
    <article className="kpi-widget-card">
      <div className="kpi-widget-card-header">
        <div>
          <h4>{kpiInfo?.etiqueta || tx("unknown_kpi", `KPI #${idKpiDefinition}`)}</h4>
          <p className="kpi-widget-meta">{tx(`chart_type_${widget.tipo_grafica}`, chartTypeLabel)}</p>
          <p className="kpi-widget-meta">{rangoTexto}</p>
          {rangoBTexto && <p className="kpi-widget-meta">{tx("vs_label", "vs.")} {rangoBTexto}</p>}
        </div>
        <div className="kpi-widget-card-actions">
          <button type="button" className="kpi-icon-button" title={t("common.edit")} onClick={onEdit}><Pencil size={15} /></button>
          <button type="button" className="kpi-icon-button danger" title={t("common.delete")} onClick={onDelete}><Trash2 size={15} /></button>
        </div>
      </div>

      <div className="kpi-chart-box">
        {loading && <p className="kpi-empty-inline">{t("common.loading")}</p>}
        {!loading && error === "missing_range" && (
          <p className="kpi-empty-inline">{tx("widget_missing_range", "A este gráfico le falta un rango de fechas. Edítalo para configurarlo.")}</p>
        )}
        {!loading && error && error !== "missing_range" && (
          <p className="kpi-error-inline">{t(error, error)}</p>
        )}
        {!loading && !error && snapshot && (
          <KpiChartBody widget={widget} snapshot={snapshot} kpiInfo={kpiInfo} userLabel={userLabel} formatNumber={formatNumber} tx={tx} />
        )}
      </div>
    </article>
  );
}

function KpiChartBody({ widget, snapshot, kpiInfo, userLabel, formatNumber, tx }) {
  const hasCompare = Boolean(snapshot?.rango_b);

  if (widget.tipo_grafica === "numero") {
    const total = snapshot.rango_a.total;
    const totalB = snapshot.rango_b?.total;
    const unidad = kpiInfo?.unidad ? ` ${kpiInfo.unidad}` : "";
    const delta = hasCompare ? total - totalB : null;
    const deltaPct = hasCompare && totalB ? (delta / Math.abs(totalB)) * 100 : null;
    return (
      <div className="kpi-number-widget">
        <strong>{formatNumber(total)}{unidad}</strong>
        {delta !== null && (
          <span className={`kpi-delta ${delta >= 0 ? "up" : "down"}`}>
            {delta >= 0 ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
            {formatNumber(Math.abs(delta))}{unidad}
            {deltaPct !== null && Number.isFinite(deltaPct) ? ` (${deltaPct >= 0 ? "+" : ""}${deltaPct.toFixed(1)}%)` : ""}
            {" "}{tx("vs_compare", "vs. periodo anterior")}
          </span>
        )}
      </div>
    );
  }

  if (widget.tipo_grafica === "dona") {
    const othersLabel = tx("others", "Otros");
    const data = buildPieData(snapshot, userLabel, othersLabel);
    if (!data.length) return <p className="kpi-empty-inline">{tx("no_data", "Sin datos en el rango seleccionado.")}</p>;
    return (
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Tooltip formatter={(value) => formatNumber(value)} />
          <Legend
            wrapperStyle={{ fontSize: 12 }}
            formatter={(value) => (
              <span className="kpi-legend-item">
                {value !== othersLabel && <EmployeeAvatar size="small" />}
                {value}
              </span>
            )}
          />
          <Pie data={data} dataKey="value" nameKey="name" innerRadius="55%" outerRadius="80%" paddingAngle={2}>
            {data.map((entry, index) => (
              <Cell key={entry.name} fill={index < CATEGORICAL.length ? CATEGORICAL[index] : COLOR_OTHERS} stroke="#fff" strokeWidth={2} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    );
  }

  const data = buildSeriesData(snapshot, userLabel, widget.parametros?.empleados);
  if (!data.length) return <p className="kpi-empty-inline">{tx("no_data", "Sin datos en el rango seleccionado.")}</p>;

  if (widget.tipo_grafica === "barras") {
    return (
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e1e0d9" vertical={false} />
          <XAxis dataKey="name" tick={AXIS_TICK} axisLine={{ stroke: "#c3c2b7" }} tickLine={false} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={44} />
          <Tooltip formatter={(value) => formatNumber(value)} />
          {hasCompare && <Legend wrapperStyle={{ fontSize: 12 }} />}
          <Bar dataKey="a" name={tx("range_a", "Periodo A")} fill={COLOR_A} radius={[4, 4, 0, 0]} />
          {hasCompare && <Bar dataKey="b" name={tx("range_b", "Periodo B")} fill={COLOR_B} radius={[4, 4, 0, 0]} />}
        </BarChart>
      </ResponsiveContainer>
    );
  }

  if (widget.tipo_grafica === "linea") {
    return (
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e1e0d9" vertical={false} />
          <XAxis dataKey="name" tick={AXIS_TICK} axisLine={{ stroke: "#c3c2b7" }} tickLine={false} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={44} />
          <Tooltip formatter={(value) => formatNumber(value)} />
          {hasCompare && <Legend wrapperStyle={{ fontSize: 12 }} />}
          <Line type="monotone" dataKey="a" name={tx("range_a", "Periodo A")} stroke={COLOR_A} strokeWidth={2} dot={{ r: 4 }} />
          {hasCompare && <Line type="monotone" dataKey="b" name={tx("range_b", "Periodo B")} stroke={COLOR_B} strokeWidth={2} dot={{ r: 4 }} />}
        </LineChart>
      </ResponsiveContainer>
    );
  }

  if (widget.tipo_grafica === "area") {
    return (
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e1e0d9" vertical={false} />
          <XAxis dataKey="name" tick={AXIS_TICK} axisLine={{ stroke: "#c3c2b7" }} tickLine={false} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={44} />
          <Tooltip formatter={(value) => formatNumber(value)} />
          {hasCompare && <Legend wrapperStyle={{ fontSize: 12 }} />}
          <Area type="monotone" dataKey="a" name={tx("range_a", "Periodo A")} stroke={COLOR_A} fill={COLOR_A} fillOpacity={0.25} strokeWidth={2} />
          {hasCompare && <Area type="monotone" dataKey="b" name={tx("range_b", "Periodo B")} stroke={COLOR_B} fill={COLOR_B} fillOpacity={0.25} strokeWidth={2} />}
        </AreaChart>
      </ResponsiveContainer>
    );
  }

  return null;
}

function KpiWidgetFormModal({ editing, kpiCatalog, users, onCancel, onSave, t, tx }) {
  const parametrosIniciales = editing?.parametros || {};

  // Catalogo agrupado por modulo (facturacion, operaciones, ...): el paso de
  // categoria solo hace falta cuando hay mas de uno, si no se muestran los
  // KPIs directo.
  const kpisPorModulo = useMemo(() => {
    const mapa = new Map();
    kpiCatalog.forEach((kpi) => {
      const lista = mapa.get(kpi.modulo) || [];
      lista.push(kpi);
      mapa.set(kpi.modulo, lista);
    });
    return mapa;
  }, [kpiCatalog]);
  const modulosDisponibles = Array.from(kpisPorModulo.keys());
  const necesitaCategoria = modulosDisponibles.length > 1;
  // El widget guarda una lista (`ids_kpi_definition`) para poder mostrar
  // varios KPIs mas adelante, pero por ahora este formulario solo edita uno
  // -- el primero de la lista. Defensivo por si llegara vacia.
  const editingIdKpiDefinition = Array.isArray(editing?.ids_kpi_definition) ? editing.ids_kpi_definition[0] : undefined;
  const editingKpi = kpiCatalog.find((kpi) => kpi.id_kpi_definition === editingIdKpiDefinition);

  const [idKpiDefinition, setIdKpiDefinition] = useState(editingIdKpiDefinition ? String(editingIdKpiDefinition) : "");
  const [categoriaKpi, setCategoriaKpi] = useState(
    () => editingKpi?.modulo || (modulosDisponibles.length === 1 ? modulosDisponibles[0] : ""),
  );
  const [tipoGrafica, setTipoGrafica] = useState(editing?.tipo_grafica || "numero");
  const [fechaInicio, setFechaInicio] = useState(parametrosIniciales.fecha_inicio || daysAgoIso(30));
  const [fechaFin, setFechaFin] = useState(parametrosIniciales.fecha_fin || todayIso());
  const [comparar, setComparar] = useState(Boolean(parametrosIniciales.fecha_inicio_b && parametrosIniciales.fecha_fin_b));
  const [fechaInicioB, setFechaInicioB] = useState(parametrosIniciales.fecha_inicio_b || "");
  const [fechaFinB, setFechaFinB] = useState(parametrosIniciales.fecha_fin_b || "");
  const [empleadosSeleccionados, setEmpleadosSeleccionados] = useState(
    Array.isArray(parametrosIniciales.empleados) ? parametrosIniciales.empleados.map(String) : [],
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function toggleEmpleado(idUser) {
    setEmpleadosSeleccionados((prev) => (prev.includes(idUser) ? prev.filter((item) => item !== idUser) : [...prev, idUser]));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    if (!idKpiDefinition) { setError(tx("kpi_required", "Elige un KPI.")); return; }
    if (!fechaInicio || !fechaFin) { setError(tx("range_required", "Elige el rango de fechas.")); return; }
    if (comparar && (!fechaInicioB || !fechaFinB)) { setError(tx("range_b_required", "Elige el rango de comparación o desactívala.")); return; }

    const parametros = { fecha_inicio: fechaInicio, fecha_fin: fechaFin };
    if (comparar) { parametros.fecha_inicio_b = fechaInicioB; parametros.fecha_fin_b = fechaFinB; }
    if (empleadosSeleccionados.length) parametros.empleados = empleadosSeleccionados.map(Number);

    // Un solo elemento por ahora: el backend ya acepta varios KPIs por
    // widget (`ids_kpi_definition`), pero combinarlos en una misma grafica es
    // un cambio aparte -- por hoy cada widget sigue representando uno solo.
    const payload = { ids_kpi_definition: [Number(idKpiDefinition)], tipo_grafica: tipoGrafica, parametros };
    setSaving(true);
    try {
      await onSave(payload, editing);
    } catch (err) {
      setError(t(err.message || "errors.request_failed", err.message || "errors.request_failed"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="kpi-modal-backdrop" role="presentation">
      <form className="kpi-modal" onSubmit={handleSubmit}>
        <header>
          <div>
            <p className="eyebrow">{tx("widget", "Gráfico")}</p>
            <h3>{editing ? tx("edit_widget", "Editar gráfico") : tx("add_widget", "Agregar gráfico")}</h3>
          </div>
          <button type="button" className="kpi-icon-button" onClick={onCancel} aria-label={t("common.cancel")}><X size={18} /></button>
        </header>

        {kpiCatalog.length === 0 ? (
          <div className="empty">
            <strong>{tx("no_kpis_title", "No tienes KPIs asignados")}</strong>
            <p>{tx("no_kpis_body", "Pide a un administrador que te asigne permiso sobre algún KPI para poder graficarlo aquí.")}</p>
          </div>
        ) : (
          <>
            <div className="kpi-picker-section">
              <span>{tx("kpi", "KPI")}</span>
              {necesitaCategoria && (
                <div className="kpi-icon-option-group" role="group" aria-label={tx("kpi_category", "Categoría")}>
                  {modulosDisponibles.map((modulo) => {
                    const meta = kpiModuleMeta(modulo);
                    const ModuleIcon = meta.icon;
                    const activo = categoriaKpi === modulo;
                    return (
                      <button
                        type="button"
                        key={modulo}
                        className={`kpi-icon-option ${activo ? "active" : ""}`}
                        onClick={() => { setCategoriaKpi(modulo); setIdKpiDefinition(""); }}
                      >
                        <ModuleIcon size={20} />
                        <span>{meta.label}</span>
                      </button>
                    );
                  })}
                </div>
              )}
              {(!necesitaCategoria || categoriaKpi) && (
                <div className="kpi-chip-option-group">
                  {(necesitaCategoria ? kpisPorModulo.get(categoriaKpi) || [] : kpiCatalog).map((kpi) => (
                    <button
                      type="button"
                      key={kpi.id_kpi_definition}
                      className={`kpi-chip-option ${idKpiDefinition === String(kpi.id_kpi_definition) ? "active" : ""}`}
                      onClick={() => setIdKpiDefinition(String(kpi.id_kpi_definition))}
                    >
                      {kpi.etiqueta || kpi.clave}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="kpi-picker-section">
              <span>{tx("chart_type", "Tipo de gráfico")}</span>
              <div className="kpi-icon-option-group">
                {CHART_TYPES.map((opt) => {
                  const ChartIcon = CHART_TYPE_ICONS[opt.value];
                  const activo = tipoGrafica === opt.value;
                  const etiqueta = tx(`chart_type_${opt.value}`, opt.label);
                  return (
                    <button
                      type="button"
                      key={opt.value}
                      className={`kpi-icon-option ${activo ? "active" : ""}`}
                      onClick={() => setTipoGrafica(opt.value)}
                      title={etiqueta}
                    >
                      <ChartIcon size={20} />
                      <span>{etiqueta}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="form-grid">
              <label className="field">
                <span>{tx("start_date", "Fecha inicio")}</span>
                <input type="date" value={fechaInicio} max={fechaFin || undefined} onChange={(event) => setFechaInicio(event.target.value)} required />
              </label>
              <label className="field">
                <span>{tx("end_date", "Fecha fin")}</span>
                <input type="date" value={fechaFin} min={fechaInicio || undefined} onChange={(event) => setFechaFin(event.target.value)} required />
              </label>
            </div>

            <label className="field checkbox-field">
              <input type="checkbox" checked={comparar} onChange={(event) => setComparar(event.target.checked)} />
              <span>{tx("compare_toggle", "Comparar contra otro periodo")}</span>
            </label>

            {comparar && (
              <div className="form-grid">
                <label className="field">
                  <span>{tx("start_date_b", "Fecha inicio (comparación)")}</span>
                  <input type="date" value={fechaInicioB} max={fechaFinB || undefined} onChange={(event) => setFechaInicioB(event.target.value)} required={comparar} />
                </label>
                <label className="field">
                  <span>{tx("end_date_b", "Fecha fin (comparación)")}</span>
                  <input type="date" value={fechaFinB} min={fechaInicioB || undefined} onChange={(event) => setFechaFinB(event.target.value)} required={comparar} />
                </label>
              </div>
            )}

            {users.length > 0 && (
              <div className="kpi-employee-picker">
                <span className="kpi-employee-picker-label">{tx("employees_filter", "Filtrar por empleados (opcional)")}</span>
                <div className="kpi-employee-list">
                  {users.map((user) => (
                    <label className="kpi-employee-chip" key={user.id_user}>
                      <input
                        type="checkbox"
                        checked={empleadosSeleccionados.includes(String(user.id_user))}
                        onChange={() => toggleEmpleado(String(user.id_user))}
                      />
                      <EmployeeAvatar size="small" />
                      <span>{user.full_name || user.username || `#${user.id_user}`}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {error && <div className="alert error">{error}</div>}

        <footer>
          <button type="button" className="button" onClick={onCancel}>{t("common.cancel")}</button>
          {kpiCatalog.length > 0 && <button type="submit" className="button primary" disabled={saving}>{t("common.save")}</button>}
        </footer>
      </form>
    </div>
  );
}
