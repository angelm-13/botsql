import test from "node:test";
import assert from "node:assert/strict";
import {
  cambiaLaComparacion, diasDelTramo, esDeFechasFijas, parametrosConRangoRelativo, rangoRelativoPorDuracion,
} from "./kpiFechasFijas.js";

const HOY = new Date(2026, 9, 29); // 2026-10-29

test("los dias del tramo cuentan los dos extremos", () => {
  assert.equal(diasDelTramo("2026-09-29", "2026-09-29"), 1);
  assert.equal(diasDelTramo("2026-08-01", "2026-09-29"), 60);
  assert.equal(diasDelTramo("2026-09-29", "2026-08-01"), null);
  assert.equal(diasDelTramo("no", "2026-09-29"), null);
});

test("solo un tramo de 1, 7, 30 o 90 dias equivale a un rango relativo; 60 dias no", () => {
  assert.equal(rangoRelativoPorDuracion("2026-09-29", "2026-09-29"), "hoy");
  assert.equal(rangoRelativoPorDuracion("2026-09-23", "2026-09-29"), "7_dias");
  assert.equal(rangoRelativoPorDuracion("2026-08-31", "2026-09-29"), "30_dias");
  assert.equal(rangoRelativoPorDuracion("2026-07-02", "2026-09-29"), "90_dias");
  assert.equal(rangoRelativoPorDuracion("2026-08-01", "2026-09-29"), null, "60 dias: la persona elige");
  assert.equal(rangoRelativoPorDuracion("2026-09-01", "2026-09-30"), "30_dias", "30 dias exactos aunque sea un mes");
});

test("quien tiene fechas fijas: un rango guardado sin rango_relativo vigente, que no sea tabla en vivo", () => {
  const fijo = { tipo_grafica: "barras", parametros: { fecha_inicio: "2026-08-01", fecha_fin: "2026-09-29" } };
  assert.equal(esDeFechasFijas(fijo, [{ modo: "snapshot" }]), true);
  assert.equal(esDeFechasFijas({ ...fijo, parametros: { ...fijo.parametros, rango_relativo: "30_dias" } }, []), false);
  assert.equal(esDeFechasFijas({ ...fijo, parametros: { ...fijo.parametros, rango_relativo: "trimestre_pasado" } }, []), true, "un valor de una version futura no es vigente");
  assert.equal(esDeFechasFijas({ tipo_grafica: "tabla", parametros: {} }, []), false);
  assert.equal(esDeFechasFijas(fijo, [{ modo: "vivo" }]), false);
  assert.equal(esDeFechasFijas({ tipo_grafica: "barras", parametros: {} }, []), false, "sin fechas ya dice que le falta el rango");
  assert.equal(esDeFechasFijas(null, []), false);
});

test("convertir conserva el resto de los parametros y deja las fechas de hoy", () => {
  const guardados = { fecha_inicio: "2026-08-01", fecha_fin: "2026-09-29", empleados: [5], id_teams: [2], titulo: "Mi grafico", agrupar_por: "periodo" };
  assert.deepEqual(parametrosConRangoRelativo(guardados, "30_dias", HOY), {
    ...guardados, rango_relativo: "30_dias", fecha_inicio: "2026-09-30", fecha_fin: "2026-10-29",
  });
  assert.equal(guardados.fecha_fin, "2026-09-29", "no muta lo guardado");
});

test("un rango de comparacion fijo pasa a 'contra el periodo anterior'; uno ya relativo no se toca", () => {
  const conB = { fecha_inicio: "2026-08-01", fecha_fin: "2026-09-29", fecha_inicio_b: "2026-06-01", fecha_fin_b: "2026-07-31" };
  assert.equal(cambiaLaComparacion(conB), true);
  const convertido = parametrosConRangoRelativo(conB, "7_dias", HOY);
  assert.equal(convertido.comparar_anterior, true);
  assert.deepEqual([convertido.fecha_inicio, convertido.fecha_fin], ["2026-10-23", "2026-10-29"]);
  assert.deepEqual([convertido.fecha_inicio_b, convertido.fecha_fin_b], ["2026-10-16", "2026-10-22"]);

  const conDesfase = { ...conB, comparar_desfase_dias: 30 };
  assert.equal(cambiaLaComparacion(conDesfase), false);
  assert.equal("comparar_anterior" in parametrosConRangoRelativo(conDesfase, "7_dias", HOY), false);
  assert.equal(cambiaLaComparacion({ fecha_inicio: "2026-08-01", fecha_fin: "2026-09-29" }), false);
});

test("un rango desconocido no se acepta", () => {
  assert.throws(() => parametrosConRangoRelativo({}, "trimestre_pasado", HOY));
});
