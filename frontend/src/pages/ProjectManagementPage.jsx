import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { idAAbrir } from "../notifications/destino";
import { ArrowRight, ChevronRight, Eye, HelpingHand, LayoutGrid, List, LogOut, MessageSquare, Pencil, Plus, RefreshCw, Trash2, X } from "lucide-react";
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
  getTaskNotes,
  releaseProyect,
  takeProyect,
  transitionProyect,
  transitionTask,
  updateProyect,
} from "../api";
import { useI18n } from "../i18n";
import MaterialNecesario from "../components/MaterialNecesario.jsx";
import ProyectoExpediente from "../components/ProyectoExpediente.jsx";
import PageHeader from "../components/PageHeader.jsx";
import { formatearFechaHora } from "../utils/fechas";

/* eslint-disable react/prop-types */

// En que orden se leen las columnas del tablero. Es presentacion, y el servidor
// no la conoce: el catalogo dice cuales existen, esto en que orden se pintan.
// Un estatus que el catalogo traiga y esta lista no nombre se pinta al final,
// en vez de desaparecer del tablero.
const STATUS_ORDER = ["draft", "submitted", "blocked", "authorized", "waiting_material", "in_progress", "stopped", "collected", "completed", "denied"];
const TASK_STATUS_ORDER = ["pendiente", "en_proceso", "bloqueada", "en_revision", "terminada", "cancelada"];

// Lo que cada papel puede PEDIR, con los mismos grupos que comprueba
// `transition_project` en el servidor: quien autoriza y quien ejecuta.
// Supervisor no tiene ninguno a proposito -- Gerente es quien saca el
// proyecto de Borrador, al recibir la orden de compra, no Supervisor.
//
// Va por ESTADO ACTUAL, no solo por destino: "en_proceso" ya no significa
// lo mismo segun de donde venga -- desde "en espera de material" lo decide
// Gerente (la compra puede surtir a varios proyectos, ver el comentario de
// PROJECT_STATUSES en el backend), desde "detenido" lo reanuda el taller.
// Mismo destino, dos candados de rol distintos, igual que en
// `transition_project` (backend).
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
  supervisor: {},
  manager: {
    // Gerencia primero lo pasa a revision; de ahi lo autoriza.
    draft: ["submitted", "denied", "blocked"],
    submitted: ["authorized", "denied", "blocked"],
    blocked: ["authorized", "denied", "blocked"],
    // La espera de material es obligatoria y la abre quien confirma el
    // material, no el taller: Gerente de respaldo y, desde 2026-10-16, quien
    // tenga `project_supply` (Compras; ver `puedeDarMaterial` en actionTargets).
    authorized: ["waiting_material"],
    waiting_material: ["in_progress"],
    // Completar lo recolectado es del responsable o de Gerencia.
    collected: ["completed"],
  },
  workshop: {
    // Taller NO tiene "blocked": para un proyecto ya en curso, lo suyo es
    // "detenido" (`stopped`). Bloquearlo es cosa de quien lidera el
    // proyecto o de quien autoriza. Ver el candado real en
    // `transition_project` (backend). La pausa a medio trabajo (el
    // material se acaba ya arrancado) SI es del taller -- a diferencia de
    // la espera de entrada, que controla Gerente arriba.
    // Recolectar lo cambia el taller cuando el proyecto lleva maquila (sin
    // maquila lo cambia el supervisor, ver `leadsIt` abajo).
    in_progress: ["waiting_material", "stopped", "collected"],
    waiting_material: ["stopped"],
    stopped: ["in_progress"],
  },
  // `unrestricted` no aparece: sin limite de papel, manda el catalogo solo.
};
// Los campos de la ORDEN DE TRABAJO se agregan aqui a proposito, y no en una
// pantalla propia: son atributos del proyecto, no otra entidad. Todos
// opcionales salvo lo que ya era obligatorio -- un proyecto se puede crear
// antes de tener folio asignado, y completarse despues.
//
// `leader` (responsable) NO esta aqui: siempre es quien crea el proyecto, sin
// selector -- se muestra fijo, nunca se manda en el payload. `purchase_order`
// solo se muestra y se manda cuando edita Gerente (ver `mode` en el JSX del
// modal); para Supervisor queda siempre vacio. `purchase_order_item` ya no se
// captura en el formulario -- era redundante con `purchase_order` (misma
// orden de compra, sin renglon aparte); la columna y el modelo se dejan
// intactos, solo se dejo de pedir en la UI.
// `proyect_description` tampoco esta en el formulario: era redundante con
// `title` (el campo real que la gente llenaba) y el backend la sigue
// exigiendo al crear, asi que `saveProject` la manda igual al titulo, sin
// pedirsela dos veces a quien captura.
const EMPTY_FORM = {
  id_customer_contact: "", title: "",
  folio: "", id_quotation: "", purchase_order: "",
  delivery_date: "",
  // Solo para Gerencia (ver `canEditManagement`), igual que `purchase_order`:
  // el candado real vive en el backend (`project_management_service`), esto
  // solo evita ofrecer el campo a quien de todas formas se ignoraria en
  // silencio.
  priority: "", total_cost: "",
  // Si el proyecto pasa por el taller (maquila) o no (pinturas, drenaje,
  // cimientos). Por omision true: es el recorrido de siempre, y un proyecto
  // que si necesita maquila es el caso comun.
  requires_maquila: true,
};

