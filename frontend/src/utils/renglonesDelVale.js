// Agrupa los renglones de un vale por lo que representan de verdad: un
// prestamo, no una fila de tabla.
//
// La devolucion AGREGA un renglon de ENTRADA en vez de reescribir el de
// SALIDA (por diseno, ver el comentario de `devolver_renglon` en
// warehouse_voucher_service.py: "la historia no se corrige, se continua" —
// nunca se pierde un hecho del libro). Es la decision correcta para la base,
// pero pintada tal cual en pantalla el mismo producto aparece DOS veces: una
// vez como salida ya cerrada y otra vez como una fila de entrada aparte, que
// para quien no conoce el sistema se lee como si se hubieran llevado dos
// cosas en vez de una.
//
// Esta funcion empareja cada salida con la entrada que la cerro -mismo
// producto, misma pieza cuando la tiene- y devuelve UN renglon por prestamo
// real, con los dos datos que hacen falta a simple vista: si ya volvio, y a
// donde. Vive aparte del componente por el mismo motivo que `mezclar` en
// `historialDelProducto.js`: se puede probar sin montar React.

export function agruparRenglones(lineas) {
  const todas = lineas || [];
  const salidas = todas.filter((l) => l.direction !== "entrada");
  const entradas = todas.filter((l) => l.direction === "entrada");

  // Una cola de entradas por producto/pieza: un vale puede llevar el mismo
  // producto fungible en dos renglones, y sin la cola el segundo se quedaria
  // sin pareja aunque los dos hayan vuelto.
  const colas = new Map();
  entradas.forEach((entrada) => {
    const clave = `${entrada.id_product}-${entrada.id_inventory_asset ?? ""}`;
    if (!colas.has(clave)) colas.set(clave, []);
    colas.get(clave).push(entrada);
  });

  const usadas = new Set();
  const items = salidas.map((salida) => {
    let entrada = null;
    if (salida.close_date) {
      const clave = `${salida.id_product}-${salida.id_inventory_asset ?? ""}`;
      const cola = colas.get(clave) || [];
      entrada = cola.find((e) => !usadas.has(e.id_nm_incident_product)) || null;
      if (entrada) usadas.add(entrada.id_nm_incident_product);
    }
    return { salida, entrada };
  });

  // Una entrada que ninguna salida reclamo no deberia poder pasar -toda
  // entrada nace de la devolucion de una salida concreta- pero si pasara, es
  // mejor mostrarla suelta que perder el dato.
  entradas.forEach((entrada) => {
    if (usadas.has(entrada.id_nm_incident_product)) return;
    items.push({ salida: null, entrada });
  });

  return items;
}
