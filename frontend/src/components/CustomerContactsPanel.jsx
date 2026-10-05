import { useEffect, useMemo, useState } from "react";
import { Pencil, RefreshCw, Search, Trash2 } from "lucide-react";

import {
  createCustomerContact,
  deleteCustomerContact,
  getAllCustomerSupplier,
  getAllCustomerContact,
  updateCustomerContact,
} from "../api";
import { useI18n } from "../i18n";
import PageHeader from "./PageHeader.jsx";
import FormularioPlegable from "./FormularioPlegable.jsx";

/* eslint-disable react/prop-types */

const emptyForm = {
  id_customer_supplier: "",
  full_name: "",
  email: "",
  phone: "",
  position: "",
  status: "activo",
};

function listItems(payload) {
  return Array.isArray(payload) ? payload : payload?.items || [];
}

// Los contactos por empresa que alimentan el select de "Cliente" al crear un
// proyecto ("Empresa — Contacto") -- se gestionan aquí, dentro de Clientes, y
// no en una pantalla propia: son subordinados a la empresa, igual que
// `logistics_contact` dentro de Logística.
export default function CustomerContactsPanel() {
  const { t } = useI18n();
  const [contacts, setContacts] = useState([]);
  const [clients, setClients] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const etiqueta = (clave, porOmision) => t(`customer_contact.${clave}`, porOmision);

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [contactPayload, clientPayload] = await Promise.all([
        getAllCustomerContact({ page: 1, per_page: 200 }),
        getAllCustomerSupplier({ page: 1, per_page: 500, type: "client" }),
      ]);
      setContacts(listItems(contactPayload));
      setClients(listItems(clientPayload));
    } catch (requestError) {
      setError(t(requestError.message, etiqueta("error_load", "No fue posible cargar los contactos.")));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadData(); }, []);

  const clientNames = useMemo(
    () => new Map(clients.map((client) => [Number(client.id_customer_supplier), client.name])),
    [clients],
  );
  const filteredContacts = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return contacts;
    return contacts.filter((contact) => [
      contact.full_name,
      contact.email,
      contact.phone,
      contact.position,
      clientNames.get(Number(contact.id_customer_supplier)),
    ].some((value) => String(value || "").toLowerCase().includes(needle)));
  }, [clientNames, contacts, query]);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    const payload = { ...form, id_customer_supplier: Number(form.id_customer_supplier) };
    try {
      if (editingId) await updateCustomerContact(editingId, payload);
      else await createCustomerContact(payload);
      setForm(emptyForm);
      setEditingId(null);
      await loadData();
    } catch (requestError) {
      setError(t(requestError.message, etiqueta("error_save", "No fue posible guardar el contacto.")));
    }
  }

  function editContact(contact) {
    setEditingId(contact.id_customer_contact);
    setForm({ ...emptyForm, ...contact, id_customer_supplier: String(contact.id_customer_supplier) });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function removeContact(contact) {
    if (!window.confirm(`${etiqueta("confirm_delete", "¿Eliminar este contacto?")} ${contact.full_name}`)) return;
    try {
      await deleteCustomerContact(contact.id_customer_contact);
      await loadData();
    } catch (requestError) {
      setError(t(requestError.message, etiqueta("error_save", "No fue posible guardar el contacto.")));
    }
  }

  return (
    <section className="entity-page customer-contact-panel">
      <PageHeader eyebrow="CRM" titulo={etiqueta("title", "Contactos")} subtitulo={etiqueta("subtitle", "Las personas con quienes tratas en cada empresa cliente. Elige la empresa a la que pertenece el contacto (debe estar registrada antes en Clientes); después podrás elegir ese contacto al crear un proyecto.")}>
        <button className="button ghost" type="button" onClick={loadData}><RefreshCw size={16} /> {t("common.refresh")}</button>
      </PageHeader>

      <FormularioPlegable
        titulo={editingId ? etiqueta("edit_contact", "Editar contacto") : etiqueta("new_contact", "Nuevo contacto")}
        abrirSi={editingId}
        onSubmit={handleSubmit}
      >
        <div className="form-grid">
          <label className="field"><span>{etiqueta("customer", "Empresa")}</span><select name="id_customer_supplier" value={form.id_customer_supplier} onChange={handleChange} required><option value="">{etiqueta("select_customer", "Selecciona una empresa")}</option>{clients.map((client) => <option key={client.id_customer_supplier} value={client.id_customer_supplier}>{client.name}</option>)}</select></label>
          <label className="field"><span>{etiqueta("full_name", "Nombre completo")}</span><input name="full_name" value={form.full_name} onChange={handleChange} maxLength="150" required /></label>
          <label className="field"><span>{etiqueta("email", "Correo")}</span><input name="email" type="email" value={form.email} onChange={handleChange} maxLength="100" /></label>
          <label className="field"><span>{etiqueta("phone", "Teléfono")}</span><input name="phone" value={form.phone} onChange={handleChange} maxLength="30" /></label>
          <label className="field"><span>{etiqueta("position", "Cargo")}</span><input name="position" value={form.position} onChange={handleChange} maxLength="80" /></label>
          <label className="field"><span>{etiqueta("status", "Estado")}</span><select name="status" value={form.status} onChange={handleChange}><option value="activo">{etiqueta("status_activo", "Activo")}</option><option value="inactivo">{etiqueta("status_inactivo", "Inactivo")}</option></select></label>
        </div>
        <div className="form-actions"><button className="button primary" type="submit">{etiqueta("save", "Guardar")}</button>{editingId && <button className="button" type="button" onClick={() => { setEditingId(null); setForm(emptyForm); }}>{etiqueta("cancel", "Cancelar")}</button>}</div>
      </FormularioPlegable>

      <div className="toolbar"><div className="search-box"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("common.search")} /></div></div>
      {error && <div className="alert error">{error}</div>}
      {loading && <div className="alert">{t("common.loading")}</div>}
      {!loading && filteredContacts.length === 0 && <div className="empty"><strong>{etiqueta("empty", "Sin contactos registrados.")}</strong></div>}
      {!loading && filteredContacts.length > 0 && <div className="table-card"><table><thead><tr><th>{t("common.actions")}</th><th>{etiqueta("customer", "Empresa")}</th><th>{etiqueta("full_name", "Nombre completo")}</th><th>{etiqueta("email", "Correo")}</th><th>{etiqueta("phone", "Teléfono")}</th><th>{etiqueta("position", "Cargo")}</th><th>{etiqueta("status", "Estado")}</th></tr></thead><tbody>{filteredContacts.map((contact) => <tr key={contact.id_customer_contact}><td className="row-actions"><button type="button" onClick={() => editContact(contact)} title={etiqueta("edit", "Editar")}><Pencil size={15} /></button><button type="button" onClick={() => removeContact(contact)} title={etiqueta("delete", "Eliminar")}><Trash2 size={15} /></button></td><td>{clientNames.get(Number(contact.id_customer_supplier)) || contact.id_customer_supplier}</td><td>{contact.full_name}</td><td>{contact.email}</td><td>{contact.phone}</td><td>{contact.position}</td><td>{etiqueta(`status_${contact.status}`, contact.status)}</td></tr>)}</tbody></table></div>}
    </section>
  );
}
