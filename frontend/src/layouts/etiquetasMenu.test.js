import assert from "node:assert/strict";
import test from "node:test";
import {
  ETIQUETAS_ACENTUADAS, GRUPOS_ACENTUADOS, etiquetaParaMostrar, grupoParaMostrar,
} from "./etiquetasMenu.js";

test("los grupos sin acento se muestran con acento", () => {
  assert.equal(grupoParaMostrar("Facturacion"), "Facturación");
  assert.equal(grupoParaMostrar("Logistica"), "Logística");
  assert.equal(grupoParaMostrar("Configuracion"), "Configuración");
});

test("un grupo que ya viene bien, o que no se conoce, se deja igual", () => {
  for (const grupo of ["Logística", "Configuración", "Inventario", "CRM", "Recursos humanos", "Punto de venta", "Un grupo nuevo"]) {
    assert.equal(grupoParaMostrar(grupo), grupo);
  }
});

test("las etiquetas del menu que vienen de la siembra se muestran con acento", () => {
  assert.equal(etiquetaParaMostrar("Ordenes de servicio"), "Órdenes de servicio");
  assert.equal(etiquetaParaMostrar("Vales de almacen"), "Vales de almacén");
  assert.equal(etiquetaParaMostrar("Periodos de nomina"), "Periodos de nómina");
  assert.equal(etiquetaParaMostrar("Tipos de ubicacion"), "Tipos de ubicación");
  assert.equal(etiquetaParaMostrar("Categorias de documento"), "Categorías de documento");
  assert.equal(etiquetaParaMostrar("Bitacora diaria de taller"), "Bitácora diaria de taller");
});

test("es idempotente y no toca etiquetas ya correctas", () => {
  for (const etiqueta of ["Almacén", "Cotizaciones", "Productos", "Conexión al dispositivo", undefined, ""]) {
    assert.equal(etiquetaParaMostrar(etiquetaParaMostrar(etiqueta)), etiquetaParaMostrar(etiqueta));
  }
  assert.equal(etiquetaParaMostrar("Productos"), "Productos");
});

test("nada de lo que se traduce es ya un texto acentuado (la tabla solo lleva formas SIN acento)", () => {
  const acentos = /[áéíóúÁÉÍÓÚñ]/;
  for (const original of [...Object.keys(GRUPOS_ACENTUADOS), ...Object.keys(ETIQUETAS_ACENTUADAS)]) {
    assert.doesNotMatch(original, acentos, original);
  }
  for (const corregida of [...Object.values(GRUPOS_ACENTUADOS), ...Object.values(ETIQUETAS_ACENTUADAS)]) {
    assert.match(corregida, acentos, corregida);
  }
});
