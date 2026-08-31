import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle, ArrowRightLeft, CheckCircle2, ClipboardList,
  PackagePlus, RefreshCw, Scale, Warehouse,
} from "lucide-react";
import { useI18n } from "../i18n";
import {
  createInventoryMovement, createInventoryTransfer, getAllEntityPermission,
  getAllProduct, getInventoryMovements, getInventoryReconciliation,
  getLocationTree, getProductStock, getWarehouseStock,
} from "../api";

const ENTITY_KEY = "product";
const ADJUSTMENT_CAPABILITY = "inventory_adjustment";
const ACTION_READ = 2;
const ACTION_UPDATE = 4;

// Movimientos que el almacen registra a mano. El traspaso va aparte porque
// mueve dos ubicaciones a la vez, y el ajuste porque exige otra capacidad.
const MOVEMENT_TYPES = [
  { value: "receive", sign: 1 },
  { value: "return", sign: 1 },
  { value: "issue", sign: -1 },
  { value: "loan", sign: -1 },
  { value: "loss", sign: -1 },
  { value: "damage", sign: -1 },
  { value: "destroy", sign: -1 },
];

// Los que cambian existencia sin documento detras: el motivo es obligatorio y
// conviene que la pantalla lo pida antes de que el servidor lo rechace.
const REASON_REQUIRED = new Set(["loss", "damage", "destroy", "adjustment"]);

const REFERENCE_TYPES = ["invoice", "invoice_line", "purchase", "project", "task", "incident", "count", "manual"];

function hasBit(value, bit) {
  return (Number(value || 0) & bit) === bit;
}

function normalizeList(data) {
  return Array.isArray(data) ? data : (data?.items || data?.data || []);
}

function readCurrentUser() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch (_) { return {}; }
}

function flattenTree(nodes, depth = 0, out = []) {
  for (const node of nodes || []) {
    out.push({ ...node, depth });
    flattenTree(node.children, depth + 1, out);
  }
  return out;
}

