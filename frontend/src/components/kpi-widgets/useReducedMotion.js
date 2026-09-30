import { useEffect, useState } from "react";

/** `prefers-reduced-motion: reduce` como estado de React, reactivo a que la
 * persona lo cambie en vivo en las preferencias del sistema mientras la
 * pagina sigue abierta -- no solo en la carga. */
export default function useReducedMotion() {
  const [reducido, setReducido] = useState(() => (
    typeof window !== "undefined" && window.matchMedia
      ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
      : false
  ));

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return undefined;
    const medio = window.matchMedia("(prefers-reduced-motion: reduce)");
    const escuchar = (evento) => setReducido(evento.matches);
    medio.addEventListener("change", escuchar);
    return () => medio.removeEventListener("change", escuchar);
  }, []);

  return reducido;
}
