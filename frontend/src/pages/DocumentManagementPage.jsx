import { useEffect, useMemo, useRef, useState } from "react";
import { Download, Eye, FilePlus2, Lock, RefreshCw, Search, Trash2, X } from "lucide-react";

import {
  deleteDocument, downloadDocumentVersion, getAllCustomerSupplier, getAllEntityPermission, getDocument,
  getDocumentCategories, getDocumentEmployees, getDocumentUploaders, getDocuments, uploadDocument,
} from "../api";
import "../styles/laboratory.css";

const PER_PAGE = 20;
const EMPTY_FILTERS = { search: "", status: "", id_document_category: "", person: "", created_by: "", issue_date_from: "", issue_date_to: "" };
const SIMPLE_FILTERS = ["search", "status", "id_document_category", "created_by", "issue_date_from", "issue_date_to"];
const FULL_ACCESS = { scope_create: 4, scope_read: 4, scope_update: 4, scope_delete: 4 };
const STATUS_LABELS = { draft: "Borrador", issued: "Emitido", signed: "Firmado", rejected: "Rechazado", cancelled: "Cancelado" };
const TARGET_LABELS = { employee: "Empleado", customer_supplier: "Cliente o proveedor", equipment: "Equipo", service_order: "Orden" };
const ERROR_TEXT = {
  "documents.system_generated_not_deletable": "Este documento lo genero el sistema (vale o reporte de diagnostico) y no se puede borrar.",
  "documents.invalid_file_type": "Tipo de archivo no permitido.",
  "documents.mime_mismatch": "El contenido del archivo no corresponde a su extension.",
  "documents.invalid_file_size": "El archivo esta vacio o pasa del tamano permitido.",
  "documents.single_relation_required": "Indica a quien esta ligado el documento.",
  "errors.permission_denied": "Tu rol no tiene permiso para esta accion.",
  "errors.resource_not_found": "El documento ya no existe o no esta disponible para ti.",
};

function errorText(caught) {
  return ERROR_TEXT[caught?.message] || caught?.message || "No se pudo completar la operacion.";
}

function readCurrentUser() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch (_) { return {}; }
}

function rowsOf(payload) {
  return Array.isArray(payload) ? payload : (payload?.items || []);
}

function previewKind(version) {
  if (version.mime_type === "application/pdf") return "pdf";
  if (String(version.mime_type || "").startsWith("image/")) return "image";
  return "other";
}

