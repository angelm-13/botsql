import assert from "node:assert/strict";
import test from "node:test";
import { etiquetasDePersonas, nombreCorto, partesDeNombre, unidadesDeNombre } from "./kpiNombreCorto.js";

test("los casos pedidos: 3 palabras se quedan, 4 o mas se acortan, la y une apellidos y los compuestos no se parten", () => {
  assert.equal(nombreCorto("María José Ramírez"), "María José Ramírez");
  assert.equal(nombreCorto("María José Ramírez Soto"), "María José Ramírez");
  assert.equal(nombreCorto("Carlos Alberto Mendoza Ruiz"), "Carlos Mendoza");
  assert.equal(nombreCorto("Miguel Hidalgo y Costilla"), "Miguel Hidalgo y Costilla");
  assert.equal(nombreCorto("Luis Fernando Torres Vega"), "Luis Fernando Torres");
  assert.equal(nombreCorto("Luis Fernando Torres Ríos"), "Luis Fernando Torres");
});

test("de 1 a 3 unidades no se acorta", () => {
  assert.equal(nombreCorto("Ana"), "Ana");
  assert.equal(nombreCorto("Ana Pérez"), "Ana Pérez");
  assert.equal(nombreCorto("Ana Pérez López"), "Ana Pérez López");
  assert.equal(nombreCorto("Juan Carlos Pérez"), "Juan Carlos Pérez");
});

test("vacio, nulo, espacios y mayusculas", () => {
  assert.equal(nombreCorto(""), "");
  assert.equal(nombreCorto(null), "");
  assert.equal(nombreCorto(undefined), "");
  assert.equal(nombreCorto("   "), "");
  assert.equal(nombreCorto("  Carlos   Alberto  Mendoza   Ruiz "), "Carlos Mendoza");
  // se conserva el texto como vino: Adser guarda los nombres en mayusculas
  assert.equal(nombreCorto("CARLOS ALBERTO MENDOZA RUIZ"), "CARLOS MENDOZA");
  assert.equal(nombreCorto("MARIA JOSE RAMIREZ SOTO"), "MARIA JOSE RAMIREZ");
});

test("acentos y ñ: la lista de compuestos no distingue acentos ni mayusculas", () => {
  assert.equal(nombreCorto("MARÍA JOSÉ Núñez Peña"), "MARÍA JOSÉ Núñez");
  assert.equal(nombreCorto("Miguel Angel Muñoz Ibáñez"), "Miguel Angel Muñoz");
  assert.equal(nombreCorto("Ángel Íñiguez Ñandú Ortiz"), "Ángel Ñandú");
});

test("las particulas se pegan al apellido que sigue", () => {
  assert.deepEqual(unidadesDeNombre("María de los Ángeles Pérez"), ["María", "de los Ángeles", "Pérez"]);
  assert.equal(nombreCorto("María de los Ángeles Pérez"), "María de los Ángeles Pérez");
  assert.equal(nombreCorto("María de los Ángeles Pérez López"), "María Pérez");
  assert.equal(nombreCorto("Juan Carlos de la Cruz Pérez"), "Juan Carlos de la Cruz");
  assert.equal(nombreCorto("Pedro Pablo de la Garza del Valle"), "Pedro de la Garza");
  assert.equal(nombreCorto("Ana Sofía San Martín Ruiz"), "Ana San Martín");
});

test("la y une los apellidos vecinos como una unidad", () => {
  assert.deepEqual(unidadesDeNombre("Miguel Hidalgo y Costilla"), ["Miguel", "Hidalgo y Costilla"]);
  assert.equal(nombreCorto("Juan Pablo Ruiz y Díaz Soto"), "Juan Ruiz y Díaz");
  assert.equal(nombreCorto("Ana Lucía Pérez y de la Torre Soto"), "Ana Pérez y de la Torre");
  // una y suelta al principio o al final no une nada
  assert.deepEqual(unidadesDeNombre("y Ana"), ["y", "Ana"]);
  assert.deepEqual(unidadesDeNombre("Ana y"), ["Ana", "y"]);
});

