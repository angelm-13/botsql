/* eslint-disable react/prop-types */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AreaChart as AreaChartIcon, BarChart2, Boxes, ChevronDown, ChevronUp,
  Check, ClipboardList, FileDown, FileText, FlaskConical, GripVertical, Hash, LineChart as LineChartIcon,
  Loader2, Pencil, PieChart as PieChartIcon, Plus, Receipt,
  RefreshCw, SlidersHorizontal, Table as TableIcon, Trash2, User, Utensils,
} from "lucide-react";
import { DndContext, DragOverlay, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import { SortableContext, useSortable } from "@dnd-kit/sortable";
import { CSS as DndCss } from "@dnd-kit/utilities";
import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";
import { useI18n } from "../i18n";
import FormularioPlegable from "../components/FormularioPlegable.jsx";
import useReducedMotion from "../components/kpi-widgets/useReducedMotion";
import useMasonryRef from "../components/kpi-widgets/useMasonry";
import useRellenoDelGrid from "../components/kpi-widgets/useRellenoDelGrid";
import useReordenarTarjetas, { sinColision } from "../components/kpi-widgets/useReordenarTarjetas";
import {
  getAllKpiDashboard, createKpiDashboard, updateKpiDashboard, deleteKpiDashboard,
  getAllKpiDashboardWidget, createKpiDashboardWidget, updateKpiDashboardWidget, deleteKpiDashboardWidget, saveKpiWidgetOrdenTabla,
  getAllKpiDefinition, getKpiDimensions, queryKpiSnapshot, queryKpiVivo, getUserOptions, getAllDepartment,
} from "../api";
import "../styles/kpi-widgets.css";
import "../styles/kpi-editor.css";
import "../styles/kpi-dashboard.css";
import PageHeader from "../components/PageHeader.jsx";
import TIPO_GRAFICA_COMPONENTE from "../components/kpi-widgets/tipoGraficaComponentes";
import Skeleton from "../components/kpi-widgets/Skeleton";
import { resolverColoresModernosParaPdf } from "../kpi/colorParaPdf";
import SelectorDeKpi from "../components/kpi-widgets/SelectorDeKpi";
import {
  colorDeKpi, colorEfectivoDeKpi, enriquecerCatalogo, etiquetasDeDimension, etiquetasDeSnapshots, labelForDimension,
  muestraFiltroDePersonas, normalizarBusqueda, unidadInfo,
} from "../kpi/kpiDatos.js";
import {
  armarParametros, columnasDeWidget, estadoDeWidget, filasDeWidget, mezclaUnidades, motivoParaNoCombinar, rangoInicialDelBorrador,
  tiposDeGraficaPermitidos as tiposPermitidosPorKpi, unidadDeKpi, widgetDeBorrador,
} from "../kpi/kpiParametros.js";
import {
  DESFASES_DE_COMPARACION, ETIQUETA_RANGO_POR_OMISION, RANGOS_RELATIVOS, RANGO_PERSONALIZADO, fechaLocalIso,
  parametrosEfectivos, periodoAnterior, rangoDesfasado, resolverRangoRelativo,
} from "../kpi/kpiRango.js";
import { datosDeEjemplo } from "../kpi/datosDeEjemplo.js";
import { MOTIVO_SIN_DATOS, ofreceVerEjemplo } from "../kpi/vistaPreviaDeEjemplo.js";
import {
  filasTablaPrestamo, propsDona, propsNumero,
  propsNumeroBajoStock, propsSeries, tendenciaDeSnapshot,
} from "../kpi/kpiAdaptadores.js";

const CHART_TYPES = [
  { value: "numero", label: "Número" },
  { value: "barras", label: "Barras" },
  { value: "linea", label: "Línea" },
  { value: "area", label: "Área" },
  { value: "dona", label: "Dona" },
  // Solo para KPIs "vivos" (material_prestado_actual): lo permite el propio
  // KPI via `graficas_permitidas`, no esta lista.
  { value: "tabla", label: "Tabla" },
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

// Resolucion de la captura del reporte PDF (generarReportePdf) -- tiene que
// ser la MISMA que usan tanto la llamada a html2canvas como
// medirFilasDeTarjetas al pasar de px del DOM a px del canvas capturado, o
// las filas medidas quedan desalineadas del recorte real.
const ESCALA_CAPTURA_PDF = 2;

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
  tabla: TableIcon,
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
  inventario: { icon: Boxes, label: "Inventario" },
  laboratorio: { icon: FlaskConical, label: "Laboratorio" },
  documentos: { icon: FileText, label: "Documentos" },
  restaurante: { icon: Utensils, label: "Restaurante" },
};
const DEFAULT_MODULE_ICON = SlidersHorizontal;

function kpiModuleMeta(modulo) {
  return KPI_MODULE_META[modulo] || {
    icon: DEFAULT_MODULE_ICON,
    label: modulo ? modulo.charAt(0).toUpperCase() + modulo.slice(1) : "",
  };
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

// Barra desplegable reutilizable: boton cerrado por default con un resumen
// ("Filtrar por empleados", "3 empleados seleccionados") + chevron; al hacer
// click despliega un popover con un buscador arriba y las opciones abajo.
// Reemplaza la caja siempre-abierta que tenian antes tanto el picker de
// empleados como las variables sueltas -- mismo componente en los dos
// lugares para que se vean y se comporten igual (ver su uso en
// KpiWidgetPanel). El picker de departamento deliberadamente NO usa este
// patron por ahora, se dejo tal cual estaba (chips simples siempre visibles).
// `renderOptions(filtro)` (filtro ya normalizado via normalizarBusqueda, o ""
// sin busqueda activa) es quien decide que mostrar -- cada uso filtra su
// propia lista y arma el mensaje de "sin resultados", este componente solo
// pone el input y limpia la busqueda cada vez que se abre.
function KpiDropdownPicker({ label, searchPlaceholder, renderOptions }) {
  const [abierto, setAbierto] = useState(false);
  const [busqueda, setBusqueda] = useState("");

  // Mismo patron de "cerrar al hacer clic afuera" que ya usa el popover de
  // color de los KPIs (ver SelectorDeKpi).
  useEffect(() => {
    if (!abierto) return undefined;
    function handleClickFuera(event) {
      if (!event.target.closest(".kpi-dropdown-picker")) setAbierto(false);
    }
    document.addEventListener("mousedown", handleClickFuera);
    return () => document.removeEventListener("mousedown", handleClickFuera);
  }, [abierto]);

  function alternar() {
    setAbierto((actual) => {
      const proximo = !actual;
      if (proximo) setBusqueda("");
      return proximo;
    });
  }

  return (
    <div className="kpi-dropdown-picker">
      <button
        type="button"
        className="kpi-dropdown-picker-toggle"
        onClick={alternar}
        aria-expanded={abierto}
      >
        <span>{label}</span>
        {abierto ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>
      {abierto && (
        <div className="kpi-dropdown-picker-menu" role="menu">
          <input
            type="text"
            className="kpi-dropdown-picker-search"
            value={busqueda}
            onChange={(event) => setBusqueda(event.target.value)}
            placeholder={searchPlaceholder}
            autoFocus
          />
          {renderOptions(normalizarBusqueda(busqueda))}
        </div>
      )}
    </div>
  );
}

// AAAA-MM-DD de hoy en hora LOCAL (ver fechaLocalIso).
function todayIso() {
  return fechaLocalIso(new Date());
}

// SOLO VISUAL -- exhibicion, no filtra nada todavia. `departments` (el prop
// real, via getAllDepartment) no trae mas que "General" en la practica hoy;
// esta lista fija es puramente de aparador para que el picker no se vea
// vacio, NO esta conectada a Permission.id_department ni a ninguna tabla real.
// No confundir con una fila de `department`: no hay migracion, no hay
// id_department real detras de estos nombres. Cuando haya un pedido real de
// filtrar por departamento, esto se reemplaza por datos de verdad.
const DEPARTAMENTOS_VISUALES = ["RRHH", "Contabilidad", "Producción", "Ventas", "Sistemas/TI", "Administración", "Logística"];

// El panel "Agregar grafico" es permanente (ya no se monta/desmonta al
// abrir/cerrar), asi que su borrador ya no puede vivir en un useState propio
// -se perderia entero al cambiar de tablero-. Dashboard() guarda uno de
// estos por `id_kpi_dashboard` (ver `panelStateByDashboard`); esta funcion
// es el valor con el que arranca un tablero que todavia no tiene entrada.
function defaultPanelState() {
  return {
    editingWidgetId: null,
    // Cerrado por omision: el editor va debajo de las graficas y solo se abre
    // cuando hace falta (ver KpiWidgetPanel / FormularioPlegable).
    colapsado: true,
    // Paso del asistente (0 = Que medir); vive aqui, no en el panel, para que
    // el borrador sobreviva a cambiar de tablero.
    paso: 0,
    idsKpiSeleccionados: [],
    tipoGrafica: "numero",
    // Rango: por omision "ultimos 30 dias" como chip (se recalcula cada vez que
    // se mira); "personalizado" = fechas tecleadas a mano, como antes.
    ...rangoInicialDelBorrador(),
    comparar: false,
    // null = contra el periodo anterior; un numero = contra el mismo rango N dias atras.
    desfaseComparacion: null,
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
    // Solo cuenta para una tabla: las tablas nuevas nacen de 2 columnas (una fila de 4 datos
    // no cabe bien en 340px); las guardadas antes de este campo se abren con 1.
    columnas: 2,
    filas: 2,
  };
}

function listOf(data) {
  return Array.isArray(data) ? data : data?.items || [];
}

function localeFor(lang) {
  return lang === "ja" ? "ja-JP" : lang === "en" ? "en-US" : lang === "pt" ? "pt-BR" : lang === "de" ? "de-DE" : "es-MX";
}

function esperar(ms) {
  return new Promise((resolve) => { setTimeout(resolve, ms); });
}

// Franja vertical (en px de CANVAS, ya multiplicada por `escalaCaptura` --
// debe ser la MISMA escala que se le pasa a html2canvas) que ocupa cada fila
// REAL de tarjetas dentro del grid, midiendo el DOM en vivo (getBoundingClientRect)
// antes de capturar -- no un recorte a una altura de pagina fija. Esto es lo
// que le permite a `agregarSeccionAlPdf` cortar SOLO entre filas completas,
// nunca a la mitad de una tarjeta (ver el comentario ahi). Ignora
// `.kpi-widget-placeholder` porque busca `.kpi-widget-card`, una clase
// distinta -- los espacios "de fabrica" ya se ocultan aparte durante la
// captura (ver kpi-pdf-exporting en kpi-dashboard.css), pero aunque no se
// ocultaran esta funcion no los contaria.
function medirFilasDeTarjetas(nodoGrid, escalaCaptura) {
  const tarjetas = Array.from(nodoGrid.querySelectorAll(".kpi-widget-card"));
  if (tarjetas.length === 0) return [];
  const gridRect = nodoGrid.getBoundingClientRect();
  const filas = [];
  let filaActual = [];
  let topFilaActual = null;

  function cerrarFila() {
    if (filaActual.length === 0) return;
    const top = Math.min(...filaActual.map((r) => r.top));
    const bottom = Math.max(...filaActual.map((r) => r.bottom));
    filas.push({ top: top * escalaCaptura, bottom: bottom * escalaCaptura });
    filaActual = [];
  }

  tarjetas.forEach((tarjeta) => {
    const r = tarjeta.getBoundingClientRect();
    const top = r.top - gridRect.top;
    const bottom = r.bottom - gridRect.top;
    // Un par de pixeles de tolerancia -- suficiente para el redondeo de
    // subpixel del layout, no para confundir dos filas distintas.
    if (topFilaActual !== null && Math.abs(top - topFilaActual) > 4) cerrarFila();
    topFilaActual = top;
    filaActual.push({ top, bottom });
  });
  cerrarFila();
  return filas;
}

// Dibuja UNA seccion (un panel/tablero completo, ya capturado como `canvas`
// por html2canvas, con sus filas ya medidas en vivo por
// `medirFilasDeTarjetas`) dentro de `pdf`, empacando tantas FILAS COMPLETAS
// como quepan en cada pagina -- nunca corta una fila (ni, por lo tanto, una
// tarjeta) a la mitad; si ni siquiera la primera fila pendiente cabe entera
// en una pagina nueva, se dibuja sola de todas formas (mejor una fila que
// se sale un poco del margen que una que desaparece). `estadoPagina`
// (`{ vacia: bool }`) es compartido entre TODAS las llamadas a esta funcion
// durante la generacion de un mismo PDF: el primer bloque de la primera
// seccion reusa la pagina en blanco con la que jsPDF ya arranca; cualquier
// otro bloque -sea la continuacion de una seccion muy alta, o el arranque
// de la siguiente seccion- agrega una pagina nueva. Eso resuelve a la vez
// "compactar sin espacios en blanco" y "cada panel en su propia
// seccion/salto de pagina" con la misma regla.
function agregarSeccionAlPdf({ pdf, canvas, filas, margin, tituloSeccion, estadoPagina }) {
  if (filas.length === 0) return;
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const anchoDisponible = pageWidth - margin * 2;
  const escala = anchoDisponible / canvas.width;

  let indiceFila = 0;
  let esPrimerBloqueDeSeccion = true;
  while (indiceFila < filas.length) {
    if (estadoPagina.vacia) {
      estadoPagina.vacia = false;
    } else {
      pdf.addPage();
    }

    let yImagen = margin;
    if (esPrimerBloqueDeSeccion) {
      pdf.setFontSize(13);
      pdf.setFont(undefined, "bold");
      pdf.text(tituloSeccion, margin, margin + 10);
      yImagen = margin + 24;
    }
    const altoDisponiblePx = (pageHeight - yImagen - margin) / escala;

    const inicioBloque = filas[indiceFila].top;
    let finBloque = filas[indiceFila].bottom;
    let ultimaFilaIncluida = indiceFila;
    for (let i = indiceFila + 1; i < filas.length; i += 1) {
      if (filas[i].bottom - inicioBloque > altoDisponiblePx) break;
      finBloque = filas[i].bottom;
      ultimaFilaIncluida = i;
    }

    const altoBloquePx = finBloque - inicioBloque;
    const franja = document.createElement("canvas");
    franja.width = canvas.width;
    franja.height = altoBloquePx;
    franja.getContext("2d").drawImage(canvas, 0, inicioBloque, canvas.width, altoBloquePx, 0, 0, canvas.width, altoBloquePx);
    pdf.addImage(franja.toDataURL("image/png"), "PNG", margin, yImagen, anchoDisponible, altoBloquePx * escala);

    indiceFila = ultimaFilaIncluida + 1;
    esPrimerBloqueDeSeccion = false;
  }
}

// Al arrastrar, dnd-kit no desplaza a las vecinas: su estrategia por rectangulos supone que el orden
// de la lista es el de los rectangulos, y en el masonry no lo es. El orden que toma el tablero lo
// decide `elegirOrden` (kpi/kpiMasonry.js) simulando el masonry, y el navegador acomoda las tarjetas
// con ese orden (ver useReordenarTarjetas.js).
const sinDesplazarVecinas = () => null;

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

  const reducirMovimiento = useReducedMotion();
  // Ancla del editor (debajo de la cuadricula) y contador de "llevame al
  // editor": cada pedido incrementa el contador y el efecto de abajo hace el
  // scroll suave -- ver abrirEditor y onAbierto del panel.
  const editorRef = useRef(null);
  const [pedidoScrollEditor, setPedidoScrollEditor] = useState(0);
  // Widget recien creado: su tarjeta entra con animacion y la pantalla se
  // lleva hasta ella (el editor se cierra solo al agregar, ver handleSaveWidget).
  const [idWidgetNuevo, setIdWidgetNuevo] = useState(null);

  // Abre el editor de ESTE tablero con un borrador nuevo (o con el widget que
  // se va a editar, via `estado`) y pide el scroll suave hasta el.
  const abrirEditor = useCallback((idDashboard, estado = {}) => {
    setPanelStateByDashboard((prev) => ({
      ...prev,
      [idDashboard]: { ...defaultPanelState(), ...estado, colapsado: false },
    }));
    setPedidoScrollEditor((n) => n + 1);
  }, []);

  useEffect(() => {
    if (!pedidoScrollEditor) return undefined;
    // El panel anima su alto al abrirse (.22s): si el scroll saliera al
    // instante, llegaria a la altura que el documento tiene TODAVIA y se
    // quedaria corto. Con reduced-motion no hay animacion que esperar.
    const espera = reducirMovimiento ? 0 : 260;
    const cronometro = setTimeout(() => {
      editorRef.current?.scrollIntoView({ behavior: reducirMovimiento ? "auto" : "smooth", block: "start" });
    }, espera);
    return () => clearTimeout(cronometro);
  }, [pedidoScrollEditor, reducirMovimiento]);

  useEffect(() => {
    if (!idWidgetNuevo) return undefined;
    document.querySelector(`[data-widget-id="${idWidgetNuevo}"]`)
      ?.scrollIntoView({ behavior: reducirMovimiento ? "auto" : "smooth", block: "nearest" });
    const cronometro = setTimeout(() => setIdWidgetNuevo(null), 1600);
    return () => clearTimeout(cronometro);
  }, [idWidgetNuevo, reducirMovimiento]);

  // El nodo real del grid, en un ref mutable -- lo
  // necesita `generarReportePdf` para capturarlo con html2canvas. Tiene que
  // ser un ref y no un valor cerrado sobre el render en el que se creo el
  // closure de esa funcion: mientras "todos los paneles" recorre tableros
  // via `setActiveId`, el grid se desmonta/remonta con cada carga
  // (`{!loadingWidgets && (...)}` en el render), y solo un ref mutable sigue
  // reflejando el nodo ACTUAL en cada vuelta del bucle.
  const widgetGridNodeRef = useRef(null);
  // Recuadros punteados "Agregar gráfico" que completan la cuadricula (ver useRellenoDelGrid).
  const [rellenoCount, rellenoRef] = useRellenoDelGrid(
    widgets.length,
    widgets.filter((w) => columnasDeWidget(w) === 2).length,
  );
  const widgetGridRef = useCallback((nodo) => {
    widgetGridNodeRef.current = nodo;
    rellenoRef(nodo);
  }, [rellenoRef]);

  // Filtro que una tarjeta le pone a otra: un clic en la barra de un responsable en "Incidencias
  // abiertas por responsable" filtra la tabla de material prestado. Vive aqui (no en cada tarjeta)
  // porque las dos tarjetas son hermanas; se limpia al cambiar de tablero.
  const [filtroResponsable, setFiltroResponsable] = useState(null);
  const quitarFiltroResponsable = useCallback(() => setFiltroResponsable(null), []);
  useEffect(() => { setFiltroResponsable(null); }, [activeId]);
  const hayTablaDePrestamos = widgets.some((widget) => widget.tipo_grafica === "tabla");
  const alFiltrarResponsable = useCallback((nuevo) => {
    setFiltroResponsable((actual) => (actual && String(actual.id) === String(nuevo.id) ? null : nuevo));
  }, []);

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

  // Devuelve la lista (ademas de guardarla en `widgets`, como siempre) para
  // que quien la llame directamente -el reporte PDF, ver generarReportePdf-
  // pueda saber de inmediato si este tablero trae algo que capturar, sin
  // depender de esperar a que el estado se refleje en un render.
  //
  // `silencioso`: recarga SIN esconder la cuadricula (sin pasar por "cargando").
  // Es lo que hace falta despues de agregar o reordenar un widget: si el grid se
  // desmontara, todas las tarjetas volverian a pedir sus datos y a animarse
  // desde cero, y la entrada de la nueva se perderia entre las demas.
  const loadWidgets = useCallback(async (dashboardId, { silencioso = false } = {}) => {
    if (!dashboardId) { setWidgets([]); return []; }
    if (!silencioso) setLoadingWidgets(true);
    setWidgetsError("");
    try {
      const data = await getAllKpiDashboardWidget(dashboardId);
      const lista = listOf(data);
      setWidgets(lista);
      return lista;
    } catch (error) {
      setWidgetsError(error.message || "errors.request_failed");
      setWidgets([]);
      return [];
    } finally {
      setLoadingWidgets(false);
    }
  }, []);

  // Sensor con distancia minima antes de armar un drag: sin esto, un simple
  // clic en "Editar"/"Eliminar" dentro de la tarjeta se interpretaria como el
  // inicio de un arrastre (mismo mousedown) y el clic normal dejaria de
  // funcionar.
  const dragSensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  function notifyError(error) {
    window.alert(t(error.message || "errors.request_failed", error.message || "errors.request_failed"));
  }

  // --- Reporte PDF (exportar el dashboard, ver generarReportePdf mas abajo) ---
  const [mostrarDialogoExportarPdf, setMostrarDialogoExportarPdf] = useState(false);
  const [exportandoPdf, setExportandoPdf] = useState(false);
  // Cuenta animada del numero y dibujo de las graficas: apagados si la
  // persona pidio reducir el movimiento, y tambien mientras se captura el
  // reporte PDF (una captura a mitad de animacion saldria con el 0 o con
  // barras a medio crecer).
  const animarWidgets = !reducirMovimiento && !exportandoPdf;
  // IDs de tarjeta (`id_kpi_dashboard_widget`) que ya terminaron de resolver
  // sus propios datos (exito O error, ver el `onReady` en KpiWidgetCard). Un
  // ref y no un estado a proposito: nada en pantalla necesita re-renderizar
  // cuando cambia, solo `esperarWidgetsListos` lo consulta mientras genera el
  // PDF. Los ids son unicos globales (no por tablero), asi que no hace falta
  // limpiarlo entre paneles -- un id de un tablero anterior nunca coincide
  // con uno del tablero que se esta esperando ahora.
  const widgetsListosRef = useRef(new Set());
  const handleWidgetReady = useCallback((idWidget) => { widgetsListosRef.current.add(idWidget); }, []);

  // Oculta los espacios "de fabrica" y los iconos de editar/eliminar/
  // arrastrar de cada tarjeta MIENTRAS se captura para el PDF -- un reporte
  // no deberia verse como una foto de la pantalla de administracion (ver
  // kpi-pdf-exporting en kpi-dashboard.css).
  useEffect(() => {
    document.body.classList.toggle("kpi-pdf-exporting", exportandoPdf);
    return () => document.body.classList.remove("kpi-pdf-exporting");
  }, [exportandoPdf]);

  async function esperarWidgetsListos(idsEsperados) {
    if (idsEsperados.length === 0) return;
    const limite = Date.now() + 20000;
    while (Date.now() < limite) {
      if (idsEsperados.every((id) => widgetsListosRef.current.has(id))) return;
      await esperar(120);
    }
    // Se agota el tiempo de espera (20s) y se sigue de todas formas -- mejor
    // un reporte con alguna tarjeta a medio cargar que dejar la generacion
    // colgada para siempre por una sola peticion lenta.
  }

  // Genera el PDF del dashboard completo, capturando lo que YA esta pintado
  // en pantalla (mismos SVG de Recharts, mismos colores) en vez de rearmar
  // los graficos del lado del servidor -- ver la nota junto a
  // `documents-reports/` sobre por que ese generador no sirve aqui (Jinja2 +
  // WeasyPrint no ejecuta React). `modo` es "actual" (solo el tablero que
  // esta viendo el usuario) o "todos" (uno por tablero, cada uno en su
  // propia seccion/salto de pagina, ver agregarSeccionAlPdf). Para "todos"
  // hace falta ir cambiando `activeId` tablero por tablero -reusando el
  // mismo camino real de carga y el mismo grid que ya se ve en pantalla, en
  // vez de duplicar la logica en un arbol oculto- por eso la pantalla
  // "parpadea" entre pestañas mientras genera: el overlay de abajo lo tapa a
  // proposito.
  async function generarReportePdf(modo) {
    setMostrarDialogoExportarPdf(false);
    setExportandoPdf(true);
    const idActivoOriginal = activeId;
    try {
      const objetivos = modo === "todos" ? dashboards : dashboards.filter((d) => d.id_kpi_dashboard === activeId);
      if (objetivos.length === 0) return;

      const pdf = new jsPDF({ orientation: "landscape", unit: "pt", format: "a4" });
      const margin = 24;
      const estadoPagina = { vacia: true };
      let huboContenido = false;

      // Un tablero por vuelta, nunca en paralelo -- cada uno depende del
      // anterior (mismo grid real reutilizado via `setActiveId`, no arboles
      // ocultos), asi que un `await` dentro de este `for` es intencional.
      for (const dashboard of objetivos) {
        setActiveId(dashboard.id_kpi_dashboard);
        const listaWidgets = await loadWidgets(dashboard.id_kpi_dashboard);
        // Panel sin graficos: se omite entero, sin pagina ni titulo vacio.
        if (!listaWidgets || listaWidgets.length === 0) continue;

        await esperarWidgetsListos(listaWidgets.map((w) => w.id_kpi_dashboard_widget));
        // Un respiro extra despues de "listo": Recharts todavia necesita un
        // par de frames para terminar de pintar el SVG tras el ultimo cambio
        // de datos, y `onReady` solo avisa que la peticion ya resolvio.
        await esperar(300);

        const nodoGrid = widgetGridNodeRef.current;
        if (!nodoGrid) continue;
        // Medir las filas ANTES de capturar (misma escala que `scale` de
        // html2canvas, ver medirFilasDeTarjetas) -- el DOM en vivo es lo
        // unico que sabe donde termina cada tarjeta, un canvas ya es solo
        // pixeles.
        const filas = medirFilasDeTarjetas(nodoGrid, ESCALA_CAPTURA_PDF);
        if (filas.length === 0) continue;
        const canvas = await html2canvas(nodoGrid, {
          scale: ESCALA_CAPTURA_PDF,
          backgroundColor: "#ffffff",
          // html2canvas no entiende color()/color-mix()/oklch() (ver kpi/colorParaPdf.js).
          onclone: (_doc, clon) => resolverColoresModernosParaPdf(clon),
        });
        agregarSeccionAlPdf({ pdf, canvas, filas, margin, tituloSeccion: dashboard.nombre, estadoPagina });
        huboContenido = true;
      }

      if (!huboContenido) {
        window.alert(tx("pdf_report_empty", "Ninguno de los paneles tiene gráficos para incluir en el reporte."));
        return;
      }
      pdf.save(`reporte-kpis-${todayIso()}.pdf`);
    } catch (error) {
      notifyError(error);
    } finally {
      setActiveId(idActivoOriginal);
      await loadWidgets(idActivoOriginal);
      setExportandoPdf(false);
    }
  }

  // Arrastrar para reordenar: el grid sigue siendo responsive (auto-fill de
  // kpi-widget-grid, ver kpi-dashboard.css) -- dnd-kit con rectSortingStrategy
  // ya sabe acomodar el resto de tarjetas alrededor del hueco, no hace falta
  // una cuadricula de posiciones fijas. Optimista en la UI (reordena de
  // inmediato) y persiste `posicion_orden` -campo que ya existia en el
  // backend, ver KpiDashboardWidget.posicion_orden- con el mismo criterio de
  // espaciado (100, 200, 300...) que ya usa `_reemplazar_kpis` para el orden
  // de KPIs dentro de un widget.
  async function guardarOrdenWidgets(idsEnOrden) {
    const porId = new Map(widgets.map((item) => [String(item.id_kpi_dashboard_widget), item]));
    const reordenados = idsEnOrden.map((id) => porId.get(String(id))).filter(Boolean);
    if (reordenados.length !== widgets.length) return;
    setWidgets(reordenados);
    try {
      await Promise.all(
        reordenados.map((widget, index) => updateKpiDashboardWidget(
          widget.id_kpi_dashboard_widget,
          { posicion_orden: (index + 1) * 100 },
        )),
      );
    } catch (error) {
      // Si algo fallo a medio camino, el orden en el servidor puede haber
      // quedado a medias -- se recarga desde ahi para no dejar la UI
      // mostrando un orden que no coincide con lo guardado.
      setWidgetsError(error.message || "errors.request_failed");
      await loadWidgets(activeId, { silencioso: true });
    }
  }

  // Reordenar arrastrando: durante el arrastre las demas tarjetas se corren y la arrastrada deja un
  // hueco de su tamano donde caeria; al soltar se guarda ESE orden. Ver useReordenarTarjetas.js.
  const reorden = useReordenarTarjetas({
    widgets, guardarOrden: guardarOrdenWidgets, gridNodeRef: widgetGridNodeRef, reducirMovimiento,
  });

  useEffect(() => { loadDashboards(); }, [loadDashboards]);
  // Durante la generacion del reporte PDF, `generarReportePdf` ya llama a
  // `loadWidgets` el mismo directo y espera su resultado -- sin este freno
  // este efecto dispararia UNA carga extra (redundante, no incorrecta) cada
  // vez que el reporte cambia de tablero con `setActiveId`.
  useEffect(() => {
    if (exportandoPdf) return;
    loadWidgets(activeId);
  }, [activeId, loadWidgets, exportandoPdf]);

  useEffect(() => {
    let cancelado = false;
    // El catalogo de KPIs y el de dimensiones (persona/catalogo/categoria/global) se piden juntos:
    // a cada KPI se le agrega el tipo de su dimension. Sin el catalogo de dimensiones (backend
    // viejo) el Dashboard se comporta como siempre.
    Promise.all([getAllKpiDefinition(), getKpiDimensions().catch(() => [])])
      .then(([definiciones, dimensiones]) => {
        if (cancelado) return;
        setKpiCatalog(enriquecerCatalogo(listOf(definiciones), listOf(dimensiones)));
      })
      .catch(() => { if (!cancelado) setKpiCatalog([]); });
    // Solo id+nombre, sin pedir el catalogo de RH completo (`GET /user/` exige permiso de seguridad):
    // sirve al filtro por empleados. Los nombres de las graficas los manda el backend.
    getUserOptions().then((data) => { if (!cancelado) setUsers(listOf(data)); }).catch(() => { if (!cancelado) setUsers([]); });
    getAllDepartment({ per_page: 500 }).then((data) => { if (!cancelado) setDepartments(listOf(data)); }).catch(() => { if (!cancelado) setDepartments([]); });
    return () => { cancelado = true; };
  }, []);

  const userLabel = useCallback((idUser) => {
    const found = users.find((user) => String(user.id_user) === String(idUser));
    return found?.full_name || found?.username || `#${idUser}`;
  }, [users]);

  // Respaldo: el nombre del producto lo manda el backend (`etiquetas`); ya no se carga el catalogo.
  const productLabel = useCallback((idProduct) => `#${idProduct}`, []);

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
    abrirEditor(activeId, estadoDeWidget(widget, kpiCatalog));
  }

  async function handleSaveWidget(payload, editingWidgetId) {
    let creado = null;
    if (editingWidgetId) {
      await updateKpiDashboardWidget(editingWidgetId, payload);
    } else {
      creado = await createKpiDashboardWidget(activeId, payload);
    }
    // "Terminar" vacia el borrador de ESTE tablero, listo para el siguiente;
    // el panel se cierra solo (cerrarAlEnviar de FormularioPlegable) y la
    // tarjeta nueva entra con animacion.
    resetPanelState(activeId);
    await loadWidgets(activeId, { silencioso: true });
    if (creado?.id_kpi_dashboard_widget) setIdWidgetNuevo(creado.id_kpi_dashboard_widget);
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
        <button
          type="button"
          className="button ghost"
          onClick={() => setMostrarDialogoExportarPdf(true)}
          disabled={exportandoPdf || !activeDashboard}
        >
          <FileDown size={16} />{tx("pdf_report_button", "Generar reporte PDF")}
        </button>
        <button className="button ghost" onClick={() => loadDashboards()} disabled={loadingDashboards}>
        <RefreshCw size={16} />{loadingDashboards ? t("common.loading") : t("common.refresh")}
        </button>
      </PageHeader>

      {mostrarDialogoExportarPdf && (
        <div className="kpi-pdf-dialog-backdrop" role="dialog" aria-modal="true">
          <div className="kpi-pdf-dialog">
            <h2>{tx("pdf_report_dialog_title", "Generar reporte PDF")}</h2>
            <p>{tx("pdf_report_dialog_body", "¿Quieres incluir solo el panel que estás viendo o todos los paneles?")}</p>
            <div className="kpi-pdf-dialog-actions">
              <button type="button" className="button" onClick={() => setMostrarDialogoExportarPdf(false)}>
                {t("common.cancel")}
              </button>
              <button type="button" className="button" onClick={() => generarReportePdf("actual")}>
                {tx("pdf_report_current", "Panel actual")}
              </button>
              <button type="button" className="button primary" onClick={() => generarReportePdf("todos")}>
                {tx("pdf_report_all", "Todos los paneles")}
              </button>
            </div>
          </div>
        </div>
      )}

      {exportandoPdf && (
        <div className="kpi-pdf-exporting-overlay">
          <Loader2 size={22} className="kpi-spin" />
          <span>{tx("pdf_report_generating", "Generando reporte PDF…")}</span>
        </div>
      )}

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
          {widgetsError && <div className="alert error">{t(widgetsError, widgetsError)}</div>}
          {loadingWidgets && <div className="alert">{t("common.loading")}</div>}

          {!loadingWidgets && !widgetsError && (
            <DndContext sensors={dragSensors} collisionDetection={sinColision} {...reorden.handlers}>
            <SortableContext items={reorden.idsVista} strategy={sinDesplazarVecinas}>
            <div className={`kpi-widget-grid${reorden.activoId ? " kpi-widget-grid-arrastrando" : ""}`} ref={widgetGridRef}>
              {reorden.widgetsVista.map((widget) => (
                <SortableKpiWidgetCard
                  key={widget.id_kpi_dashboard_widget}
                  widget={widget}
                  kpiCatalog={kpiCatalog}
                  userLabel={userLabel}
                  productLabel={productLabel}
                  formatNumber={formatNumber}
                  onEdit={() => handleEditWidget(widget)}
                  onDelete={() => handleDeleteWidget(widget)}
                  onReady={handleWidgetReady}
                  esNuevo={widget.id_kpi_dashboard_widget === idWidgetNuevo}
                  animar={animarWidgets}
                  reducirMovimiento={reducirMovimiento}
                  esHueco={String(widget.id_kpi_dashboard_widget) === reorden.activoId}
                  filtroResponsable={filtroResponsable}
                  onFiltrarResponsable={hayTablaDePrestamos ? alFiltrarResponsable : undefined}
                  onQuitarFiltroResponsable={quitarFiltroResponsable}
                  t={t}
                  tx={tx}
                />
              ))}
              {/* Recuadros punteados al final: con el tablero vacío llenan lo que alcanza a verse; con
                  tarjetas, completan la última fila. Entran al masonry como tarjetas de una
                  columna, después de todas las reales, así que no las mueven. */}
              {Array.from({ length: rellenoCount }).map((_, index) => (
                <button
                  type="button"
                  key={`kpi-widget-placeholder-${index}`}
                  className="kpi-widget-placeholder"
                  onClick={() => abrirEditor(activeId)}
                  title={tx("add_widget", "Agregar gráfico")}
                  tabIndex={reorden.activoId ? -1 : undefined}
                >
                  <Plus size={22} />
                  <span>{tx("add_widget", "Agregar gráfico")}</span>
                </button>
              ))}
            </div>
            </SortableContext>
            {/* Lo que sigue al puntero: una copia ESTATICA de la tarjeta (su HTML), no otra tarjeta
                viva -- no vuelve a pedir datos ni a montar graficas. La tarjeta real se queda en el
                masonry, escondida, como hueco. */}
            <DragOverlay dropAnimation={reducirMovimiento ? null : { duration: 200, easing: "cubic-bezier(.2,.8,.2,1)" }}>
              {reorden.instantanea && (
                <div
                  className="kpi-widget-superpuesta"
                  style={{ width: reorden.instantanea.ancho }}
                  // eslint-disable-next-line react/no-danger
                  dangerouslySetInnerHTML={{ __html: reorden.instantanea.html }}
                />
              )}
            </DragOverlay>
            </DndContext>
          )}

          {/* Editor de graficos, DEBAJO de la cuadricula: lo que se mira va
              arriba y lo que se arma de vez en cuando, abajo (mismo criterio
              que FormularioPlegable en el resto de las pantallas). `key`
              fuerza una instancia nueva por tablero para que el estado
              efimero de UI (error, saving, aviso) arranque limpio al cambiar
              de tablero -- el borrador real (KPIs, fechas, filtros) vive en
              `panelStateByDashboard` y sobrevive al remount via props. */}
          <div className="kpi-editor-ancla" ref={editorRef}>
            <KpiWidgetPanel
              key={activeId}
              panelState={currentPanelState}
              onChangePanelState={(patch) => updatePanelState(activeId, patch)}
              kpiCatalog={kpiCatalog}
              users={users}
              departments={departments}
              userLabel={userLabel}
              productLabel={productLabel}
              formatNumber={formatNumber}
              onCancel={() => resetPanelState(activeId)}
              onAbierto={() => setPedidoScrollEditor((n) => n + 1)}
              onSave={(payload) => handleSaveWidget(payload, currentPanelState.editingWidgetId)}
              t={t}
              tx={tx}
            />
          </div>
        </div>
      )}

    </section>
  );
}

