import { useEffect, useMemo, useState } from "react";
import { Plus, Pencil, Trash2, UserMinus, UserPlus, Users, X } from "lucide-react";
import {
  getAllTeam,
  createTeam,
  updateTeam,
  deleteTeam,
  getAllNmTeamUser,
  createNmTeamUser,
  deleteNmTeamUser,
  getAllUser
} from "../api";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader.jsx";
import { fetchAllPages } from "../utils/fetchAllPages";

function asItems(payload) {
  if (Array.isArray(payload)) return payload;
  return payload?.items || payload?.data || payload?.records || [];
}

function userLabel(user) {
  if (!user) return "";
  return user.full_name || user.username || user.email || `#${user.id_user ?? user.id}`;
}

/**
 * Gestor de equipos (Team): equipo de usuarios distinto de la columna
 * `menu_group` (esa es solo agrupacion visual del menu). Un equipo agrupa
 * usuarios para el alcance "Mis grupos" del gestor de roles/permisos -- este
 * cambio (Fase 1) solo entrega la entidad y la membresia; el filtrado real
 * por equipo todavia no esta conectado (ver ARQUITECTURA_TYAKXA_TNY.md).
 *
 * Equipos y membresias se dan de baja, no se borran: cada periodo de una
 * persona en un equipo es una fila (`creation_date` -> `deletion_date`), y los
 * KPIs de asistencia atribuyen cada marca al equipo que la persona tenia
 * entonces. Quitar a alguien y volver a agregarlo crea una membresia nueva.
 */
