import test from "node:test";
import assert from "node:assert/strict";
import { crearControlador, accionDeTecla } from "./dialogoControl.js";

test("confirmar: aceptar da true y cancelar da false", async () => {
  const c = crearControlador();
  const si = c.confirmar("¿Seguro?");
  c.aceptar();
  assert.equal(await si, true);
  const no = c.confirmar("¿Seguro?");
  c.cancelar();
  assert.equal(await no, false);
});

test("pedirTexto: aceptar da el texto y cancelar da null", async () => {
  const c = crearControlador();
  const ok = c.pedirTexto("Nombre del nuevo tablero");
  c.aceptar("Ventas");
  assert.equal(await ok, "Ventas");
  const nada = c.pedirTexto("Nombre del nuevo tablero");
  c.cancelar();
  assert.equal(await nada, null);
});

test("pedirTexto: aceptar con texto vacío o en blanco no hace nada", async () => {
  const c = crearControlador();
  let resuelto = false;
  const p = c.pedirTexto("Nombre").then((v) => { resuelto = true; return v; });
  assert.equal(c.aceptar(""), false);
  assert.equal(c.aceptar("   "), false);
  await Promise.resolve();
  assert.equal(resuelto, false);
  c.aceptar("Algo");
  assert.equal(await p, "Algo");
});

test("avisar se cierra con aceptar o con cancelar", async () => {
  const c = crearControlador();
  const a = c.avisar("Listo");
  c.cancelar();
  assert.equal(await a, undefined);
});

test("dos diálogos seguidos quedan en fila, no se encimen", async () => {
  const c = crearControlador();
  const vistos = [];
  c.suscribir((d) => vistos.push(d && d.mensaje));
  const uno = c.confirmar("uno");
  const dos = c.confirmar("dos");
  c.aceptar();
  assert.equal(await uno, true);
  c.cancelar();
  assert.equal(await dos, false);
  assert.deepEqual(vistos, [null, "uno", "dos", null]);
});

test("teclado: Esc cancela, Enter acepta, Enter sobre un botón no se intercepta", () => {
  assert.equal(accionDeTecla({ key: "Escape" }), "cancelar");
  assert.equal(accionDeTecla({ key: "Enter" }), "aceptar");
  assert.equal(accionDeTecla({ key: "Enter", enBoton: true }), null);
  assert.equal(accionDeTecla({ key: "a" }), null);
});
