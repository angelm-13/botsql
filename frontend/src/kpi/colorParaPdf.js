// html2canvas 1.4.x solo sabe leer colores en hex/rgb/hsl. El navegador, en cambio, devuelve
// como valor CALCULADO de `color-mix(in srgb, ...)` (y de oklch, lab, etc.) una funcion
// `color(srgb r g b / a)` u otra moderna, y html2canvas truena con
// "Attempting to parse an unsupported color function 'color'".
//
// Los colores del Dashboard dependen de variables por tarjeta (--nivel, --kpi-acento...), asi
// que no se pueden precalcular a hex en el CSS sin cambiar como se ven en pantalla. En su
// lugar, `resolverColoresModernosParaPdf` se usa en el `onclone` de html2canvas: reescribe
// SOLO el clon que se fotografia (la pantalla real no se toca) con el mismo color ya
// convertido a rgb()/rgba() por el propio navegador.

const FUNCION_MODERNA = /\b(?:color|color-mix|oklch|oklab|lab|lch|hwb)\([^()]*\)/g;

const PROPIEDADES_CON_COLOR = [
  "color",
  "background-color",
  "background-image",
  "border-top-color",
  "border-right-color",
  "border-bottom-color",
  "border-left-color",
  "outline-color",
  "box-shadow",
  "text-shadow",
  "text-decoration-color",
  "caret-color",
  "column-rule-color",
  "fill",
  "stroke",
  "stop-color",
];

export function contieneColorModerno(valor) {
  FUNCION_MODERNA.lastIndex = 0;
  return typeof valor === "string" && FUNCION_MODERNA.test(valor);
}

// Convierte un color CSS cualquiera a "rgb(r, g, b)" / "rgba(r, g, b, a)" dejando que un canvas
// 2D lo pinte y leyendo el pixel de vuelta. Devuelve null si el navegador no lo entiende.
export function colorARgb(valor, doc = document) {
  const lienzo = doc.createElement("canvas");
  lienzo.width = lienzo.height = 1;
  const ctx = lienzo.getContext("2d", { willReadFrequently: true });
  if (!ctx) return null;
  ctx.clearRect(0, 0, 1, 1);
  ctx.fillStyle = "#000";
  ctx.fillStyle = valor;
  ctx.fillRect(0, 0, 1, 1);
  const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data;
  // El canvas guarda el color premultiplicado; con alfa 0 (transparent) no hay canal util.
  if (a === 0) return "rgba(0, 0, 0, 0)";
  if (a === 255) return `rgb(${r}, ${g}, ${b})`;
  return `rgba(${r}, ${g}, ${b}, ${Math.round((a / 255) * 1000) / 1000})`;
}

export function resolverColoresModernosParaPdf(raiz, doc = raiz.ownerDocument) {
  const vista = doc.defaultView;
  const cache = new Map();
  const convertir = (funcion) => {
    if (!cache.has(funcion)) cache.set(funcion, colorARgb(funcion, doc) || "rgba(0, 0, 0, 0)");
    return cache.get(funcion);
  };
  const nodos = [raiz, ...raiz.querySelectorAll("*")];
  for (const nodo of nodos) {
    if (!nodo.style) continue;
    const calculado = vista.getComputedStyle(nodo);
    for (const propiedad of PROPIEDADES_CON_COLOR) {
      const valor = calculado.getPropertyValue(propiedad);
      if (!contieneColorModerno(valor)) continue;
      nodo.style.setProperty(propiedad, valor.replace(FUNCION_MODERNA, convertir), "important");
    }
  }
}
