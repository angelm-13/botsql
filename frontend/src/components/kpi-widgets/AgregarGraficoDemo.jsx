import { useState } from "react";
import {
  AreaChart as AreaChartIcon, BarChart2, Boxes, Check, FileText, FlaskConical,
  Hash, LineChart as LineChartIcon, PieChart as PieChartIcon, Receipt,
  Table as TableIcon,
} from "lucide-react";
import FormularioPlegable from "../FormularioPlegable";
import SelectorDeKpi from "./SelectorDeKpi";
import { EMPLEADOS_DEMO, KPIS_DEMO_PARA_EDITOR } from "./demoData";
import { colorDeAvatar, inicialesDe } from "./avatar";

// Un icono propio por modulo -- hoy Inventario/Laboratorio/Documentos
// comparten el mismo icono de sliders en el editor real (ver Dashboard.jsx,
// KPI_MODULE_META). Aqui cada modulo que puede traer un KPI tiene el suyo.
const ICONO_MODULO = {
  facturacion: Receipt,
  operaciones: Boxes,
  laboratorio: FlaskConical,
  documentos: FileText,
};

// Un tono propio por tipo de grafica -- vivo y claro, uno distinto por tipo
// para reconocerlos a simple vista; nunca marrones ni grafitos.
const CHART_TYPES = [
  { tipo: "numero", etiqueta: "Número", Icono: Hash, color: "#2a78d6" },
  { tipo: "barras", etiqueta: "Barras", Icono: BarChart2, color: "#eb6834" },
  { tipo: "linea", etiqueta: "Línea", Icono: LineChartIcon, color: "#12b8c9" },
  { tipo: "area", etiqueta: "Área", Icono: AreaChartIcon, color: "#1baf7a" },
  { tipo: "dona", etiqueta: "Dona", Icono: PieChartIcon, color: "#8b6cf6" },
  { tipo: "tabla", etiqueta: "Tabla", Icono: TableIcon, color: "#e87ba4" },
];

const PERIODOS_RELATIVOS = ["Hoy", "7 días", "30 días", "90 días", "Este mes", "Mes anterior", "Este año", "Personalizado"];

const PASOS = ["Qué medir", "Cómo verlo", "Periodo", "Filtros"];

// El selector es el MISMO componente que usa el editor real; la demo solo le
// da un catalogo con la forma de /kpi_definition/ (un id por KPI).
const CATALOGO_DEMO = KPIS_DEMO_PARA_EDITOR.map((kpi, indice) => ({ ...kpi, id_kpi_definition: indice + 1, modo: "snapshot" }));
const ETIQUETA_MODULO = { facturacion: "Facturación", operaciones: "Operaciones", laboratorio: "Laboratorio", documentos: "Documentos" };
const metaDeModulo = (modulo) => ({ icon: ICONO_MODULO[modulo] || Boxes, label: ETIQUETA_MODULO[modulo] || modulo });

