// Agrupamiento del selector de KPI del editor "Agregar gráfico" (kpiSelector.js):
// cada pestaña de módulo trae TODOS los KPIs de su módulo (los sin desglose, al final, como
// "combinables") y "Variables" es la vista transversal de todos los sin desglose.
//
// El catálogo es una copia de los 45 KPIs del registry (fixtures/catalogo_del_registry.json:
// clave, módulo, dimensiones y unidad tal como los siembra `kpi_definition`). Si cambia el
// registry, se actualiza esa copia.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { motivoParaNoCombinar } from "./kpiParametros.js";
import {
  agruparKpis, claveDeGrupo, esVariable, estadoDeOpcion, grupoInicial, ORDEN_DE_MODULOS, pestanaDeKpi, resumenDeModulos,
} from "./kpiSelector.js";

const CATALOGO = JSON.parse(readFileSync(new URL("./fixtures/catalogo_del_registry.json", import.meta.url), "utf8"));
const grupoDe = (grupos, clave) => grupos.find((g) => g.clave === clave);
const ids = (kpis) => kpis.map((k) => k.id_kpi_definition);
const claves = (kpis) => kpis.map((k) => k.clave);

// Los siete KPIs de checadas: `grupo: "asistencias"` (pestaña propia) y `modulo: "operaciones"` (el módulo real).
const CHECADAS = [
  "checadas_en_turno_por_equipo", "checadas_sin_salida_por_equipo", "checadas_entradas_por_equipo",
  "checadas_salidas_por_equipo", "horas_trabajadas_por_empleado", "checadas_en_turno_por_empleado",
  "checadas_con_duracion_anomala",
];
const delCatalogo = (...lista) => CATALOGO.filter((k) => lista.includes(k.clave));

const SIN_DESGLOSE_DE_RESTAURANTE = [
  "ventas_restaurante", "ticket_promedio", "propinas_restaurante", "propina_pct_de_venta", "tiempo_de_entrega", "cuentas_sin_cobrar",
];

test("el catálogo de la prueba son los 45 KPIs del registry: 9 sin desglose, 6 de ellos de restaurante", () => {
  assert.equal(CATALOGO.length, 45);
  assert.equal(CATALOGO.filter(esVariable).length, 9);
  assert.deepEqual(claves(CATALOGO.filter((k) => k.modulo === "restaurante" && esVariable(k))).sort(), [...SIN_DESGLOSE_DE_RESTAURANTE].sort());
});

test("los siete KPIs de checadas salen en la pestaña Asistencias, ya no en Operaciones ni en Variables, y su módulo real sigue siendo operaciones", () => {
  const grupos = agruparKpis(CATALOGO, "");
  const asistencias = grupoDe(grupos, "asistencias");
  assert.deepEqual(claves(asistencias.kpis).sort(), [...CHECADAS].sort());
  assert.deepEqual(asistencias.combinables, [], "todos tienen desglose");
  const enOperaciones = new Set(claves(grupoDe(grupos, "operaciones").kpis));
  for (const clave of CHECADAS) assert.ok(!enOperaciones.has(clave), `${clave} ya no está en Operaciones`);
  for (const kpi of asistencias.kpis) {
    assert.equal(kpi.modulo, "operaciones", `${kpi.clave}: el módulo real no cambia (licencias, permisos, filtros, PDF)`);
    assert.equal(kpi.grupo, "asistencias");
    assert.equal(pestanaDeKpi(kpi), "asistencias");
  }
  assert.deepEqual(claves(grupoDe(grupos, "variables").kpis).filter((clave) => CHECADAS.includes(clave)), [], "ninguno es sin desglose");
  assert.equal(CATALOGO.filter(esVariable).length, 9, "las Variables siguen siendo las mismas 9");
  assert.equal(grupoDe(grupos, "variables").kpis.length, 9, "y su pestaña no cambia");
});

