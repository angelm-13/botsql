import React, { useEffect, useMemo, useState } from "react";
import { ArrowRight, Eye, LayoutGrid, List, MessageSquare, Pencil, Plus, RefreshCw, Trash2, X } from "lucide-react";
import {
  addProyectMessage,
  createProyect,
  deleteProyect,
  getAllCustomerSupplier,
  getAllProyect,
  getAllUser,
  getMyPermissions,
  getProyect,
  transitionProyect,
  updateProyect,
} from "../api";
import { useI18n } from "../i18n";

/* eslint-disable react/prop-types */

const STATUS_CODES = ["draft", "submitted", "blocked", "authorized", "in_progress", "stopped", "completed", "denied"];
const TRANSITIONS = {
  supervisor: { draft: ["submitted"], blocked: ["submitted"] },
  manager: { submitted: ["authorized", "denied", "blocked"], blocked: ["authorized", "denied"] },
  workshop: { authorized: ["in_progress"], in_progress: ["stopped", "completed"], stopped: ["in_progress"] },
  unrestricted: {
    draft: ["submitted"], submitted: ["authorized", "denied", "blocked"], blocked: ["submitted", "authorized", "denied"],
    authorized: ["in_progress"], in_progress: ["stopped", "completed"], stopped: ["in_progress"],
  },
};
const NEEDS_REASON = new Set(["denied", "blocked", "stopped"]);
const EMPTY_FORM = { id_customer_supplier: "", leader: "", title: "", proyect_description: "" };

function transitionNoteKey(transition) {
  if (transition.target === "completed") return "final_note";
  if (transition.target === "stopped") return "stop_detail";
  if (transition.target === "in_progress" && transition.project.proyect_status === "stopped") return "resume_note";
  return "observation";
}

function listOf(payload) {
  return Array.isArray(payload) ? payload : payload?.items || [];
}

function storedUser() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch { return {}; }
}

function hasRead(rows, name) {
  const row = rows.find((item) => item.entity_name === name);
  return Boolean(Number(row?.control_type || 0) & 2);
}

function customerLabel(customer, fallbackLabel) {
  return customer?.name || customer?.business_name || customer?.commercial_name || `${fallbackLabel} #${customer?.id_customer_supplier}`;
}

function userLabel(user, fallbackId, fallbackLabel) {
  return user?.full_name || user?.username || user?.email || `${fallbackLabel} #${fallbackId}`;
}

function dateLabel(value) {
  return value ? new Date(value).toLocaleDateString(document.documentElement.lang || "es") : "-";
}

