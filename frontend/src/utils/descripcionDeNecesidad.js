// Si lo que el supervisor escribio no parece una descripcion.
//
// Es la misma regla que `descripcion_sospechosa` del servidor
// (`proyect_material_need_service.py`), repetida aqui solo para avisar al instante;
// la que cuenta es la del servidor. Solo atrapa lo EVIDENTE -"12o3pifsfjg",
// "asdfgh", "aaaaa"-: sin letras, de menos de tres caracteres, con una letra
// repetida en serie, o con un tramo de letras de cinco o mas casi sin vocales.
//
// Probada contra 26 pedidos reales (soldadura 6013, tuerca M8x1.25, cable THW
// calibre 12, electrodo E7018...): no rechaza ninguno. NO detecta texto que parece
// palabra ("hjkl") ni errores de dedo: de eso se encarga quien revisa. Ni "THW" ni
// "THHN" -cables reales- tienen vocales, por eso el tramo es de cinco y no menos.

const VOCALES = new Set("aeiou");

function normalizar(texto) {
  return String(texto || "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

/** El motivo (`too_short`, `no_letters`, `repeated`, `few_vowels`, `consonants`) o `null`. */
export function descripcionSospechosa(texto) {
  const t = normalizar(texto);
  if (t.replace(/ /g, "").length < 3) return "too_short";
  if (!/[a-z]/.test(t)) return "no_letters";
  if (/([a-z])\1{3,}/.test(t.replace(/ /g, ""))) return "repeated";
  for (const tramo of t.match(/[a-z]+/g) || []) {
    if (tramo.length < 5) continue;
    const vocales = [...tramo].filter((c) => VOCALES.has(c)).length;
    if (vocales / tramo.length < 0.2) return "few_vowels";
    if (/[^aeiou]{5,}/.test(tramo)) return "consonants";
  }
  return null;
}

// Las unidades que se aceptan; el servidor valida la misma lista.
export const UNIDADES = [
  "pza", "kg", "g", "m", "cm", "mm", "m2", "m3", "lt", "ml", "galon", "cubeta",
  "caja", "bolsa", "saco", "rollo", "juego", "par", "paquete", "tramo",
];

export const CANTIDAD_MAXIMA = 100000;
