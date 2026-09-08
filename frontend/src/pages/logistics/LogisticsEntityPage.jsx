import { useEffect, useMemo, useState } from "react";
import { Pencil, Plus, RefreshCw, Search, Trash2 } from "lucide-react";

import { getAllCustomerSupplier } from "../../api";
import { useI18n } from "../../i18n";

/* eslint-disable react/prop-types */

function listItems(payload) {
  return Array.isArray(payload) ? payload : payload?.items || [];
}

const clientRelation = {
  field: "id_customer_supplier",
  label: "Cliente",
  labelKey: "logistics.customer",
  placeholder: "Selecciona un cliente",
  placeholderKey: "logistics.select_customer",
  getAll: () => getAllCustomerSupplier({ page: 1, per_page: 500, type: "client" }),
  idField: "id_customer_supplier",
  displayField: "name",
};

export default function LogisticsEntityPage({ config }) {
  const { t } = useI18n();
  const translate = (key, fallback) => key ? t(key, fallback) : fallback;
  const singular = translate(config.singularKey, config.singular);
  const plural = translate(config.pluralKey, config.plural);
  const article = translate(config.articleKey, config.article);
  const newLabel = translate(config.newLabelKey, config.newLabel);
  const moduleLabel = translate(config.moduleLabelKey, config.moduleLabel || t("logistics.module"));
  const fieldLabel = (field) => translate(field.labelKey, field.label);
  const relationLabel = (relation) => translate(relation.labelKey, relation.label);
  const [items, setItems] = useState([]);
  const [relatedItems, setRelatedItems] = useState({});
  const [form, setForm] = useState(config.emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const relations = useMemo(() => {
    if (config.relations) return config.relations;
    const relation = config.relation === undefined ? clientRelation : config.relation;
    return relation ? [relation] : [];
  }, [config]);

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [itemPayload, ...relatedPayloads] = await Promise.all([
        config.getAll({ page: 1, per_page: 200 }),
        ...relations.map((relation) => relation.getAll()),
      ]);
      setItems(listItems(itemPayload));
      setRelatedItems(Object.fromEntries(relations.map((relation, index) => [relation.field, listItems(relatedPayloads[index])])));
    } catch (requestError) {
      setError(requestError.message || `${t("logistics.error_load")} ${plural.toLowerCase()}.`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let mounted = true;
    Promise.all([
      config.getAll({ page: 1, per_page: 200 }),
      ...relations.map((relation) => relation.getAll()),
    ])
      .then(([itemPayload, ...relatedPayloads]) => {
        if (!mounted) return;
        setItems(listItems(itemPayload));
        setRelatedItems(Object.fromEntries(relations.map((relation, index) => [relation.field, listItems(relatedPayloads[index])])));
      })
      .catch((requestError) => {
        if (mounted) setError(requestError.message || `${t("logistics.error_load")} ${plural.toLowerCase()}.`);
      })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [config, relations]); // eslint-disable-line react-hooks/exhaustive-deps

  const relatedNames = useMemo(() => Object.fromEntries(relations.map((relation) => [
    relation.field,
    new Map((relatedItems[relation.field] || []).map((item) => [Number(item[relation.idField]), item[relation.displayField]])),
  ])), [relatedItems, relations]);
  const filteredItems = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return items;
    return items.filter((item) => [
      ...relations.map((relation) => relatedNames[relation.field]?.get(Number(item[relation.field]))),
      ...config.searchFields.map((fieldName) => item[fieldName]),
    ].some((value) => String(value || "").toLowerCase().includes(needle)));
  }, [config.searchFields, items, query, relatedNames, relations]);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  function resetForm() {
    setForm(config.emptyForm);
    setEditingId(null);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    const payload = { ...form };
    relations.forEach((relation) => {
      payload[relation.field] = form[relation.field] === "" ? null : Number(form[relation.field]);
    });
    config.fields.filter((field) => field.type === "number").forEach((field) => {
      payload[field.name] = payload[field.name] === "" ? null : Number(payload[field.name]);
    });
    try {
      config.fields.filter((field) => field.type === "json").forEach((field) => {
        payload[field.name] = payload[field.name].trim() ? JSON.parse(payload[field.name]) : {};
      });
      if (editingId) await config.update(editingId, payload);
      else await config.create(payload);
      resetForm();
      await loadData();
    } catch (requestError) {
      setError(requestError.message || `${t("logistics.error_save")} ${singular.toLowerCase()}.`);
    }
  }

  function editItem(item) {
    const nextForm = { ...config.emptyForm };
    Object.keys(nextForm).forEach((fieldName) => {
      const field = config.fields.find((candidate) => candidate.name === fieldName);
      const value = item[fieldName];
      if (field?.type === "json") nextForm[fieldName] = JSON.stringify(value || {}, null, 2);
      else if (field?.type === "datetime-local" && value) nextForm[fieldName] = String(value).slice(0, 16);
      else nextForm[fieldName] = value ?? "";
    });
     relations.forEach((relation) => { nextForm[relation.field] = item[relation.field] == null ? "" : String(item[relation.field]); });
    setEditingId(item[config.idField]);
    setForm(nextForm);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function removeItem(item) {
    const itemName = item[config.displayField] || item[config.idField];
    if (!window.confirm(`${t("logistics.confirm_delete")} ${article} ${singular.toLowerCase()} ${itemName}?`)) return;
    try {
      await config.remove(item[config.idField]);
      await loadData();
    } catch (requestError) {
      setError(requestError.message || `${t("logistics.error_delete")} ${singular.toLowerCase()}.`);
    }
  }

  return (
    <section className="entity-page logistics-entity-page">
      <div className="page-heading">
        <div><p className="eyebrow">{moduleLabel}</p><h2>{plural}</h2></div>
        <button className="button ghost" type="button" onClick={loadData}><RefreshCw size={16} /> {t("logistics.refresh")}</button>
      </div>

      <form className="form-card" onSubmit={handleSubmit}>
        <div className="form-header"><Plus size={18} /><strong>{editingId ? `${t("logistics.edit")} ${singular.toLowerCase()}` : `${newLabel} ${singular.toLowerCase()}`}</strong></div>
        <div className="form-grid">
          {relations.map((relation) => <label className="field" key={relation.field}><span>{relationLabel(relation)}</span><select name={relation.field} value={form[relation.field]} onChange={handleChange} required={relation.required !== false}><option value="">{translate(relation.placeholderKey, relation.placeholder)}</option>{(relatedItems[relation.field] || []).map((item) => <option key={item[relation.idField]} value={item[relation.idField]}>{item[relation.displayField]}</option>)}</select></label>)}
          {config.fields.map((field) => (
            <label className="field" key={field.name}>
              <span>{fieldLabel(field)}</span>
              {field.options ? (
                <select name={field.name} value={form[field.name]} onChange={handleChange} required={field.required}>{field.options.map((option) => <option key={option.value} value={option.value}>{translate(option.labelKey, option.label)}</option>)}</select>
              ) : field.type === "textarea" ? (
                  <textarea name={field.name} value={form[field.name]} onChange={handleChange} required={field.required} maxLength={field.maxLength} />
                ) : field.type === "json" ? (
                  <textarea name={field.name} value={form[field.name]} onChange={handleChange} required={field.required} maxLength={field.maxLength} />
              ) : (
                <input name={field.name} type={field.type || "text"} value={form[field.name]} onChange={handleChange} required={field.required} maxLength={field.maxLength} min={field.min} step={field.step} />
              )}
            </label>
          ))}
        </div>
        <div className="form-actions"><button className="button primary" type="submit">{t("logistics.save")}</button>{editingId && <button className="button" type="button" onClick={resetForm}>{t("logistics.cancel")}</button>}</div>
      </form>

      <div className="toolbar"><div className="search-box"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={`${t("logistics.search")} ${singular.toLowerCase()}${relations.length ? ` ${t("logistics.or")} ${relations.map((relation) => relationLabel(relation).toLowerCase()).join("/")}` : ""}`} /></div></div>
      {error && <div className="alert error">{error}</div>}
      {loading && <div className="alert">{t("logistics.loading")} {plural.toLowerCase()}...</div>}
      {!loading && filteredItems.length === 0 && <div className="empty"><strong>{t("logistics.empty")} {plural.toLowerCase()}</strong><p>{translate(config.emptyMessageKey, config.emptyMessage)}</p></div>}
      {!loading && filteredItems.length > 0 && <div className="table-card"><table><thead><tr><th>{t("logistics.actions")}</th>{relations.map((relation) => <th key={relation.field}>{relationLabel(relation)}</th>)}{config.columns.map((column) => <th key={column.name}>{translate(column.labelKey, column.label)}</th>)}</tr></thead><tbody>{filteredItems.map((item) => <tr key={item[config.idField]}><td className="row-actions"><button type="button" onClick={() => editItem(item)} title={t("logistics.edit")}><Pencil size={15} /></button><button type="button" onClick={() => removeItem(item)} title={t("logistics.delete")}><Trash2 size={15} /></button></td>{relations.map((relation) => <td key={relation.field}>{relatedNames[relation.field]?.get(Number(item[relation.field])) || item[relation.field]}</td>)}{config.columns.map((column) => <td key={column.name}>{column.format ? column.format(item[column.name], item) : item[column.name]}</td>)}</tr>)}</tbody></table></div>}
    </section>
  );
}