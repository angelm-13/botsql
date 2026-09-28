import PropTypes from "prop-types";
import { ArrowDown, ArrowUp, Minus } from "lucide-react";
import useCountUp from "./useCountUp";

function Sparkline({ valores, color }) {
  if (!valores || valores.length < 2) return null;
  const minimo = Math.min(...valores);
  const maximo = Math.max(...valores);
  const rango = maximo - minimo || 1;
  const ancho = 96;
  const alto = 28;
  const puntos = valores
    .map((valor, indice) => {
      const x = (indice / (valores.length - 1)) * ancho;
      const y = alto - ((valor - minimo) / rango) * alto;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg className="kpi-preview-sparkline" width={ancho} height={alto} viewBox={`0 0 ${ancho} ${alto}`} aria-hidden="true">
      <polyline points={puntos} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

Sparkline.propTypes = { valores: PropTypes.arrayOf(PropTypes.number), color: PropTypes.string.isRequired };
Sparkline.defaultProps = { valores: null };

/** El color de la flecha NUNCA es la unica senal: siempre va con un icono
 * (ArrowUp/ArrowDown/Minus) y con el texto de la variacion -- ver el pedido
 * explicito de no depender solo del color. */
export default function NumeroWidget({ valor, variacion, direccion, tendencia, animar }) {
  const valorAnimado = useCountUp(valor, { activo: animar });
  const entero = Math.round(valorAnimado);

  let colorDelta = "var(--kpi-neutral)";
  let IconoDelta = Minus;
  let leyenda = "sin cambio";
  if (variacion != null && variacion !== 0) {
    const subio = variacion > 0;
    const esBueno = direccion === "alto_es_mejor" ? subio : direccion === "bajo_es_mejor" ? !subio : null;
    colorDelta = esBueno === null ? "var(--kpi-neutral)" : esBueno ? "var(--kpi-bueno)" : "var(--kpi-malo)";
    IconoDelta = subio ? ArrowUp : ArrowDown;
    leyenda = `${Math.abs(variacion)} vs. hace 30 días`;
  }

  return (
    <div className="kpi-preview-numero">
      <div className="kpi-preview-numero-fila">
        <strong className="kpi-preview-numero-valor">{entero}</strong>
        <Sparkline valores={tendencia} color={colorDelta} />
      </div>
      <p className="kpi-preview-delta" style={{ color: colorDelta }}>
        <IconoDelta size={14} aria-hidden="true" />
        <span>{leyenda}</span>
      </p>
    </div>
  );
}

NumeroWidget.propTypes = {
  valor: PropTypes.number.isRequired,
  variacion: PropTypes.number,
  direccion: PropTypes.oneOf(["alto_es_mejor", "bajo_es_mejor", "neutral"]),
  tendencia: PropTypes.arrayOf(PropTypes.number),
  animar: PropTypes.bool,
};

NumeroWidget.defaultProps = { variacion: null, direccion: "neutral", tendencia: null, animar: true };
