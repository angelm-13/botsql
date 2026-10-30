import { useId, useState } from "react";
import PropTypes from "prop-types";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { DefinicionDePatrones, MuestraDePatron } from "./PatronesSvg";
import { rellenoConPatron } from "../../kpi/kpiAccesibilidad";

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
export default function DonaWidget({ datos, animar, formatearValor, conPatrones, descripcion, totalCentro }) {
  const [resaltado, setResaltado] = useState(null);
  const idBase = useId().replace(/:/g, "");

  return (
    <div className="kpi-preview-dona-wrap" role={descripcion ? "img" : undefined} aria-label={descripcion || undefined} title={descripcion || undefined}>
      <div className="kpi-preview-dona-grafica">
      <ResponsiveContainer width="100%" height={190}>
        <PieChart>
          {conPatrones && <DefinicionDePatrones idBase={idBase} colores={datos.map((entrada) => entrada.color)} />}
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
                fill={conPatrones ? rellenoConPatron(idBase, indice) : entrada.color}
                fillOpacity={resaltado === null || resaltado === indice ? 1 : 0.35}
              />
            ))}
          </Pie>
          <Tooltip content={<TooltipDona formatearValor={formatearValor} />} />
        </PieChart>
      </ResponsiveContainer>
      {totalCentro && (
        <div className="kpi-preview-dona-total" aria-hidden="true">
          <strong style={{ fontSize: `${totalCentro.fuente}px` }}>{totalCentro.texto}</strong>
          <span>{totalCentro.detalle}</span>
        </div>
      )}
      </div>
      <ul className="kpi-preview-dona-leyenda">
        {datos.map((entrada, indice) => (
          <li
            key={entrada.categoria}
            className={resaltado !== null && resaltado !== indice ? "kpi-preview-leyenda-atenuada" : ""}
            onMouseEnter={() => setResaltado(indice)}
            onMouseLeave={() => setResaltado(null)}
          >
            {conPatrones
              ? <MuestraDePatron idBase={idBase} color={entrada.color} indice={indice} />
              : <span className="kpi-preview-tooltip-dot" style={{ background: entrada.color }} />}
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
  // Un patron por rebanada y en la leyenda (segundo canal ademas del color).
  conPatrones: PropTypes.bool,
  descripcion: PropTypes.string,
  // El total al centro (`totalCentroDeDona`): solo cuando las rebanadas suman un total con sentido.
  totalCentro: PropTypes.shape({ texto: PropTypes.string.isRequired, detalle: PropTypes.string.isRequired, fuente: PropTypes.number.isRequired }),
};
DonaWidget.defaultProps = { animar: true, formatearValor: (valor) => String(valor), conPatrones: false, descripcion: "", totalCentro: null };
