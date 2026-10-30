// Punto de entrada que empaqueta renderTarjetas.test.mjs con esbuild: pinta la
// tarjeta y el cuerpo del Dashboard en servidor (renderToStaticMarkup) para
// que la prueba pueda comprobar que NINGUNA combinacion lanza al renderizar.
import { renderToStaticMarkup } from "react-dom/server";
import { CuerpoDeWidget, KpiWidgetCard, KpiWidgetPanel, MarcoDeEjemplo } from "../pages/Dashboard.jsx";
import SelectorDeKpi from "../components/kpi-widgets/SelectorDeKpi.jsx";
import { rangoInicialDelBorrador } from "./kpiParametros.js";

const t = (clave, respaldo) => (typeof respaldo === "string" ? respaldo : clave);
const tx = (clave, respaldo) => respaldo ?? clave;
const formatNumber = (valor) => new Intl.NumberFormat("es-MX", { maximumFractionDigits: 2 }).format(valor || 0);
const userLabel = (id) => ({ 5: "Ana", 7: "Beto", 9: "Carla" }[id] || `#${id}`);
const productLabel = (id) => `Producto ${id}`;

/** La tarjeta completa (encabezado + cuerpo en estado de carga: en servidor no
 * corren los efectos que traen los datos). */
export function pintarTarjeta({ widget, kpiCatalog }) {
  return renderToStaticMarkup(
    <KpiWidgetCard
      widget={widget}
      kpiCatalog={kpiCatalog}
      userLabel={userLabel}
      productLabel={productLabel}
      formatNumber={formatNumber}
      onEdit={() => {}}
      onDelete={() => {}}
      onReady={() => {}}
      t={t}
      tx={tx}
      dragHandleProps={{}}
      isDragging={false}
      animar={false}
      esNuevo={false}
    />,
  );
}

/** El cuerpo con datos ya cargados (o vacios, o con error). */
export function pintarCuerpo({ widget, datos }) {
  return renderToStaticMarkup(
    <CuerpoDeWidget
      widget={widget}
      datos={datos}
      userLabel={userLabel}
      productLabel={productLabel}
      formatNumber={formatNumber}
      t={t}
      tx={tx}
      animar={false}
    />,
  );
}

/** El selector de KPI del editor. `props` son las del componente; lo que no se
 * pase toma valores de prueba (metaDeModulo sin iconos, tooltip legible). */
export function pintarSelector(props) {
  return renderToStaticMarkup(
    <SelectorDeKpi
      onAlternar={() => {}}
      metaDeModulo={(modulo) => ({ icon: null, label: `Modulo ${modulo}` })}
      textoDeBloqueo={(kpi, motivo) => `BLOQUEADO(${motivo}): ${kpi.etiqueta}`}
      {...props}
    />,
  );
}

/** El panel "Agregar grafico" abierto en su primer paso («Que medir»), con su selector de KPI cableado como en la pantalla
 * real: sirve para comprobar lo que el Dashboard le pasa al selector (iconos y nombres de pestana, traducciones).
 * `traducir` (opcional) reemplaza al `tx` de prueba, que devuelve el texto de respaldo. */
export function pintarPanel({ kpiCatalog, idsKpiSeleccionados = [], traducir } = {}) {
  const panelState = {
    editingWidgetId: null, colapsado: false, paso: 0, idsKpiSeleccionados, tipoGrafica: "barras",
    ...rangoInicialDelBorrador(), comparar: false, desfaseComparacion: null,
    fechaInicioB: "", fechaFinB: "", empleadosSeleccionados: [], departamentosSeleccionados: [], coloresKpi: {},
    agruparPor: "entidad", umbralBajoStock: "", filas: 1,
  };
  return renderToStaticMarkup(
    <KpiWidgetPanel
      panelState={panelState}
      onChangePanelState={() => {}}
      kpiCatalog={kpiCatalog}
      users={[]}
      departments={[]}
      userLabel={userLabel}
      productLabel={productLabel}
      formatNumber={formatNumber}
      onCancel={() => {}}
      onSave={() => {}}
      onAbierto={() => {}}
      t={t}
      tx={traducir || tx}
    />,
  );
}

/** El aviso y la marca de una vista previa con datos de ejemplo (texto en espanol, como el `tx` de prueba). */
export function pintarMarcoEjemplo({ hijo = "contenido" } = {}) {
  return renderToStaticMarkup(<MarcoDeEjemplo tx={tx}>{hijo}</MarcoDeEjemplo>);
}
