import PropTypes from "prop-types";

/** Bloque animado (shimmer) en vez de un spinner -- ver dashboard-preview.css
 * para el keyframe y el apagado bajo prefers-reduced-motion. */
export default function Skeleton({ tipo, className }) {
  return <div className={`kpi-skeleton kpi-skeleton-${tipo} ${className}`.trim()} aria-hidden="true" />;
}

Skeleton.propTypes = {
  tipo: PropTypes.oneOf(["numero", "grafica", "tabla", "dona"]),
  className: PropTypes.string,
};

Skeleton.defaultProps = { tipo: "grafica", className: "" };