test("cada KPI está en SU pestaña (su grupo si lo tiene, si no su módulo), con todos los de esa pestaña (también los sin desglose)", () => {
  const grupos = agruparKpis(CATALOGO);
  for (const kpi of CATALOGO) {
    const pestana = pestanaDeKpi(kpi);
    const grupo = grupoDe(grupos, pestana);
    assert.ok(grupo, `falta la pestaña de ${pestana}`);
    assert.ok(ids(grupo.kpis).includes(kpi.id_kpi_definition), `${kpi.clave} no está en ${pestana}`);
  }
  const totales = Object.fromEntries(grupos.filter((g) => !g.esVariables).map((g) => [g.clave, g.kpis.length]));
  assert.deepEqual(totales, { operaciones: 12, asistencias: 7, inventario: 4, facturacion: 4, laboratorio: 3, documentos: 1, restaurante: 14 });
  assert.deepEqual(grupos.map((g) => g.clave), [...ORDEN_DE_MODULOS, "variables"], "orden fijo y Variables al final");
});

test("los sin desglose van al final de su pestaña, como combinables; los de restaurante ya no se pierden en Variables", () => {
  const restaurante = grupoDe(agruparKpis(CATALOGO), "restaurante");
  assert.deepEqual(claves(restaurante.combinables).sort(), [...SIN_DESGLOSE_DE_RESTAURANTE].sort());
  assert.equal(restaurante.conDesglose.length, 8);
  assert.ok(restaurante.conDesglose.every((k) => !esVariable(k)));
  assert.deepEqual(ids(restaurante.kpis), [...ids(restaurante.conDesglose), ...ids(restaurante.combinables)], "primero los que tienen desglose");
  const facturacion = grupoDe(agruparKpis(CATALOGO), "facturacion");
  assert.deepEqual(claves(facturacion.combinables), ["ingresos_totales", "egresos_totales"]);
  assert.equal(facturacion.conDesglose.length, 2);
  // Un módulo sin ningún sin-desglose no tiene combinables.
  assert.deepEqual(grupoDe(agruparKpis(CATALOGO), "laboratorio").combinables, []);
});

test("«Variables» es la vista transversal: los 9 sin desglose de todos los módulos, cada uno con su módulo", () => {
  const variables = grupoDe(agruparKpis(CATALOGO), "variables");
  assert.equal(variables.esVariables, true);
  assert.equal(variables.kpis.length, 9);
  assert.ok(variables.kpis.every((k) => esVariable(k) && k.modulo), "todos son sin desglose y traen su módulo (la etiqueta de la tarjeta)");
  assert.deepEqual([...new Set(variables.kpis.map((k) => k.modulo))].sort(), ["facturacion", "operaciones", "restaurante"]);
  assert.equal(variables.kpis.filter((k) => k.modulo === "restaurante").length, 6);
});

