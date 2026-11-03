// A que paso del asistente de "Agregar grafico" se puede ir al tocar su pestana. Puro y sin React -- ver kpiPasos.test.js.
//
// Los pasos (Que medir -> Periodo -> Filtros) se recorren EN ORDEN: hacia atras siempre, hacia adelante solo el
// siguiente y solo cuando el actual ya se puede dar por bueno (`puedeAvanzar`). Saltar de "Que medir" a "Filtros"
// dejaba el periodo sin ver.
export function puedeIrAlPaso({ indice, pasoActual, puedeAvanzar }) {
  if (indice <= pasoActual) return true;
  return indice === pasoActual + 1 && Boolean(puedeAvanzar);
}

// El paso "Filtros" solo existe si lo elegido tiene algun filtro aplicable y no es una tabla (datos de "ahora").
export function kpiAdmiteFiltros({ hayAlgunFiltro, tipo }) {
  return Boolean(hayAlgunFiltro) && tipo !== "tabla";
}

// Agregar/guardar exige haber VISITADO "Filtros" cuando el indicador los admite. `visitados` son las claves de paso vistas.
export function puedeAgregar({ admiteFiltros, visitados }) {
  if (!admiteFiltros) return true;
  return Array.isArray(visitados) && visitados.includes("filtros");
}

// Enter dentro de un campo nunca guarda: en un paso intermedio avanza (salvo en el buscador de indicadores, donde
// solo se escribe) y en el ultimo no hace nada; se guarda unicamente con el boton.
export function accionDeEnter({ esUltimoPaso, puedeAvanzar, enBuscador }) {
  if (esUltimoPaso || enBuscador || !puedeAvanzar) return "nada";
  return "avanzar";
}
