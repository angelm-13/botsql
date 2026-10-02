// Logica pura del MODO SERVIDOR de la tabla de "Material prestado ahora" (components/kpi-widgets/
// TablaWidget.jsx). En este modo el filtro por responsable, la busqueda, el orden y los conteos los hace el
// servidor sobre TODOS los renglones prestados (GET /kpi_definition/<id>/vivo, ver
// backend/app/kpis/registry.py::material_prestado_actual_query), y la tabla pide el resto por paginas.
// El modo local (kpiPrestamos.js) no cambia: lo usan la vista previa con datos demo y sus pruebas.
// Sin React -- ver kpiPrestamosServidor.test.js.

import { RENGLONES_VISIBLES } from "./kpiPrestamos.js";

// Renglones por pagina en el panel "Ver todos"; la tarjeta pide solo los que muestra.
export const TAMANO_PAGINA_PANEL = 50;
export const TAMANO_PAGINA_TARJETA = RENGLONES_VISIBLES;

/** Los parametros de la consulta: solo los que tienen valor (el servidor no recibe vacios). */
export function parametrosDeVivo({ limit, offset = 0, idUser, ambito, busqueda, orden, agrupada } = {}) {
  const parametros = { limit, offset };
  if (idUser !== undefined && idUser !== null && idUser !== "") parametros.id_user = idUser;
  if (ambito !== undefined && ambito !== null && ambito !== "") parametros.id_user_ambito = ambito;
  const texto = String(busqueda ?? "").trim();
  if (texto) parametros.q = texto;
  if (orden?.campo) parametros.orden = orden.campo;
  if (orden?.direccion) parametros.direccion = orden.direccion;
  if (agrupada) parametros.agrupar = 1;
  return parametros;
}

/** Une una pagina nueva a lo ya cargado, sin repetir renglones (un renglon que cambio de pagina entre dos
 * peticiones no debe aparecer dos veces). */
export function unirPaginas(actuales, nuevas) {
  const vistos = new Set((actuales || []).map((fila) => fila.id_nm_incident_product));
  const agregadas = (nuevas || []).filter((fila) => !vistos.has(fila.id_nm_incident_product));
  return [...(actuales || []), ...agregadas];
}

/** Las opciones del desplegable "Responsable", con los renglones REALES de cada uno (los trae el
 * servidor, no se cuentan sobre lo cargado). El valor es el `id_user`, no el nombre: dos personas con el
 * mismo nombre -o un nombre sucio repetido en el dato, ej. "ESTANCIA EN EL TALLER"- son dos opciones
 * distintas. Esto NO limpia el dato: el nombre sucio se sigue viendo hasta que se corrija en origen. Un
 * renglon sin responsable no tiene id por el que filtrar: entra en "Todos", no tiene opcion propia. */
export function opcionesDeResponsables(responsables) {
  return (responsables || [])
    .filter((fila) => fila.id_user !== null && fila.id_user !== undefined)
    .map((fila) => ({ valor: String(fila.id_user), nombre: fila.responsable, renglones: fila.renglones }));
}

/** Cuantos renglones prestados hay en total (la suma de los de cada responsable). */
export function totalDeResponsables(responsables) {
  return (responsables || []).reduce((suma, fila) => suma + (fila.renglones || 0), 0);
}

/** La vista agrupada con lo que ya llego del servidor. El servidor entrega cada responsable en un solo
 * tramo (`agrupar=1`), asi que basta cortar donde cambia el `id_user`; el numero del encabezado y los dias
 * del mas antiguo son los REALES del responsable, no los de las filas cargadas. `ocultos` = lo que falta
 * por cargar de ese grupo. */
export function agruparContiguos(filas, responsables) {
  const reales = new Map((responsables || []).map((fila) => [fila.id_user, fila]));
  const grupos = [];
  for (const fila of filas || []) {
    const ultimo = grupos[grupos.length - 1];
    if (ultimo && ultimo.id_user === fila.id_user) ultimo.filas.push(fila);
    else grupos.push({ id_user: fila.id_user, responsable: fila.responsable, filas: [fila] });
  }
  return grupos.map((grupo) => {
    const real = reales.get(grupo.id_user);
    const masAntiguo = real ? real.mas_antiguo_dias : Math.max(...grupo.filas.map((fila) => fila.dias_prestado));
    return {
      ...grupo,
      masAntiguo,
      ocultos: real ? Math.max(0, real.renglones - grupo.filas.length) : 0,
    };
  });
}

/** El resumen de arriba, con la forma que ya pinta la tabla (la del modo local): el servidor da los
 * numeros de TODO lo que cumple los filtros. */
export function resumenDeServidor(resumen) {
  const r = resumen || {};
  return {
    renglones: r.renglones || 0,
    cargados: r.renglones || 0,
    responsables: r.responsables || 0,
    masAntiguo: r.mas_antiguo
      ? { dias: r.mas_antiguo.dias, articulo: r.mas_antiguo.articulo, responsable: r.mas_antiguo.responsable }
      : null,
  };
}

/** La respuesta del servidor, completa. Si el backend aun no manda `resumen` ni `responsables` (un frontend
 * nuevo contra un backend viejo, durante un despliegue por partes), se derivan de lo recibido: la tabla
 * funciona -con los numeros de esa pagina- en vez de quedarse cargando para siempre. */
export function completarRespuesta(respuesta) {
  const items = respuesta?.items || [];
  const total = respuesta?.total ?? items.length;
  let responsables = respuesta?.responsables;
  if (!responsables) {
    const porUsuario = new Map();
    for (const fila of items) {
      const actual = porUsuario.get(fila.id_user) || { id_user: fila.id_user, responsable: fila.responsable, renglones: 0, mas_antiguo_dias: 0 };
      actual.renglones += 1;
      actual.mas_antiguo_dias = Math.max(actual.mas_antiguo_dias, fila.dias_prestado || 0);
      porUsuario.set(fila.id_user, actual);
    }
    responsables = [...porUsuario.values()].sort((a, b) => String(a.responsable).localeCompare(String(b.responsable), "es"));
  }
  let resumen = respuesta?.resumen;
  if (!resumen) {
    const masAntiguo = items.reduce((mayor, fila) => (!mayor || fila.dias_prestado > mayor.dias_prestado ? fila : mayor), null);
    resumen = {
      renglones: total,
      responsables: new Set(items.map((fila) => fila.id_user)).size,
      mas_antiguo: masAntiguo && { dias: masAntiguo.dias_prestado, articulo: masAntiguo.articulo, responsable: masAntiguo.responsable },
    };
  }
  return { items, total, resumen, responsables };
}