test("un KPI que sale en dos pestañas es el mismo: mismo id, mismo objeto y mismas reglas de combinación", () => {
  const grupos = agruparKpis(CATALOGO);
  const variables = grupoDe(grupos, "variables");
  for (const enVariables of variables.kpis) {
    const enModulo = grupoDe(grupos, pestanaDeKpi(enVariables)).kpis.find((k) => k.id_kpi_definition === enVariables.id_kpi_definition);
    assert.equal(enModulo, enVariables, `${enVariables.clave}: no es el mismo objeto en su módulo y en Variables`);
  }
  // Mismas reglas: con un KPI de otra unidad elegido, el estado (elegida/bloqueo) es idéntico lo mire desde donde lo mire.
  const ingresos = CATALOGO.find((k) => k.clave === "ingresos_totales");
  const cancelaciones = CATALOGO.find((k) => k.clave === "cancelaciones_por_empleado");
  const ventas = CATALOGO.find((k) => k.clave === "ventas_restaurante");
  for (const seleccionados of [[], [String(cancelaciones.id_kpi_definition)], [String(ventas.id_kpi_definition)]]) {
    for (const multiple of [true, false]) {
      const desdeSuModulo = grupoDe(grupos, "facturacion").kpis.find((k) => k.clave === "ingresos_totales");
      const desdeVariables = variables.kpis.find((k) => k.clave === "ingresos_totales");
      assert.deepEqual(
        estadoDeOpcion({ kpi: desdeSuModulo, seleccionados, catalogo: CATALOGO, multiple }),
        estadoDeOpcion({ kpi: desdeVariables, seleccionados, catalogo: CATALOGO, multiple }),
      );
    }
  }
  assert.equal(estadoDeOpcion({ kpi: ingresos, seleccionados: [String(cancelaciones.id_kpi_definition)], catalogo: CATALOGO, multiple: true }).motivo, motivoParaNoCombinar([cancelaciones], ingresos));
  assert.equal(motivoParaNoCombinar([cancelaciones], ingresos), "unidad", "moneda contra número: se bloquea en las dos pestañas");
  // Elegido en una pestaña = elegido en la otra (la selección son ids).
  assert.equal(estadoDeOpcion({ kpi: ingresos, seleccionados: [String(ingresos.id_kpi_definition)], catalogo: CATALOGO, multiple: true }).elegida, true);
});

test("los conteos de las pestañas son el total del módulo (con sus combinables) y Variables cuenta los sin desglose", () => {
  const resumen = resumenDeModulos(CATALOGO, "", []);
  assert.deepEqual(resumen.map((m) => [m.clave, m.total]), [
    ["operaciones", 12], ["asistencias", 7], ["inventario", 4], ["facturacion", 4], ["laboratorio", 3], ["documentos", 1], ["restaurante", 14], ["variables", 9],
  ]);
  // Elegir un sin desglose cuenta en su módulo y en Variables (la selección es la misma).
  const ventas = CATALOGO.find((k) => k.clave === "ventas_restaurante");
  const conEleccion = Object.fromEntries(resumenDeModulos(CATALOGO, "", [String(ventas.id_kpi_definition)]).map((m) => [m.clave, m.elegidos]));
  assert.equal(conEleccion.restaurante, 1);
  assert.equal(conEleccion.variables, 1);
  assert.equal(conEleccion.operaciones, 0);
});

test("buscar un sin desglose lo encuentra en su módulo y en Variables; buscar uno con desglose, solo en su módulo", () => {
  const sinDesglose = agruparKpis(CATALOGO, "ticket promedio");
  assert.deepEqual(sinDesglose.map((g) => g.clave), ["restaurante", "variables"]);
  const conDesglose = agruparKpis(CATALOGO, "mesas ocupadas");
  assert.deepEqual(conDesglose.map((g) => g.clave), ["restaurante"]);
  const resumen = Object.fromEntries(resumenDeModulos(CATALOGO, "ticket promedio", []).map((m) => [m.clave, [m.total, m.coincidencias]]));
  assert.deepEqual(resumen.restaurante, [14, 1], "el total no cambia al buscar; las coincidencias sí");
  assert.deepEqual(resumen.variables, [9, 1]);
});

test("abre en el módulo del primer KPI elegido, también si es un sin desglose (ahí están todos sus KPIs)", () => {
  const grupos = agruparKpis(CATALOGO);
  const ventas = CATALOGO.find((k) => k.clave === "ventas_restaurante");
  assert.equal(claveDeGrupo(ventas), "restaurante");
  assert.equal(grupoInicial(grupos, CATALOGO, [String(ventas.id_kpi_definition)]), "restaurante");
  // Un KPI sin desglose que no declara módulo (no debería pasar) abre en Variables.
  assert.equal(claveDeGrupo({ dimensiones: ["global"] }), "variables");
});

