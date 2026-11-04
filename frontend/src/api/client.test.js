// `request`/`requestBlob` ante un fallo de red (U3) y un 403 con su motivo (U2). Sin red ni navegador: `fetch` y `localStorage` son de mentira.
import test, { beforeEach } from "node:test";
import assert from "node:assert/strict";

globalThis.localStorage = { getItem: () => null, removeItem: () => {}, setItem: () => {} };
globalThis.window = { location: { href: "" } };
const { request, requestBlob } = await import("./client.js");
const { claveDeErrorDeKpi, ERROR_DE_ALCANCE, ERROR_DE_RED } = await import("../kpi/kpiErrores.js");

let llamadas;
beforeEach(() => { llamadas = []; });

function conFetch(implementacion) {
  globalThis.fetch = async (...args) => { llamadas.push(args); return implementacion(...args); };
}

test("un fallo de red sale como errors.network (no como el TypeError en ingles del navegador)", async () => {
  for (const mensaje of ["Failed to fetch", "Load failed", "NetworkError when attempting to fetch resource."]) {
    conFetch(() => { throw new TypeError(mensaje); });
    await assert.rejects(request("/kpi_snapshot/query"), (error) => {
      assert.equal(error.message, ERROR_DE_RED, mensaje);
      assert.equal(error.status, 0);
      assert.ok(error.cause instanceof TypeError, "conserva la causa original");
      return true;
    });
  }
});

test("lo mismo para las descargas (requestBlob)", async () => {
  conFetch(() => { throw new TypeError("Failed to fetch"); });
  await assert.rejects(requestBlob("/documents/1/download"), (error) => error.message === ERROR_DE_RED && error.status === 0);
});

test("un 403 por alcance conserva su payload y se distingue del 403 por permiso", async () => {
  const respuesta = (cuerpo, status) => ({ ok: false, status, json: async () => cuerpo });
  conFetch(() => respuesta({ error_key: "errors.permission_denied", meta: { kpi: 9, reason: "scope" } }, 403));
  const alcance = await request("/kpi_snapshot/query").catch((e) => e);
  assert.equal(alcance.status, 403);
  assert.equal(alcance.message, "errors.permission_denied");
  assert.equal(alcance.payload.meta.reason, "scope");
  assert.equal(claveDeErrorDeKpi(alcance), ERROR_DE_ALCANCE);

  conFetch(() => respuesta({ error_key: "errors.permission_denied", meta: { kpi: 9 } }, 403));
  const permiso = await request("/kpi_snapshot/query").catch((e) => e);
  assert.equal(claveDeErrorDeKpi(permiso), "errors.permission_denied");
});

test("las respuestas buenas y los errores del servidor no cambian", async () => {
  conFetch(() => ({ ok: true, status: 200, json: async () => ({ total: 3 }) }));
  assert.deepEqual(await request("/x"), { total: 3 });
  conFetch(() => ({ ok: false, status: 500, json: async () => ({ error_key: "errors.internal_error" }) }));
  const error = await request("/x").catch((e) => e);
  assert.equal(error.message, "errors.internal_error");
  assert.equal(error.status, 500);
  conFetch(() => ({ ok: false, status: 502, json: async () => { throw new Error("no es json"); } }));
  assert.equal((await request("/x").catch((e) => e)).message, "errors.request_failed");
});
