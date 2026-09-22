/**
 * El componente reutilizable: recibe un widget y lo dibuja segun `chart_type`.
 *
 * Es el unico lugar del frontend que sabe de Recharts. Cambiar a Chart.js o a
 * D3 seria reescribir este archivo y nada mas -- `DashboardGrid` y `BIChat`
 * solo le pasan widgets.
 *
 * Reglas de dibujo que estan aqui a proposito, no por gusto
 * ---------------------------------------------------------
 *  * **Un solo eje Y.** Nunca dos escalas en la misma grafica: es el error mas
 *    comun de los tableros y hace que dos series parezcan cruzarse cuando no
 *    tienen nada que ver. El contrato del backend da un `y_axis`, uno solo.
 *  * **Los tonos no se ciclan.** Mas de ocho categorias no vuelven a empezar
 *    por el color uno: las que sobran se agrupan en "Otros", en gris. Dos
 *    rebanadas del mismo color en un pastel son una mentira, no un adorno.
 *  * **Leyenda solo cuando hay identidades que distinguir.** Una barra por
 *    categoria con un solo valor no necesita caja de leyenda -- el eje X ya
 *    nombra cada barra. El pastel si, porque ahi el color ES la identidad.
 *  * **Rejilla y ejes recesivos**, marcas delgadas, y ningun numero impreso
 *    sobre cada punto: lo que se lee es la forma, y el dato exacto lo da el
 *    tooltip o la tabla.
 *  * **Toda grafica trae su tabla a un clic.** Es la vista accesible y ademas
 *    la "via de relieve" que la paleta exige en modo claro.
 */

import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { Fila, Widget } from "../types";
import { formatoCompacto, formatoCompleto, usarPaleta } from "../theme";
import { DataTable } from "./DataTable";
import { KPICard } from "./KPICard";

const MAX_CATEGORIAS = 8;

/**
 * Sin animacion de entrada, a proposito.
 *
 * En un tablero no aporta informacion, y si introduce un modo de falla real:
 * la animacion avanza con `requestAnimationFrame`, que el navegador frena en
 * una pestana que no se esta dibujando. Una grafica que se anima mientras esta
 * en segundo plano se queda congelada a medio camino y aparece con las barras
 * a un decimo de su altura -- con los ejes correctos, que es lo que hace el
 * error dificil de ver. Verificado en este mismo componente antes de apagarla.
 */
const SIN_ANIMACION = { isAnimationActive: false } as const;

/** Agrupa la cola larga en "Otros" en vez de reciclar tonos. */
function plegarCola(filas: Fila[], ejeX: string, ejeY: string): Fila[] {
  if (filas.length <= MAX_CATEGORIAS) return filas;

  const cabeza = filas.slice(0, MAX_CATEGORIAS - 1);
  const cola = filas.slice(MAX_CATEGORIAS - 1);
  const suma = cola.reduce((acc, f) => {
    const v = f[ejeY];
    return acc + (typeof v === "number" ? v : 0);
  }, 0);

  return [...cabeza, { [ejeX]: `Otros (${cola.length})`, [ejeY]: suma } as Fila];
}

function TooltipPropio({
  active,
  payload,
  label,
  etiquetaY,
}: {
  active?: boolean;
  payload?: { value: number | string; name?: string }[];
  label?: string | number;
  etiquetaY: string;
}) {
  const { tokens } = usarPaleta();
  if (!active || !payload?.length) return null;

  return (
    <div
      className="rounded-lg border px-3 py-2 text-sm shadow-sm"
      style={{ backgroundColor: tokens.superficie, borderColor: tokens.borde }}
    >
      <p className="font-medium" style={{ color: tokens.tintaPrimaria }}>
        {String(label ?? payload[0].name ?? "")}
      </p>
      <p className="tabular-nums" style={{ color: tokens.tintaSecundaria }}>
        {etiquetaY}: {formatoCompleto(payload[0].value)}
      </p>
    </div>
  );
}

