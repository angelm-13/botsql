import { useEffect, useMemo, useState } from "react";
import { Copy, Eye, KeyRound, Pencil, RefreshCw, Search } from "lucide-react";
import {
  bulkSalesCatalogMargin,
  bulkSalesCatalogPublish,
  createSalesCatalogApiKey,
  getSalesCatalogApiKeys,
  getSalesCatalogProducts,
  previewSalesCatalogProductPrice,
  revokeSalesCatalogApiKey,
  updateSalesCatalogApiKey,
  upsertSalesCatalogProductConfig,
  getMyPermissions,
} from "../api";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader.jsx";
import FormularioPlegable from "../components/FormularioPlegable.jsx";

function asArray(payload) {
  if (Array.isArray(payload?.items)) return payload.items;
  if (Array.isArray(payload)) return payload;
  return [];
}

function money(value) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("es-MX", { style: "currency", currency: "MXN" });
}

function numberOrEmpty(value) {
  if (value === null || value === undefined || value === "") return "";
  return String(value);
}

function textOrDash(value) {
  const text = String(value ?? "").trim();
  return text || "—";
}

function productId(row) {
  return row.id_product ?? row.product_id ?? row.id;
}

function productName(row) {
  return row.descripcion || row.name || row.product_name || row.product_description || "—";
}

function productSku(row) {
  return row.product_code || row.sku || row.code || "—";
}

function statusRawValue(row) {
  const raw = row.publication_status
    || row.inventory_status_code
    || row.inventory_status
    || row.status
    || row.config?.inventory_status_code
    || row.config?.inventory_status
    || row.inventory_status_description
    || (row.is_published ? "web_published" : "");

  if (typeof raw !== "object" || raw === null) return raw || "";
  return raw.inventory_status_code
    || raw.code
    || raw.value
    || raw.inventory_status_description
    || raw.label
    || raw.name
    || raw.description
    || raw.status
    || "";
}

function statusCode(row) {
  const normalized = String(statusRawValue(row) || "").trim().toLowerCase();
  const aliases = {
    publicado: "web_published",
    "publicado en web": "web_published",
    published: "web_published",
    despublicado: "web_unpublished",
    "no publicado": "web_unpublished",
    unpublished: "web_unpublished",
    borrador: "web_draft",
    draft: "web_draft",
  };
  return aliases[normalized] || normalized;
}

function statusText(row) {
  const labels = {
    web_published: "Publicado",
    web_unpublished: "Despublicado",
    web_draft: "Borrador",
  };
  const code = statusCode(row);
  return labels[code] || String(statusRawValue(row) || "").trim();
}

function configValue(row, key) {
  return row?.config?.[key] ?? row?.[key];
}

function pricingValue(row, key) {
  return row?.pricing?.[key] ?? row?.[key];
}

function finalPrice(row) {
  return pricingValue(row, "public_price") ?? pricingValue(row, "final_price") ?? pricingValue(row, "price_with_tax") ?? row.price ?? row.preview_price;
}

const PERMISSION_BITS = { CREATE: 1, READ: 2, UPDATE: 4, DELETE: 8 };

function controlMask(row) {
  const value = Number(row?.control_type ?? 0);
  return Number.isFinite(value) ? value : 0;
}

function hasEntityPermission(rows, entityName, bit) {
  return (rows || []).some((row) => row?.entity_name === entityName && (controlMask(row) & bit) === bit);
}

function canManageEntity(rows, entityName) {
  return hasEntityPermission(rows, entityName, PERMISSION_BITS.CREATE)
    || hasEntityPermission(rows, entityName, PERMISSION_BITS.UPDATE)
    || hasEntityPermission(rows, entityName, PERMISSION_BITS.DELETE);
}

function currentCatalogUser() {
  try {
    return JSON.parse(localStorage.getItem("user") || "null") || {};
  } catch {
    return {};
  }
}

function isCatalogPrivilegedUser(user) {
  const username = String(user?.username || "").trim();
  const userType = String(user?.user_type || "").trim().toLowerCase();
  const bootstrapUsername = import.meta.env.VITE_BOOTSTRAP_ADMIN_USERNAME || "admin1";
  return Boolean(
    user?.is_superuser
    || user?.is_bootstrap_admin
    || userType === "admin"
    || username === bootstrapUsername
  );
}

