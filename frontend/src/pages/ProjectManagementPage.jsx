import { useEffect, useMemo, useState } from "react";
import { ArrowRight, ChevronRight, Eye, Hand, Undo2, LayoutGrid, List, MessageSquare, Pencil, Plus, RefreshCw, Trash2, X } from "lucide-react";
import {
  addProyectMessage,
  addTaskNote,
  createProyect,
  deleteProyect,
  getCustomerContactOptions,
  getCustomerSupplierOptions,
  getAllProyect,
  getUserOptions,
  getMyPermissions,
  getOperationsCatalog,
  getProyect,
  getQuotationOptions,
  getTaskNotes,
  releaseProyect,
  takeProyect,
  transitionProyect,
  transitionTask,
  updateProyect,
} from "../api";
import { useI18n } from "../i18n";
import ProyectoExpediente from "../components/ProyectoExpediente.jsx";
import PageHeader from "../components/PageHeader.jsx";

/* eslint-disable react/prop-types */

// En que orden se leen las columnas del tablero. Es presentacion, y el servidor
// no la conoce: el catalogo dice cuales existen, esto en que orden se pintan.
// Un estatus que el catalogo traiga y esta lista no nombre se pinta al final,
// en vez de desaparecer del tablero.
const STATUS_ORDER = ["draft", "submitted", "blocked", "authorized", "in_progress", "stopped", "completed", "denied"];
const TASK_STATUS_ORDER = ["pendiente", "en_proceso", "bloqueada", "en_revision", "terminada", "cancelada"];

// Lo que cada papel puede PEDIR, con los mismos grupos que comprueba
// `transition_project` en el servidor: quien autoriza y quien ejecuta.
// Supervisor no tiene ninguno a proposito -- Gerente es quien saca el
// proyecto de Borrador, al recibir la orden de compra, no Supervisor.
//
// De que estatus sale cada transicion ya NO se repite aqui: se lee de
// /operations/catalog. Antes esta pantalla llevaba una copia completa de
// PROJECT_TRANSITIONS en JavaScript, y dos copias de una maquina de estados
// divergen: la interfaz acaba ofreciendo un paso que el servidor rechaza, o
// escondiendo uno que si es valido.
const ROLE_TARGETS = {
  // Vacio, no ausente: si la clave faltara, `actionTargets()` caeria en
  // "sin limite de papel" y le ofreceria a Supervisor lo que sea que el
  // catalogo del servidor traiga para el estado actual.
  supervisor: [],
  manager: ["authorized", "denied", "blocked"],
  // "blocked" tambien para el taller: puede bloquear un proyecto que ya esta
  // en curso, no solo Gerente rechazandolo antes de iniciar. Ver el candado
  // real en `transition_project` (backend).
  workshop: ["in_progress", "stopped", "completed", "blocked"],
  // `unrestricted` no aparece: sin limite de papel, manda el catalogo solo.
};
// Los campos de la ORDEN DE TRABAJO se agregan aqui a proposito, y no en una
// pantalla propia: son atributos del proyecto, no otra entidad. Todos
// opcionales salvo lo que ya era obligatorio -- un proyecto se puede crear
// antes de tener folio asignado, y completarse despues.
//
// `leader` (responsable) NO esta aqui: siempre es quien crea el proyecto, sin
// selector -- se muestra fijo, nunca se manda en el payload. `id_supervisor`
// tampoco: ya no se asigna desde aqui, el supervisor TOMA el proyecto desde
// la lista. `purchase_order`/`purchase_order_item` solo se muestran y se
// mandan cuando edita Gerente (ver `mode` en el JSX del modal); para
// Supervisor quedan siempre vacios.
const EMPTY_FORM = {
  id_customer_contact: "", title: "", proyect_description: "",
  folio: "", id_quotation: "", purchase_order: "",
  purchase_order_item: "", delivery_date: "",
};

function orderedStatuses(fromServer, order) {
  if (!fromServer?.length) return order;
  const rank = (status) => (order.indexOf(status) === -1 ? order.length : order.indexOf(status));
  return [...fromServer].sort((a, b) => rank(a) - rank(b));
}

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
  return Number(row?.scope_read || 0) !== 0;
}