test("un módulo nuevo (logística, RH, POS) cae solo en su pestaña, sin tocar el código, y un módulo solo de sin-desglose también", () => {
  const nuevos = [
    { id_kpi_definition: 101, clave: "viajes_a_tiempo", etiqueta: "Viajes a tiempo", modulo: "logistica", dimensiones: ["unidad"], unidad: "porcentaje" },
    { id_kpi_definition: 102, clave: "ventas_pos", etiqueta: "Ventas del POS", modulo: "pos", dimensiones: ["global"], unidad: "moneda" },
    { id_kpi_definition: 103, clave: "rotacion", etiqueta: "Rotación", modulo: "rh", dimensiones: ["global"], unidad: "porcentaje" },
  ];
  const grupos = agruparKpis([...CATALOGO, ...nuevos]);
  assert.deepEqual(grupos.map((g) => g.clave), [...ORDEN_DE_MODULOS, "logistica", "pos", "rh", "variables"], "después de los conocidos, por nombre; Variables al final");
  assert.deepEqual(ids(grupoDe(grupos, "logistica").kpis), [101]);
  assert.deepEqual(ids(grupoDe(grupos, "pos").combinables), [102], "solo sin desglose: igual tiene su pestaña");
  assert.equal(grupoDe(grupos, "pos").conDesglose.length, 0);
  const variables = grupoDe(grupos, "variables");
  assert.deepEqual(ids(variables.kpis.filter((k) => k.modulo === "pos" || k.modulo === "rh")), [102, 103], "y aparecen en Variables con su módulo");
  assert.equal(variables.kpis.length, 11);
  assert.deepEqual(resumenDeModulos([...CATALOGO, ...nuevos], "", []).map((m) => m.clave).slice(-4), ["logistica", "pos", "rh", "variables"]);
});

test("«Variables» es transversal: con un solo módulo en el catálogo (un rol con pocos KPIs) no aparece", () => {
  const unKpi = [CATALOGO.find((k) => k.clave === "ventas_por_empleado")];
  assert.deepEqual(agruparKpis(unKpi).map((g) => g.clave), ["facturacion"], "un KPI, una pestaña");
  // Un solo KPI sin desglose: su módulo (con la sección «Combinables»), sin repetirlo en «Variables».
  const unaVariable = [CATALOGO.find((k) => k.clave === "ingresos_totales")];
  const grupos = agruparKpis(unaVariable);
  assert.deepEqual(grupos.map((g) => g.clave), ["facturacion"]);
  assert.equal(grupos[0].combinables.length, 1);
  assert.deepEqual(resumenDeModulos(unaVariable, "", []).map((m) => [m.clave, m.total]), [["facturacion", 1]]);
  // Todo un módulo de un rol (restaurante): sus 14 KPIs en su pestaña y ninguna segunda con los 6 sin desglose.
  const soloRestaurante = CATALOGO.filter((k) => k.modulo === "restaurante");
  assert.deepEqual(agruparKpis(soloRestaurante).map((g) => g.clave), ["restaurante"]);
  // Con dos módulos vuelve a haber vista transversal.
  const dos = [...unaVariable, CATALOGO.find((k) => k.clave === "ventas_restaurante")];
  assert.deepEqual(agruparKpis(dos).map((g) => g.clave), ["facturacion", "restaurante", "variables"]);
  // Buscar no la hace aparecer ni desaparecer: se decide con el catálogo completo.
  assert.deepEqual(agruparKpis(soloRestaurante, "ticket").map((g) => g.clave), ["restaurante"]);
  assert.deepEqual(agruparKpis(dos, "ingresos").map((g) => g.clave), ["facturacion", "variables"]);
});

test("las pestañas salen solo de los módulos con KPIs permitidos y el contador es de lo permitido", () => {
  const rol = CATALOGO.filter((k) => ["ventas_por_empleado", "ventas_restaurante", "ticket_promedio"].includes(k.clave));
  const resumen = resumenDeModulos(rol, "", []);
  assert.deepEqual(resumen.map((m) => [m.clave, m.total]), [["facturacion", 1], ["restaurante", 2], ["variables", 2]]);
  assert.equal(resumen.some((m) => m.clave === "operaciones"), false, "sin KPIs permitidos de operaciones no hay pestaña");
  assert.deepEqual(resumenDeModulos([], "", []), [], "un rol sin ningún KPI no tiene pestañas");
});

