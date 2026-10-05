import test from "node:test";
import assert from "node:assert/strict";
import { destinoDeNotificacion, idAAbrir } from "./destino.js";

test("un destino explicito lleva a su pantalla", () => {
  assert.equal(destinoDeNotificacion({ target_entity: "proyect", target_id: 12 }), "/proyect?abrir=12");
  assert.equal(destinoDeNotificacion({ target_entity: "voucher", target_id: 7 }), "/vouchers?abrir=7");
});

test("los avisos anteriores se infieren de lo que ya traian", () => {
  assert.equal(destinoDeNotificacion({ id_proyect: 3 }), "/proyect?abrir=3");
  assert.equal(destinoDeNotificacion({ metadata: { id_incident: 9 } }), "/vouchers?abrir=9");
});

test("el destino explicito gana sobre lo inferido", () => {
  assert.equal(
    destinoDeNotificacion({ target_entity: "voucher", target_id: 4, id_proyect: 3 }),
    "/vouchers?abrir=4",
  );
});

test("un destino desconocido o sin id no lleva a ningun lado", () => {
  assert.equal(destinoDeNotificacion({ target_entity: "tarea", target_id: 5 }), null);
  assert.equal(destinoDeNotificacion({ target_entity: "proyect", target_id: null }), null);
  assert.equal(destinoDeNotificacion({ target_entity: "proyect", target_id: 0 }), null);
  assert.equal(destinoDeNotificacion({}), null);
  assert.equal(destinoDeNotificacion(null), null);
});

test("un id con basura no arma una ruta", () => {
  assert.equal(destinoDeNotificacion({ target_entity: "proyect", target_id: "12; drop" }), null);
  assert.equal(destinoDeNotificacion({ target_entity: "proyect", target_id: -3 }), null);
  assert.equal(destinoDeNotificacion({ target_entity: "proyect", target_id: 1.5 }), null);
});

test("idAAbrir lee el parametro de la URL y rechaza lo que no es un id", () => {
  assert.equal(idAAbrir(new URLSearchParams("abrir=15")), 15);
  assert.equal(idAAbrir({ abrir: "8" }), 8);
  assert.equal(idAAbrir(new URLSearchParams("abrir=abc")), null);
  assert.equal(idAAbrir(new URLSearchParams("abrir=0")), null);
  assert.equal(idAAbrir(new URLSearchParams("")), null);
  assert.equal(idAAbrir(undefined), null);
});
