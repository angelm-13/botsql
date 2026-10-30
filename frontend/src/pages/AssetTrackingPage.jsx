import { useSearchParams } from "react-router-dom";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle, ArrowRightLeft, Ban, Check, ClipboardList, Hand,
  PackageOpen, Plus, RefreshCw, Search, Wrench, X,
} from "lucide-react";
import { useI18n } from "../i18n";
import "../styles/asset-tracking.css";
import PageHeader from "../components/PageHeader.jsx";
import { formatearFechaHora } from "../utils/fechas";
import {
  assignAsset, backAssetFromRepair, createAsset, getAssetByTag, getAssetHistory,
  getAssets, getOverdueAssets, lendAsset, moveAsset, reportAssetLost,
  retireAsset, returnAsset, sendAssetToRepair, getAllLocation, getAllProduct,
} from "../api";

// Los seis estados de una pieza, con el color que dice de un vistazo si hay que
// preocuparse. El orden es el del recorrido natural: de lista para usarse hasta
// dada de baja.
const ESTADOS = [
  { clave: "disponible", tono: "ok" },
  { clave: "en_uso", tono: "info" },
  { clave: "prestada", tono: "warn" },
  { clave: "en_reparacion", tono: "warn" },
  { clave: "extraviada", tono: "crit" },
  { clave: "retirada", tono: "muted" },
];

const TONO_POR_ESTADO = Object.fromEntries(ESTADOS.map((e) => [e.clave, e.tono]));

// Que se puede hacer desde cada estado. Es la misma tabla que el servidor tiene
// en `TRANSICIONES`, y se repite aqui a proposito: sin ella la pantalla ofrece
// botones que el servidor va a rechazar, y el usuario aprende a base de errores.
// El servidor sigue siendo el que decide.
const ACCIONES = {
  assign: { icono: Hand, desde: ["disponible", "en_uso"], pide: ["holder"] },
  lend: { icono: ArrowRightLeft, desde: ["disponible", "en_uso"], pide: ["holder", "due"] },
  return: { icono: PackageOpen, desde: ["prestada", "en_uso"], pide: ["location"] },
  "send-to-repair": { icono: Wrench, desde: ["disponible", "en_uso", "prestada"], pide: ["reason"] },
  "back-from-repair": { icono: Check, desde: ["en_reparacion"], pide: ["location"] },
  "report-lost": { icono: AlertTriangle, desde: ["disponible", "en_uso", "prestada", "en_reparacion"], pide: ["reason"], peligro: true },
  retire: { icono: Ban, desde: ["disponible", "en_uso", "en_reparacion", "extraviada"], pide: ["reason"], peligro: true },
  move: { icono: ArrowRightLeft, desde: ["disponible"], pide: ["location", "reason"] },
};

const LLAMADA = {
  assign: assignAsset,
  lend: lendAsset,
  return: returnAsset,
  "send-to-repair": sendAssetToRepair,
  "back-from-repair": backAssetFromRepair,
  "report-lost": reportAssetLost,
  retire: retireAsset,
  move: moveAsset,
};

const hoy = () => new Date().toISOString().slice(0, 10);
const enDias = (dias) =>
  new Date(Date.now() + dias * 86400000).toISOString().slice(0, 10);

