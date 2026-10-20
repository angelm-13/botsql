// La clase de un articulo del almacen. Es la misma lista del servidor
// (`ITEM_CLASSES` en backend/app/utils/item_class.py): si se agrega una, va en los dos
// y en el CHECK de la migracion `20261020120000`.
//
// Es una etiqueta para clasificar y filtrar; no cambia como se rastrea ni si se vende.
export const CLASES_DE_ARTICULO = [
  { clave: "herramienta", etiqueta: "Herramienta" },
  { clave: "consumible", etiqueta: "Consumible" },
  { clave: "sobrante", etiqueta: "Sobrante" },
  { clave: "recargable", etiqueta: "Recargable" },
];

export function etiquetaDeClase(clave, t) {
  if (!clave) return "";
  const base = CLASES_DE_ARTICULO.find((c) => c.clave === clave)?.etiqueta || clave;
  return t ? t(`item_class.${clave}`, base) : base;
}
