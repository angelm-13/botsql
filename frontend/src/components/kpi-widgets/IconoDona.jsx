import PropTypes from "prop-types";

// Icono del tipo "Dona": un anillo con un tramo resaltado. Misma firma que los iconos de lucide (`size`, resto de
// props al <svg>) y pinta con `currentColor`, asi que toma el color del modulo igual que los demas iconos del
// selector. El anillo va tenue y el tramo resaltado a color pleno.
const RADIO = 7;
const CIRCUNFERENCIA = 2 * Math.PI * RADIO;
const TRAMO = CIRCUNFERENCIA * 0.3;

export default function IconoDona({ size = 24, ...resto }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="3.5"
      aria-hidden="true"
      focusable="false"
      {...resto}
    >
      <circle cx="12" cy="12" r={RADIO} opacity="0.35" />
      <circle
        cx="12"
        cy="12"
        r={RADIO}
        strokeDasharray={`${TRAMO} ${CIRCUNFERENCIA - TRAMO}`}
        transform="rotate(-90 12 12)"
      />
    </svg>
  );
}

IconoDona.propTypes = {
  size: PropTypes.number,
};
