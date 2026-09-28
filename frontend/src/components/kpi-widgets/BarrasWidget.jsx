import PropTypes from "prop-types";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

function TooltipRico({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="kpi-preview-tooltip">
      <strong>{label}</strong>
      {payload.map((entrada) => (
        <div key={entrada.dataKey} className="kpi-preview-tooltip-fila">
          <span className="kpi-preview-tooltip-dot" style={{ background: entrada.color }} />
          <span>{entrada.name}</span>
          <strong>{entrada.value}</strong>
        </div>
      ))}
    </div>
  );
}

TooltipRico.propTypes = {
  active: PropTypes.bool,
  payload: PropTypes.arrayOf(PropTypes.object),
  label: PropTypes.string,
};
TooltipRico.defaultProps = { active: false, payload: null, label: "" };

/** Recharts ya trae animacion de dibujo (`isAnimationActive`) -- no hace
 * falta ninguna libreria de animacion aparte para "la grafica se dibuja al
 * aparecer". `onBarClick` es opcional: lo usa el widget de empleados para
 * resaltar la tabla de material prestado (interaccion entre widgets). */
export default function BarrasWidget({ datos, series, campoEtiqueta, animar, onBarClick, barraResaltada }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={datos} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--kpi-grid)" vertical={false} />
        <XAxis dataKey={campoEtiqueta} tick={{ fontSize: 11, fill: "var(--kpi-texto-suave)" }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: "var(--kpi-texto-suave)" }} axisLine={false} tickLine={false} allowDecimals={false} />
        <Tooltip content={<TooltipRico />} cursor={{ fill: "var(--kpi-hover-barra)" }} />
        {series.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
        {series.map((serie) => (
          <Bar
            key={serie.clave}
            dataKey={serie.clave}
            name={serie.nombre}
            fill={serie.color}
            radius={[4, 4, 0, 0]}
            isAnimationActive={animar}
            animationDuration={700}
            cursor={onBarClick ? "pointer" : "default"}
            onClick={onBarClick}
          >
            {datos.map((fila) => (
              <Cell
                key={fila[campoEtiqueta]}
                fillOpacity={barraResaltada && fila[campoEtiqueta] !== barraResaltada ? 0.35 : 1}
              />
            ))}
          </Bar>
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

BarrasWidget.propTypes = {
  datos: PropTypes.arrayOf(PropTypes.object).isRequired,
  series: PropTypes.arrayOf(PropTypes.shape({
    clave: PropTypes.string.isRequired,
    nombre: PropTypes.string.isRequired,
    color: PropTypes.string.isRequired,
  })).isRequired,
  campoEtiqueta: PropTypes.string.isRequired,
  animar: PropTypes.bool,
  onBarClick: PropTypes.func,
  barraResaltada: PropTypes.string,
};

BarrasWidget.defaultProps = { animar: true, onBarClick: null, barraResaltada: null };
