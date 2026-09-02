import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertTriangle, Camera, ImageOff, MapPin, RefreshCw, Search, Wrench,
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
                  </div>
                </header>

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

                <h3 className="trace-section">{t("trace.what_happened", "Qué le ha pasado")}</h3>
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

                {piezas.length > 0 && (
                  <>
                    <h3 className="trace-section">
                      <Wrench size={14} /> {t("trace.pieces", "Sus piezas")}
                    </h3>
                    <ul className="trace-assets">
                      {piezas.map((a) => (
                        <li key={a.id_inventory_asset || a.asset_tag}>
                          <span className="mono">{a.asset_tag}</span>
                          <span className={`trace-chip ${TONO_DE_ESTADO[a.status] || "muted"}`}>
                            {t(`assets.status_${a.status}`, a.status)}
                          </span>
                          {/* Quien la tiene solo aplica cuando esta fuera de su
                              sitio; en `disponible` el responsable es nadie. */}
                          {a.holder_name && (
                            <span className="trace-holder">{a.holder_name}</span>
                          )}
                          {a.due_date && (
                            <span className="muted">
                              {t("trace.due", "regresa")} {a.due_date}
                            </span>
                          )}
                          {/* Esta pantalla localiza; las acciones sobre la pieza
                              -prestar, devolver, mandar a reparar, dar de baja-
                              viven en su pantalla, que es donde estan sus
                              transiciones de estado y su historial. Se enlaza en
                              vez de repetirlas aqui: dos sitios que prestan la
                              misma herramienta acaban discrepando. */}
                          <Link className="trace-manage"
                                to={`/assets?tag=${encodeURIComponent(a.asset_tag || "")}`}>
                            {t("trace.manage_piece", "Gestionar")}
                          </Link>
                        </li>
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
