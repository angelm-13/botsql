import React, { useCallback, useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  AlertTriangle, Camera, Crosshair, History, ImageOff, MapPin, Package,
  RefreshCw, Search, Wrench,
} from "lucide-react";
import { Link } from "react-router-dom";
import { inventoryTrace, uploadProductImage, urlDeArchivo } from "../api";
import { useI18n } from "../i18n";
import "../styles/inventory-trace.css";

/**
 * Localizar cualquier cosa del almacen.
 *
 * Contesta la pregunta que se hace primero en un almacen y que hasta ahora
 * requeria cuatro consultas distintas: se escribe un texto y sale donde esta,
 * cuanto hay en cada sitio, que le ha pasado, y -si se rastrea pieza por
 * pieza- en que estado esta cada una y quien la tiene.
 *
 * Tres decisiones que se ven en la pantalla:
 *
 * * **Se busca tambien por etiqueta de pieza.** Es lo que esta pegado en la
 *   herramienta: quien la tiene en la mano lee ese numero, no el codigo del
 *   producto.
 * * **La foto se sube desde aqui.** Un almacen con cuatrocientos articulos
 *   parecidos se cuenta mal sin foto, y obligar a ir a la pantalla de Producto
 *   para ponerla significa que nadie la pone.
 * * **Lo que el alcance esconde se cuenta.** Si hay coincidencias de otro
 *   proyecto, se dice cuantas. Quien busca algo que existe y no lo ve merece
 *   saber que el filtro es el alcance y no que no exista.
 * * **Buscar una pieza y buscar el producto se contestan distinto.** Son dos
 *   preguntas: "donde esta el taladro TAL-001-C" y "cuantos taladros tengo y
 *   como estan". Antes se contestaban igual -salia el producto con sus tres
 *   piezas y sin decir cual era la que se pidio-, asi que quien tenia el numero
 *   en la mano tenia que buscarlo a ojo en la lista. Ahora el servidor dice por
 *   que salio cada resultado (`match_kind`) y cual pieza coincide, y la pantalla
 *   ensena la pieza pedida arriba con su bitacora, y las demas unidades debajo.
 */

const PROPOSITOS = [
  ["", "all_purposes", "Todo el almacén"],
  ["mercancia", "merchandise", "Mercancía"],
  ["uso_interno", "internal_use", "Uso interno"],
];

// Los estados de una pieza, con el tono con el que se pintan. `disponible` es
// el unico que cuenta como existencia; el resto explica por que no esta.
const TONO_DE_ESTADO = {
  disponible: "ok",
  en_uso: "info",
  prestada: "warn",
  en_reparacion: "warn",
  extraviada: "crit",
  retirada: "muted",
};

// Como se pinta cada tipo de movimiento del historial. Entradas en verde,
// salidas normales en gris, y en rojo lo que se perdio sin venderse: eso es lo
// que hay que mirar.
const TONO_DE_HISTORIA = {
  comprado: "ok", recibido: "ok", devuelto: "ok",
  vendido: "info", entregado: "muted", trasladado: "muted", ajustado: "muted",
  prestado: "warn",
  danado: "crit", destruido: "crit", extraviado: "crit", caducado: "crit",
};

/**
 * Una pieza: su etiqueta, su estado, quien la tiene y -si es la que se
 * busco- todo lo que le ha pasado.
 *
 * La bitacora solo se ensena de la pieza pedida. El servidor tampoco la manda
 * para las demas: desplegar la historia de treinta piezas para ver una es
 * ruido, y la historia del producto -que si sale siempre- ya contesta la
 * pregunta general.
 */
