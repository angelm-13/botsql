/**
 * Los colores de las graficas, y la regla de como se reparten.
 *
 * La paleta esta validada -- no elegida a ojo -- contra las seis pruebas de
 * accesibilidad (banda de luminosidad, piso de croma, separacion para daltonismo,
 * piso de vision normal, contraste contra la superficie) en modo claro y oscuro.
 * El modo oscuro NO es un volteo automatico del claro: son los mismos ocho tonos
 * re-escalonados para la superficie oscura.
 *
 * Dos reglas que no se rompen:
 *
 *  1. **El orden de los tonos es el mecanismo de seguridad, no decoracion.**
 *     Se asignan en orden fijo. Nunca se ciclan: la novena categoria no recibe
 *     de nuevo el color uno -- se pliega a "Otros", en gris.
 *  2. **El texto nunca lleva el color de la serie.** Los numeros y etiquetas
 *     van en tinta; el color lo carga la marca que esta al lado.
 *
 * En modo claro, tres de los ocho tonos quedan por debajo de 3:1 contra la
 * superficie. Eso obliga a la "via de relieve": toda grafica trae su vista de
 * tabla a un clic (`DynamicChartViewer`), para que la identidad nunca dependa
 * solo del color.
 */

import { useEffect, useState } from "react";

export const SERIES_CLARO = [
  "#2a78d6", // azul
  "#eb6834", // naranja
  "#1baf7a", // aqua
  "#eda100", // amarillo
  "#e87ba4", // magenta
  "#008300", // verde
  "#4a3aa7", // violeta
  "#e34948", // rojo
] as const;

export const SERIES_OSCURO = [
  "#3987e5",
  "#d95926",
  "#199e70",
  "#c98500",
  "#d55181",
  "#008300",
  "#9085e9",
  "#e66767",
] as const;

/** Mas categorias que tonos: el resto se agrupa aqui, nunca se recicla un tono. */
export const COLOR_DE_OTROS_CLARO = "#8a8981";
export const COLOR_DE_OTROS_OSCURO = "#6f6e67";

/** Los tokens de tinta y superficie de un modo. */
export interface TokensDeTema {
  superficie: string;
  tintaPrimaria: string;
  tintaSecundaria: string;
  tintaTenue: string;
  rejilla: string;
  borde: string;
}

export const TOKENS: Record<"claro" | "oscuro", TokensDeTema> = {
  claro: {
    superficie: "#fcfcfb",
    tintaPrimaria: "#0b0b0b",
    tintaSecundaria: "#52514e",
    tintaTenue: "#8a8981",
    rejilla: "#e7e6e1",
    borde: "#dedcd5",
  },
  oscuro: {
    superficie: "#1a1a19",
    tintaPrimaria: "#ffffff",
    tintaSecundaria: "#c3c2b7",
    tintaTenue: "#8a8981",
    rejilla: "#2f2f2c",
    borde: "#383835",
  },
};

export interface Paleta {
  esOscuro: boolean;
  series: readonly string[];
  otros: string;
  tokens: TokensDeTema;
}

/**
 * Detecta el modo y reacciona a que cambie.
 *
 * Se escucha el cambio de verdad (`matchMedia`) en vez de leerlo una sola vez
 * al montar: quien cambia el tema del sistema con el tablero abierto veria si
 * no una grafica con los colores del modo anterior sobre la superficie nueva,
 * que es justo el caso donde el contraste se cae.
 */
export function usarPaleta(): Paleta {
  const [esOscuro, setEsOscuro] = useState(() =>
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches,
  );

  useEffect(() => {
    const consulta = window.matchMedia("(prefers-color-scheme: dark)");
    const alCambiar = (e: MediaQueryListEvent) => setEsOscuro(e.matches);
    consulta.addEventListener("change", alCambiar);
    return () => consulta.removeEventListener("change", alCambiar);
  }, []);

  return {
    esOscuro,
    series: esOscuro ? SERIES_OSCURO : SERIES_CLARO,
    otros: esOscuro ? COLOR_DE_OTROS_OSCURO : COLOR_DE_OTROS_CLARO,
    tokens: esOscuro ? TOKENS.oscuro : TOKENS.claro,
  };
}

// ---------------------------------------------------------------------------
// Formato de numeros
// ---------------------------------------------------------------------------

const COMPACTO = new Intl.NumberFormat("es-MX", {
  notation: "compact",
  maximumFractionDigits: 1,
});
const COMPLETO = new Intl.NumberFormat("es-MX", { maximumFractionDigits: 2 });

/** Para los ejes: corto, porque compite por espacio con las etiquetas. */
export const formatoCompacto = (v: number | string): string =>
  typeof v === "number" ? COMPACTO.format(v) : String(v);

/** Para tarjetas, tablas y tooltips: el numero completo, que es el dato. */
export const formatoCompleto = (v: unknown): string => {
  if (v === null || v === undefined) return "--";
  if (typeof v === "number") return COMPLETO.format(v);
  return String(v);
};
