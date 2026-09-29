// Punto de entrada que empaqueta renderTarjetas.test.mjs con esbuild: pinta la
// tarjeta y el cuerpo del Dashboard en servidor (renderToStaticMarkup) para
// que la prueba pueda comprobar que NINGUNA combinacion lanza al renderizar.
import { renderToStaticMarkup } from "react-dom/server";
import { CuerpoDeWidget, KpiWidgetCard } from "../pages/Dashboard.jsx";
import SelectorDeKpi from "../components/kpi-widgets/SelectorDeKpi.jsx";

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
