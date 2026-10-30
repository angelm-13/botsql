import PropTypes from "prop-types";
import {
  Area, AreaChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { TooltipRico } from "./BarrasWidget";

const EJE = { fontSize: 11, fill: "var(--kpi-texto-suave)" };

/** Lineas y areas comparten componente: mismo eje, mismo tooltip, mismas
 * series -- solo cambia si se rellena debajo del trazo. Una serie con
 * `punteada` (la del periodo de comparacion) se dibuja con trazo discontinuo
 * y, en area, con menos relleno: el color nunca es la unica senal. */
export default function LineaAreaWidget({
  tipo, datos, series, campoEtiqueta, animar, formatearEje, anchoEje, descripcion, etiquetasCortas,
}) {
  const Grafica = tipo === "area" ? AreaChart : LineChart;
  return (
    <div role={descripcion ? "img" : undefined} aria-label={descripcion || undefined} title={descripcion || undefined}>
    <ResponsiveContainer width="100%" height={220}>
      <Grafica data={datos} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="2 4" stroke="var(--kpi-grid)" vertical={false} />
        <XAxis
          dataKey={campoEtiqueta} tick={EJE} axisLine={false} tickLine={false}
          tickFormatter={etiquetasCortas ? (valor) => etiquetasCortas[valor] ?? valor : undefined}
        />
        <YAxis tick={EJE} axisLine={false} tickLine={false} tickFormatter={formatearEje || undefined} width={anchoEje} />
        <Tooltip content={<TooltipRico series={series} />} />
        {series.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
        {series.map((serie) => (tipo === "area" ? (
          <Area
            key={serie.clave}
            type="monotone"
            dataKey={serie.clave}
            name={serie.nombre}
            stroke={serie.color}
            fill={serie.color}
            fillOpacity={serie.opacidad ?? 0.25}
            strokeWidth={2}
            strokeDasharray={serie.punteada ? "5 4" : undefined}
            isAnimationActive={animar}
            animationDuration={700}
          />
        ) : (
          <Line
            key={serie.clave}
            type="monotone"
            dataKey={serie.clave}
            name={serie.nombre}
            stroke={serie.color}
            strokeWidth={2}
            strokeDasharray={serie.punteada ? "5 4" : undefined}
            dot={{ r: serie.punteada ? 3 : 4 }}
            isAnimationActive={animar}
            animationDuration={700}
          />
        )))}
      </Grafica>
    </ResponsiveContainer>
    </div>
  );
}

LineaAreaWidget.propTypes = {
  tipo: PropTypes.oneOf(["linea", "area"]).isRequired,
  datos: PropTypes.arrayOf(PropTypes.object).isRequired,
  series: PropTypes.arrayOf(PropTypes.shape({
    clave: PropTypes.string.isRequired,
    nombre: PropTypes.string.isRequired,
    color: PropTypes.string.isRequired,
    opacidad: PropTypes.number,
    punteada: PropTypes.bool,
    formatear: PropTypes.func,
  })).isRequired,
  campoEtiqueta: PropTypes.string.isRequired,
  animar: PropTypes.bool,
  formatearEje: PropTypes.func,
  anchoEje: PropTypes.number,
  descripcion: PropTypes.string,
  // nombre completo -> nombre corto, solo para rotular el eje (grafica por persona).
  etiquetasCortas: PropTypes.objectOf(PropTypes.string),
};

LineaAreaWidget.defaultProps = { animar: true, formatearEje: null, anchoEje: 60, descripcion: "", etiquetasCortas: null };
