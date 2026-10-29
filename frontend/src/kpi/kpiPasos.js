// A que paso del asistente de "Agregar grafico" se puede ir al tocar su pestana. Puro y sin React -- ver kpiPasos.test.js.
//
// Los pasos (Que medir -> Periodo -> Filtros) se recorren EN ORDEN: hacia atras siempre, hacia adelante solo el
// siguiente y solo cuando el actual ya se puede dar por bueno (`puedeAvanzar`). Saltar de "Que medir" a "Filtros"
// dejaba el periodo sin ver.
export function puedeIrAlPaso({ indice, pasoActual, puedeAvanzar }) {
  if (indice <= pasoActual) return true;
  return indice === pasoActual + 1 && Boolean(puedeAvanzar);
}
