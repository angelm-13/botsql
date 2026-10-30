import { useMemo, useState } from "react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { AlertTriangle, BarChart2, Download, Table } from "lucide-react";

// Cuantas categorias se dibujan completas antes de agrupar la cola en "Otros".
// Antes eran 8 y el pastel mostraba 7 + "Otros", asi que un "top 8" salia
// recortado. Ahora se dibuja todo lo que el usuario pidio hasta este tope.
const MAX_CATEGORIAS = 15;
// Una tabla de 1000 filas pintadas de golpe congela la pestaña: se muestran por tandas.
const FILAS_POR_TANDA = 50;
// Mas barras que esto se dibujan en horizontal: los nombres largos caben sin girarse.
const MAX_BARRAS_VERTICALES = 6;
const COLORES = ["#1b7a60", "#173b66", "#d97706", "#7c3aed", "#0891b2", "#be123c",
  "#65a30d", "#c2410c", "#4f46e5", "#0d9488", "#a21caf", "#475569", "#ca8a04", "#2563eb", "#db2777"];
const GRIS = "#94a3b8";
const EJE = { fontSize: 12, fill: "#64748b" };

const compacto = new Intl.NumberFormat("es-MX", { notation: "compact", maximumFractionDigits: 1 });
const completo = new Intl.NumberFormat("es-MX", { maximumFractionDigits: 2 });
const REGEX_FECHA = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?/;

// El servidor manda las fechas como ISO; se muestran como las lee la gente (sin pasar por
// Date, que las movería de día según la zona horaria).
function fmtFecha(valor) {
  const m = REGEX_FECHA.exec(valor);
  if (!m) return null;
  const dia = `${m[3]}/${m[2]}/${m[1]}`;
  return m[4] && (m[4] !== "00" || m[5] !== "00") ? `${dia} ${m[4]}:${m[5]}` : dia;
}

const fmt = (v) => {
  if (typeof v === "number") return completo.format(v);
  if (v == null) return "—";
  if (typeof v === "string") return fmtFecha(v) ?? v;
  return String(v);
};
const bonito = (columna) => String(columna).replace(/_/g, " ");
const recortar = (v, n = 24) => { const s = String(v ?? ""); return s.length > n ? `${s.slice(0, n - 1)}…` : s; };

function plegarCola(filas, ejeX, ejeY) {
  if (filas.length <= MAX_CATEGORIAS) return filas;
  const cabeza = filas.slice(0, MAX_CATEGORIAS - 1);
  const cola = filas.slice(MAX_CATEGORIAS - 1);
  const suma = cola.reduce((a, f) => a + (typeof f[ejeY] === "number" ? f[ejeY] : 0), 0);
  return [...cabeza, { [ejeX]: `Otros (${cola.length})`, [ejeY]: suma }];
}