// Envoltura sortable: separa el "como se arrastra" (dnd-kit) de "que se
// muestra" (KpiWidgetCard). El handle (GripVertical) es la UNICA zona con los
// listeners de arrastre -- si se le pusieran a la tarjeta entera, un clic en
// "Editar"/"Eliminar" competiria con el inicio de un drag.
function SortableKpiWidgetCard({ reducirMovimiento, esHueco, ...props }) {
  const { widget } = props;
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: widget.id_kpi_dashboard_widget,
  });
  const style = {
    // La que se arrastra no se mueve: su copia (DragOverlay) sigue al puntero y ella es el hueco.
    transform: esHueco ? undefined : DndCss.Transform.toString(transform),
    // La transicion de dnd-kit es la que acomoda con animacion suave al
    // resto de las tarjetas cuando una se suelta -- se conserva SIEMPRE,
    // incluso mientras se arrastra la propia (isDragging), para que las
    // demas nunca salten de golpe a su nuevo lugar.
    // Con reduced-motion las demas tarjetas ocupan su nuevo lugar de golpe.
    transition: reducirMovimiento ? undefined : transition,
    zIndex: isDragging ? 1 : "auto",
  };
  const masonryRef = useMasonryRef();
  const asignarRef = useCallback((nodo) => { setNodeRef(nodo); masonryRef(nodo); }, [setNodeRef, masonryRef]);
  return (
    <div
      ref={asignarRef}
      style={style}
      className={[
        esHueco && "kpi-widget-hueco",
        columnasDeWidget(widget) === 2 && "kpi-widget-doble",
        filasDeWidget(widget) === 2 && "kpi-widget-filas-2",
      ].filter(Boolean).join(" ")}
      data-widget-id={widget.id_kpi_dashboard_widget}
    >
      <KpiWidgetCard {...props} dragHandleProps={{ ...attributes, ...listeners }} isDragging={isDragging} />
    </div>
  );
}