export default function AssetTrackingPage() {
  const { t } = useI18n();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [filtros, setFiltros] = useState({ status: "", id_holder: "", id_location: "" });
  const [soloVencidos, setSoloVencidos] = useState(false);
  // La etiqueta puede llegar en la url. Localizar es la puerta de entrada del
  // almacen y desde cada pieza enlaza aqui: sin esto, quien llega tendria que
  // volver a escribir a mano la etiqueta que acababa de ver en pantalla.
  const [parametros] = useSearchParams();
  const [busqueda, setBusqueda] = useState(() => parametros.get("tag") || "");
  const [cargando, setCargando] = useState(false);
  const [errorKey, setErrorKey] = useState("");
  const [avisoKey, setAvisoKey] = useState("");

  const [detalle, setDetalle] = useState(null);
  const [accion, setAccion] = useState(null);
  const [formulario, setFormulario] = useState({});

  const [locations, setLocations] = useState([]);
  const [productos, setProductos] = useState([]);
  const [alta, setAlta] = useState(null);

  function reportar(error) {
    setErrorKey(error?.message || "errors.request_failed");
  }

  const cargar = useCallback(async () => {
    setCargando(true);
    setErrorKey("");
    try {
      const datos = soloVencidos
        ? await getOverdueAssets()
        : await getAssets({
            status: filtros.status || undefined,
            id_holder: filtros.id_holder || undefined,
            id_location: filtros.id_location || undefined,
            per_page: 100,
          });
      setItems(datos.items || []);
      setTotal(datos.total ?? (datos.items || []).length);
    } catch (error) {
      reportar(error);
    } finally {
      setCargando(false);
    }
  }, [filtros, soloVencidos]);

  useEffect(() => { cargar(); }, [cargar]);

  useEffect(() => {
    let vivo = true;
    Promise.all([
      getAllLocation({ per_page: 200 }).catch(() => ({ items: [] })),
      getAllProduct({ per_page: 200 }).catch(() => ({ items: [] })),
    ]).then(([ubicaciones, prods]) => {
      if (!vivo) return;
      setLocations(ubicaciones.items || []);
      setProductos(prods.items || []);
    });
    return () => { vivo = false; };
  }, []);

  // El recuento por estado que va arriba: es lo que se mira primero para saber
  // si algo anda mal antes de leer la tabla.
  const recuento = useMemo(() => {
    const base = Object.fromEntries(ESTADOS.map((e) => [e.clave, 0]));
    items.forEach((pieza) => {
      if (base[pieza.status] !== undefined) base[pieza.status] += 1;
    });
    return base;
  }, [items]);

  async function buscarPorEtiqueta(evento) {
    evento.preventDefault();
    const etiqueta = busqueda.trim();
    if (!etiqueta) return;
    setErrorKey("");
    try {
      // Se busca por la etiqueta pegada en la carcasa, que es el dato que se
      // tiene cuando se pregunta por una herramienta con ella en la mano.
      setDetalle(await getAssetByTag(etiqueta));
    } catch (error) {
      reportar(error);
    }
  }

  async function abrirDetalle(id) {
    setErrorKey("");
    try {
      setDetalle(await getAssetHistory(id));
    } catch (error) {
      reportar(error);
    }
  }

  function abrirAccion(pieza, nombre) {
    setAccion({ pieza, nombre });
    setFormulario({
      id_location: pieza.id_location || "",
      due_date: enDias(7),
      id_holder: "",
      reason: "",
    });
  }

  async function ejecutar(evento) {
    evento.preventDefault();
    const { pieza, nombre } = accion;
    const pide = ACCIONES[nombre].pide;
    const cuerpo = {};
    if (pide.includes("holder")) cuerpo.id_holder = formulario.id_holder;
    if (pide.includes("due")) cuerpo.due_date = formulario.due_date;
    if (pide.includes("location")) cuerpo.id_location = formulario.id_location;
    if (pide.includes("reason") || formulario.reason) cuerpo.reason = formulario.reason;

    setCargando(true);
    setErrorKey("");
    setAvisoKey("");
    try {
      await LLAMADA[nombre](pieza.id_inventory_asset, cuerpo);
      setAvisoKey(`assets.done_${nombre.replace(/-/g, "_")}`);
      setAccion(null);
      await cargar();
      if (detalle?.asset?.id_inventory_asset === pieza.id_inventory_asset) {
        await abrirDetalle(pieza.id_inventory_asset);
      }
    } catch (error) {
      reportar(error);
    } finally {
      setCargando(false);
    }
  }

  async function darDeAlta(evento) {
    evento.preventDefault();
    setCargando(true);
    setErrorKey("");
    try {
      await createAsset(alta);
      setAvisoKey("assets.done_register");
      setAlta(null);
      await cargar();
    } catch (error) {
      reportar(error);
    } finally {
      setCargando(false);
    }
  }

  const nombreUbicacion = (id) => {
    const fila = locations.find((l) => String(l.id_location) === String(id));
    return fila?.location_description || (id ? `#${id}` : "—");
  };

  return (
    <section className="page asset-page">
      <PageHeader
        eyebrow={t("assets.eyebrow", "Inventario")}
        titulo={t("assets.title", "Rastreo de piezas")}
        subtitulo={t(
              "assets.subtitle",
              "Herramienta, equipo y activos de uso: cada pieza con su estado, dónde está y quién responde por ella."
            )}
      >
        <div className="page-header-actions">
        <button className="button" onClick={cargar} disabled={cargando}>
        <RefreshCw size={16} />
        {cargando ? t("common.loading") : t("common.refresh")}
        </button>
        <button className="button primary" onClick={() => setAlta({ id_product: "", asset_tag: "", id_location: "" })}>
        <Plus size={16} />
        {t("assets.register", "Dar de alta pieza")}
        </button>
        </div>
      </PageHeader>

      {errorKey && <p className="error">{t(errorKey, errorKey)}</p>}
      {avisoKey && <p className="notice">{t(avisoKey, avisoKey)}</p>}

      {/* Lo primero que se ve: cuantas piezas hay en cada estado. Sin esto hay
          que leer la tabla entera para notar que algo falta. */}
      <div className="asset-tally">
        {ESTADOS.map(({ clave, tono }) => (
          <button
            key={clave}
            type="button"
            className={`asset-tally-card tono-${tono} ${filtros.status === clave ? "activa" : ""}`}
            onClick={() => {
              setSoloVencidos(false);
              setFiltros((f) => ({ ...f, status: f.status === clave ? "" : clave }));
            }}
          >
            <span className="asset-tally-count">{recuento[clave]}</span>
            <span className="asset-tally-label">{t(`assets.status_${clave}`, clave)}</span>
          </button>
        ))}
        <button
          type="button"
          className={`asset-tally-card tono-crit ${soloVencidos ? "activa" : ""}`}
          onClick={() => { setSoloVencidos((v) => !v); setFiltros({ status: "", id_holder: "", id_location: "" }); }}
        >
          <span className="asset-tally-count">
            {soloVencidos ? total : <AlertTriangle size={22} />}
          </span>
          <span className="asset-tally-label">{t("assets.overdue", "Préstamos vencidos")}</span>
        </button>
      </div>

      <div className="asset-toolbar">
        <form className="asset-search" onSubmit={buscarPorEtiqueta}>
          <Search size={16} />
          <input
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder={t("assets.search_by_tag", "Buscar por etiqueta (la pegada en la pieza)")}
            aria-label={t("assets.search_by_tag", "Buscar por etiqueta")}
          />
          <button className="button" type="submit">{t("common.search", "Buscar")}</button>
        </form>
        <select
          value={filtros.id_location}
          onChange={(e) => { setSoloVencidos(false); setFiltros((f) => ({ ...f, id_location: e.target.value })); }}
          aria-label={t("assets.filter_location", "Ubicación")}
        >
          <option value="">{t("assets.all_locations", "Todas las ubicaciones")}</option>
          {locations.map((l) => (
            <option key={l.id_location} value={l.id_location}>{l.location_description}</option>
          ))}
        </select>
        <input
          type="number"
          value={filtros.id_holder}
          onChange={(e) => { setSoloVencidos(false); setFiltros((f) => ({ ...f, id_holder: e.target.value })); }}
          placeholder={t("assets.filter_holder", "Responsable (id)")}
          aria-label={t("assets.filter_holder", "Responsable")}
        />
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{t("assets.tag", "Etiqueta")}</th>
              <th>{t("assets.status", "Estado")}</th>
              <th>{t("assets.location", "Ubicación")}</th>
              <th>{t("assets.holder", "Responsable")}</th>
              <th>{t("assets.due", "Regresa")}</th>
              <th>{t("common.actions", "Acciones")}</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td colSpan="6" className="muted">
                  {cargando
                    ? t("common.loading")
                    : t("assets.empty", "No hay piezas con esos filtros.")}
                </td>
              </tr>
            )}
            {items.map((pieza) => (
              <tr key={pieza.id_inventory_asset}>
                <td>
                  <button type="button" className="asset-tag" onClick={() => abrirDetalle(pieza.id_inventory_asset)}>
                    {pieza.asset_tag}
                  </button>
                  {pieza.serial_number && <p className="muted mono">{pieza.serial_number}</p>}
                </td>
                <td>
                  <span className={`asset-chip tono-${TONO_POR_ESTADO[pieza.status] || "muted"}`}>
                    {t(`assets.status_${pieza.status}`, pieza.status)}
                  </span>
                </td>
                <td>{nombreUbicacion(pieza.id_location)}</td>
                <td className="mono">{pieza.id_holder ?? "—"}</td>
                <td className={pieza.days_overdue ? "mono vencido" : "mono"}>
                  {pieza.due_date || "—"}
                  {pieza.days_overdue ? ` (+${pieza.days_overdue}d)` : ""}
                </td>
                <td className="row-actions">
                  {Object.entries(ACCIONES)
                    .filter(([, config]) => config.desde.includes(pieza.status))
                    .map(([nombre, config]) => {
                      const Icono = config.icono;
                      return (
                        <button
                          key={nombre}
                          type="button"
                          className={config.peligro ? "peligro" : undefined}
                          title={t(`assets.action_${nombre.replace(/-/g, "_")}`, nombre)}
                          onClick={() => abrirAccion(pieza, nombre)}
                        >
                          <Icono size={15} />
                        </button>
                      );
                    })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* --- historia de la pieza --- */}
      {detalle && (
        <div className="asset-drawer-backdrop" role="dialog" aria-modal="true">
          <div className="asset-drawer">
            <header>
              <div>
                <p className="eyebrow">{t("assets.history", "Historia de la pieza")}</p>
                <h2>{detalle.asset.asset_tag}</h2>
                <p className="muted">
                  <span className={`asset-chip tono-${TONO_POR_ESTADO[detalle.asset.status]}`}>
                    {t(`assets.status_${detalle.asset.status}`, detalle.asset.status)}
                  </span>
                  {" · "}
                  {nombreUbicacion(detalle.asset.id_location)}
                  {detalle.asset.id_holder ? ` · ${t("assets.holder", "Responsable")} ${detalle.asset.id_holder}` : ""}
                </p>
              </div>
              <button className="button ghost" onClick={() => setDetalle(null)} aria-label={t("common.close", "Cerrar")}>
                <X size={18} />
              </button>
            </header>

            <ol className="asset-timeline">
              {detalle.events.map((evento) => (
                <li key={evento.id_inventory_asset_event}>
                  <div className="asset-timeline-mark" aria-hidden="true" />
                  <div>
                    <p className="asset-timeline-title">
                      <strong>{t(`assets.event_${evento.event_type}`, evento.event_type)}</strong>
                      <span className="muted mono"> {formatearFechaHora(evento.creation_date || "", "es-MX")}</span>
                    </p>
                    <p className="muted">
                      {evento.status_before ? `${evento.status_before} → ` : ""}
                      {evento.status_after}
                      {evento.id_holder_after ? ` · ${t("assets.holder", "Responsable")} ${evento.id_holder_after}` : ""}
                      {evento.due_date ? ` · ${t("assets.due", "Regresa")} ${evento.due_date}` : ""}
                    </p>
                    {evento.reason && <p className="asset-timeline-reason">{evento.reason}</p>}
                    {evento.id_inventory_ledger && (
                      <p className="muted mono">
                        {t("assets.ledger_row", "Movimiento de almacén")} #{evento.id_inventory_ledger}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}

      {/* --- una accion sobre la pieza --- */}
      {accion && (
        <div className="asset-drawer-backdrop" role="dialog" aria-modal="true">
          <form className="asset-dialog" onSubmit={ejecutar}>
            <header>
              <h2>{t(`assets.action_${accion.nombre.replace(/-/g, "_")}`, accion.nombre)}</h2>
              <button type="button" className="button ghost" onClick={() => setAccion(null)}>
                <X size={16} />
              </button>
            </header>
            <p className="muted">{accion.pieza.asset_tag}</p>

            {ACCIONES[accion.nombre].pide.includes("holder") && (
              <div className="field">
                <label htmlFor="a-holder">{t("assets.holder", "Responsable")}</label>
                <input
                  id="a-holder" type="number" required
                  value={formulario.id_holder}
                  onChange={(e) => setFormulario((f) => ({ ...f, id_holder: e.target.value }))}
                />
              </div>
            )}
            {ACCIONES[accion.nombre].pide.includes("due") && (
              <div className="field">
                <label htmlFor="a-due">{t("assets.due", "Fecha de regreso")}</label>
                <input
                  id="a-due" type="date" required min={hoy()}
                  value={formulario.due_date}
                  onChange={(e) => setFormulario((f) => ({ ...f, due_date: e.target.value }))}
                />
                <p className="field-hint muted">
                  {t("assets.due_hint", "Un préstamo sin fecha nunca está vencido, así que nadie lo reclama.")}
                </p>
              </div>
            )}
            {ACCIONES[accion.nombre].pide.includes("location") && (
              <div className="field">
                <label htmlFor="a-loc">{t("assets.location", "Ubicación")}</label>
                <select
                  id="a-loc" required
                  value={formulario.id_location}
                  onChange={(e) => setFormulario((f) => ({ ...f, id_location: e.target.value }))}
                >
                  <option value="">{t("common.select", "Seleccionar")}</option>
                  {locations.map((l) => (
                    <option key={l.id_location} value={l.id_location}>{l.location_description}</option>
                  ))}
                </select>
              </div>
            )}
            <div className="field">
              <label htmlFor="a-reason">
                {t("assets.reason", "Motivo")}
                {ACCIONES[accion.nombre].pide.includes("reason") ? " *" : ""}
              </label>
              <input
                id="a-reason"
                required={ACCIONES[accion.nombre].pide.includes("reason")}
                value={formulario.reason}
                onChange={(e) => setFormulario((f) => ({ ...f, reason: e.target.value }))}
              />
            </div>

            <div className="form-actions">
              <button
                className={ACCIONES[accion.nombre].peligro ? "button danger" : "button primary"}
                type="submit"
                disabled={cargando}
              >
                {t("common.confirm", "Confirmar")}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* --- alta de una pieza --- */}
      {alta && (
        <div className="asset-drawer-backdrop" role="dialog" aria-modal="true">
          <form className="asset-dialog" onSubmit={darDeAlta}>
            <header>
              <h2>{t("assets.register", "Dar de alta pieza")}</h2>
              <button type="button" className="button ghost" onClick={() => setAlta(null)}>
                <X size={16} />
              </button>
            </header>
            <p className="muted">
              {t(
                "assets.register_hint",
                "Solo los productos marcados como serializados se rastrean pieza por pieza. Un insumo se lleva por cantidad."
              )}
            </p>

            <div className="field">
              <label htmlFor="n-product">{t("assets.product", "Producto")}</label>
              <select
                id="n-product" required
                value={alta.id_product}
                onChange={(e) => setAlta((a) => ({ ...a, id_product: e.target.value }))}
              >
                <option value="">{t("common.select", "Seleccionar")}</option>
                {productos
                  .filter((p) => p.tracking_mode === "serializado")
                  .map((p) => (
                    <option key={p.id_product} value={p.id_product}>
                      #{p.id_product} {p.descripcion || ""}
                    </option>
                  ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="n-tag">{t("assets.tag", "Etiqueta")}</label>
              <input
                id="n-tag" required maxLength={40}
                value={alta.asset_tag}
                onChange={(e) => setAlta((a) => ({ ...a, asset_tag: e.target.value }))}
                placeholder="A-014"
              />
              <p className="field-hint muted">
                {t("assets.tag_hint", "La que va pegada en la pieza. No se puede repetir.")}
              </p>
            </div>
            <div className="field">
              <label htmlFor="n-serial">{t("assets.serial", "Número de serie")}</label>
              <input
                id="n-serial" maxLength={120}
                value={alta.serial_number || ""}
                onChange={(e) => setAlta((a) => ({ ...a, serial_number: e.target.value }))}
              />
            </div>
            <div className="field">
              <label htmlFor="n-loc">{t("assets.location", "Ubicación")}</label>
              <select
                id="n-loc" required
                value={alta.id_location}
                onChange={(e) => setAlta((a) => ({ ...a, id_location: e.target.value }))}
              >
                <option value="">{t("common.select", "Seleccionar")}</option>
                {locations.map((l) => (
                  <option key={l.id_location} value={l.id_location}>{l.location_description}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="n-cost">{t("assets.cost", "Costo de adquisición")}</label>
              <input
                id="n-cost" type="number" step="0.01" min="0"
                value={alta.acquisition_cost || ""}
                onChange={(e) => setAlta((a) => ({ ...a, acquisition_cost: e.target.value }))}
              />
            </div>

            <div className="form-actions">
              <button className="button primary" type="submit" disabled={cargando}>
                <ClipboardList size={15} />
                {t("common.save", "Guardar")}
              </button>
            </div>
          </form>
        </div>
      )}
    </section>
  );
}
