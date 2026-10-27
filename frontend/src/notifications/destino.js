// A donde lleva un clic en una notificacion de la campana.
//
// Cada aviso trae `target_entity` + `target_id` (ver `notification_service`).
// Este mapa es el UNICO lugar que sabe que ruta abre cada destino: agregar un
// modulo que notifique es agregar una linea aqui, no tocar la campana.
//
// Un destino que no se conoce devuelve `null`: el aviso se ve igual, solo que
// sin clic. Mejor eso que navegar a una ruta que no existe.

const RUTAS = {
  proyect: (id) => `/proyect?abrir=${id}`,
  voucher: (id) => `/vouchers?abrir=${id}`,
  purchase_order: (id) => `/ordenes-de-compra?abrir=${id}`,
  employee_leave: () => "/my_leaves",
};

const enteroPositivo = (valor) => {
  const n = Number(valor);
  return Number.isInteger(n) && n > 0 ? n : null;
};

/**
 * La ruta a la que lleva la notificacion, o `null` si no lleva a ningun lado.
 *
 * Se lee primero el destino explicito y, para los avisos anteriores a que
 * existiera (por si la migracion no los alcanzo), se infiere de lo que ya
 * traian: `id_proyect` o el `id_incident` del `metadata`.
 */
export function destinoDeNotificacion(notificacion) {
  if (!notificacion) return null;
  let entidad = notificacion.target_entity || null;
  let id = enteroPositivo(notificacion.target_id);

  if (!entidad || id === null) {
    const proyecto = enteroPositivo(notificacion.id_proyect);
    const vale = enteroPositivo(notificacion.metadata?.id_incident);
    if (proyecto !== null) { entidad = "proyect"; id = proyecto; }
    else if (vale !== null) { entidad = "voucher"; id = vale; }
    else return null;
  }

  const ruta = RUTAS[entidad];
  return ruta ? ruta(id) : null;
}

/**
 * El registro que una pantalla debe abrir al llegar con `?abrir=<id>`, o `null`.
 * Acepta tanto `URLSearchParams` como un objeto plano.
 */
export function idAAbrir(parametros) {
  const crudo = typeof parametros?.get === "function"
    ? parametros.get("abrir")
    : parametros?.abrir;
  return enteroPositivo(crudo);
}
