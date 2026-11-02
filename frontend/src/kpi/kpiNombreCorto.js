// Nombre corto de una persona para ejes y leyendas de las graficas. Puro y sin React -- ver kpiNombreCorto.test.js.
//
// El nombre viaja como UN solo texto (`full_name`): el modelo trae `first_name` y los apellidos, pero casi nadie los tiene
// llenos (lo migrado de Adser solo trae `full_name`). Por eso se parte por palabras y se asume la forma
// «nombre(s) apellido-paterno apellido-materno».
//
// - Se cuentan UNIDADES, no palabras: las particulas («de», «de la», «del», «de los»...) se pegan a la palabra que sigue y la «y» une
//   los apellidos vecinos («Hidalgo y Costilla» es una sola unidad).
// - De 1 a 3 unidades el nombre NO se acorta.
// - Con 4 o mas: primer nombre + apellido paterno (la penultima unidad). Un nombre compuesto de `NOMBRES_COMPUESTOS` no se parte:
//   «María José Ramírez Soto» -> «María José Ramírez».
// - Limite conocido: un nombre compuesto que no este en la lista («José Manuel Pérez López») se acorta a «José Pérez».
//
// Tooltip, leyenda del PDF y descripcion para lector de pantalla siguen con el nombre completo: esto es solo para el eje.

/** Nombres compuestos frecuentes que NO se parten. Lista corta y editable (sin acentos ni mayusculas da igual). */
export const NOMBRES_COMPUESTOS = [
  "María José", "María Fernanda", "María Guadalupe", "José Luis", "José Antonio", "Juan Carlos", "Luis Fernando", "Miguel Ángel",
];

/** Particulas que se pegan a la palabra que sigue. */
export const PARTICULAS = ["de", "del", "la", "las", "los", "san", "santa", "da", "das", "do", "dos", "van", "von", "der", "di", "le"];

const sinAcentos = (texto) => String(texto ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const PARTICULAS_NORMALES = new Set(PARTICULAS.map(sinAcentos));
const COMPUESTOS_NORMALES = new Set(NOMBRES_COMPUESTOS.map(sinAcentos));

const palabrasDe = (nombre) => String(nombre ?? "").trim().split(/\s+/).filter(Boolean);

// Una aclaracion entre parentesis al final ("PRUEBA Persona 11 (sin equipo)") no es parte del nombre: sus palabras no cuentan
// como unidades y el eje no la rotula. Si el nombre ENTERO es un parentesis se deja como esta, para no quedar vacio.
const PARENTESIS_FINAL = /\s*\([^)]*\)\s*$/;
const sinParentesisFinal = (nombre) => {
  const texto = String(nombre ?? "").trim();
  const sinAclaracion = texto.replace(PARENTESIS_FINAL, "");
  return sinAclaracion ? sinAclaracion : texto;
};

/** Las unidades del nombre: particulas pegadas a lo que sigue y «y» uniendo a los vecinos. */
export function unidadesDeNombre(nombre) {
  const palabras = palabrasDe(nombre);
  const unidades = [];
  let particulas = [];
  let unirConAnterior = false;
  palabras.forEach((palabra, indice) => {
    const normal = sinAcentos(palabra);
    const hayDespues = indice + 1 < palabras.length;
    if (normal === "y" && unidades.length > 0 && particulas.length === 0 && hayDespues) {
      unirConAnterior = true;
      return;
    }
    if (PARTICULAS_NORMALES.has(normal) && hayDespues) {
      particulas.push(palabra);
      return;
    }
    const unidad = [...particulas, palabra].join(" ");
    particulas = [];
    if (unirConAnterior) {
      unidades[unidades.length - 1] += ` y ${unidad}`;
      unirConAnterior = false;
    } else {
      unidades.push(unidad);
    }
  });
  if (particulas.length > 0) {
    if (unidades.length > 0) unidades[unidades.length - 1] += ` ${particulas.join(" ")}`;
    else unidades.push(particulas.join(" "));
  }
  return unidades;
}

