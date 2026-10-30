import test from "node:test";
import assert from "node:assert/strict";
import {
  agruparContiguos, completarRespuesta, opcionesDeResponsables, parametrosDeVivo, resumenDeServidor, totalDeResponsables, unirPaginas,
} from "./kpiPrestamosServidor.js";

const fila = (id, id_user, dias = 10, responsable = `R${id_user}`) => ({
  id_nm_incident_product: id, id, id_user, responsable, dias_prestado: dias, articulo: `A${id}`,
});

test("parametrosDeVivo: manda solo lo que tiene valor y traduce los nombres", () => {
  assert.deepEqual(parametrosDeVivo({ limit: 50 }), { limit: 50, offset: 0 });
  assert.deepEqual(
    parametrosDeVivo({
      limit: 10, offset: 20, idUser: "7", ambito: 3, busqueda: "  escalera  ",
      orden: { campo: "articulo", direccion: "asc" }, agrupada: true,
    }),
    { limit: 10, offset: 20, id_user: "7", id_user_ambito: 3, q: "escalera", orden: "articulo", direccion: "asc", agrupar: 1 },
  );
  assert.deepEqual(parametrosDeVivo({ limit: 5, idUser: "", ambito: null, busqueda: "   " }), { limit: 5, offset: 0 });
});

test("unirPaginas: no repite renglones que ya estaban", () => {
  const unidas = unirPaginas([fila(1, 1), fila(2, 1)], [fila(2, 1), fila(3, 2)]);
  assert.deepEqual(unidas.map((f) => f.id_nm_incident_product), [1, 2, 3]);
  assert.deepEqual(unirPaginas(undefined, [fila(1, 1)]).length, 1);
});

test("opcionesDeResponsables: el valor es el id, asi dos con el mismo nombre son dos opciones", () => {
  const opciones = opcionesDeResponsables([
    { id_user: 972, responsable: "ESTANCIA EN EL TALLER", renglones: 5 },
    { id_user: 973, responsable: "ESTANCIA EN EL TALLER", renglones: 5 },
    { id_user: null, responsable: null, renglones: 2 },
  ]);
  assert.deepEqual(opciones, [
    { valor: "972", nombre: "ESTANCIA EN EL TALLER", renglones: 5 },
    { valor: "973", nombre: "ESTANCIA EN EL TALLER", renglones: 5 },
  ]);
  assert.equal(totalDeResponsables([{ renglones: 5 }, { renglones: 5 }, { renglones: 2 }]), 12);
});

test("agruparContiguos: corta donde cambia el responsable y usa los numeros reales del servidor", () => {
  const grupos = agruparContiguos(
    [fila(1, 1, 400), fila(2, 1, 399), fila(3, 2, 200)],
    [
      { id_user: 1, responsable: "R1", renglones: 63, mas_antiguo_dias: 400 },
      { id_user: 2, responsable: "R2", renglones: 1, mas_antiguo_dias: 200 },
    ],
  );
  assert.equal(grupos.length, 2);
  assert.deepEqual(grupos.map((g) => [g.id_user, g.filas.length, g.ocultos, g.masAntiguo]), [[1, 2, 61, 400], [2, 1, 0, 200]]);
});

test("agruparContiguos: sin datos del servidor se arregla con lo cargado", () => {
  const [grupo] = agruparContiguos([fila(1, 9, 30), fila(2, 9, 45)], []);
  assert.deepEqual([grupo.masAntiguo, grupo.ocultos], [45, 0]);
  assert.deepEqual(agruparContiguos([], []), []);
});

test("resumenDeServidor: la forma que ya pinta la tabla", () => {
  assert.deepEqual(
    resumenDeServidor({ renglones: 186, responsables: 15, mas_antiguo: { dias: 514, articulo: "TALADRO", responsable: "OMAR" } }),
    { renglones: 186, cargados: 186, responsables: 15, masAntiguo: { dias: 514, articulo: "TALADRO", responsable: "OMAR" } },
  );
  assert.equal(resumenDeServidor({ renglones: 0, responsables: 0, mas_antiguo: null }).masAntiguo, null);
  assert.equal(resumenDeServidor(null).renglones, 0);
});

test("completarRespuesta: una respuesta vieja (sin resumen ni responsables) se completa con lo recibido", () => {
  const completa = completarRespuesta({ items: [fila(1, 1, 400, "Omar"), fila(2, 1, 30, "Omar"), fila(3, 2, 10, "Ana")], total: 3 });
  assert.deepEqual(completa.resumen, { renglones: 3, responsables: 2, mas_antiguo: { dias: 400, articulo: "A1", responsable: "Omar" } });
  assert.deepEqual(completa.responsables.map((r) => [r.id_user, r.renglones, r.mas_antiguo_dias]), [[2, 1, 10], [1, 2, 400]]);
  assert.deepEqual(completarRespuesta({ items: [], total: 0 }).resumen, { renglones: 0, responsables: 0, mas_antiguo: null });
});

test("completarRespuesta: lo que ya trae el servidor no se toca", () => {
  const resumen = { renglones: 186, responsables: 15, mas_antiguo: null };
  const responsables = [{ id_user: 1, responsable: "X", renglones: 186, mas_antiguo_dias: 5 }];
  assert.deepEqual(completarRespuesta({ items: [fila(1, 1)], total: 186, resumen, responsables }), { items: [fila(1, 1)], total: 186, resumen, responsables });
});
