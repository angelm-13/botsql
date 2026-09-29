// Logica pura de la tabla de "Material prestado ahora" (components/kpi-widgets/
// TablaWidget.jsx): gravedad por dias, duracion legible, resumen, filtro por
// responsable, orden y agrupado. Sin React -- ver kpi.test.js.

// Hasta cuantos dias un prestamo se considera reciente (verde) y hasta cuantos pide
// atencion (ambar); mas de eso es grave (coral).
export const DIAS_HASTA_VERDE = 30;
export const DIAS_HASTA_AMBAR = 90;

// Cuantos renglones se ven antes de "Ver todos".
export const RENGLONES_VISIBLES = 10;

const DIAS_POR_MES = 30.44;

/** "ok" (hasta 30 dias), "atencion" (31 a 90) o "critico" (mas de 90). El color
 * nunca es la unica senal: cada nivel lleva su propio icono y su texto. */
export function gravedadDeDias(dias) {
  if (dias <= DIAS_HASTA_VERDE) return "ok";
  if (dias <= DIAS_HASTA_AMBAR) return "atencion";
  return "critico";
}

const plural = (cantidad, singular, plural_) => `${cantidad} ${cantidad === 1 ? singular : plural_}`;

/** La misma duracion en anos y meses, para no tener que dividir 512 entre 365:
 * "1 año, 5 meses". Menos de un mes no dice nada (los dias ya se ven); de 1 a 11
 * meses dice solo los meses. Los meses se redondean, y 12 pasan a un año. */
export function duracionLegible(dias) {
  if (!Number.isFinite(dias) || dias < DIAS_POR_MES) return "";
  if (dias < 365) return plural(Math.max(1, Math.round(dias / DIAS_POR_MES)), "mes", "meses");
  let anios = Math.floor(dias / 365);
  let meses = Math.round((dias - anios * 365) / DIAS_POR_MES);
  if (meses >= 12) { anios += 1; meses = 0; }
  return meses ? `${plural(anios, "año", "años")}, ${plural(meses, "mes", "meses")}` : plural(anios, "año", "años");
}

/** El texto del chip de una fila: "512 días · 1 año, 5 meses". */
export function etiquetaDeDias(dias) {
  const base = plural(dias, "día", "días");
  const larga = duracionLegible(dias);
  return larga ? `${base} · ${larga}` : base;
}

/** Los responsables distintos, en orden alfabetico. */
export function responsablesDe(filas) {
  return [...new Set((filas || []).map((fila) => fila.responsable))].sort((a, b) => String(a).localeCompare(String(b), "es"));
}

/** Solo los renglones de un responsable ("" = todos). */
export function filtrarPorResponsable(filas, responsable) {
  return responsable ? (filas || []).filter((fila) => fila.responsable === responsable) : (filas || []);
}

/** Ordena sin alterar la lista recibida. Empata por fecha del vale (el mas viejo
 * primero) y por articulo, para que el orden sea siempre el mismo. */
export function ordenarFilas(filas, campo = "dias_prestado", direccion = "desc") {
  const signo = direccion === "asc" ? 1 : -1;
  return [...(filas || [])].sort((a, b) => {
    const x = a[campo];
    const y = b[campo];
    const comparacion = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y), "es");
    return signo * comparacion
      || String(a.fecha_prestamo).localeCompare(String(b.fecha_prestamo))
      || String(a.articulo).localeCompare(String(b.articulo), "es");
  });
}

/** Lo que dice el resumen de arriba: cuantos renglones, cuantos responsables y cual
 * es el mas antiguo. `total` es el conteo del servidor cuando `filas` es solo la
 * primera pagina. */
export function resumenDePrestamos(filas, total = 0) {
  const lista = filas || [];
  const masAntiguo = lista.reduce((mayor, fila) => (!mayor || fila.dias_prestado > mayor.dias_prestado ? fila : mayor), null);
  return {
    renglones: Math.max(lista.length, total || 0),
    cargados: lista.length,
    responsables: new Set(lista.map((fila) => fila.responsable)).size,
    masAntiguo: masAntiguo && { dias: masAntiguo.dias_prestado, articulo: masAntiguo.articulo, responsable: masAntiguo.responsable },
  };
}

/** La vista agrupada por responsable: cada grupo con sus renglones (por dias) y su
 * renglon mas antiguo; el grupo con el prestamo mas viejo va primero. */
export function agruparPorResponsable(filas) {
  const grupos = new Map();
  for (const fila of filas || []) {
    const actual = grupos.get(fila.responsable) || [];
    actual.push(fila);
    grupos.set(fila.responsable, actual);
  }
  return [...grupos.entries()]
    .map(([responsable, renglones]) => {
      const ordenados = ordenarFilas(renglones);
      return { responsable, filas: ordenados, masAntiguo: ordenados[0].dias_prestado };
    })
    .sort((a, b) => b.masAntiguo - a.masAntiguo || String(a.responsable).localeCompare(String(b.responsable), "es"));
}

/** Los primeros `limite` renglones, o todos si se pidio "Ver todos". */
export function recortar(filas, verTodos, limite = RENGLONES_VISIBLES) {
  return verTodos ? filas : filas.slice(0, limite);
}

/** Como `recortar`, pero sobre grupos: se cortan los RENGLONES (no los grupos), en el
 * orden en que se ven, y los grupos que se quedan sin ninguno desaparecen. */
export function recortarGrupos(grupos, verTodos, limite = RENGLONES_VISIBLES) {
  if (verTodos) return grupos;
  let restantes = limite;
  const salida = [];
  for (const grupo of grupos) {
    if (restantes <= 0) break;
    const filas = grupo.filas.slice(0, restantes);
    restantes -= filas.length;
    salida.push({ ...grupo, filas, ocultos: grupo.filas.length - filas.length });
  }
  return salida;
}

/** Ancho de la barra de un renglon (0 a 100): proporcional al que lleva mas dias de los
 * que se estan viendo, con un minimo para que un renglon de 0 dias no desaparezca. */
export function anchoDeBarra(dias, maximo) {
  if (!maximo || maximo <= 0) return 4;
  return Math.max(4, Math.min(100, Math.round((dias / maximo) * 100)));
}
