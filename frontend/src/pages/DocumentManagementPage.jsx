import { useEffect, useState } from "react";
import { Download, FilePlus2, RefreshCw, Search } from "lucide-react";

import { downloadDocumentVersion, getAllCustomerSupplier, getDocument, getDocumentCategories, getDocumentEmployees, getDocuments, uploadDocument } from "../api";
import "../styles/laboratory.css";


export default function DocumentManagementPage() {
  const [documents, setDocuments] = useState([]);
  const [categories, setCategories] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", id_document_category: "", id_customer_supplier: "", id_employee: "", relation_type: "customer", status: "draft" });
  const [file, setFile] = useState(null);

  async function load() {
    setLoading(true); setError("");
    try {
      const [docs, categoryRows, customerRows, employeeRows] = await Promise.all([
        getDocuments({ page: 1, per_page: 50, search, status }), getDocumentCategories(), getAllCustomerSupplier({ page: 1, per_page: 500 }), getDocumentEmployees(),
      ]);
      setDocuments(docs.items || []); setCategories(categoryRows || []); setCustomers(customerRows.items || customerRows || []); setEmployees(employeeRows || []);
    } catch (caught) { setError(caught.message); } finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function submit(event) {
    event.preventDefault(); setError("");
    if (!file) { setError("Selecciona un archivo PDF, JPEG o PNG."); return; }
    try {
      await uploadDocument(form, file);
      setForm({ ...form, title: "", description: "" }); setFile(null); event.currentTarget.reset(); await load();
    } catch (caught) { setError(caught.message); }
  }

  async function inspect(id) {
    try { setSelected(await getDocument(id)); } catch (caught) { setError(caught.message); }
  }

  async function download(documentId, version) {
    try {
      const blob = await downloadDocumentVersion(documentId, version);
      const url = URL.createObjectURL(blob); const anchor = window.document.createElement("a");
      anchor.href = url; anchor.download = `documento-${documentId}-v${version}`; anchor.click(); URL.revokeObjectURL(url);
    } catch (caught) { setError(caught.message); }
  }

  return <div className="lab-page">
    <header className="lab-heading"><div><p>GESTION DOCUMENTAL</p><h1>Documentos y evidencias</h1></div><button className="icon-command" onClick={load} title="Actualizar"><RefreshCw size={18} /></button></header>
    {error && <div className="lab-error">{error}</div>}
    <div className="lab-columns">
      <form className="lab-panel lab-form" onSubmit={submit}>
        <h2><FilePlus2 size={18} /> Cargar documento</h2>
        <label>Titulo<input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required /></label>
        <label>Categoria<select value={form.id_document_category} onChange={(event) => setForm({ ...form, id_document_category: event.target.value })} required><option value="">Seleccionar</option>{categories.map((item) => <option key={item.id_document_category} value={item.id_document_category}>{item.name}</option>)}</select></label>
        <label>Relacionado con<select value={form.relation_type} onChange={(event) => setForm({ ...form, relation_type: event.target.value, id_customer_supplier: "", id_employee: "" })}><option value="customer">Cliente o proveedor</option><option value="employee">Empleado</option></select></label>
        {form.relation_type === "employee" ? <label>Empleado<select value={form.id_employee} onChange={(event) => setForm({ ...form, id_employee: event.target.value })} required><option value="">{employees.length ? "Seleccionar" : "No hay empleados activos"}</option>{employees.map((item) => <option key={item.id_user} value={item.id_user}>{item.full_name}</option>)}</select></label> : <label>Cliente o proveedor<select value={form.id_customer_supplier} onChange={(event) => setForm({ ...form, id_customer_supplier: event.target.value })} required><option value="">Seleccionar</option>{customers.map((item) => <option key={item.id_customer_supplier} value={item.id_customer_supplier}>{item.name}</option>)}</select></label>}
        <label>Descripcion<textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
        <label>Archivo<input type="file" accept="application/pdf,image/jpeg,image/png" onChange={(event) => setFile(event.target.files?.[0] || null)} required /></label>
        <button className="primary-command" type="submit">Cargar</button>
      </form>
      <section className="lab-panel lab-list-panel">
        <div className="lab-toolbar"><div className="search-control"><Search size={16} /><input placeholder="Buscar por titulo" value={search} onChange={(event) => setSearch(event.target.value)} /></div><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">Todos los estados</option><option value="draft">Borrador</option><option value="issued">Emitido</option><option value="signed">Firmado</option><option value="rejected">Rechazado</option><option value="cancelled">Cancelado</option></select><button onClick={load}>Filtrar</button></div>
        <div className="lab-table-wrap"><table><thead><tr><th>Titulo</th><th>Estado</th><th>Creacion</th><th></th></tr></thead><tbody>{documents.map((item) => <tr key={item.id_document}><td>{item.title}</td><td><span className={`status-chip status-${item.status}`}>{item.status}</span></td><td>{String(item.creation_date || "").slice(0, 10)}</td><td><button className="table-action" onClick={() => inspect(item.id_document)}>Versiones</button></td></tr>)}</tbody></table>{!documents.length && !loading && <p className="empty-state">No hay documentos para estos filtros.</p>}</div>
        {selected && <div className="version-drawer"><h3>{selected.title}</h3>{selected.versions.map((version) => <div className="version-row" key={version.id_document_version}><span>v{version.version} · {version.source} · {version.status}</span><button className="icon-command" title="Descargar" onClick={() => download(selected.id_document, version.version)}><Download size={17} /></button></div>)}</div>}
      </section>
    </div>
  </div>;
}