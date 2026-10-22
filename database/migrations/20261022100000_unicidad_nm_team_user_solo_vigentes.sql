-- Una persona no puede estar DOS VECES en el mismo equipo al mismo tiempo, pero si puede
-- volver a un equipo del que ya se le dio de baja.
--
-- Hasta aqui `nm_team_user` tenia `uq_nm_team_user UNIQUE (id_team, id_user)` sobre TODAS las
-- filas, tambien las de baja. Con la baja logica de las membresias (`deletion_date`), eso
-- impedia agregar de nuevo a alguien a un equipo que ya habia tenido: el INSERT chocaba con la
-- fila de baja. La unica salida era reactivar la fila vieja, y eso falsea el historico: la
-- membresia seguiria "vigente" durante el hueco en que la persona estuvo en otro equipo, y las
-- checadas de ese hueco se atribuirian al equipo equivocado (A -> B -> A).
--
-- La regla correcta es que no haya dos membresias VIGENTES iguales. Cada periodo en un equipo es
-- su propia fila, con su `creation_date` y su `deletion_date`, y el historico queda por periodos.
--
-- Esto cambia solo la unicidad: no agrega tablas ni columnas, y el indice parcial reemplaza al
-- constraint (no se suma a el). El mismo cambio vive en `__table_args__` de `NmTeamUser`
-- (`app/models/nm_team_user.py`), para que el esquema que arma el ORM en las pruebas sea el mismo.
--
-- Se reaplica en cada arranque del pod (sin tabla de control): el constraint se quita solo si
-- existe y el indice se crea solo si falta. Los datos que ya hay no pueden tener duplicados
-- vigentes, porque el constraint anterior ya prohibia cualquier duplicado, vigente o no.
BEGIN;

ALTER TABLE nm_team_user DROP CONSTRAINT IF EXISTS uq_nm_team_user;

CREATE UNIQUE INDEX IF NOT EXISTS uq_nm_team_user_vigente
    ON nm_team_user (id_team, id_user) WHERE deletion_date IS NULL;

COMMIT;
