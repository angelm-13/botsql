import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { RefreshCw, ShoppingCart } from "lucide-react";
import PageHeader from "../components/PageHeader.jsx";
import {
  confirmMaterialNeedBuy, getMaterialNeedsToBuy, getMyPermissions, linkMaterialNeed,
  returnMaterialNeed,
} from "../api";
import { estadoDeOrden } from "../utils/ordenDeCompra";
import { useI18n } from "../i18n";
import "../styles/material-necesario.css";

function actorGuardado() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch { return {}; }
}

function esPrivilegiado(actor) {
  return Boolean(actor.is_superuser || actor.is_bootstrap_admin || actor.username === "admin1");
}

function fechaCorta(iso) {
  if (!iso) return "";
  return new Date(`${iso}T00:00:00`).toLocaleDateString("es-MX");
}

// Cuantos dias faltan para la fecha (negativo = ya paso); null si no hay fecha.
function diasPara(iso) {
  if (!iso) return null;
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  const dia = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(dia.getTime())) return null;
  return Math.round((dia - hoy) / 86400000);
}

function etiquetaDeProyecto(p) {
  const folio = p.folio ? `#${p.folio}` : `#${p.id_proyect}`;
  return p.title ? `${folio} — ${p.title}` : folio;
}

/**
 * Lo que hace falta comprar: las necesidades de TODOS los proyectos, agrupadas.
 *
 * Lo que el supervisor vinculo al catalogo se compara con la existencia ("Hay" y
 * "Falta"). Lo que escribio con sus palabras NO se compara con nada: sale "Por
 * revisar", con lo que el catalogo sugiere, y alguien que conoce el almacen decide
 * con un clic si ya existe (se vincula) o si de verdad hay que comprarlo.
 *
 * Nunca se oculta algo por parecerse a una cosa del catalogo: buscar por texto no es
 * confiable, y el peor caso tiene que ser una revision de mas, no una compra de mas.
 */
