"""Columnas de auditoria: las ve cualquiera que pueda leer el registro.

Quien creo un registro y cuando se creo, actualizo o elimino no es un dato que
se conceda campo por campo. `scripts/sync_field_catalog.py` y el catalogo de
permisos las dejan fuera del gestor a proposito -nadie debe capturarlas, y
`created_by` no se concede nunca para que nadie atribuya un registro a otra
persona-, pero cada ruta recortaba la respuesta a lo que el rol tenia en
`nm_field_permission`. Como esas filas no existen ni pueden existir, todo rol
que no fuera administrador perdia las fechas y el autor sin remedio.

Esto solo concede LECTURA: nunca se agregan al conjunto de campos escribibles.
"""

COLUMNAS_DE_AUDITORIA = frozenset({
    "created_by", "creation_date", "last_update_date", "deletion_date",
})
