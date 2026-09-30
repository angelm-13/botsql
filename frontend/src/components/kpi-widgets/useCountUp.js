import { useEffect, useRef, useState } from "react";

/** Cuenta de 0 a `valorFinal` con easing, via requestAnimationFrame -- sin
 * libreria: es la misma tecnica de siempre para un numero grande que "carga
 * en vivo". Si `activo` es false (reduced-motion, o `animar={false}`) salta
 * directo al valor final, sin animar nada. */
export default function useCountUp(valorFinal, { duracionMs = 900, activo = true } = {}) {
  const [valor, setValor] = useState(activo ? 0 : valorFinal);
  const cuadroRef = useRef(null);

  useEffect(() => {
    if (!activo) {
      setValor(valorFinal);
      return undefined;
    }
    const inicio = performance.now();
    function paso(ahora) {
      const avance = Math.min(1, (ahora - inicio) / duracionMs);
      const suavizado = 1 - (1 - avance) ** 3; // ease-out cubico
      setValor(valorFinal * suavizado);
      if (avance < 1) cuadroRef.current = requestAnimationFrame(paso);
    }
    cuadroRef.current = requestAnimationFrame(paso);
    return () => cancelAnimationFrame(cuadroRef.current);
  }, [valorFinal, duracionMs, activo]);

  return valor;
}