// --- pestaña «Asistencias»: un grupo del selector, no un módulo del plan ------------------------------------
// El catálogo que llega al selector es `GET /kpi_definition/`: solo lo permitido al rol. Estos casos recortan el
// catálogo como lo haría un rol y miran qué pestañas y contadores salen.

test("superusuario (catálogo completo): Operaciones 12 y Asistencias 7; ningún KPI se duplica ni se pierde entre pestañas", () => {
  const grupos = agruparKpis(CATALOGO).filter((g) => !g.esVariables);
  const porPestana = Object.fromEntries(grupos.map((g) => [g.clave, g.kpis.length]));
  assert.equal(porPestana.operaciones, 12);
  assert.equal(porPestana.asistencias, 7);
  const todos = grupos.flatMap((g) => ids(g.kpis));
  assert.equal(todos.length, CATALOGO.length, "la suma de las pestañas es el catálogo completo");
  assert.equal(new Set(todos).size, todos.length, "ningún KPI sale en dos pestañas (Variables aparte, que es la vista transversal)");
  assert.deepEqual([...todos].sort((a, b) => a - b), ids(CATALOGO).sort((a, b) => a - b), "ni falta ninguno");
  // Operaciones conserva los 12 de siempre y ninguno de checadas.
  const operaciones = claves(grupoDe(agruparKpis(CATALOGO), "operaciones").kpis);
  assert.equal(operaciones.filter((clave) => CHECADAS.includes(clave)).length, 0);
});

test("un rol con solo UNO o DOS de los siete ve solo la pestaña Asistencias, con su contador, y ninguna de Operaciones", () => {
  // Tienen modulo "operaciones", pero la pestaña es la del grupo: no aparece una pestaña Operaciones vacía ni a medias.
  const uno = delCatalogo("checadas_en_turno_por_equipo");
  assert.deepEqual(agruparKpis(uno).map((g) => g.clave), ["asistencias"]);
  assert.deepEqual(resumenDeModulos(uno, "", []).map((m) => [m.clave, m.total]), [["asistencias", 1]]);
  const dos = delCatalogo("checadas_en_turno_por_equipo", "horas_trabajadas_por_empleado");
  assert.deepEqual(agruparKpis(dos).map((g) => g.clave), ["asistencias"], "una sola pestaña: sin Variables, que no tendría nada que cruzar");
  assert.deepEqual(resumenDeModulos(dos, "", []).map((m) => [m.clave, m.total]), [["asistencias", 2]]);
  assert.equal(grupoInicial(agruparKpis(dos), dos, []), "asistencias", "abre en Asistencias");
  // Elegir uno lo cuenta en Asistencias.
  assert.deepEqual(resumenDeModulos(dos, "", [String(dos[1].id_kpi_definition)]).map((m) => [m.clave, m.elegidos]), [["asistencias", 1]]);
  // Con algo de otro módulo vuelve la fila de pestañas: Asistencias y la otra, cada una con lo suyo.
  const mixto = delCatalogo("checadas_en_turno_por_equipo", "checadas_entradas_por_equipo", "ingresos_totales");
  assert.deepEqual(resumenDeModulos(mixto, "", []).map((m) => [m.clave, m.total]), [["asistencias", 2], ["facturacion", 1], ["variables", 1]]);
});

test("un rol sin ninguno de los siete no ve la pestaña Asistencias", () => {
  const sinChecadas = CATALOGO.filter((k) => !CHECADAS.includes(k.clave));
  assert.equal(sinChecadas.length, 38);
  assert.equal(agruparKpis(sinChecadas).some((g) => g.clave === "asistencias"), false);
  assert.equal(resumenDeModulos(sinChecadas, "", []).some((m) => m.clave === "asistencias"), false);
  assert.equal(grupoDe(agruparKpis(sinChecadas), "operaciones").kpis.length, 12);
  assert.deepEqual(resumenDeModulos([], "", []), [], "y un rol sin ningún KPI no tiene pestañas");
});

