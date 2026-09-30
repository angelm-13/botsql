import { useEffect, useMemo, useState } from "react";
import PageHeader from "../components/PageHeader.jsx";
import {
  createActivityLog,
  getActivityLogs,
  getAllProyect,
  getMyTeamWorkers,
} from "../api";
import { useI18n } from "../i18n";

/**
 * La bitacora diaria del taller: solo Jefe de taller la sube, y solo del
 * proyecto que EL tomo (`take_project`) -- el servidor ya lo exige
 * (`require_project_taken_by_actor`), esta pantalla solo evita ofrecer un
 * proyecto que el servidor de todos modos va a rechazar.
 */
function actorGuardado() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch { return {}; }
}

const ESTADOS = [
  { value: "pending", label: "Pendiente" },
  { value: "in_progress", label: "En proceso" },
  { value: "completed", label: "Completada" },
];

function hoyISO() {
  return new Date().toISOString().slice(0, 10);
}

export default function ActivityLogPage() {
  const { t } = useI18n();
  const actor = useMemo(() => actorGuardado(), []);

  const [misProyectos, setMisProyectos] = useState([]);
  const [miPlantilla, setMiPlantilla] = useState([]);
  const [bitacoras, setBitacoras] = useState([]);
  const [loading, setLoading] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);
  const [mensaje, setMensaje] = useState(null);

  const [form, setForm] = useState({
    id_proyect: "",
    activity_date: hoyISO(),
    description: "",
    status: "completed",
    hours_spent: "",
    notes: "",
    worker_ids: [],
  });

  async function cargarTodo() {
    setLoading(true);
    setError(null);
    try {
      const [proyectosRes, plantillaRes, bitacorasRes] = await Promise.all([
        getAllProyect({ per_page: 100 }),
        getMyTeamWorkers(),
        getActivityLogs({ limit: 30 }),
      ]);
      // El proyecto ya viene acotado por el servidor (libres + el mio), pero
      // la bitacora solo se puede subir de uno que YA tome -- no de uno
      // libre que todavia no es de nadie.
      const tomados = (proyectosRes.items || []).filter(
        (p) => Number(p.id_supervisor) === Number(actor.id_user)
      );
      setMisProyectos(tomados);
      setMiPlantilla(plantillaRes || []);
      setBitacoras(bitacorasRes || []);
    } catch (err) {
      setError(err?.message || "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    cargarTodo();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function actualizarCampo(campo, valor) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  }

  function alternarObrero(idUser) {
    setForm((prev) => {
      const yaEsta = prev.worker_ids.includes(idUser);
      return {
        ...prev,
        worker_ids: yaEsta
          ? prev.worker_ids.filter((id) => id !== idUser)
          : [...prev.worker_ids, idUser],
      };
    });
  }

  async function guardar(event) {
    event.preventDefault();
    setGuardando(true);
    setError(null);
    setMensaje(null);
    try {
      await createActivityLog({
        id_proyect: Number(form.id_proyect),
        activity_date: form.activity_date,
        description: form.description.trim(),
        status: form.status,
        hours_spent: form.hours_spent || undefined,
        notes: form.notes.trim() || undefined,
        worker_ids: form.worker_ids,
      });
      setMensaje(t("activity_log.saved", "Bitácora registrada."));
      setForm({
        id_proyect: form.id_proyect,
        activity_date: hoyISO(),
        description: "",
        status: "completed",
        hours_spent: "",
        notes: "",
        worker_ids: [],
      });
      await cargarTodo();
    } catch (err) {
      setError(err?.message || "error");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="entity-page">
      <PageHeader
        eyebrow={t("common.module", "Módulo")}
        titulo={t("activity_log.title", "Bitácora diaria")}
        subtitulo={t(
          "activity_log.subtitle",
          "Reporta el avance del día en el proyecto que tomaste, y quién de tu plantilla trabajó."
        )}
      />

      {error && <div className="alert error">{String(error)}</div>}
      {mensaje && <div className="alert success">{mensaje}</div>}

      <form className="form-card" onSubmit={guardar}>
        <div className="form-grid">
          <label className="field">
            <span>{t("activity_log.project", "Proyecto")}</span>
            <select
              required
              value={form.id_proyect}
              onChange={(e) => actualizarCampo("id_proyect", e.target.value)}
            >
              <option value="">{t("common.select", "— Selecciona —")}</option>
              {misProyectos.map((p) => (
                <option key={p.id_proyect} value={p.id_proyect}>
                  {p.title || p.proyect_description || `Proyecto #${p.id_proyect}`}
                </option>
              ))}
            </select>
            {!loading && misProyectos.length === 0 && (
              <span className="field-error">
                {t(
                  "activity_log.no_projects",
                  "No tienes ningún proyecto tomado todavía. Toma uno desde Proyectos antes de subir tu bitácora."
                )}
              </span>
            )}
          </label>

          <label className="field">
            <span>{t("activity_log.date", "Fecha")}</span>
            <input
              type="date"
              required
              value={form.activity_date}
              onChange={(e) => actualizarCampo("activity_date", e.target.value)}
            />
          </label>

          <label className="field">
            <span>{t("activity_log.status", "Estatus")}</span>
            <select value={form.status} onChange={(e) => actualizarCampo("status", e.target.value)}>
              {ESTADOS.map((op) => (
                <option key={op.value} value={op.value}>{op.label}</option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>{t("activity_log.hours", "Horas dedicadas")}</span>
            <input
              type="number" min="0" max="24" step="0.5"
              value={form.hours_spent}
              onChange={(e) => actualizarCampo("hours_spent", e.target.value)}
            />
          </label>

          <label className="field wide-field">
            <span>{t("activity_log.description", "Qué se hizo hoy")}</span>
            <textarea
              required rows={3}
              value={form.description}
              onChange={(e) => actualizarCampo("description", e.target.value)}
            />
          </label>

          <label className="field wide-field">
            <span>{t("activity_log.notes", "Notas / problemas encontrados")}</span>
            <textarea
              rows={2}
              value={form.notes}
              onChange={(e) => actualizarCampo("notes", e.target.value)}
            />
          </label>

          {miPlantilla.length > 0 && (
            <div className="field wide-field">
              <span>{t("activity_log.workers", "Quién de tu plantilla trabajó hoy")}</span>
              <div className="checkbox-list">
                {miPlantilla.map((w) => (
                  <label key={w.id_user} className="checkbox-inline-item">
                    <input
                      type="checkbox"
                      checked={form.worker_ids.includes(w.id_user)}
                      onChange={() => alternarObrero(w.id_user)}
                    />
                    <span>{w.full_name || w.username}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="form-actions">
          <button className="button primary" type="submit" disabled={guardando || !misProyectos.length}>
            {guardando ? t("common.saving", "Guardando…") : t("activity_log.save", "Guardar bitácora")}
          </button>
        </div>
      </form>

      <div className="table-card">
        <table>
          <thead>
            <tr>
              <th>{t("activity_log.date", "Fecha")}</th>
              <th>{t("activity_log.project", "Proyecto")}</th>
              <th>{t("activity_log.description", "Qué se hizo")}</th>
              <th>{t("activity_log.status", "Estatus")}</th>
              <th>{t("activity_log.hours", "Horas")}</th>
            </tr>
          </thead>
          <tbody>
            {bitacoras.map((b) => (
              <tr key={b.id_activity}>
                <td>{b.activity_date}</td>
                <td>{misProyectos.find((p) => p.id_proyect === b.id_proyect)?.title || b.id_proyect}</td>
                <td><p className="cell-value">{b.description}</p></td>
                <td>{ESTADOS.find((e) => e.value === b.status)?.label || b.status}</td>
                <td>{b.hours_spent ?? "—"}</td>
              </tr>
            ))}
            {!bitacoras.length && (
              <tr><td colSpan="5" className="muted">{t("activity_log.empty", "Todavía no subes ninguna bitácora.")}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
