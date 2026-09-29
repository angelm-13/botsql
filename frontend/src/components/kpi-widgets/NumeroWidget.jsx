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
 * explicito de no depender solo del color.
 *
 * Props opcionales pensadas para el Dashboard real (la vista previa no las
 * usa y se ve igual que siempre): `formatear` (valor con unidad),
 * `variacionTexto` (variacion ya formateada, con su porcentaje),
 * `leyendaVariacion`, `textoSinVariacion`, `icono`/`colorAcento` (insignia
 * del modulo junto al valor) y `pistaRango` (lo que va a la derecha cuando
 * no hay tendencia que dibujar -- nunca se deja ese lado vacio). */
export default function NumeroWidget({
  valor, variacion, direccion, tendencia, animar, formatear, variacionTexto,
  leyendaVariacion, textoSinVariacion, icono: Icono, colorAcento, pistaRango,
}) {
  const valorAnimado = useCountUp(valor, { activo: animar });
  const mostrado = formatear ? formatear(valorAnimado) : String(Math.round(valorAnimado));

  let colorDelta = "var(--kpi-neutral)";
  let IconoDelta = Minus;
  let leyenda = textoSinVariacion || "sin cambio";
  if (variacion != null) {
    const subio = variacion > 0;
    if (variacion !== 0) {
      const esBueno = direccion === "alto_es_mejor" ? subio : direccion === "bajo_es_mejor" ? !subio : null;
      colorDelta = esBueno === null ? "var(--kpi-neutral)" : esBueno ? "var(--kpi-bueno)" : "var(--kpi-malo)";
      IconoDelta = subio ? ArrowUp : ArrowDown;
    }
    leyenda = `${variacionTexto ?? Math.abs(variacion)} ${leyendaVariacion}`;
  }

  const hayTendencia = Array.isArray(tendencia) && tendencia.length >= 2;

  return (
    <div className="kpi-preview-numero">
      <div className="kpi-preview-numero-fila">
        <div className="kpi-preview-numero-valor-caja">
          {Icono && (
            <span className="kpi-preview-numero-insignia" style={{ background: colorAcento }}>
              <Icono size={16} color="#fff" aria-hidden="true" />
            </span>
          )}
          <strong className="kpi-preview-numero-valor">{mostrado}</strong>
        </div>
        {hayTendencia ? (
          <Sparkline valores={tendencia} color={colorAcento || colorDelta} />
        ) : (
          pistaRango && <span className="kpi-preview-numero-pista">{pistaRango}</span>
        )}
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
  formatear: PropTypes.func,
  variacionTexto: PropTypes.string,
  leyendaVariacion: PropTypes.string,
  textoSinVariacion: PropTypes.string,
  icono: PropTypes.elementType,
  colorAcento: PropTypes.string,
  pistaRango: PropTypes.string,
};

NumeroWidget.defaultProps = {
  variacion: null,
  direccion: "neutral",
  tendencia: null,
  animar: true,
  formatear: null,
  variacionTexto: null,
  leyendaVariacion: "vs. hace 30 días",
  textoSinVariacion: null,
  icono: null,
  colorAcento: null,
  pistaRango: null,
};