/** Lo que se ve y lo que se omitio: `{ corto, primerNombre, apellido, segundoNombre, apellidoMaterno, acortado }`. */
export function partesDeNombre(nombre) {
  const completo = palabrasDe(sinParentesisFinal(nombre)).join(" ");
  const unidades = unidadesDeNombre(completo);
  if (unidades.length <= 3) {
    return { corto: completo, primerNombre: null, apellido: null, segundoNombre: null, apellidoMaterno: null, acortado: false };
  }
  const compuesto = COMPUESTOS_NORMALES.has(sinAcentos(`${unidades[0]} ${unidades[1]}`));
  const primerNombre = compuesto ? `${unidades[0]} ${unidades[1]}` : unidades[0];
  const apellido = unidades[unidades.length - 2];
  return {
    corto: `${primerNombre} ${apellido}`,
    primerNombre,
    apellido,
    segundoNombre: compuesto ? null : unidades[1],
    apellidoMaterno: unidades[unidades.length - 1],
    acortado: true,
  };
}

/** `nombreCorto("Carlos Alberto Mendoza Ruiz")` -> "Carlos Mendoza". Vacio o nulo -> "". */
export function nombreCorto(nombre) {
  return partesDeNombre(nombre).corto;
}

// La inicial de una unidad con su punto ("Ruiz" -> "R."). Una unidad que empieza con numero ("1") no tiene inicial: se deja
// completa, porque "1." seria un punto sobrante.
const inicial = (unidad) => {
  const sinParticulas = String(unidad ?? "").replace(/^(?:(?:de|del|la|las|los|san|santa|da|das|do|dos|van|von|der|di|le)\s+)+/i, "");
  const letra = Array.from(sinParticulas)[0];
  if (!letra) return "";
  return /\p{L}/u.test(letra) ? `${letra.toLocaleUpperCase("es")}.` : sinParticulas;
};

// De lo mas discreto a lo mas completo: cada nivel agrega un dato extra SOLO a quien se confunde con otra persona.
const NIVELES = [
  (p) => (p.acortado && p.segundoNombre ? `${p.primerNombre} ${inicial(p.segundoNombre)} ${p.apellido}` : p.corto),
  (p) => (p.acortado ? `${p.corto} ${inicial(p.apellidoMaterno)}` : p.corto),
  (p) => (p.acortado && p.segundoNombre
    ? `${p.primerNombre} ${inicial(p.segundoNombre)} ${p.apellido} ${inicial(p.apellidoMaterno)}`
    : (p.acortado ? `${p.corto} ${inicial(p.apellidoMaterno)}` : p.corto)),
];

/**
 * `{ nombreCompleto: etiqueta }` de las personas que salen en UNA grafica. Quien no se confunde con nadie lleva su nombre corto
 * a secas; quienes comparten forma corta (sin distinguir mayusculas ni acentos) llevan la inicial del segundo nombre, la del
 * apellido materno o ambas, lo primero que las distinga; como ultimo recurso, el nombre completo. Dos personas con EXACTAMENTE el
 * mismo nombre completo no se pueden distinguir con el nombre: comparten etiqueta (la pantalla decide si agrega el usuario).
 */
export function etiquetasDePersonas(nombres) {
  const unicos = Array.from(new Set((nombres || []).map((nombre) => palabrasDe(nombre).join(" ")).filter(Boolean)));
  const partes = new Map(unicos.map((nombre) => [nombre, partesDeNombre(nombre)]));
  const grupos = new Map();
  unicos.forEach((nombre) => {
    const clave = sinAcentos(partes.get(nombre).corto);
    grupos.set(clave, [...(grupos.get(clave) || []), nombre]);
  });
  const etiquetas = {};
  grupos.forEach((miembros) => {
    if (miembros.length === 1) {
      etiquetas[miembros[0]] = partes.get(miembros[0]).corto;
      return;
    }
    const nivel = NIVELES.find((formar) => new Set(miembros.map((nombre) => sinAcentos(formar(partes.get(nombre))))).size === miembros.length);
    miembros.forEach((nombre) => { etiquetas[nombre] = nivel ? nivel(partes.get(nombre)) : nombre; });
  });
  return etiquetas;
}