export default function DocumentManagementPage() {
  const currentUser = useMemo(readCurrentUser, []);
  const isSuperUser = Boolean(currentUser?.is_superuser || currentUser?.is_bootstrap_admin);
  const roleId = currentUser?.id_permission;

  const [permissions, setPermissions] = useState({});
  const [documents, setDocuments] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [categories, setCategories] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [uploaders, setUploaders] = useState([]);
  const [draft, setDraft] = useState(EMPTY_FILTERS);
  const [applied, setApplied] = useState(EMPTY_FILTERS);
  const [reloadKey, setReloadKey] = useState(0);
  const [viewer, setViewer] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", id_document_category: "", id_customer_supplier: "", id_employee: "", relation_type: "customer", status: "draft" });
  const [file, setFile] = useState(null);

  const listRequest = useRef(0);
  const viewRequest = useRef(0);
  const viewerUrl = useRef(null);

  // Lo que el rol puede hacer sale del Gestor de roles y permisos: el boton que
  // no corresponde ni se pinta, y el backend lo niega igual si se fuerza.
  const can = (entity, field) => isSuperUser || Number(permissions[entity]?.[field] || 0) !== 0;
  const canCreate = can("document", "scope_create");
  const canDelete = can("document", "scope_delete");
  const canViewContent = can("document_version", "scope_read");

  useEffect(() => {
    let alive = true;
    if (isSuperUser) { setPermissions({ document: FULL_ACCESS, document_version: FULL_ACCESS }); return () => { alive = false; }; }
    getAllEntityPermission({ page: 1, per_page: 5000 })
      .then((payload) => {
        if (!alive) return;
        const mine = {};
        rowsOf(payload).filter((row) => String(row.id_permission) === String(roleId)).forEach((row) => { mine[row.entity_name] = row; });
        setPermissions(mine);
      })
      .catch(() => { if (alive) setPermissions({}); });
    return () => { alive = false; };
  }, [isSuperUser, roleId]);

  useEffect(() => {
    let alive = true;
    Promise.allSettled([getDocumentCategories(), getAllCustomerSupplier({ page: 1, per_page: 500 }), getDocumentEmployees()]).then(([cats, custs, emps]) => {
      if (!alive) return;
      if (cats.status === "fulfilled") setCategories(cats.value || []);
      if (custs.status === "fulfilled") setCustomers(rowsOf(custs.value));
      if (emps.status === "fulfilled") setEmployees(emps.value || []);
    });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    let alive = true;
    getDocumentUploaders().then((rows) => { if (alive) setUploaders(rows || []); }).catch(() => {});
    return () => { alive = false; };
  }, [reloadKey]);

  useEffect(() => {
    const request = ++listRequest.current;
    const params = { page, per_page: PER_PAGE };
    SIMPLE_FILTERS.forEach((key) => { if (applied[key]) params[key] = applied[key]; });
    if (applied.person) {
      const [kind, id] = applied.person.split(":");
      params[kind === "employee" ? "id_employee" : "id_customer_supplier"] = id;
    }
    setLoading(true); setError("");
    getDocuments(params)
      .then((result) => { if (request === listRequest.current) { setDocuments(result.items || []); setTotal(result.total || 0); } })
      .catch((caught) => { if (request === listRequest.current) setError(errorText(caught)); })
      .finally(() => { if (request === listRequest.current) setLoading(false); });
  }, [applied, page, reloadKey]);

  function releaseViewerUrl() {
    if (viewerUrl.current) { URL.revokeObjectURL(viewerUrl.current); viewerUrl.current = null; }
  }

  function closeViewer() {
    viewRequest.current += 1; releaseViewerUrl(); setViewer(null);
  }

  useEffect(() => releaseViewerUrl, []);
  useEffect(() => {
    if (!viewer) return undefined;
    const onKey = (event) => { if (event.key === "Escape") closeViewer(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [viewer === null]);

  async function showVersion(doc, version) {
    const request = ++viewRequest.current;
    releaseViewerUrl();
    const kind = previewKind(version);
    setViewer({ doc, version, kind, url: null, loading: kind !== "other", error: "" });
    if (kind === "other") return;
    try {
      const blob = await downloadDocumentVersion(doc.id_document, version.version, false);
      if (request !== viewRequest.current) return;
      const url = URL.createObjectURL(blob);
      viewerUrl.current = url;
      setViewer((current) => (current && current.version === version ? { ...current, url, loading: false } : current));
    } catch (caught) {
      if (request === viewRequest.current) setViewer((current) => current && { ...current, loading: false, error: errorText(caught) });
    }
  }

  async function openViewer(item) {
    setError("");
    try {
      const detail = await getDocument(item.id_document);
      if (!detail.versions?.length) { setError("Este documento no tiene archivos."); return; }
      await showVersion(detail, detail.versions[0]);
    } catch (caught) { setError(errorText(caught)); }
  }

  async function download(doc, version) {
    try {
      const blob = await downloadDocumentVersion(doc.id_document, version.version, true);
      const url = URL.createObjectURL(blob); const anchor = window.document.createElement("a");
      anchor.href = url; anchor.download = version.original_filename || `documento-${doc.id_document}-v${version.version}`; anchor.click(); URL.revokeObjectURL(url);
    } catch (caught) { setError(errorText(caught)); }
  }

  async function remove(item) {
    if (!window.confirm(`Eliminar el documento "${item.title}"? Dejara de aparecer en el listado.`)) return;
    setError("");
    try {
      await deleteDocument(item.id_document);
      if (viewer?.doc.id_document === item.id_document) closeViewer();
      if (documents.length === 1 && page > 1) setPage(page - 1); else setReloadKey((key) => key + 1);
    } catch (caught) { setError(errorText(caught)); }
  }

  async function submit(event) {
    event.preventDefault(); setError("");
    const formElement = event.currentTarget;
    if (!file) { setError("Selecciona un archivo PDF, JPEG o PNG."); return; }
    try {
      await uploadDocument(form, file);
      setForm({ ...form, title: "", description: "" }); setFile(null); formElement.reset();
      setPage(1); setReloadKey((key) => key + 1);
    } catch (caught) { setError(errorText(caught)); }
  }

  function applyFilters(event) {
    event.preventDefault();
    if (draft.issue_date_from && draft.issue_date_to && draft.issue_date_from > draft.issue_date_to) {
      setError("La fecha inicial no puede ser posterior a la final."); return;
    }
    setPage(1); setApplied({ ...draft });
  }

  function clearFilters() {
    setDraft(EMPTY_FILTERS); setApplied({ ...EMPTY_FILTERS }); setPage(1);
  }

  const setFilter = (key) => (event) => setDraft({ ...draft, [key]: event.target.value });
  const pages = Math.max(1, Math.ceil(total / PER_PAGE));
  const hasFilters = Object.values(applied).some(Boolean);

  return <div className="lab-page">
    <header className="lab-heading"><div><p>GESTION DOCUMENTAL</p><h1>Documentos y evidencias</h1></div><button className="icon-command" onClick={() => setReloadKey((key) => key + 1)} title="Actualizar"><RefreshCw size={18} /></button></header>
    {error && <div className="lab-error">{error}</div>}
    <div className="lab-columns" style={canCreate ? undefined : { gridTemplateColumns: "minmax(0, 1fr)" }}>
      {canCreate && <form className="lab-panel lab-form" onSubmit={submit}>
        <h2><FilePlus2 size={18} /> Cargar documento</h2>
        <label>Titulo<input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required /></label>
        <label>Categoria<select value={form.id_document_category} onChange={(event) => setForm({ ...form, id_document_category: event.target.value })} required><option value="">Seleccionar</option>{categories.map((item) => <option key={item.id_document_category} value={item.id_document_category}>{item.name}</option>)}</select></label>
        <label>Relacionado con<select value={form.relation_type} onChange={(event) => setForm({ ...form, relation_type: event.target.value, id_customer_supplier: "", id_employee: "" })}><option value="customer">Cliente o proveedor</option><option value="employee">Empleado</option></select></label>
        {form.relation_type === "employee" ? <label>Empleado<select value={form.id_employee} onChange={(event) => setForm({ ...form, id_employee: event.target.value })} required><option value="">{employees.length ? "Seleccionar" : "No hay empleados activos"}</option>{employees.map((item) => <option key={item.id_user} value={item.id_user}>{item.full_name}</option>)}</select></label> : <label>Cliente o proveedor<select value={form.id_customer_supplier} onChange={(event) => setForm({ ...form, id_customer_supplier: event.target.value })} required><option value="">Seleccionar</option>{customers.map((item) => <option key={item.id_customer_supplier} value={item.id_customer_supplier}>{item.name}</option>)}</select></label>}
        <label>Descripcion<textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
        <label>Archivo<input type="file" accept="application/pdf,image/jpeg,image/png" onChange={(event) => setFile(event.target.files?.[0] || null)} required /></label>
        <button className="primary-command" type="submit">Cargar</button>
      </form>}
      <section className="lab-panel lab-list-panel">
        <form className="doc-filters" onSubmit={applyFilters}>
          <label className="doc-filter-wide">Buscar<span className="search-control"><Search size={16} /><input placeholder="Titulo o descripcion" value={draft.search} onChange={setFilter("search")} /></span></label>
          <label>Persona<select value={draft.person} onChange={setFilter("person")}>
            <option value="">Todas</option>
            {employees.length > 0 && <optgroup label="Empleados">{employees.map((item) => <option key={`e${item.id_user}`} value={`employee:${item.id_user}`}>{item.full_name}</option>)}</optgroup>}
            {customers.length > 0 && <optgroup label="Clientes y proveedores">{customers.map((item) => <option key={`c${item.id_customer_supplier}`} value={`customer:${item.id_customer_supplier}`}>{item.name}</option>)}</optgroup>}
          </select></label>
          <label>Tipo de documento<select value={draft.id_document_category} onChange={setFilter("id_document_category")}><option value="">Todos</option>{categories.map((item) => <option key={item.id_document_category} value={item.id_document_category}>{item.name}</option>)}</select></label>
          <label>Estado<select value={draft.status} onChange={setFilter("status")}><option value="">Todos</option>{Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <label>Subido por<select value={draft.created_by} onChange={setFilter("created_by")}><option value="">Todos</option>{uploaders.map((item) => <option key={item.id_user} value={item.id_user}>{item.full_name}</option>)}</select></label>
          <label>Emitido desde<input type="date" value={draft.issue_date_from} onChange={setFilter("issue_date_from")} /></label>
          <label>Emitido hasta<input type="date" value={draft.issue_date_to} onChange={setFilter("issue_date_to")} /></label>
          <div className="doc-filter-actions"><button className="primary-command" type="submit">Filtrar</button><button className="secondary-command" type="button" onClick={clearFilters} disabled={!hasFilters && JSON.stringify(draft) === JSON.stringify(EMPTY_FILTERS)}>Limpiar</button></div>
        </form>
        <div className="lab-table-wrap"><table><thead><tr><th>Titulo</th><th>Tipo</th><th>Ligado a</th><th>Estado</th><th>Subido por</th><th>Emision</th><th>Creacion</th><th></th></tr></thead><tbody>{documents.map((item) => <tr key={item.id_document}>
          <td>{item.title}{item.system_generated && <span className="status-chip doc-system-chip" title="Lo genero el sistema">Sistema</span>}</td>
          <td>{item.category_name || "—"}</td>
          <td>{item.related?.length ? item.related.map((target) => `${TARGET_LABELS[target.target] || target.target}: ${target.name || "—"}`).join(", ") : "—"}</td>
          <td><span className={`status-chip status-${item.status}`}>{STATUS_LABELS[item.status] || item.status}</span></td>
          <td>{item.created_by_name || "—"}</td>
          <td>{String(item.issue_date || "").slice(0, 10) || "—"}</td>
          <td>{String(item.creation_date || "").slice(0, 10)}</td>
          <td className="doc-actions">
            {canViewContent && <button className="table-action" onClick={() => openViewer(item)} title="Ver documento"><Eye size={16} /> Ver</button>}
            {canDelete && (item.system_generated
              ? <button className="table-action danger" disabled title="Lo genero el sistema y no se puede borrar"><Lock size={16} /> Borrar</button>
              : <button className="table-action danger" onClick={() => remove(item)} title="Eliminar documento"><Trash2 size={16} /> Borrar</button>)}
          </td>
        </tr>)}</tbody></table>{!documents.length && !loading && <p className="empty-state">No hay documentos para estos filtros.</p>}</div>
        <div className="doc-pager"><span>{total} {total === 1 ? "documento" : "documentos"}</span><div>
          <button className="table-action" disabled={page <= 1 || loading} onClick={() => setPage(page - 1)}>Anterior</button>
          <span>Pagina {page} de {pages}</span>
          <button className="table-action" disabled={page >= pages || loading} onClick={() => setPage(page + 1)}>Siguiente</button>
        </div></div>
      </section>
    </div>
    {viewer && <div className="doc-viewer-backdrop" onClick={closeViewer}>
      <div className="doc-viewer" role="dialog" aria-modal="true" aria-label={viewer.doc.title} onClick={(event) => event.stopPropagation()}>
        <header className="doc-viewer-head">
          <div><h2>{viewer.doc.title}</h2><small>{viewer.doc.category_name}{viewer.doc.system_generated ? " · generado por el sistema" : ""}</small></div>
          <div className="doc-viewer-tools">
            <button className="secondary-command" onClick={() => download(viewer.doc, viewer.version)}><Download size={16} /> Descargar</button>
            <button className="icon-command" onClick={closeViewer} title="Cerrar"><X size={18} /></button>
          </div>
        </header>
        {viewer.doc.versions.length > 1 && <div className="doc-viewer-versions">{viewer.doc.versions.map((version) => <button key={version.id_document_version} className={`table-action${version.version === viewer.version.version ? " active" : ""}`} onClick={() => showVersion(viewer.doc, version)}>v{version.version} · {STATUS_LABELS[version.status] || version.status}</button>)}</div>}
        <div className="doc-viewer-body">
          {viewer.loading && <p className="empty-state">Cargando...</p>}
          {viewer.error && <div className="lab-error">{viewer.error}</div>}
          {viewer.kind === "pdf" && viewer.url && <iframe title={viewer.doc.title} src={viewer.url} />}
          {viewer.kind === "image" && viewer.url && <img alt={viewer.doc.title} src={viewer.url} />}
          {viewer.kind === "other" && <p className="empty-state">Este tipo de archivo ({viewer.version.extension}) no se puede mostrar aqui. Descargalo para abrirlo.</p>}
        </div>
      </div>
    </div>}
  </div>;
}
