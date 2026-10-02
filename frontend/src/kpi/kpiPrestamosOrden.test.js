import test from "node:test";
import assert from "node:assert/strict";
import {
  CAMPOS_DE_ORDEN, OPCIONES_DE_ORDEN, claveDeEtiquetaDeOrden, claveDeOrden, direccionInicial, ordenDeClave, siguienteOrden,
} from "./kpiPrestamos.js";

test("direccionInicial: los textos de la A a la Z; los dias y la fecha, de mas a menos", () => {
  assert.equal(direccionInicial("articulo"), "asc");
  assert.equal(direccionInicial("responsable"), "asc");
  assert.equal(direccionInicial("dias_prestado"), "desc");   // mas dias primero
  assert.equal(direccionInicial("fecha_prestamo"), "desc");  // la mas reciente primero
});

test("siguienteOrden: la misma columna invierte el sentido, otra arranca por el suyo", () => {
  const dias = { campo: "dias_prestado", direccion: "desc" };
  assert.deepEqual(siguienteOrden(dias, "dias_prestado"), { campo: "dias_prestado", direccion: "asc" });
  assert.deepEqual(siguienteOrden({ campo: "dias_prestado", direccion: "asc" }, "dias_prestado"), dias);
  assert.deepEqual(siguienteOrden(dias, "fecha_prestamo"), { campo: "fecha_prestamo", direccion: "desc" });
  assert.deepEqual(siguienteOrden(dias, "articulo"), { campo: "articulo", direccion: "asc" });
  assert.deepEqual(siguienteOrden(undefined, "responsable"), { campo: "responsable", direccion: "asc" });
});

test("OPCIONES_DE_ORDEN: cada columna con sus dos sentidos, sin repetir", () => {
  assert.equal(OPCIONES_DE_ORDEN.length, CAMPOS_DE_ORDEN.length * 2);
  assert.equal(new Set(OPCIONES_DE_ORDEN.map(claveDeOrden)).size, OPCIONES_DE_ORDEN.length);
  for (const campo of CAMPOS_DE_ORDEN) {
    assert.deepEqual(OPCIONES_DE_ORDEN.filter((o) => o.campo === campo).map((o) => o.direccion).sort(), ["asc", "desc"]);
  }
  assert.deepEqual(OPCIONES_DE_ORDEN[0], { campo: "dias_prestado", direccion: "desc" }); // lo de siempre, primero
});

test("claveDeOrden y ordenDeClave van y vienen; una clave rara se descarta", () => {
  for (const orden of OPCIONES_DE_ORDEN) assert.deepEqual(ordenDeClave(claveDeOrden(orden)), orden);
  assert.equal(ordenDeClave("sql:desc"), null);
  assert.equal(ordenDeClave("dias_prestado:de_lado"), null);
  assert.equal(ordenDeClave(undefined), null);
  assert.equal(claveDeEtiquetaDeOrden("dias_prestado", "asc"), "orden_dias_prestado_asc");
});
