import PropTypes from "prop-types";
import { patronesDeRelleno } from "./patronesDeRelleno";

/** Cuadrito de la leyenda con el mismo patron que la barra o la rebanada, con sus propios `<defs>`. */
export function MuestraDePatron({ idBase, color, indice }) {
  const id = `${idBase}-muestra-${indice}`;
  return (
    <svg className="kpi-preview-tooltip-dot" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true" focusable="false">
      <defs>{patronesDeRelleno(id, [color])}</defs>
      <rect width="12" height="12" rx="6" fill={`url(#${id}-0)`} />
    </svg>
  );
}
MuestraDePatron.propTypes = { idBase: PropTypes.string.isRequired, color: PropTypes.string.isRequired, indice: PropTypes.number.isRequired };