export default function CatalogoWebPage() {
  const { t } = useI18n();
  const [tab, setTab] = useState("products");
  const [products, setProducts] = useState([]);
  const [apiKeys, setApiKeys] = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [configFilter, setConfigFilter] = useState("all");
  const [bulkMargin, setBulkMargin] = useState("");
  const [editingProduct, setEditingProduct] = useState(null);
  const [productForm, setProductForm] = useState({ margin_percent: "", manual_price: "", id_inventory_status: "", is_active: true });
  const [pricePreview, setPricePreview] = useState(null);
  const [keyForm, setKeyForm] = useState({ label: "", allowed_domains: "[]", rate_limit_per_min: "60" });
  const [createdKey, setCreatedKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [permissions, setPermissions] = useState([]);

  const filteredProducts = useMemo(() => products.filter((row) => {
    const haystack = `${productName(row)} ${productSku(row)}`.toLowerCase();
    const matchesQuery = !query.trim() || haystack.includes(query.trim().toLowerCase());
    const normalizedStatus = statusCode(row);
    const matchesStatus = statusFilter === "all" || normalizedStatus === statusFilter;
    const marginValue = configValue(row, "margin_percent");
    const manualPriceValue = configValue(row, "manual_price");
    const hasMargin = marginValue !== null && marginValue !== undefined && marginValue !== "";
    const hasManualPrice = manualPriceValue !== null && manualPriceValue !== undefined && manualPriceValue !== "";
    const configured = hasMargin || hasManualPrice;
    const matchesConfig = configFilter === "all" || (configFilter === "configured" ? configured : !configured);
    return matchesQuery && matchesStatus && matchesConfig;
  }), [products, query, statusFilter, configFilter]);

  const selectedCount = selectedIds.size;
  const catalogUser = currentCatalogUser();
  const isCatalogAdmin = isCatalogPrivilegedUser(catalogUser);
  const canReadProducts = isCatalogAdmin || hasEntityPermission(permissions, "product_sale_config", PERMISSION_BITS.READ);
  const canManageProducts = isCatalogAdmin || canManageEntity(permissions, "product_sale_config");
  const canManageApiKeys = isCatalogAdmin || canManageEntity(permissions, "public_api_key");

  function resolveError(err) {
    const payload = err?.payload || {};
    const raw = payload.error_key || err?.message || "errors.request_failed";
    const fallbackByKey = {
      "errors.permission_denied": "No tienes permiso para realizar esta acción.",
      "errors.invalid_token": "La sesión o llave no es válida.",
      "errors.request_failed": "No se pudo completar la solicitud.",
    };
    return t(raw, fallbackByKey[raw] || "No se pudo completar la solicitud");
  }

  async function loadProducts() {
    setLoading(true);
    setError("");
    try {
      const payload = await getSalesCatalogProducts({ page: 1, per_page: 500 });
      setProducts(asArray(payload));
    } catch (err) {
      setError(resolveError(err));
    } finally {
      setLoading(false);
    }
  }

  async function loadApiKeys() {
    setLoading(true);
    setError("");
    try {
      const payload = await getSalesCatalogApiKeys();
      setApiKeys(asArray(payload));
    } catch (err) {
      setError(resolveError(err));
    } finally {
      setLoading(false);
    }
  }

  async function loadPermissions() {
    const payload = await getMyPermissions();
    const rows = Array.isArray(payload?.entity_permissions) ? payload.entity_permissions : [];
    setPermissions(rows);
    return rows;
  }

  async function reloadAll() {
    setMessage("");
    setError("");
    try {
      const rows = await loadPermissions();
      const apiKeysAllowed = isCatalogPrivilegedUser(currentCatalogUser()) || canManageEntity(rows, "public_api_key");
      await Promise.all([
        loadProducts(),
        apiKeysAllowed ? loadApiKeys() : Promise.resolve(setApiKeys([])),
      ]);
    } catch (err) {
      setError(resolveError(err));
    }
  }

  useEffect(() => { reloadAll(); }, []);
  useEffect(() => { if (tab === "keys" && !canManageApiKeys) setTab("products"); }, [tab, canManageApiKeys]);

  function toggleSelected(id) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function clearSelection() {
    setSelectedIds(new Set());
  }

  function startEditProduct(row) {
    if (!canManageProducts) return;
    setEditingProduct(row);
    setPricePreview(null);
    setProductForm({
      margin_percent: numberOrEmpty(configValue(row, "margin_percent")),
      manual_price: numberOrEmpty(configValue(row, "manual_price")),
      id_inventory_status: numberOrEmpty(configValue(row, "id_inventory_status") || row.publication_status?.id_inventory_status),
      is_active: configValue(row, "is_active") === undefined || configValue(row, "is_active") === null ? true : Boolean(configValue(row, "is_active")),
    });
  }

  async function previewProductPrice() {
    if (!editingProduct) return;
    try {
      const payload = await previewSalesCatalogProductPrice(productId(editingProduct));
      setPricePreview(payload);
    } catch (err) {
      setError(resolveError(err));
    }
  }

  async function saveProductConfig() {
    if (!canManageProducts) { setError(t("errors.permission_denied", "No tienes permiso para realizar esta acción.")); return; }
    if (!editingProduct) return;
    try {
      await upsertSalesCatalogProductConfig(productId(editingProduct), {
        margin_percent: productForm.margin_percent === "" ? null : Number(productForm.margin_percent),
        manual_price: productForm.manual_price === "" ? null : Number(productForm.manual_price),
        id_inventory_status: productForm.id_inventory_status === "" ? null : Number(productForm.id_inventory_status),
        is_active: Boolean(productForm.is_active),
      });
      setMessage(t("catalogo_web.saved", "Guardado correctamente"));
      setEditingProduct(null);
      await loadProducts();
    } catch (err) {
      setError(resolveError(err));
    }
  }

  async function applyBulkMargin() {
    if (!canManageProducts) { setError(t("errors.permission_denied", "No tienes permiso para realizar esta acción.")); return; }
    if (!selectedCount) { setError(t("catalogo_web.missing_selection", "Selecciona al menos un producto.")); return; }
    try {
      await bulkSalesCatalogMargin({ product_ids: Array.from(selectedIds), margin_percent: Number(bulkMargin || 0) });
      setMessage(t("catalogo_web.saved", "Guardado correctamente"));
      clearSelection();
      await loadProducts();
    } catch (err) {
      setError(resolveError(err));
    }
  }

  async function applyBulkPublish(publish) {
    if (!canManageProducts) { setError(t("errors.permission_denied", "No tienes permiso para realizar esta acción.")); return; }
    if (!selectedCount) { setError(t("catalogo_web.missing_selection", "Selecciona al menos un producto.")); return; }
    if (!window.confirm(t("catalogo_web.confirm_bulk_publish", "¿Aplicar cambio de publicación a los productos seleccionados?"))) return;
    try {
      await bulkSalesCatalogPublish({ product_ids: Array.from(selectedIds), publish: Boolean(publish) });
      setMessage(t("catalogo_web.saved", "Guardado correctamente"));
      clearSelection();
      await loadProducts();
    } catch (err) {
      setError(resolveError(err));
    }
  }

  async function createKey(event) {
    event.preventDefault();
    if (!canManageApiKeys) { setError(t("errors.permission_denied", "No tienes permiso para realizar esta acción.")); return; }
    setCreatedKey("");
    try {
      const payload = await createSalesCatalogApiKey({
        label: keyForm.label,
        allowed_domains: keyForm.allowed_domains || "[]",
        rate_limit_per_min: Number(keyForm.rate_limit_per_min || 60),
      });
      setCreatedKey(payload.plain_key || "");
      setKeyForm({ label: "", allowed_domains: "[]", rate_limit_per_min: "60" });
      setMessage(t("catalogo_web.saved", "Guardado correctamente"));
      await loadApiKeys();
    } catch (err) {
      setError(resolveError(err));
    }
  }

  async function updateKey(row, field, value) {
    if (!canManageApiKeys) { setError(t("errors.permission_denied", "No tienes permiso para realizar esta acción.")); return; }
    try {
      await updateSalesCatalogApiKey(row.id_public_api_key, { ...row, [field]: field === "rate_limit_per_min" ? Number(value || 60) : value });
      setMessage(t("catalogo_web.saved", "Guardado correctamente"));
      await loadApiKeys();
    } catch (err) {
      setError(resolveError(err));
    }
  }

  async function revokeKey(row) {
    if (!canManageApiKeys) { setError(t("errors.permission_denied", "No tienes permiso para realizar esta acción.")); return; }
    if (!window.confirm(t("catalogo_web.confirm_revoke", "¿Revocar esta API key?"))) return;
    try {
      await revokeSalesCatalogApiKey(row.id_public_api_key);
      setMessage(t("catalogo_web.revoked", "Llave revocada"));
      await loadApiKeys();
    } catch (err) {
      setError(resolveError(err));
    }
  }

  function copy(text) {
    if (!text) return;
    navigator.clipboard?.writeText(text);
  }

  return (
    <section className="entity-page catalogo-web-page">
      <PageHeader
        eyebrow={"Issue 10"}
        titulo={t("catalogo_web.title", "Catálogo Web")}
        subtitulo={t("catalogo_web.subtitle", "Gestiona productos publicados y llaves API públicas para la tienda online.")}
      >
        <button type="button" className="button" onClick={reloadAll} disabled={loading}><RefreshCw size={16} />{t("catalogo_web.reload", "Recargar")}</button>
      </PageHeader>

      {message && <div className="alert success">{message}</div>}
      {error && <div className="alert error">{error}</div>}

      <div className="catalogo-tabs">
        <button type="button" className={tab === "products" ? "button active" : "button"} onClick={() => setTab("products")}>{t("catalogo_web.products", "Productos")}</button>
        {canManageApiKeys && <button type="button" className={tab === "keys" ? "button active" : "button"} onClick={() => setTab("keys")}>{t("catalogo_web.api_keys", "API Keys")}</button>}
      </div>

      {tab === "products" && (
        <>
          <div className="form-card catalogo-toolbar">
            <label className="search-box"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("catalogo_web.search_placeholder", "Buscar por nombre o SKU")} /></label>
            <label className="field compact-field">{t("catalogo_web.publication_status", "Estado publicación")}<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="all">{t("catalogo_web.all", "Todos")}</option><option value="web_published">{t("catalogo_web.published", "Publicado")}</option><option value="web_unpublished">{t("catalogo_web.unpublished", "Despublicado")}</option><option value="web_draft">{t("catalogo_web.draft", "Borrador")}</option></select></label>
            <label className="field compact-field">{t("catalogo_web.configuration", "Configuración")}<select value={configFilter} onChange={(event) => setConfigFilter(event.target.value)}><option value="all">{t("catalogo_web.all", "Todos")}</option><option value="configured">{t("catalogo_web.configured", "Configurados")}</option><option value="not_configured">{t("catalogo_web.not_configured", "Sin configurar")}</option></select></label>
            {canManageProducts && <label className="field compact-field">{t("catalogo_web.margin_percent", "Margen %")}<input type="number" step="0.01" value={bulkMargin} onChange={(event) => setBulkMargin(event.target.value)} /></label>}
            {canManageProducts && <button type="button" className="button primary" onClick={applyBulkMargin}>% {t("catalogo_web.bulk_margin", "Aplicar margen masivo")}</button>}
            {canManageProducts && <button type="button" className="button" onClick={() => applyBulkPublish(true)}>{t("catalogo_web.bulk_publish", "Publicar seleccionados")}</button>}
            {canManageProducts && <button type="button" className="button" onClick={() => applyBulkPublish(false)}>{t("catalogo_web.bulk_unpublish", "Despublicar seleccionados")}</button>}
          </div>

          <div className="table-card catalogo-table-card">
            {canManageProducts && <div className="permission-toolbar"><strong>{selectedCount} {t("catalogo_web.selected", "seleccionado(s)")}</strong><button type="button" className="button ghost" onClick={clearSelection}>{t("catalogo_web.clear_selection", "Limpiar selección")}</button></div>}
            <table>
              <thead><tr>{canManageProducts && <th></th>}<th>{t("catalogo_web.image", "Imagen")}</th><th>{t("catalogo_web.sku", "SKU")}</th><th>{t("catalogo_web.name", "Nombre")}</th><th>{t("catalogo_web.stock", "Stock")}</th><th>{t("catalogo_web.base_cost", "Costo/Base")}</th><th>{t("catalogo_web.margin_percent", "Margen %")}</th><th>{t("catalogo_web.manual_price", "Precio manual")}</th><th>{t("catalogo_web.final_price", "Precio final")}</th><th>{t("catalogo_web.status", "Estado")}</th><th>{t("catalogo_web.active", "Activo")}</th>{canManageProducts && <th>{t("catalogo_web.actions", "Acciones")}</th>}</tr></thead>
              <tbody>
                {filteredProducts.map((row) => {
                  const id = productId(row);
                  return <tr key={id}>{canManageProducts && <td><input type="checkbox" checked={selectedIds.has(id)} onChange={() => toggleSelected(id)} /></td>}<td>{row.image_url || row.path_imagen ? <img className="table-image" src={row.image_url || row.path_imagen} alt="" /> : <span className="muted">—</span>}</td><td>{productSku(row)}</td><td><strong>{productName(row)}</strong><p className="cell-value">#{id}</p></td><td>{row.stock_available ?? row.stock ?? "—"}</td><td>{money(row.base_cost ?? row.cost ?? row.gross_price)}</td><td>{configValue(row, "margin_percent") ?? "—"}</td><td>{money(configValue(row, "manual_price"))}</td><td><strong>{money(finalPrice(row))}</strong></td><td><span className="catalogo-pill">{textOrDash(statusText(row))}</span></td><td>{row.is_active === false ? "—" : "✓"}</td>{canManageProducts && <td className="row-actions"><button type="button" onClick={() => startEditProduct(row)} title={t("common.edit", "Editar")}><Pencil size={15} /></button></td>}</tr>;
                })}
                {!filteredProducts.length && <tr><td colSpan={canManageProducts ? 12 : 10} className="muted">{t("catalogo_web.no_products", "No hay productos para los filtros.")}</td></tr>}
              </tbody>
            </table>
          </div>

          {canManageProducts && editingProduct && <div className="catalogo-edit-grid">
            <div className="form-card">
              <div className="form-header"><Pencil size={16} /><strong>{t("catalogo_web.edit_product", "Editar producto de catálogo")}</strong></div>
              <p><strong>{productSku(editingProduct)} - {productName(editingProduct)}</strong></p>
              <div className="form-grid">
                <label className="field">{t("catalogo_web.margin_percent", "Margen %")}<input type="number" step="0.01" value={productForm.margin_percent} onChange={(event) => setProductForm((prev) => ({ ...prev, margin_percent: event.target.value }))} /></label>
                <label className="field">{t("catalogo_web.manual_price", "Precio manual")}<input type="number" step="0.01" value={productForm.manual_price} onChange={(event) => setProductForm((prev) => ({ ...prev, manual_price: event.target.value }))} /></label>
                <label className="field">{t("catalogo_web.status", "Estado")}<input value={productForm.id_inventory_status} onChange={(event) => setProductForm((prev) => ({ ...prev, id_inventory_status: event.target.value }))} placeholder="id_inventory_status" /></label>
                <label className="field checkbox-field"><input type="checkbox" checked={productForm.is_active} onChange={(event) => setProductForm((prev) => ({ ...prev, is_active: event.target.checked }))} />{t("catalogo_web.active", "Activo")}</label>
              </div>
              <div className="form-actions"><button type="button" className="button" onClick={previewProductPrice}><Eye size={15} />{t("catalogo_web.preview_price", "Preview de precio")}</button><button type="button" className="button" onClick={() => setEditingProduct(null)}>{t("common.cancel", "Cancelar")}</button><button type="button" className="button primary" onClick={saveProductConfig}>{t("catalogo_web.save_changes", "Guardar cambios")}</button></div>
            </div>
            <div className="form-card catalogo-price-card">
              <div className="form-header"><Eye size={16} /><strong>{t("catalogo_web.preview_price", "Preview de precio")}</strong></div>
              <div className="metric-grid"><div><span>{t("catalogo_web.base_cost", "Costo/Base")}</span><strong>{money(pricingValue(editingProduct, "base_price") ?? editingProduct.base_cost ?? editingProduct.cost ?? editingProduct.gross_price)}</strong></div><div><span>{t("catalogo_web.margin_percent", "Margen %")}</span><strong>{productForm.margin_percent || "—"}</strong></div><div><span>{t("catalogo_web.manual_price", "Precio manual")}</span><strong>{money(productForm.manual_price)}</strong></div><div><span>{t("catalogo_web.final_price", "Precio final")}</span><strong>{money(pricePreview?.pricing?.public_price ?? pricePreview?.final_price ?? pricePreview?.price_with_tax ?? finalPrice(editingProduct))}</strong></div></div>
              <p className="muted">{t("catalogo_web.price_hint", "Resultado estimado usando reglas de precio del catálogo.")}</p>
            </div>
          </div>}
        </>
      )}

      {tab === "keys" && canManageApiKeys && (
        <>
          <FormularioPlegable
            titulo={t("catalogo_web.create_key", "Crear API key")}
            icono={KeyRound}
            onSubmit={createKey}
          >
            <div className="form-grid"><label className="field">{t("catalogo_web.label", "Etiqueta")}<input value={keyForm.label} onChange={(event) => setKeyForm((prev) => ({ ...prev, label: event.target.value }))} required /></label><label className="field wide-field">{t("catalogo_web.allowed_domains", "Dominios permitidos")}<input value={keyForm.allowed_domains} onChange={(event) => setKeyForm((prev) => ({ ...prev, allowed_domains: event.target.value }))} placeholder='["https://tienda.luis.com"]' /></label><label className="field">{t("catalogo_web.rate_limit", "Límite por minuto")}<input type="number" min="1" value={keyForm.rate_limit_per_min} onChange={(event) => setKeyForm((prev) => ({ ...prev, rate_limit_per_min: event.target.value }))} /></label></div>
            <div className="form-actions"><button className="button primary" type="submit">{t("catalogo_web.create_key", "Crear API key")}</button></div>
            {createdKey && <div className="alert success"><strong>{t("catalogo_web.plain_key_once", "Copia esta llave ahora. Solo se mostrará una vez.")}</strong><p><code>{createdKey}</code></p><button type="button" className="button" onClick={() => copy(createdKey)}><Copy size={15} />{t("catalogo_web.copy_key", "Copiar key")}</button></div>}
          </FormularioPlegable>
          <div className="table-card catalogo-table-card"><table><thead><tr><th>ID</th><th>{t("catalogo_web.label", "Etiqueta")}</th><th>Prefix</th><th>{t("catalogo_web.allowed_domains", "Dominios permitidos")}</th><th>{t("catalogo_web.rate_limit", "Límite por minuto")}</th><th>{t("catalogo_web.active", "Activo")}</th><th>{t("catalogo_web.actions", "Acciones")}</th></tr></thead><tbody>{apiKeys.map((row) => <tr key={row.id_public_api_key}><td>{row.id_public_api_key}</td><td><input value={row.label || ""} onChange={(event) => setApiKeys((prev) => prev.map((item) => item.id_public_api_key === row.id_public_api_key ? { ...item, label: event.target.value } : item))} onBlur={(event) => updateKey(row, "label", event.target.value)} /></td><td>{row.key_prefix}</td><td><input value={row.allowed_domains || "[]"} onChange={(event) => setApiKeys((prev) => prev.map((item) => item.id_public_api_key === row.id_public_api_key ? { ...item, allowed_domains: event.target.value } : item))} onBlur={(event) => updateKey(row, "allowed_domains", event.target.value)} /></td><td><input type="number" min="1" value={row.rate_limit_per_min || 60} onChange={(event) => setApiKeys((prev) => prev.map((item) => item.id_public_api_key === row.id_public_api_key ? { ...item, rate_limit_per_min: event.target.value } : item))} onBlur={(event) => updateKey(row, "rate_limit_per_min", event.target.value)} /></td><td>{row.is_active ? "✓" : "—"}</td><td className="row-actions"><button type="button" onClick={() => revokeKey(row)}>{t("catalogo_web.revoke", "Revocar")}</button></td></tr>)}{!apiKeys.length && <tr><td colSpan="7" className="muted">{t("catalogo_web.no_keys", "No hay API keys registradas.")}</td></tr>}</tbody></table></div>
        </>
      )}
    </section>
  );
}