export function DynamicChartViewer({ widget }: { widget: Widget }) {
  const { series, otros, tokens } = usarPaleta();
  const [verTabla, setVerTabla] = useState(false);

  const vis = widget.visualization;
  const ejeX = vis.x_axis || widget.columnas[0] || "";
  const ejeY = vis.y_axis || widget.columnas[1] || widget.columnas[0] || "";

  const datos = useMemo(
    () => (vis.chart_type === "pie" ? plegarCola(widget.filas, ejeX, ejeY) : widget.filas),
    [widget.filas, vis.chart_type, ejeX, ejeY],
  );

  if (!widget.ok) return <PanelDeError widget={widget} />;
  if (vis.chart_type === "kpi_card") return <KPICard widget={widget} />;

  const esTabla = vis.chart_type === "table" || verTabla;

  const ejes = (
    <>
      <CartesianGrid stroke={tokens.rejilla} strokeDasharray="0" vertical={false} />
      <XAxis
        dataKey={ejeX}
        tick={{ fill: tokens.tintaSecundaria, fontSize: 12 }}
        tickLine={false}
        axisLine={{ stroke: tokens.rejilla }}
        interval="preserveStartEnd"
      />
      <YAxis
        tickFormatter={formatoCompacto}
        tick={{ fill: tokens.tintaSecundaria, fontSize: 12 }}
        tickLine={false}
        axisLine={false}
        width={56}
      />
      <Tooltip
        content={<TooltipPropio etiquetaY={vis.metric_label || ejeY} />}
        cursor={{ fill: tokens.rejilla, fillOpacity: 0.45 }}
      />
    </>
  );

  return (
    <figure
      className="flex h-full flex-col rounded-xl border p-4"
      style={{ borderColor: tokens.borde, backgroundColor: tokens.superficie }}
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <figcaption>
          <h3 className="text-sm font-semibold" style={{ color: tokens.tintaPrimaria }}>
            {vis.title || widget.explanation || "Resultado"}
          </h3>
          {widget.explanation && vis.title && (
            <p className="mt-0.5 text-xs" style={{ color: tokens.tintaSecundaria }}>
              {widget.explanation}
            </p>
          )}
        </figcaption>

        {vis.chart_type !== "table" && (
          <button
            type="button"
            onClick={() => setVerTabla((v) => !v)}
            className="shrink-0 rounded-md border px-2 py-1 text-xs"
            style={{ borderColor: tokens.borde, color: tokens.tintaSecundaria }}
            aria-pressed={verTabla}
          >
            {verTabla ? "Ver gráfica" : "Ver tabla"}
          </button>
        )}
      </div>

      <div className="min-h-0 flex-1">
        {esTabla ? (
          <DataTable columnas={widget.columnas} filas={widget.filas} />
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            {vis.chart_type === "bar" ? (
              <BarChart data={datos} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                {ejes}
                {/* Extremo redondeado de 4px anclado a la linea base, y 2px de
                    separacion entre barras: la marca se lee, no se emborrona. */}
                <Bar dataKey={ejeY} fill={series[0]} radius={[4, 4, 0, 0]} maxBarSize={44} {...SIN_ANIMACION} />
              </BarChart>
            ) : vis.chart_type === "line" ? (
              <LineChart data={datos} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                {ejes}
                <Line
                  type="monotone"
                  dataKey={ejeY}
                  stroke={series[0]}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, strokeWidth: 2, stroke: tokens.superficie }}
                  {...SIN_ANIMACION}
                />
              </LineChart>
            ) : vis.chart_type === "area" ? (
              <AreaChart data={datos} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                {ejes}
                <Area
                  type="monotone"
                  dataKey={ejeY}
                  stroke={series[0]}
                  strokeWidth={2}
                  fill={series[0]}
                  fillOpacity={0.15}
                  {...SIN_ANIMACION}
                />
              </AreaChart>
            ) : (
              <PieChart>
                <Tooltip content={<TooltipPropio etiquetaY={vis.metric_label || ejeY} />} />
                <Legend
                  verticalAlign="bottom"
                  height={36}
                  formatter={(v) => (
                    <span style={{ color: tokens.tintaSecundaria, fontSize: 12 }}>{v}</span>
                  )}
                />
                <Pie
                  data={datos}
                  dataKey={ejeY}
                  nameKey={ejeX}
                  innerRadius="45%"
                  outerRadius="78%"
                  paddingAngle={1}
                  stroke={tokens.superficie}
                  strokeWidth={2}
                  {...SIN_ANIMACION}
                >
                  {datos.map((fila, i) => (
                    <Cell
                      key={i}
                      fill={
                        String(fila[ejeX]).startsWith("Otros")
                          ? otros
                          : series[i % series.length]
                      }
                    />
                  ))}
                </Pie>
              </PieChart>
            )}
          </ResponsiveContainer>
        )}
      </div>

      <PieDelPie widget={widget} />
    </figure>
  );
}

