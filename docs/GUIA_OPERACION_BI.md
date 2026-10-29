# Guía de operación y de uso — Análisis BI

Parte del entregable 6 del anteproyecto. Para usuarios y para quien administra el servicio.

## A. Para el usuario

1. Entra al ERP y abre **Análisis BI** (grupo de analítica del menú).
2. Escribe tu pregunta en español, como la dirías en voz alta (hasta 1,000 caracteres). Ejemplos:
   - «¿Cuántos proyectos hay por estatus?»
   - «Top 8 productos por existencias»
   - «Total facturado por cliente»
   - «Dashboard general de operaciones» (tablero de hasta 8 componentes)
   - «¿Qué es un vale?» / «¿Qué puedo ver?» (ayuda sobre el sistema)
3. El resultado llega como indicador, tabla o gráfica (barras, líneas, área, pastel). Puedes pedir el tipo:
   «… en pastel».

**Lo que verás depende de tu rol.** Si preguntas por algo fuera de tu rol, el sistema contesta «La consulta
no está permitida para tu rol». Si tu rol limita tus datos a *Propios* o *Mis grupos*, los totales cuentan
solo lo tuyo o lo de tu equipo. Para cambiar lo que ves, pídelo al administrador del ERP.

**Consejos:** menciona el módulo y el estatus («vales cerrados»); pide «top N» cuando quieras un número
exacto de elementos; si no entiende, reformula con otras palabras. Las preguntas frecuentes responden al
instante; una pregunta nueva puede tardar de uno a tres minutos (el modelo corre en el propio servidor).

## B. Para el administrador

| Situación | Qué hacer |
|---|---|
| Ver si el servicio está sano | `GET /api/v1/bi/health` (base de datos y modelo) |
| «El modelo no está disponible» (503) | Arrancar Ollama (`ollama serve`) y comprobar `BI_OLLAMA_URL`; el ERP no se detiene y las preguntas con receta siguen respondiendo |
| Un rol ve de más o de menos | Gestor de roles y permisos: alcance de **Lectura** por entidad; esperar ≤ 60 s (caché de acceso) |
| Revisar quién preguntó qué | `SELECT * FROM bi_query_log ORDER BY creation_date DESC` (usuario, rol, pregunta, SQL, filas, ms) |
| Ocultar importes a un rol | `python scripts/bi_ocultar_montos.py --rol "<rol>" --aplicar` (`--restaurar` para revertir) |
| Una respuesta salió mal | Anotar la pregunta; si es frecuente, agregar una receta (ver Manual técnico §8) y su prueba |
| Cambió el esquema de la base | No requiere acción: la caché se renueva sola (≤ 5 min) |
| Ver el SQL generado (depuración) | Solo administrador: `?debug_sql=1` en la petición |

**Buenas prácticas de producción:** usar el rol de solo lectura `bi_lector` en `BI_DATABASE_URL`;
mantener `BI_SAMPLE_VALUES=0` si la política de privacidad exige que el modelo no reciba valores de datos;
revisar `bi_query_log` periódicamente.
