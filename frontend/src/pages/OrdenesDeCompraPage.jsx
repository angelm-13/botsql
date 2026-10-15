import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Plus, RefreshCw } from "lucide-react";
import PageHeader from "../components/PageHeader.jsx";
import OrdenDeCompraDetalle from "../components/OrdenDeCompraDetalle.jsx";
import OrdenDeCompraEditor from "../components/OrdenDeCompraEditor.jsx";
import PoliticaDeCompra from "../components/PoliticaDeCompra.jsx";
import PresupuestosDeCompra from "../components/PresupuestosDeCompra.jsx";
import {
  getMyPermissions, getPurchaseOrder, getPurchaseOrders, getPurchasePolicy,
} from "../api";
import { dinero, estadoDeOrden } from "../utils/ordenDeCompra";
import { idAAbrir } from "../notifications/destino";
import { useI18n } from "../i18n";
import "../styles/ordenes-de-compra.css";

const FILTROS = [
  { clave: "", etiqueta: "Todas", estados: "" },
  { clave: "pending", etiqueta: "Por autorizar", estados: "pending_authorization" },
  { clave: "authorized", etiqueta: "Por comprar", estados: "authorized" },
  { clave: "bought", etiqueta: "Compradas", estados: "purchased,partially_received,received,closed" },
  { clave: "open", etiqueta: "Borradores", estados: "draft,rejected" },
  { clave: "cancelled", etiqueta: "Canceladas", estados: "cancelled" },
];

function actorGuardado() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch { return {}; }
}

function esPrivilegiado(actor) {
  return Boolean(actor.is_superuser || actor.is_bootstrap_admin || actor.username === "admin1");
}