const PROJECT_PRIORITIES = ["baja", "media", "alta"];

// Los dos pasos del material, por estatus de partida. Quien los da (Compras)
// los ve como un boton en la fila, con el texto de la accion y no el del
// estatus; el resto de los cambios siguen en el desplegable.
const PASO_DE_MATERIAL = { authorized: "waiting_material", waiting_material: "in_progress" };

// Cuanto material falta de un proyecto con control (la lista lo trae solo de los
// que ya estan en la espera o en curso). Nulo si no falta nada o no hay cuenta.
function materialPendiente(project) {
  const material = project.material_readiness;
  return material && material.total > 0 && !material.ready ? material : null;
}

function MaterialBadge({ project, label }) {
  const material = materialPendiente(project);
  if (!material) return null;
  return <span className="project-status material-pending" title={`${material.received} / ${material.total}`}>{label} {material.received}/{material.total}</span>;
}

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
  const priorityLabel = (priority) => (PROJECT_PRIORITIES.includes(priority) ? projectText(`priority_${priority}`) : priority);
  const collectionStatusLabel = (status) => (
    ["pendiente", "cobrado", "excedido"].includes(status) ? projectText(`collection_status_${status}`) : status
  );
  // `title` ya no tiene forma de capturarse desde /task (el formulario se
  // redujo a descripcion/proyecto/fase, ver 828255e) -- sin este respaldo,
  // toda tarea real se veia como "Tarea #5" en vez de lo unico que su
  // responsable si escribio.
  const taskLabel = (task) => task.title || task.task_description || task.task_code || `${projectText("task")} #${task.id_task}`;

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
  // Llegar desde una notificacion: `/proyect?abrir=<id>` abre ese proyecto. El
  // parametro se consume una vez (se limpia) para que recargar no lo reabra.
  const [parametros, setParametros] = useSearchParams();
  const idPorAbrir = idAAbrir(parametros);
  // Su PROPIO estado: `loadData` limpia `error` al arrancar y, segun quien gane
  // la carrera, borraba este mensaje antes de que se leyera.
  const [noSeAbrio, setNoSeAbrio] = useState("");
  useEffect(() => {
    if (!idPorAbrir) return;
    // Limpiar el parametro vuelve a ejecutar este efecto (idPorAbrir pasa a
    // null): por eso aqui NO hay guardia de "sigue vigente" -- cancelaria el
    // `setDetail` de la peticion que acaba de salir.
    setParametros({}, { replace: true });
    setNoSeAbrio("");
    (async () => {
      try {
        setDetail(await getProyect(idPorAbrir));
      } catch {
        // 403/404: el aviso apunta a un proyecto que ya no existe o que este
        // usuario no puede ver. Se dice, no se deja la pantalla en blanco.
        setNoSeAbrio(t("project_management.error_open_notification"));
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idPorAbrir]);
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
  // Las capacidades suman: quien tiene autorizar Y ejecutar en el Gestor es "manager" para la
  // pantalla, pero tambien puede ejecutar (tomar el proyecto). El servidor decide igual.
  const puedeEjecutar = privileged || hasRead(permissions, "project_execution");
  // Los dos pasos de material (a "en espera" y de ahi a "en proceso"): quien
  // tiene `project_supply` (Compras) o, de respaldo, quien autoriza -- igual
  // que `_puede_dar_el_material` en el servidor.
  const puedeDarMaterial = privileged || hasRead(permissions, "project_supply") || hasRead(permissions, "project_authorization");
  const statusCodes = useMemo(() => orderedStatuses(catalog?.proyect?.statuses, STATUS_ORDER), [catalog]);
  const needsReason = (target) => (catalog?.proyect?.reason_required || []).includes(target);
  const taskNeedsReason = (target) => (catalog?.task?.reason_required || []).includes(target);
  const projectPermission = permissions.find((item) => item.entity_name === "proyect");
  const canCreate = privileged || Number(projectPermission?.scope_create || 0) !== 0;
  const canDelete = privileged || Number(projectPermission?.scope_delete || 0) !== 0;
  const customerById = useMemo(() => Object.fromEntries(customers.map((item) => [item.id_customer_supplier, item])), [customers]);
  const userById = useMemo(() => Object.fromEntries(users.map((item) => [item.id_user, item])), [users]);
  const canEditManagement = mode === "manager" || mode === "unrestricted";
  // Cambiar el estatus de una tarea (taller) es capacidad de Gerente/Jefe de
  // taller/administrador -- ver seed de `entity_permission` para "task"
  // (`scope_update`): Supervisor solo tiene lectura. El backend ya lo exige
  // (`require_entity_permission('task', 'update')` en /task/<id>/transition),
  // esto solo evita ofrecerle el control a quien de todas formas recibiria
  // un 403.
  const canChangeTaskStatus = mode !== "supervisor";
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
        const [permissionPayload, customerPayload, contactPayload, userPayload, catalogPayload] = await Promise.all([
          privileged ? Promise.resolve({ entity_permissions: [] }) : getMyPermissions().catch(() => ({ entity_permissions: [] })),
          getCustomerSupplierOptions().catch(() => []),
          getCustomerContactOptions().catch(() => []),
          getUserOptions().catch(() => []),
          // Si el catalogo no llega, `statusCodes` cae en STATUS_ORDER y los
          // cambios de estatus quedan sin ofrecer, no ofrecidos a ciegas: el
          // servidor los rechazaria y el mensaje seria peor.
          getOperationsCatalog().catch(() => null),
        ]);
        setPermissions(permissionPayload.entity_permissions || []);
        setCustomers(listOf(customerPayload));
        setContacts(listOf(contactPayload));
        setUsers(listOf(userPayload));
        setCatalog(catalogPayload);
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
    setEditingLeader(actor.id_user || null);
    setForm(EMPTY_FORM);
    setShowForm(true);
  }

  function openEdit(project) {
    setEditingId(project.id_proyect);
    setEditingLeader(project.leader || null);
    setForm({
      id_customer_contact: project.id_customer_contact || "",
      title: project.title || "",
      folio: project.folio || "",
      id_quotation: project.id_quotation || project.quotation_reference || "", purchase_order: project.purchase_order || "",
      delivery_date: project.delivery_date || "",
      priority: project.priority || "",
      total_cost: project.total_cost ?? "",
      requires_maquila: project.requires_maquila ?? true,
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
    // La cotizacion se manda tal cual, como texto: puede ser un id real de
    // esta base o un folio externo con letras/guiones (ej. el sistema aparte
    // que usa adser). El backend decide a que columna va.
    const textoOpcional = (v) => (String(v ?? "").trim() === "" ? undefined : String(v).trim());
    const cuerpo = {
      ...form,
      // El backend sigue exigiendo proyect_description (NOT NULL) al crear;
      // como ya no es un campo del formulario, se manda igual al titulo.
      proyect_description: form.title,
      id_customer_contact: numeroOpcional(form.id_customer_contact),
      id_quotation: textoOpcional(form.id_quotation),
      // Orden de compra solo la captura Gerente (`canEditManagement`); para
      // Supervisor el formulario ni la muestra, y aqui se manda `undefined`
      // para no pisar lo ya capturado con vacio.
      purchase_order: canEditManagement ? (form.purchase_order.trim() || undefined) : undefined,
      // La partida es opcional y de ellos: vacia se manda como null, para que
      // al editar tambien se pueda quitar (con `undefined` no viajaba).
      folio: form.folio.trim() || null,
      delivery_date: form.delivery_date || undefined,
      // Prioridad y costo total: mismo candado que orden de compra -- el
      // backend los ignora en silencio si el actor no tiene el alcance, pero
      // ni se mandan desde aqui para no pisar lo ya capturado con vacio.
      priority: canEditManagement ? (form.priority || undefined) : undefined,
      total_cost: canEditManagement ? (String(form.total_cost ?? "").trim() === "" ? undefined : Number(form.total_cost)) : undefined,
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

  // El proyecto no se asigna: lo toma quien lo va a sacar adelante
  // (`take_project`, backend). Existia la ruta y el cliente de API
  // (`takeProyect`) pero nunca se conecto a ningun boton -- Jefe de taller
  // no tenia como tomar un proyecto libre desde la pantalla.
  async function tomarProyecto(project) {
    setBusyId(project.id_proyect);
    setError("");
    try {
      await takeProyect(project.id_proyect);
      await loadData();
      if (detail?.id_proyect === project.id_proyect) setDetail(await getProyect(project.id_proyect));
    } catch (requestError) {
      setError(requestError.message || projectText("error_transition"));
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
      if (detail?.id_proyect === project.id_proyect) setDetail(await getProyect(project.id_proyect));
    } catch (requestError) {
      setError(requestError.message || projectText("error_transition"));
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
      // Material sin recibir: el servidor pide un motivo para arrancar igual.
      if (requestError.message === "errors.project_material_pending") setTransition((t) => ({ ...t, materialReason: true }));
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
    const porPapel = ROLE_TARGETS[mode];
    const permitidos = porPapel ? (porPapel[project.proyect_status] || []) : null;
    const base = permitidos ? desdeElServidor.filter((target) => permitidos.includes(target)) : desdeElServidor;
    let resultado = base;
    // Completar lo recolectado es del LIDER del proyecto (normalmente
    // Supervisor, quien lo crea), no del rol -- igual que el candado real en
    // `transition_project` (backend). Por eso no vive en ROLE_TARGETS: ese
    // mapa es por papel, esto es por quien lidera este proyecto en concreto.
    const leadsIt = Number(project.leader) === Number(actor.id_user);
    if (leadsIt && project.proyect_status === "collected" && !resultado.includes("completed")) {
      resultado = [...resultado, "completed"];
    }
    // Los pasos de material los da quien tiene `project_supply` aunque su rol
    // no sea "manager" (Compras cae en el modo "supervisor", sin acciones por
    // papel). Lo mismo con o sin maquila: los dos pasan por Compras.
    const pasoDeMaterial = PASO_DE_MATERIAL[project.proyect_status];
    if (puedeDarMaterial && pasoDeMaterial && desdeElServidor.includes(pasoDeMaterial)
        && !resultado.includes(pasoDeMaterial)) {
      resultado = [...resultado, pasoDeMaterial];
    }
    // Un proyecto sin maquila no lo lleva el Jefe de taller sino quien lo
    // lidera (el supervisor): ya en proceso, lo detiene, lo reanuda y lo
    // completa. Es por proyecto y no por rol, como "entregado" arriba; el
    // servidor (`transition_project`, via `leads_it`) lo vuelve a comprobar.
    if (leadsIt && !project.requires_maquila) {
      const delSupervisor = { in_progress: ["stopped", "collected"], stopped: ["in_progress"] }[project.proyect_status] || [];
      for (const destino of delSupervisor) {
        if (desdeElServidor.includes(destino) && !resultado.includes(destino)) resultado = [...resultado, destino];
      }
    }
    return resultado;
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
    const todos = actionTargets(project);
    // El paso del material sale como boton a la vista ("Material en camino" /
    // "Material recibido, iniciar"); el desplegable queda con lo demas.
    const pasoDeMaterial = puedeDarMaterial && todos.includes(PASO_DE_MATERIAL[project.proyect_status])
      ? PASO_DE_MATERIAL[project.proyect_status] : null;
    const targets = todos.filter((target) => target !== pasoDeMaterial);
    // El proyecto no se asigna: lo toma quien lo va a sacar adelante. Si
    // aparece en esta lista y sigue sin supervisor, es porque `_scoped_query`
    // (backend) ya lo dejo ver como libre -- un Jefe de taller nunca ve lo
    // que ya tomo otro companero, asi que no hace falta repetir aqui esa
    // comprobacion de estatus.
    const puedeTomar = puedeEjecutar && !project.id_supervisor;
    const puedeSoltar = Number(project.id_supervisor) === Number(actor.id_user);
    return <div className="project-actions">
      <button className="icon-button" type="button" title={projectText("view_detail")} onClick={() => openDetail(project)}><Eye size={16} /></button>
      {(((mode === "unrestricted" || Number(project.leader) === Number(actor.id_user)
          // Ver un proyecto ajeno (`scope_read` Todos) no es poder editarlo: eso lo manda
          // `scope_update` -- Propios solo alcanza lo propio; Mis grupos o Todos, mas.
          || (mode === "supervisor" && (Number(project.created_by) === Number(actor.id_user)
              || (Number(projectPermission?.scope_update || 0) & 6) !== 0))
         ) && ["draft", "blocked"].includes(project.proyect_status)) || canEditManagement) && <button className="icon-button" type="button" title={projectText("edit")} onClick={() => openEdit(project)}><Pencil size={16} /></button>}
      {canDelete && project.proyect_status === "draft" && <button className="icon-button danger" type="button" title={projectText("delete")} onClick={() => removeProject(project)}><Trash2 size={16} /></button>}
      {puedeTomar && <button className="icon-button" type="button" title={projectText("take_project")} disabled={busyId === project.id_proyect} onClick={() => tomarProyecto(project)}><HelpingHand size={16} /></button>}
      {puedeSoltar && <button className="icon-button" type="button" title={projectText("release_project")} disabled={busyId === project.id_proyect} onClick={() => soltarProyecto(project)}><LogOut size={16} /></button>}
      {pasoDeMaterial && <button className="button primary small" type="button" disabled={busyId === project.id_proyect} onClick={() => setTransition({ project, target: pasoDeMaterial, reason: "", content: "", reviewDate: "" })}>{projectText(pasoDeMaterial === "waiting_material" ? "material_en_camino" : (materialPendiente(project)?.received > 0 ? "material_parcial" : "material_recibido"))}</button>}
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
    {noSeAbrio && <div className="alert error">{noSeAbrio}</div>}
    {loading && <div className="alert">{projectText("loading")}</div>}
    {!loading && !filtered.length && <div className="empty"><strong>{projectText("empty")}</strong><p>{projectText("empty_body")}</p></div>}

    {!loading && filtered.length > 0 && view === "table" && <div className="table-card"><div className="table-wrap"><table><thead><tr><th>{projectText("folio")}</th><th>{projectText("project")}</th><th>{projectText("customer")}</th><th>{projectText("creator")}</th><th>{projectText("created")}</th><th>{projectText("status")}</th><th>{projectText("updated")}</th><th>{projectText("delivery_date")}</th>{canEditManagement && <th>{projectText("priority")}</th>}{canEditManagement && <th>{projectText("collection_status")}</th>}<th>{projectText("actions")}</th></tr></thead><tbody>{filtered.map((project) => <tr key={project.id_proyect}><td><strong>{project.folio || "—"}</strong></td><td><strong>{project.title || `${projectText("project")} #${project.id_proyect}`}</strong>{!project.requires_maquila && <span className="project-status no-maquila">{projectText("no_maquila_badge")}</span>}<MaterialBadge project={project} label={projectText("material_label")} /><p className="cell-value">{project.proyect_description}</p></td><td>{customerLabel(customerById[project.id_customer_supplier], projectText("customer"))}</td><td>{userLabel(userById[project.created_by], project.created_by, projectText("user"))}</td><td>{dateLabel(project.creation_date)}</td><td><span className={`project-status status-${project.proyect_status}`}>{statusLabel(project.proyect_status)}</span></td><td>{dateLabel(project.last_update_date)}</td><td>{dateLabel(project.delivery_date)}</td>{canEditManagement && <td>{project.priority ? <span className={`project-status priority-${project.priority}`}>{priorityLabel(project.priority)}</span> : "—"}</td>}{canEditManagement && <td>{project.collection_status ? <span className={`project-status collection-${project.collection_status}`}>{collectionStatusLabel(project.collection_status)}</span> : "—"}</td>}<td><ProjectActions project={project} /></td></tr>)}</tbody></table></div></div>}

    {!loading && view === "board" && <div className="project-board">{statusCodes.map((status) => { const cards = filtered.filter((project) => project.proyect_status === status); return <section className={`project-column status-${status}`} key={status}><header><strong>{statusLabel(status)}</strong><span>{cards.length}</span></header><div>{cards.map((project) => <article className="project-card" key={project.id_proyect}><strong>{project.title || `${projectText("project")} #${project.id_proyect}`}</strong><p>{customerLabel(customerById[project.id_customer_supplier], projectText("customer"))}</p><small>{project.proyect_description}</small><ProjectActions project={project} /></article>)}{!cards.length && <p className="project-column-empty">{projectText("no_projects")}</p>}</div></section>; })}</div>}

    {!loading && total > 0 && <div className="pagination"><button className="button" type="button" disabled={page <= 1} onClick={() => loadData(page - 1)}>{projectText("previous")}</button><span>{projectText("page")} {page} / {Math.max(Math.ceil(total / perPage), 1)}</span><select value={perPage} onChange={(event) => { const nextPerPage = Number(event.target.value); setPerPage(nextPerPage); loadData(1, nextPerPage); }} aria-label={projectText("per_page")}><option value={10}>10</option><option value={20}>20</option><option value={50}>50</option><option value={100}>100</option></select><button className="button" type="button" disabled={page * perPage >= total} onClick={() => loadData(page + 1)}>{projectText("next")}</button></div>}

    {showForm && <div className="project-modal-backdrop" role="presentation"><form className="project-modal" onSubmit={saveProject}><header><div><p className="eyebrow">{projectText("project")}</p><h3>{projectText(editingId ? "edit_project" : "new_project")}</h3></div><button className="icon-button" type="button" onClick={() => setShowForm(false)} aria-label={projectText("close")}><X size={18} /></button></header><div className="form-grid"><label className="field"><span>{projectText("title_field")}</span><input required maxLength={50} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label><label className="field"><span>{projectText("customer")}</span><select required value={form.id_customer_contact} onChange={(event) => setForm({ ...form, id_customer_contact: event.target.value })}><option value="">{projectText("select_contact")}</option>{contacts.map((contact) => <option key={contact.id_customer_contact} value={contact.id_customer_contact}>{contactLabel(contact, projectText("customer"))}</option>)}</select></label><label className="field"><span>{projectText("responsible")}</span><p className="field-static">{editingId ? userLabel(userById[editingLeader], editingLeader, projectText("user")) : (actor.full_name || actor.username || actor.email || projectText("current_user"))}</p></label><label className="field"><span>{projectText("folio")}</span><input maxLength={40} value={form.folio} onChange={(event) => setForm({ ...form, folio: event.target.value })} /></label><label className="field"><span>{projectText("quotation")}</span><input type="text" maxLength={80} value={form.id_quotation} onChange={(event) => setForm({ ...form, id_quotation: event.target.value })} /></label><label className="field"><span>{projectText("delivery_date")}</span><input type="date" value={form.delivery_date} onChange={(event) => setForm({ ...form, delivery_date: event.target.value })} /></label><label className="field checkbox-inline"><input type="checkbox" checked={form.requires_maquila} onChange={(event) => setForm({ ...form, requires_maquila: event.target.checked })} /><span>{projectText("requires_maquila")}</span></label>{canEditManagement && <label className="field"><span>{projectText("purchase_order")}</span><input maxLength={60} value={form.purchase_order} onChange={(event) => setForm({ ...form, purchase_order: event.target.value })} /></label>}{canEditManagement && <label className="field"><span>{projectText("priority")}</span><select value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value })}><option value="">{projectText("select_priority")}</option>{PROJECT_PRIORITIES.map((value) => <option key={value} value={value}>{priorityLabel(value)}</option>)}</select></label>}{canEditManagement && <label className="field"><span>{projectText("total_cost")}</span><input type="number" min="0" step="0.01" value={form.total_cost} onChange={(event) => setForm({ ...form, total_cost: event.target.value })} /></label>}</div><footer><button className="button" type="button" onClick={() => setShowForm(false)}>{projectText("cancel")}</button><button className="button primary" disabled={busyId !== null}>{projectText("save")}</button></footer></form></div>}

    {transition && <div className="project-modal-backdrop" role="presentation"><form className="project-modal compact" onSubmit={applyTransition}><header><div><p className="eyebrow">{projectText("status_change")}</p><h3>{statusLabel(transition.target)}</h3></div><button className="icon-button" type="button" onClick={() => setTransition(null)} aria-label={projectText("close")}><X size={18} /></button></header><p>{transition.project.title || `${projectText("project")} #${transition.project.id_proyect}`}</p>{transition.materialReason && <p className="alert error">{t("errors.project_material_pending")}</p>}{(needsReason(transition.target) || transition.materialReason) && <label className="field"><span>{projectText("reason")}</span><textarea required rows={3} value={transition.reason} onChange={(event) => setTransition({ ...transition, reason: event.target.value })} /></label>}<label className="field"><span>{projectText(transitionNoteKey(transition))}</span><textarea rows={3} value={transition.content} onChange={(event) => setTransition({ ...transition, content: event.target.value })} /></label>{transition.target === "blocked" && <label className="field"><span>{projectText("review_date")}</span><input type="datetime-local" value={transition.reviewDate} onChange={(event) => setTransition({ ...transition, reviewDate: event.target.value })} /></label>}<footer><button className="button" type="button" onClick={() => setTransition(null)}>{projectText("cancel")}</button><button className="button primary" disabled={busyId !== null}>{projectText("confirm_change")}</button></footer></form></div>}

    {detail && <div className="project-modal-backdrop" role="presentation"><aside className="project-detail-panel"><header><div><p className="eyebrow">{projectText("record")} #{detail.id_proyect}</p><h3>{detail.title || projectText("project")}</h3></div><button className="icon-button" type="button" onClick={() => setDetail(null)} aria-label={projectText("close")}><X size={18} /></button></header><span className={`project-status status-${detail.proyect_status}`}>{statusLabel(detail.proyect_status)}</span>{!detail.requires_maquila && <span className="project-status no-maquila">{projectText("no_maquila_badge")}</span>}<p>{detail.proyect_description}</p><div className="project-progress">{detail.task_progress && <label><span>{projectText("progress_tasks")}: {detail.task_progress.done}/{detail.task_progress.total}</span><progress max={detail.task_progress.total || 1} value={detail.task_progress.done} /></label>}{detail.material_readiness?.total > 0 && <label><span>{projectText("progress_material")}: {detail.material_readiness.received}/{detail.material_readiness.total}{detail.material_readiness.not_ordered > 0 && ` · ${detail.material_readiness.not_ordered} ${projectText("progress_not_ordered")}`}</span><progress max={detail.material_readiness.total} value={detail.material_readiness.received} /></label>}</div><ProyectoExpediente detalle={detail} catalogo={catalog} modo={mode} onCambio={async () => setDetail(await getProyect(detail.id_proyect))} /><MaterialNecesario idProyect={detail.id_proyect} estatus={detail.proyect_status} /><h4>{projectText("tasks")}</h4>{detail.tasks?.length ? detail.tasks.map((task) => <button className="project-detail-row project-task-row" type="button" key={task.id_task} onClick={() => openTask(task)} disabled={busyId !== null}><strong>{taskLabel(task)}</strong><span className="project-task-row-end"><span className={`project-status status-${task.task_status || "unknown"}`}>{taskStatusLabel(task.task_status)}</span><ChevronRight size={16} /></span></button>) : <p className="muted">{projectText("no_tasks")}</p>}<h4>{projectText("history")}</h4><div className="project-timeline">{detail.events?.slice().reverse().map((event) => <div key={event.id_proyect_event}><span>{formatearFechaHora(event.creation_date, document.documentElement.lang || "es")}</span><strong>{eventTitle(event)}</strong>{(event.reason || event.content) && <p>{event.reason || event.content}</p>}</div>)}</div><form className="project-message" onSubmit={sendMessage}><label className="field"><span>{projectText("new_message")}</span><textarea rows={2} value={message} onChange={(event) => setMessage(event.target.value)} placeholder={projectText("message_placeholder")} /></label><button className="button primary" disabled={!message.trim() || busyId !== null}><MessageSquare size={16} />{projectText("publish")}</button></form></aside></div>}

    {taskDetail && <div className="project-modal-backdrop" role="presentation"><aside className="project-detail-panel"><header><div><p className="eyebrow">{projectText("task")} #{taskDetail.task.id_task}</p><h3>{taskLabel(taskDetail.task)}</h3></div><button className="icon-button" type="button" onClick={closeTask} aria-label={projectText("close")}><X size={18} /></button></header>
      <div className="project-task-status"><span className={`project-status status-${taskDetail.task.task_status || "unknown"}`}>{taskStatusLabel(taskDetail.task.task_status)}</span>{canChangeTaskStatus && taskActionTargets(taskDetail.task).length > 0 && <label className="project-transition"><ArrowRight size={15} /><select value="" disabled={busyId !== null} onChange={(event) => event.target.value && setTaskTransition({ task: taskDetail.task, target: event.target.value, reason: "", content: "" })} aria-label={projectText("change_status")}><option value="">{projectText("change_status")}</option>{taskActionTargets(taskDetail.task).map((target) => <option value={target} key={target}>{taskStatusLabel(target)}</option>)}</select></label>}</div>
      {taskDetail.task.task_description && <p>{taskDetail.task.task_description}</p>}
      <h4>{projectText("task_notes")}</h4>
      {taskDetail.notes.length ? taskDetail.notes.map((note) => <div className="project-note" key={note.id_task_note}><span>{new Date(note.date || note.creation_date).toLocaleString(document.documentElement.lang || "es")}</span><p>{note.task_note_description}</p></div>) : <p className="muted">{projectText("no_task_notes")}</p>}
      <form className="project-message" onSubmit={sendTaskNote}><label className="field"><span>{projectText("new_task_note")}</span><textarea rows={2} value={taskNote} onChange={(event) => setTaskNote(event.target.value)} placeholder={projectText("task_note_placeholder")} /></label><button className="button primary" disabled={!taskNote.trim() || busyId !== null}><MessageSquare size={16} />{projectText("publish")}</button></form>
    </aside></div>}

    {taskTransition && <div className="project-modal-backdrop" role="presentation"><form className="project-modal compact" onSubmit={applyTaskTransition}><header><div><p className="eyebrow">{projectText("status_change")}</p><h3>{taskStatusLabel(taskTransition.target)}</h3></div><button className="icon-button" type="button" onClick={() => setTaskTransition(null)} aria-label={projectText("close")}><X size={18} /></button></header><p>{taskLabel(taskTransition.task)}</p>{taskNeedsReason(taskTransition.target) && <label className="field"><span>{projectText("reason")}</span><textarea required rows={3} value={taskTransition.reason} onChange={(event) => setTaskTransition({ ...taskTransition, reason: event.target.value })} /></label>}<label className="field"><span>{projectText("observation")}</span><textarea rows={3} value={taskTransition.content} onChange={(event) => setTaskTransition({ ...taskTransition, content: event.target.value })} /></label><footer><button className="button" type="button" onClick={() => setTaskTransition(null)}>{projectText("cancel")}</button><button className="button primary" disabled={busyId !== null}>{projectText("confirm_change")}</button></footer></form></div>}
  </section>;
}