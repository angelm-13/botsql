// Datos de EJEMPLO para la vista previa de un KPI permitido cuyo rango vuelve vacio («Ver ejemplo»).
// Puro y sin React, y SIN tocar la API ni `kpi_snapshot`: se arman solo a partir de los metadatos del KPI
// (`/kpi_definition/`: unidad, dimension, categorias, etiquetas...).
//
// Producen la MISMA forma que `/kpi_snapshot/query` (`{ rango_a, rango_b }`), asi la tarjeta se pinta con los
// adaptadores reales (`propsNumero`, `propsSeries`, `propsDona`) y el ejemplo no puede divergir de lo real.
//
// Deterministas: los numeros salen de un generador sembrado con la `clave` del KPI, asi que el mismo KPI
// siempre muestra lo mismo. Solo las fechas del eje de periodos dependen de "hoy" (los valores, no).
import { tipoDeDimension } from "./kpiDatos.js";

export const DIAS_DE_EJEMPLO = 14;
export const ENTIDADES_DE_EJEMPLO = 5;

const TEXTOS_POR_OMISION = {
  entidad: "Ejemplo",
  categoria: "Categoría",
};

// [minimo, maximo, decimales] segun la unidad.
const RANGO_POR_UNIDAD = {
  moneda: [8000, 60000, 0],
  numero: [3, 40, 0],
  piezas: [3, 60, 0],
  dias: [2, 40, 0],
  porcentaje: [20, 90, 1],
  minutos: [8, 45, 1],
};
// Estas unidades se promedian al juntar los dias; las demas se suman.
const UNIDADES_PROMEDIADAS = new Set(["porcentaje", "minutos", "dias"]);

/** Hash de texto a entero de 32 bits (FNV-1a). */
function semilla(texto) {
  let h = 0x811c9dc5;
  for (const caracter of String(texto)) {
    h ^= caracter.charCodeAt(0);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

/** Generador pseudoaleatorio (mulberry32): mismo entero de entrada, misma secuencia. */
export function generador(entero) {
  let estado = entero >>> 0;
  return () => {
    estado = (estado + 0x6d2b79f5) >>> 0;
    let t = estado;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function valorEnRango(aleatorio, unidad) {
  const [minimo, maximo, decimales] = RANGO_POR_UNIDAD[unidad] || RANGO_POR_UNIDAD.numero;
  const crudo = minimo + aleatorio() * (maximo - minimo);
  const factor = 10 ** decimales;
  return Math.round(crudo * factor) / factor;
}

const redondear = (valor, unidad) => {
  const decimales = (RANGO_POR_UNIDAD[unidad] || RANGO_POR_UNIDAD.numero)[2];
  const factor = 10 ** decimales;
  return Math.round(valor * factor) / factor;
};

/** Los `dias` ultimos dias hasta `hoy` (incluido), como `AAAA-MM-DD`, del mas viejo al mas nuevo. */
function fechasHasta(hoy, dias) {
  const base = Date.UTC(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());
  return Array.from({ length: dias }, (_, i) => new Date(base - (dias - 1 - i) * 86400000).toISOString().slice(0, 10));
}

const combinar = (valores, unidad) => {
  if (!valores.length) return 0;
  const suma = valores.reduce((acumulado, valor) => acumulado + valor, 0);
  return redondear(UNIDADES_PROMEDIADAS.has(unidad) ? suma / valores.length : suma, unidad);
};

/** Las categorias de un KPI de dimension "estado": su orden declarado, o las claves de sus nombres o colores. */
export function categoriasDeEjemplo(kpiInfo, textos = TEXTOS_POR_OMISION) {
  if (kpiInfo?.orden_categorias?.length) return [...kpiInfo.orden_categorias];
  if (kpiInfo?.etiquetas_categoria) return Object.keys(kpiInfo.etiquetas_categoria);
  if (kpiInfo?.colores_categoria) return Object.keys(kpiInfo.colores_categoria);
  return [1, 2, 3].map((n) => `${textos.categoria} ${n}`);
}

/**
 * `{ rango_a, rango_b: null }` de ejemplo para un KPI, con la forma de `/kpi_snapshot/query`.
 *
 * - dimension "global": una serie por dia (`por_periodo`) y `por_empleado` vacio.
 * - "estado": una entrada por categoria, con los nombres de `etiquetas_categoria` si el KPI los declara.
 * - persona / catalogo: `ENTIDADES_DE_EJEMPLO` entidades genericas ("Ejemplo 1"...), nunca nombres reales.
 * `por_periodo` va siempre, para quien agrupe por periodo.
 */
export function datosDeEjemplo(kpiInfo, { hoy = new Date(), textos = {} } = {}) {
  const t = { ...TEXTOS_POR_OMISION, ...textos };
  const clave = kpiInfo?.clave || "kpi";
  const unidad = kpiInfo?.unidad;
  const aleatorio = generador(semilla(clave));
  const dimension = kpiInfo?.dimensiones?.[0] || "global";
  const tipo = kpiInfo?.dimension_tipo ?? tipoDeDimension(dimension);

  const porPeriodo = {};
  fechasHasta(hoy, DIAS_DE_EJEMPLO).forEach((fecha) => { porPeriodo[fecha] = valorEnRango(aleatorio, unidad); });

  let porEmpleado = {};
  let etiquetas = {};
  if (tipo === "categoria") {
    categoriasDeEjemplo(kpiInfo, t).forEach((categoria) => { porEmpleado[categoria] = valorEnRango(aleatorio, unidad); });
    etiquetas = { ...(kpiInfo?.etiquetas_categoria || {}) };
  } else if (tipo !== "global") {
    const cantidad = Math.min(ENTIDADES_DE_EJEMPLO, kpiInfo?.limite_categorias || ENTIDADES_DE_EJEMPLO);
    for (let i = 1; i <= cantidad; i += 1) {
      porEmpleado[String(i)] = valorEnRango(aleatorio, unidad);
      etiquetas[String(i)] = `${t.entidad} ${i}`;
    }
  }
  porEmpleado = Object.fromEntries(Object.entries(porEmpleado).sort((x, y) => y[1] - x[1]));

  const valores = tipo === "global" ? Object.values(porPeriodo) : Object.values(porEmpleado);
  return {
    rango_a: { total: combinar(valores, unidad), por_empleado: porEmpleado, por_periodo: porPeriodo, etiquetas },
    rango_b: null,
  };
}

/** Si una respuesta de `/kpi_snapshot/query` no trae nada (el KPI aun no tiene datos en el rango). */
export function rangoVacio(snapshot) {
  const rango = snapshot?.rango_a;
  if (!rango) return true;
  return !Object.keys(rango.por_empleado || {}).length && !Object.keys(rango.por_periodo || {}).length && !rango.total;
}