function fechaCorta(iso) {
  if (!iso) return "";
  const d = new Date(iso.length <= 10 ? `${iso}T00:00:00` : iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("es-MX");
}

/**
 * Las ordenes de compra: de lo que falta por comprar a la compra hecha, con su
 * comprobante y quien dio cada paso.
 *
 * Lista a la izquierda y la orden abierta a la derecha. Compras arma y compra; quien
 * autoriza (Gerencia) aprueba o rechaza; el almacen solo mira lo que va a llegar. Los
 * botones los decide el servidor segun quien mira (`actions`), y cada accion se vuelve
 * a comprobar al ejecutarla.
 */
export default function OrdenesDeCompraPage() {
  const { t } = useI18n();
  const traducir = useRef(t);
  traducir.current = t;
  const navegar = useNavigate();
  const ubicacion = useLocation();
  const actor = useMemo(actorGuardado, []);
  const [permisos, setPermisos] = useState([]);
  const [lista, setLista] = useState({ items: [], total: 0 });
  const [filtro, setFiltro] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [orden, setOrden] = useState(null);
  const [modo, setModo] = useState("ver");
  const [precarga, setPrecarga] = useState([]);
  const [politica, setPolitica] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");

  const decirError = useCallback((e, porOmision) => setError(
    e?.payload?.error_key
      ? traducir.current(e.payload.error_key, porOmision)
      : traducir.current("errors.request_failed", porOmision)), []);

  const puede = (entidad, campo) => esPrivilegiado(actor)
    || Number(permisos.find((p) => p.entity_name === entidad)?.[campo] || 0) !== 0;

  const cargar = useCallback(async () => {
    setCargando(true);
    setError("");
    try {
      const estados = FILTROS.find((f) => f.clave === filtro)?.estados || "";
      setLista(await getPurchaseOrders({ status: estados || undefined, q: busqueda || undefined }));
    } catch (e) {
      decirError(e, "No se pudieron cargar las órdenes.");
    } finally {
      setCargando(false);
    }
  }, [filtro, busqueda, decirError]);

  useEffect(() => { cargar(); }, [cargar]);

  useEffect(() => {
    let vivo = true;
    getMyPermissions()
      .then((p) => { if (vivo) setPermisos(p?.entity_permissions || []); })
      .catch(() => { if (vivo) setPermisos([]); });
    getPurchasePolicy()
      .then((p) => { if (vivo) setPolitica(p); })
      .catch(() => { if (vivo) setPolitica(null); });
    return () => { vivo = false; };
  }, []);

  // Desde "Por comprar" se llega con las necesidades escogidas: se abre la orden nueva.
  useEffect(() => {
    const ids = ubicacion.state?.needIds;
    if (Array.isArray(ids) && ids.length > 0) {
      setPrecarga(ids.map(Number));
      setOrden(null);
      setModo("nueva");
      navegar(ubicacion.pathname, { replace: true, state: null });
    }
  }, [ubicacion.state, ubicacion.pathname, navegar]);

  async function abrir(id) {
    setError("");
    try {
      setOrden(await getPurchaseOrder(id));
      setModo("ver");
    } catch (e) {
      decirError(e, "No se pudo abrir la orden.");
    }
  }

  // Llegar desde una notificacion: `/ordenes-de-compra?abrir=<id>` abre esa orden.
  // Se consume una vez (el parametro se limpia para que recargar no la reabra). El
  // aviso de "no se pudo abrir" tiene su PROPIO estado: `cargar()` limpia `error` al
  // arrancar y, segun quien gane la carrera, borraria el mensaje antes de leerse.
  const [parametros, setParametros] = useSearchParams();
  const idPorAbrir = idAAbrir(parametros);
  const [noSeAbrio, setNoSeAbrio] = useState("");
  useEffect(() => {
    if (!idPorAbrir) return;
    setParametros({}, { replace: true });
    setNoSeAbrio("");
    (async () => {
      try {
        setOrden(await getPurchaseOrder(idPorAbrir));
        setModo("ver");
      } catch {
        // 403/404: el aviso apunta a una orden que ya no existe o que este usuario
        // no puede ver.
        setNoSeAbrio(traducir.current("errors.not_found", "No se encontró esa orden."));
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idPorAbrir]);

  // Una accion del detalle devuelve la orden ya cambiada: se pinta tal cual y se
  // refresca la lista, que es donde se ve el estado nuevo.
  function alCambiar(actualizada) {
    setOrden(actualizada);
    setModo("ver");
    cargar();
  }

  function alGuardar(guardada) {
    setPrecarga([]);
    alCambiar(guardada);
  }

  const items = lista.items || [];

  return (
    <section className="page ordenes-de-compra">
      <PageHeader
        eyebrow={t("order.eyebrow", "Compras")}
        titulo={t("order.title", "Órdenes de compra")}
        subtitulo={t("order.subtitle",
          "Cada compra con su proveedor, su comprobante y quién dio cada paso: pedirla, autorizarla, comprarla y recibirla.")}
      >
        <button type="button" className="button ghost" onClick={cargar} disabled={cargando}>
          <RefreshCw size={16} />
          {cargando ? t("common.loading", "Cargando…") : t("common.refresh", "Actualizar")}
        </button>
        {puede("purchase_order", "scope_create") && (
          <button type="button" className="button primary"
                  onClick={() => { setOrden(null); setPrecarga([]); setModo("nueva"); }}>
            <Plus size={16} /> {t("order.new_short", "Nueva orden")}
          </button>
        )}
      </PageHeader>

      <PoliticaDeCompra politica={politica} puedeEditar={puede("purchase_policy", "scope_update")}
                        onCambio={setPolitica} />
      <PresupuestosDeCompra puedeEditar={puede("purchase_policy", "scope_update")} />

      {error && <div className="alert error">{error}</div>}
      {noSeAbrio && <div className="alert error">{noSeAbrio}</div>}

      <div className="oc-layout">
        <aside className="oc-lista">
          <div className="oc-filtros" role="tablist">
            {FILTROS.map((f) => (
              <button key={f.clave} type="button" role="tab" aria-selected={filtro === f.clave}
                      className={`oc-filtro${filtro === f.clave ? " activo" : ""}`}
                      onClick={() => setFiltro(f.clave)}>
                {t(`order.filter_${f.clave || "all"}`, f.etiqueta)}
              </button>
            ))}
          </div>
          <input type="search" className="oc-busqueda" value={busqueda}
                 placeholder={t("order.search", "Buscar por folio, proveedor o factura")}
                 onChange={(e) => setBusqueda(e.target.value)} />

          {!cargando && items.length === 0 && (
            <div className="empty">
              <strong>{t("order.empty", "No hay órdenes con ese filtro.")}</strong>
            </div>
          )}

          <ul className="oc-ordenes">
            {items.map((o) => {
              const estado = estadoDeOrden(o.order_status);
              return (
                <li key={o.id_purchase_order}>
                  <button type="button"
                          className={`oc-orden${orden?.id_purchase_order === o.id_purchase_order ? " activa" : ""}`}
                          onClick={() => abrir(o.id_purchase_order)}>
                    <span className="oc-orden-linea">
                      <strong>{o.folio}</strong>
                      <span className={`oc-estado oc-estado-${estado.clase}`}>{estado.etiqueta}</span>
                    </span>
                    <span className="oc-orden-proveedor">{o.supplier_name}</span>
                    <span className="oc-orden-linea muted">
                      <span>
                        {o.projects_count > 0
                          ? `${o.projects_count} ${o.projects_count === 1 ? "proyecto" : "proyectos"}`
                          : `${o.lines_count} renglones`}
                      </span>
                      <span className="mono">{dinero(o.total_amount ?? o.authorized_total ?? o.quoted_total, o.currency)}</span>
                    </span>
                    <small className="muted">{fechaCorta(o.creation_date)} · {o.created_by_name || `#${o.created_by}`}</small>
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>

        <div className="oc-panel">
          {modo === "nueva" && (
            <OrdenDeCompraEditor precargar={precarga} onGuardada={alGuardar}
                                 onCancelar={() => { setModo("ver"); setPrecarga([]); }} />
          )}
          {modo === "editar" && orden && (
            <OrdenDeCompraEditor orden={orden} onGuardada={alGuardar} onCancelar={() => setModo("ver")} />
          )}
          {modo === "ver" && orden && (
            <OrdenDeCompraDetalle orden={orden} politica={politica} onCambio={alCambiar}
                                  onEditar={() => setModo("editar")} />
          )}
          {modo === "ver" && !orden && (
            <div className="empty">
              <strong>{t("order.pick_one", "Elige una orden para verla.")}</strong>
              <p className="muted">
                {t("order.pick_one_help", "O arma una nueva con lo que falta por comprar.")}
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
