import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ERROR_DE_ALCANCE, ERROR_DE_RED, claveDeErrorDeKpi, vistaDelCatalogo } from "./kpiErrores.js";

const es = JSON.parse(readFileSync(new URL("../i18n/locales/es.json", import.meta.url), "utf8"));
const texto = (clave) => clave.split(".").reduce((o, p) => o?.[p], es);

// --- U2: permiso vs alcance ------------------------------------------------------------------------------------------------
test("un 403 con meta.reason 'scope' usa la clave de alcance; uno sin motivo conserva la de permiso", () => {
  const alcance = Object.assign(new Error("errors.permission_denied"), { status: 403, payload: { error_key: "errors.permission_denied", meta: { kpi: 7, reason: "scope" } } });
  const permiso = Object.assign(new Error("errors.permission_denied"), { status: 403, payload: { error_key: "errors.permission_denied", meta: { kpi: 7 } } });
  assert.equal(claveDeErrorDeKpi(alcance), ERROR_DE_ALCANCE);
  assert.equal(claveDeErrorDeKpi(permiso), "errors.permission_denied");
});

test("cualquier otro fallo conserva su clave, y sin clave cae en request_failed", () => {
  assert.equal(claveDeErrorDeKpi(Object.assign(new Error("errors.rango_excede_limite"), { payload: { meta: { dias_maximo: 365 } } })), "errors.rango_excede_limite");
  assert.equal(claveDeErrorDeKpi(Object.assign(new Error("errors.resource_not_found"), { payload: {} })), "errors.resource_not_found");
  assert.equal(claveDeErrorDeKpi(new Error("")), "errors.request_failed");
  assert.equal(claveDeErrorDeKpi(null), "errors.request_failed");
  assert.equal(claveDeErrorDeKpi(undefined), "errors.request_failed");
});

// --- U5: estado del catalogo -----------------------------------------------------------------------------------------------
test("el catalogo cargando o fallido no es un catalogo vacio", () => {
  assert.equal(vistaDelCatalogo({ estado: "cargando", total: 0 }), "cargando");
  assert.equal(vistaDelCatalogo({ estado: "error", total: 0 }), "error");
  assert.equal(vistaDelCatalogo({ estado: "listo", total: 0 }), "vacio");
  assert.equal(vistaDelCatalogo({ estado: "listo", total: 12 }), "lista");
});

test("un catalogo que ya traia KPIs sigue siendo lista aunque se recargue en silencio con otro estado de lista", () => {
  assert.equal(vistaDelCatalogo({ total: 3 }), "lista", "sin estado se toma como listo");
  assert.equal(vistaDelCatalogo(), "vacio");
});

// --- los textos nuevos: existen y no hablan en codigos -----------------------------------------------------------------------
test("los textos nuevos existen en es.json, dicen que hacer y no traen codigos crudos", () => {
  const claves = [ERROR_DE_RED, ERROR_DE_ALCANCE, "kpi_dashboard.change_period", "kpi_dashboard.catalog_loading", "kpi_dashboard.catalog_error_title", "kpi_dashboard.catalog_error_body", "kpi_dashboard.retry", "errors.permission_denied", "errors.resource_not_found"];
  for (const clave of claves) {
    const valor = texto(clave);
    assert.equal(typeof valor, "string", `${clave} falta en es.json`);
    assert.ok(valor.length > 5, clave);
    assert.doesNotMatch(valor, /\b403\b|\bscope\b|Failed to fetch|errors\./i, `${clave}: ${valor}`);
  }
  assert.match(texto(ERROR_DE_RED), /conexión|internet/i);
  assert.match(texto(ERROR_DE_RED), /intenta de nuevo/i);
  assert.match(texto(ERROR_DE_ALCANCE), /administrador/i);
  assert.match(texto("errors.permission_denied"), /Pide acceso a tu administrador/);
});