test("particulas sueltas al final y nombres que son solo particulas no revientan", () => {
  assert.deepEqual(unidadesDeNombre("Ana de"), ["Ana", "de"]);
  assert.deepEqual(unidadesDeNombre("de la"), ["de la"]);
  assert.equal(nombreCorto("de"), "de");
});

test("un nombre compuesto fuera de la lista se acorta (limite conocido)", () => {
  assert.equal(nombreCorto("José Manuel Pérez López"), "José Pérez");
});

test("partesDeNombre dice que se omitio", () => {
  const partes = partesDeNombre("Carlos Alberto Mendoza Ruiz");
  assert.equal(partes.acortado, true);
  assert.equal(partes.segundoNombre, "Alberto");
  assert.equal(partes.apellidoMaterno, "Ruiz");
  const compuesto = partesDeNombre("Luis Fernando Torres Vega");
  assert.equal(compuesto.segundoNombre, null);
  assert.equal(compuesto.apellidoMaterno, "Vega");
  assert.equal(partesDeNombre("Ana Pérez").acortado, false);
});

test("sin colision, cada persona lleva su nombre corto a secas", () => {
  const etiquetas = etiquetasDePersonas(["María José Ramírez", "Carlos Alberto Mendoza Ruiz", "Miguel Hidalgo y Costilla", "Luis Fernando Torres Vega"]);
  assert.deepEqual(etiquetas, {
    "María José Ramírez": "María José Ramírez",
    "Carlos Alberto Mendoza Ruiz": "Carlos Mendoza",
    "Miguel Hidalgo y Costilla": "Miguel Hidalgo y Costilla",
    "Luis Fernando Torres Vega": "Luis Fernando Torres",
  });
});

test("las dos Maria Jose Ramirez comparten forma corta y se distinguen: la de 3 palabras ya es el nombre completo", () => {
  // «María José Ramírez» (3 unidades) y «María José Ramírez Soto» (4) dan la misma forma: solo la segunda lleva el dato extra
  const etiquetas = etiquetasDePersonas(["María José Ramírez", "María José Ramírez Soto"]);
  assert.equal(etiquetas["María José Ramírez"], "María José Ramírez");
  assert.equal(etiquetas["María José Ramírez Soto"], "María José Ramírez S.");
});

test("Luis Fernando Torres Vega y Rios: colision por el apellido materno, solo ellos llevan la inicial", () => {
  const etiquetas = etiquetasDePersonas(["Luis Fernando Torres Vega", "Luis Fernando Torres Ríos", "Carlos Alberto Mendoza Ruiz"]);
  assert.equal(etiquetas["Luis Fernando Torres Vega"], "Luis Fernando Torres V.");
  assert.equal(etiquetas["Luis Fernando Torres Ríos"], "Luis Fernando Torres R.");
  assert.equal(etiquetas["Carlos Alberto Mendoza Ruiz"], "Carlos Mendoza");
});

test("colision que distingue el segundo nombre: se prefiere esa inicial", () => {
  const etiquetas = etiquetasDePersonas(["Carlos Alberto Mendoza Ruiz", "Carlos Bruno Mendoza Ruiz"]);
  assert.equal(etiquetas["Carlos Alberto Mendoza Ruiz"], "Carlos A. Mendoza");
  assert.equal(etiquetas["Carlos Bruno Mendoza Ruiz"], "Carlos B. Mendoza");
});

test("si ningun nivel distingue (mismas iniciales), se queda el nombre completo", () => {
  const etiquetas = etiquetasDePersonas(["Carlos Alberto Mendoza Ruiz", "Carlos Andrés Mendoza Ruiz"]);
  assert.equal(etiquetas["Carlos Alberto Mendoza Ruiz"], "Carlos Alberto Mendoza Ruiz");
  assert.equal(etiquetas["Carlos Andrés Mendoza Ruiz"], "Carlos Andrés Mendoza Ruiz");
});

