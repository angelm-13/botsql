// Columnas de auditoria: las ve cualquiera que pueda leer el registro.
//
// Quien creo un registro y cuando se creo, actualizo o elimino no se concede
// campo por campo: el gestor de roles no las ofrece (no se capturan a mano) y
// por eso no hay filas de permiso que las habiliten. Las pantallas decidian la
// visibilidad solo con esas filas, asi que un rol que no fuera administrador
// nunca veia las columnas. El backend aplica la misma regla en
// `app/utils/field_access.py`; solo es lectura, nunca escritura.
export const CAMPOS_DE_AUDITORIA = new Set([
  "created_by", "creation_date", "last_update_date", "deletion_date",
]);
