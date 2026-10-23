# Base de conocimiento del asistente BI

Aqui vive lo que el asistente responde cuando la pregunta NO es de datos.
(Este archivo es .txt a proposito: el asistente solo lee los .md.)

- `ayuda_bi.md`, `glosario.md`: ayuda general, la ve todo el mundo.
- `modulos/<modulo>.md`: un manual por modulo. Cabecera obligatoria:

      ---
      modulo: inventario
      entidades_clave: [product, location]   # el rol debe poder LEER al menos una
      ---

  `entidades_clave: []` = lo ve cualquiera. Cada seccion `##` debe medir menos de ~900
  caracteres (se busca por seccion). Titulos autoexplicativos: la busqueda pesa mas el titulo.
- Se generan solos, por rol y desde el Gestor de roles: "Mis permisos", "Modulos disponibles",
  "Estructura de la tabla X" (solo columnas que el rol puede leer).
- Documentacion tecnica (arquitectura, seguridad): carpeta(s) en `BI_KB_ADMIN_DIRS`; solo administrador.

Al cambiar un modulo, actualiza su manual. Marca lo que no se sepa como "No documentado:".