function Pieza({ pieza, destacada, t }) {
  return (
    <li className={destacada ? "trace-asset-hit" : undefined}>
      <div className="trace-asset-line">
        {destacada && <Crosshair size={13} className="trace-hit-icon" />}
        <span className="mono">{pieza.asset_tag}</span>
        <span className={`trace-chip ${TONO_DE_ESTADO[pieza.status] || "muted"}`}>
          {t(`assets.status_${pieza.status}`, pieza.status)}
        </span>
        {/* Quien la tiene solo aplica cuando esta fuera de su sitio; en
            `disponible` el responsable es nadie. */}
        {pieza.holder_name && <span className="trace-holder">{pieza.holder_name}</span>}
        {pieza.location_description && (
          <span className="muted">
            <MapPin size={12} /> {pieza.location_description}
          </span>
        )}
        {pieza.due_date && (
          <span className="muted">{t("trace.due", "regresa")} {pieza.due_date}</span>
        )}
        {/* Esta pantalla localiza; las acciones sobre la pieza -prestar,
            devolver, mandar a reparar, dar de baja- viven en su pantalla, que es
            donde estan sus transiciones de estado. Se enlaza en vez de
            repetirlas aqui: dos sitios que prestan la misma herramienta acaban
            discrepando. */}
        <Link className="trace-manage"
              to={`/assets?tag=${encodeURIComponent(pieza.asset_tag || "")}`}>
          {t("trace.manage_piece", "Gestionar")}
        </Link>
      </div>

      {destacada && pieza.timeline?.length > 0 && (
        <ol className="trace-timeline">
          {pieza.timeline.map((e) => (
            <li key={e.id_inventory_asset_event}>
              <span className="trace-when">
                {e.creation_date ? new Date(e.creation_date).toLocaleString("es-MX") : ""}
              </span>
              <span className="trace-what">
                {t(`trace.event_${e.event_type}`, e.etiqueta)}
                {(e.holder_after_name || e.holder_before_name) && (
                  <strong> {e.holder_after_name || e.holder_before_name}</strong>
                )}
                {e.location_after_description && (
                  <em> · {e.location_after_description}</em>
                )}
              </span>
              {e.reason && <span className="muted">{e.reason}</span>}
            </li>
          ))}
        </ol>
      )}
    </li>
  );
}


Pieza.propTypes = {
  pieza: PropTypes.shape({
    id_inventory_asset: PropTypes.number,
    asset_tag: PropTypes.string,
    status: PropTypes.string,
    holder_name: PropTypes.string,
    location_description: PropTypes.string,
    due_date: PropTypes.string,
    timeline: PropTypes.arrayOf(PropTypes.object),
  }).isRequired,
  destacada: PropTypes.bool,
  t: PropTypes.func.isRequired,
};


