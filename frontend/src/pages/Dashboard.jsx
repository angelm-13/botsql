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
  getAllKpiDefinition, queryKpiSnapshot, getAllUser, getAllDepartment, getAllProduct,
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

// Unicos tipos que pueden combinar varios KPIs en el mismo widget -- "numero"
// y "dona" se quedan limitados a uno solo (ver KpiWidgetPanel.aplicarTipoGrafica).
const MULTI_KPI_CHART_TYPES = ["barras", "linea", "area"];
function esTipoMultiKpi(tipoGrafica) {
  return MULTI_KPI_CHART_TYPES.includes(tipoGrafica);
}

// Mismo tope por omision que `KPI_RANGO_DIAS_MAX_POR_OMISION` en
// `backend/app/routes/kpi.py`: el backend sigue siendo la autoridad real (un
// plan de cliente puede declarar otro limite via `limite('kpi_rango_dias_max', ...)`),
// esto solo evita el viaje redondo cuando el rango ya se ve mal armado.
const KPI_RANGO_DIAS_MAX = 365;

function diffDias(fechaInicio, fechaFin) {
  if (!fechaInicio || !fechaFin) return 0;
  const inicio = new Date(`${fechaInicio}T00:00:00`);
  const fin = new Date(`${fechaFin}T00:00:00`);
  return Math.round((fin - inicio) / 86400000);
}

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
const COLOR_OTHERS = "#898781";
const AXIS_TICK = { fontSize: 11, fill: "#898781" };

// Color fijo por KPI (no por posicion en un arreglo): antes un widget de un
// solo KPI siempre salia con `CATEGORICAL[0]` sin importar cual KPI fuera, y
// el mismo par de KPIs combinados en dos widgets distintos podia salir con
// colores distintos si se elegian en otro orden. El modulo (`%`) sobre el id
// real es determinista y estable entre widgets/tableros -mismo KPI, mismo
// color, siempre- sin necesitar guardar un mapeo aparte. Con las 8 entradas
// de CATEGORICAL y solo 3 KPIs reales hoy (ver KPI_REGISTRY en
// backend/app/kpis/registry.py) el riesgo de colision es nulo en la
// practica; si el catalogo real llegara a superar las 8 entradas, dos KPIs
// podrian coincidir en color -aceptable por ahora, no hay pedido de un
// selector manual todavia.
function colorDeKpi(idKpiDefinition) {
  const id = Number(idKpiDefinition);
  if (!Number.isFinite(id)) return COLOR_OTHERS;
  return CATEGORICAL[((id % CATEGORICAL.length) + CATEGORICAL.length) % CATEGORICAL.length];
}

// Color EFECTIVO de un KPI dentro de un widget ya guardado: el override manual
// (`parametros.colores_kpi`, `{ [id_kpi_definition]: '#hex' }`) gana sobre el
// determinista de `colorDeKpi` cuando existe. Las llaves de un objeto JSON
// siempre llegan como string -- de ahi el `String(id)` al leer.
function colorEfectivoDeKpi(idKpiDefinition, coloresOverride) {
  const override = (coloresOverride || {})[String(idKpiDefinition)];
  return override || colorDeKpi(idKpiDefinition);
}

