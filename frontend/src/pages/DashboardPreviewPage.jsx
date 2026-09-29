import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import "../styles/kpi-widgets.css";
import "../styles/kpi-editor.css";
import "../styles/dashboard-preview.css";
import WidgetCard from "../components/kpi-widgets/WidgetCard";
import Skeleton from "../components/kpi-widgets/Skeleton";
import NumeroWidget from "../components/kpi-widgets/NumeroWidget";
import BarrasWidget from "../components/kpi-widgets/BarrasWidget";
import TablaWidget from "../components/kpi-widgets/TablaWidget";
import DonaWidget from "../components/kpi-widgets/DonaWidget";
import AgregarGraficoDemo from "../components/kpi-widgets/AgregarGraficoDemo";
import useReducedMotion from "../components/kpi-widgets/useReducedMotion";
import {
  ABIERTAS_VS_CERRADAS_DEMO, INCIDENCIAS_PENDIENTES_DEMO,
  INCIDENCIAS_POR_EMPLEADO_DEMO, MATERIAL_POR_ESTADO_DEMO, MATERIAL_PRESTADO_DEMO,
} from "../components/kpi-widgets/demoData";

/**
 * Vista previa AISLADA del rediseño del Dashboard de KPIs -- direccion
 * "Taller". Datos fijos, nunca pega a la API ni a la base; no reemplaza el
 * Dashboard real (Dashboard.jsx no se toca). Sirve para decidir el diseño
 * antes de conectarlo (Paso 3).
 */
export default function DashboardPreviewPage() {
  const [tema, setTema] = useState("claro");
  const [cargando, setCargando] = useState(true);
  const [empleadoResaltado, setEmpleadoResaltado] = useState(null);
  const reducirMovimiento = useReducedMotion();

  useEffect(() => {
    // Simula la primera carga real (pedir /kpi_snapshot/query tarda algo) --
    // sin esto el skeleton nunca se alcanza a ver.
    const cronometro = setTimeout(() => setCargando(false), 700);
    return () => clearTimeout(cronometro);
  }, []);

  const empleadoResaltadoNombre = empleadoResaltado
    ? INCIDENCIAS_POR_EMPLEADO_DEMO.find((fila) => fila.id_user === empleadoResaltado)?.nombreCompleto
    : null;

  return (
    <div className="dashboard-preview-page" data-theme={tema === "oscuro" ? "dark" : "light"}>
      <div className="kpi-preview-topbar">
        <div>
          <h1>Vista previa -- Dashboard de KPIs (Adser)</h1>
          <p>Datos fijos de demostración. No conectado al Dashboard real ni a la base.</p>
        </div>
        <button
          type="button"
          className="kpi-preview-theme-toggle"
          onClick={() => setTema((actual) => (actual === "claro" ? "oscuro" : "claro"))}
        >
          {tema === "claro" ? <Moon size={16} /> : <Sun size={16} />}
          {tema === "claro" ? "Modo oscuro" : "Modo claro"}
        </button>
      </div>

      <div className="kpi-preview-grid">
        <WidgetCard titulo="Incidencias pendientes hoy" color="#2a78d6" actualizado="Actualizado: hace 4 min" indice={0} reducirMovimiento={reducirMovimiento}>
          {cargando ? <Skeleton tipo="numero" /> : (
            <NumeroWidget
              valor={INCIDENCIAS_PENDIENTES_DEMO.valor}
              variacion={INCIDENCIAS_PENDIENTES_DEMO.variacion}
              direccion={INCIDENCIAS_PENDIENTES_DEMO.direccion}
              tendencia={INCIDENCIAS_PENDIENTES_DEMO.tendencia}
              animar={!reducirMovimiento}
            />
          )}
        </WidgetCard>

        <WidgetCard titulo="Abiertas vs. cerradas · últimos 90 días" color="#22b573" actualizado="Actualizado: hace 4 min" indice={1} reducirMovimiento={reducirMovimiento}>
          {cargando ? <Skeleton tipo="grafica" /> : (
            <BarrasWidget
              datos={ABIERTAS_VS_CERRADAS_DEMO}
              campoEtiqueta="semana"
              animar={!reducirMovimiento}
              series={[
                { clave: "abiertas", nombre: "Abiertas", color: "#ef6f5c" },
                { clave: "cerradas", nombre: "Cerradas", color: "#22b573" },
              ]}
            />
          )}
        </WidgetCard>

        <WidgetCard titulo="Incidencias abiertas por responsable · 30 días" color="#eb6834" actualizado="Actualizado: hace 4 min" indice={2} reducirMovimiento={reducirMovimiento}>
          {cargando ? <Skeleton tipo="grafica" /> : (
            <BarrasWidget
              datos={INCIDENCIAS_POR_EMPLEADO_DEMO}
              campoEtiqueta="empleado"
              animar={!reducirMovimiento}
              series={[{ clave: "cantidad", nombre: "Incidencias", color: "#2a78d6" }]}
              barraResaltada={INCIDENCIAS_POR_EMPLEADO_DEMO.find((f) => f.id_user === empleadoResaltado)?.empleado || null}
              onBarClick={(datosBarra) => {
                const fila = INCIDENCIAS_POR_EMPLEADO_DEMO.find((f) => f.empleado === datosBarra.empleado);
                setEmpleadoResaltado((actual) => (actual === fila?.id_user ? null : fila?.id_user ?? null));
              }}
            />
          )}
          <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>
            Clic en una barra resalta a ese empleado en la tabla de material prestado.
          </p>
        </WidgetCard>

        <WidgetCard titulo="Material prestado ahora" color="#8b6cf6" actualizado="Actualizado: en vivo" indice={3} reducirMovimiento={reducirMovimiento} className="kpi-preview-card-ancha">
          {cargando ? <Skeleton tipo="tabla" /> : (
            <TablaWidget filas={MATERIAL_PRESTADO_DEMO} resaltarResponsable={empleadoResaltadoNombre} />
          )}
        </WidgetCard>

        <WidgetCard titulo="Material por estado" color="#12b8c9" actualizado="Actualizado: hace 4 min" indice={4} reducirMovimiento={reducirMovimiento}>
          {cargando ? <Skeleton tipo="dona" /> : (
            <DonaWidget datos={MATERIAL_POR_ESTADO_DEMO} animar={!reducirMovimiento} />
          )}
        </WidgetCard>
      </div>

      <div style={{ marginTop: 24 }}>
        <AgregarGraficoDemo />
      </div>
    </div>
  );
}
