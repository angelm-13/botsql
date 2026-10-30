# Pasos de despliegue por cambio

El procedimiento general (cómo se construyen las imágenes, cómo se promueve
un overlay, cómo corren las migraciones) vive en
`ARQUITECTURA_TYAKXA_TNY.md` §7.1. Esta carpeta es para lo que un cambio
concreto exige **además** de eso: un backfill, un orden específico, una
verificación que no es obvia.

Un archivo por cambio, `AAAA-MM-DD_<tema>.md`, con:

1. Qué commit(s) cubre y qué migraciones trae.
2. Pasos en orden, con los comandos exactos y por ambiente si difieren.
3. Cómo verificar que funcionó (consultas o llamadas concretas, con el
   resultado esperado).
4. Qué hacer si algo sale mal.

Si un cambio no necesita nada más allá de §7.1, no lleva archivo aquí.