// Avatar por omision para un empleado: no hay fotos de perfil reales, asi que
// este icono neutro sobre fondo circular es el placeholder en todos lados
// donde se muestra un nombre de empleado. `color` (opcional) es el acento
// determinista por persona del picker de empleados -- ver colorDeKpi, mismo
// patron `id % CATEGORICAL.length`, reusado aqui para id_user en vez de
// id_kpi_definition.
function EmployeeAvatar({ size = "regular", color }) {
  return (
    <span className={`kpi-avatar ${size === "small" ? "small" : ""}`} style={color ? { background: color } : undefined}>
      <User size={size === "small" ? 10 : 13} color={color ? "#fff" : undefined} />
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

function startOfWeekIso() {
  const fecha = new Date();
  const dia = fecha.getDay(); // 0 = domingo
  const offset = dia === 0 ? 6 : dia - 1; // semana ISO: lunes como inicio
  fecha.setDate(fecha.getDate() - offset);
  return fecha.toISOString().slice(0, 10);
}

function startOfMonthIso() {
  const fecha = new Date();
  fecha.setDate(1);
  return fecha.toISOString().slice(0, 10);
}

// SOLO VISUAL -- exhibicion, no filtra nada todavia. `departments` (el prop
// real, via getAllDepartment) no trae mas que "General" en la practica hoy;
// esta lista fija es puramente de aparador para que el picker no se vea
// vacio, NO esta conectada a Permission.id_department ni a ninguna tabla real.
// No confundir con una fila de `department`: no hay migracion, no hay
// id_department real detras de estos nombres. Cuando haya un pedido real de
// filtrar por departamento, esto se reemplaza por datos de verdad.
const DEPARTAMENTOS_VISUALES = ["RRHH", "Contabilidad", "Producción", "Ventas", "Sistemas/TI", "Administración", "Logística"];

// "Personalizado" no trae `range`: solo marca el modo manual, nunca toca los
// campos -- los atajos son un llenado rapido, no un reemplazo de los
// selectores de fecha libres.
const DATE_SHORTCUTS = [
  { key: "hoy", label: "Hoy", range: () => [todayIso(), todayIso()] },
  { key: "semana", label: "Esta semana", range: () => [startOfWeekIso(), todayIso()] },
  { key: "mes", label: "Este mes", range: () => [startOfMonthIso(), todayIso()] },
  { key: "personalizado", label: "Personalizado", range: null },
];

// El panel "Agregar grafico" es permanente (ya no se monta/desmonta al
// abrir/cerrar), asi que su borrador ya no puede vivir en un useState propio
// -se perderia entero al cambiar de tablero-. Dashboard() guarda uno de
// estos por `id_kpi_dashboard` (ver `panelStateByDashboard`); esta funcion
// es el valor con el que arranca un tablero que todavia no tiene entrada.
function defaultPanelState() {
  return {
    editingWidgetId: null,
    idsKpiSeleccionados: [],
    categoriaKpi: "",
    tipoGrafica: "numero",
    fechaInicio: daysAgoIso(30),
    fechaFin: todayIso(),
    atajoActivo: null,
    comparar: false,
    fechaInicioB: "",
    fechaFinB: "",
    empleadosSeleccionados: [],
    departamentosSeleccionados: [],
    coloresKpi: {},
    // "entidad": desglosado por empleado/producto (comportamiento de
    // siempre). "periodo": una sola serie sumada entre todas las entidades,
    // por dia -- la tendencia en el tiempo que Aurora pidio poder elegir
    // ("Ambas, seleccionable").
    agruparPor: "entidad",
    // Solo aplica al KPI "articulos_bajo_stock": el umbral se captura aqui,
    // en el widget, y nunca en una columna nueva de base de datos (decision
    // explicita de Aurora -- no hay stock minimo declarado en el catalogo de
    // productos).
    umbralBajoStock: "",
  };
}

// Como etiquetar una entidad segun la dimension real del KPI (empleado,
// producto o "global" -- sin desglose).
function labelForDimension(dimension, userLabel, productLabel) {
  if (dimension === "producto") return productLabel;
  if (dimension === "global") return () => "Total";
  return userLabel;
}

function listOf(data) {
  return Array.isArray(data) ? data : data?.items || [];
}

function localeFor(lang) {
  return lang === "ja" ? "ja-JP" : lang === "en" ? "en-US" : lang === "pt" ? "pt-BR" : lang === "de" ? "de-DE" : "es-MX";
}

// El nombre de campo del backend (`por_empleado`) es historico -- se
// conserva tal cual aunque ahora tambien puede traer productos (KPIs con
// dimension "producto") o quedar vacio (KPIs "globales", ej. ingresos/
// egresos totales, o cuando el widget pidio `agrupar_por=periodo`). Este
// helper decide de que campo leer segun el modo de agrupacion elegido en el
// widget, sin que cada `build*Data` tenga que repetir la logica.
function entradasPorModo(ladoDelRango, agruparPorPeriodo) {
  return agruparPorPeriodo ? (ladoDelRango?.por_periodo || {}) : (ladoDelRango?.por_empleado || {});
}

function buildSeriesData(snapshot, labelForId, entidadesFiltro, agruparPorPeriodo) {
  const porA = entradasPorModo(snapshot?.rango_a, agruparPorPeriodo);
  const porB = entradasPorModo(snapshot?.rango_b, agruparPorPeriodo);
  let ids = Array.from(new Set([...Object.keys(porA), ...Object.keys(porB)]));
  if (agruparPorPeriodo) {
    // Las llaves son fechas ISO (`AAAA-MM-DD`): ordenan bien como texto.
    ids.sort();
  } else if (Array.isArray(entidadesFiltro) && entidadesFiltro.length) {
    const orden = entidadesFiltro.map(String);
    ids = orden.filter((id) => ids.includes(id));
  } else {
    ids.sort((x, y) => (porA[y] ?? 0) - (porA[x] ?? 0));
  }
  return ids.map((id) => ({
    name: labelForId(id),
    a: porA[id] ?? 0,
    b: id in porB ? porB[id] : undefined,
  }));
}

// Un widget con varios KPIs hace una llamada a `/kpi_snapshot/query` POR CADA
// id (ver KpiWidgetCard) -- `snapshots[i]` corresponde a `kpiInfos[i]`. Cada
// fila resultante trae una columna `kpi_<indice>_a`/`kpi_<indice>_b` por KPI,
// para que Recharts pinte una serie por cada uno sin tocar el eje X (que
// sigue siendo por empleado, igual que con un solo KPI).
function buildMultiSeriesData(snapshots, labelForId, entidadesFiltro, agruparPorPeriodo) {
  const ids = new Set();
  snapshots.forEach((snapshot) => {
    Object.keys(entradasPorModo(snapshot?.rango_a, agruparPorPeriodo)).forEach((id) => ids.add(id));
    Object.keys(entradasPorModo(snapshot?.rango_b, agruparPorPeriodo)).forEach((id) => ids.add(id));
  });
  let ordenados = Array.from(ids);
  if (agruparPorPeriodo) {
    ordenados.sort();
  } else if (Array.isArray(entidadesFiltro) && entidadesFiltro.length) {
    const orden = entidadesFiltro.map(String);
    ordenados = orden.filter((id) => ordenados.includes(id));
  } else {
    const totalPorId = (id) => snapshots.reduce(
      (suma, snapshot) => suma + (entradasPorModo(snapshot?.rango_a, agruparPorPeriodo)[id] ?? 0), 0,
    );
    ordenados.sort((x, y) => totalPorId(y) - totalPorId(x));
  }
  return ordenados.map((id) => {
    const fila = { name: labelForId(id) };
    snapshots.forEach((snapshot, index) => {
      const porA = entradasPorModo(snapshot?.rango_a, agruparPorPeriodo);
      const porB = entradasPorModo(snapshot?.rango_b, agruparPorPeriodo);
      fila[`kpi_${index}_a`] = porA[id] ?? 0;
      fila[`kpi_${index}_b`] = id in porB ? porB[id] : undefined;
    });
    return fila;
  });
}

// Nombre real del KPI (no "Periodo A/B" generico) con su unidad al lado --
// para que el tooltip/leyenda no confundan KPIs de distinta naturaleza (ej.
// moneda vs. porcentaje) combinados en la misma grafica.
function kpiSeriesLabel(kpiInfo, index) {
  const etiqueta = kpiInfo?.etiqueta || `KPI #${index + 1}`;
  return kpiInfo?.unidad ? `${etiqueta} (${kpiInfo.unidad})` : etiqueta;
}

function buildPieData(snapshot, labelForId, othersLabel, agruparPorPeriodo) {
  const porA = entradasPorModo(snapshot?.rango_a, agruparPorPeriodo);
  const entradas = agruparPorPeriodo
    ? Object.entries(porA).sort((x, y) => (x[0] < y[0] ? -1 : x[0] > y[0] ? 1 : 0))
    : Object.entries(porA).sort((x, y) => y[1] - x[1]);
  const principales = entradas.slice(0, CATEGORICAL.length);
  const restoTotal = entradas.slice(CATEGORICAL.length).reduce((suma, [, valor]) => suma + valor, 0);
  const data = principales.map(([id, valor]) => ({ name: labelForId(id), value: valor }));
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
  const [departments, setDepartments] = useState([]);
  const [products, setProducts] = useState([]);

  // Borrador del panel "Agregar grafico", uno por tablero (`id_kpi_dashboard`):
  // el panel ya no se desmonta al cambiar de tablero, asi que su estado no
  // puede vivir dentro del componente del panel -se perderia o se mezclaria
  // entre tableros-. Vive aqui, arriba, indexado por tablero.
  const [panelStateByDashboard, setPanelStateByDashboard] = useState({});
  const currentPanelState = panelStateByDashboard[activeId] || defaultPanelState();

  const updatePanelState = useCallback((idDashboard, patch) => {
    setPanelStateByDashboard((prev) => ({
      ...prev,
      [idDashboard]: { ...(prev[idDashboard] || defaultPanelState()), ...patch },
    }));
  }, []);

  const resetPanelState = useCallback((idDashboard) => {
    setPanelStateByDashboard((prev) => ({ ...prev, [idDashboard]: defaultPanelState() }));
  }, []);

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
    getAllDepartment({ per_page: 500 }).then((data) => { if (!cancelado) setDepartments(listOf(data)); }).catch(() => { if (!cancelado) setDepartments([]); });
    getAllProduct({ per_page: 5000 }).then((data) => { if (!cancelado) setProducts(listOf(data)); }).catch(() => { if (!cancelado) setProducts([]); });
    return () => { cancelado = true; };
  }, []);

  const userLabel = useCallback((idUser) => {
    const found = users.find((user) => String(user.id_user) === String(idUser));
    return found?.full_name || found?.username || `#${idUser}`;
  }, [users]);

  const productLabel = useCallback((idProduct) => {
    const found = products.find((product) => String(product.id_product) === String(idProduct));
    return found?.descripcion || found?.product_code || `#${idProduct}`;
  }, [products]);

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
      // Limpia tambien el borrador del panel de ESTE tablero -- ya no existe,
      // no tiene caso conservarlo colgado en el mapa.
      setPanelStateByDashboard((prev) => {
        const next = { ...prev };
        delete next[dashboard.id_kpi_dashboard];
        return next;
      });
      await loadDashboards();
    } catch (error) {
      notifyError(error);
    }
  }

  async function handleDeleteWidget(widget) {
    if (!window.confirm(tx("delete_widget_confirm", "¿Quitar este gráfico del tablero?"))) return;
    try {
      await deleteKpiDashboardWidget(widget.id_kpi_dashboard_widget);
      // Si el panel de este tablero estaba editando justo el widget que se
      // acaba de borrar, no dejarlo apuntando a un id que ya no existe.
      setPanelStateByDashboard((prev) => {
        const actual = prev[activeId];
        if (!actual || actual.editingWidgetId !== widget.id_kpi_dashboard_widget) return prev;
        return { ...prev, [activeId]: defaultPanelState() };
      });
      await loadWidgets(activeId);
    } catch (error) {
      notifyError(error);
    }
  }

  // Carga en el panel (permanente, compartido con la cuadricula) los datos
  // del widget elegido para editar, reemplazando por completo el borrador
  // que hubiera en este tablero.
  function handleEditWidget(widget) {
    const ids = Array.isArray(widget.ids_kpi_definition) ? widget.ids_kpi_definition.map(String) : [];
    const primerKpi = kpiCatalog.find((kpi) => String(kpi.id_kpi_definition) === ids[0]);
    const parametros = widget.parametros || {};
    updatePanelState(activeId, {
      editingWidgetId: widget.id_kpi_dashboard_widget,
      idsKpiSeleccionados: ids,
      categoriaKpi: primerKpi?.modulo || "",
      tipoGrafica: widget.tipo_grafica || "numero",
      fechaInicio: parametros.fecha_inicio || daysAgoIso(30),
      fechaFin: parametros.fecha_fin || todayIso(),
      atajoActivo: null,
      comparar: Boolean(parametros.fecha_inicio_b && parametros.fecha_fin_b),
      fechaInicioB: parametros.fecha_inicio_b || "",
      fechaFinB: parametros.fecha_fin_b || "",
      empleadosSeleccionados: Array.isArray(parametros.empleados) ? parametros.empleados.map(String) : [],
      departamentosSeleccionados: Array.isArray(parametros.id_departments) ? parametros.id_departments.map(String) : [],
      // Las llaves de `colores_kpi` ya llegan como string desde el JSON
      // guardado -- se copian tal cual, sin volver a tocar el tipo.
      coloresKpi: parametros.colores_kpi && typeof parametros.colores_kpi === "object" ? { ...parametros.colores_kpi } : {},
      agruparPor: parametros.agrupar_por === "periodo" ? "periodo" : "entidad",
      umbralBajoStock: parametros.umbral_bajo_stock != null ? String(parametros.umbral_bajo_stock) : "",
    });
  }

  async function handleSaveWidget(payload, editingWidgetId) {
    if (editingWidgetId) {
      await updateKpiDashboardWidget(editingWidgetId, payload);
    } else {
      await createKpiDashboardWidget(activeId, payload);
    }
    // El panel es permanente -no hay overlay que cerrar-, asi que "terminar"
    // significa vaciar el borrador de ESTE tablero, listo para el siguiente.
    resetPanelState(activeId);
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
            <button className="button primary" onClick={() => resetPanelState(activeId)}>
              <Plus size={16} />{tx("add_widget", "Agregar gráfico")}
            </button>
          </div>

          {/* Panel permanente: ya no se monta/desmonta con un clic (ver
              PANEL "AGREGAR GRAFICO" ESTATICO POR DASHBOARD). `key={activeId}`
              fuerza una instancia nueva por tablero para que el estado
              efimero de UI (error, saving, aviso) del componente arranque
              limpio al cambiar de tablero -- el borrador real (KPIs, fechas,
              filtros) vive arriba en `panelStateByDashboard` y sobrevive al
              remount via props. */}
          <KpiWidgetPanel
            key={activeId}
            panelState={currentPanelState}
            onChangePanelState={(patch) => updatePanelState(activeId, patch)}
            kpiCatalog={kpiCatalog}
            users={users}
            departments={departments}
            onCancel={() => resetPanelState(activeId)}
            onSave={(payload) => handleSaveWidget(payload, currentPanelState.editingWidgetId)}
            t={t}
            tx={tx}
          />

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
                  productLabel={productLabel}
                  formatNumber={formatNumber}
                  onEdit={() => handleEditWidget(widget)}
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
                  onClick={() => resetPanelState(activeId)}
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

    </section>
  );
}

