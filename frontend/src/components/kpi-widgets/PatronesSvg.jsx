import PropTypes from "prop-types";
import { patronDeIndice } from "../../kpi/kpiAccesibilidad";

// Los trazos de cada patron, sobre el color de la categoria. El relleno sigue siendo el color de siempre: el trazo
// (blanco, semitransparente) es el segundo canal para quien no distingue rojo de verde.
const TRAZO = { stroke: "#fff", strokeOpacity: 0.85, strokeWidth: 1.6 };
function Trazos({ patron }) {
  switch (patron) {
    case "diagonal": return <path d="M-1,9 l2,-2 M0,8 l8,-8 M7,9 l2,-2" {...TRAZO} />;
    case "diagonal_inversa": return <path d="M-1,-1 l2,2 M0,0 l8,8 M7,-1 l2,2" {...TRAZO} />;
    case "horizontal": return <path d="M0,2 h8 M0,6 h8" {...TRAZO} />;
    case "vertical": return <path d="M2,0 v8 M6,0 v8" {...TRAZO} />;
    case "cruz": return <path d="M4,0 v8 M0,4 h8" {...TRAZO} />;
    default: return <circle cx="4" cy="4" r="1.4" fill="#fff" fillOpacity="0.85" />;
  }
}
Trazos.propTypes = { patron: PropTypes.string.isRequired };

/** `<defs>` de un patron por categoria, para pegar dentro de un `<svg>`. El id de cada uno es `${idBase}-${indice}`. */
export function DefinicionDePatrones({ idBase, colores }) {
  return (
    <defs>
      {colores.map((color, indice) => (
        <pattern key={`${idBase}-${color}-${indice}`} id={`${idBase}-${indice}`} width="8" height="8" patternUnits="userSpaceOnUse">
          <rect width="8" height="8" fill={color} />
          <Trazos patron={patronDeIndice(indice)} />
        </pattern>
      ))}
    </defs>
  );
}
DefinicionDePatrones.propTypes = { idBase: PropTypes.string.isRequired, colores: PropTypes.arrayOf(PropTypes.string).isRequired };

/** Cuadrito de la leyenda con el mismo patron que la barra o la rebanada, con sus propios `<defs>`. */
export function MuestraDePatron({ idBase, color, indice }) {
  const id = `${idBase}-muestra-${indice}`;
  return (
    <svg className="kpi-preview-tooltip-dot" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true" focusable="false">
      <DefinicionDePatrones idBase={id} colores={[color]} />
      <rect width="12" height="12" rx="6" fill={`url(#${id}-0)`} />
    </svg>
  );
}
MuestraDePatron.propTypes = { idBase: PropTypes.string.isRequired, color: PropTypes.string.isRequired, indice: PropTypes.number.isRequired };
