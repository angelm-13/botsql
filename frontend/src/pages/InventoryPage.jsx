import { useCallback, useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import {
  AlertTriangle, ArrowRight, ArrowRightLeft, Boxes, CheckCircle2, ChevronDown,
  ChevronRight, ClipboardList, PackagePlus, RefreshCw, Scale, Search, Warehouse,
} from "lucide-react";
import ProductLots from "../components/ProductLots.jsx";
import { useI18n } from "../i18n";
import "../styles/inventory-warehouses.css";
import PageHeader from "../components/PageHeader.jsx";
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

/**
 * La ruta completa de cada ubicacion, por identificador.
 *
 * "Rack A-1" no dice de que nave es, y con dos naves hay un Rack A-1 en cada
 * una: el desplegable de los formularios ofrecia esa descripcion suelta, asi
 * que elegir la ubicacion correcta era cuestion de saberse el almacen de
 * memoria. El arbol ya venia anidado del backend; aqui solo se recorre.
 */
function construirRutas(nodos, ancestros = [], mapa = new Map()) {
  for (const nodo of nodos || []) {
    const camino = [...ancestros, nodo.location_description];
    mapa.set(String(nodo.id_location), {
      nodo,
      camino,
      etiqueta: camino.join(" › "),
    });
    construirRutas(nodo.children, camino, mapa);
  }
  return mapa;
}

/** Cuanto hay del producto elegido en esa ubicacion, segun lo ya cargado. */
function existenciaEn(stock, idUbicacion) {
  if (!stock || !idUbicacion) return null;
  const fila = (stock.items || []).find(
    (x) => String(x.id_location) === String(idUbicacion));
  return fila ? Number(fila.quantity || 0) : 0;
}

/**
 * Una rama del arbol de ubicaciones.
 *
 * Antes esto era una tabla y la jerarquia se simulaba con espacios dentro de un
 * `<pre>`. Se leia con dos niveles; con cuatro, no, y no se podia plegar una
 * nave para ver las demas.
 *
 * La barra dice que parte del total del almacen esta en esta ubicacion. Es lo
 * que contesta "donde esta concentrado" sin hacer cuentas a mano, y es la
 * pregunta que se hace antes de ir a buscar algo.
 */
function RamaDeUbicacion({ nodo, nivel, elegida, plegados, onElegir, onPlegar,
                           totalDelAlmacen, filtro, t }) {
  const hijos = nodo.children || [];
  const plegado = plegados.has(String(nodo.id_location));
  const propio = Number(nodo.quantity || 0);
  const acumulado = Number(nodo.total_quantity || 0);
  const porcion = totalDelAlmacen > 0
    ? Math.round((acumulado / totalDelAlmacen) * 100) : 0;

  // Con filtro se muestra el nodo si el o alguno de sus descendientes coincide:
  // esconder al padre esconderia al hijo que se esta buscando.
  const coincide = (n) => {
    const texto = String(n.location_description || "").toLowerCase();
    if (texto.includes(filtro)) return true;
    return (n.children || []).some(coincide);
  };
  if (filtro && !coincide(nodo)) return null;

  return (
    <div>
      <button
        type="button"
        className={[
          "inv-nodo",
          nodo.is_warehouse ? "es-almacen" : "",
          String(elegida) === String(nodo.id_location) ? "elegida" : "",
          acumulado === 0 ? "vacia" : "",
        ].filter(Boolean).join(" ")}
        onClick={() => onElegir(String(nodo.id_location))}
      >
        <span
          className={`inv-plegar ${hijos.length ? "" : "sin-hijos"}`}
          role={hijos.length ? "button" : undefined}
          tabIndex={-1}
          onClick={(e) => { e.stopPropagation(); onPlegar(String(nodo.id_location)); }}
        >
          {hijos.length ? (plegado ? <ChevronRight size={14} /> : <ChevronDown size={14} />) : null}
        </span>

        <span className="inv-nombre">
          {nodo.is_warehouse ? <Warehouse size={14} /> : <Boxes size={13} />}
          <span title={nodo.location_description}>{nodo.location_description}</span>
          {nodo.location_type_description && (
            <em className="inv-tipo">{nodo.location_type_description}</em>
          )}
        </span>

        <span className="inv-cifras">
          <strong className="inv-acumulado">{acumulado}</strong>
          {/* Lo asentado justo aqui, cuando difiere de lo acumulado. Si son
              iguales el segundo numero no aporta y solo hace ruido. */}
          {hijos.length > 0 && propio !== acumulado && (
            <span className="inv-propio"
                  title={t("inventory.own_here", "asentado en esta ubicación")}>
              {propio} {t("inventory.own_short", "aquí")}
            </span>
          )}
        </span>

        <span className="inv-barra"
              title={`${porcion}% ${t("inventory.of_warehouse", "del almacén")}`}>
          <i style={{ width: `${porcion}%` }} />
        </span>
      </button>

      {hijos.length > 0 && !plegado && (
        <div className="inv-hijos">
          {hijos.map((hijo) => (
            <RamaDeUbicacion
              key={hijo.id_location}
              nodo={hijo}
              nivel={nivel + 1}
              elegida={elegida}
              plegados={plegados}
              onElegir={onElegir}
              onPlegar={onPlegar}
              totalDelAlmacen={totalDelAlmacen}
              filtro={filtro}
              t={t}
            />
          ))}
        </div>
      )}
    </div>
  );
}

RamaDeUbicacion.propTypes = {
  nodo: PropTypes.shape({
    id_location: PropTypes.number,
    location_description: PropTypes.string,
    location_type_description: PropTypes.string,
    is_warehouse: PropTypes.bool,
    quantity: PropTypes.number,
    total_quantity: PropTypes.number,
    children: PropTypes.array,
  }).isRequired,
  nivel: PropTypes.number.isRequired,
  elegida: PropTypes.any,
  plegados: PropTypes.instanceOf(Set).isRequired,
  onElegir: PropTypes.func.isRequired,
  onPlegar: PropTypes.func.isRequired,
  totalDelAlmacen: PropTypes.number.isRequired,
  filtro: PropTypes.string.isRequired,
  t: PropTypes.func.isRequired,
};


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
  // El lote que nombra una entrada. Solo se usa cuando el producto lleva lotes;
  // en los demas ni se pinta ni se manda.
  const [lote, setLote] = useState({ lot_code: "", expiry_date: "" });
  // Para volver a pedir el desglose despues de un movimiento, sin recargar la
  // pantalla entera.
  const [refrescoDeLotes, setRefrescoDeLotes] = useState(0);
  // Que ramas estan plegadas y el texto del buscador del arbol. Un almacen con
  // cuarenta baldas no se lee entero: se plega lo que no interesa o se busca.
  const [plegados, setPlegados] = useState(() => new Set());
  const [filtroUbicacion, setFiltroUbicacion] = useState("");
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
      // El lote solo en la entrada de un producto que los lleva. En la salida
      // no se manda: se sirve del que vence primero, que es el unico orden que
      // reduce la merma por caducidad.
      if (llevaLotes && esEntrada && lote.lot_code.trim()) {
        body.lot = {
          lot_code: lote.lot_code.trim(),
          expiry_date: lote.expiry_date || undefined,
        };
      }
      const result = await createInventoryMovement(selectedProduct, body);
      setNotice(result.idempotent_replay ? "inventory.movement_replayed" : "inventory.movement_registered");
      setMovement((prev) => ({ ...prev, quantity: "1", reason: "", reference_id: "" }));
      setLote({ lot_code: "", expiry_date: "" });
      setRefrescoDeLotes((n) => n + 1);
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

  // Si el producto elegido se lleva por lotes. Es lo unico que decide si el
  // formulario pide el lote: para todo lo demas la pantalla no cambia.
  const productoElegido = products.find(
    (row) => String(row.id_product) === String(selectedProduct));
  const llevaLotes = Boolean(productoElegido?.lot_control);
  const esEntrada = movement.movement_type !== "adjustment"
    && (MOVEMENT_TYPES.find((x) => x.value === movement.movement_type)?.sign || 0) > 0;

  // La ruta completa de cada ubicacion, para los desplegables de los dos
  // formularios: sin ella hay que saberse de memoria de que nave es cada rack.
  const rutas = useMemo(() => construirRutas(tree), [tree]);
  const rutaDe = (idUbicacion) => rutas.get(String(idUbicacion))?.etiqueta || "";
  // Ordenadas por su ruta: asi los racks de una nave salen juntos y detras de
  // ella, en vez de mezclados por orden de captura.
  const ubicacionesConRuta = useMemo(
    () => [...rutas.values()].sort((a, b) => a.etiqueta.localeCompare(b.etiqueta)),
    [rutas],
  );

  // La cuenta antes de mandar. Sin esto se teclea a ciegas y el servidor
  // contesta 409 con el saldo disponible, que es enterarse tarde.
  const signoElegido = MOVEMENT_TYPES.find(
    (x) => x.value === movement.movement_type)?.sign;
  const hayEnLaUbicacion = existenciaEn(stock, movement.id_location);
  const cantidadPedida = Number(movement.quantity) || 0;
  const saldoTrasMovimiento = hayEnLaUbicacion === null ? null : (
    movement.movement_type === "adjustment"
      ? hayEnLaUbicacion + cantidadPedida
      : hayEnLaUbicacion + (signoElegido || 0) * Math.abs(cantidadPedida)
  );

  const hayEnOrigen = existenciaEn(stock, transfer.id_location_from);
  const aTraspasar = Number(transfer.quantity) || 0;
  const traspasoNoAlcanza = hayEnOrigen !== null && aTraspasar > hayEnOrigen;

  const plegar = (id) => setPlegados((antes) => {
    const siguiente = new Set(antes);
    if (siguiente.has(id)) siguiente.delete(id); else siguiente.add(id);
    return siguiente;
  });
  const productLabel = (row) => row.descripcion || row.product_code || `#${row.id_product}`;

  if (!permissionReady) return <main className="page"><p className="muted">{t("common.loading", "Cargando...")}</p></main>;
  if (!canRead) return <main className="page"><p className="error">{t("errors.permission_denied", "No tienes permiso para ver el inventario.")}</p></main>;

  return (
    <main className="page">
      <PageHeader
        eyebrow={<><Warehouse size={14} /> {t("inventory.eyebrow", "Almacén")}</>}
        titulo={t("inventory.title", "Inventario por almacén")}
        subtitulo={t("inventory.subtitle", "Existencia por ubicación, movimientos y traspasos entre almacenes.")}
      >
        <button className="button" type="button" onClick={loadBase} disabled={loading}>
        <RefreshCw size={16} /> {t("common.refresh", "Actualizar")}
        </button>
      </PageHeader>

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

        {locations.length > 8 && (
          <div className="inv-buscador">
            <Search size={15} />
            <input
              value={filtroUbicacion}
              onChange={(event) => setFiltroUbicacion(event.target.value)}
              placeholder={t("inventory.filter_locations", "Busca una nave, un pasillo o un rack")}
              aria-label={t("inventory.filter_locations", "Buscar ubicación")}
            />
          </div>
        )}

        {/* El numero grande de cada renglon es lo acumulado -contando lo que
            cuelga debajo- y el pequeno es lo asentado justo ahi. Antes eran dos
            columnas rotuladas "Propio" y "Acumulado", y habia que volver a la
            cabecera cada vez para saber cual era cual. */}
        <div className="inv-arbol">
          {tree.map((raiz) => (
            <RamaDeUbicacion
              key={raiz.id_location}
              nodo={raiz}
              nivel={0}
              elegida={selectedWarehouse}
              plegados={plegados}
              onElegir={pickWarehouse}
              onPlegar={plegar}
              totalDelAlmacen={Number(raiz.total_quantity || 0)}
              filtro={filtroUbicacion.trim().toLowerCase()}
              t={t}
            />
          ))}
        </div>

        {/* El contenido va PEGADO al arbol y no en una tarjeta trescientos
            pixeles mas abajo: se elige un sitio justamente para ver lo que
            tiene, y tener que bajar rompe ese gesto. */}
        {warehouseContent && (
          <div className="inv-contenido">
            <h3>
              <ClipboardList size={16} />
              {rutaDe(selectedWarehouse) || warehouseContent.location_description}
              <em>
                {t("inventory.total", "total")}: {warehouseContent.total}
                {" · "}
                {warehouseContent.locations_included}{" "}
                {t("inventory.locations_included_short", "ubicaciones")}
              </em>
            </h3>
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
                        {/* Con la ruta: dentro de una nave grande, "Rack A-1" no
                            dice en que pasillo esta. */}
                        <td>{rutaDe(row.id_location) || row.location_description}</td>
                        <td><strong>{row.quantity}</strong></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </section>

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

        {selectedProduct && llevaLotes && (
          <ProductLots idProduct={selectedProduct} refrescar={refrescoDeLotes} />
        )}

        {selectedProduct && canWrite && (
          <div className="form-grid-2">
            <form className="form-card" onSubmit={submitMovement}>
              <div className="form-header">
                <PackagePlus size={16} />
                <strong>{t("inventory.register_movement", "Registrar movimiento")}</strong>
                {/* El signo, a la vista. Antes habia que deducirlo del nombre
                    del movimiento o del "(+)" pegado dentro del desplegable. */}
                {movement.movement_type === "adjustment" ? (
                  <span className="inv-signo ajuste">± {t("inventory.sign_adjust", "ajusta")}</span>
                ) : signoElegido > 0 ? (
                  <span className="inv-signo entra">+ {t("inventory.sign_in", "entra")}</span>
                ) : (
                  <span className="inv-signo sale">− {t("inventory.sign_out", "sale")}</span>
                )}
              </div>

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

              {/* La ubicacion con su ruta completa. Con dos naves hay un Rack
                  A-1 en cada una, y la descripcion suelta no dice de cual. */}
              <label className="field">
                <span>{t("inventory.location", "Ubicación")}</span>
                <select value={movement.id_location} onChange={(event) => setMovement((prev) => ({ ...prev, id_location: event.target.value }))} required>
                  <option value="">{t("inventory.pick_location", "Elige la ubicación")}</option>
                  {ubicacionesConRuta.map(({ nodo, etiqueta }) => (
                    <option key={nodo.id_location} value={nodo.id_location}>{etiqueta}</option>
                  ))}
                </select>
              </label>

              {/* El lote, solo en la entrada. En la salida no se pregunta:
                  se sirve del que vence primero, y elegirlo a mano es como se
                  desordena el anaquel -sale lo de enfrente, no lo que urge-. */}
              {llevaLotes && esEntrada && (
                <div className="inv-lote">
                  <label className="field">
                    <span>{t("inventory.lot_code", "Lote")} <strong>*</strong></span>
                    <input
                      value={lote.lot_code}
                      maxLength={60}
                      onChange={(event) => setLote({ ...lote, lot_code: event.target.value })}
                      placeholder={t("inventory.lot_code_placeholder",
                        "El que trae el proveedor")}
                      required
                    />
                  </label>
                  <label className="field">
                    <span>{t("inventory.expiry_date", "Caduca")}</span>
                    <input
                      type="date"
                      value={lote.expiry_date}
                      onChange={(event) => setLote({ ...lote, expiry_date: event.target.value })}
                    />
                  </label>
                  <p className="inv-ruta-ayuda">
                    {t("inventory.lot_why",
                      "Es el único momento en que se sabe: con la factura del proveedor delante. Después, un saldo sin lotes no dice cuándo caduca nada.")}
                  </p>
                </div>
              )}

              {llevaLotes && !esEntrada && movement.movement_type !== "adjustment" && (
                <p className="inv-ruta-ayuda inv-fefo">
                  <AlertTriangle size={13} />
                  {t("inventory.fefo_note",
                    "Se descuenta del lote que vence primero. No hay que elegirlo.")}
                </p>
              )}

              <label className="field">
                <span>{movement.movement_type === "adjustment" ? t("inventory.quantity_delta", "Diferencia (puede ser negativa)") : t("inventory.quantity", "Cantidad")}</span>
                <input type="number" step="1" value={movement.quantity} onChange={(event) => setMovement((prev) => ({ ...prev, quantity: event.target.value }))} required />
              </label>

              {/* La cuenta antes de mandar. Sin esto se teclea a ciegas y el
                  servidor contesta 409 con el saldo disponible: la cifra que
                  hacia falta ANTES, no despues. */}
              {hayEnLaUbicacion !== null && cantidadPedida !== 0 && (
                <p className={`inv-previa ${saldoTrasMovimiento < 0 ? "no-alcanza" : ""}`}>
                  {saldoTrasMovimiento < 0 && <AlertTriangle size={14} />}
                  <span>{t("inventory.there_are", "Hay")}</span>
                  <strong>{hayEnLaUbicacion}</strong>
                  <ArrowRight size={13} className="inv-flecha" />
                  <strong>{saldoTrasMovimiento}</strong>
                  <span>
                    {saldoTrasMovimiento < 0
                      ? t("inventory.not_enough", "— no alcanza, el almacén no puede quedar en negativo")
                      : t("inventory.after_movement", "tras el movimiento")}
                  </span>
                </p>
              )}

              <label className="field">
                <span>
                  {t("inventory.reason", "Motivo")}
                  {movementNeedsReason && <strong> *</strong>}
                </span>
                <input value={movement.reason} onChange={(event) => setMovement((prev) => ({ ...prev, reason: event.target.value }))} required={movementNeedsReason} maxLength={250} />
                {movementNeedsReason && (
                  <p className="inv-ruta-ayuda">
                    {t("inventory.reason_why",
                      "Este movimiento cambia la existencia sin un documento detrás: sin motivo, el descuadre no se puede auditar después.")}
                  </p>
                )}
              </label>

              {/* Decia "Origen", igual que el origen del traspaso, y son dos
                  cosas distintas: aquello es una ubicacion y esto el documento
                  que respalda el movimiento. */}
              <label className="field">
                <span>{t("inventory.reference", "Documento de respaldo")}</span>
                <select value={movement.reference_type} onChange={(event) => setMovement((prev) => ({ ...prev, reference_type: event.target.value }))}>
                  <option value="">{t("inventory.no_reference", "Sin documento")}</option>
                  {REFERENCE_TYPES.map((value) => (
                    <option key={value} value={value}>{t(`inventory.reference_${value}`, value)}</option>
                  ))}
                </select>
                <p className="inv-ruta-ayuda">
                  {t("inventory.reference_why",
                    "Decide cómo se cuenta después: una entrada con una compra detrás es «comprado»; sin documento es «recibido».")}
                </p>
              </label>
              {movement.reference_type && (
                <label className="field">
                  <span>{t("inventory.reference_id", "Folio del documento")}</span>
                  <input value={movement.reference_id} onChange={(event) => setMovement((prev) => ({ ...prev, reference_id: event.target.value }))} maxLength={100} />
                </label>
              )}
              <div className="form-actions">
                <button className="button primary" type="submit" disabled={busy}>{t("inventory.register", "Registrar")}</button>
              </div>
            </form>

            <form className="form-card" onSubmit={submitTransfer}>
              <div className="form-header"><ArrowRightLeft size={16} /><strong>{t("inventory.transfer", "Traspaso entre ubicaciones")}</strong></div>
              <p className="muted">{t("inventory.transfer_help", "Saca de un lugar y mete en otro en una sola operación: o se mueven las dos puntas o ninguna.")}</p>

              {/* Origen y destino uno al lado del otro, con la direccion a la
                  vista: es un movimiento con dos puntas y leerlo en dos campos
                  apilados no lo dice. */}
              <div className="inv-traspaso-caminos">
                <label className="field">
                  <span>{t("inventory.from", "Sale de")}</span>
                  <select value={transfer.id_location_from} onChange={(event) => setTransfer((prev) => ({ ...prev, id_location_from: event.target.value }))} required>
                    <option value="">{t("inventory.pick_location", "Elige la ubicación")}</option>
                    {ubicacionesConRuta.map(({ nodo, etiqueta }) => (
                      <option key={nodo.id_location} value={nodo.id_location}>{etiqueta}</option>
                    ))}
                  </select>
                </label>
                <span className="inv-traspaso-flecha"><ArrowRight size={20} /></span>
                <label className="field">
                  <span>{t("inventory.to", "Entra en")}</span>
                  {/* El origen no se ofrece como destino: el servidor lo rechaza
                      con `inventory_transfer_same_location`, y enterarse al
                      mandar es enterarse tarde. */}
                  <select value={transfer.id_location_to} onChange={(event) => setTransfer((prev) => ({ ...prev, id_location_to: event.target.value }))} required>
                    <option value="">{t("inventory.pick_location", "Elige la ubicación")}</option>
                    {ubicacionesConRuta
                      .filter(({ nodo }) => String(nodo.id_location) !== String(transfer.id_location_from))
                      .map(({ nodo, etiqueta }) => (
                        <option key={nodo.id_location} value={nodo.id_location}>{etiqueta}</option>
                      ))}
                  </select>
                </label>
              </div>

              <label className="field">
                <span>{t("inventory.quantity", "Cantidad")}</span>
                <input
                  type="number" min="1" step="1"
                  max={hayEnOrigen !== null && hayEnOrigen > 0 ? hayEnOrigen : undefined}
                  value={transfer.quantity}
                  onChange={(event) => setTransfer((prev) => ({ ...prev, quantity: event.target.value }))}
                  required
                />
              </label>

              {/* Las dos puntas, antes de mandar: cuanto queda en el origen y
                  cuanto habra en el destino. */}
              {hayEnOrigen !== null && aTraspasar > 0 && transfer.id_location_from && (
                <p className={`inv-previa ${traspasoNoAlcanza ? "no-alcanza" : ""}`}>
                  {traspasoNoAlcanza && <AlertTriangle size={14} />}
                  {traspasoNoAlcanza ? (
                    <span>
                      {t("inventory.only_there_are", "Solo hay")} <strong>{hayEnOrigen}</strong>{" "}
                      {t("inventory.in_origin", "en el origen")}
                    </span>
                  ) : (
                    <>
                      <span>{t("inventory.origin_short", "Origen")}</span>
                      <strong>{hayEnOrigen}</strong>
                      <ArrowRight size={13} className="inv-flecha" />
                      <strong>{hayEnOrigen - aTraspasar}</strong>
                      {transfer.id_location_to && (
                        <>
                          <span>{" · "}{t("inventory.destination_short", "Destino")}</span>
                          <strong>{existenciaEn(stock, transfer.id_location_to)}</strong>
                          <ArrowRight size={13} className="inv-flecha" />
                          <strong>{(existenciaEn(stock, transfer.id_location_to) || 0) + aTraspasar}</strong>
                        </>
                      )}
                    </>
                  )}
                </p>
              )}

              <label className="field">
                <span>{t("inventory.reason", "Motivo")} <strong>*</strong></span>
                <input value={transfer.reason} onChange={(event) => setTransfer((prev) => ({ ...prev, reason: event.target.value }))} required maxLength={250} />
              </label>
              <div className="form-actions">
                <button
                  className="button primary" type="submit"
                  disabled={busy || traspasoNoAlcanza
                    || !transfer.id_location_from || !transfer.id_location_to}
                >
                  {t("inventory.transfer_action", "Traspasar")}
                </button>
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
