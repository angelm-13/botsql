// Mensaje del 409 "no se puede eliminar": dice QUE registros lo impiden, no solo que los hay.
//
// El backend manda `meta.related = [{ table, count, deleted_count }]` con el nombre tecnico de la
// tabla; el nombre que entiende la persona vive en el catalogo (`related_tables.<tabla>`). Una tabla sin
// nombre en el catalogo sale con su nombre tecnico legible (`nm_team_user` -> "Nm team user") en vez de
// esconderse: mejor un nombre feo que un bloqueo sin explicar.

export const LLAVE_BORRADO_BLOQUEADO = "errors.delete_has_related_records";

function nombreLegible(t, tabla) {
  const crudo = String(tabla).replace(/_/g, " ");
  return t(`related_tables.${tabla}`, crudo.charAt(0).toUpperCase() + crudo.slice(1));
}

export function mensajeDeBorradoBloqueado(t, meta) {
  const base = t(LLAVE_BORRADO_BLOQUEADO, LLAVE_BORRADO_BLOQUEADO);
  const relacionados = Array.isArray(meta?.related) ? meta.related : [];
  if (!relacionados.length) return base;

  const lista = relacionados.map(({ table, count, deleted_count: deleted }) => {
    const baja = deleted > 0
      ? ` (${deleted} ${t("errors.delete_has_related_records_deleted", "already removed")})`
      : "";
    return `${nombreLegible(t, table)}: ${count}${baja}`;
  }).join("; ");

  return `${t("errors.delete_has_related_records_detail", base)} ${lista}. ${t("errors.delete_has_related_records_hint", "")}`.trim();
}