function KpiWidgetCard({ widget, kpiCatalog, userLabel, productLabel, formatNumber, onEdit, onDelete, t, tx }) {
  const [snapshots, setSnapshots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const idsKpiDefinition = Array.isArray(widget.ids_kpi_definition) ? widget.ids_kpi_definition : [];
  // "numero" y "dona" solo grafican un KPI (ver reglas en KpiWidgetPanel): si
  // el widget trajera mas de uno guardado -no deberia, el panel ya lo evita
  // al guardar- solo se usa el primero, defensivo para no romper la pantalla.
  const idsUsados = ["numero", "dona"].includes(widget.tipo_grafica) ? idsKpiDefinition.slice(0, 1) : idsKpiDefinition;
  const idsKey = idsUsados.join(",");
  const kpiInfos = idsUsados.map((id) => kpiCatalog.find((kpi) => kpi.id_kpi_definition === id));
  const parametros = widget.parametros || {};
  const fechaInicio = parametros.fecha_inicio;
  const fechaFin = parametros.fecha_fin;
  const fechaInicioB = parametros.fecha_inicio_b;
  const fechaFinB = parametros.fecha_fin_b;
  const empleadosKey = Array.isArray(parametros.empleados) ? parametros.empleados.join(",") : "";
  const departamentosKey = Array.isArray(parametros.id_departments) ? parametros.id_departments.join(",") : "";
  const agruparPor = parametros.agrupar_por === "periodo" ? "periodo" : "entidad";

  useEffect(() => {
    let cancelado = false;
    async function cargar() {
      if (idsUsados.length === 0) {
        setLoading(false);
        setSnapshots([]);
        setError("missing_kpi");
        return;
      }
      if (!fechaInicio || !fechaFin) {
        setLoading(false);
        setSnapshots([]);
        setError("missing_range");
        return;
      }
      setLoading(true);
      setError("");
      try {
        const paramsComunes = { fecha_inicio: fechaInicio, fecha_fin: fechaFin };
        if (fechaInicioB && fechaFinB) {
          paramsComunes.fecha_inicio_b = fechaInicioB;
          paramsComunes.fecha_fin_b = fechaFinB;
        }
        if (empleadosKey) paramsComunes.empleados = empleadosKey;
        if (departamentosKey) paramsComunes.id_departments = departamentosKey;
        if (agruparPor === "periodo") paramsComunes.agrupar_por = agruparPor;
        // Una llamada POR CADA KPI del widget -- el backend solo acepta un
        // `id_kpi_definition` a la vez, la combinacion pasa aqui.
        const resultados = await Promise.all(
          idsUsados.map((id) => queryKpiSnapshot({ ...paramsComunes, id_kpi_definition: id })),
        );
        if (!cancelado) setSnapshots(resultados);
      } catch (err) {
        if (!cancelado) { setError(err.message || "errors.request_failed"); setSnapshots([]); }
      } finally {
        if (!cancelado) setLoading(false);
      }
    }
    cargar();
    return () => { cancelado = true; };
  // `idsKey` es el proxy estable de `idsUsados` (un array nuevo cada
  // render); `idsUsados` en si mismo nunca deberia ir en las dependencias.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idsKey, fechaInicio, fechaFin, fechaInicioB, fechaFinB, empleadosKey, departamentosKey, agruparPor]);

  const chartTypeLabel = CHART_TYPES.find((opt) => opt.value === widget.tipo_grafica)?.label || widget.tipo_grafica;
  const rangoTexto = fechaInicio && fechaFin ? `${fechaInicio} → ${fechaFin}` : tx("missing_range", "Sin rango de fechas configurado");
  const rangoBTexto = fechaInicioB && fechaFinB ? `${fechaInicioB} → ${fechaFinB}` : "";
  const titulo = kpiInfos.length > 1
    ? kpiInfos.map((info, index) => info?.etiqueta || `KPI #${idsUsados[index]}`).join(" + ")
    : (kpiInfos[0]?.etiqueta || tx("unknown_kpi", `KPI #${idsUsados[0] ?? "?"}`));

  return (
    <article className="kpi-widget-card">
      <div className="kpi-widget-card-header">
        <div>
          <h4>{titulo}</h4>
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
        {!loading && error === "missing_kpi" && (
          <p className="kpi-empty-inline">{tx("widget_missing_kpi", "A este gráfico le falta un KPI. Edítalo para configurarlo.")}</p>
        )}
        {!loading && error === "errors.rango_excede_limite" && (
          <p className="kpi-error-inline">{tx("range_exceeds_limit", "El rango de fechas de este gráfico excede el máximo permitido (aprox. un año). Edítalo para acortarlo.")}</p>
        )}
        {!loading && error && !["missing_range", "missing_kpi", "errors.rango_excede_limite"].includes(error) && (
          <p className="kpi-error-inline">{t(error, error)}</p>
        )}
        {!loading && !error && snapshots.length > 0 && (
          <KpiChartBody widget={widget} snapshots={snapshots} kpiInfos={kpiInfos} userLabel={userLabel} productLabel={productLabel} formatNumber={formatNumber} tx={tx} />
        )}
      </div>
    </article>
  );
}

function KpiChartBody({ widget, snapshots, kpiInfos, userLabel, productLabel, formatNumber, tx }) {
  const snapshot = snapshots[0];
  const kpiInfo = kpiInfos[0];
  const hasCompare = Boolean(snapshot?.rango_b);
  const coloresOverride = widget.parametros?.colores_kpi;
  const agruparPorPeriodo = widget.parametros?.agrupar_por === "periodo";
  const labelForId = agruparPorPeriodo ? (id) => id : labelForDimension(kpiInfo?.dimensiones?.[0], userLabel, productLabel);

  // Umbral manual de "artículos bajo stock" (decision de Aurora: se captura
  // en el widget, no en una columna nueva de base de datos -- ver
  // `articulos_bajo_stock_query` en el backend). Solo tiene sentido con un
  // unico KPI seleccionado y ese KPI siendo justo este.
  const umbralBajoStock = Number(widget.parametros?.umbral_bajo_stock);
  const esBajoStock = kpiInfos.length <= 1 && kpiInfo?.clave === "articulos_bajo_stock" && Number.isFinite(umbralBajoStock);

  if (widget.tipo_grafica === "numero") {
    if (esBajoStock) {
      const porA = snapshot?.rango_a?.por_empleado || {};
      const bajoStock = Object.values(porA).filter((valor) => valor < umbralBajoStock).length;
      return (
        <div className="kpi-number-widget">
          <strong>{bajoStock}</strong>
          <span className="kpi-delta">{tx("bajo_stock_note", `producto(s) por debajo de ${umbralBajoStock}`)}</span>
        </div>
      );
    }
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
    const data = buildPieData(snapshot, labelForId, othersLabel, agruparPorPeriodo);
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

  // Un solo KPI: mismo layout de siempre, pero el color ya no es
  // `CATEGORICAL[0]` fijo -- es el color determinista de ESTE KPI
  // (`colorDeKpi`), para que el mismo KPI se vea siempre con el mismo color
  // sin importar en que widget aparezca. El rango de comparacion (B) reusa
  // el mismo color con menos opacidad/trazo punteado en vez de un segundo
  // color fijo -mismo criterio que ya usa el camino multi-KPI de abajo con
  // sus propias series "b".
  if (kpiInfos.length <= 1) {
    let data = buildSeriesData(snapshot, labelForId, widget.parametros?.empleados, agruparPorPeriodo);
    if (esBajoStock) data = data.filter((fila) => fila.a < umbralBajoStock);
    if (!data.length) return <p className="kpi-empty-inline">{tx("no_data", "Sin datos en el rango seleccionado.")}</p>;
    const colorKpi = colorEfectivoDeKpi(kpiInfo?.id_kpi_definition, coloresOverride);

    if (widget.tipo_grafica === "barras") {
      return (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e1e0d9" vertical={false} />
            <XAxis dataKey="name" tick={AXIS_TICK} axisLine={{ stroke: "#c3c2b7" }} tickLine={false} />
            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={44} />
            <Tooltip formatter={(value) => formatNumber(value)} />
            {hasCompare && <Legend wrapperStyle={{ fontSize: 12 }} />}
            <Bar dataKey="a" name={tx("range_a", "Periodo A")} fill={colorKpi} radius={[4, 4, 0, 0]} />
            {hasCompare && <Bar dataKey="b" name={tx("range_b", "Periodo B")} fill={colorKpi} fillOpacity={0.45} radius={[4, 4, 0, 0]} />}
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
            <Line type="monotone" dataKey="a" name={tx("range_a", "Periodo A")} stroke={colorKpi} strokeWidth={2} dot={{ r: 4 }} />
            {hasCompare && <Line type="monotone" dataKey="b" name={tx("range_b", "Periodo B")} stroke={colorKpi} strokeWidth={2} strokeDasharray="5 4" dot={{ r: 3 }} />}
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
            <Area type="monotone" dataKey="a" name={tx("range_a", "Periodo A")} stroke={colorKpi} fill={colorKpi} fillOpacity={0.25} strokeWidth={2} />
            {hasCompare && <Area type="monotone" dataKey="b" name={tx("range_b", "Periodo B")} stroke={colorKpi} fill={colorKpi} fillOpacity={0.1} strokeWidth={2} strokeDasharray="5 4" />}
          </AreaChart>
        </ResponsiveContainer>
      );
    }

    return null;
  }

  // Varios KPIs combinados: una serie por KPI, coloreada por identidad del
  // KPI (`colorDeKpi`) y no por su posicion dentro de esta seleccion -- el
  // mismo par de KPIs combinados en otro widget, o en otro orden, sale
  // siempre con los mismos colores. El eje X sigue siendo por empleado. La
  // serie de comparacion (rango B) de cada KPI reusa el MISMO color que su
  // rango A -distingue por opacidad/trazo, no por un segundo color fijo-
  // porque con N KPIs ya no hay solo dos roles (A/B) que colorear
  // aparte como con un solo KPI.
  const data = buildMultiSeriesData(snapshots, labelForId, widget.parametros?.empleados, agruparPorPeriodo);
  if (!data.length) return <p className="kpi-empty-inline">{tx("no_data", "Sin datos en el rango seleccionado.")}</p>;
  const comparacionSufijo = ` (${tx("vs_compare_short", "comparación")})`;

  if (widget.tipo_grafica === "barras") {
    return (
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e1e0d9" vertical={false} />
          <XAxis dataKey="name" tick={AXIS_TICK} axisLine={{ stroke: "#c3c2b7" }} tickLine={false} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={44} />
          <Tooltip formatter={(value) => formatNumber(value)} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {kpiInfos.map((info, index) => (
            <Bar key={`a-${index}`} dataKey={`kpi_${index}_a`} name={kpiSeriesLabel(info, index)} fill={colorEfectivoDeKpi(info.id_kpi_definition, coloresOverride)} radius={[4, 4, 0, 0]} />
          ))}
          {hasCompare && kpiInfos.map((info, index) => (
            <Bar key={`b-${index}`} dataKey={`kpi_${index}_b`} name={`${kpiSeriesLabel(info, index)}${comparacionSufijo}`} fill={colorEfectivoDeKpi(info.id_kpi_definition, coloresOverride)} fillOpacity={0.45} radius={[4, 4, 0, 0]} />
          ))}
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
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {kpiInfos.map((info, index) => (
            <Line key={`a-${index}`} type="monotone" dataKey={`kpi_${index}_a`} name={kpiSeriesLabel(info, index)} stroke={colorEfectivoDeKpi(info.id_kpi_definition, coloresOverride)} strokeWidth={2} dot={{ r: 4 }} />
          ))}
          {hasCompare && kpiInfos.map((info, index) => (
            <Line key={`b-${index}`} type="monotone" dataKey={`kpi_${index}_b`} name={`${kpiSeriesLabel(info, index)}${comparacionSufijo}`} stroke={colorEfectivoDeKpi(info.id_kpi_definition, coloresOverride)} strokeWidth={2} strokeDasharray="5 4" dot={{ r: 3 }} />
          ))}
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
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {kpiInfos.map((info, index) => (
            <Area key={`a-${index}`} type="monotone" dataKey={`kpi_${index}_a`} name={kpiSeriesLabel(info, index)} stroke={colorEfectivoDeKpi(info.id_kpi_definition, coloresOverride)} fill={colorEfectivoDeKpi(info.id_kpi_definition, coloresOverride)} fillOpacity={0.25} strokeWidth={2} />
          ))}
          {hasCompare && kpiInfos.map((info, index) => (
            <Area key={`b-${index}`} type="monotone" dataKey={`kpi_${index}_b`} name={`${kpiSeriesLabel(info, index)}${comparacionSufijo}`} stroke={colorEfectivoDeKpi(info.id_kpi_definition, coloresOverride)} fill={colorEfectivoDeKpi(info.id_kpi_definition, coloresOverride)} fillOpacity={0.1} strokeWidth={2} strokeDasharray="5 4" />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    );
  }

  return null;
}

function KpiWidgetPanel({ panelState, onChangePanelState, kpiCatalog, users, departments, onCancel, onSave, t, tx }) {
  const {
    editingWidgetId,
    idsKpiSeleccionados,
    categoriaKpi,
    tipoGrafica,
    fechaInicio,
    fechaFin,
    atajoActivo,
    comparar,
    fechaInicioB,
    fechaFinB,
    empleadosSeleccionados,
    departamentosSeleccionados,
    coloresKpi,
    agruparPor,
    umbralBajoStock,
  } = panelState;

  // KPIs fijos por modulo (dimension "empleado"/"producto") vs. variables
  // sueltas (dimension "global", ej. ingresos_totales/egresos_totales -- ver
  // el comentario de esas entradas en KPI_REGISTRY). Una variable suelta no
  // se desglosa por nada: sirve para combinar en un mismo grafico ("ingresos"
  // vs "egresos"), no para elegir por modulo, asi que vive en su propia
  // seccion del picker y se saca de la lista por modulo para no repetir el
  // mismo chip en dos lugares.
  const kpisFijos = useMemo(() => kpiCatalog.filter((kpi) => kpi.dimensiones?.[0] !== "global"), [kpiCatalog]);
  const kpisVariables = useMemo(() => kpiCatalog.filter((kpi) => kpi.dimensiones?.[0] === "global"), [kpiCatalog]);

  // Catalogo agrupado por modulo (facturacion, operaciones, ...): el paso de
  // categoria solo hace falta cuando hay mas de uno, si no se muestran los
  // KPIs directo.
  const kpisPorModulo = useMemo(() => {
    const mapa = new Map();
    kpisFijos.forEach((kpi) => {
      const lista = mapa.get(kpi.modulo) || [];
      lista.push(kpi);
      mapa.set(kpi.modulo, lista);
    });
    return mapa;
  }, [kpisFijos]);
  const modulosDisponibles = Array.from(kpisPorModulo.keys());
  const necesitaCategoria = modulosDisponibles.length > 1;

  // Efimero de UI, no borrador: se reinicia limpio en cada tablero porque
  // Dashboard() monta una instancia nueva de este componente por
  // `id_kpi_dashboard` (`key={activeId}`) -- ver PANEL "AGREGAR GRAFICO"
  // ESTATICO POR DASHBOARD en Dashboard().
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [avisoKpi, setAvisoKpi] = useState("");
  // Que swatch de color tiene su popover de paleta abierto (un id de KPI, o
  // null si ninguno) -- efimero de UI, igual que `saving`/`error` de arriba.
  const [swatchAbierto, setSwatchAbierto] = useState(null);

  const multiKpiPermitido = esTipoMultiKpi(tipoGrafica);

  // Info de los KPIs ya elegidos -- de aqui salen la etiqueta del toggle
  // "Agrupar por" (Empleado/Producto, segun la dimension real del primer KPI
  // elegido) y si hay que mostrar el campo de umbral de "artículos bajo
  // stock" (solo cuando ese KPI especifico esta seleccionado).
  const kpisSeleccionadosInfo = idsKpiSeleccionados
    .map((id) => kpiCatalog.find((kpi) => String(kpi.id_kpi_definition) === id))
    .filter(Boolean);
  const primeraDimension = kpisSeleccionadosInfo[0]?.dimensiones?.[0];
  const tieneBajoStockSeleccionado = kpisSeleccionadosInfo.some((kpi) => kpi.clave === "articulos_bajo_stock");

  // Cierra el popover de color al hacer clic fuera de el -- sin esto se
  // quedaria abierto hasta elegir un color o deseleccionar el KPI.
  useEffect(() => {
    if (!swatchAbierto) return undefined;
    function handleClickFuera(event) {
      if (!event.target.closest(".kpi-color-swatch-wrap")) setSwatchAbierto(null);
    }
    document.addEventListener("mousedown", handleClickFuera);
    return () => document.removeEventListener("mousedown", handleClickFuera);
  }, [swatchAbierto]);

  // Cambiar a "numero"/"dona" con varios KPIs marcados no rompe nada: se
  // conserva solo el primero y se avisa, en vez de guardar una combinacion
  // que ese tipo de grafica no sabe representar.
  function aplicarTipoGrafica(valor) {
    if (!esTipoMultiKpi(valor) && idsKpiSeleccionados.length > 1) {
      const conservado = idsKpiSeleccionados[0];
      const kpiConservado = kpiCatalog.find((kpi) => String(kpi.id_kpi_definition) === conservado);
      onChangePanelState({ tipoGrafica: valor, idsKpiSeleccionados: [conservado] });
      setAvisoKpi(tx("kpi_multi_not_supported", `Este tipo de gráfico solo admite un KPI. Se conservó "${kpiConservado?.etiqueta || conservado}".`));
    } else {
      onChangePanelState({ tipoGrafica: valor });
      setAvisoKpi("");
    }
  }

  function toggleKpi(idKpi) {
    setAvisoKpi("");
    if (multiKpiPermitido) {
      onChangePanelState({
        idsKpiSeleccionados: idsKpiSeleccionados.includes(idKpi)
          ? idsKpiSeleccionados.filter((item) => item !== idKpi)
          : [...idsKpiSeleccionados, idKpi],
      });
    } else {
      onChangePanelState({
        idsKpiSeleccionados: idsKpiSeleccionados.length === 1 && idsKpiSeleccionados[0] === idKpi ? [] : [idKpi],
      });
    }
  }

  // Override manual de color para UN KPI, siempre dentro de la paleta cerrada
  // CATEGORICAL -- nunca un input de color libre (ver colorEfectivoDeKpi).
  // Elegir el mismo tono que ya le tocaria por default equivale a "quitar el
  // override": no tiene caso guardar una entrada identica al determinista.
  function elegirColorKpi(idKpi, colorElegido) {
    const proximo = { ...coloresKpi };
    if (colorElegido === colorDeKpi(idKpi)) {
      delete proximo[idKpi];
    } else {
      proximo[idKpi] = colorElegido;
    }
    onChangePanelState({ coloresKpi: proximo });
    setSwatchAbierto(null);
  }

  // Un chip de KPI (fijo o variable suelta) con su swatch de color -- se usa
  // en las dos secciones del picker (KPIs por modulo y variables sueltas),
  // de ahi que salga de la lista con el mismo criterio ambas veces.
  function renderKpiChip(kpi) {
    const idStr = String(kpi.id_kpi_definition);
    const posicion = idsKpiSeleccionados.indexOf(idStr);
    // El swatch de color solo tiene sentido cuando este KPI ya esta
    // seleccionado Y el tipo de grafica activo de verdad pinta un color por
    // KPI (barras/linea/area) -- en "numero"/"dona" el color no depende del
    // KPI, no hay nada que este swatch pudiera cambiar.
    const puedeElegirColor = multiKpiPermitido && posicion >= 0;
    return (
      <div className="kpi-chip-with-swatch" key={kpi.id_kpi_definition}>
        <button
          type="button"
          className={`kpi-chip-option ${posicion >= 0 ? "active" : ""}`}
          onClick={() => toggleKpi(idStr)}
        >
          {multiKpiPermitido && posicion >= 0 && <span className="kpi-chip-badge">{posicion + 1}</span>}
          {kpi.etiqueta || kpi.clave}
        </button>
        {puedeElegirColor && (
          <div className="kpi-color-swatch-wrap">
            <button
              type="button"
              className="kpi-color-swatch"
              style={{ background: colorEfectivoDeKpi(idStr, coloresKpi) }}
              onClick={() => setSwatchAbierto((actual) => (actual === idStr ? null : idStr))}
              title={tx("kpi_color_choose", "Elegir color")}
              aria-label={tx("kpi_color_choose", "Elegir color")}
              aria-expanded={swatchAbierto === idStr}
            />
            {swatchAbierto === idStr && (
              <div className="kpi-color-popover" role="menu">
                {CATEGORICAL.map((color) => {
                  const activo = colorEfectivoDeKpi(idStr, coloresKpi) === color;
                  return (
                    <button
                      type="button"
                      key={color}
                      className={`kpi-color-option ${activo ? "active" : ""}`}
                      style={{ background: color }}
                      onClick={() => elegirColorKpi(idStr, color)}
                      aria-label={color}
                      role="menuitemradio"
                      aria-checked={activo}
                    />
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  function toggleEmpleado(idUser) {
    onChangePanelState({
      empleadosSeleccionados: empleadosSeleccionados.includes(idUser)
        ? empleadosSeleccionados.filter((item) => item !== idUser)
        : [...empleadosSeleccionados, idUser],
    });
  }

  function toggleDepartamento(idDepartamento) {
    onChangePanelState({
      departamentosSeleccionados: departamentosSeleccionados.includes(idDepartamento)
        ? departamentosSeleccionados.filter((item) => item !== idDepartamento)
        : [...departamentosSeleccionados, idDepartamento],
    });
  }

  // Los atajos solo rellenan fecha_inicio/fecha_fin -- nunca reemplazan los
  // selectores libres. "Personalizado" no trae rango: solo marca el modo
  // manual (ver DATE_SHORTCUTS).
  function aplicarAtajo(atajo) {
    if (!atajo.range) { onChangePanelState({ atajoActivo: atajo.key }); return; }
    const [inicio, fin] = atajo.range();
    onChangePanelState({ atajoActivo: atajo.key, fechaInicio: inicio, fechaFin: fin });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    if (idsKpiSeleccionados.length === 0) { setError(tx("kpi_required", "Elige al menos un KPI.")); return; }
    if (!fechaInicio || !fechaFin) { setError(tx("range_required", "Elige el rango de fechas.")); return; }
    if (diffDias(fechaInicio, fechaFin) > KPI_RANGO_DIAS_MAX) {
      setError(tx("range_exceeds_limit", "El rango de fechas no puede exceder un año. Ajusta las fechas."));
      return;
    }
    if (comparar && (!fechaInicioB || !fechaFinB)) { setError(tx("range_b_required", "Elige el rango de comparación o desactívala.")); return; }
    if (comparar && diffDias(fechaInicioB, fechaFinB) > KPI_RANGO_DIAS_MAX) {
      setError(tx("range_exceeds_limit", "El rango de comparación no puede exceder un año. Ajusta las fechas."));
      return;
    }

    const parametros = { fecha_inicio: fechaInicio, fecha_fin: fechaFin };
    if (comparar) { parametros.fecha_inicio_b = fechaInicioB; parametros.fecha_fin_b = fechaFinB; }
    if (empleadosSeleccionados.length) parametros.empleados = empleadosSeleccionados.map(Number);
    if (departamentosSeleccionados.length) parametros.id_departments = departamentosSeleccionados.map(Number);
    // Solo los overrides de KPIs que siguen seleccionados -- un KPI que se
    // quito de la seleccion no debe dejar un color huerfano guardado.
    const coloresVigentes = Object.fromEntries(
      idsKpiSeleccionados.filter((id) => coloresKpi[id]).map((id) => [id, coloresKpi[id]]),
    );
    if (Object.keys(coloresVigentes).length) parametros.colores_kpi = coloresVigentes;
    if (agruparPor === "periodo") parametros.agrupar_por = "periodo";
    if (tieneBajoStockSeleccionado && umbralBajoStock !== "" && Number.isFinite(Number(umbralBajoStock))) {
      parametros.umbral_bajo_stock = Number(umbralBajoStock);
    }

    const payload = { ids_kpi_definition: idsKpiSeleccionados.map(Number), tipo_grafica: tipoGrafica, parametros };
    setSaving(true);
    try {
      await onSave(payload);
    } catch (err) {
      const clave = err.message || "errors.request_failed";
      setError(
        clave === "errors.rango_excede_limite"
          ? tx("range_exceeds_limit", "El rango de fechas excede el máximo permitido (aprox. un año). Ajusta las fechas e inténtalo de nuevo.")
          : t(clave, clave),
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="kpi-widget-panel">
      <header>
        <div>
          <p className="eyebrow">{tx("widget", "Gráfico")}</p>
          <h3>{editingWidgetId ? tx("edit_widget", "Editar gráfico") : tx("add_widget", "Agregar gráfico")}</h3>
        </div>
        <button type="button" className="kpi-icon-button" onClick={onCancel} aria-label={t("common.cancel")}><X size={18} /></button>
      </header>

      <form onSubmit={handleSubmit}>
        {kpiCatalog.length === 0 ? (
          <div className="empty">
            <strong>{tx("no_kpis_title", "No tienes KPIs asignados")}</strong>
            <p>{tx("no_kpis_body", "Pide a un administrador que te asigne permiso sobre algún KPI para poder graficarlo aquí.")}</p>
          </div>
        ) : (
          <>
          <div className="kpi-panel-columns">
            <div className="kpi-panel-col">
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
                      onClick={() => aplicarTipoGrafica(opt.value)}
                      title={etiqueta}
                    >
                      <ChartIcon size={20} />
                      <span>{etiqueta}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="kpi-picker-section">
              <span>
                {tx("kpi", "KPI")}
                {multiKpiPermitido && idsKpiSeleccionados.length > 0 && (
                  <em className="kpi-picker-count"> — {tx("kpi_selected_count", `${idsKpiSeleccionados.length} seleccionado(s)`)}</em>
                )}
              </span>
              {avisoKpi && <p className="kpi-inline-notice">{avisoKpi}</p>}
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
                        onClick={() => onChangePanelState({ categoriaKpi: modulo })}
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
                  {(necesitaCategoria ? kpisPorModulo.get(categoriaKpi) || [] : kpisFijos).map(renderKpiChip)}
                </div>
              )}
            </div>

            {kpisVariables.length > 0 && (
              <div className="kpi-picker-section">
                <span>{tx("kpi_variables", "Variables (para combinar en un mismo gráfico)")}</span>
                <div className="kpi-chip-option-group">
                  {kpisVariables.map(renderKpiChip)}
                </div>
              </div>
            )}
            </div>

            <div className="kpi-panel-col">
            <div className="kpi-picker-section">
              <span>{tx("date_shortcuts", "Atajos de fecha")}</span>
              <div className="kpi-date-shortcuts">
                {DATE_SHORTCUTS.map((atajo) => (
                  <button
                    type="button"
                    key={atajo.key}
                    className={`kpi-shortcut-button ${atajoActivo === atajo.key ? "active" : ""}`}
                    onClick={() => aplicarAtajo(atajo)}
                  >
                    {tx(`date_shortcut_${atajo.key}`, atajo.label)}
                  </button>
                ))}
              </div>
            </div>

            {idsKpiSeleccionados.length > 0 && primeraDimension !== "global" && (
              <div className="kpi-picker-section">
                <span>{tx("group_by", "Agrupar por")}</span>
                <div className="kpi-icon-option-group">
                  <button
                    type="button"
                    className={`kpi-chip-option ${agruparPor === "entidad" ? "active" : ""}`}
                    onClick={() => onChangePanelState({ agruparPor: "entidad" })}
                  >
                    {primeraDimension === "producto" ? tx("group_by_product", "Producto") : tx("group_by_employee", "Empleado")}
                  </button>
                  <button
                    type="button"
                    className={`kpi-chip-option ${agruparPor === "periodo" ? "active" : ""}`}
                    onClick={() => onChangePanelState({ agruparPor: "periodo" })}
                  >
                    {tx("group_by_period", "Periodo (tendencia)")}
                  </button>
                </div>
              </div>
            )}

            {tieneBajoStockSeleccionado && (
              <label className="field">
                <span>{tx("umbral_bajo_stock", "Umbral de stock bajo")}</span>
                <input
                  type="number"
                  min="0"
                  value={umbralBajoStock}
                  onChange={(event) => onChangePanelState({ umbralBajoStock: event.target.value })}
                  placeholder={tx("umbral_bajo_stock_placeholder", "Ej. 10")}
                />
              </label>
            )}

            <div className="form-grid">
              <label className="field">
                <span>{tx("start_date", "Fecha inicio")}</span>
                <input
                  type="date"
                  value={fechaInicio}
                  max={fechaFin || undefined}
                  onChange={(event) => onChangePanelState({ fechaInicio: event.target.value, atajoActivo: "personalizado" })}
                  required
                />
              </label>
              <label className="field">
                <span>{tx("end_date", "Fecha fin")}</span>
                <input
                  type="date"
                  value={fechaFin}
                  min={fechaInicio || undefined}
                  onChange={(event) => onChangePanelState({ fechaFin: event.target.value, atajoActivo: "personalizado" })}
                  required
                />
              </label>
            </div>

            <label className="field checkbox-field">
              <input type="checkbox" checked={comparar} onChange={(event) => onChangePanelState({ comparar: event.target.checked })} />
              <span>{tx("compare_toggle", "Comparar contra otro periodo")}</span>
            </label>

            {comparar && (
              <div className="form-grid">
                <label className="field">
                  <span>{tx("start_date_b", "Fecha inicio (comparación)")}</span>
                  <input type="date" value={fechaInicioB} max={fechaFinB || undefined} onChange={(event) => onChangePanelState({ fechaInicioB: event.target.value })} required={comparar} />
                </label>
                <label className="field">
                  <span>{tx("end_date_b", "Fecha fin (comparación)")}</span>
                  <input type="date" value={fechaFinB} min={fechaInicioB || undefined} onChange={(event) => onChangePanelState({ fechaFinB: event.target.value })} required={comparar} />
                </label>
              </div>
            )}
            </div>

            <div className="kpi-panel-col">
            {users.length > 0 && (
              <div className="kpi-employee-picker">
                <span className="kpi-employee-picker-label">{tx("employees_filter", "Filtrar por empleados (opcional)")}</span>
                <div className="kpi-employee-list">
                  {users.map((user) => {
                    const activo = empleadosSeleccionados.includes(String(user.id_user));
                    const colorEmpleado = colorDeKpi(user.id_user);
                    return (
                      <button
                        type="button"
                        className={`kpi-employee-chip ${activo ? "active" : ""}`}
                        key={user.id_user}
                        style={{ "--employee-color": colorEmpleado }}
                        onClick={() => toggleEmpleado(String(user.id_user))}
                        aria-pressed={activo}
                        title={user.full_name || user.username || `#${user.id_user}`}
                      >
                        <EmployeeAvatar size="small" color={colorEmpleado} />
                        <span>{user.full_name || user.username || `#${user.id_user}`}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {departments.length > 0 && (
              <div className="kpi-department-picker">
                <span className="kpi-department-picker-label">{tx("departments_filter", "Filtrar por departamento (opcional)")}</span>
                <div className="kpi-department-list">
                  {departments.map((department) => (
                    <label className="kpi-department-chip" key={department.id_department}>
                      <input
                        type="checkbox"
                        checked={departamentosSeleccionados.includes(String(department.id_department))}
                        onChange={() => toggleDepartamento(String(department.id_department))}
                      />
                      <span>{department.department_description || `#${department.id_department}`}</span>
                    </label>
                  ))}
                  {/* SOLO VISUAL: ver DEPARTAMENTOS_VISUALES arriba -- no
                      filtran nada, no estan conectados a
                      Permission.id_department ni a ninguna tabla real. */}
                  {DEPARTAMENTOS_VISUALES.map((nombre) => (
                    <span
                      className="kpi-department-chip visual-only"
                      key={nombre}
                      title={tx("department_visual_only", "Próximamente: todavía no filtra datos reales")}
                    >
                      {nombre}
                    </span>
                  ))}
                </div>
              </div>
            )}
            </div>
          </div>
          </>
        )}

        {error && <div className="alert error">{error}</div>}

        <footer>
          <button type="button" className="button" onClick={onCancel}>{t("common.cancel")}</button>
          {kpiCatalog.length > 0 && <button type="submit" className="button primary" disabled={saving}>{t("common.save")}</button>}
        </footer>
      </form>
    </section>
  );
}