function customerLabel(customer, fallbackLabel) {
  return customer?.name || customer?.business_name || customer?.commercial_name || `${fallbackLabel} #${customer?.id_customer_supplier}`;
}

function contactLabel(contact, fallbackLabel) {
  return contact?.label || contact?.full_name || `${fallbackLabel} #${contact?.id_customer_contact}`;
}

function userLabel(user, fallbackId, fallbackLabel) {
  return user?.full_name || user?.username || user?.email || `${fallbackLabel} #${fallbackId}`;
}

function quotationLabel(quotation, customerById) {
  const folio = quotation.folio || `COT-${String(quotation.id_invoice).padStart(6, "0")}`;
  const customer = customerById[quotation.id_customer_supplier];
  return customer ? `${folio} — ${customerLabel(customer, "")}` : folio;
}

function dateLabel(value) {
  return value ? new Date(value).toLocaleDateString(document.documentElement.lang || "es") : "-";
}

export default function ProjectManagementPage() {
  const { t } = useI18n();
  const projectText = (key) => t(`project_management.${key}`);
  const statusLabel = (status) => projectText(`status_${status}`);
  // El estatus de tarea puede traer texto libre de cuando el campo no
  // validaba: si no esta en el catalogo se muestra tal cual, en vez de la
  // clave de traduccion sin resolver.
  const taskStatusLabel = (status) => (
    !status ? projectText("no_status")
      : TASK_STATUS_ORDER.includes(status) ? projectText(`task_status_${status}`)
      : status
  );
  const taskLabel = (task) => task.title || task.task_code || `${projectText("task")} #${task.id_task}`;

  function eventTitle(event) {
    if (event.event_type === "status_changed") return `${statusLabel(event.previous_status)} → ${statusLabel(event.new_status)}`;
    if (event.event_type === "task_status_changed") return `${projectText("task")}: ${taskStatusLabel(event.previous_status)} → ${taskStatusLabel(event.new_status)}`;
    if (event.event_type === "task_note") return projectText("task_note_event");
    return projectText(event.event_type === "message" ? "message" : "created_event");
  }
  const actor = useMemo(storedUser, []);
  const privileged = Boolean(actor.is_superuser || actor.is_bootstrap_admin || actor.username === "admin1");
  const [permissions, setPermissions] = useState([]);
  const [items, setItems] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [contacts, setContacts] = useState([]);
  const [quotations, setQuotations] = useState([]);
  const [users, setUsers] = useState([]);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [creatorFilter, setCreatorFilter] = useState("");
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
  // Solo para mostrar "Responsable" fijo en el modal -- nunca se manda en el
  // payload, `leader` ya no es un campo del formulario.
  const [editingLeader, setEditingLeader] = useState(null);
  const [transition, setTransition] = useState(null);
  const [detail, setDetail] = useState(null);
  const [message, setMessage] = useState("");
  // Las maquinas de estado, tal como las valida el servidor.
  const [catalog, setCatalog] = useState(null);
  // La tarea abierta desde el expediente, con su bitacora. Aqui se cierra el
  // flujo: proyecto -> tarea -> nota. Las notas viven en `task_note`, cuya
  // columna `id_task` es NOT NULL, o sea que una nota no existe sin su tarea;
  // con pantalla propia habia que abrir una tercera lista y elegir la tarea en
  // un desplegable para escribir una, y la bitacora no se leia junta.
  const [taskDetail, setTaskDetail] = useState(null);
  const [taskTransition, setTaskTransition] = useState(null);
  const [taskNote, setTaskNote] = useState("");

  const mode = privileged ? "unrestricted" : hasRead(permissions, "project_authorization") ? "manager" : hasRead(permissions, "project_execution") ? "workshop" : "supervisor";
  const statusCodes = useMemo(() => orderedStatuses(catalog?.proyect?.statuses, STATUS_ORDER), [catalog]);
  const needsReason = (target) => (catalog?.proyect?.reason_required || []).includes(target);
  const taskNeedsReason = (target) => (catalog?.task?.reason_required || []).includes(target);
  const projectPermission = permissions.find((item) => item.entity_name === "proyect");
  const canCreate = privileged || Number(projectPermission?.scope_create || 0) !== 0;
  const canDelete = privileged || Number(projectPermission?.scope_delete || 0) !== 0;
  const customerById = useMemo(() => Object.fromEntries(customers.map((item) => [item.id_customer_supplier, item])), [customers]);
  const userById = useMemo(() => Object.fromEntries(users.map((item) => [item.id_user, item])), [users]);
  const canEditManagement = mode === "manager" || mode === "unrestricted";
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
        created_by: creatorFilter || undefined,
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
        // Cada llamada se atrapa por separado: un rol como Supervisor no
        // tiene lectura de customer_supplier ni de user (a proposito, ver
        // la matriz de roles), y antes un solo 403 ahi tumbaba el
        // Promise.all completo -incluido getMyPermissions()-, dejando
        // `permissions` vacio para siempre y el boton de crear invisible
        // aunque el permiso real del rol si alcanzara.
        const [permissionPayload, customerPayload, contactPayload, userPayload, catalogPayload, quotationPayload] = await Promise.all([
          privileged ? Promise.resolve({ entity_permissions: [] }) : getMyPermissions().catch(() => ({ entity_permissions: [] })),
          getCustomerSupplierOptions().catch(() => []),
          getCustomerContactOptions().catch(() => []),
          getUserOptions().catch(() => []),
          // Si el catalogo no llega, `statusCodes` cae en STATUS_ORDER y los
          // cambios de estatus quedan sin ofrecer, no ofrecidos a ciegas: el
          // servidor los rechazaria y el mensaje seria peor.
          getOperationsCatalog().catch(() => null),
          getQuotationOptions().catch(() => []),
        ]);
        setPermissions(permissionPayload.entity_permissions || []);
        setCustomers(listOf(customerPayload));
        setContacts(listOf(contactPayload));
        setUsers(listOf(userPayload));
        setCatalog(catalogPayload);
        setQuotations(listOf(quotationPayload));
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

  // Tomar el proyecto: el servidor decide si el actor puede -- capacidad
  // `project_execution` -- y pone su propio id. Aqui solo se dispara.
  async function tomarProyecto(project) {
    setBusyId(project.id_proyect);
    setError("");
    try {
      await takeProyect(project.id_proyect);
      await loadData();
    } catch (requestError) {
      setError(requestError.message || projectText("error_save"));
    } finally {
      setBusyId(null);
    }
  }

  async function soltarProyecto(project) {
    setBusyId(project.id_proyect);
    setError("");
    try {
      await releaseProyect(project.id_proyect);
      await loadData();
    } catch (requestError) {
      setError(requestError.message || projectText("error_save"));
    } finally {
      setBusyId(null);
    }
  }

  function openCreate() {
    setEditingId(null);
    setEditingLeader(actor.id_user || null);
    setForm(EMPTY_FORM);
    setShowForm(true);
  }

  function openEdit(project) {
    setEditingId(project.id_proyect);
    setEditingLeader(project.leader || null);
    setForm({
      id_customer_contact: project.id_customer_contact || "",
      title: project.title || "", proyect_description: project.proyect_description || "",
      folio: project.folio || "",
      id_quotation: project.id_quotation || "", purchase_order: project.purchase_order || "",
      purchase_order_item: project.purchase_order_item || "",
      delivery_date: project.delivery_date || "",
    });
    setShowForm(true);
  }

  async function saveProject(event) {
    event.preventDefault();
    setBusyId(editingId || "new");
    setError("");
    // Los numericos vacios no se mandan como "": el backend los toma como
    // llave ajena y "" no es un id valido. Igual que ya hace el formulario
    // del vale con sus campos opcionales.
    const numeroOpcional = (v) => (String(v ?? "").trim() === "" ? undefined : Number(v));
    const cuerpo = {
      ...form,
      id_customer_contact: numeroOpcional(form.id_customer_contact),
      id_quotation: numeroOpcional(form.id_quotation),
      // Orden de compra/partida solo los captura Gerente (`canEditManagement`);
      // para Supervisor el formulario ni los muestra, y aqui se manda
      // `undefined` para no pisar lo ya capturado con vacio.
      purchase_order_item: canEditManagement ? numeroOpcional(form.purchase_order_item) : undefined,
      purchase_order: canEditManagement ? (form.purchase_order.trim() || undefined) : undefined,
      folio: form.folio.trim() || undefined,
      delivery_date: form.delivery_date || undefined,
    };
    try {
      if (editingId) await updateProyect(editingId, cuerpo);
      else await createProyect(cuerpo);
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
    const desdeElServidor = catalog?.proyect?.transitions?.[project.proyect_status] || [];
    const permitidos = ROLE_TARGETS[mode];
    return permitidos ? desdeElServidor.filter((target) => permitidos.includes(target)) : desdeElServidor;
  }

  function taskActionTargets(task) {
    const transitions = catalog?.task?.transitions;
    if (!transitions) return [];
    const current = task.task_status || "";
    // Un estatus anterior al catalogo -texto libre, de cuando el campo no
    // validaba- puede moverse a cualquiera valido. Es lo que permite el
    // servidor en `validate_transition`, y la unica forma de regularizar un
    // registro ya capturado en vez de dejarlo atascado.
    return Object.prototype.hasOwnProperty.call(transitions, current)
      ? transitions[current]
      : Object.keys(transitions);
  }

  async function openTask(task) {
    setBusyId(task.id_task);
    setError("");
    try { setTaskDetail({ task, notes: listOf(await getTaskNotes(task.id_task)) }); }
    catch (requestError) { setError(requestError.message); }
    finally { setBusyId(null); }
  }

  function closeTask() {
    setTaskDetail(null);
    setTaskTransition(null);
    setTaskNote("");
  }

  async function refreshTask(taskId) {
    // El expediente del proyecto se recarga junto con la tarea: el cambio de
    // estatus y la nota quedan anotados en `proyect_event`, asi que la linea de
    // tiempo cambia al mismo tiempo que la tarea.
    const proyecto = detail ? await getProyect(detail.id_proyect) : null;
    if (proyecto) setDetail(proyecto);
    const actualizada = proyecto?.tasks?.find((item) => item.id_task === taskId);
    setTaskDetail({
      task: actualizada || taskDetail.task,
      notes: listOf(await getTaskNotes(taskId)),
    });
  }

  async function applyTaskTransition(event) {
    event.preventDefault();
    const taskId = taskTransition.task.id_task;
    setBusyId(taskId);
    setError("");
    try {
      await transitionTask(taskId, { status: taskTransition.target, reason: taskTransition.reason, content: taskTransition.content });
      setTaskTransition(null);
      await refreshTask(taskId);
    } catch (requestError) {
      setError(requestError.message || projectText("error_transition"));
    } finally {
      setBusyId(null);
    }
  }

  async function sendTaskNote(event) {
    event.preventDefault();
    if (!taskNote.trim()) return;
    const taskId = taskDetail.task.id_task;
    setBusyId(taskId);
    setError("");
    try {
      await addTaskNote(taskId, { task_note_description: taskNote });
      setTaskNote("");
      await refreshTask(taskId);
    } catch (requestError) {
      setError(requestError.message || projectText("error_save"));
    } finally {
      setBusyId(null);
    }
  }

  function applyFilters(event) {
    event.preventDefault();
    loadData(1);
  }

  function ProjectActions({ project }) {
    const targets = actionTargets(project);
    return <div className="project-actions">
      <button className="icon-button" type="button" title={projectText("view_detail")} onClick={() => openDetail(project)}><Eye size={16} /></button>
      {(((mode === "supervisor" || mode === "unrestricted") && ["draft", "blocked"].includes(project.proyect_status)) || canEditManagement) && <button className="icon-button" type="button" title={projectText("edit")} onClick={() => openEdit(project)}><Pencil size={16} /></button>}
      {canDelete && project.proyect_status === "draft" && <button className="icon-button danger" type="button" title={projectText("delete")} onClick={() => removeProject(project)}><Trash2 size={16} /></button>}
      {/* Tomar y soltar. Solo se ofrece a quien el servidor dejaria hacerlo --
          el taller, o sin restriccion -- para no ensenar un boton que devuelve
          403. El servidor lo vuelve a comprobar: esto es cortesia, no la
          medida de seguridad. */}
      {(mode === "workshop" || mode === "unrestricted") && !project.id_supervisor
        && <button className="icon-button" type="button" disabled={busyId === project.id_proyect} title={projectText("take")} onClick={() => tomarProyecto(project)}><Hand size={16} /></button>}
      {(mode === "workshop" || mode === "unrestricted") && Number(project.id_supervisor) === Number(actor.id_user)
        && <button className="icon-button" type="button" disabled={busyId === project.id_proyect} title={projectText("release")} onClick={() => soltarProyecto(project)}><Undo2 size={16} /></button>}
      {targets.length > 0 && <label className="project-transition"><ArrowRight size={15} /><select value="" disabled={busyId === project.id_proyect} onChange={(event) => event.target.value && setTransition({ project, target: event.target.value, reason: "", content: "", reviewDate: "" })} aria-label={`${projectText("change_status")}: ${project.title}`}><option value="">{projectText("change_status")}</option>{targets.map((target) => <option value={target} key={target}>{statusLabel(target)}</option>)}</select></label>}
    </div>;
  }

  return <section className="entity-page project-management">
    <PageHeader
        eyebrow={projectText("operations")}
        titulo={projectText("title")}
        subtitulo={projectText(mode === "manager" ? "subtitle_manager" : mode === "workshop" ? "subtitle_workshop" : "subtitle_supervisor")}
      >
        <div className="project-heading-actions">{canCreate && <button className="button primary" type="button" onClick={openCreate}><Plus size={16} />{projectText("new_project")}</button>}<button className="button ghost" type="button" onClick={() => loadData(page)}><RefreshCw size={16} />{t("common.refresh")}</button></div>
      </PageHeader>

    <form className="project-toolbar" onSubmit={applyFilters}>
      <div className="search-box"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={projectText("search")} /></div>
      <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label={projectText("filter_status")}><option value="">{projectText("all_statuses")}</option>{statusCodes.map((value) => <option key={value} value={value}>{statusLabel(value)}</option>)}</select>
      {(mode === "manager" || mode === "unrestricted") && <select value={creatorFilter} onChange={(event) => setCreatorFilter(event.target.value)} aria-label={projectText("filter_creator")}><option value="">{projectText("all_creators")}</option>{users.map((user) => <option key={user.id_user} value={user.id_user}>{userLabel(user, user.id_user, projectText("user"))}</option>)}</select>}
      <label className="field compact"><span>{projectText("from")}</span><input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} /></label>
      <label className="field compact"><span>{projectText("to")}</span><input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} /></label>
      <select value={sort} onChange={(event) => setSort(event.target.value)} aria-label={projectText("sort")}><option value="-last_update_date">{projectText("sort_recent")}</option><option value="creation_date">{projectText("sort_created_asc")}</option><option value="-creation_date">{projectText("sort_created_desc")}</option><option value="title">{projectText("sort_name_asc")}</option><option value="-title">{projectText("sort_name_desc")}</option><option value="proyect_status">{projectText("sort_status")}</option></select>
      <button className="button" type="submit">{projectText("apply")}</button>
      <div className="project-view-toggle" role="tablist" aria-label={projectText("view")}><button type="button" className={view === "table" ? "active" : ""} onClick={() => setView("table")} title={projectText("table")}><List size={17} /></button><button type="button" className={view === "board" ? "active" : ""} onClick={() => setView("board")} title={projectText("board")}><LayoutGrid size={17} /></button></div>
    </form>

    {error && <div className="alert error">{t(error, error)}</div>}
    {loading && <div className="alert">{projectText("loading")}</div>}
    {!loading && !filtered.length && <div className="empty"><strong>{projectText("empty")}</strong><p>{projectText("empty_body")}</p></div>}

    {!loading && filtered.length > 0 && view === "table" && <div className="table-card"><div className="table-wrap"><table><thead><tr><th>{projectText("folio")}</th><th>{projectText("project")}</th><th>{projectText("customer")}</th><th>{projectText("creator")}</th><th>{projectText("supervisor")}</th><th>{projectText("created")}</th><th>{projectText("submitted")}</th><th>{projectText("status")}</th><th>{projectText("updated")}</th><th>{projectText("actions")}</th></tr></thead><tbody>{filtered.map((project) => <tr key={project.id_proyect}><td><strong>{project.folio || `PRJ-${String(project.id_proyect).padStart(6, "0")}`}</strong></td><td><strong>{project.title || `${projectText("project")} #${project.id_proyect}`}</strong><p className="cell-value">{project.proyect_description}</p></td><td>{customerLabel(customerById[project.id_customer_supplier], projectText("customer"))}</td><td>{userLabel(userById[project.created_by], project.created_by, projectText("user"))}</td><td>{project.id_supervisor ? userLabel(userById[project.id_supervisor], project.id_supervisor, projectText("user")) : <span className="muted">{projectText("unassigned")}</span>}</td><td>{dateLabel(project.creation_date)}</td><td>{dateLabel(project.submitted_date)}</td><td><span className={`project-status status-${project.proyect_status}`}>{statusLabel(project.proyect_status)}</span></td><td>{dateLabel(project.last_update_date)}</td><td><ProjectActions project={project} /></td></tr>)}</tbody></table></div></div>}

    {!loading && view === "board" && <div className="project-board">{statusCodes.map((status) => { const cards = filtered.filter((project) => project.proyect_status === status); return <section className={`project-column status-${status}`} key={status}><header><strong>{statusLabel(status)}</strong><span>{cards.length}</span></header><div>{cards.map((project) => <article className="project-card" key={project.id_proyect}><strong>{project.title || `${projectText("project")} #${project.id_proyect}`}</strong><p>{customerLabel(customerById[project.id_customer_supplier], projectText("customer"))}</p><small>{project.proyect_description}</small><ProjectActions project={project} /></article>)}{!cards.length && <p className="project-column-empty">{projectText("no_projects")}</p>}</div></section>; })}</div>}

    {!loading && total > 0 && <div className="pagination"><button className="button" type="button" disabled={page <= 1} onClick={() => loadData(page - 1)}>{projectText("previous")}</button><span>{projectText("page")} {page} / {Math.max(Math.ceil(total / perPage), 1)}</span><select value={perPage} onChange={(event) => { const nextPerPage = Number(event.target.value); setPerPage(nextPerPage); loadData(1, nextPerPage); }} aria-label={projectText("per_page")}><option value={10}>10</option><option value={20}>20</option><option value={50}>50</option><option value={100}>100</option></select><button className="button" type="button" disabled={page * perPage >= total} onClick={() => loadData(page + 1)}>{projectText("next")}</button></div>}

    {showForm && <div className="project-modal-backdrop" role="presentation"><form className="project-modal" onSubmit={saveProject}><header><div><p className="eyebrow">{projectText("project")}</p><h3>{projectText(editingId ? "edit_project" : "new_project")}</h3></div><button className="icon-button" type="button" onClick={() => setShowForm(false)} aria-label={projectText("close")}><X size={18} /></button></header><div className="form-grid"><label className="field"><span>{projectText("title_field")}</span><input required maxLength={50} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label><label className="field"><span>{projectText("customer")}</span><select required value={form.id_customer_contact} onChange={(event) => setForm({ ...form, id_customer_contact: event.target.value })}><option value="">{projectText("select_contact")}</option>{contacts.map((contact) => <option key={contact.id_customer_contact} value={contact.id_customer_contact}>{contactLabel(contact, projectText("customer"))}</option>)}</select></label><label className="field"><span>{projectText("responsible")}</span><p className="field-static">{editingId ? userLabel(userById[editingLeader], editingLeader, projectText("user")) : (actor.full_name || actor.username || actor.email || projectText("current_user"))}</p></label><label className="field wide"><span>{projectText("description")}</span><textarea required maxLength={200} rows={4} value={form.proyect_description} onChange={(event) => setForm({ ...form, proyect_description: event.target.value })} /></label><label className="field"><span>{projectText("folio")}</span><input maxLength={40} value={form.folio} onChange={(event) => setForm({ ...form, folio: event.target.value })} /></label><label className="field"><span>{projectText("quotation")}</span><select value={form.id_quotation} onChange={(event) => setForm({ ...form, id_quotation: event.target.value })}><option value="">{projectText("select_quotation")}</option>{quotations.map((quotation) => <option key={quotation.id_invoice} value={quotation.id_invoice}>{quotationLabel(quotation, customerById)}</option>)}</select></label>{canEditManagement && <label className="field"><span>{projectText("purchase_order")}</span><input maxLength={60} value={form.purchase_order} onChange={(event) => setForm({ ...form, purchase_order: event.target.value })} /></label>}{canEditManagement && <label className="field"><span>{projectText("purchase_order_item")}</span><input type="number" min="1" value={form.purchase_order_item} onChange={(event) => setForm({ ...form, purchase_order_item: event.target.value })} /></label>}<label className="field"><span>{projectText("delivery_date")}</span><input type="date" value={form.delivery_date} onChange={(event) => setForm({ ...form, delivery_date: event.target.value })} /></label></div><footer><button className="button" type="button" onClick={() => setShowForm(false)}>{projectText("cancel")}</button><button className="button primary" disabled={busyId !== null}>{projectText("save")}</button></footer></form></div>}

    {transition && <div className="project-modal-backdrop" role="presentation"><form className="project-modal compact" onSubmit={applyTransition}><header><div><p className="eyebrow">{projectText("status_change")}</p><h3>{statusLabel(transition.target)}</h3></div><button className="icon-button" type="button" onClick={() => setTransition(null)} aria-label={projectText("close")}><X size={18} /></button></header><p>{transition.project.title || `${projectText("project")} #${transition.project.id_proyect}`}</p>{needsReason(transition.target) && <label className="field"><span>{projectText("reason")}</span><textarea required rows={3} value={transition.reason} onChange={(event) => setTransition({ ...transition, reason: event.target.value })} /></label>}<label className="field"><span>{projectText(transitionNoteKey(transition))}</span><textarea rows={3} value={transition.content} onChange={(event) => setTransition({ ...transition, content: event.target.value })} /></label>{transition.target === "blocked" && <label className="field"><span>{projectText("review_date")}</span><input type="datetime-local" value={transition.reviewDate} onChange={(event) => setTransition({ ...transition, reviewDate: event.target.value })} /></label>}<footer><button className="button" type="button" onClick={() => setTransition(null)}>{projectText("cancel")}</button><button className="button primary" disabled={busyId !== null}>{projectText("confirm_change")}</button></footer></form></div>}

    {detail && <div className="project-modal-backdrop" role="presentation"><aside className="project-detail-panel"><header><div><p className="eyebrow">{projectText("record")} #{detail.id_proyect}</p><h3>{detail.title || projectText("project")}</h3></div><button className="icon-button" type="button" onClick={() => setDetail(null)} aria-label={projectText("close")}><X size={18} /></button></header><span className={`project-status status-${detail.proyect_status}`}>{statusLabel(detail.proyect_status)}</span><p>{detail.proyect_description}</p><ProyectoExpediente detalle={detail} catalogo={catalog} modo={mode} onCambio={async () => setDetail(await getProyect(detail.id_proyect))} /><h4>{projectText("tasks")}</h4>{detail.tasks?.length ? detail.tasks.map((task) => <button className="project-detail-row project-task-row" type="button" key={task.id_task} onClick={() => openTask(task)} disabled={busyId !== null}><strong>{taskLabel(task)}</strong><span className="project-task-row-end"><span className={`project-status status-${task.task_status || "unknown"}`}>{taskStatusLabel(task.task_status)}</span><ChevronRight size={16} /></span></button>) : <p className="muted">{projectText("no_tasks")}</p>}<h4>{projectText("history")}</h4><div className="project-timeline">{detail.events?.slice().reverse().map((event) => <div key={event.id_proyect_event}><span>{new Date(event.creation_date).toLocaleString(document.documentElement.lang || "es")}</span><strong>{eventTitle(event)}</strong>{(event.reason || event.content) && <p>{event.reason || event.content}</p>}</div>)}</div><form className="project-message" onSubmit={sendMessage}><label className="field"><span>{projectText("new_message")}</span><textarea rows={2} value={message} onChange={(event) => setMessage(event.target.value)} placeholder={projectText("message_placeholder")} /></label><button className="button primary" disabled={!message.trim() || busyId !== null}><MessageSquare size={16} />{projectText("publish")}</button></form></aside></div>}

    {taskDetail && <div className="project-modal-backdrop" role="presentation"><aside className="project-detail-panel"><header><div><p className="eyebrow">{projectText("task")} #{taskDetail.task.id_task}</p><h3>{taskLabel(taskDetail.task)}</h3></div><button className="icon-button" type="button" onClick={closeTask} aria-label={projectText("close")}><X size={18} /></button></header>
      <div className="project-task-status"><span className={`project-status status-${taskDetail.task.task_status || "unknown"}`}>{taskStatusLabel(taskDetail.task.task_status)}</span>{taskActionTargets(taskDetail.task).length > 0 && <label className="project-transition"><ArrowRight size={15} /><select value="" disabled={busyId !== null} onChange={(event) => event.target.value && setTaskTransition({ task: taskDetail.task, target: event.target.value, reason: "", content: "" })} aria-label={projectText("change_status")}><option value="">{projectText("change_status")}</option>{taskActionTargets(taskDetail.task).map((target) => <option value={target} key={target}>{taskStatusLabel(target)}</option>)}</select></label>}</div>
      {taskDetail.task.task_description && <p>{taskDetail.task.task_description}</p>}
      <h4>{projectText("task_notes")}</h4>
      {taskDetail.notes.length ? taskDetail.notes.map((note) => <div className="project-note" key={note.id_task_note}><span>{new Date(note.date || note.creation_date).toLocaleString(document.documentElement.lang || "es")}</span><p>{note.task_note_description}</p></div>) : <p className="muted">{projectText("no_task_notes")}</p>}
      <form className="project-message" onSubmit={sendTaskNote}><label className="field"><span>{projectText("new_task_note")}</span><textarea rows={2} value={taskNote} onChange={(event) => setTaskNote(event.target.value)} placeholder={projectText("task_note_placeholder")} /></label><button className="button primary" disabled={!taskNote.trim() || busyId !== null}><MessageSquare size={16} />{projectText("publish")}</button></form>
    </aside></div>}

    {taskTransition && <div className="project-modal-backdrop" role="presentation"><form className="project-modal compact" onSubmit={applyTaskTransition}><header><div><p className="eyebrow">{projectText("status_change")}</p><h3>{taskStatusLabel(taskTransition.target)}</h3></div><button className="icon-button" type="button" onClick={() => setTaskTransition(null)} aria-label={projectText("close")}><X size={18} /></button></header><p>{taskLabel(taskTransition.task)}</p>{taskNeedsReason(taskTransition.target) && <label className="field"><span>{projectText("reason")}</span><textarea required rows={3} value={taskTransition.reason} onChange={(event) => setTaskTransition({ ...taskTransition, reason: event.target.value })} /></label>}<label className="field"><span>{projectText("observation")}</span><textarea rows={3} value={taskTransition.content} onChange={(event) => setTaskTransition({ ...taskTransition, content: event.target.value })} /></label><footer><button className="button" type="button" onClick={() => setTaskTransition(null)}>{projectText("cancel")}</button><button className="button primary" disabled={busyId !== null}>{projectText("confirm_change")}</button></footer></form></div>}
  </section>;
}