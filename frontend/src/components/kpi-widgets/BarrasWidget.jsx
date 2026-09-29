import PropTypes from "prop-types";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

export function TooltipRico({ active, payload, label, series }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="kpi-preview-tooltip">
      <strong>{label}</strong>
      {payload.map((entrada) => {
        // Cada serie puede traer su propio formato (unidades distintas en un
        // mismo grafico); sin `formatear` se muestra el valor crudo.
        const formatear = series.find((serie) => serie.clave === entrada.dataKey)?.formatear;
        return (
          <div key={entrada.dataKey} className="kpi-preview-tooltip-fila">
            <span className="kpi-preview-tooltip-dot" style={{ background: entrada.color }} />
            <span>{entrada.name}</span>
            <strong>{formatear ? formatear(entrada.value) : entrada.value}</strong>
          </div>
        );
      })}
    </div>
  );
}

TooltipRico.propTypes = {
  active: PropTypes.bool,
  payload: PropTypes.arrayOf(PropTypes.object),
  label: PropTypes.string,
  series: PropTypes.arrayOf(PropTypes.object),
};
TooltipRico.defaultProps = { active: false, payload: null, label: "", series: [] };

/** Recharts ya trae animacion de dibujo (`isAnimationActive`) -- no hace
 * falta ninguna libreria de animacion aparte para "la grafica se dibuja al
 * aparecer". `onBarClick` es opcional: lo usa el widget de empleados para
 * resaltar la tabla de material prestado (interaccion entre widgets). */
export default function BarrasWidget({
  datos, series, campoEtiqueta, animar, onBarClick, barraResaltada, colorPorFila,
}) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={datos} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--kpi-grid)" vertical={false} />
        <XAxis dataKey={campoEtiqueta} tick={{ fontSize: 11, fill: "var(--kpi-texto-suave)" }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: "var(--kpi-texto-suave)" }} axisLine={false} tickLine={false} />
        <Tooltip content={<TooltipRico series={series} />} cursor={{ fill: "var(--kpi-hover-barra)" }} />
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
                key={fila.id ?? fila[campoEtiqueta]}
                fill={colorPorFila ? colorPorFila(fila) : serie.color}
                fillOpacity={barraResaltada && fila[campoEtiqueta] !== barraResaltada ? 0.35 : (serie.opacidad ?? 1)}
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
    opacidad: PropTypes.number,
    formatear: PropTypes.func,
  })).isRequired,
  campoEtiqueta: PropTypes.string.isRequired,
  animar: PropTypes.bool,
  onBarClick: PropTypes.func,
  barraResaltada: PropTypes.string,
  // fila -> color: para categorias fijas (estado), donde cada barra lleva SU
  // color en vez del de la serie.
  colorPorFila: PropTypes.func,
};

BarrasWidget.defaultProps = { animar: true, onBarClick: null, barraResaltada: null, colorPorFila: null };