export default function ProjectManagementPage() {
  const { t } = useI18n();
  const projectText = (key) => t(`project_management.${key}`);
  const statusLabel = (status) => projectText(`status_${status}`);
  const actor = useMemo(storedUser, []);
  const privileged = Boolean(actor.is_superuser || actor.is_bootstrap_admin || actor.username === "admin1");
  const [permissions, setPermissions] = useState([]);
  const [items, setItems] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [users, setUsers] = useState([]);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [supervisorFilter, setSupervisorFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sort, setSort] = useState("-last_update_date");
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [total, setTotal] = useState(0);
  const [view, setView] = useState("table");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [transition, setTransition] = useState(null);
  const [detail, setDetail] = useState(null);
  const [message, setMessage] = useState("");

  const mode = privileged ? "unrestricted" : hasRead(permissions, "project_authorization") ? "manager" : hasRead(permissions, "project_execution") ? "workshop" : "supervisor";
  const projectPermission = permissions.find((item) => item.entity_name === "proyect");
  const canCreate = privileged || Boolean(Number(projectPermission?.control_type || 0) & 1);
  const canDelete = privileged || Boolean(Number(projectPermission?.control_type || 0) & 8);
  const customerById = useMemo(() => Object.fromEntries(customers.map((item) => [item.id_customer_supplier, item])), [customers]);
  const userById = useMemo(() => Object.fromEntries(users.map((item) => [item.id_user, item])), [users]);
  const filtered = items;

  async function loadData(nextPage = page, nextPerPage = perPage) {
    setLoading(true);
    setError("");
    try {
      const payload = await getAllProyect({
        page: nextPage,
        per_page: nextPerPage,
        sort,
        search: query.trim() || undefined,
        proyect_status: statusFilter || undefined,
        created_by: supervisorFilter || undefined,
        creation_date_from: dateFrom || undefined,
        creation_date_to: dateTo || undefined,
      });
      setItems(listOf(payload));
      setTotal(Number(payload?.total ?? listOf(payload).length));
      setPage(nextPage);
    } catch (requestError) {
      setError(requestError.message || projectText("error_load"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    async function initialize() {
      try {
        const [permissionPayload, customerPayload, userPayload] = await Promise.all([
          privileged ? Promise.resolve({ entity_permissions: [] }) : getMyPermissions(),
          getAllCustomerSupplier({ page: 1, per_page: 100 }),
          getAllUser({ page: 1, per_page: 100 }),
        ]);
        setPermissions(permissionPayload.entity_permissions || []);
        setCustomers(listOf(customerPayload));
        setUsers(listOf(userPayload));
      } catch (requestError) {
        setError(requestError.message || projectText("error_prepare"));
      }
      await loadData();
    }
    initialize();
  }, [privileged]);

  useEffect(() => {
    if (mode === "workshop") setView("board");
  }, [mode]);

  function openCreate() {
    setEditingId(null);
    setForm({ ...EMPTY_FORM, leader: actor.id_user || "" });
    setShowForm(true);
  }

  function openEdit(project) {
    setEditingId(project.id_proyect);
    setForm({ id_customer_supplier: project.id_customer_supplier, leader: project.leader, title: project.title || "", proyect_description: project.proyect_description || "" });
    setShowForm(true);
  }

  async function saveProject(event) {
    event.preventDefault();
    setBusyId(editingId || "new");
    setError("");
    try {
      if (editingId) await updateProyect(editingId, form);
      else await createProyect(form);
      setShowForm(false);
      setForm(EMPTY_FORM);
      setEditingId(null);
      await loadData();
    } catch (requestError) {
      setError(requestError.message || projectText("error_save"));
    } finally {
      setBusyId(null);
    }
  }

  async function removeProject(project) {
    if (!window.confirm(`${projectText("confirm_delete")} ${project.title || projectText("project")}?`)) return;
    setBusyId(project.id_proyect);
    try { await deleteProyect(project.id_proyect); await loadData(); }
    catch (requestError) { setError(requestError.message); }
    finally { setBusyId(null); }
  }

  async function applyTransition(event) {
    event.preventDefault();
    setBusyId(transition.project.id_proyect);
    setError("");
    try {
      await transitionProyect(transition.project.id_proyect, {
        status: transition.target,
        reason: transition.reason,
        content: transition.content,
        review_date: transition.reviewDate,
      });
      setTransition(null);
      await loadData();
      if (detail?.id_proyect === transition.project.id_proyect) setDetail(await getProyect(transition.project.id_proyect));
    } catch (requestError) {
      setError(requestError.message || projectText("error_transition"));
    } finally {
      setBusyId(null);
    }
  }

  async function openDetail(project) {
    setBusyId(project.id_proyect);
    try { setDetail(await getProyect(project.id_proyect)); }
    catch (requestError) { setError(requestError.message); }
    finally { setBusyId(null); }
  }

  async function sendMessage(event) {
    event.preventDefault();
    if (!message.trim()) return;
    setBusyId(detail.id_proyect);
    try {
      await addProyectMessage(detail.id_proyect, { content: message });
      setMessage("");
      setDetail(await getProyect(detail.id_proyect));
    } catch (requestError) { setError(requestError.message); }
    finally { setBusyId(null); }
  }

  function actionTargets(project) {
    return TRANSITIONS[mode]?.[project.proyect_status] || [];
  }

  function applyFilters(event) {
    event.preventDefault();
    loadData(1);
  }

  function ProjectActions({ project }) {
    const targets = actionTargets(project);
    return <div className="project-actions">
      <button className="icon-button" type="button" title={projectText("view_detail")} onClick={() => openDetail(project)}><Eye size={16} /></button>
      {(mode === "supervisor" || mode === "unrestricted") && ["draft", "blocked"].includes(project.proyect_status) && <button className="icon-button" type="button" title={projectText("edit")} onClick={() => openEdit(project)}><Pencil size={16} /></button>}
      {canDelete && project.proyect_status === "draft" && <button className="icon-button danger" type="button" title={projectText("delete")} onClick={() => removeProject(project)}><Trash2 size={16} /></button>}
      {targets.length > 0 && <label className="project-transition"><ArrowRight size={15} /><select value="" disabled={busyId === project.id_proyect} onChange={(event) => event.target.value && setTransition({ project, target: event.target.value, reason: "", content: "", reviewDate: "" })} aria-label={`${projectText("change_status")}: ${project.title}`}><option value="">{projectText("change_status")}</option>{targets.map((target) => <option value={target} key={target}>{statusLabel(target)}</option>)}</select></label>}
    </div>;
  }

  return <section className="entity-page project-management">
    <div className="page-heading">
      <div><p className="eyebrow">{projectText("operations")}</p><h2>{projectText("title")}</h2><p className="muted">{projectText(mode === "manager" ? "subtitle_manager" : mode === "workshop" ? "subtitle_workshop" : "subtitle_supervisor")}</p></div>
      <div className="project-heading-actions">{canCreate && <button className="button primary" type="button" onClick={openCreate}><Plus size={16} />{projectText("new_project")}</button>}<button className="button ghost" type="button" onClick={() => loadData(page)}><RefreshCw size={16} />{t("common.refresh")}</button></div>
    </div>

    <form className="project-toolbar" onSubmit={applyFilters}>
      <div className="search-box"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={projectText("search")} /></div>
      <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label={projectText("filter_status")}><option value="">{projectText("all_statuses")}</option>{STATUS_CODES.map((value) => <option key={value} value={value}>{statusLabel(value)}</option>)}</select>
      {(mode === "manager" || mode === "unrestricted") && <select value={supervisorFilter} onChange={(event) => setSupervisorFilter(event.target.value)} aria-label={projectText("filter_supervisor")}><option value="">{projectText("all_supervisors")}</option>{users.map((user) => <option key={user.id_user} value={user.id_user}>{userLabel(user, user.id_user, projectText("user"))}</option>)}</select>}
      <label className="field compact"><span>{projectText("from")}</span><input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} /></label>
      <label className="field compact"><span>{projectText("to")}</span><input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} /></label>
      <select value={sort} onChange={(event) => setSort(event.target.value)} aria-label={projectText("sort")}><option value="-last_update_date">{projectText("sort_recent")}</option><option value="creation_date">{projectText("sort_created_asc")}</option><option value="-creation_date">{projectText("sort_created_desc")}</option><option value="title">{projectText("sort_name_asc")}</option><option value="-title">{projectText("sort_name_desc")}</option><option value="proyect_status">{projectText("sort_status")}</option></select>
      <button className="button" type="submit">{projectText("apply")}</button>
      <div className="project-view-toggle" role="tablist" aria-label={projectText("view")}><button type="button" className={view === "table" ? "active" : ""} onClick={() => setView("table")} title={projectText("table")}><List size={17} /></button><button type="button" className={view === "board" ? "active" : ""} onClick={() => setView("board")} title={projectText("board")}><LayoutGrid size={17} /></button></div>
    </form>

    {error && <div className="alert error">{t(error, error)}</div>}
    {loading && <div className="alert">{projectText("loading")}</div>}
    {!loading && !filtered.length && <div className="empty"><strong>{projectText("empty")}</strong><p>{projectText("empty_body")}</p></div>}

    {!loading && filtered.length > 0 && view === "table" && <div className="table-card"><div className="table-wrap"><table><thead><tr><th>{projectText("folio")}</th><th>{projectText("project")}</th><th>{projectText("customer")}</th><th>{projectText("supervisor")}</th><th>{projectText("created")}</th><th>{projectText("submitted")}</th><th>{projectText("status")}</th><th>{projectText("updated")}</th><th>{projectText("actions")}</th></tr></thead><tbody>{filtered.map((project) => <tr key={project.id_proyect}><td><strong>{project.folio || `PRJ-${String(project.id_proyect).padStart(6, "0")}`}</strong></td><td><strong>{project.title || `${projectText("project")} #${project.id_proyect}`}</strong><p className="cell-value">{project.proyect_description}</p></td><td>{customerLabel(customerById[project.id_customer_supplier], projectText("customer"))}</td><td>{userLabel(userById[project.created_by], project.created_by, projectText("user"))}</td><td>{dateLabel(project.creation_date)}</td><td>{dateLabel(project.submitted_date)}</td><td><span className={`project-status status-${project.proyect_status}`}>{statusLabel(project.proyect_status)}</span></td><td>{dateLabel(project.last_update_date)}</td><td><ProjectActions project={project} /></td></tr>)}</tbody></table></div></div>}

    {!loading && view === "board" && <div className="project-board">{STATUS_CODES.map((status) => { const cards = filtered.filter((project) => project.proyect_status === status); return <section className={`project-column status-${status}`} key={status}><header><strong>{statusLabel(status)}</strong><span>{cards.length}</span></header><div>{cards.map((project) => <article className="project-card" key={project.id_proyect}><strong>{project.title || `${projectText("project")} #${project.id_proyect}`}</strong><p>{customerLabel(customerById[project.id_customer_supplier], projectText("customer"))}</p><small>{project.proyect_description}</small><ProjectActions project={project} /></article>)}{!cards.length && <p className="project-column-empty">{projectText("no_projects")}</p>}</div></section>; })}</div>}

    {!loading && total > 0 && <div className="pagination"><button className="button" type="button" disabled={page <= 1} onClick={() => loadData(page - 1)}>{projectText("previous")}</button><span>{projectText("page")} {page} / {Math.max(Math.ceil(total / perPage), 1)}</span><select value={perPage} onChange={(event) => { const nextPerPage = Number(event.target.value); setPerPage(nextPerPage); loadData(1, nextPerPage); }} aria-label={projectText("per_page")}><option value={10}>10</option><option value={20}>20</option><option value={50}>50</option><option value={100}>100</option></select><button className="button" type="button" disabled={page * perPage >= total} onClick={() => loadData(page + 1)}>{projectText("next")}</button></div>}

    {showForm && <div className="project-modal-backdrop" role="presentation"><form className="project-modal" onSubmit={saveProject}><header><div><p className="eyebrow">{projectText("project")}</p><h3>{projectText(editingId ? "edit_project" : "new_project")}</h3></div><button className="icon-button" type="button" onClick={() => setShowForm(false)} aria-label={projectText("close")}><X size={18} /></button></header><div className="form-grid"><label className="field"><span>{projectText("title_field")}</span><input required maxLength={50} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label><label className="field"><span>{projectText("customer")}</span><select required value={form.id_customer_supplier} onChange={(event) => setForm({ ...form, id_customer_supplier: event.target.value })}><option value="">{projectText("select_customer")}</option>{customers.map((customer) => <option key={customer.id_customer_supplier} value={customer.id_customer_supplier}>{customerLabel(customer, projectText("customer"))}</option>)}</select></label><label className="field"><span>{projectText("responsible")}</span><select value={form.leader} onChange={(event) => setForm({ ...form, leader: event.target.value })}><option value="">{projectText("current_user")}</option>{users.map((user) => <option key={user.id_user} value={user.id_user}>{user.full_name || user.username || user.email}</option>)}</select></label><label className="field wide"><span>{projectText("description")}</span><textarea required maxLength={200} rows={4} value={form.proyect_description} onChange={(event) => setForm({ ...form, proyect_description: event.target.value })} /></label></div><footer><button className="button" type="button" onClick={() => setShowForm(false)}>{projectText("cancel")}</button><button className="button primary" disabled={busyId !== null}>{projectText("save")}</button></footer></form></div>}

    {transition && <div className="project-modal-backdrop" role="presentation"><form className="project-modal compact" onSubmit={applyTransition}><header><div><p className="eyebrow">{projectText("status_change")}</p><h3>{statusLabel(transition.target)}</h3></div><button className="icon-button" type="button" onClick={() => setTransition(null)} aria-label={projectText("close")}><X size={18} /></button></header><p>{transition.project.title || `${projectText("project")} #${transition.project.id_proyect}`}</p>{NEEDS_REASON.has(transition.target) && <label className="field"><span>{projectText("reason")}</span><textarea required rows={3} value={transition.reason} onChange={(event) => setTransition({ ...transition, reason: event.target.value })} /></label>}<label className="field"><span>{projectText(transitionNoteKey(transition))}</span><textarea rows={3} value={transition.content} onChange={(event) => setTransition({ ...transition, content: event.target.value })} /></label>{transition.target === "blocked" && <label className="field"><span>{projectText("review_date")}</span><input type="datetime-local" value={transition.reviewDate} onChange={(event) => setTransition({ ...transition, reviewDate: event.target.value })} /></label>}<footer><button className="button" type="button" onClick={() => setTransition(null)}>{projectText("cancel")}</button><button className="button primary" disabled={busyId !== null}>{projectText("confirm_change")}</button></footer></form></div>}

    {detail && <div className="project-modal-backdrop" role="presentation"><aside className="project-detail-panel"><header><div><p className="eyebrow">{projectText("record")} #{detail.id_proyect}</p><h3>{detail.title || projectText("project")}</h3></div><button className="icon-button" type="button" onClick={() => setDetail(null)} aria-label={projectText("close")}><X size={18} /></button></header><span className={`project-status status-${detail.proyect_status}`}>{statusLabel(detail.proyect_status)}</span><p>{detail.proyect_description}</p><h4>{projectText("tasks")}</h4>{detail.tasks?.length ? detail.tasks.map((task) => <div className="project-detail-row" key={task.id_task}><strong>{task.title || task.task_code || `${projectText("task")} #${task.id_task}`}</strong><span>{task.task_status || projectText("no_status")}</span></div>) : <p className="muted">{projectText("no_tasks")}</p>}<h4>{projectText("history")}</h4><div className="project-timeline">{detail.events?.slice().reverse().map((event) => <div key={event.id_proyect_event}><span>{new Date(event.creation_date).toLocaleString(document.documentElement.lang || "es")}</span><strong>{event.event_type === "status_changed" ? `${statusLabel(event.previous_status)} → ${statusLabel(event.new_status)}` : projectText(event.event_type === "message" ? "message" : "created_event")}</strong>{(event.reason || event.content) && <p>{event.reason || event.content}</p>}</div>)}</div><form className="project-message" onSubmit={sendMessage}><label className="field"><span>{projectText("new_message")}</span><textarea rows={2} value={message} onChange={(event) => setMessage(event.target.value)} placeholder={projectText("message_placeholder")} /></label><button className="button primary" disabled={!message.trim() || busyId !== null}><MessageSquare size={16} />{projectText("publish")}</button></form></aside></div>}
  </section>;
}