export default function TeamManagerPage() {
  const { t } = useI18n();
  const [teams, setTeams] = useState([]);
  const [users, setUsers] = useState([]);
  const [memberships, setMemberships] = useState([]);
  const [selectedTeamId, setSelectedTeamId] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [teamFormOpen, setTeamFormOpen] = useState(false);
  const [editingTeamId, setEditingTeamId] = useState(null);
  const [teamDescription, setTeamDescription] = useState("");
  const [memberQuery, setMemberQuery] = useState("");

  async function loadAll() {
    setLoading(true); setError("");
    try {
      const [teamPayload, userPayload, membershipPayload] = await Promise.all([
        fetchAllPages(getAllTeam),
        fetchAllPages(getAllUser),
        fetchAllPages(getAllNmTeamUser)
      ]);
      setTeams(asItems(teamPayload));
      setUsers(asItems(userPayload));
      setMemberships(asItems(membershipPayload));
    } catch (err) {
      setError(t(err.message, err.message || "No se pudo cargar el gestor de equipos"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadAll(); }, []);

  useEffect(() => {
    if (!selectedTeamId && teams.length) setSelectedTeamId(String(teams[0].id_team));
  }, [teams, selectedTeamId]);

  const selectedTeam = useMemo(
    () => teams.find((team) => String(team.id_team) === String(selectedTeamId)) || null,
    [teams, selectedTeamId]
  );

  const membershipsForSelectedTeam = useMemo(
    () => memberships.filter((row) => String(row.id_team) === String(selectedTeamId)),
    [memberships, selectedTeamId]
  );

  const memberUserIds = useMemo(
    () => new Set(membershipsForSelectedTeam.map((row) => String(row.id_user))),
    [membershipsForSelectedTeam]
  );

  const usersById = useMemo(() => new Map(users.map((user) => [String(user.id_user ?? user.id), user])), [users]);

  const memberRows = useMemo(
    () => membershipsForSelectedTeam
      .map((row) => ({ membership: row, user: usersById.get(String(row.id_user)) }))
      .sort((left, right) => userLabel(left.user).localeCompare(userLabel(right.user))),
    [membershipsForSelectedTeam, usersById]
  );

  const nonMemberUsers = useMemo(() => {
    const needle = memberQuery.trim().toLowerCase();
    return users
      .filter((user) => !memberUserIds.has(String(user.id_user ?? user.id)))
      .filter((user) => !needle || userLabel(user).toLowerCase().includes(needle))
      .sort((left, right) => userLabel(left).localeCompare(userLabel(right)));
  }, [users, memberUserIds, memberQuery]);

  function openNewTeam() {
    setEditingTeamId(null);
    setTeamDescription("");
    setTeamFormOpen(true);
    setNotice(""); setError("");
  }

  function openEditTeam(team) {
    setEditingTeamId(team.id_team);
    setTeamDescription(team.team_description || "");
    setTeamFormOpen(true);
    setNotice(""); setError("");
  }

  async function handleSaveTeam(event) {
    event.preventDefault();
    if (!teamDescription.trim()) {
      setError(t("errors.validation_failed", "Completa los campos obligatorios"));
      return;
    }
    setSaving(true); setError(""); setNotice("");
    try {
      const payload = { team_description: teamDescription.trim() };
      let saved = null;
      if (editingTeamId) saved = await updateTeam(editingTeamId, payload);
      else saved = await createTeam(payload);
      await loadAll();
      const nextId = saved?.id_team || editingTeamId;
      if (nextId) setSelectedTeamId(String(nextId));
      setTeamFormOpen(false);
      setNotice(t("common.team_saved", "Equipo guardado correctamente"));
    } catch (err) {
      setError(t(err.message, err.message || "No se pudo guardar el equipo"));
    } finally {
      setSaving(false);
    }
  }

  // Dar de baja un equipo NO lo borra: el servidor le pone fecha de baja a el y a sus membresias vigentes (en un solo
  // paso, por eso aqui ya no se quitan los miembros uno por uno). Queda la historia de quien estuvo en que equipo, y
  // con ella las checadas de antes se siguen atribuyendo a ese equipo.
  async function handleDeleteTeam(team) {
    if (!window.confirm(t("common.confirm_delete_team", `¿Dar de baja el equipo "${team.team_description}"? Sus miembros dejan de pertenecer a él; la historia de quién estuvo en el equipo se conserva.`))) return;
    setSaving(true); setError(""); setNotice("");
    try {
      await deleteTeam(team.id_team);
      if (String(selectedTeamId) === String(team.id_team)) setSelectedTeamId("");
      await loadAll();
      setNotice(t("common.team_deleted", "Equipo dado de baja correctamente"));
    } catch (err) {
      setError(t(err.message, err.message || "No se pudo dar de baja el equipo"));
    } finally {
      setSaving(false);
    }
  }

  async function addMember(user) {
    if (!selectedTeamId) return;
    setError(""); setNotice("");
    try {
      await createNmTeamUser({ id_team: Number(selectedTeamId), id_user: Number(user.id_user ?? user.id) });
      await loadAll();
    } catch (err) {
      setError(t(err.message, err.message || "No se pudo agregar el miembro"));
    }
  }

  async function removeMember(membershipRow) {
    if (!membershipRow?.id_nm_team_user) return;
    setError(""); setNotice("");
    try {
      await deleteNmTeamUser(membershipRow.id_nm_team_user);
      await loadAll();
    } catch (err) {
      setError(t(err.message, err.message || "No se pudo quitar el miembro"));
    }
  }

  return (
    <section className="entity-page team-manager">
      <PageHeader
        eyebrow={"RBAC"}
        titulo={t("common.team_manager", "Gestor de equipos")}
        subtitulo={t("common.team_manager_body", "Agrupa usuarios en equipos. Sirve de base para el alcance \"Mis grupos\" del gestor de roles y permisos.")}
      >
        <button className="button primary" type="button" onClick={openNewTeam}><Plus size={16} />{t("common.new_team", "Nuevo equipo")}</button>
      </PageHeader>

      {notice && <div className="alert success">{notice}</div>}
      {error && <div className="alert error">{error}</div>}

      {teamFormOpen && (
        <form className="form-card" onSubmit={handleSaveTeam}>
          <div className="form-header"><strong>{editingTeamId ? t("common.edit_team", "Editar equipo") : t("common.new_team", "Nuevo equipo")}</strong><button className="button ghost" type="button" onClick={() => setTeamFormOpen(false)}><X size={16} /></button></div>
          <div className="form-grid">
            <label className="field">
              <span>{t("fields.team.team_description", "Nombre del equipo")}</span>
              <input required maxLength={150} value={teamDescription} onChange={(event) => setTeamDescription(event.target.value)} placeholder={t("common.team_name_placeholder", "Ej. Taller nocturno")} />
            </label>
          </div>
          <div className="form-actions">
            <button className="button primary" type="submit" disabled={saving}>{saving ? t("common.loading", "Cargando...") : t("common.save", "Guardar")}</button>
            <button className="button" type="button" onClick={() => setTeamFormOpen(false)}>{t("common.cancel", "Cancelar")}</button>
          </div>
        </form>
      )}

      {loading ? <div className="empty">{t("common.loading", "Cargando...")}</div> : (
        <div className="team-manager-workspace">
          <article className="table-card">
            <div className="form-header"><Users size={18} /><strong>{t("common.teams", "Equipos")}</strong></div>
            {teams.length === 0 ? <div className="empty">{t("common.no_teams", "Todavía no hay equipos. Crea el primero.")}</div> : (
              <div className="team-list">
                {teams.map((team) => (
                  <div
                    key={team.id_team}
                    className={`team-list-row ${String(selectedTeamId) === String(team.id_team) ? "selected-row" : ""}`}
                    onClick={() => setSelectedTeamId(String(team.id_team))}
                  >
                    <span>{team.team_description}</span>
                    <span className="row-actions">
                      <button type="button" onClick={(event) => { event.stopPropagation(); openEditTeam(team); }} title={t("common.edit", "Editar")}><Pencil size={14} /></button>
                      <button type="button" onClick={(event) => { event.stopPropagation(); handleDeleteTeam(team); }} title={t("common.delete", "Eliminar")}><Trash2 size={14} /></button>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </article>

          <article className="form-card">
            {!selectedTeam ? <p>{t("common.select_team", "Selecciona un equipo para administrar sus miembros.")}</p> : (
              <>
                <div className="form-header"><strong>{t("common.team_members", "Miembros de")} {selectedTeam.team_description}</strong></div>
                <div className="team-member-columns">
                  <div className="team-member-column">
                    <h4>{t("common.current_members", "Miembros actuales")} ({memberRows.length})</h4>
                    {memberRows.length === 0 ? <p className="muted-text">{t("common.no_members_yet", "Este equipo todavía no tiene miembros.")}</p> : memberRows.map(({ membership, user }) => (
                      <div className="team-member-row" key={membership.id_nm_team_user}>
                        <span>{user ? userLabel(user) : `#${membership.id_user}`}</span>
                        <button className="button ghost" type="button" onClick={() => removeMember(membership)} title={t("common.remove_member", "Quitar")}><UserMinus size={15} /></button>
                      </div>
                    ))}
                  </div>
                  <div className="team-member-column">
                    <h4>{t("common.add_members", "Agregar miembros")}</h4>
                    <input
                      className="team-member-search"
                      aria-label={t("common.search", "Buscar")}
                      value={memberQuery}
                      onChange={(event) => setMemberQuery(event.target.value)}
                      placeholder={t("common.search_users_placeholder", "Buscar usuario...")}
                    />
                    {nonMemberUsers.slice(0, 50).map((user) => (
                      <div className="team-member-row" key={user.id_user ?? user.id}>
                        <span>{userLabel(user)}</span>
                        <button className="button ghost" type="button" onClick={() => addMember(user)} title={t("common.add_member", "Agregar")}><UserPlus size={15} /></button>
                      </div>
                    ))}
                    {nonMemberUsers.length === 0 && <p className="muted-text">{t("common.no_more_users", "No hay más usuarios para agregar.")}</p>}
                  </div>
                </div>
              </>
            )}
          </article>
        </div>
      )}
    </section>
  );
}
