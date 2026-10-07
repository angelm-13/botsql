// Formato de oracion de la descripcion de un producto. Es el MISMO algoritmo que
// backend/app/utils/product_description.py: si cambia uno, cambia el otro.
//
// "Pulidor chico 3/4": primera letra en mayuscula, el resto en minusculas, con
// espacios, numeros y simbolos (diagonal, guion). Las siglas de dos o mas letras
// ("PVC", "LED") se respetan; en un texto TODO en mayusculas solo las conocidas.

export const ACRONIMOS_CONOCIDOS = new Set([
  "PVC", "CPVC", "ABS", "LED", "USB", "HDMI", "HSS", "NPT", "AWG", "MDF", "OSB",
  "EPDM", "CFE", "IVA", "SDS", "RJ45", "UTP", "LCD", "GPS", "RPM", "PPR", "TIG",
  "MIG", "AC", "DC", "NOM", "SAE", "ISO", "EPP", "IP", "PU", "PP", "PE",
]);

const MAX_LONGITUD = 250;
const CARACTERES_PERMITIDOS = /^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 /\-.,()"°%#+&:]+$/;
const LETRA = /[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]/;

function esSiglaConForma(palabra) {
  const letras = palabra.match(/[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]/g) || [];
  return letras.length >= 2 && letras.every((c) => c === c.toUpperCase());
}

export function sugerirDescripcion(texto) {
  const limpio = String(texto ?? "").split(/\s+/).filter(Boolean).join(" ");
  if (!limpio) return "";
  const todoEnMayusculas = ![...limpio].some((c) => c !== c.toUpperCase());
  const palabras = limpio.split(" ").map((palabra) => {
    const nucleo = palabra.replace(/^[.,()"]+|[.,()"]+$/g, "");
    if (esSiglaConForma(nucleo) && (!todoEnMayusculas || ACRONIMOS_CONOCIDOS.has(nucleo))) return palabra;
    return palabra.toLowerCase();
  });
  const primera = [...palabras[0]];
  const i = primera.findIndex((c) => LETRA.test(c));
  if (i >= 0) primera[i] = primera[i].toUpperCase();
  palabras[0] = primera.join("");
  return palabras.join(" ");
}

export function descripcionValida(texto) {
  if (texto === null || texto === undefined || String(texto).trim() === "") return true;
  const valor = String(texto);
  if (valor.length > MAX_LONGITUD) return false;
  if (!CARACTERES_PERMITIDOS.test(valor)) return false;
  const inicial = valor[0];
  if (!LETRA.test(inicial) || inicial !== inicial.toUpperCase()) return false;
  return sugerirDescripcion(valor) === valor;
}
