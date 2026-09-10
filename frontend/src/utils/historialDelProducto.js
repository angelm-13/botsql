// Cruce del libro de inventario con los renglones de vale.
//
// Vive aparte del componente por dos motivos: el linter avisa cuando un
// archivo de componentes exporta algo que no lo es -- rompe el refresco en
// caliente --, y porque asi se puede ejecutar sin montar React, que es la
// unica forma de comprobar el emparejamiento sin un runner de pruebas.

/**
 * Cruza el libro con los renglones de vale y devuelve UNA lista, la más
 * reciente primero.
 *
 * El asiento del libro que apunta a un vale y el renglón de ese vale son el
 * mismo hecho: se emiten como un solo renglón con lo que aporta cada fuente.
 * Se emparejan por `id_incident`, y con una cola por vale porque un mismo vale
 * puede llevar dos renglones del mismo producto —salida y devolución—: sin la
 * cola, los dos asientos se quedarían con el mismo renglón.
 */
export function mezclar(asientos, renglonesDeVale) {
  const libro = asientos || [];
  const vales = renglonesDeVale || [];

  const porVale = new Map();
  vales.forEach((r) => {
    const clave = String(r.id_incident);
    if (!porVale.has(clave)) porVale.set(clave, []);
    porVale.get(clave).push(r);
  });

  const usados = new Set();
  const filas = [];

  libro.forEach((m) => {
    let vale = null;
    if (String(m.reference_type) === "incident" && m.reference_id != null) {
      const cola = porVale.get(String(m.reference_id)) || [];
      vale = cola.find((r) => !usados.has(r.id_nm_incident_product)) || null;
      if (vale) usados.add(vale.id_nm_incident_product);
    }
    filas.push({
      clave: `libro-${m.id_inventory_ledger}`,
      fecha: m.creation_date,
      tipo: m.movement_type,
      delta: Number(m.quantity_delta || 0),
      saldo: m.balance_after,
      ubicacion: m.location_description,
      destino: m.location_target_description,
      motivo: m.reason,
      autor: m.created_by_name,
      // Del vale, cuando lo hay.
      folio: vale?.voucher_folio ?? null,
      responsable: vale?.holder_name ?? null,
      devuelto: vale ? vale.returned : null,
      vencido: vale ? vale.overdue : false,
    });
  });

  // Los renglones de vale que ningun asiento reclamo. Es TODO lo importado.
  vales.forEach((r) => {
    if (usados.has(r.id_nm_incident_product)) return;
    filas.push({
      clave: `vale-${r.id_nm_incident_product}`,
      fecha: r.start_date,
      tipo: "loan",
      // El renglon de vale no lleva saldo -- el libro es quien lo lleva -- y
      // ponerle uno inventado seria peor que dejarlo vacio.
      delta: r.quantity ? -Math.abs(Number(r.quantity)) : null,
      saldo: null,
      ubicacion: null,
      destino: null,
      motivo: null,
      autor: null,
      folio: r.voucher_folio ?? null,
      responsable: r.holder_name ?? null,
      devuelto: r.returned,
      vencido: r.overdue,
    });
  });

  // Lo mas reciente primero. Sin fecha, al final: es lo que menos se puede
  // situar y arriba estorbaria a lo que si.
  return filas.sort((a, b) => {
    if (!a.fecha) return 1;
    if (!b.fecha) return -1;
    return String(b.fecha).localeCompare(String(a.fecha));
  });
}