// CSV con BOM y separador de coma: Excel en español lo abre con los acentos bien.
function descargarCsv(widget) {
  const celda = (v) => {
    const s = v == null ? "" : String(v);
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lineas = [widget.columnas.map(celda).join(",")];
  for (const f of widget.filas) lineas.push(widget.columnas.map((c) => celda(f[c])).join(","));
  const url = URL.createObjectURL(new Blob([`﻿${lineas.join("\r\n")}`], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  const nombre = (widget.visualization?.title || "consulta").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  a.href = url;
  a.download = `${nombre || "consulta"}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function Tabla({ widget }) {
  const [limite, setLimite] = useState(FILAS_POR_TANDA);
  const { columnas, filas } = widget;
  // Una columna es numerica si su primer valor presente lo es: se alinea a la derecha.
  const numericas = useMemo(() => new Set(columnas.filter((c) => {
    const f = filas.find((x) => x[c] != null);
    return f && typeof f[c] === "number";
  })), [columnas, filas]);
  const visibles = filas.slice(0, limite);
  const restan = filas.length - visibles.length;

  return (
    <>
      <div className="bi-table-wrapper">
        <table className="bi-table">
          <thead><tr>{columnas.map((c) => <th key={c} className={numericas.has(c) ? "num" : undefined}>{bonito(c)}</th>)}</tr></thead>
          <tbody>
            {visibles.map((f, i) => (
              <tr key={i}>
                {columnas.map((c) => (
                  <td key={c} className={[numericas.has(c) ? "num" : "", f[c] == null ? "nil" : ""].join(" ").trim() || undefined}>{fmt(f[c])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {restan > 0 && (
        <div className="bi-more">
          <button type="button" className="bi-btn sm" onClick={() => setLimite((l) => l + FILAS_POR_TANDA)}>
            Mostrar {Math.min(FILAS_POR_TANDA, restan)} más · quedan {restan}
          </button>
        </div>
      )}
    </>
  );
}

function Kpi({ widget, ejeY }) {
  const fila = widget.filas[0] || {};
  const valor = fila[ejeY] ?? Object.values(fila)[0];
  return (
    <div className="bi-kpi">
      <span className="bi-kpi-value">{fmt(valor)}</span>
      <span className="bi-kpi-label">{widget.visualization.metric_label || bonito(ejeY)}</span>
    </div>
  );
}

function Punta({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const p = payload[0];
  return (
    <div className="bi-tip">
      <strong>{fmt(label ?? p.name)}</strong>
      <span>{fmt(p.value)}</span>
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
  const tip = <Tooltip content={<Punta />} cursor={{ fill: "rgba(27,122,96,.07)" }} />;
  const rejilla = <CartesianGrid stroke="#e8eef5" strokeDasharray="3 4" vertical={false} />;
  const degradado = (
    <defs>
      <linearGradient id="bi-grad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#23a07e" /><stop offset="100%" stopColor="#1b7a60" />
      </linearGradient>
      <linearGradient id="bi-grad-h" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stopColor="#1b7a60" /><stop offset="100%" stopColor="#23a07e" />
      </linearGradient>
      <linearGradient id="bi-grad-area" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#1b7a60" stopOpacity={0.35} /><stop offset="100%" stopColor="#1b7a60" stopOpacity={0.02} />
      </linearGradient>
    </defs>
  );
  const ejes = (
    <>
      {rejilla}
      <XAxis dataKey={ejeX} tick={EJE} tickLine={false} axisLine={{ stroke: "#e2e8f0" }} interval={datos.length > 24 ? "preserveStartEnd" : 0}
        tickFormatter={(v) => recortar(fmt(v), 14)}
        angle={datos.length > 6 ? -25 : 0} textAnchor={datos.length > 6 ? "end" : "middle"}
        height={datos.length > 6 ? 70 : 30} />
      <YAxis tick={EJE} tickLine={false} axisLine={false} tickFormatter={(v) => compacto.format(v)} width={56} />
      {tip}
    </>
  );

  if (tipo === "pie") {
    return (
      <ResponsiveContainer width="100%" height={340}>
        <PieChart>
          <Pie data={datos} dataKey={ejeY} nameKey={ejeX} innerRadius={64} outerRadius={118} paddingAngle={2} stroke="#fff" strokeWidth={2} {...sin}>
            {datos.map((d, i) => (
              <Cell key={i} fill={String(d[ejeX]).startsWith("Otros (") ? GRIS : COLORES[i % COLORES.length]} />
            ))}
          </Pie>
          {tip}
          <Legend iconType="circle" wrapperStyle={{ fontSize: 12.5 }} />
        </PieChart>
      </ResponsiveContainer>
    );
  }
  if (tipo === "line") {
    return (
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={datos} margin={{ top: 8, right: 16 }}>{ejes}
          <Line dataKey={ejeY} stroke={COLORES[0]} strokeWidth={2.5} dot={datos.length < 40 ? { r: 3, strokeWidth: 2, fill: "#fff" } : false} activeDot={{ r: 5 }} {...sin} />
        </LineChart>
      </ResponsiveContainer>
    );
  }
  if (tipo === "area") {
    return (
      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={datos} margin={{ top: 8, right: 16 }}>{degradado}{ejes}
          <Area dataKey={ejeY} stroke={COLORES[0]} strokeWidth={2.5} fill="url(#bi-grad-area)" {...sin} />
        </AreaChart>
      </ResponsiveContainer>
    );
  }
  if (datos.length > MAX_BARRAS_VERTICALES) {
    return (
      <ResponsiveContainer width="100%" height={Math.min(720, Math.max(300, datos.length * 36 + 40))}>
        <BarChart data={datos} layout="vertical" margin={{ top: 4, right: 24, left: 4 }}>
          {degradado}
          <CartesianGrid stroke="#e8eef5" strokeDasharray="3 4" horizontal={false} />
          <XAxis type="number" tick={EJE} tickLine={false} axisLine={false} tickFormatter={(v) => compacto.format(v)} />
          <YAxis type="category" dataKey={ejeX} tick={EJE} tickLine={false} axisLine={false} width={150} interval={0}
            tickFormatter={(v) => recortar(fmt(v), 24)} />
          {tip}
          <Bar dataKey={ejeY} fill="url(#bi-grad-h)" radius={[0, 7, 7, 0]} barSize={20} {...sin} />
        </BarChart>
      </ResponsiveContainer>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={340}>
      <BarChart data={datos} margin={{ top: 8, right: 16 }}>{degradado}{ejes}
        <Bar dataKey={ejeY} fill="url(#bi-grad)" radius={[7, 7, 0, 0]} maxBarSize={64} {...sin} />
      </BarChart>
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
      <div className="bi-error-box" role="alert">
        <AlertTriangle size={20} className="bi-error-icon" aria-hidden="true" />
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
  const hayFilas = widget.filas.length > 0;

  return (
    <div className="bi-widget">
      <div className="bi-widget-head">
        <div>
          <h3 className="bi-widget-title">{vis.title}</h3>
          {widget.explanation && widget.explanation !== vis.title && <p className="bi-widget-expl">{widget.explanation}</p>}
        </div>
        <div className="bi-widget-tools">
          {!esKpi && vis.chart_type !== "table" && (
            <button type="button" className="bi-btn sm" onClick={() => setVerTabla((v) => !v)}>
              {verTabla ? <><BarChart2 size={15} aria-hidden="true" /> Ver gráfica</> : <><Table size={15} aria-hidden="true" /> Ver tabla</>}
            </button>
          )}
          {hayFilas && !esKpi && (
            <button type="button" className="bi-btn sm" onClick={() => descargarCsv(widget)} title="Descargar los datos en CSV">
              <Download size={15} aria-hidden="true" /> CSV
            </button>
          )}
        </div>
      </div>
      {esKpi ? <Kpi widget={widget} ejeY={ejeY} />
        : !hayFilas ? <p className="bi-widget-expl">La consulta no devolvió resultados.</p>
          : esTabla ? <Tabla widget={widget} />
            : <Grafica widget={widget} ejeX={ejeX} ejeY={ejeY} />}
      <p className="bi-widget-foot">
        <span>{widget.total_filas} {widget.total_filas === 1 ? "fila" : "filas"}{widget.truncado ? " (resultado recortado)" : ""}</span>
        <span>{widget.ms} ms en la base de datos</span>
      </p>
      {widget.advertencias?.map((a, i) => <p key={i} className="bi-widget-warn">{a}</p>)}
    </div>
  );
}