test("mismo nombre completo repetido comparte etiqueta; las etiquetas no dependen del orden de la lista", () => {
  const a = etiquetasDePersonas(["Luis Fernando Torres Vega", "Luis Fernando Torres Ríos", "Luis Fernando Torres Vega"]);
  const b = etiquetasDePersonas(["Luis Fernando Torres Ríos", "Luis Fernando Torres Vega"]);
  assert.deepEqual(a, b);
});

test("lista vacia o con vacios", () => {
  assert.deepEqual(etiquetasDePersonas([]), {});
  assert.deepEqual(etiquetasDePersonas(undefined), {});
  assert.deepEqual(etiquetasDePersonas(["", null, "Ana Pérez"]), { "Ana Pérez": "Ana Pérez" });
});

test("sin distinguir acentos para detectar la colision", () => {
  const etiquetas = etiquetasDePersonas(["Jose Luis Gomez Vega", "José Luis Gómez Ríos"]);
  assert.equal(etiquetas["Jose Luis Gomez Vega"], "Jose Luis Gomez V.");
  assert.equal(etiquetas["José Luis Gómez Ríos"], "José Luis Gómez R.");
});

test("una aclaracion entre parentesis al final no cuenta como nombre: PRUEBA Persona 10 (cambia de equipo) ya no sale 'PRUEBA (cambia'", () => {
  assert.equal(nombreCorto("PRUEBA Persona 10 (cambia de equipo)"), "PRUEBA Persona 10");
  assert.equal(nombreCorto("PRUEBA Persona 11 (sin equipo)"), "PRUEBA Persona 11");
  assert.equal(nombreCorto("PRUEBA Persona 12 (dos equipos)"), "PRUEBA Persona 12");
  assert.equal(partesDeNombre("PRUEBA Persona 12 (dos equipos)").acortado, false);
  // Sin parentesis, o con el parentesis en medio, la regla de siempre.
  assert.equal(nombreCorto("PRUEBA Persona 08"), "PRUEBA Persona 08");
  assert.equal(nombreCorto("Carlos Alberto Mendoza Ruiz (suplente)"), "Carlos Mendoza");
  assert.equal(nombreCorto("Ana (Anita) Pérez"), "Ana (Anita) Pérez");
  // Un nombre que es solo un parentesis no queda vacio.
  assert.equal(nombreCorto("(sin nombre)"), "(sin nombre)");
});

test("etiquetasDePersonas: los nombres con aclaracion entre parentesis no pierden el nombre en el eje", () => {
  const nombres = ["PRUEBA Persona 09", "PRUEBA Persona 10 (cambia de equipo)", "PRUEBA Persona 11 (sin equipo)", "PRUEBA Persona 12 (dos equipos)"];
  const etiquetas = etiquetasDePersonas(nombres);
  assert.deepEqual(Object.values(etiquetas), ["PRUEBA Persona 09", "PRUEBA Persona 10", "PRUEBA Persona 11", "PRUEBA Persona 12"]);
  // Dos personas que solo se distinguen por la aclaracion no se pueden separar con el nombre: conservan el nombre completo.
  const iguales = etiquetasDePersonas(["PRUEBA Persona 11 (sin equipo)", "PRUEBA Persona 11 (dos equipos)"]);
  assert.deepEqual(Object.values(iguales).sort(), ["PRUEBA Persona 11 (dos equipos)", "PRUEBA Persona 11 (sin equipo)"]);
});

test("la inicial de una unidad numerica no deja un punto sobrante: 'Empleado incidencias 1', no 'Empleado incidencias 1.'", () => {
  const etiquetas = etiquetasDePersonas(["Empleado demo incidencias 1", "Empleado demo incidencias 2", "Empleado demo incidencias 3"]);
  assert.deepEqual(Object.values(etiquetas), ["Empleado incidencias 1", "Empleado incidencias 2", "Empleado incidencias 3"]);
  // Con letras, la inicial lleva su punto como siempre.
  const letras = etiquetasDePersonas(["Luis Fernando Torres Vega", "Luis Fernando Torres Ríos"]);
  assert.deepEqual(Object.values(letras), ["Luis Fernando Torres V.", "Luis Fernando Torres R."]);
});
