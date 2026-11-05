import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, Plus, RefreshCw } from "lucide-react";
import PageHeader from "../components/PageHeader.jsx";
import OrdenDeCompraDetalle from "../components/OrdenDeCompraDetalle.jsx";
import OrdenDeCompraEditor from "../components/OrdenDeCompraEditor.jsx";
import PoliticaDeCompra from "../components/PoliticaDeCompra.jsx";
import PresupuestosDeCompra from "../components/PresupuestosDeCompra.jsx";
import RentasActivas from "../components/RentasActivas.jsx";
import { AvisoFlotante, GuiaDelModulo } from "../components/GuiaDeCompras.jsx";
import {
  getMyPermissions, getPurchaseOrder, getPurchaseOrders, getPurchasePolicy,
} from "../api";
import { PASOS_DE_ORDEN, avisoTrasAccion, dinero, estadoDeOrden } from "../utils/ordenDeCompra";
import { idAAbrir } from "../notifications/destino";
import { useI18n } from "../i18n";
import "../styles/ordenes-de-compra.css";

const FILTROS = [
  { clave: "", etiqueta: "Todas", estados: "" },
  { clave: "pending", etiqueta: "Por autorizar", estados: "pending_authorization" },
  { clave: "authorized", etiqueta: "Por comprar", estados: "authorized" },
  { clave: "receiving", etiqueta: "Por recibir", estados: "purchased,partially_received" },
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

// Las tarjetas de arriba: cada una es un filtro y dice cuantas hay en esos estados.
const RESUMEN = [
  { clave: "pending", etiqueta: "Por autorizar", estados: ["pending_authorization"], tono: "alerta" },
  { clave: "authorized", etiqueta: "Por comprar", estados: ["authorized"], tono: "info" },
  { clave: "receiving", etiqueta: "Por recibir", estados: ["purchased", "partially_received"], tono: "ok" },
  { clave: "open", etiqueta: "Borradores", estados: ["draft", "rejected"], tono: "neutro" },
];

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

  // El aviso pequeño de "que paso y que sigue" tras cada accion (se va solo).
  const [avisoFlotante, setAvisoFlotante] = useState(null);
  const cerrarAviso = useCallback(() => setAvisoFlotante(null), []);

  // Una accion del detalle devuelve la orden ya cambiada: se pinta tal cual y se
  // refresca la lista, que es donde se ve el estado nuevo.
  function alCambiar(actualizada, accion) {
    setOrden(actualizada);
    setModo("ver");
    if (accion) setAvisoFlotante(avisoTrasAccion(accion, actualizada));
    setVersionRentas((v) => v + 1);
    cargar();
  }
  const [versionRentas, setVersionRentas] = useState(0);

  function alGuardar(guardada) {
    setPrecarga([]);
    alCambiar(guardada, "guardar");
  }

  // La guia de entrada se dice segun lo que el Gestor le da a quien mira: arma
  // ordenes (Compras), autoriza, recibe (almacen) o solo consulta.
  const tieneCapacidad = (entidad) => esPrivilegiado(actor) || permisos.some((p) => p.entity_name === entidad
    && ["scope_read", "scope_update", "scope_create"].some((c) => Number(p[c] || 0) !== 0));
  const puntosDeGuia = [
    puede("purchase_order", "scope_create")
      && t("guide.orders.buyer", "Tú armas la orden: desde Por comprar elige lo que vas a comprar, o usa \"Nueva orden\". Luego la envías a autorización, subes la factura y registras la compra."),
    tieneCapacidad("purchase_authorize")
      && t("guide.orders.authorizer", "Tú autorizas: abre las órdenes \"Por autorizar\", revisa monto y presupuesto, y autorízalas o recházalas con un motivo."),
    tieneCapacidad("purchase_receive")
      && t("guide.orders.receiver", "Tú recibes: cuando llegue el material, abre las órdenes \"Por recibir\" y anota cuánto llegó de cada renglón."),
    t("guide.orders.next", "Al abrir una orden, el recuadro \"Qué sigue\" te dice en qué paso va y qué te toca."),
    t("guide.orders.rental", "La maquinaria rentada no se recibe en el almacén: quien lleva la obra marca \"Llegó a obra\" y \"Devuelta al proveedor\". En \"Rentas de maquinaria\" ves lo que está en obra y cuándo vence."),
  ];

  const items = lista.items || [];
  const porEstado = lista.by_status || {};
  // Sin orden abierta la lista ocupa todo el ancho como tabla; al abrir una, pasa a
  // tarjetas a la izquierda para dejar sitio al detalle.
  const vistaTabla = modo === "ver" && !orden;

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

      <GuiaDelModulo id="ordenes-de-compra" titulo={t("guide.orders.title", "Así avanza una orden de compra")}
                     pasos={PASOS_DE_ORDEN} prefijo="order.step"
                     puntos={puntosDeGuia.filter(Boolean)} />
      <AvisoFlotante aviso={avisoFlotante} onCerrar={cerrarAviso} />

      <PoliticaDeCompra politica={politica} puedeEditar={puede("purchase_policy", "scope_update")}
                        onCambio={setPolitica} />
      <PresupuestosDeCompra puedeEditar={puede("purchase_policy", "scope_update")} />
      <RentasActivas version={versionRentas} onAbrirOrden={abrir}
                     onCambio={(actualizada) => {
                       // Si la orden que cambio esta abierta, se pinta la nueva; y la lista se refresca.
                       if (actualizada && orden?.id_purchase_order === actualizada.id_purchase_order) {
                         setOrden(actualizada);
                       }
                       cargar();
                     }} />

      {error && <div className="alert error">{error}</div>}
      {noSeAbrio && <div className="alert error">{noSeAbrio}</div>}

      <div className="oc-resumen">
        {RESUMEN.map((r) => {
          const cuantas = r.estados.reduce((suma, e) => suma + (porEstado[e] || 0), 0);
          return (
            <button key={r.clave} type="button"
                    className={`oc-resumen-tarjeta oc-tono-${r.tono}${filtro === r.clave ? " activa" : ""}${cuantas === 0 ? " vacia" : ""}`}
                    onClick={() => setFiltro(filtro === r.clave ? "" : r.clave)}>
              <strong>{cuantas}</strong>
              <span>{t(`order.filter_${r.clave}`, r.etiqueta)}</span>
            </button>
          );
        })}
      </div>

      <div className={`oc-layout${vistaTabla ? " oc-layout-tabla" : ""}`}>
        <aside className="oc-lista">
          {!vistaTabla && (
            <button type="button" className="button ghost oc-todas"
                    onClick={() => { setOrden(null); setModo("ver"); setPrecarga([]); }}>
              <ArrowLeft size={14} /> {t("order.all_orders", "Todas las órdenes")}
            </button>
          )}
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
              <strong>{filtro
                ? t("order.empty", "No hay órdenes con ese filtro.")
                : t("order.empty_all", "Todavía no hay órdenes de compra.")}</strong>
              {!filtro && (
                <p className="muted">{puede("purchase_order", "scope_create")
                  ? t("order.empty_all_buyer", "Empieza en Por comprar: elige lo que piden los proyectos y arma la orden, o usa \"Nueva orden\".")
                  : t("order.empty_all_reader", "Las órdenes las arma Compras con lo que piden los proyectos.")}</p>
              )}
            </div>
          )}

          {vistaTabla && items.length > 0 && (
            <div className="table-card">
              <div className="table-wrap">
                <table className="oc-tabla-lista">
                  <thead>
                    <tr>
                      <th>{t("order.col_folio", "Folio")}</th>
                      <th>{t("order.col_supplier", "Proveedor")}</th>
                      <th>{t("order.col_projects", "Proyectos")}</th>
                      <th className="num">{t("order.col_total", "Total")}</th>
                      <th>{t("order.col_created", "Creada")}</th>
                      <th>{t("order.col_status", "Estado")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((o) => {
                      const estado = estadoDeOrden(o.order_status);
                      return (
                        <tr key={o.id_purchase_order} tabIndex={0} className="oc-fila"
                            onClick={() => abrir(o.id_purchase_order)}
                            onKeyDown={(e) => { if (e.key === "Enter") abrir(o.id_purchase_order); }}>
                          <td><strong>{o.folio}</strong></td>
                          <td>{o.supplier_name}</td>
                          <td>
                            {o.projects_count > 0
                              ? `${o.projects_count} ${o.projects_count === 1 ? "proyecto" : "proyectos"}`
                              : `${o.lines_count} renglones`}
                          </td>
                          <td className="num mono">{dinero(o.total_amount ?? o.authorized_total ?? o.quoted_total, o.currency)}</td>
                          <td>
                            {fechaCorta(o.creation_date)}
                            <small className="muted oc-creador">{o.created_by_name || `#${o.created_by}`}</small>
                          </td>
                          <td><span className={`oc-estado oc-estado-${estado.clase}`}>{estado.etiqueta}</span></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <ul className="oc-ordenes" hidden={vistaTabla}>
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

        {!vistaTabla && <div className="oc-panel">
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
        </div>}
      </div>
    </section>
  );
}
