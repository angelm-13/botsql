import { useState } from "react";
import { useI18n } from "../i18n";
import "../styles/task-board.css";

// Las columnas del tablero son fijas y van en este orden: asi una columna sin
// tareas sigue ahi para soltar una tarjeta. `en_revision` es opcional y solo se
// pinta si ya hay tareas en ese estatus.
const COLUMNS = ["pendiente", "en_proceso", "bloqueada", "cancelada", "terminada"];

/**
 * Tablero de tareas por estatus (`task_status`).
 *
 * Mover una tarjeta llama al flujo formal (`/task/<id>/transition`): las
 * transiciones y los estatus que exigen motivo salen de `catalogo`
 * (/operations/catalog), no se repiten aqui. Un movimiento que el catalogo no
 * permite no se ofrece ni en el arrastre ni en el selector.
 */
export default function TaskBoard({ tareas, catalogo, etiquetaEstatus, etiquetaResponsable, etiquetaProyecto, puedeMover, onMover, acciones }) {
  const { t } = useI18n();
  const [arrastrada, setArrastrada] = useState(null);
  const [pendiente, setPendiente] = useState(null); // { tarea, destino, motivo }
  const [error, setError] = useState("");

  const transiciones = catalogo?.task?.transitions || {};
  const exigeMotivo = (destino) => (catalogo?.task?.reason_required || []).includes(destino);
  const destinosDe = (tarea) => {
    const actual = tarea.task_status || "";
    // Un estatus anterior al catalogo puede moverse a cualquiera valido, igual
    // que lo permite `validate_transition` en el servidor.
    return Object.prototype.hasOwnProperty.call(transiciones, actual) ? transiciones[actual] : Object.keys(transiciones);
  };

  const columnas = tareas.some((tarea) => tarea.task_status === "en_revision")
    ? [...COLUMNS.slice(0, 2), "en_revision", ...COLUMNS.slice(2)]
    : COLUMNS;
  const conocidos = new Set(columnas);
  const sueltas = tareas.filter((tarea) => !conocidos.has(tarea.task_status));

  async function mover(tarea, destino, motivo) {
    setError("");
    try {
      await onMover(tarea, destino, motivo);
      setPendiente(null);
    } catch (fallo) {
      setError(fallo.message || "errors.request_failed");
    }
  }

  function pedirMovimiento(tarea, destino) {
    if (!destino || destino === tarea.task_status) return;
    if (exigeMotivo(destino)) setPendiente({ tarea, destino, motivo: "" });
    else mover(tarea, destino);
  }

  function soltar(evento, destino) {
    evento.preventDefault();
    const tarea = arrastrada;
    setArrastrada(null);
    if (tarea && destinosDe(tarea).includes(destino)) pedirMovimiento(tarea, destino);
  }

  const tarjeta = (tarea) => (
    <article
      className={`kanban-card task-card status-${tarea.task_status || "unknown"}`}
      key={tarea.id_task}
      draggable={puedeMover}
      onDragStart={() => setArrastrada(tarea)}
      onDragEnd={() => setArrastrada(null)}
    >
      <strong>{String(tarea.task_description ?? tarea.id_task)}</strong>
      <small>#{tarea.id_task} · {etiquetaProyecto(tarea.id_proyect)}</small>
      {tarea.owner != null && <small className="task-card-owner">{etiquetaResponsable(tarea.owner)}</small>}
      {tarea.status_reason && <p className="task-card-reason">{tarea.status_reason}</p>}
      {puedeMover && destinosDe(tarea).length > 0 && (
        <select value="" onChange={(evento) => pedirMovimiento(tarea, evento.target.value)} aria-label={t("project_management.change_status")}>
          <option value="">{t("project_management.change_status")}</option>
          {destinosDe(tarea).map((destino) => <option key={destino} value={destino}>{etiquetaEstatus(destino)}</option>)}
        </select>
      )}
      {acciones && <div>{acciones(tarea)}</div>}
    </article>
  );

  return (
    <>
      {error && <div className="alert error">{t(error, error)}</div>}
      <div className="kanban task-board">
        {columnas.map((estatus) => {
          const delGrupo = tareas.filter((tarea) => tarea.task_status === estatus);
          const admite = arrastrada && destinosDe(arrastrada).includes(estatus);
          return (
            <div
              className={`kanban-column${admite ? " task-drop-ok" : ""}`}
              key={estatus}
              onDragOver={(evento) => admite && evento.preventDefault()}
              onDrop={(evento) => soltar(evento, estatus)}
            >
              <h3>{etiquetaEstatus(estatus)} <span>{delGrupo.length}</span></h3>
              {delGrupo.map(tarjeta)}
            </div>
          );
        })}
        {sueltas.length > 0 && (
          <div className="kanban-column">
            <h3>{t("common.unclassified")} <span>{sueltas.length}</span></h3>
            {sueltas.map(tarjeta)}
          </div>
        )}
      </div>

      {pendiente && (
        <div className="task-modal-backdrop" role="presentation">
          <form className="task-modal" onSubmit={(evento) => { evento.preventDefault(); mover(pendiente.tarea, pendiente.destino, pendiente.motivo); }}>
            <h3>{etiquetaEstatus(pendiente.destino)}</h3>
            <p>{pendiente.tarea.task_description}</p>
            <label className="field">
              <span>{t("project_management.reason")}</span>
              <textarea required rows={3} autoFocus value={pendiente.motivo} onChange={(evento) => setPendiente({ ...pendiente, motivo: evento.target.value })} />
            </label>
            <div className="form-actions">
              <button className="button primary" type="submit" disabled={!pendiente.motivo.trim()}>{t("project_management.confirm_change")}</button>
              <button className="button" type="button" onClick={() => setPendiente(null)}>{t("common.cancel")}</button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