/** El pie de la figura: avisos, conteo y el SQL que de verdad se ejecuto. */
function PieDelPie({ widget }: { widget: Widget }) {
  const { tokens } = usarPaleta();

  return (
    <div className="mt-3 space-y-1.5 text-xs" style={{ color: tokens.tintaTenue }}>
      {widget.advertencias.map((a, i) => (
        <p key={i}>⚠ {a}</p>
      ))}
      <div className="flex items-center justify-between gap-2">
        <span>
          {widget.total_filas} fila{widget.total_filas === 1 ? "" : "s"}
          {widget.truncado ? " (recortado)" : ""} · {widget.ms} ms
        </span>
        <details className="min-w-0">
          <summary className="cursor-pointer select-none">Ver SQL</summary>
          <pre
            className="mt-2 max-h-40 overflow-auto rounded-md border p-2 text-[11px] leading-relaxed whitespace-pre-wrap"
            style={{ borderColor: tokens.borde, color: tokens.tintaSecundaria }}
          >
            {widget.sql}
          </pre>
        </details>
      </div>
    </div>
  );
}

/**
 * Un widget rechazado o roto.
 *
 * Se muestra el motivo y el SQL que se intento. Un tablero que solo dice "no
 * se pudo" obliga a adivinar; con el motivo -- `relacion_no_permitida`,
 * `columna_sensible` -- se entiende si fue una barrera de seguridad o un error
 * del modelo, que son cosas muy distintas.
 */
function PanelDeError({ widget }: { widget: Widget }) {
  const { tokens } = usarPaleta();
  const e = widget.error;

  return (
    <div
      className="flex h-full flex-col rounded-xl border border-dashed p-4"
      style={{ borderColor: tokens.borde }}
    >
      <h3 className="text-sm font-semibold" style={{ color: tokens.tintaPrimaria }}>
        {widget.visualization.title || "Esta consulta no se ejecutó"}
      </h3>
      <p className="mt-1 text-xs" style={{ color: tokens.tintaSecundaria }}>
        {e?.tipo === "sql_rechazado"
          ? `Bloqueada por la revisión de seguridad: ${e.motivo}`
          : (e?.mensaje ?? "Error desconocido.")}
        {e?.detalle ? ` (${e.detalle})` : ""}
      </p>
      {widget.sql && (
        <details className="mt-3 text-xs" style={{ color: tokens.tintaTenue }}>
          <summary className="cursor-pointer select-none">SQL que se intentó</summary>
          <pre
            className="mt-2 max-h-40 overflow-auto rounded-md border p-2 text-[11px] whitespace-pre-wrap"
            style={{ borderColor: tokens.borde }}
          >
            {widget.sql}
          </pre>
        </details>
      )}
    </div>
  );
}
