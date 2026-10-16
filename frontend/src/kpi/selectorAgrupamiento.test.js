// Agrupamiento del selector de KPI del editor "Agregar gráfico" (kpiSelector.js):
// cada pestaña de módulo trae TODOS los KPIs de su módulo (los sin desglose, al final, como
// "combinables") y "Variables" es la vista transversal de todos los sin desglose.
//
// El catálogo es una copia de los 38 KPIs del registry (fixtures/catalogo_del_registry.json:
// clave, módulo, dimensiones y unidad tal como los siembra `kpi_definition`). Si cambia el
// registry, se actualiza esa copia.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { motivoParaNoCombinar } from "./kpiParametros.js";
import {
  agruparKpis, claveDeGrupo, esVariable, estadoDeOpcion, grupoInicial, ORDEN_DE_MODULOS, resumenDeModulos,
} from "./kpiSelector.js";

const CATALOGO = JSON.parse(readFileSync(new URL("./fixtures/catalogo_del_registry.json", import.meta.url), "utf8"));
const grupoDe = (grupos, clave) => grupos.find((g) => g.clave === clave);
const ids = (kpis) => kpis.map((k) => k.id_kpi_definition);
const claves = (kpis) => kpis.map((k) => k.clave);

const SIN_DESGLOSE_DE_RESTAURANTE = [
  "ventas_restaurante", "ticket_promedio", "propinas_restaurante", "propina_pct_de_venta", "tiempo_de_entrega", "cuentas_sin_cobrar",
];

test("el catálogo de la prueba son los 38 KPIs del registry: 9 sin desglose, 6 de ellos de restaurante", () => {
  assert.equal(CATALOGO.length, 38);
  assert.equal(CATALOGO.filter(esVariable).length, 9);
  assert.deepEqual(claves(CATALOGO.filter((k) => k.modulo === "restaurante" && esVariable(k))).sort(), [...SIN_DESGLOSE_DE_RESTAURANTE].sort());
});

test("cada KPI está en la pestaña de SU módulo, con todos los de ese módulo (también los sin desglose)", () => {
  const grupos = agruparKpis(CATALOGO);
  for (const kpi of CATALOGO) {
    const grupo = grupoDe(grupos, kpi.modulo);
    assert.ok(grupo, `falta la pestaña de ${kpi.modulo}`);
    assert.ok(ids(grupo.kpis).includes(kpi.id_kpi_definition), `${kpi.clave} no está en ${kpi.modulo}`);
  }
  const totales = Object.fromEntries(grupos.filter((g) => !g.esVariables).map((g) => [g.clave, g.kpis.length]));
  assert.deepEqual(totales, { operaciones: 12, inventario: 4, facturacion: 4, laboratorio: 3, documentos: 1, restaurante: 14 });
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
    const enModulo = grupoDe(grupos, enVariables.modulo).kpis.find((k) => k.id_kpi_definition === enVariables.id_kpi_definition);
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
    ["operaciones", 12], ["inventario", 4], ["facturacion", 4], ["laboratorio", 3], ["documentos", 1], ["restaurante", 14], ["variables", 9],
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
