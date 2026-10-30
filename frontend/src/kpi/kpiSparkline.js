// Puntos de la mini-tendencia de una tarjeta de numero. Puro y sin React -- ver kpiSparkline.test.js.
//
// El trazo (2 px, puntas redondeadas) se dibuja CENTRADO en cada punto: si un punto cae en el borde del svg, la mitad
// del trazo queda fuera y el svg la recorta (la punta de la derecha se veia cortada). Por eso los puntos van dentro de un
// margen de `trazo / 2 + 1` px.
export const TRAZO_SPARKLINE = 2;

export function puntosDeSparkline(valores, ancho, alto, trazo = TRAZO_SPARKLINE) {
  if (!Array.isArray(valores) || valores.length < 2) return [];
  const margen = trazo / 2 + 1;
  const minimo = Math.min(...valores);
  const maximo = Math.max(...valores);
  const rango = maximo - minimo || 1;
  const util = { ancho: ancho - 2 * margen, alto: alto - 2 * margen };
  return valores.map((valor, indice) => ({
    x: margen + (indice / (valores.length - 1)) * util.ancho,
    // Una serie plana va a media altura, no pegada al borde.
    y: maximo === minimo ? alto / 2 : margen + util.alto - ((valor - minimo) / rango) * util.alto,
  }));
}
