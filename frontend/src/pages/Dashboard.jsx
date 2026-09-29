/* eslint-disable react/prop-types */
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  AreaChart as AreaChartIcon, BarChart2, Boxes, ChevronDown, ChevronUp,
  Check, ClipboardList, FileDown, FileText, FlaskConical, GripVertical, Hash, LineChart as LineChartIcon,
  Loader2, Pencil, PieChart as PieChartIcon, Plus, Receipt,
  RefreshCw, SlidersHorizontal, Table as TableIcon, Trash2, User,
} from "lucide-react";
import { DndContext, PointerSensor, closestCenter, useSensor, useSensors } from "@dnd-kit/core";
import { SortableContext, arrayMove, rectSortingStrategy, useSortable } from "@dnd-kit/sortable";
import { CSS as DndCss } from "@dnd-kit/utilities";
import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";
import { useI18n } from "../i18n";
import FormularioPlegable from "../components/FormularioPlegable.jsx";
import useReducedMotion from "../components/kpi-widgets/useReducedMotion";
import {
  getAllKpiDashboard, createKpiDashboard, updateKpiDashboard, deleteKpiDashboard,
  getAllKpiDashboardWidget, createKpiDashboardWidget, updateKpiDashboardWidget, deleteKpiDashboardWidget,
  getAllKpiDefinition, queryKpiSnapshot, queryKpiVivo, getAllUser, getAllDepartment, getAllProduct,
} from "../api";
import "../styles/kpi-widgets.css";
import "../styles/kpi-editor.css";
import "../styles/kpi-dashboard.css";
import PageHeader from "../components/PageHeader.jsx";
import TIPO_GRAFICA_COMPONENTE from "../components/kpi-widgets/tipoGraficaComponentes";
import Skeleton from "../components/kpi-widgets/Skeleton";
import {
  CATEGORICAL, colorDeKpi, colorEfectivoDeKpi, labelForDimension,
} from "../kpi/kpiDatos.js";
import {
  armarParametros, estadoDeWidget, rangoInicialDelBorrador, widgetDeBorrador,
} from "../kpi/kpiParametros.js";
import {
  RANGOS_RELATIVOS, RANGO_PERSONALIZADO, fechaLocalIso, parametrosEfectivos,
  periodoAnterior, resolverRangoRelativo,
} from "../kpi/kpiRango.js";
import {
  UMBRAL_ATRASO_PRESTAMO_DIAS, filasTablaPrestamo, propsDona, propsNumero,
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

// Sin distinguir mayusculas/acentos: mismo patron NFD que ya usa
// normalizarEstatus en InventoryTracePage.jsx, aqui aplicado a busqueda libre
// (nombre de empleado o de variable) en vez de a un estatus fijo.
function normalizarBusqueda(valor) {
  return String(valor || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .trim();
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
  // color de los chips de KPI (ver swatchAbierto en KpiWidgetPanel).
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
    categoriaKpi: "",
    tipoGrafica: "numero",
    // Rango: por omision "ultimos 30 dias" como chip (se recalcula cada vez que
    // se mira); "personalizado" = fechas tecleadas a mano, como antes.
    ...rangoInicialDelBorrador(),
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

  const [placeholderCount, gridRefDeSondeo] = useCompleteGridPlaceholders(widgets.length);
  // El nodo real del grid, en un ref mutable (no en el estado interno del
  // hook de arriba, que ademas de callback-ref no expone su nodo) -- lo
  // necesita `generarReportePdf` para capturarlo con html2canvas. Tiene que
  // ser un ref y no un valor cerrado sobre el render en el que se creo el
  // closure de esa funcion: mientras "todos los paneles" recorre tableros
  // via `setActiveId`, el grid se desmonta/remonta con cada carga
  // (`{!loadingWidgets && (...)}` en el render), y solo un ref mutable sigue
  // reflejando el nodo ACTUAL en cada vuelta del bucle.
  const widgetGridNodeRef = useRef(null);
  const widgetGridRef = useCallback((nodo) => {
    widgetGridNodeRef.current = nodo;
    gridRefDeSondeo(nodo);
  }, [gridRefDeSondeo]);

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
  const loadWidgets = useCallback(async (dashboardId) => {
    if (!dashboardId) { setWidgets([]); return []; }
    setLoadingWidgets(true);
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

  // --- Reporte PDF (exportar el dashboard, ver generarReportePdf mas abajo) ---
  const [mostrarDialogoExportarPdf, setMostrarDialogoExportarPdf] = useState(false);
  const [exportandoPdf, setExportandoPdf] = useState(false);
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
        const canvas = await html2canvas(nodoGrid, { scale: ESCALA_CAPTURA_PDF, backgroundColor: "#ffffff" });
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
  async function handleDragEndWidgets(event) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = widgets.findIndex((item) => item.id_kpi_dashboard_widget === active.id);
    const newIndex = widgets.findIndex((item) => item.id_kpi_dashboard_widget === over.id);
    if (oldIndex === -1 || newIndex === -1) return;

    const reordenados = arrayMove(widgets, oldIndex, newIndex);
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
      await loadWidgets(activeId);
    }
  }

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
    await loadWidgets(activeId);
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
            <DndContext sensors={dragSensors} collisionDetection={closestCenter} onDragEnd={handleDragEndWidgets}>
            <SortableContext items={widgets.map((widget) => widget.id_kpi_dashboard_widget)} strategy={rectSortingStrategy}>
            <div className="kpi-widget-grid" ref={widgetGridRef}>
              {widgets.map((widget) => (
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
                  onClick={() => abrirEditor(activeId)}
                  title={tx("add_widget", "Agregar gráfico")}
                >
                  <Plus size={22} />
                  <span>{tx("add_widget", "Agregar gráfico")}</span>
                </button>
              ))}
            </div>
            </SortableContext>
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
function SortableKpiWidgetCard(props) {
  const { widget } = props;
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: widget.id_kpi_dashboard_widget,
  });
  const style = {
    transform: DndCss.Transform.toString(transform),
    // La transicion de dnd-kit es la que acomoda con animacion suave al
    // resto de las tarjetas cuando una se suelta -- se conserva SIEMPRE,
    // incluso mientras se arrastra la propia (isDragging), para que las
    // demas nunca salten de golpe a su nuevo lugar.
    transition,
    zIndex: isDragging ? 1 : "auto",
  };
  return (
    <div ref={setNodeRef} style={style} className={isDragging ? "kpi-widget-dragging" : ""} data-widget-id={widget.id_kpi_dashboard_widget}>
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
function useDatosDeWidget({ widget, kpiCatalog, onReady }) {
  const [snapshots, setSnapshots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  // KPI "vivo" (ver material_prestado_actual): su propio estado, aparte del
  // de kpi_snapshot -- ni la forma de los datos (una lista paginada, no
  // series por entidad/dia) ni el endpoint (GET .../vivo) son los mismos.
  const [vivoItems, setVivoItems] = useState([]);
  const [vivoTotal, setVivoTotal] = useState(0);

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

  useEffect(() => {
    let cancelado = false;
    async function cargarVivo() {
      setLoading(true);
      setError("");
      try {
        const resultado = await queryKpiVivo(idsUsados[0], { limit: 50, offset: 0 });
        if (!cancelado) { setVivoItems(resultado.items || []); setVivoTotal(resultado.total || 0); }
      } catch (err) {
        if (!cancelado) { setError(err.message || "errors.request_failed"); setVivoItems([]); }
      } finally {
        if (!cancelado) { setLoading(false); onReady?.(idWidget); }
      }
    }
    if (esTablaVivo) cargarVivo();
    return () => { cancelado = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [esTablaVivo, idsKey, onReady, idWidget]);

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

  return { snapshots, loading, error, vivoItems, vivoTotal, kpiInfos, idsUsados, esTablaVivo };
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
function CuerpoDeWidget({ widget, datos, userLabel, productLabel, formatNumber, t, tx, animar }) {
  const { snapshots, loading, error, vivoItems, vivoTotal, kpiInfos, esTablaVivo } = datos;
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
        <KpiTablaVivo items={vivoItems} total={vivoTotal} tx={tx} />
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
        />
      )}
    </>
  );
}

// Vista previa del editor: consulta EXACTAMENTE lo que se va a guardar (el
// borrador pasa por armarParametros, igual que al guardar) y lo pinta con el
// mismo cuerpo que la tarjeta del tablero. Skeleton mientras espera -tanto la
// pausa de tecleo como la respuesta del servidor-.
function VistaPreviaEditor({ widget, kpiCatalog, userLabel, productLabel, formatNumber, t, tx }) {
  const widgetRetrasado = useValorRetrasado(widget, 400);
  const datos = useDatosDeWidget({ widget: widgetRetrasado, kpiCatalog });
  const pendiente = JSON.stringify(widget) !== JSON.stringify(widgetRetrasado);
  return (
    <div className="kpi-editor-vista-previa-cuerpo">
      <CuerpoDeWidget
        widget={widgetRetrasado}
        datos={{ ...datos, loading: datos.loading || pendiente }}
        userLabel={userLabel}
        productLabel={productLabel}
        formatNumber={formatNumber}
        t={t}
        tx={tx}
        animar={false}
      />
    </div>
  );
}

function KpiWidgetCard({ widget, kpiCatalog, userLabel, productLabel, formatNumber, onEdit, onDelete, onReady, t, tx, dragHandleProps, isDragging, animar, esNuevo }) {
  const datos = useDatosDeWidget({ widget, kpiCatalog, onReady });
  const { kpiInfos, idsUsados, esTablaVivo } = datos;
  const parametros = parametrosEfectivos(widget.parametros);
  const fechaInicio = parametros.fecha_inicio;
  const fechaFin = parametros.fecha_fin;
  const fechaInicioB = parametros.fecha_inicio_b;
  const fechaFinB = parametros.fecha_fin_b;

  const chartTypeLabel = CHART_TYPES.find((opt) => opt.value === widget.tipo_grafica)?.label || widget.tipo_grafica;
  const rangoTexto = esTablaVivo
    ? tx("live_data", "En vivo -- siempre lo más reciente")
    : (fechaInicio && fechaFin ? `${etiquetaRango}${fechaInicio} → ${fechaFin}` : tx("missing_range", "Sin rango de fechas configurado"));
  const rangoBTexto = fechaInicioB && fechaFinB ? `${fechaInicioB} → ${fechaFinB}` : "";
  // "Ultimos 30 dias · 2026-08-31 → 2026-09-29": el nombre del rango solo si el
  // widget lo trae; uno de fechas fijas se ve como siempre.
  const etiquetaRango = RANGOS_RELATIVOS.includes(widget.parametros?.rango_relativo)
    ? `${tx(`range_${widget.parametros.rango_relativo}`, widget.parametros.rango_relativo)} · `
    : "";
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
        <div>
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
function KpiTablaVivo({ items, total, tx }) {
  const Componente = TIPO_GRAFICA_COMPONENTE.tabla;
  return (
    <Componente
      filas={filasTablaPrestamo(items, tx("unknown_user", "Sin asignar"))}
      total={total}
      umbralDias={UMBRAL_ATRASO_PRESTAMO_DIAS}
      etiquetas={{
        articulo: tx("loan_item", "Artículo"),
        responsable: tx("loan_holder", "Responsable"),
        fecha_prestamo: tx("loan_date", "Fecha del vale"),
        dias_prestado: tx("loan_days", "Días prestado"),
        dias: tx("loan_days_unit", "días"),
        vacio: tx("widget_no_loans", "No hay artículos prestados sin devolver en este momento."),
        ordenar: tx("loan_sort_by", "Ordenar por"),
        invertir_orden: tx("loan_sort_reverse", "Invertir el orden"),
        mostrando: tx("loan_showing", "Mostrando"),
        de: tx("loan_of", "de"),
      }}
    />
  );
}

// El mapa `tipo_grafica -> componente` vive en
// components/kpi-widgets/tipoGraficaComponentes.js; aqui solo se arman las
// props de cada uno (ver kpi/kpiAdaptadores.js).
function KpiChartBody({ widget, snapshots, kpiInfos, userLabel, productLabel, formatNumber, tx, animar }) {
  const snapshot = snapshots[0];
  const kpiInfo = kpiInfos[0];
  const parametros = widget.parametros || {};
  const agruparPorPeriodo = parametros.agrupar_por === "periodo";
  const labelForId = agruparPorPeriodo ? (id) => id : labelForDimension(kpiInfo?.dimensiones?.[0], userLabel, productLabel);
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
  return <Componente {...props} tipo={widget.tipo_grafica} animar={animar} />;
}

// Texto de cada chip de rango cuando la traduccion no lo trae.
const ETIQUETA_RANGO_POR_OMISION = {
  hoy: "Hoy",
  "7_dias": "7 días",
  "30_dias": "30 días",
  "90_dias": "90 días",
  este_mes: "Este mes",
  mes_anterior: "Mes anterior",
  este_anio: "Este año",
  personalizado: "Personalizado",
};

// Tipos de grafica que admiten TODOS los KPIs elegidos a la vez (interseccion
// de sus `graficas_permitidas`). Sin KPI elegido, todos menos "tabla", que
// solo existe para KPIs "vivos". Un KPI que no trae la lista no restringe.
function tiposDeGraficaPermitidos(kpiInfos) {
  const todos = CHART_TYPES.map((opt) => opt.value);
  if (kpiInfos.length === 0) return todos.filter((tipo) => tipo !== "tabla");
  return kpiInfos.reduce((permitidos, info) => {
    const lista = Array.isArray(info.graficas_permitidas) && info.graficas_permitidas.length ? info.graficas_permitidas : todos.filter((tipo) => tipo !== "tabla");
    return permitidos.filter((tipo) => lista.includes(tipo));
  }, todos);
}

function KpiWidgetPanel({ panelState, onChangePanelState, kpiCatalog, users, departments, userLabel, productLabel, formatNumber, onCancel, onSave, onAbierto, t, tx }) {
  const {
    editingWidgetId,
    colapsado,
    paso,
    idsKpiSeleccionados,
    categoriaKpi,
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

  // Para el resumen del picker desplegable de variables (ver KpiDropdownPicker).
  const variablesSeleccionadas = kpisSeleccionadosInfo.filter((kpi) => kpi.dimensiones?.[0] === "global");

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

  function toggleKpi(idKpi) {
    setAvisoKpi("");
    let proximos;
    if (multiKpiPermitido) {
      proximos = idsKpiSeleccionados.includes(idKpi)
        ? idsKpiSeleccionados.filter((item) => item !== idKpi)
        : [...idsKpiSeleccionados, idKpi];
    } else {
      proximos = idsKpiSeleccionados.length === 1 && idsKpiSeleccionados[0] === idKpi ? [] : [idKpi];
    }
    let infos = proximos.map((id) => kpiCatalog.find((kpi) => String(kpi.id_kpi_definition) === id)).filter(Boolean);
    // Dos KPIs sin ninguna grafica en comun (uno "vivo" y uno de serie) no
    // se pueden combinar: se queda solo el que se acaba de elegir.
    if (infos.length > 1 && tiposDeGraficaPermitidos(infos).length === 0) {
      proximos = [idKpi];
      infos = infos.filter((kpi) => String(kpi.id_kpi_definition) === idKpi);
      setAvisoKpi(tx("kpi_incompatible", "Ese KPI no se puede combinar con los anteriores. Se conservó solo el nuevo."));
    }
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

  function irAPaso(indice) {
    setError("");
    onChangePanelState({ paso: Math.max(0, Math.min(indice, pasos.length - 1)) });
  }

  const tituloPanel = editingWidgetId ? tx("edit_widget", "Editar gráfico") : tx("add_widget", "Agregar gráfico");

  // Rango relativo vigente: las fechas que se muestran son las de HOY (no las
  // que quedaron en el borrador), igual que las que se consultan y se guardan.
  const esRelativo = RANGOS_RELATIVOS.includes(rangoRelativo);
  const rangoResuelto = esRelativo ? resolverRangoRelativo(rangoRelativo) : null;
  const periodoBResuelto = esRelativo ? periodoAnterior(rangoResuelto) : null;

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
                <KpiDropdownPicker
                  label={
                    variablesSeleccionadas.length > 0
                      ? tx("kpi_variables_selected_count", `${variablesSeleccionadas.length} variable(s) seleccionada(s)`)
                      : tx("kpi_variables", "Variables (para combinar en un mismo gráfico)")
                  }
                  searchPlaceholder={tx("dropdown_search_placeholder", "Buscar...")}
                  renderOptions={(filtro) => {
                    const variablesFiltradas = filtro
                      ? kpisVariables.filter((kpi) => normalizarBusqueda(kpi.etiqueta || kpi.clave).includes(filtro))
                      : kpisVariables;
                    if (variablesFiltradas.length === 0) {
                      return <p className="kpi-dropdown-picker-empty">{tx("no_results", "Sin resultados")}</p>;
                    }
                    return (
                      <div className="kpi-chip-option-group">
                        {variablesFiltradas.map(renderKpiChip)}
                      </div>
                    );
                  }}
                />
              </div>
            )}
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
              <span>{esRelativo ? tx("compare_previous_toggle", "Comparar contra el periodo anterior") : tx("compare_toggle", "Comparar contra otro periodo")}</span>
            </label>

            {comparar && esRelativo && (
              <p className="kpi-editor-rango-resuelto">{periodoBResuelto.fecha_inicio_b} → {periodoBResuelto.fecha_fin_b}</p>
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
            {users.length > 0 && (
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
                <button type="submit" className="button primary" disabled={saving || idsKpiSeleccionados.length === 0}>
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
