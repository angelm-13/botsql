import { useMemo, useState } from "react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

// Cuantas categorias se dibujan completas antes de agrupar la cola en "Otros".
// Antes eran 8 y el pastel mostraba 7 + "Otros", asi que un "top 8" salia
// recortado. Ahora se dibuja todo lo que el usuario pidio hasta este tope.
const MAX_CATEGORIAS = 15;
const COLORES = ["#1b7a60", "#173b66", "#d97706", "#7c3aed", "#0891b2", "#be123c",
  "#65a30d", "#c2410c", "#4f46e5", "#0d9488", "#a21caf", "#475569", "#ca8a04", "#2563eb", "#db2777"];
const GRIS = "#94a3b8";

const compacto = new Intl.NumberFormat("es-MX", { notation: "compact", maximumFractionDigits: 1 });
const completo = new Intl.NumberFormat("es-MX", { maximumFractionDigits: 2 });
const fmt = (v) => (typeof v === "number" ? completo.format(v) : v == null ? "—" : String(v));

function plegarCola(filas, ejeX, ejeY) {
  if (filas.length <= MAX_CATEGORIAS) return filas;
  const cabeza = filas.slice(0, MAX_CATEGORIAS - 1);
  const cola = filas.slice(MAX_CATEGORIAS - 1);
  const suma = cola.reduce((a, f) => a + (typeof f[ejeY] === "number" ? f[ejeY] : 0), 0);
  return [...cabeza, { [ejeX]: `Otros (${cola.length})`, [ejeY]: suma }];
}

function Tabla({ widget }) {
  return (
    <div className="bi-table-wrapper">
      <table className="bi-table">
        <thead><tr>{widget.columnas.map((c) => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>
          {widget.filas.map((f, i) => (
            <tr key={i} className="bi-table-row">
              {widget.columnas.map((c) => <td key={c}>{fmt(f[c])}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Kpi({ widget, ejeY }) {
  const fila = widget.filas[0] || {};
  const valor = fila[ejeY] ?? Object.values(fila)[0];
  return (
    <div className="bi-kpi">
      <span className="bi-kpi-value">{typeof valor === "number" ? completo.format(valor) : fmt(valor)}</span>
      <span className="bi-kpi-label">{widget.visualization.metric_label || ejeY}</span>
    </div>
  );
}

function Grafica({ widget, ejeX, ejeY }) {
  const tipo = widget.visualization.chart_type;
  const datos = useMemo(
    () => (tipo === "pie" ? plegarCola(widget.filas, ejeX, ejeY) : widget.filas),
    [widget.filas, tipo, ejeX, ejeY],
  );
  // Sin animacion: en una pestana en segundo plano se queda a medio dibujar.
  const sin = { isAnimationActive: false };
  const tip = <Tooltip formatter={(v) => fmt(v)} />;
  const ejes = (
    <>
      <CartesianGrid stroke="#e2e8f0" vertical={false} />
      <XAxis dataKey={ejeX} tick={{ fontSize: 12 }} interval={0}
        angle={datos.length > 6 ? -25 : 0} textAnchor={datos.length > 6 ? "end" : "middle"}
        height={datos.length > 6 ? 70 : 30} />
      <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => compacto.format(v)} width={60} />
      {tip}
    </>
  );

  if (tipo === "pie") {
    return (
      <ResponsiveContainer width="100%" height={340}>
        <PieChart>
          <Pie data={datos} dataKey={ejeY} nameKey={ejeX} outerRadius={120} {...sin}>
            {datos.map((d, i) => (
              <Cell key={i} fill={String(d[ejeX]).startsWith("Otros (") ? GRIS : COLORES[i % COLORES.length]} />
            ))}
          </Pie>
          {tip}
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    );
  }
  if (tipo === "line") {
    return (
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={datos}>{ejes}<Line dataKey={ejeY} stroke={COLORES[0]} strokeWidth={2} dot={datos.length < 40} {...sin} /></LineChart>
      </ResponsiveContainer>
    );
  }
  if (tipo === "area") {
    return (
      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={datos}>{ejes}<Area dataKey={ejeY} stroke={COLORES[0]} fill={COLORES[0]} fillOpacity={0.2} {...sin} /></AreaChart>
      </ResponsiveContainer>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={340}>
      <BarChart data={datos}>{ejes}<Bar dataKey={ejeY} fill={COLORES[0]} radius={[4, 4, 0, 0]} {...sin} /></BarChart>
    </ResponsiveContainer>
  );
}

const MENSAJES = {
  sql_rechazado: "Esa consulta no está permitida para tu rol o no se pudo validar.",
  fallo_de_ejecucion: "No se pudo ejecutar la consulta. Intenta reformular la pregunta.",
};

export default function BiWidget({ widget }) {
  const [verTabla, setVerTabla] = useState(false);
  const vis = widget.visualization || {};

  if (!widget.ok) {
    return (
      <div className="bi-error-box">
        <span className="bi-error-icon">⚠️</span>
        <div>
          <p className="bi-error-title">{vis.title || "No se pudo resolver esta parte"}</p>
          <p className="bi-error-message">{widget.error?.mensaje || MENSAJES[widget.error?.tipo] || "Error en la consulta."}</p>
        </div>
      </div>
    );
  }

  // Respuesta de ayuda sobre el sistema (no son datos): solo texto.
  if (vis.chart_type === "text") {
    return (
      <div className="bi-widget bi-answer">
        <p className="bi-answer-text">{widget.explanation}</p>
        {vis.fuentes?.length > 0 && <p className="bi-widget-foot">Fuente: {vis.fuentes.join(" · ")}</p>}
      </div>
    );
  }

  const ejeX = vis.x_axis || widget.columnas[0] || "";
  const ejeY = vis.y_axis || widget.columnas[1] || widget.columnas[0] || "";
  const esKpi = vis.chart_type === "kpi_card";
  const esTabla = vis.chart_type === "table" || verTabla;

  return (
    <div className="bi-widget">
      <div className="bi-widget-head">
        <div>
          <h3 className="bi-widget-title">{vis.title}</h3>
          {widget.explanation && <p className="bi-widget-expl">{widget.explanation}</p>}
        </div>
        {!esKpi && vis.chart_type !== "table" && (
          <button type="button" className="button ghost" onClick={() => setVerTabla((v) => !v)}>
            {verTabla ? "Ver gráfica" : "Ver tabla"}
          </button>
        )}
      </div>
      {esKpi ? <Kpi widget={widget} ejeY={ejeY} />
        : esTabla ? <Tabla widget={widget} />
          : <Grafica widget={widget} ejeX={ejeX} ejeY={ejeY} />}
      <p className="bi-widget-foot">
        {widget.total_filas} {widget.total_filas === 1 ? "fila" : "filas"}
        {widget.truncado ? " (resultado recortado)" : ""} · {widget.ms} ms
      </p>
      {widget.advertencias?.map((a, i) => <p key={i} className="bi-widget-warn">{a}</p>)}
    </div>
  );
}