test("un rol con solo KPIs de Operaciones (ninguno de checadas) ve Operaciones y no Asistencias", () => {
  const soloOperaciones = CATALOGO.filter((k) => k.modulo === "operaciones" && !CHECADAS.includes(k.clave));
  assert.equal(soloOperaciones.length, 12);
  assert.deepEqual(agruparKpis(soloOperaciones).map((g) => g.clave), ["operaciones"], "sin Variables: con una sola pestaña no hay nada que cruzar");
  assert.deepEqual(resumenDeModulos(soloOperaciones, "", []).map((m) => [m.clave, m.total]), [["operaciones", 12]]);
});

test("buscar un KPI de checadas lo encuentra solo en Asistencias, y el buscador recorre todas las pestañas", () => {
  assert.deepEqual(agruparKpis(CATALOGO, "personas en turno").map((g) => g.clave), ["asistencias"]);
  // «turno» está en el nombre (y la clave) de dos de los siete: el fixture no trae descripciones.
  assert.deepEqual(claves(grupoDe(agruparKpis(CATALOGO, "turno"), "asistencias").kpis), ["checadas_en_turno_por_equipo", "checadas_en_turno_por_empleado"]);
  const resumen = Object.fromEntries(resumenDeModulos(CATALOGO, "turno", []).map((m) => [m.clave, [m.total, m.coincidencias]]));
  assert.deepEqual(resumen.asistencias, [7, 2], "el total no cambia al buscar; las coincidencias sí");
  assert.deepEqual(resumen.operaciones, [12, 0], "Operaciones ya no tiene ninguno de los dos");
});

test("la regla de unidades dentro de Asistencias no cambia: otra unidad se bloquea, la misma no, también desde otra pestaña", () => {
  const minutos = CATALOGO.find((k) => k.clave === "horas_trabajadas_por_empleado");
  const mismaUnidad = CATALOGO.find((k) => k.clave === "checadas_en_turno_por_empleado");
  const otraUnidad = CATALOGO.find((k) => k.clave === "checadas_en_turno_por_equipo");
  assert.deepEqual([minutos.unidad, mismaUnidad.unidad, otraUnidad.unidad], ["minutos", "minutos", "numero"]);
  const elegido = [String(minutos.id_kpi_definition)];
  const estado = (kpi) => estadoDeOpcion({ kpi, seleccionados: elegido, catalogo: CATALOGO, multiple: true });
  assert.equal(estado(otraUnidad).motivo, "unidad", "cantidad contra minutos: se atenúa");
  assert.equal(estado(mismaUnidad).motivo, null, "minutos con minutos: se puede");
  assert.equal(estado(minutos).elegida, true);
  // La selección se conserva al cambiar de pestaña: un KPI de Operaciones de otra unidad también se atenúa.
  const porcentaje = CATALOGO.find((k) => k.modulo === "operaciones" && k.unidad === "porcentaje");
  assert.equal(pestanaDeKpi(porcentaje), "operaciones");
  assert.equal(estado(porcentaje).motivo, "unidad");
  // Con un solo KPI por gráfico (multiple: false) nada se bloquea.
  assert.equal(estadoDeOpcion({ kpi: otraUnidad, seleccionados: elegido, catalogo: CATALOGO, multiple: false }).motivo, null);
});

test("un grupo y un módulo con la misma clave se fundirían: el orden fijo lista Asistencias justo después de Operaciones", () => {
  assert.deepEqual(ORDEN_DE_MODULOS.slice(0, 2), ["operaciones", "asistencias"]);
  assert.equal(new Set(ORDEN_DE_MODULOS).size, ORDEN_DE_MODULOS.length, "sin claves repetidas");
});