export default function PorComprarPage() {
  const { t } = useI18n();
  // `t` cambia en cada render; como dependencia de `cargar` lo repetia sin parar.
  const traducir = useRef(t);
  traducir.current = t;
  const [respuesta, setRespuesta] = useState(null);
  const [soloFaltantes, setSoloFaltantes] = useState(true);
  const [cargando, setCargando] = useState(false);
  const [ocupado, setOcupado] = useState("");
  // Que grupo se esta devolviendo y con que motivo.
  const [devolviendo, setDevolviendo] = useState({ key: "", motivo: "" });
  const [error, setError] = useState("");
  const navegar = useNavigate();
  const actor = useMemo(actorGuardado, []);
  const [permisos, setPermisos] = useState([]);
  // Las necesidades escogidas para armar una orden de compra.
  const [seleccion, setSeleccion] = useState([]);

  const decirError = useCallback((e, porOmision) => setError(
    e?.payload?.error_key
      ? traducir.current(e.payload.error_key, porOmision)
      : traducir.current("errors.request_failed", porOmision)), []);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError("");
    try {
      setRespuesta(await getMaterialNeedsToBuy({ only_missing: soloFaltantes ? 1 : 0 }));
    } catch (e) {
      decirError(e, "No se pudo cargar la lista.");
    } finally {
      setCargando(false);
    }
  }, [soloFaltantes, decirError]);

  useEffect(() => { cargar(); }, [cargar]);

  useEffect(() => {
    let vivo = true;
    getMyPermissions()
      .then((p) => { if (vivo) setPermisos(p?.entity_permissions || []); })
      .catch(() => { if (vivo) setPermisos([]); });
    return () => { vivo = false; };
  }, []);

  const puedeArmarOrden = esPrivilegiado(actor)
    || Number(permisos.find((p) => p.entity_name === "purchase_order")?.scope_create || 0) !== 0;
  const alternar = (id) => setSeleccion(
    (s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  // Lo que ya esta en una orden no se vuelve a escoger; si se acaba de meter en una,
  // la seleccion vieja se limpia al recargar.
  const armarOrden = () => navegar("/ordenes-de-compra", { state: { needIds: seleccion } });

  // Un grupo puede juntar renglones de varios proyectos: la decision aplica a todos
  // los que siguen sin revisar.
  async function revisar(grupo, accion) {
    const pendientes = grupo.projects.filter((p) => p.needs_review);
    setOcupado(grupo.key);
    setError("");
    try {
      for (const p of pendientes) {
        // eslint-disable-next-line no-await-in-loop
        await accion(p.id_proyect_material_need);
      }
    } catch (e) {
      decirError(e, "No se pudo guardar la revisión.");
    } finally {
      setOcupado("");
      await cargar();
    }
  }

  const vincular = (grupo, sugerencia) => revisar(
    grupo, (idNeed) => linkMaterialNeed(idNeed, sugerencia.id_material));
  const confirmar = (grupo) => revisar(grupo, (idNeed) => confirmMaterialNeedBuy(idNeed));
  const devolver = async (grupo) => {
    const motivo = devolviendo.motivo.trim();
    if (motivo.length < 5) return;
    await revisar(grupo, (idNeed) => returnMaterialNeed(idNeed, motivo));
    setDevolviendo({ key: "", motivo: "" });
  };

  const items = respuesta?.items || [];
  const porRevisar = respuesta?.to_review || 0;
  const puedeRevisar = Boolean(respuesta?.can_review);
  // Lo que falta confirmar va aparte de lo que ya es compra: se trabajan distinto.
  const gruposPorRevisar = items.filter((g) => g.needs_review);
  const gruposPorComprar = items.filter((g) => !g.needs_review);
  // Lo que se puede meter en una orden: lo comprable que aun no esta en una.
  const seleccionables = puedeArmarOrden
    ? items.flatMap((g) => g.projects.filter((p) => p.purchasable && !p.order)
      .map((p) => p.id_proyect_material_need))
    : [];
  const todoSeleccionado = seleccionables.length > 0
    && seleccionables.every((id) => seleccion.includes(id));

  const filaDe = (g) => {
    const nombre = g.linked ? g.material?.material_description : g.description;
    const dias = g.missing > 0 || !g.linked ? diasPara(g.needed_by) : null;
    const urgencia = dias === null ? "" : dias < 0 ? "vencida" : dias <= 3 ? "proxima" : "";
    return (
      <Fragment key={g.key}>
        <tr className={[g.needs_review ? "por-comprar-revisar" : "", urgencia ? `por-comprar-${urgencia}` : ""].filter(Boolean).join(" ") || undefined}>
          <td>
            <strong>{nombre}</strong>
            {g.unit && <span className="muted"> · {g.unit}</span>}
            {g.linked && (
              <small className="muted por-comprar-origen">
                {t("purchase.in_catalog", "Del almacén")}
              </small>
            )}
            {!g.linked && (
              <span className={`necesidad-estado ${g.needs_review ? "revisar" : "compra"}`}>
                {g.needs_review
                  ? t("purchase.badge_review", "Por revisar")
                  : t("purchase.badge_buy", "Compra confirmada")}
              </span>
            )}
          </td>
          <td className="mono">{g.required}</td>
          <td className="mono">{g.linked ? g.in_stock : <span className="muted">—</span>}</td>
          <td className={`mono ${g.missing > 0 ? "por-comprar-falta" : "por-comprar-cubierto"}`}>
            {g.missing > 0 ? g.missing : t("purchase.covered", "cubierto")}
          </td>
          <td>
            {fechaCorta(g.needed_by) || <span className="muted">—</span>}
            {urgencia === "vencida" && (
              <span className="por-comprar-plazo vencida">
                {t("purchase.overdue", "Vencido hace")} {Math.abs(dias)} {Math.abs(dias) === 1 ? "día" : "días"}
              </span>
            )}
            {urgencia === "proxima" && (
              <span className="por-comprar-plazo proxima">
                {dias === 0 ? t("purchase.today", "Para hoy")
                  : `${t("purchase.in_days", "En")} ${dias} ${dias === 1 ? "día" : "días"}`}
              </span>
            )}
          </td>
          <td>
            <ul className="por-comprar-proyectos">
              {g.projects.map((p) => (
                <li key={p.id_proyect_material_need} className="por-comprar-chip">
                  <span>
                    {puedeArmarOrden && p.purchasable && !p.order && (
                      <input type="checkbox" className="por-comprar-casilla"
                             checked={seleccion.includes(p.id_proyect_material_need)}
                             onChange={() => alternar(p.id_proyect_material_need)}
                             aria-label={t("purchase.pick_for_order", "Incluir en una orden de compra")} />
                    )}
                    {etiquetaDeProyecto(p)}
                    {p.order && (
                      <span className={`oc-estado oc-estado-${estadoDeOrden(p.order.order_status).clase} por-comprar-en-orden`}
                            title={estadoDeOrden(p.order.order_status).etiqueta}>
                        {p.order.folio}
                      </span>
                    )}
                  </span>
                  <span className="mono por-comprar-cantidad">× {p.quantity}</span>
                </li>
              ))}
            </ul>
          </td>
        </tr>
        {g.needs_review && (
          <tr className="por-comprar-revision">
            <td colSpan={6}>
              {g.suggestions.length > 0 ? (
                <div className="por-comprar-sugerencias">
                  <p className="muted">
                    {t("purchase.maybe_exists", "El almacén tiene algo parecido. ¿Es lo mismo?")}
                  </p>
                  <ul>
                    {g.suggestions.map((s) => (
                      <li key={s.id_material}>
                        <span>
                          <strong>{s.material_description}</strong>
                          <small className="muted"> · {t("purchase.in_stock", "hay")} {s.in_stock}</small>
                        </span>
                        {puedeRevisar && (
                          <button type="button" className="button button-quiet"
                                  disabled={ocupado === g.key}
                                  onClick={() => vincular(g, s)}>
                            {t("purchase.already_in_warehouse", "Ya está en almacén")}
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="muted">
                  {t("purchase.nothing_similar", "El almacén no tiene nada con ese nombre. Puede existir con otro: revísalo antes de comprar.")}
                </p>
              )}
              {puedeRevisar && devolviendo.key !== g.key && (
                <div className="por-comprar-acciones">
                  <button type="button" className="button primary"
                          disabled={ocupado === g.key}
                          onClick={() => confirmar(g)}>
                    {t("purchase.confirm_buy", "Sí hay que comprarlo")}
                  </button>
                  <button type="button" className="button button-quiet"
                          disabled={ocupado === g.key}
                          onClick={() => setDevolviendo({ key: g.key, motivo: "" })}>
                    {t("purchase.return", "No se entiende: devolver")}
                  </button>
                </div>
              )}
              {puedeRevisar && devolviendo.key === g.key && (
                <div className="por-comprar-devolver">
                  <label>
                    <span>{t("purchase.return_why", "¿Qué tiene que corregir el supervisor?")}</span>
                    <input type="text" maxLength={300} autoFocus value={devolviendo.motivo}
                           placeholder={t("purchase.return_placeholder", "Ej. ¿Qué material es exactamente?")}
                           onChange={(e) => setDevolviendo({ key: g.key, motivo: e.target.value })} />
                  </label>
                  <button type="button" className="button primary"
                          disabled={ocupado === g.key || devolviendo.motivo.trim().length < 5}
                          onClick={() => devolver(g)}>
                    {t("purchase.return_send", "Devolver")}
                  </button>
                  <button type="button" className="button"
                          onClick={() => setDevolviendo({ key: "", motivo: "" })}>
                    {t("common.cancel", "Cancelar")}
                  </button>
                </div>
              )}
            </td>
          </tr>
        )}
      </Fragment>
    );
  };

  const tabla = (grupos) => (
    <div className="table-card">
      <table>
        <thead>
              <tr>
                <th>{t("purchase.col_material", "Qué")}</th>
                <th>{t("purchase.col_required", "Piden")}</th>
                <th>{t("purchase.col_stock", "Hay")}</th>
                <th>{t("purchase.col_missing", "Falta")}</th>
                <th>{t("purchase.col_needed_by", "Para cuándo")}</th>
                <th>{t("purchase.col_projects", "Proyectos")}</th>
              </tr>
            </thead>
        <tbody>
          {grupos.map(filaDe)}
        </tbody>
      </table>
    </div>
  );

  return (
    <section className="page por-comprar">
      <PageHeader
        eyebrow={t("purchase.eyebrow", "Compras")}
        titulo={t("purchase.title", "Por comprar")}
        subtitulo={t("purchase.subtitle",
          "Lo que piden los proyectos. Lo que se pide con texto libre sale por revisar hasta que alguien confirme si ya existe en el almacén o hay que comprarlo.")}
      >
        <button type="button" className="button ghost" onClick={cargar} disabled={cargando}>
          <RefreshCw size={16} />
          {cargando ? t("common.loading", "Cargando…") : t("common.refresh", "Actualizar")}
        </button>
      </PageHeader>

      <div className="por-comprar-barra">
        <label className="por-comprar-filtro">
          <input type="checkbox" checked={!soloFaltantes}
                 onChange={(e) => setSoloFaltantes(!e.target.checked)} />
          {t("purchase.show_covered", "Ver también lo que ya cubre el almacén")}
        </label>
        {porRevisar > 0 && (
          <span className="necesidad-estado revisar">
            {porRevisar} {t("purchase.to_review", "por revisar")}
          </span>
        )}
        {seleccionables.length > 0 && (
          <button type="button" className="button button-quiet"
                  onClick={() => setSeleccion(todoSeleccionado ? [] : seleccionables)}>
            {todoSeleccionado
              ? t("purchase.clear_all", "Quitar selección")
              : `${t("purchase.select_all", "Seleccionar todo lo comprable")} (${seleccionables.length})`}
          </button>
        )}
        {puedeArmarOrden && seleccion.length > 0 && (
          <button type="button" className="button primary" onClick={armarOrden}>
            <ShoppingCart size={16} />
            {t("purchase.make_order", "Armar orden de compra")} ({seleccion.length})
          </button>
        )}
      </div>

      {error && <div className="alert error">{error}</div>}

      {!cargando && !error && items.length === 0 && (
        <div className="empty">
          <strong>{soloFaltantes
            ? t("purchase.nothing_missing", "No falta nada por comprar.")
            : t("purchase.nothing_asked", "Ningún proyecto ha pedido nada.")}</strong>
        </div>
      )}

      {gruposPorRevisar.length > 0 && (
        <>
          <h3 className="por-comprar-seccion">
            {t("purchase.section_review", "Por revisar")} <span className="necesidad-estado revisar">{gruposPorRevisar.length}</span>
          </h3>
          <p className="muted por-comprar-seccion-ayuda">
            {t("purchase.section_review_help", "Texto libre que nadie ha confirmado: decide si ya existe en el almacén o hay que comprarlo.")}
          </p>
          {tabla(gruposPorRevisar)}
        </>
      )}

      {gruposPorComprar.length > 0 && (
        <>
          <h3 className="por-comprar-seccion">
            {t("purchase.section_buy", "Por comprar")} <span className="necesidad-estado compra">{gruposPorComprar.length}</span>
          </h3>
          {tabla(gruposPorComprar)}
        </>
      )}
    </section>
  );
}