export default function AgregarGraficoDemo() {
  const [paso, setPaso] = useState(0);
  const [idKpi, setIdKpi] = useState(null);
  const [tipoGrafica, setTipoGrafica] = useState(null);
  const [periodo, setPeriodo] = useState("30 días");
  const [empleadosSeleccionados, setEmpleadosSeleccionados] = useState([]);

  const kpiSeleccionado = CATALOGO_DEMO.find((kpi) => String(kpi.id_kpi_definition) === idKpi) || null;
  const claveKpi = kpiSeleccionado?.clave || null;

  // Un KPI por grafico: elegir otro reemplaza al anterior, y volver a pulsar el
  // elegido lo quita.
  function elegirKpi(id) {
    if (id === idKpi) {
      setIdKpi(null);
      return;
    }
    setIdKpi(id);
    setTipoGrafica(CATALOGO_DEMO.find((kpi) => String(kpi.id_kpi_definition) === id).grafica_default);
  }

  function alternarEmpleado(idUsuario) {
    setEmpleadosSeleccionados((actual) => (
      actual.includes(idUsuario) ? actual.filter((id) => id !== idUsuario) : [...actual, idUsuario]
    ));
  }

  const mostrarFiltroEmpleados = kpiSeleccionado?.dimensiones?.includes("empleado");
  const puedeAvanzar = paso === 0 ? Boolean(claveKpi) : paso === 1 ? Boolean(tipoGrafica) : true;
  const esUltimoPaso = paso === PASOS.length - 1;

  async function manejarEnvio(evento) {
    evento.preventDefault();
    // Demo: no pega a ninguna API. Solo demuestra el `cerrarAlEnviar` opt-in
    // de FormularioPlegable -- una promesa real (con su propio await) es lo
    // que en Paso 3 conectaria de verdad al backend.
    await new Promise((resolver) => { setTimeout(resolver, 300); });
    setPaso(0);
    setIdKpi(null);
    setTipoGrafica(null);
    setEmpleadosSeleccionados([]);
  }

  return (
    <FormularioPlegable titulo="Agregar gráfico" onSubmit={manejarEnvio} cerrarAlEnviar className="kpi-editor-demo">
      <ol className="kpi-editor-pasos" aria-label="Pasos del formulario">
        {PASOS.map((etiqueta, indice) => (
          <li key={etiqueta}>
            <button
              type="button"
              className={`kpi-editor-paso ${indice === paso ? "activo" : ""} ${indice < paso ? "completo" : ""}`}
              onClick={() => setPaso(indice)}
            >
              <span className="kpi-editor-paso-numero">{indice < paso ? <Check size={13} /> : indice + 1}</span>
              {etiqueta}
            </button>
          </li>
        ))}
      </ol>

      <div className="kpi-editor-cuerpo">
        <div className="kpi-editor-paso-contenido">
          {paso === 0 && (
            <div className="kpi-editor-seccion">
              <SelectorDeKpi
                catalogo={CATALOGO_DEMO}
                seleccionados={idKpi ? [idKpi] : []}
                multiple={false}
                onAlternar={elegirKpi}
                metaDeModulo={metaDeModulo}
              />
            </div>
          )}

          {paso === 1 && (
            <div className="kpi-editor-seccion">
              <div className="kpi-editor-tipo-grid">
                {CHART_TYPES.map(({ tipo, etiqueta, Icono, color }) => {
                  const permitido = !kpiSeleccionado || kpiSeleccionado.graficas_permitidas.includes(tipo);
                  const activo = tipoGrafica === tipo;
                  return (
                    <button
                      type="button"
                      key={tipo}
                      disabled={!permitido}
                      title={!permitido ? `${kpiSeleccionado.etiqueta} no admite esta gráfica` : etiqueta}
                      className={`kpi-editor-tipo-opcion ${activo ? "activo" : ""}`}
                      style={{ "--tinte": color }}
                      onClick={() => permitido && setTipoGrafica(tipo)}
                    >
                      <Icono size={20} aria-hidden="true" />
                      <span>{etiqueta}</span>
                      {activo && <Check size={13} className="kpi-editor-tipo-check" aria-hidden="true" />}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {paso === 2 && (
            <div className="kpi-editor-seccion">
              <div className="kpi-editor-chips">
                {PERIODOS_RELATIVOS.map((opcion) => (
                  <button
                    type="button"
                    key={opcion}
                    className={`kpi-editor-chip ${periodo === opcion ? "activo" : ""}`}
                    onClick={() => setPeriodo(opcion)}
                  >
                    {opcion}
                  </button>
                ))}
              </div>
              {periodo === "Personalizado" && (
                <div className="kpi-editor-fechas">
                  <label>Desde <input type="date" /></label>
                  <label>Hasta <input type="date" /></label>
                </div>
              )}
              <label className="kpi-editor-switch-fila">
                <span className="kpi-editor-switch">
                  <input type="checkbox" />
                  <span className="kpi-editor-switch-riel" />
                </span>
                Comparar contra otro periodo
              </label>
            </div>
          )}

          {paso === 3 && (
            <div className="kpi-editor-seccion">
              {mostrarFiltroEmpleados ? (
                <div className="kpi-editor-empleados">
                  <p className="kpi-editor-grupo-titulo">Empleados</p>
                  <div className="kpi-editor-avatares-fila">
                    {empleadosSeleccionados.length === 0 && <span className="muted">Todos</span>}
                    {empleadosSeleccionados.slice(0, 4).map((id) => {
                      const empleado = EMPLEADOS_DEMO.find((e) => e.id_user === id);
                      return (
                        <span key={id} className="kpi-editor-avatar-mini" style={{ background: colorDeAvatar(id) }}>
                          {inicialesDe(empleado?.full_name)}
                        </span>
                      );
                    })}
                    {empleadosSeleccionados.length > 4 && (
                      <span className="kpi-editor-avatar-mini kpi-editor-avatar-mas">+{empleadosSeleccionados.length - 4}</span>
                    )}
                  </div>
                  <div className="kpi-editor-empleado-lista">
                    {EMPLEADOS_DEMO.map((empleado) => {
                      const activo = empleadosSeleccionados.includes(empleado.id_user);
                      return (
                        <button
                          type="button"
                          key={empleado.id_user}
                          className={`kpi-editor-empleado-opcion ${activo ? "activo" : ""}`}
                          onClick={() => alternarEmpleado(empleado.id_user)}
                        >
                          <span className="kpi-editor-avatar-mini" style={{ background: colorDeAvatar(empleado.id_user) }}>
                            {inicialesDe(empleado.full_name)}
                          </span>
                          {empleado.full_name}
                          {activo && <Check size={14} aria-hidden="true" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <p className="muted">Este KPI no se desglosa por empleado -- no hay filtros que aplicar.</p>
              )}
            </div>
          )}
        </div>

        <aside className="kpi-editor-vista-previa">
          <p className="kpi-editor-grupo-titulo">Vista previa</p>
          {!claveKpi ? (
            <div className="kpi-skeleton kpi-skeleton-grafica" />
          ) : (
            <div className="kpi-editor-vista-previa-tarjeta">
              <strong>{kpiSeleccionado.etiqueta}</strong>
              <span className="muted">{tipoGrafica || kpiSeleccionado.grafica_default} · {periodo}</span>
            </div>
          )}
        </aside>
      </div>

      <footer className="kpi-editor-footer">
        <div className="kpi-editor-footer-nav">
          <button type="button" className="button ghost" disabled={paso === 0} onClick={() => setPaso((p) => p - 1)}>
            Atrás
          </button>
          {!esUltimoPaso ? (
            <button type="button" className="button primary" disabled={!puedeAvanzar} onClick={() => setPaso((p) => p + 1)}>
              Siguiente
            </button>
          ) : (
            <button type="submit" className="button primary" disabled={!claveKpi || !tipoGrafica}>
              Agregar gráfico
            </button>
          )}
        </div>
      </footer>
    </FormularioPlegable>
  );
}
