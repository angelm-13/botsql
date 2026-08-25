import React, { useEffect, useMemo, useState } from "react";
import { Pencil, Plus, RefreshCw, Search, Trash2 } from "lucide-react";

import {
  createLogisticsContact,
  deleteLogisticsContact,
  getAllCustomerSupplier,
  getAllLogisticsContact,
  updateLogisticsContact,
} from "../../api";
import { useI18n } from "../../i18n";

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

export default function LogisticsContactsPage() {
  const { t } = useI18n();
  const [contacts, setContacts] = useState([]);
  const [clients, setClients] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [contactPayload, clientPayload] = await Promise.all([
        getAllLogisticsContact({ page: 1, per_page: 200 }),
        getAllCustomerSupplier({ page: 1, per_page: 500, type: "client" }),
      ]);
      setContacts(listItems(contactPayload));
      setClients(listItems(clientPayload));
    } catch (requestError) {
      setError(requestError.message || `${t("logistics.error_load")} ${t("logistics.contact_plural").toLowerCase()}.`);
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
      if (editingId) await updateLogisticsContact(editingId, payload);
      else await createLogisticsContact(payload);
      setForm(emptyForm);
      setEditingId(null);
      await loadData();
    } catch (requestError) {
      setError(requestError.message || `${t("logistics.error_save")} ${t("logistics.contact_singular").toLowerCase()}.`);
    }
  }

  function editContact(contact) {
    setEditingId(contact.id_logistics_contact);
    setForm({ ...emptyForm, ...contact, id_customer_supplier: String(contact.id_customer_supplier) });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function removeContact(contact) {
    if (!window.confirm(`${t("logistics.confirm_delete")} ${t("logistics.contact_article")} ${t("logistics.contact_singular").toLowerCase()} ${contact.full_name}?`)) return;
    try {
      await deleteLogisticsContact(contact.id_logistics_contact);
      await loadData();
    } catch (requestError) {
      setError(requestError.message || `${t("logistics.error_delete")} ${t("logistics.contact_singular").toLowerCase()}.`);
    }
  }

  return (
    <section className="entity-page logistics-entity-page">
      <div className="page-heading">
        <div><p className="eyebrow">{t("logistics.crm")}</p><h2>{t("logistics.contact_plural")}</h2></div>
        <button className="button ghost" type="button" onClick={loadData}><RefreshCw size={16} /> {t("logistics.refresh")}</button>
      </div>

      <form className="form-card" onSubmit={handleSubmit}>
        <div className="form-header"><Plus size={18} /><strong>{editingId ? `${t("logistics.edit")} ${t("logistics.contact_singular").toLowerCase()}` : `${t("logistics.contact_new")} ${t("logistics.contact_singular").toLowerCase()}`}</strong></div>
        <div className="form-grid">
          <label className="field"><span>{t("logistics.customer")}</span><select name="id_customer_supplier" value={form.id_customer_supplier} onChange={handleChange} required><option value="">{t("logistics.select_customer")}</option>{clients.map((client) => <option key={client.id_customer_supplier} value={client.id_customer_supplier}>{client.name}</option>)}</select></label>
          <label className="field"><span>{t("logistics.full_name")}</span><input name="full_name" value={form.full_name} onChange={handleChange} maxLength="150" required /></label>
          <label className="field"><span>{t("logistics.email")}</span><input name="email" type="email" value={form.email} onChange={handleChange} maxLength="100" /></label>
          <label className="field"><span>{t("logistics.phone")}</span><input name="phone" value={form.phone} onChange={handleChange} maxLength="30" /></label>
          <label className="field"><span>{t("logistics.position")}</span><input name="position" value={form.position} onChange={handleChange} maxLength="80" /></label>
          <label className="field"><span>{t("logistics.status")}</span><select name="status" value={form.status} onChange={handleChange}><option value="activo">{t("logistics.status_active")}</option><option value="inactivo">{t("logistics.status_inactive")}</option></select></label>
        </div>
        <div className="form-actions"><button className="button primary" type="submit">{t("logistics.save")}</button>{editingId && <button className="button" type="button" onClick={() => { setEditingId(null); setForm(emptyForm); }}>{t("logistics.cancel")}</button>}</div>
      </form>

      <div className="toolbar"><div className="search-box"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("logistics.contact_search")} /></div></div>
      {error && <div className="alert error">{error}</div>}
      {loading && <div className="alert">{t("logistics.loading")} {t("logistics.contact_plural").toLowerCase()}...</div>}
      {!loading && filteredContacts.length === 0 && <div className="empty"><strong>{t("logistics.empty")} {t("logistics.contact_plural").toLowerCase()}</strong><p>{t("logistics.contact_empty")}</p></div>}
      {!loading && filteredContacts.length > 0 && <div className="table-card"><table><thead><tr><th>{t("logistics.actions")}</th><th>{t("logistics.customer")}</th><th>{t("logistics.name")}</th><th>{t("logistics.email")}</th><th>{t("logistics.phone")}</th><th>{t("logistics.position")}</th><th>{t("logistics.status")}</th></tr></thead><tbody>{filteredContacts.map((contact) => <tr key={contact.id_logistics_contact}><td className="row-actions"><button type="button" onClick={() => editContact(contact)} title={t("logistics.edit")}><Pencil size={15} /></button><button type="button" onClick={() => removeContact(contact)} title={t("logistics.delete")}><Trash2 size={15} /></button></td><td>{clientNames.get(Number(contact.id_customer_supplier)) || contact.id_customer_supplier}</td><td>{contact.full_name}</td><td>{contact.email}</td><td>{contact.phone}</td><td>{contact.position}</td><td>{t(`logistics.status_${contact.status}`, contact.status)}</td></tr>)}</tbody></table></div>}
    </section>
  );
}