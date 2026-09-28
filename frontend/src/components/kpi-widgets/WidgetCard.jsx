import PropTypes from "prop-types";

/** La tarjeta comun a los 5 widgets: header + cuerpo + entrada escalonada
 * (el orden lo fija `indice`, consumido por CSS via `--orden-entrada`) +
 * elevacion suave al pasar el mouse. Nunca las anima si `reducirMovimiento`
 * viene en true -- ver dashboard-preview.css, que ademas ya respeta
 * `prefers-reduced-motion` por su cuenta como respaldo. */
export default function WidgetCard({ titulo, actualizado, indice, reducirMovimiento, children, className }) {
  return (
    <article
      className={`kpi-preview-card ${reducirMovimiento ? "sin-movimiento" : ""} ${className}`.trim()}
      style={{ "--orden-entrada": indice }}
    >
      <header className="kpi-preview-card-header">
        <h3>{titulo}</h3>
        {actualizado && <span className="kpi-preview-updated">{actualizado}</span>}
      </header>
      <div className="kpi-preview-card-body">{children}</div>
    </article>
  );
}

WidgetCard.propTypes = {
  titulo: PropTypes.string.isRequired,
  actualizado: PropTypes.string,
  indice: PropTypes.number,
  reducirMovimiento: PropTypes.bool,
  children: PropTypes.node,
  className: PropTypes.string,
};

WidgetCard.defaultProps = {
  actualizado: null,
  indice: 0,
  reducirMovimiento: false,
  children: null,
  className: "",
};