export default function InventoryPage() {
  const { t } = useI18n();
  const currentUser = useMemo(() => readCurrentUser(), []);
  const isSuperUser = Boolean(currentUser?.is_superuser || currentUser?.is_bootstrap_admin);
  const roleId = currentUser?.id_permission;

  const [permissionReady, setPermissionReady] = useState(false);
  const [modulePermission, setModulePermission] = useState(null);
  const [canAdjust, setCanAdjust] = useState(false);

  const [tree, setTree] = useState([]);
  const [products, setProducts] = useState([]);
  const [selectedWarehouse, setSelectedWarehouse] = useState("");
  const [warehouseContent, setWarehouseContent] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState("");
  const [stock, setStock] = useState(null);
  const [ledger, setLedger] = useState(null);
  const [reconciliation, setReconciliation] = useState(null);
  const [ledgerFilter, setLedgerFilter] = useState({ movement_type: "", id_location: "" });

  const [movement, setMovement] = useState({ movement_type: "receive", quantity: "1", id_location: "", reason: "", reference_type: "", reference_id: "" });
  const [transfer, setTransfer] = useState({ id_location_from: "", id_location_to: "", quantity: "1", reason: "" });

  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [errorMeta, setErrorMeta] = useState(null);
  const [notice, setNotice] = useState("");

  const canRead = isSuperUser || hasBit(modulePermission?.control_type, ACTION_READ);
  const canWrite = isSuperUser || hasBit(modulePermission?.control_type, ACTION_UPDATE);
  const locations = useMemo(() => flattenTree(tree), [tree]);
  const warehouses = useMemo(() => locations.filter((node) => node.is_warehouse), [locations]);

  // --- permisos -----------------------------------------------------------
  useEffect(() => {
    let alive = true;
    if (isSuperUser) {
      setModulePermission({ control_type: 15 });
      setCanAdjust(true);
      setPermissionReady(true);
      return () => { alive = false; };
    }
    getAllEntityPermission({ page: 1, per_page: 500 })
      .then((payload) => {
        if (!alive) return;
        const rows = normalizeList(payload).filter((row) => String(row.id_permission) === String(roleId));
        setModulePermission(rows.find((row) => row.entity_name === ENTITY_KEY) || null);
        setCanAdjust(rows.some((row) => row.entity_name === ADJUSTMENT_CAPABILITY && hasBit(row.control_type, ACTION_READ)));
      })
      .catch(() => { if (alive) setModulePermission(null); })
      .finally(() => { if (alive) setPermissionReady(true); });
    return () => { alive = false; };
  }, [isSuperUser, roleId]);

  // --- carga base ---------------------------------------------------------
  const loadBase = useCallback(async () => {
    if (!permissionReady || !canRead) return;
    setLoading(true);
    setError("");
    try {
      const [treePayload, productPayload] = await Promise.all([
        getLocationTree(),
        getAllProduct({ page: 1, per_page: 300 }),
      ]);
      setTree(treePayload?.items || []);
      setProducts(normalizeList(productPayload));
    } catch (requestError) {
      showError(requestError);
    } finally {
      setLoading(false);
    }
  }, [permissionReady, canRead]);

  useEffect(() => { loadBase(); }, [loadBase]);

  function showError(requestError) {
    const payload = requestError?.payload || {};
    setError(payload.error_key || payload.error || requestError?.message || "errors.unexpected");
    setErrorMeta(payload.meta || null);
  }

  const refreshProduct = useCallback(async (productId, filters = ledgerFilter) => {
    if (!productId) { setStock(null); setLedger(null); setReconciliation(null); return; }
    try {
      const params = {};
      if (filters.movement_type) params.movement_type = filters.movement_type;
      if (filters.id_location) params.id_location = filters.id_location;
      const [stockPayload, ledgerPayload, reconciliationPayload] = await Promise.all([
        getProductStock(productId),
        getInventoryMovements(productId, { ...params, per_page: 25 }),
        getInventoryReconciliation(productId),
      ]);
      setStock(stockPayload);
      setLedger(ledgerPayload);
      setReconciliation(reconciliationPayload);
    } catch (requestError) {
      showError(requestError);
    }
  }, [ledgerFilter]);

  async function pickProduct(productId) {
    setSelectedProduct(productId);
    setError(""); setNotice("");
    await refreshProduct(productId);
    const product = products.find((row) => String(row.id_product) === String(productId));
    const fallback = product?.id_location ? String(product.id_location) : "";
    setMovement((prev) => ({ ...prev, id_location: prev.id_location || fallback }));
    setTransfer((prev) => ({ ...prev, id_location_from: prev.id_location_from || fallback }));
  }

  async function pickWarehouse(locationId) {
    setSelectedWarehouse(locationId);
    setWarehouseContent(null);
    if (!locationId) return;
    try {
      setWarehouseContent(await getWarehouseStock(locationId));
    } catch (requestError) {
      showError(requestError);
    }
  }

  async function submitMovement(event) {
    event.preventDefault();
    if (!selectedProduct || busy) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const body = {
        movement_type: movement.movement_type,
        id_location: Number(movement.id_location) || undefined,
      };
      if (movement.movement_type === "adjustment") {
        body.quantity_delta = Number(movement.quantity);
      } else {
        body.quantity = Number(movement.quantity);
      }
      if (movement.reason.trim()) body.reason = movement.reason.trim();
      if (movement.reference_type) {
        body.reference_type = movement.reference_type;
        if (movement.reference_id.trim()) body.reference_id = movement.reference_id.trim();
      }
      const result = await createInventoryMovement(selectedProduct, body);
      setNotice(result.idempotent_replay ? "inventory.movement_replayed" : "inventory.movement_registered");
      setMovement((prev) => ({ ...prev, quantity: "1", reason: "", reference_id: "" }));
      await refreshProduct(selectedProduct);
      if (selectedWarehouse) await pickWarehouse(selectedWarehouse);
    } catch (requestError) {
      showError(requestError);
    } finally {
      setBusy(false);
    }
  }

  async function submitTransfer(event) {
    event.preventDefault();
    if (!selectedProduct || busy) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await createInventoryTransfer(selectedProduct, {
        id_location_from: Number(transfer.id_location_from),
        id_location_to: Number(transfer.id_location_to),
        quantity: Number(transfer.quantity),
        reason: transfer.reason.trim(),
      });
      setNotice(result.idempotent_replay ? "inventory.transfer_replayed" : "inventory.transfer_registered");
      setTransfer((prev) => ({ ...prev, quantity: "1", reason: "" }));
      await refreshProduct(selectedProduct);
      if (selectedWarehouse) await pickWarehouse(selectedWarehouse);
    } catch (requestError) {
      showError(requestError);
    } finally {
      setBusy(false);
    }
  }

  async function applyLedgerFilter(next) {
    setLedgerFilter(next);
    if (!selectedProduct) return;
    await refreshProduct(selectedProduct, next);
  }

  const movementNeedsReason = REASON_REQUIRED.has(movement.movement_type);
  const productLabel = (row) => row.descripcion || row.product_code || `#${row.id_product}`;
  const locationLabel = (node) => `${"  ".repeat(node.depth)}${node.is_warehouse ? "■ " : "└ "}${node.location_description}`;

  if (!permissionReady) return <main className="page"><p className="muted">{t("common.loading", "Cargando...")}</p></main>;
  if (!canRead) return <main className="page"><p className="error">{t("errors.permission_denied", "No tienes permiso para ver el inventario.")}</p></main>;

  return (
    <main className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow"><Warehouse size={14} /> {t("inventory.eyebrow", "Almacén")}</p>
          <h1>{t("inventory.title", "Inventario por almacén")}</h1>
          <p className="muted">{t("inventory.subtitle", "Existencia por ubicación, movimientos y traspasos entre almacenes.")}</p>
        </div>
        <button className="button" type="button" onClick={loadBase} disabled={loading}>
          <RefreshCw size={16} /> {t("common.refresh", "Actualizar")}
        </button>
      </header>

      {error && (
        <p className="error">
          {t(error, error)}
          {errorMeta?.available !== undefined && ` (${t("inventory.available", "disponible")}: ${errorMeta.available})`}
        </p>
      )}
      {notice && <p className="notice"><CheckCircle2 size={15} /> {t(notice, notice)}</p>}

      <section className="card">
        <h2><Warehouse size={17} /> {t("inventory.warehouses", "Almacenes y ubicaciones")}</h2>
        {warehouses.length === 0 && (
          <p className="muted">
            {t("inventory.no_warehouses", "No hay almacenes definidos. Marca un tipo de ubicación como almacén en Tipo de ubicación.")}
          </p>
        )}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t("inventory.location", "Ubicación")}</th>
                <th>{t("inventory.own_stock", "Propio")}</th>
                <th>{t("inventory.rolled_up", "Acumulado")}</th>
                <th>{t("common.actions", "Acciones")}</th>
              </tr>
            </thead>
            <tbody>
              {locations.map((node) => (
                <tr key={node.id_location} className={String(selectedWarehouse) === String(node.id_location) ? "is-selected" : ""}>
                  <td><pre className="cell-value">{locationLabel(node)}</pre></td>
                  <td>{node.quantity}</td>
                  <td><strong>{node.total_quantity}</strong></td>
                  <td>
                    <button className="button ghost" type="button" onClick={() => pickWarehouse(String(node.id_location))}>
                      {t("inventory.see_content", "Ver contenido")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {warehouseContent && (
        <section className="card">
          <h2><ClipboardList size={17} /> {warehouseContent.location_description} · {t("inventory.total", "total")}: {warehouseContent.total}</h2>
          <p className="muted">
            {t("inventory.locations_included", "Ubicaciones incluidas")}: {warehouseContent.locations_included}
          </p>
          {warehouseContent.items.length === 0 ? (
            <p className="muted">{t("inventory.warehouse_empty", "Sin existencia en este almacén.")}</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t("inventory.product", "Producto")}</th>
                    <th>{t("inventory.location", "Ubicación")}</th>
                    <th>{t("inventory.quantity", "Cantidad")}</th>
                  </tr>
                </thead>
                <tbody>
                  {warehouseContent.items.map((row) => (
                    <tr key={`${row.id_product}-${row.id_location}`}>
                      <td>{row.product_description || row.product_code || `#${row.id_product}`}</td>
                      <td>{row.location_description}</td>
                      <td><strong>{row.quantity}</strong></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      <section className="card">
        <h2><PackagePlus size={17} /> {t("inventory.product_movements", "Movimientos de un producto")}</h2>
        <label className="field">
          <span>{t("inventory.product", "Producto")}</span>
          <select value={selectedProduct} onChange={(event) => pickProduct(event.target.value)}>
            <option value="">{t("inventory.pick_product", "Elige un producto")}</option>
            {products.map((row) => (
              <option key={row.id_product} value={row.id_product}>{productLabel(row)}</option>
            ))}
          </select>
        </label>

        {stock && (
          <>
            <h3>{t("inventory.stock_by_location", "Existencia por ubicación")} · {t("inventory.total", "total")}: {stock.total}</h3>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t("inventory.warehouse", "Almacén")}</th>
                    <th>{t("inventory.location", "Ubicación")}</th>
                    <th>{t("inventory.quantity", "Cantidad")}</th>
                  </tr>
                </thead>
                <tbody>
                  {stock.items.length === 0 && (
                    <tr><td colSpan="3" className="muted">{t("inventory.no_stock", "Este producto no tiene existencia registrada.")}</td></tr>
                  )}
                  {stock.items.map((row) => (
                    <tr key={row.id_location}>
                      <td>{row.warehouse_description || <span className="muted">{t("inventory.no_warehouse", "sin almacén")}</span>}</td>
                      <td>{row.location_description}</td>
                      <td><strong>{row.quantity}</strong></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {reconciliation && (
          <p className={reconciliation.is_reconciled ? "notice" : "error"}>
            <Scale size={15} />{" "}
            {reconciliation.is_reconciled
              ? t("inventory.reconciled", "El libro, la existencia y el total del producto cuadran.")
              : t("inventory.not_reconciled", "Descuadre detectado entre el libro y la existencia.")}
            {" · "}{t("inventory.ledger", "libro")}: {reconciliation.ledger_balance}
            {" · "}{t("inventory.stock", "existencia")}: {reconciliation.stock_balance}
            {" · "}{t("inventory.movements", "movimientos")}: {reconciliation.movements}
          </p>
        )}

        {selectedProduct && canWrite && (
          <div className="form-grid-2">
            <form className="form-card" onSubmit={submitMovement}>
              <div className="form-header"><PackagePlus size={16} /><strong>{t("inventory.register_movement", "Registrar movimiento")}</strong></div>
              <label className="field">
                <span>{t("inventory.movement_type", "Tipo de movimiento")}</span>
                <select value={movement.movement_type} onChange={(event) => setMovement((prev) => ({ ...prev, movement_type: event.target.value }))}>
                  {MOVEMENT_TYPES.map((option) => (
                    <option key={option.value} value={option.value}>
                      {t(`inventory.movement_${option.value}`, option.value)} ({option.sign > 0 ? "+" : "−"})
                    </option>
                  ))}
                  {canAdjust && <option value="adjustment">{t("inventory.movement_adjustment", "Ajuste")} (±)</option>}
                </select>
              </label>
              {!canAdjust && (
                <p className="muted">
                  <AlertTriangle size={13} /> {t("inventory.adjust_not_allowed", "Los ajustes requieren permiso de jefe de almacén.")}
                </p>
              )}
              <label className="field">
                <span>{movement.movement_type === "adjustment" ? t("inventory.quantity_delta", "Diferencia (puede ser negativa)") : t("inventory.quantity", "Cantidad")}</span>
                <input type="number" step="1" value={movement.quantity} onChange={(event) => setMovement((prev) => ({ ...prev, quantity: event.target.value }))} required />
              </label>
              <label className="field">
                <span>{t("inventory.location", "Ubicación")}</span>
                <select value={movement.id_location} onChange={(event) => setMovement((prev) => ({ ...prev, id_location: event.target.value }))} required>
                  <option value="">{t("inventory.pick_location", "Elige la ubicación")}</option>
                  {locations.map((node) => (
                    <option key={node.id_location} value={node.id_location}>{node.location_description}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>
                  {t("inventory.reason", "Motivo")}
                  {movementNeedsReason && <strong> *</strong>}
                </span>
                <input value={movement.reason} onChange={(event) => setMovement((prev) => ({ ...prev, reason: event.target.value }))} required={movementNeedsReason} maxLength={250} />
              </label>
              <label className="field">
                <span>{t("inventory.reference", "Origen")}</span>
                <select value={movement.reference_type} onChange={(event) => setMovement((prev) => ({ ...prev, reference_type: event.target.value }))}>
                  <option value="">{t("inventory.no_reference", "Sin origen")}</option>
                  {REFERENCE_TYPES.map((value) => (
                    <option key={value} value={value}>{t(`inventory.reference_${value}`, value)}</option>
                  ))}
                </select>
              </label>
              {movement.reference_type && (
                <label className="field">
                  <span>{t("inventory.reference_id", "Documento")}</span>
                  <input value={movement.reference_id} onChange={(event) => setMovement((prev) => ({ ...prev, reference_id: event.target.value }))} maxLength={100} />
                </label>
              )}
              <div className="form-actions">
                <button className="button primary" type="submit" disabled={busy}>{t("inventory.register", "Registrar")}</button>
              </div>
            </form>

            <form className="form-card" onSubmit={submitTransfer}>
              <div className="form-header"><ArrowRightLeft size={16} /><strong>{t("inventory.transfer", "Traspaso entre almacenes")}</strong></div>
              <p className="muted">{t("inventory.transfer_help", "Saca de un lugar y mete en otro en una sola operación: o se mueven las dos puntas o ninguna.")}</p>
              <label className="field">
                <span>{t("inventory.from", "Origen")}</span>
                <select value={transfer.id_location_from} onChange={(event) => setTransfer((prev) => ({ ...prev, id_location_from: event.target.value }))} required>
                  <option value="">{t("inventory.pick_location", "Elige la ubicación")}</option>
                  {locations.map((node) => <option key={node.id_location} value={node.id_location}>{node.location_description}</option>)}
                </select>
              </label>
              <label className="field">
                <span>{t("inventory.to", "Destino")}</span>
                <select value={transfer.id_location_to} onChange={(event) => setTransfer((prev) => ({ ...prev, id_location_to: event.target.value }))} required>
                  <option value="">{t("inventory.pick_location", "Elige la ubicación")}</option>
                  {locations.map((node) => <option key={node.id_location} value={node.id_location}>{node.location_description}</option>)}
                </select>
              </label>
              <label className="field">
                <span>{t("inventory.quantity", "Cantidad")}</span>
                <input type="number" min="1" step="1" value={transfer.quantity} onChange={(event) => setTransfer((prev) => ({ ...prev, quantity: event.target.value }))} required />
              </label>
              <label className="field">
                <span>{t("inventory.reason", "Motivo")} <strong>*</strong></span>
                <input value={transfer.reason} onChange={(event) => setTransfer((prev) => ({ ...prev, reason: event.target.value }))} required maxLength={250} />
              </label>
              <div className="form-actions">
                <button className="button primary" type="submit" disabled={busy}>{t("inventory.transfer_action", "Traspasar")}</button>
              </div>
            </form>
          </div>
        )}

        {ledger && (
          <>
            <h3><ClipboardList size={16} /> {t("inventory.ledger_title", "Libro de movimientos")} ({ledger.total})</h3>
            <div className="filters">
              <label className="field">
                <span>{t("inventory.movement_type", "Tipo de movimiento")}</span>
                <select value={ledgerFilter.movement_type} onChange={(event) => applyLedgerFilter({ ...ledgerFilter, movement_type: event.target.value })}>
                  <option value="">{t("common.all", "Todos")}</option>
                  {[...MOVEMENT_TYPES.map((option) => option.value), "adjustment", "transfer"].map((value) => (
                    <option key={value} value={value}>{t(`inventory.movement_${value}`, value)}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>{t("inventory.location", "Ubicación")}</span>
                <select value={ledgerFilter.id_location} onChange={(event) => applyLedgerFilter({ ...ledgerFilter, id_location: event.target.value })}>
                  <option value="">{t("common.all", "Todas")}</option>
                  {locations.map((node) => <option key={node.id_location} value={node.id_location}>{node.location_description}</option>)}
                </select>
              </label>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t("inventory.movement_type", "Tipo")}</th>
                    <th>{t("inventory.change", "Cambio")}</th>
                    <th>{t("inventory.location", "Ubicación")}</th>
                    <th>{t("inventory.balance_at_location", "Saldo en la ubicación")}</th>
                    <th>{t("inventory.reference", "Origen")}</th>
                    <th>{t("inventory.reason", "Motivo")}</th>
                    <th>{t("inventory.date", "Fecha")}</th>
                  </tr>
                </thead>
                <tbody>
                  {ledger.items.length === 0 && (
                    <tr><td colSpan="7" className="muted">{t("inventory.no_movements", "Sin movimientos con estos filtros.")}</td></tr>
                  )}
                  {ledger.items.map((row) => (
                    <tr key={row.id_inventory_ledger}>
                      <td>{t(`inventory.movement_${row.movement_type}`, row.movement_type)}</td>
                      <td><strong>{row.quantity_delta > 0 ? `+${row.quantity_delta}` : row.quantity_delta}</strong></td>
                      <td>{row.id_location ?? "—"}</td>
                      <td>{row.location_balance_after ?? "—"}</td>
                      <td>{row.reference_type ? `${t(`inventory.reference_${row.reference_type}`, row.reference_type)}${row.reference_id ? ` / ${row.reference_id}` : ""}` : "—"}</td>
                      <td>{row.reason || "—"}</td>
                      <td>{row.creation_date ? row.creation_date.slice(0, 19).replace("T", " ") : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </main>
  );
}