// Carga los datos de un widget (guardado, o el borrador de la vista previa del
// editor): una llamada a /kpi_snapshot/query POR CADA KPI -el backend solo
// acepta un `id_kpi_definition` a la vez, la combinacion pasa aqui-, o el
// endpoint "vivo" si es una tabla de un KPI en modo "vivo".
//
// `onReady(id)` avisa cuando la tarjeta ya no va a cambiar (exito O error): el
// reporte PDF (ver esperarWidgetsListos en Dashboard()) necesita saber cuando
// puede capturarla, sin importar si el resultado fue un dato real o un mensaje
// de error ya asentado en pantalla.
// Una sola lista vacia, para que el modo servidor de la tabla no reciba un arreglo nuevo en cada render.
const SIN_RENGLONES = [];

// Cuanto se espera, despues del ultimo clic en una flecha de orden, antes de guardarlo: invertir el sentido dos
// veces seguidas es una sola peticion.
const RETRASO_GUARDAR_ORDEN_MS = 600;

// Guarda el orden elegido en la tabla (`parametros.orden_tabla` del widget). Sin permiso de actualizar el
// widget (403), con la red caida o con cualquier otro error, el orden se queda solo en la pantalla y no se
// avisa: elegir como ver la tabla nunca debe sentirse como un fallo. Lo pendiente se manda al desmontar.
function useGuardarOrdenTabla(idWidget) {
  const pendiente = useRef(null);
  const temporizador = useRef(null);
  const enviar = useCallback(() => {
    clearTimeout(temporizador.current);
    temporizador.current = null;
    const orden = pendiente.current;
    if (!orden || !idWidget) return;
    pendiente.current = null;
    saveKpiWidgetOrdenTabla(idWidget, orden).catch(() => {});
  }, [idWidget]);
  const guardar = useCallback((orden) => {
    pendiente.current = orden;
    clearTimeout(temporizador.current);
    temporizador.current = setTimeout(enviar, RETRASO_GUARDAR_ORDEN_MS);
  }, [enviar]);
  useEffect(() => () => enviar(), [enviar]);
  return guardar;
}

