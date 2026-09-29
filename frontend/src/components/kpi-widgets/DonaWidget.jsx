import { useState } from "react";
import PropTypes from "prop-types";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

function TooltipDona({ active, payload, formatearValor }) {
  if (!active || !payload || !payload.length) return null;
  const dato = payload[0];
  return (
    <div className="kpi-preview-tooltip">
      <span className="kpi-preview-tooltip-dot" style={{ background: dato.payload.color }} />
      <strong>{dato.name}</strong>: {formatearValor(dato.value)}
    </div>
  );
}
TooltipDona.propTypes = {
  active: PropTypes.bool,
  payload: PropTypes.arrayOf(PropTypes.object),
  formatearValor: PropTypes.func.isRequired,
};
TooltipDona.defaultProps = { active: false, payload: null };

/** Categorias fijas -- nunca "Otros" aqui, porque no aplica un umbral de
 * dimension abierta a una dona de estado con catalogo cerrado. El color
 * nunca es la unica senal: la leyenda siempre trae el nombre de la
 * categoria en texto junto al punto de color. */
export default function DonaWidget({ datos, animar, formatearValor }) {
  const [resaltado, setResaltado] = useState(null);

  return (
    <div className="kpi-preview-dona-wrap">
      <ResponsiveContainer width="100%" height={190}>
        <PieChart>
          <Pie
            data={datos}
            dataKey="valor"
            nameKey="categoria"
            innerRadius={50}
            outerRadius={76}
            paddingAngle={2}
            isAnimationActive={animar}
            animationDuration={700}
            onMouseEnter={(_, indice) => setResaltado(indice)}
            onMouseLeave={() => setResaltado(null)}
          >
            {datos.map((entrada, indice) => (
              <Cell
                key={entrada.categoria}
                fill={entrada.color}
                fillOpacity={resaltado === null || resaltado === indice ? 1 : 0.35}
              />
            ))}
          </Pie>
          <Tooltip content={<TooltipDona formatearValor={formatearValor} />} />
        </PieChart>
      </ResponsiveContainer>
      <ul className="kpi-preview-dona-leyenda">
        {datos.map((entrada, indice) => (
          <li
            key={entrada.categoria}
            className={resaltado !== null && resaltado !== indice ? "kpi-preview-leyenda-atenuada" : ""}
            onMouseEnter={() => setResaltado(indice)}
            onMouseLeave={() => setResaltado(null)}
          >
            <span className="kpi-preview-tooltip-dot" style={{ background: entrada.color }} />
            <span>{entrada.categoria}</span>
            <strong>{formatearValor(entrada.valor)}</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}

DonaWidget.propTypes = {
  datos: PropTypes.arrayOf(PropTypes.shape({
    categoria: PropTypes.string.isRequired,
    valor: PropTypes.number.isRequired,
    color: PropTypes.string.isRequired,
  })).isRequired,
  animar: PropTypes.bool,
  formatearValor: PropTypes.func,
};
DonaWidget.defaultProps = { animar: true, formatearValor: (valor) => String(valor) };
