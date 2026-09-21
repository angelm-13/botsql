import { useCallback, useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import {
  Boxes, ChevronDown, ChevronRight, ClipboardList, History, ImageOff, Package,
  RefreshCw, Search, Tag, Warehouse,
} from "lucide-react";
import { useI18n } from "../i18n";
import "../styles/inventory-warehouses.css";
import PageHeader from "../components/PageHeader.jsx";
import VisorDeFoto from "../components/VisorDeFoto";
import ProductHistory from "../components/ProductHistory.jsx";
import { getAllEntityPermission, getLocationTree, getWarehouseStock, urlDeArchivo } from "../api";

const ENTITY_KEY = "product";
const ACTION_READ = 2;

// El estatus tal como lo trae el sistema anterior en `product.product_status`
// (ENTRADA, SALIDA, DAÑADO, DESTRUCCIÓN, EXTRAVIADO...), con el mismo color
// por GRAVEDAD que ya usa Localizar (`InventoryTracePage.jsx`) y no un
// esquema propio: son siete etiquetas de texto, pero solo cinco preguntas
// reales -esta bien, esta fuera sin problema, hay que atenderlo, se perdio,
// se dio de baja-, y es esa pregunta la que importa de un vistazo.
const TONO_DE_ESTATUS = {
  ENTRADA: "ok",
  SALIDA: "info",
  RENTA: "info",
  DANADO: "warn",
  "EQ. DANADOS": "warn",
  REPARACION: "warn",
  EXTRAVIADO: "crit",
  DESTRUCCION: "muted",
};

function normalizarEstatus(valor) {
  return String(valor || "")
    .toUpperCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .trim();
}

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

  const [tree, setTree] = useState([]);
  const [selectedWarehouse, setSelectedWarehouse] = useState("");
  const [warehouseContent, setWarehouseContent] = useState(null);
  // Que ramas estan plegadas y el texto del buscador del arbol. Un almacen con
  // cuarenta baldas no se lee entero: se plega lo que no interesa o se busca.
  const [plegados, setPlegados] = useState(() => new Set());
  const [filtroUbicacion, setFiltroUbicacion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [errorMeta, setErrorMeta] = useState(null);
  // La foto que se esta mirando en grande, o null.
  const [fotoAmpliada, setFotoAmpliada] = useState(null);
  // Las fotos que fallaron al cargar: se recuerdan para no reintentar la
  // misma URL rota en cada render y caer al marcador en su lugar.
  const [fotosRotas, setFotosRotas] = useState(() => new Set());
  // El producto cuyo historial se esta mirando, o null.
  const [historialProducto, setHistorialProducto] = useState(null);

  const canRead = isSuperUser || Number(modulePermission?.scope_read || 0) !== 0;
  const locations = useMemo(() => flattenTree(tree), [tree]);
  const warehouses = useMemo(() => locations.filter((node) => node.is_warehouse), [locations]);

  // --- permisos -----------------------------------------------------------
  useEffect(() => {
    let alive = true;
    if (isSuperUser) {
      setModulePermission({ scope_create: 4, scope_read: 4, scope_update: 4, scope_delete: 4 });
      setPermissionReady(true);
      return () => { alive = false; };
    }
    getAllEntityPermission({ page: 1, per_page: 500 })
      .then((payload) => {
        if (!alive) return;
        const rows = normalizeList(payload).filter((row) => String(row.id_permission) === String(roleId));
        setModulePermission(rows.find((row) => row.entity_name === ENTITY_KEY) || null);
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
      const treePayload = await getLocationTree();
      setTree(treePayload?.items || []);
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

  // La ruta completa de cada ubicacion: sin ella hay que saberse de memoria de
  // que nave es cada rack.
  const rutas = useMemo(() => construirRutas(tree), [tree]);
  const rutaDe = (idUbicacion) => rutas.get(String(idUbicacion))?.etiqueta || "";
  const plegar = (id) => setPlegados((antes) => {
    const siguiente = new Set(antes);
    if (siguiente.has(id)) siguiente.delete(id); else siguiente.add(id);
    return siguiente;
  });

  if (!permissionReady) return <main className="page"><p className="muted">{t("common.loading", "Cargando...")}</p></main>;
  if (!canRead) return <main className="page"><p className="error">{t("errors.permission_denied", "No tienes permiso para ver el inventario.")}</p></main>;

  return (
    <main className="page">
      <PageHeader
        eyebrow={<><Warehouse size={14} /> {t("inventory.eyebrow", "Almacén")}</>}
        titulo={t("inventory.title", "Inventario por almacén")}
        subtitulo={t("inventory.subtitle", "Qué hay en cada nave, pasillo y rack. El material sale y vuelve por los vales.")}
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
              /* Antes esto era una tabla de puro texto -codigo, descripcion,
                 cantidad-: la misma cosa que ya se habia resuelto en
                 Localizar, pero sin resolver aqui. Con foto se reconoce el
                 material de un vistazo, sin tener que leer la descripcion
                 entera para saber si "DESARMADOR PLANO" es el de cruz o el
                 de plano. */
              <ul className="inv-existencia">
                {warehouseContent.items.map((row) => {
                  const clave = `${row.id_product}-${row.id_location}`;
                  const foto = fotosRotas.has(clave) ? "" : urlDeArchivo(row.path_imagen);
                  const nombre = row.product_description || row.product_code || `#${row.id_product}`;
                  const tono = row.product_status
                    ? TONO_DE_ESTATUS[normalizarEstatus(row.product_status)] : null;
                  // Familia › marca › material: lo que ya distingue Localizar
                  // entre "un desarmador" y "el desarmador TRUPER plano" sin
                  // tener que abrir la ficha completa del producto.
                  const clasificacion = [row.family, row.brand, row.material]
                    .filter(Boolean).join(" · ");
                  return (
                    <li key={clave}
                        className={`inv-existencia-item ${tono ? `tono-${tono}` : ""}`}>
                      <span className="inv-existencia-foto">
                        {foto ? (
                          <img
                            src={foto}
                            alt={nombre}
                            className="foto-ampliable"
                            loading="lazy"
                            title={t("photo.click_to_zoom", "Clic para verla en grande")}
                            onClick={() => setFotoAmpliada({
                              src: foto, titulo: nombre, descripcion: row.product_code || "",
                            })}
                            onError={() => setFotosRotas((antes) => new Set(antes).add(clave))}
                          />
                        ) : (
                          <ImageOff size={18} />
                        )}
                      </span>
                      <span className="inv-existencia-datos">
                        <strong>{nombre}</strong>
                        <span className="muted mono">
                          {row.product_code || `#${row.id_product}`}
                          {row.tracking_mode === "serializado" && (
                            <> · <Tag size={11} /> {t("voucher.serialized", "pieza por pieza")}</>
                          )}
                        </span>
                        {(clasificacion || row.color) && (
                          <span className="muted">
                            {clasificacion}
                            {row.color && <> {clasificacion ? "· " : ""}{row.color}</>}
                          </span>
                        )}
                        {/* Con la ruta: dentro de una nave grande, "Rack A-1"
                            no dice en que pasillo esta. */}
                        <span className="muted inv-existencia-ruta">
                          {rutaDe(row.id_location) || row.location_description}
                        </span>
                        {row.product_status && (
                          <span className={`inv-existencia-estatus tono-${tono || "muted"}`}>
                            {row.product_status}
                          </span>
                        )}
                      </span>
                      {/* El numero solo, con un icono, no decia de que era
                          numero: parecia una cajita sin etiqueta. Ahora dice
                          la palabra completa -unidades, o pieza cuando se
                          rastrea una por una- igual que ya hace Localizar
                          con "en existencia". */}
                      <span className="inv-existencia-cantidad">
                        <strong>{row.quantity}</strong>
                        <span>
                          {row.tracking_mode === "serializado"
                            ? <><Tag size={11} /> {t("voucher.piece", "pieza")}</>
                            : <><Package size={11} /> {t("voucher.units", "unidades")}</>}
                        </span>
                      </span>
                      {/* El historial, desde aqui y en una ventana -misma
                          idea que en Localizar-: la pregunta "y esto que ha
                          hecho" se hace sobre el renglon que se tiene
                          delante. */}
                      <button type="button" className="button button-quiet inv-existencia-historial"
                              onClick={() => setHistorialProducto(
                                { id_product: row.id_product, titulo: nombre })}>
                        <History size={14} />
                        {t("trace.open_history", "Historial")}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}
      </section>

      {fotoAmpliada && (
        <VisorDeFoto
          src={fotoAmpliada.src}
          titulo={fotoAmpliada.titulo}
          descripcion={fotoAmpliada.descripcion}
          onCerrar={() => setFotoAmpliada(null)}
        />
      )}

      {historialProducto && (
        <ProductHistory
          idProduct={historialProducto.id_product}
          titulo={historialProducto.titulo}
          onCerrar={() => setHistorialProducto(null)}
        />
      )}
    </main>
  );
}