function useDatosDeWidget({ widget, kpiCatalog, onReady }) {
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
  // Fechas al dia de hoy: un widget con `rango_relativo` las recalcula cada
  // vez que se mira; uno sin el (todos los de antes) sale tal cual se guardo.
  const parametros = parametrosEfectivos(widget.parametros);
  const fechaInicio = parametros.fecha_inicio;
  const fechaFin = parametros.fecha_fin;
  const fechaInicioB = parametros.fecha_inicio_b;
  const fechaFinB = parametros.fecha_fin_b;
  const empleadosKey = Array.isArray(parametros.empleados) ? parametros.empleados.join(",") : "";
  const departamentosKey = Array.isArray(parametros.id_departments) ? parametros.id_departments.join(",") : "";
  const agruparPor = parametros.agrupar_por === "periodo" ? "periodo" : "entidad";
  // Un widget "tabla" solo tiene sentido con un unico KPI "vivo" (hoy,
  // material_prestado_actual) -- ver KpiWidgetPanel, que ya restringe la
  // seleccion a eso para este tipo de grafica. Cualquier otra combinacion
  // (un tabla guardado antes del rediseno, o apuntando a un KPI que no es
  // vivo) cae en el estado "proximamente", nunca en un renderer generico que
  // no existe todavia.
  const esTabla = widget.tipo_grafica === "tabla";
  const esTablaVivo = esTabla && kpiInfos.length === 1 && kpiInfos[0]?.modo === "vivo";
  const idWidget = widget.id_kpi_dashboard_widget;

  // KPI "vivo" (ver material_prestado_actual): su tabla pide sus propios datos al servidor, por paginas y con
  // el filtro, la busqueda y el orden aplicados alla (ver TablaWidget, modo servidor). Aqui solo se le da la
  // llamada y el aviso de "ya cargue" para el reporte PDF.
  const idVivo = esTablaVivo ? idsUsados[0] : null;
  const cargarVivo = useMemo(
    () => (idVivo ? (parametros) => queryKpiVivo(idVivo, parametros) : null),
    [idVivo],
  );
  const onListoVivo = useCallback(() => onReady?.(idWidget), [onReady, idWidget]);
  const guardarOrdenTabla = useGuardarOrdenTabla(esTablaVivo ? idWidget : null);
  useEffect(() => {
    if (esTablaVivo) { setLoading(false); setError(""); }
  }, [esTablaVivo]);

  useEffect(() => {
    let cancelado = false;
    async function cargar() {
      // El KPI "vivo" ya tiene su propio efecto (arriba) -- este solo
      // atiende a los widgets de kpi_snapshot de siempre.
      if (esTablaVivo) return;
      if (esTabla) {
        setLoading(false);
        setSnapshots([]);
        setError(idsUsados.length === 0 ? "missing_kpi" : "tabla_no_soportada");
        onReady?.(idWidget);
        return;
      }
      if (idsUsados.length === 0) {
        setLoading(false);
        setSnapshots([]);
        setError("missing_kpi");
        onReady?.(idWidget);
        return;
      }
      if (!fechaInicio || !fechaFin) {
        setLoading(false);
        setSnapshots([]);
        setError("missing_range");
        onReady?.(idWidget);
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
        const resultados = await Promise.all(
          idsUsados.map((id) => queryKpiSnapshot({ ...paramsComunes, id_kpi_definition: id })),
        );
        if (!cancelado) setSnapshots(resultados);
      } catch (err) {
        if (!cancelado) { setError(err.message || "errors.request_failed"); setSnapshots([]); }
      } finally {
        // Se avisa "listo" tanto en exito como en error (ver el comentario de
        // arriba sobre `onReady`).
        if (!cancelado) { setLoading(false); onReady?.(idWidget); }
      }
    }
    cargar();
    return () => { cancelado = true; };
  // `idsKey` es el proxy estable de `idsUsados` (un array nuevo cada
  // render); `idsUsados` en si mismo nunca deberia ir en las dependencias.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idsKey, esTabla, esTablaVivo, fechaInicio, fechaFin, fechaInicioB, fechaFinB, empleadosKey, departamentosKey, agruparPor]);

  return { snapshots, loading, error, vivoItems: SIN_RENGLONES, vivoTotal: 0, cargarVivo, onListoVivo, guardarOrdenTabla, kpiInfos, idsUsados, esTablaVivo };
}

// El mismo valor, pero solo despues de `ms` sin cambios -- para no pedirle datos
// al servidor con cada tecla mientras se arma un rango de fechas. Compara por
// contenido (JSON), no por identidad: el borrador es un objeto nuevo en cada
// render y reiniciaria el temporizador para siempre.
function useValorRetrasado(valor, ms) {
  const clave = JSON.stringify(valor);
  const [retrasado, setRetrasado] = useState(valor);
  useEffect(() => {
    const cronometro = setTimeout(() => setRetrasado(JSON.parse(clave)), ms);
    return () => clearTimeout(cronometro);
  }, [clave, ms]);
  return retrasado;
}

// Que skeleton corresponde a cada tipo de grafica mientras cargan los datos.
const SKELETON_POR_TIPO = { numero: "numero", dona: "dona", tabla: "tabla" };

// El cuerpo de un widget en cualquiera de sus estados (cargando, sin KPI, sin
// rango, error, vacio, datos): lo comparten la tarjeta del tablero y la vista
// previa del editor, para que lo que se ve al armar sea lo que queda.
// Se exportan solo para la prueba de render (kpi/renderTarjetas.test.mjs).
// eslint-disable-next-line react-refresh/only-export-components
export function CuerpoDeWidget({
  widget, datos, userLabel, productLabel, formatNumber, t, tx, animar, filtroResponsable, onFiltrarResponsable, onQuitarFiltroResponsable,
}) {
  const { snapshots, loading, error, vivoItems, vivoTotal, cargarVivo, onListoVivo, guardarOrdenTabla, kpiInfos, esTablaVivo } = datos;
  const ERRORES_CON_TEXTO_PROPIO = ["missing_range", "missing_kpi", "errors.rango_excede_limite", "tabla_no_soportada"];
  return (
    <>
      {loading && <Skeleton tipo={SKELETON_POR_TIPO[widget.tipo_grafica] || "grafica"} />}
      {!loading && error === "missing_range" && (
        <p className="kpi-empty-inline">{tx("widget_missing_range", "A este gráfico le falta un rango de fechas. Edítalo para configurarlo.")}</p>
      )}
      {!loading && error === "missing_kpi" && (
        <p className="kpi-empty-inline">{tx("widget_missing_kpi", "A este gráfico le falta un KPI. Edítalo para configurarlo.")}</p>
      )}
      {!loading && error === "errors.rango_excede_limite" && (
        <p className="kpi-error-inline">{tx("range_exceeds_limit", "El rango de fechas de este gráfico excede el máximo permitido (aprox. un año). Edítalo para acortarlo.")}</p>
      )}
      {!loading && error === "tabla_no_soportada" && (
        <p className="kpi-empty-inline">{tx("widget_table_coming_soon", "Este tipo de tabla estará disponible próximamente.")}</p>
      )}
      {!loading && error && !ERRORES_CON_TEXTO_PROPIO.includes(error) && (
        <p className="kpi-error-inline">{t(error, error)}</p>
      )}
      {!loading && !error && esTablaVivo && (
        <KpiTablaVivo items={vivoItems} total={vivoTotal} cargar={cargarVivo} onListo={onListoVivo} tx={tx} filtroExterno={filtroResponsable} onQuitarFiltroExterno={onQuitarFiltroResponsable} ordenInicial={widget.parametros?.orden_tabla} onOrdenChange={guardarOrdenTabla} />
      )}
      {!loading && !error && !esTablaVivo && snapshots.length > 0 && (
        <KpiChartBody
          widget={widget}
          snapshots={snapshots}
          kpiInfos={kpiInfos}
          userLabel={userLabel}
          productLabel={productLabel}
          formatNumber={formatNumber}
          tx={tx}
          animar={animar}
          filtroResponsable={filtroResponsable}
          onFiltrarResponsable={onFiltrarResponsable}
        />
      )}
    </>
  );
}

// Vista previa del editor: consulta EXACTAMENTE lo que se va a guardar (el
// borrador pasa por armarParametros, igual que al guardar) y lo pinta con el
// mismo cuerpo que la tarjeta del tablero. Skeleton mientras espera -tanto la
// pausa de tecleo como la respuesta del servidor-.
function VistaPreviaEditor({ widget, kpiCatalog, userLabel, productLabel, formatNumber, t, tx, textosEjemplo }) {
  const widgetRetrasado = useValorRetrasado(widget, 400);
  const datos = useDatosDeWidget({ widget: widgetRetrasado, kpiCatalog });
  const pendiente = JSON.stringify(widget) !== JSON.stringify(widgetRetrasado);
  // "Sin datos": deteccion perezosa. Si la consulta REAL del rango vuelve vacia, se ofrece «Ver ejemplo»; el
  // ejemplo es solo de pantalla y no cambia el borrador (que sigue siendo el KPI real).
  const [verEjemplo, setVerEjemplo] = useState(false);
  const claveBorrador = JSON.stringify(widget);
  useEffect(() => { setVerEjemplo(false); }, [claveBorrador]);
  const kpiReal = datos.kpiInfos.length === 1 ? datos.kpiInfos[0] : null;
  const sinDatos = ofreceVerEjemplo({
    kpiReal, esTablaVivo: datos.esTablaVivo, loading: datos.loading, pendiente, error: datos.error, snapshots: datos.snapshots,
  });
  const mostrandoEjemplo = verEjemplo && sinDatos;
  const datosDeVista = mostrandoEjemplo
    ? { ...datos, snapshots: [datosDeEjemplo(kpiReal, { textos: textosEjemplo })] }
    : datos;
  const cuerpo = (
    <CuerpoDeWidget
      widget={widgetRetrasado}
      datos={{ ...datosDeVista, loading: datosDeVista.loading || pendiente }}
      userLabel={userLabel}
      productLabel={productLabel}
      formatNumber={formatNumber}
      t={t}
      tx={tx}
      animar={false}
    />
  );
  return (
    <div className="kpi-editor-vista-previa-cuerpo">
      {mostrandoEjemplo ? <MarcoDeEjemplo tx={tx} motivo={MOTIVO_SIN_DATOS}>{cuerpo}</MarcoDeEjemplo> : cuerpo}
      {sinDatos && (
        <div className="kpi-ejemplo-sin-datos">
          <span className="muted">{tx("example_no_data_hint", "Sin datos en el rango elegido.")}</span>
          <button type="button" className="button ghost" onClick={() => setVerEjemplo((actual) => !actual)}>
            {verEjemplo ? tx("example_hide", "Ocultar ejemplo") : tx("example_view", "Ver ejemplo")}
          </button>
        </div>
      )}
    </div>
  );
}

// Aviso y marca de una vista previa con datos de EJEMPLO: el texto fijo va siempre arriba, el sello "EJEMPLO"
// dentro de la propia grafica (para que una captura de pantalla tampoco se confunda con datos reales). Vive solo
// en el editor, fuera de las tarjetas (`.kpi-widget-card`) que captura el reporte PDF.
// eslint-disable-next-line react-refresh/only-export-components
export function MarcoDeEjemplo({ tx, motivo, children }) {
  const razon = {
    sin_datos: tx("example_reason_sin_datos", "Aún no tiene datos."),
  }[motivo];
  return (
    <div className="kpi-ejemplo-marco" data-ejemplo="true">
      <p className="kpi-ejemplo-aviso" role="status">
        {tx("example_banner", "Vista previa con datos de ejemplo. Así se vería este KPI cuando tenga datos.")}
        {razon && <em>{razon}</em>}
      </p>
      <div className="kpi-ejemplo-grafica" data-marca={tx("example_badge", "EJEMPLO")}>
        <span className="kpi-ejemplo-sello" aria-hidden="true">{tx("example_badge", "EJEMPLO")}</span>
        {children}
      </div>
    </div>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function KpiWidgetCard({
  widget, kpiCatalog, userLabel, productLabel, formatNumber, onEdit, onDelete, onReady, t, tx, dragHandleProps, isDragging, animar, esNuevo,
  filtroResponsable, onFiltrarResponsable, onQuitarFiltroResponsable,
}) {
  const datos = useDatosDeWidget({ widget, kpiCatalog, onReady });
  const { kpiInfos, idsUsados, esTablaVivo } = datos;
  const parametros = parametrosEfectivos(widget.parametros);
  const fechaInicio = parametros.fecha_inicio;
  const fechaFin = parametros.fecha_fin;
  const fechaInicioB = parametros.fecha_inicio_b;
  const fechaFinB = parametros.fecha_fin_b;

  const chartTypeLabel = CHART_TYPES.find((opt) => opt.value === widget.tipo_grafica)?.label || widget.tipo_grafica;
  // "30 días · 2026-08-31 → 2026-09-29": el nombre del rango solo si el widget
  // lo trae; uno de fechas fijas se ve como siempre. Va ANTES de rangoTexto:
  // usarlo antes de declararlo lanzaba ReferenceError y tumbaba la app entera.
  const claveRango = widget.parametros?.rango_relativo;
  const etiquetaRango = RANGOS_RELATIVOS.includes(claveRango)
    ? `${tx(`range_${claveRango}`, ETIQUETA_RANGO_POR_OMISION[claveRango])} · `
    : "";
  const rangoTexto = esTablaVivo
    ? tx("live_data", "En vivo · actualizado ahora")
    : (fechaInicio && fechaFin ? `${etiquetaRango}${fechaInicio} → ${fechaFin}` : tx("missing_range", "Sin rango de fechas configurado"));
  const rangoBTexto = fechaInicioB && fechaFinB ? `${fechaInicioB} → ${fechaFinB}` : "";
  const titulo = kpiInfos.length > 1
    ? kpiInfos.map((info, index) => info?.etiqueta || `KPI #${idsUsados[index]}`).join(" + ")
    : (kpiInfos[0]?.etiqueta || tx("unknown_kpi", `KPI #${idsUsados[0] ?? "?"}`));

  // Acento de la tarjeta: el color del primer KPI (mismo `colorEfectivoDeKpi`
  // de siempre, override manual incluido) en vez de la franja neutra fija --
  // cada tarjeta se identifica a simple vista con el color que ya lleva su
  // KPI en el resto del tablero (leyenda, barras...), no un tono aparte.
  const colorAcento = colorEfectivoDeKpi(idsUsados[0], widget.parametros?.colores_kpi);

  return (
    <article
      className={`kpi-widget-card ${isDragging ? "kpi-widget-dragging" : ""} ${esNuevo ? "kpi-widget-entrada" : ""}`.trim()}
      style={{ "--kpi-acento": colorAcento }}
    >
      <div className="kpi-widget-card-header">
        <div className="kpi-widget-card-titulos">
          <h4>{titulo}</h4>
          <p className="kpi-widget-meta">{tx(`chart_type_${widget.tipo_grafica}`, chartTypeLabel)}</p>
          <p className="kpi-widget-meta">{rangoTexto}</p>
          {rangoBTexto && <p className="kpi-widget-meta">{tx("vs_label", "vs.")} {rangoBTexto}</p>}
        </div>
        <div className="kpi-widget-card-actions">
          <button
            type="button"
            className="kpi-icon-button kpi-drag-handle"
            title={tx("drag_to_reorder", "Arrastrar para reordenar")}
            aria-label={tx("drag_to_reorder", "Arrastrar para reordenar")}
            {...dragHandleProps}
          >
            <GripVertical size={15} />
          </button>
          <button type="button" className="kpi-icon-button" title={t("common.edit")} onClick={onEdit}><Pencil size={15} /></button>
          <button type="button" className="kpi-icon-button danger" title={t("common.delete")} onClick={onDelete}><Trash2 size={15} /></button>
        </div>
      </div>

      <div className="kpi-chart-box">
        <CuerpoDeWidget
          widget={widget}
          datos={datos}
          userLabel={userLabel}
          productLabel={productLabel}
          formatNumber={formatNumber}
          t={t}
          tx={tx}
          animar={animar}
          filtroResponsable={filtroResponsable}
          onFiltrarResponsable={onFiltrarResponsable}
          onQuitarFiltroResponsable={onQuitarFiltroResponsable}
        />
      </div>
    </article>
  );
}

// Mini-tendencia SOLO para el widget "numero" con comparacion activa. El
// snapshot que ya carga KpiWidgetCard no trae la serie diaria para este tipo
// de grafica -- `agrupar_por=periodo` (la unica forma de obtenerla, ver
// `_totales` en `backend/app/routes/kpi.py`) solo se pide cuando el widget usa
// el selector "Agrupar por", que ni siquiera se muestra para tipo "numero".
// Por eso este hook pide SU PROPIO snapshot (mismo endpoint `queryKpiSnapshot`
// de siempre, no uno nuevo) del periodo A unicamente -- la tendencia que
// acompana al valor principal, no la comparacion en si (esa ya la muestra el
// delta de al lado). Devuelve una serie de numeros lista para NumeroWidget, o
// null mientras carga / si no hay al menos 2 puntos que dibujar.
function useTendenciaKpi({ activo, idKpiDefinition, fechaInicio, fechaFin, empleados, idDepartments }) {
  const [serie, setSerie] = useState(null);
  const empleadosKey = Array.isArray(empleados) ? empleados.join(",") : "";
  const idDepartmentsKey = Array.isArray(idDepartments) ? idDepartments.join(",") : "";

  useEffect(() => {
    let cancelado = false;
    if (!activo || !idKpiDefinition || !fechaInicio || !fechaFin) { setSerie(null); return undefined; }
    const params = { id_kpi_definition: idKpiDefinition, fecha_inicio: fechaInicio, fecha_fin: fechaFin, agrupar_por: "periodo" };
    if (empleadosKey) params.empleados = empleadosKey;
    if (idDepartmentsKey) params.id_departments = idDepartmentsKey;
    queryKpiSnapshot(params)
      .then((resultado) => { if (!cancelado) setSerie(tendenciaDeSnapshot(resultado)); })
      .catch(() => { if (!cancelado) setSerie([]); });
    return () => { cancelado = true; };
  }, [activo, idKpiDefinition, fechaInicio, fechaFin, empleadosKey, idDepartmentsKey]);

  return serie && serie.length >= 2 ? serie : null;
}

// Widget "numero" de un solo KPI: el valor con su unidad, la insignia del
// modulo, el delta contra el periodo de comparacion y, a la derecha, la
// mini-tendencia -- o, sin comparacion, el rango que se esta viendo (nunca se
// deja la mitad de la tarjeta en blanco).
function KpiNumero({ widget, snapshot, kpiInfo, formatNumber, tx, animar }) {
  const parametros = parametrosEfectivos(widget.parametros);
  const hayComparacion = Boolean(snapshot?.rango_b);
  const tendencia = useTendenciaKpi({
    activo: hayComparacion,
    idKpiDefinition: kpiInfo?.id_kpi_definition,
    fechaInicio: parametros.fecha_inicio,
    fechaFin: parametros.fecha_fin,
    empleados: parametros.empleados,
    idDepartments: parametros.id_departments,
  });
  const props = propsNumero({
    snapshot,
    kpiInfo,
    formatNumber,
    textos: {
      vsAnterior: tx("vs_compare", "vs. periodo anterior"),
      sinComparacion: tx("no_compare_hint", "Activa \"Comparar\" para ver la variación"),
    },
  });
  const Componente = TIPO_GRAFICA_COMPONENTE.numero;
  return (
    <Componente
      {...props}
      animar={animar}
      icono={kpiModuleMeta(kpiInfo?.modulo).icon}
      colorAcento={colorEfectivoDeKpi(kpiInfo?.id_kpi_definition, parametros.colores_kpi)}
      tendencia={tendencia}
      pistaRango={hayComparacion ? null : `${parametros.fecha_inicio} → ${parametros.fecha_fin}`}
    />
  );
}

// El unico KPI "vivo" que hoy existe (material_prestado_actual): una lista
// paginada de renglones de vale sin devolver, no una serie por fecha -- por
// eso no pasa por `KpiChartBody` (que solo sabe leer snapshots).
// `cargar` (modo servidor): la tabla pide sus renglones por paginas, ya filtrados, buscados y ordenados por el
// backend. Sin `cargar` (las pruebas de render, que le pasan renglones ya cargados) pinta `items` en modo local.
function KpiTablaVivo({ items, total, cargar, onListo, tx, filtroExterno, onQuitarFiltroExterno, ordenInicial, onOrdenChange }) {
  const Componente = TIPO_GRAFICA_COMPONENTE.tabla;
  const sinAsignar = tx("unknown_user", "Sin asignar");
  return (
    <Componente
      servidor={cargar ? { cargar, onListo, sinAsignar } : null}
      ordenInicial={ordenInicial}
      onOrdenChange={onOrdenChange}
      filas={cargar ? SIN_RENGLONES : filasTablaPrestamo(items, sinAsignar)}
      total={total}
      filtroExterno={filtroExterno}
      onQuitarFiltroExterno={onQuitarFiltroExterno}
      etiquetas={{
        articulo: tx("loan_item", "Artículo"),
        responsable: tx("loan_holder", "Responsable"),
        fecha_prestamo: tx("loan_date", "Fecha del vale"),
        dias_prestado: tx("loan_days", "Días prestado"),
        vale_del: tx("loan_voucher_of", "vale del"),
        vacio_titulo: tx("loan_empty_title", "Todo el material está en el almacén"),
        vacio: tx("widget_no_loans", "No hay artículos prestados sin devolver en este momento."),
        sin_resultados: tx("loan_no_results", "Ningún renglón de {responsable}."),
        quitar_filtro: tx("loan_clear_filter", "Ver todos los responsables"),
        ordenar: tx("loan_sort_by", "Ordenar por"),
        clic_invertir: tx("loan_sort_click_reverse", "clic para invertir"),
        ordenar_columna: tx("loan_sort_column", "Ordenar por {columna}"),
        orden_dias_prestado_desc: tx("loan_sort_days_desc", "Más días primero"),
        orden_dias_prestado_asc: tx("loan_sort_days_asc", "Menos días primero"),
        orden_fecha_prestamo_desc: tx("loan_sort_date_desc", "Vale más reciente primero"),
        orden_fecha_prestamo_asc: tx("loan_sort_date_asc", "Vale más antiguo primero"),
        orden_articulo_asc: tx("loan_sort_item_asc", "Artículo A–Z"),
        orden_articulo_desc: tx("loan_sort_item_desc", "Artículo Z–A"),
        orden_responsable_asc: tx("loan_sort_holder_asc", "Responsable A–Z"),
        orden_responsable_desc: tx("loan_sort_holder_desc", "Responsable Z–A"),
        filtro_responsable: tx("loan_filter_holder", "Responsable"),
        todos_los_responsables: tx("loan_all_holders", "Todos los responsables"),
        vista_lista: tx("loan_view_list", "Lista"),
        vista_agrupada: tx("loan_view_grouped", "Por responsable"),
        vistas: tx("loan_views", "Vista"),
        ver_todos: tx("loan_see_all", "Ver todos ({n})"),
        cerrar: tx("close", "Cerrar"),
        panel_titulo: tx("loan_panel_title", "Material prestado ahora"),
        buscar: tx("loan_search", "Buscar"),
        buscar_pista: tx("loan_search_hint", "Artículo, responsable, fecha…"),
        sin_coincidencias: tx("loan_no_matches", "Ningún renglón coincide con la búsqueda."),
        limpiar_busqueda: tx("loan_clear_search", "Limpiar la búsqueda"),
        filtrando: tx("loan_filtering", "Filtrando"),
        quitar_filtro_externo: tx("loan_remove_filter", "Quitar el filtro"),
        sin_prestamos_de: tx("loan_none_of", "{responsable} no tiene material prestado."),
        mostrando: tx("loan_showing", "Mostrando"),
        de: tx("loan_of", "de"),
        renglon: tx("loan_row", "renglón"),
        renglones: tx("loan_rows", "renglones"),
        cargando: tx("loan_loading", "Cargando…"),
        cargando_mas: tx("loan_loading_more", "Cargando más…"),
        mostrar_mas: tx("loan_show_more", "Mostrar más"),
        error_carga: tx("loan_load_error", "No se pudo cargar la lista."),
        responsable_uno: tx("loan_holder_one", "responsable"),
        responsables: tx("loan_holders", "responsables"),
        mas_antiguo: tx("loan_oldest", "el más antiguo"),
        nivel_ok: tx("loan_level_ok", "Reciente"),
        nivel_atencion: tx("loan_level_attention", "Requiere atención"),
        nivel_critico: tx("loan_level_critical", "Atrasado"),
        grupo_renglones: tx("loan_group_rows", "{n} renglones"),
      }}
    />
  );
}

// El mapa `tipo_grafica -> componente` vive en
// components/kpi-widgets/tipoGraficaComponentes.js; aqui solo se arman las
// props de cada uno (ver kpi/kpiAdaptadores.js).
function KpiChartBody({ widget, snapshots, kpiInfos, userLabel, productLabel, formatNumber, tx, animar, filtroResponsable, onFiltrarResponsable }) {
  const snapshot = snapshots[0];
  const kpiInfo = kpiInfos[0];
  const parametros = widget.parametros || {};
  const agruparPorPeriodo = parametros.agrupar_por === "periodo";
  const labelForId = agruparPorPeriodo
    ? (id) => id
    : labelForDimension(kpiInfo?.dimensiones?.[0], userLabel, productLabel, etiquetasDeSnapshots(snapshots));
  const Componente = TIPO_GRAFICA_COMPONENTE[widget.tipo_grafica];
  const sinDatos = <p className="kpi-empty-inline">{tx("no_data", "Sin datos en el rango seleccionado.")}</p>;
  if (!Componente) return null;

  // Umbral manual de "artículos bajo stock" (decision de Aurora: se captura
  // en el widget, no en una columna nueva de base de datos -- ver
  // `articulos_bajo_stock_query` en el backend). Solo tiene sentido con un
  // unico KPI seleccionado y ese KPI siendo justo este.
  const umbralBajoStock = Number(parametros.umbral_bajo_stock);
  const esBajoStock = kpiInfos.length <= 1 && kpiInfo?.clave === "articulos_bajo_stock" && Number.isFinite(umbralBajoStock);

  if (widget.tipo_grafica === "numero") {
    if (esBajoStock) {
      return (
        <Componente
          {...propsNumeroBajoStock({
            snapshot,
            umbralBajoStock,
            textos: { bajoStock: (umbral) => tx("bajo_stock_note", `producto(s) por debajo de ${umbral}`) },
          })}
          animar={animar}
        />
      );
    }
    return <KpiNumero widget={widget} snapshot={snapshot} kpiInfo={kpiInfo} formatNumber={formatNumber} tx={tx} animar={animar} />;
  }

  if (widget.tipo_grafica === "dona") {
    const props = propsDona({
      snapshot, kpiInfo, labelForId, agruparPorPeriodo, formatNumber, textos: { otros: tx("others", "Otros") },
    });
    if (!props.datos.length) return sinDatos;
    return <Componente {...props} animar={animar} />;
  }

  const props = propsSeries({
    tipo: widget.tipo_grafica,
    snapshots,
    kpiInfos,
    labelForId,
    empleados: parametros.empleados,
    agruparPorPeriodo,
    coloresOverride: parametros.colores_kpi,
    umbralBajoStock,
    esBajoStock,
    formatNumber,
    textos: {
      rangoA: tx("range_a", "Periodo A"),
      rangoB: tx("range_b", "Periodo B"),
      comparacionCorta: tx("vs_compare_short", "comparación"),
    },
  });
  if (!props.datos.length) return sinDatos;
  // Clic en la barra de un responsable: filtra la tabla de material prestado (ver
  // `filtroResponsable` en Dashboard()). Solo "Incidencias abiertas por responsable", en barras.
  const filtraLaTabla = Boolean(onFiltrarResponsable)
    && widget.tipo_grafica === "barras" && kpiInfos.length === 1 && !agruparPorPeriodo
    && kpiInfo?.clave === "incidencias_abiertas_por_empleado";
  const interaccion = filtraLaTabla
    ? {
      onBarClick: (entrada) => {
        const fila = entrada?.payload || entrada;
        if (fila?.id !== undefined) onFiltrarResponsable({ id: fila.id, nombre: fila.name });
      },
      barraResaltada: filtroResponsable?.nombre || null,
    }
    : {};
  return <Componente {...props} {...interaccion} tipo={widget.tipo_grafica} animar={animar} />;
}

function tiposDeGraficaPermitidos(kpiInfos) {
  return tiposPermitidosPorKpi(kpiInfos, CHART_TYPES.map((opt) => opt.value));
}

function KpiWidgetPanel({ panelState, onChangePanelState, kpiCatalog, users, departments, userLabel, productLabel, formatNumber, onCancel, onSave, onAbierto, t, tx }) {
  const {
    editingWidgetId,
    colapsado,
    paso,
    idsKpiSeleccionados,
    tipoGrafica,
    rangoRelativo,
    fechaInicio,
    fechaFin,
    comparar,
    fechaInicioB,
    fechaFinB,
    empleadosSeleccionados,
    departamentosSeleccionados,
    coloresKpi,
    desfaseComparacion,
    agruparPor,
    umbralBajoStock,
  } = panelState;

  // Efimero de UI, no borrador: se reinicia limpio en cada tablero porque
  // Dashboard() monta una instancia nueva de este componente por
  // `id_kpi_dashboard` (`key={activeId}`) -- ver PANEL "AGREGAR GRAFICO"
  // ESTATICO POR DASHBOARD en Dashboard().
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [avisoKpi, setAvisoKpi] = useState("");
  const multiKpiPermitido = esTipoMultiKpi(tipoGrafica);
  // Palabras genericas de los datos de ejemplo, traducidas ("Ejemplo 1", "Categoría 1"...).
  const textosEjemplo = useMemo(() => ({
    entidad: tx("example_entity", "Ejemplo"),
    categoria: tx("example_category", "Categoría"),
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [tx]);

  // Info de los KPIs ya elegidos -- de aqui salen la etiqueta del toggle
  // "Agrupar por" (Empleado/Producto, segun la dimension real del primer KPI
  // elegido) y si hay que mostrar el campo de umbral de "artículos bajo
  // stock" (solo cuando ese KPI especifico esta seleccionado).
  const kpisSeleccionadosInfo = idsKpiSeleccionados
    .map((id) => kpiCatalog.find((kpi) => String(kpi.id_kpi_definition) === id))
    .filter(Boolean);
  const primeraDimension = kpisSeleccionadosInfo[0]?.dimensiones?.[0];
  // El filtro por empleados/departamentos solo aplica a KPIs que desglosan por persona (ids de usuario).
  const mostrarFiltroDePersonas = muestraFiltroDePersonas(kpisSeleccionadosInfo);
  // Lo que se desglosa, con el nombre que le da cada KPI ("Responsable", "Tecnico"...).
  // Las dos etiquetas de siempre conservan su traduccion.
  const etiquetaDeAgrupar = etiquetasDeDimension(kpisSeleccionadosInfo)
    .map((etiqueta) => (etiqueta === "Empleado" ? tx("group_by_employee", etiqueta) : etiqueta === "Producto" ? tx("group_by_product", etiqueta) : etiqueta))
    .join(" / ");
  const tieneBajoStockSeleccionado = kpisSeleccionadosInfo.some((kpi) => kpi.clave === "articulos_bajo_stock");

  // Que tipos de grafica admite lo elegido: la interseccion de las
  // `graficas_permitidas` de cada KPI (las declara el registry del backend).
  // Sin KPI elegido todos menos "tabla", que solo existe para KPIs "vivos".
  // Un KPI sin lista (fila huerfana) no restringe nada.
  const tiposPermitidos = useMemo(
    () => tiposDeGraficaPermitidos(kpisSeleccionadosInfo),
    [kpisSeleccionadosInfo],
  );
  const esTabla = tipoGrafica === "tabla";

  // Un widget "tabla" (KPI vivo) no tiene periodo ni filtros: son datos de
  // "ahora". Su asistente es de un solo paso.
  const pasos = esTabla
    ? [{ clave: "medir", etiqueta: tx("step_measure", "Qué medir") }]
    : [
      { clave: "medir", etiqueta: tx("step_measure", "Qué medir") },
      { clave: "periodo", etiqueta: tx("step_period", "Periodo") },
      { clave: "filtros", etiqueta: tx("step_filters", "Filtros") },
    ];
  const pasoActual = Math.min(paso || 0, pasos.length - 1);
  const esUltimoPaso = pasoActual === pasos.length - 1;
  const puedeAvanzar = pasoActual === 0 ? idsKpiSeleccionados.length > 0 : true;

  // Cambiar a "numero"/"dona" con varios KPIs marcados no rompe nada: se
  // conserva solo el primero y se avisa, en vez de guardar una combinacion
  // que ese tipo de grafica no sabe representar.
  function aplicarTipoGrafica(valor) {
    if (!tiposPermitidos.includes(valor)) return;
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

  // Por que este KPI no se puede sumar a los que ya se eligieron (otra unidad, u
  // otra clase de KPI), o null. Solo aplica al combinar varios en un grafico.
  function motivoDeBloqueo(kpi) {
    if (!multiKpiPermitido || idsKpiSeleccionados.includes(String(kpi.id_kpi_definition))) return null;
    return motivoParaNoCombinar(kpisSeleccionadosInfo, kpi);
  }

  function textoDeBloqueo(kpi, motivo) {
    if (motivo === "modo") return tx("kpi_mode_mismatch", "No se puede combinar: un KPI en vivo (tabla) no comparte gráfico con uno de serie.");
    const unidadElegida = unidadInfo(unidadDeKpi(kpisSeleccionadosInfo[0])).etiquetaSelector;
    const unidadKpi = unidadInfo(unidadDeKpi(kpi)).etiquetaSelector;
    return tx(
      "kpi_unit_mismatch",
      `No se puede combinar: este KPI se mide en ${unidadKpi} y los elegidos en ${unidadElegida}. Con unidades distintas comparten eje y una barra queda invisible.`,
    );
  }

  function toggleKpi(idKpi) {
    setAvisoKpi("");
    const candidato = kpiCatalog.find((kpi) => String(kpi.id_kpi_definition) === idKpi);
    const motivo = candidato ? motivoDeBloqueo(candidato) : null;
    if (motivo) {
      setAvisoKpi(textoDeBloqueo(candidato, motivo));
      return;
    }
    let proximos;
    if (multiKpiPermitido) {
      proximos = idsKpiSeleccionados.includes(idKpi)
        ? idsKpiSeleccionados.filter((item) => item !== idKpi)
        : [...idsKpiSeleccionados, idKpi];
    } else {
      proximos = idsKpiSeleccionados.length === 1 && idsKpiSeleccionados[0] === idKpi ? [] : [idKpi];
    }
    const infos = proximos.map((id) => kpiCatalog.find((kpi) => String(kpi.id_kpi_definition) === id)).filter(Boolean);
    // Si la grafica actual ya no le sirve a lo elegido, se pasa a la que el
    // propio KPI declara como preferida (o a la primera que admita).
    const permitidos = tiposDeGraficaPermitidos(infos);
    const tipoNuevo = permitidos.includes(tipoGrafica)
      ? tipoGrafica
      : (infos[0]?.grafica_default && permitidos.includes(infos[0].grafica_default) ? infos[0].grafica_default : permitidos[0]);
    onChangePanelState({ idsKpiSeleccionados: proximos, ...(tipoNuevo && tipoNuevo !== tipoGrafica ? { tipoGrafica: tipoNuevo } : {}) });
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

  // Un chip de rango relativo guarda la INSTRUCCION ("ultimos 30 dias") y
  // rellena las fechas con lo que da hoy, para que se vean; "Personalizado"
  // conserva las fechas que haya y las deja editar a mano. Editar una fecha a
  // mano tambien pasa a "personalizado" (ver los inputs de fecha).
  function elegirRango(clave) {
    if (clave === RANGO_PERSONALIZADO) {
      onChangePanelState({ rangoRelativo: RANGO_PERSONALIZADO });
      return;
    }
    const rango = resolverRangoRelativo(clave);
    onChangePanelState({ rangoRelativo: clave, fechaInicio: rango.fecha_inicio, fechaFin: rango.fecha_fin });
  }

  function irAPaso(indice) {
    setError("");
    onChangePanelState({ paso: Math.max(0, Math.min(indice, pasos.length - 1)) });
  }

  // FormularioPlegable (cerrarAlEnviar) cierra el panel cuando esta funcion
  // RESUELVE y lo deja abierto si RECHAZA: por eso todo camino que no guardo
  // -validacion, error del servidor, "Enter" en un paso intermedio- termina
  // lanzando esto, despues de dejar su mensaje en pantalla.
  const NO_CERRAR = new Error("kpi_editor_sin_guardar");

  function rechazar(mensaje) {
    setError(mensaje);
    throw NO_CERRAR;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    // "Enter" dentro de un campo de un paso intermedio manda el formulario:
    // ahi lo esperable es pasar al siguiente paso, no guardar a medias.
    if (!esUltimoPaso) {
      if (puedeAvanzar) irAPaso(pasoActual + 1);
      throw NO_CERRAR;
    }
    if (idsKpiSeleccionados.length === 0) rechazar(tx("kpi_required", "Elige al menos un KPI."));
    // Lo que se valida es lo que se va a guardar (armarParametros): con un
    // chip relativo, las fechas ya vienen calculadas al dia de hoy.
    const parametros = armarParametros(panelState, { esTabla, tieneBajoStock: tieneBajoStockSeleccionado });
    if (!esTabla) {
      if (!parametros.fecha_inicio || !parametros.fecha_fin) rechazar(tx("range_required", "Elige el rango de fechas."));
      if (diffDias(parametros.fecha_inicio, parametros.fecha_fin) > KPI_RANGO_DIAS_MAX) {
        rechazar(tx("range_exceeds_limit", "El rango de fechas no puede exceder un año. Ajusta las fechas."));
      }
      if (comparar && (!parametros.fecha_inicio_b || !parametros.fecha_fin_b)) rechazar(tx("range_b_required", "Elige el rango de comparación o desactívala."));
      if (comparar && diffDias(parametros.fecha_inicio_b, parametros.fecha_fin_b) > KPI_RANGO_DIAS_MAX) {
        rechazar(tx("range_exceeds_limit", "El rango de comparación no puede exceder un año. Ajusta las fechas."));
      }
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
      throw err;
    } finally {
      setSaving(false);
    }
  }

  const tituloPanel = editingWidgetId ? tx("edit_widget", "Editar gráfico") : tx("add_widget", "Agregar gráfico");

  // Rango relativo vigente: las fechas que se muestran son las de HOY (no las
  // que quedaron en el borrador), igual que las que se consultan y se guardan.
  const esRelativo = RANGOS_RELATIVOS.includes(rangoRelativo);
  const rangoResuelto = esRelativo ? resolverRangoRelativo(rangoRelativo) : null;
  const periodoBResuelto = esRelativo
    ? (desfaseComparacion ? rangoDesfasado(rangoResuelto, desfaseComparacion) : periodoAnterior(rangoResuelto))
    : null;

  // Lo que va en cada paso es lo que antes eran tres columnas lado a lado;
  // el orden y los controles son los mismos, solo que ahora se recorren con
  // Atras / Siguiente y la vista previa acompana a todos.
  const contenidoDelPaso = {
    medir: (
      <>
            <div className="kpi-picker-section">
              <span>{tx("chart_type", "Tipo de gráfico")}</span>
              <div className="kpi-icon-option-group">
                {CHART_TYPES.map((opt) => {
                  const ChartIcon = CHART_TYPE_ICONS[opt.value];
                  const activo = tipoGrafica === opt.value;
                  const permitido = tiposPermitidos.includes(opt.value);
                  const etiqueta = tx(`chart_type_${opt.value}`, opt.label);
                  return (
                    <button
                      type="button"
                      key={opt.value}
                      className={`kpi-icon-option ${activo ? "active" : ""}`}
                      onClick={() => aplicarTipoGrafica(opt.value)}
                      disabled={!permitido}
                      title={permitido ? etiqueta : tx("chart_type_not_allowed", "El KPI elegido no admite este tipo de gráfico")}
                    >
                      <ChartIcon size={20} />
                      <span>{etiqueta}</span>
                      {activo && <Check size={13} className="kpi-editor-tipo-check" aria-hidden="true" />}
                    </button>
                  );
                })}
              </div>
            </div>

            {esTabla && (
              <div className="kpi-picker-section">
                <span>{tx("table_height", "Alto de la tabla")}</span>
                <div className="kpi-icon-option-group">
                  {[1, 2].map((n) => (
                    <button
                      type="button"
                      key={n}
                      className={`kpi-icon-option ${(panelState.filas === 2 ? 2 : 1) === n ? "active" : ""}`}
                      aria-pressed={(panelState.filas === 2 ? 2 : 1) === n}
                      onClick={() => onChangePanelState({ filas: n })}
                    >
                      <span>{n === 1 ? tx("table_height_1", "1 fila") : tx("table_height_2", "2 filas")}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
            {esTabla && (
              <div className="kpi-picker-section">
                <span>{tx("table_width", "Ancho de la tabla")}</span>
                <div className="kpi-icon-option-group">
                  {[1, 2].map((n) => (
                    <button
                      type="button"
                      key={n}
                      className={`kpi-icon-option ${(panelState.columnas === 2 ? 2 : 1) === n ? "active" : ""}`}
                      aria-pressed={(panelState.columnas === 2 ? 2 : 1) === n}
                      onClick={() => onChangePanelState({ columnas: n })}
                    >
                      <span>{n === 1 ? tx("table_width_1", "1 columna") : tx("table_width_2", "2 columnas")}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="kpi-picker-section">
              <span>
                {tx("kpi", "KPI")}
                {multiKpiPermitido && idsKpiSeleccionados.length > 0 && (
                  <em className="kpi-picker-count"> — {tx("kpi_selected_count", `${idsKpiSeleccionados.length} seleccionado(s)`)}</em>
                )}
              </span>
              {avisoKpi && <p className="kpi-inline-notice">{avisoKpi}</p>}
              {mezclaUnidades(kpisSeleccionadosInfo) && (
                <p className="kpi-inline-notice">
                  {tx("kpi_units_mixed_legacy", "Este gráfico combina KPIs de unidades distintas (se armó antes de que el editor lo impidiera): sigue viéndose igual, pero una barra puede quedar muy pequeña. Quita un KPI para separarlos.")}
                </p>
              )}
              <SelectorDeKpi
                catalogo={kpiCatalog}
                seleccionados={idsKpiSeleccionados}
                multiple={multiKpiPermitido}
                onAlternar={toggleKpi}
                metaDeModulo={kpiModuleMeta}
                textoDeBloqueo={textoDeBloqueo}
                coloresKpi={coloresKpi}
                onElegirColor={elegirColorKpi}
                textos={{
                  buscar: tx("kpi_search_placeholder", "Buscar KPI…"),
                  sinResultados: tx("kpi_search_empty", "Ningún KPI coincide con la búsqueda."),
                  variables: tx("kpi_variables_group", "Variables"),
                  variablesAyuda: tx("selector_variables_ayuda", "Todos los KPIs sin desglose, de cualquier módulo: sirven para combinar en un mismo gráfico."),
                  combinables: tx("selector_combinables", "Combinables (sin desglose)"),
                  elegirColor: tx("kpi_color_choose", "Elegir color"),
                }}
              />
            </div>
      </>
    ),
    periodo: (
      <>
            <div className="kpi-picker-section">
              <span>{tx("date_range", "Periodo")}</span>
              <div className="kpi-editor-chips" role="group" aria-label={tx("date_range", "Periodo")}>
                {[...RANGOS_RELATIVOS, RANGO_PERSONALIZADO].map((clave) => (
                  <button
                    type="button"
                    key={clave}
                    className={`kpi-editor-chip ${rangoRelativo === clave ? "activo" : ""}`}
                    aria-pressed={rangoRelativo === clave}
                    onClick={() => elegirRango(clave)}
                  >
                    {tx(`range_${clave}`, ETIQUETA_RANGO_POR_OMISION[clave])}
                  </button>
                ))}
              </div>
              {esRelativo && (
                <p className="kpi-editor-rango-resuelto">
                  {rangoResuelto.fecha_inicio} → {rangoResuelto.fecha_fin}
                  <span> · {tx("range_relative_hint", "se recalcula cada vez que se abre el tablero")}</span>
                </p>
              )}
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
                    {etiquetaDeAgrupar}
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

            {!esRelativo && (
              <div className="form-grid">
                <label className="field">
                  <span>{tx("start_date", "Fecha inicio")}</span>
                  <input
                    type="date"
                    value={fechaInicio}
                    max={fechaFin || undefined}
                    onChange={(event) => onChangePanelState({ fechaInicio: event.target.value, rangoRelativo: RANGO_PERSONALIZADO })}
                    required
                  />
                </label>
                <label className="field">
                  <span>{tx("end_date", "Fecha fin")}</span>
                  <input
                    type="date"
                    value={fechaFin}
                    min={fechaInicio || undefined}
                    onChange={(event) => onChangePanelState({ fechaFin: event.target.value, rangoRelativo: RANGO_PERSONALIZADO })}
                    required
                  />
                </label>
              </div>
            )}

            <label className="field checkbox-field">
              <input type="checkbox" checked={comparar} onChange={(event) => onChangePanelState({ comparar: event.target.checked })} />
              <span>{esRelativo ? tx("compare_relative_toggle", "Comparar") : tx("compare_toggle", "Comparar contra otro periodo")}</span>
            </label>

            {comparar && esRelativo && (
              <>
                <label className="field">
                  <span>{tx("compare_against", "Contra")}</span>
                  <select
                    value={desfaseComparacion || ""}
                    onChange={(event) => onChangePanelState({ desfaseComparacion: event.target.value ? Number(event.target.value) : null })}
                  >
                    <option value="">{tx("compare_previous_period", "El periodo anterior")}</option>
                    {DESFASES_DE_COMPARACION.map((dias) => (
                      <option key={dias} value={dias}>{tx(`compare_shift_${dias}`, `Hace ${dias} días`)}</option>
                    ))}
                  </select>
                </label>
                <p className="kpi-editor-rango-resuelto">{periodoBResuelto.fecha_inicio_b} → {periodoBResuelto.fecha_fin_b}</p>
              </>
            )}

            {comparar && !esRelativo && (
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
      </>
    ),
    filtros: (
      <>
            {mostrarFiltroDePersonas && users.length > 0 && (
              <div className="kpi-employee-picker">
                <KpiDropdownPicker
                  label={
                    empleadosSeleccionados.length > 0
                      ? tx("employees_selected_count", `${empleadosSeleccionados.length} empleado(s) seleccionado(s)`)
                      : tx("employees_filter", "Filtrar por empleados (opcional)")
                  }
                  searchPlaceholder={tx("dropdown_search_placeholder", "Buscar...")}
                  renderOptions={(filtro) => {
                    const usuariosFiltrados = filtro
                      ? users.filter((user) => normalizarBusqueda(user.full_name || user.username || `#${user.id_user}`).includes(filtro))
                      : users;
                    if (usuariosFiltrados.length === 0) {
                      return <p className="kpi-dropdown-picker-empty">{tx("no_results", "Sin resultados")}</p>;
                    }
                    return (
                      <div className="kpi-employee-list">
                        {usuariosFiltrados.map((user) => {
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
                    );
                  }}
                />
              </div>
            )}

            {mostrarFiltroDePersonas && departments.length > 0 && (
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
      </>
    ),
  };

  return (
    <FormularioPlegable
      titulo={tituloPanel}
      icono={editingWidgetId ? Pencil : Plus}
      className="kpi-editor"
      abierto={!colapsado}
      onCambioAbierto={(abierto) => {
        onChangePanelState({ colapsado: !abierto });
        if (abierto) onAbierto();
      }}
      onSubmit={handleSubmit}
      cerrarAlEnviar
    >
      {kpiCatalog.length === 0 ? (
        <div className="empty">
          <strong>{tx("no_kpis_title", "No tienes KPIs asignados")}</strong>
          <p>{tx("no_kpis_body", "Pide a un administrador que te asigne permiso sobre algún KPI para poder graficarlo aquí.")}</p>
        </div>
      ) : (
        <>
          {pasos.length > 1 && (
            <ol className="kpi-editor-pasos" aria-label={tx("steps_label", "Pasos")}>
              {pasos.map((item, indice) => (
                <li key={item.clave}>
                  <button
                    type="button"
                    className={`kpi-editor-paso ${indice === pasoActual ? "activo" : ""} ${indice < pasoActual ? "completo" : ""}`}
                    onClick={() => (indice <= pasoActual || puedeAvanzar) && irAPaso(indice)}
                    aria-current={indice === pasoActual ? "step" : undefined}
                  >
                    <span className="kpi-editor-paso-numero">{indice < pasoActual ? <Check size={13} /> : indice + 1}</span>
                    {item.etiqueta}
                  </button>
                </li>
              ))}
            </ol>
          )}

          <div className="kpi-editor-cuerpo">
            <div className="kpi-editor-paso-contenido kpi-panel-col">
              {contenidoDelPaso[pasos[pasoActual].clave]}
            </div>
            <aside className="kpi-editor-vista-previa">
              <p className="kpi-editor-grupo-titulo">{tx("preview", "Vista previa")}</p>
              {kpisSeleccionadosInfo.length === 0 ? (
                <p className="muted">{tx("preview_empty", "Elige un KPI para ver cómo quedará.")}</p>
              ) : (
                <div className="kpi-editor-vista-previa-tarjeta">
                  <strong>{kpisSeleccionadosInfo.map((kpi) => kpi.etiqueta || kpi.clave).join(" + ")}</strong>
                  {kpisSeleccionadosInfo.length === 1 && kpisSeleccionadosInfo[0].descripcion && (
                    <span className="muted">{kpisSeleccionadosInfo[0].descripcion}</span>
                  )}
                  <VistaPreviaEditor
                    widget={widgetDeBorrador(panelState, { esTabla, tieneBajoStock: tieneBajoStockSeleccionado })}
                    kpiCatalog={kpiCatalog}
                    userLabel={userLabel}
                    productLabel={productLabel}
                    formatNumber={formatNumber}
                    t={t}
                    tx={tx}
                    textosEjemplo={textosEjemplo}
                  />
                </div>
              )}
            </aside>
          </div>

          {error && <div className="alert error kpi-editor-error">{error}</div>}

          <footer className="kpi-editor-footer">
            <div className="kpi-editor-footer-nav">
              <div className="kpi-editor-footer-derecha">
                <button type="button" className="button ghost" onClick={onCancel}>{t("common.cancel")}</button>
                <button type="button" className="button ghost" disabled={pasoActual === 0} onClick={() => irAPaso(pasoActual - 1)}>
                  {tx("step_back", "Atrás")}
                </button>
              </div>
              {!esUltimoPaso ? (
                <button type="button" className="button primary" disabled={!puedeAvanzar} onClick={() => irAPaso(pasoActual + 1)}>
                  {tx("step_next", "Siguiente")}
                </button>
              ) : (
                <button
                  type="submit"
                  className="button primary"
                  disabled={saving || idsKpiSeleccionados.length === 0}
                >
                  {editingWidgetId ? tx("update_widget", "Actualizar") : tx("add_widget", "Agregar gráfico")}
                </button>
              )}
            </div>
          </footer>
        </>
      )}
    </FormularioPlegable>
  );
}