export default function InventoryTracePage() {
  const { t } = useI18n();
  const [consulta, setConsulta] = useState("");
  const [proposito, setProposito] = useState("");
  const [estadoFiltro, setEstadoFiltro] = useState("");
  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [subiendo, setSubiendo] = useState(null);
  // Fotos cuya ruta existe pero el archivo no. Pasa con datos de semilla y con
  // un archivo borrado a mano: el navegador ensena su icono de imagen rota, que
  // se lee como un fallo de la aplicacion. Se cae al marcador de "sin foto",
  // que es la verdad.
  const [fotosRotas, setFotosRotas] = useState(() => new Set());

  // `t` cambia de identidad en cada render; si entra en las dependencias del
  // efecto la pantalla se repide sin parar hasta que el navegador rechaza
  // peticiones. Se guarda en una referencia.
  const traducir = useRef(t);
  traducir.current = t;

  const buscar = useCallback(async (texto, fin) => {
    setCargando(true);
    setError("");
    try {
      setDatos(await inventoryTrace({ q: texto, stock_purpose: fin }));
    } catch (e) {
      setError(e?.payload?.error_key
        ? traducir.current(e.payload.error_key)
        : traducir.current("errors.request_failed", "No se pudo completar la búsqueda."));
    } finally {
      setCargando(false);
    }
  }, []);

  // Se espera a que deje de escribir: una peticion por tecla convierte una
  // busqueda de seis letras en seis consultas al almacen.
  useEffect(() => {
    const temporizador = setTimeout(() => buscar(consulta, proposito), 350);
    return () => clearTimeout(temporizador);
  }, [consulta, proposito, buscar]);

  const subirFoto = async (idProducto, archivo) => {
    if (!archivo) return;
    setSubiendo(idProducto);
    setError("");
    try {
      await uploadProductImage(idProducto, archivo);
      setFotosRotas((antes) => {
        const siguiente = new Set(antes);
        siguiente.delete(idProducto);
        return siguiente;
      });
      await buscar(consulta, proposito);
    } catch (e) {
      setError(e?.payload?.error_key
        ? traducir.current(e.payload.error_key)
        : traducir.current("errors.request_failed", "No se pudo subir la fotografía."));
    } finally {
      setSubiendo(null);
    }
  };

  const items = (datos?.items || []).filter((it) => {
    if (!estadoFiltro) return true;
    return (it.assets || []).some((a) => a.status === estadoFiltro);
  });

  return (
    <section className="page trace-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">{t("trace.eyebrow", "Almacén")}</p>
          <h1>{t("trace.title", "Localizar")}</h1>
          <p className="muted">
            {t("trace.subtitle",
              "Busca cualquier producto o herramienta y mira dónde está, qué le pasó y quién la tiene.")}
          </p>
        </div>
        <button className="button" onClick={() => buscar(consulta, proposito)} disabled={cargando}>
          <RefreshCw size={16} />
          {cargando ? t("common.loading", "Cargando…") : t("common.refresh", "Actualizar")}
        </button>
      </header>

      <div className="trace-toolbar">
        <div className="trace-search">
          <Search size={16} />
          <input
            value={consulta}
            onChange={(e) => setConsulta(e.target.value)}
            placeholder={t("trace.search_placeholder",
              "Nombre, código o etiqueta de la pieza (por ejemplo TAL-001)")}
            aria-label={t("trace.search_placeholder", "Buscar en el almacén")}
          />
        </div>
        <select value={proposito} onChange={(e) => setProposito(e.target.value)}
                aria-label={t("trace.purpose", "Para qué sirve")}>
          {PROPOSITOS.map(([valor, clave, texto]) => (
            <option key={valor} value={valor}>{t(`trace.${clave}`, texto)}</option>
          ))}
        </select>
        <select value={estadoFiltro} onChange={(e) => setEstadoFiltro(e.target.value)}
                aria-label={t("trace.by_status", "Por estado de la pieza")}>
          <option value="">{t("trace.any_status", "Cualquier estado")}</option>
          {Object.keys(TONO_DE_ESTADO).map((estado) => (
            <option key={estado} value={estado}>{t(`assets.status_${estado}`, estado)}</option>
          ))}
        </select>
      </div>

      {error && <p className="error">{error}</p>}

      {datos?.hidden_by_scope > 0 && (
        <p className="trace-warn">
          <AlertTriangle size={15} />
          {t("trace.hidden_by_scope",
            "Hay coincidencias en proyectos a los que no tienes acceso:")}{" "}
          <strong>{datos.hidden_by_scope}</strong>
        </p>
      )}

      {!cargando && items.length === 0 && (
        <p className="muted trace-empty">
          {consulta
            ? t("trace.nothing_found", "Nada coincide con esa búsqueda.")
            : t("trace.empty_warehouse", "El almacén no tiene productos registrados.")}
        </p>
      )}

      <div className="trace-list">
        {items.map((it) => {
          const historia = Object.entries(it.history || {})
            .sort((a, b) => b[1].unidades - a[1].unidades);
          const piezas = estadoFiltro
            ? (it.assets || []).filter((a) => a.status === estadoFiltro)
            : (it.assets || []);
          // La pieza que se pidio y las demas unidades del mismo producto. El
          // servidor ya las marca y las manda ordenadas; aqui solo se separan
          // para poder titularlas distinto.
          const pedidas = piezas.filter((a) => a.matched);
          const resto = piezas.filter((a) => !a.matched);
          const foto = fotosRotas.has(it.id_product) ? "" : urlDeArchivo(it.path_imagen);

          return (
            <article className="trace-card" key={it.id_product}>
              <div className="trace-photo">
                {foto ? (
                  <img
                    src={foto}
                    alt={it.descripcion || ""}
                    loading="lazy"
                    onError={() => setFotosRotas((antes) => {
                      const siguiente = new Set(antes);
                      siguiente.add(it.id_product);
                      return siguiente;
                    })}
                  />
                ) : (
                  <span className="trace-no-photo"><ImageOff size={22} /></span>
                )}
                <label className="trace-upload">
                  <Camera size={14} />
                  <span>
                    {subiendo === it.id_product
                      ? t("common.loading", "Subiendo…")
                      : foto
                        ? t("trace.replace_photo", "Cambiar")
                        : t("trace.add_photo", "Añadir foto")}
                  </span>
                  <input type="file" accept="image/*" disabled={subiendo === it.id_product}
                         onChange={(e) => subirFoto(it.id_product, e.target.files?.[0])} />
                </label>
              </div>

              <div className="trace-body">
                <header className="trace-head">
                  <div>
                    <h2>{it.descripcion || t("trace.unnamed", "Sin descripción")}</h2>
                    <p className="muted mono">
                      {it.product_code || `#${it.id_product}`}
                      {" · "}
                      {t(`trace.purpose_${it.stock_purpose}`, it.stock_purpose)}
                      {it.tracking_mode === "serializado" && (
                        <> · <Wrench size={12} /> {t("trace.serialized", "pieza por pieza")}</>
                      )}
                    </p>
                  </div>
                  <div className="trace-total">
                    <strong>{it.total}</strong>
                    <span>{t("trace.in_stock", "en existencia")}</span>
                    {/* Tres piezas de las que solo una sirve no es "tres" ni es
                        "una": la existencia cuenta lo utilizable y las unidades
                        cuentan lo que se tiene. Las dos hacen falta. */}
                    {it.unit_count > 0 && (
                      <em className="trace-units">
                        {it.available_units}/{it.unit_count}{" "}
                        {t("trace.usable_units", "unidades utilizables")}
                      </em>
                    )}
                  </div>
                </header>

                {/* Por que salio este resultado. Sin esto, buscar la
                    etiqueta de una pieza y buscar el codigo del producto dan la
                    misma pantalla, y no hay forma de saber si lo que se ve es la
                    pieza que se pidio o el inventario entero de ese modelo. */}
                {it.match_kind === "asset_tag" && it.matched_asset_tags?.length > 0 && (
                  <p className="trace-level trace-level-piece">
                    <Crosshair size={14} />
                    {t("trace.level_piece", "Buscaste una pieza:")}{" "}
                    <strong className="mono">{it.matched_asset_tags.join(", ")}</strong>
                  </p>
                )}
                {it.match_kind === "product_code" && it.unit_count > 0 && (
                  <p className="trace-level trace-level-product">
                    <Package size={14} />
                    {t("trace.level_product", "Buscaste el producto: se muestran sus")}{" "}
                    <strong>{it.unit_count}</strong>{" "}
                    {t("trace.level_product_units", "unidades")}
                  </p>
                )}

                <h3 className="trace-section">
                  <MapPin size={14} /> {t("trace.where", "Dónde está")}
                </h3>
                {it.locations.length === 0 ? (
                  <p className="muted">{t("trace.nowhere", "Sin existencia en ninguna ubicación.")}</p>
                ) : (
                  <ul className="trace-locations">
                    {it.locations.map((u) => (
                      <li key={u.id_location}>
                        <span>
                          {u.warehouse_description && u.warehouse_description !== u.location_description
                            ? `${u.warehouse_description} · ${u.location_description}`
                            : u.location_description}
                          {u.id_module && <em className="trace-module">{u.id_module}</em>}
                        </span>
                        <strong className="mono">{u.quantity}</strong>
                      </li>
                    ))}
                  </ul>
                )}

                <h3 className="trace-section">
                  <History size={14} />{" "}
                  {it.unit_count > 0
                    ? t("trace.what_happened_all", "Qué le ha pasado al producto (todas sus unidades)")
                    : t("trace.what_happened", "Qué le ha pasado")}
                </h3>
                {historia.length === 0 ? (
                  <p className="muted">{t("trace.no_history", "Sin movimientos registrados.")}</p>
                ) : (
                  <ul className="trace-history">
                    {historia.map(([clase, dato]) => (
                      <li key={clase} className={TONO_DE_HISTORIA[clase] || "muted"}>
                        <strong className="mono">{dato.unidades}</strong>
                        <span>{t(`trace.kind_${clase}`, clase)}</span>
                        <em>{dato.veces} {dato.veces === 1
                          ? t("trace.time", "vez") : t("trace.times", "veces")}</em>
                      </li>
                    ))}
                  </ul>
                )}

                {pedidas.length > 0 && (
                  <>
                    <h3 className="trace-section">
                      <Crosshair size={14} />{" "}
                      {pedidas.length === 1
                        ? t("trace.the_piece", "La pieza que buscas")
                        : t("trace.the_pieces", "Las piezas que buscas")}
                    </h3>
                    <ul className="trace-assets">
                      {pedidas.map((a) => (
                        <Pieza key={a.id_inventory_asset || a.asset_tag}
                               pieza={a} destacada t={t} />
                      ))}
                    </ul>
                  </>
                )}

                {resto.length > 0 && (
                  <>
                    <h3 className="trace-section">
                      <Wrench size={14} />{" "}
                      {pedidas.length > 0
                        ? t("trace.other_units", "Las otras unidades de este producto")
                        : t("trace.pieces", "Sus piezas")}
                      {" "}<span className="muted">({resto.length})</span>
                    </h3>
                    <ul className="trace-assets">
                      {resto.map((a) => (
                        <Pieza key={a.id_inventory_asset || a.asset_tag} pieza={a} t={t} />
                      ))}
                    </ul>
                  </>
                )}

                {it.last_movement && (
                  <p className="trace-last muted">
                    {t("trace.last_movement", "Último movimiento")}:{" "}
                    {t(`trace.kind_${it.last_movement.clasificacion}`, it.last_movement.clasificacion)}
                    {" "}({it.last_movement.quantity_delta}){" "}
                    {it.last_movement.reason && <>· {it.last_movement.reason} </>}
                    · {new Date(it.last_movement.creation_date).toLocaleString("es-MX")}
                  </p>
                )}
              </div>
            </article>
          );
        })}
      </div>

      {datos?.truncated && (
        <p className="muted trace-empty">
          {t("trace.truncated", "Se muestran los primeros resultados. Afina la búsqueda para ver el resto.")}
        </p>
      )}
    </section>
  );
}
