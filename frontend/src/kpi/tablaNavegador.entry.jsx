/* eslint-disable react/prop-types, react-refresh/only-export-components */
// Se empaqueta para el NAVEGADOR (ver navegadorTabla.test.mjs): monta la tarjeta REAL
// del Dashboard (KpiWidgetCard, la misma que pinta el tablero) dentro de la misma
// cuadricula y con vecinos "Agregar grafico", para medir con un Chrome de verdad si
// algo se sale de su tarjeta o queda tapado. Sus datos salen del fetch que la pagina
// sustituye por la respuesta REAL del backend guardada en fixtures/.
import { createRoot } from "react-dom/client";
import { KpiWidgetCard } from "../pages/Dashboard.jsx";

const t = (clave, respaldo) => (typeof respaldo === "string" ? respaldo : clave);
const tx = (clave, respaldo) => respaldo ?? clave;
const KPI = {
  id_kpi_definition: 57, clave: "material_prestado_actual", etiqueta: "Material prestado ahora",
  modulo: "operaciones", modo: "vivo", unidad: "piezas", dimensiones: ["empleado"], direccion: "neutral",
  graficas_permitidas: ["tabla"], etiqueta_dimension: "Responsable",
};

function Escenario({ columnas, vecinos }) {
  const widget = {
    id_kpi_dashboard_widget: 1, tipo_grafica: "tabla", ids_kpi_definition: [57],
    parametros: columnas ? { columnas } : {},
  };
  return (
    <div className="kpi-widget-grid">
      <div className={columnas === 2 ? "kpi-widget-doble" : undefined} data-tarjeta="1">
        <KpiWidgetCard
          widget={widget}
          kpiCatalog={[KPI]}
          userLabel={(id) => `#${id}`}
          productLabel={(id) => `#${id}`}
          formatNumber={(valor) => String(valor)}
          onEdit={() => {}}
          onDelete={() => {}}
          onReady={() => {}}
          t={t}
          tx={tx}
          dragHandleProps={{}}
          isDragging={false}
          animar={false}
          esNuevo={false}
        />
      </div>
      {Array.from({ length: vecinos }).map((_, indice) => (
        // eslint-disable-next-line react/no-array-index-key
        <button type="button" key={indice} className="kpi-widget-placeholder" data-vecino={indice}>
          <span>Agregar gráfico</span>
        </button>
      ))}
    </div>
  );
}

window.montarTabla = ({ contenedor, columnas = 0, vecinos = 3 }) => {
  createRoot(contenedor).render(<Escenario columnas={columnas} vecinos={vecinos} />);
};
