import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import { useNavigate } from "react-router-dom";
import { PackageOpen, Plus, X } from "lucide-react";
import {
  cancelMaterialNeed, createProyectMaterialNeed, getMaterialNeedSuggestions,
  getMyPermissions, getProyectMaterialNeeds, updateMaterialNeed,
} from "../api";
import { CANTIDAD_MAXIMA, UNIDADES, descripcionSospechosa } from "../utils/descripcionDeNecesidad";
import { useI18n } from "../i18n";
import "../styles/material-necesario.css";

// Un proyecto cerrado ya no compra: la lista se ve, pero no se toca.
const ESTATUS_CERRADOS = ["denied", "completed", "delivered"];

function actorGuardado() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch { return {}; }
}

function esPrivilegiado(actor) {
  return Boolean(actor.is_superuser || actor.is_bootstrap_admin || actor.username === "admin1");
}

const FORMULARIO_VACIO = {
  description: "", id_material: "", material_label: "",
  quantity: "1", unit: "", needed_by: "", note: "",
};
const SIN_SUGERENCIAS = { materials: [], previous: [] };

/**
 * Lo que el proyecto necesita, en el detalle del proyecto.
 *
 * Texto libre primero: el catalogo de este almacen es de herramienta y equipo, y lo
 * que una obra consume -tornillos, soldadura, discos- casi nunca esta ahi. Mientras
 * el supervisor escribe se le sugiere lo que el catalogo parece tener y lo que otros
 * ya pidieron y alguien confirmo; si elige una del catalogo el renglon queda
 * vinculado (y se compara con la existencia), y si no, queda como texto y alguien que
 * conoce el almacen lo revisa en "Por comprar".
 *
 * Se puede pedir MAS de lo que hay: la lista sirve justo para avisar el faltante, a
 * diferencia del prevale, que es recoger herramienta y no pasa de la existencia.
 */
export default function MaterialNecesario({ idProyect, estatus }) {
  const { t } = useI18n();
  // `t` cambia de identidad en cada render: como dependencia de `cargar` lo
  // volvia a llamar sin parar (200 peticiones en segundos). Se lee por referencia.
  const traducir = useRef(t);
  traducir.current = t;
  const navegar = useNavigate();
  const actor = useMemo(actorGuardado, []);
  const [items, setItems] = useState([]);
  const [permisos, setPermisos] = useState([]);
  const [formulario, setFormulario] = useState(FORMULARIO_VACIO);
  const [sugerencias, setSugerencias] = useState(SIN_SUGERENCIAS);
  const [correccion, setCorreccion] = useState({});
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const peticion = useRef(0);

  const decirError = useCallback((e, porOmision) => setError(
    e?.payload?.error_key
      ? traducir.current(e.payload.error_key, porOmision)
      : traducir.current("errors.request_failed", porOmision)), []);

  const puede = (campo) => esPrivilegiado(actor)
    || Number(permisos.find((p) => p.entity_name === "proyect_material_need")?.[campo] || 0) !== 0;
  const puedePedirEnAlmacen = esPrivilegiado(actor) || ["warehouse_prevoucher", "warehouse_voucher"]
    .some((k) => Number(permisos.find((p) => p.entity_name === k)?.scope_create || 0) !== 0);
  const cerrado = ESTATUS_CERRADOS.includes(String(estatus || ""));
  const puedeCrear = puede("scope_create") && !cerrado;
  const puedeEditar = puede("scope_update") && !cerrado;

  const cargar = useCallback(async () => {
    setCargando(true);
    setError("");
    try {
      const respuesta = await getProyectMaterialNeeds(idProyect);
      setItems(respuesta?.items || []);
    } catch (e) {
      decirError(e, "No se pudo cargar el material necesario.");
    } finally {
      setCargando(false);
    }
  }, [idProyect, decirError]);

  useEffect(() => { cargar(); }, [cargar]);

  useEffect(() => {
    let vivo = true;
    getMyPermissions()
      .then((p) => { if (vivo) setPermisos(p?.entity_permissions || []); })
      .catch(() => { if (vivo) setPermisos([]); });
    return () => { vivo = false; };
  }, []);

  // Las sugerencias salen de lo que se va escribiendo, con una pausa para no
  // preguntar por cada tecla. Una respuesta tardia de un texto anterior se descarta.
  useEffect(() => {
    const texto = formulario.description.trim();
    if (!puedeCrear || formulario.id_material || texto.length < 3) {
      setSugerencias(SIN_SUGERENCIAS);
      return undefined;
    }
    const numero = ++peticion.current;
    const temporizador = setTimeout(async () => {
      try {
        const r = await getMaterialNeedSuggestions(texto);
        if (numero === peticion.current) {
          setSugerencias({ materials: r?.materials || [], previous: r?.previous || [] });
        }
      } catch {
        if (numero === peticion.current) setSugerencias(SIN_SUGERENCIAS);
      }
    }, 300);
    return () => clearTimeout(temporizador);
  }, [formulario.description, formulario.id_material, puedeCrear]);

  const cambiar = (campo) => (e) => setFormulario((f) => ({ ...f, [campo]: e.target.value }));

  function elegirDelCatalogo(s) {
    setFormulario((f) => ({
      ...f, id_material: s.id_material, material_label: s.material_description, unit: "",
    }));
    setSugerencias(SIN_SUGERENCIAS);
  }

  // Lo que ya se pidio y alguien confirmo: se usa el texto tal cual, para que lo mismo
  // se escriba igual en todos los proyectos.
  function elegirYaPedido(p) {
    setFormulario((f) => ({
      ...f, description: p.description, unit: UNIDADES.includes(p.unit) ? p.unit : f.unit,
    }));
    setSugerencias(SIN_SUGERENCIAS);
  }

  const quitarVinculo = () => setFormulario((f) => ({ ...f, id_material: "", material_label: "" }));

  // Aviso al instante de lo evidente; el servidor lo vuelve a comprobar.
  const textoEscrito = formulario.description.trim();
  const motivoSospechoso = !formulario.id_material && textoEscrito.length >= 3
    ? descripcionSospechosa(textoEscrito) : null;
  const cantidadValida = Number(formulario.quantity) >= 1 && Number(formulario.quantity) <= CANTIDAD_MAXIMA;
  const listoParaAgregar = (formulario.id_material || (textoEscrito && !motivoSospechoso))
    && cantidadValida;

  async function agregar(evento) {
    evento.preventDefault();
    if (!listoParaAgregar || guardando) return;
    setGuardando(true);
    setError("");
    try {
      const datos = {
        quantity: Number(formulario.quantity),
        needed_by: formulario.needed_by || undefined,
        note: formulario.note.trim() || undefined,
      };
      if (formulario.id_material) {
        datos.id_material = Number(formulario.id_material);
      } else {
        datos.description = textoEscrito;
        datos.unit = formulario.unit || undefined;
      }
      await createProyectMaterialNeed(idProyect, datos);
      setFormulario(FORMULARIO_VACIO);
      await cargar();
    } catch (e) {
      decirError(e, "No se pudo agregar a la lista.");
    } finally {
      setGuardando(false);
    }
  }

  async function cambiarCantidad(renglon, valor) {
    const cantidad = Number(valor);
    if (!Number.isInteger(cantidad) || cantidad < 1 || cantidad === renglon.quantity) return;
    setError("");
    try {
      await updateMaterialNeed(renglon.id_proyect_material_need, { quantity: cantidad });
      await cargar();
    } catch (e) {
      decirError(e, "No se pudo cambiar la cantidad.");
      await cargar();
    }
  }

  async function cancelar(renglon) {
    setError("");
    try {
      await cancelMaterialNeed(renglon.id_proyect_material_need);
      await cargar();
    } catch (e) {
      decirError(e, "No se pudo quitar de la lista.");
    }
  }

  // "Corregir y reenviar": cambia las palabras si hace falta y vuelve a quedar por
  // revisar; si quien reviso se equivoco, basta con reenviar.
  async function reenviar(renglon) {
    const texto = (correccion[renglon.id_proyect_material_need] ?? renglon.description ?? "").trim();
    if (!texto || descripcionSospechosa(texto)) {
      setError(t("errors.need_description_invalid", "Descríbelo con palabras, por ejemplo: soldadura 6013."));
      return;
    }
    setError("");
    try {
      await updateMaterialNeed(renglon.id_proyect_material_need, {
        description: texto, resubmit: true,
      });
      setCorreccion((c) => ({ ...c, [renglon.id_proyect_material_need]: undefined }));
      await cargar();
    } catch (e) {
      decirError(e, "No se pudo reenviar.");
    }
  }

  // Del almacen a un prevale: el proyecto, lo que busca y cuanto necesita ya puestos.
  const pedirEnAlmacen = (r) => navegar("/vouchers", {
    state: { prevale: {
      id_proyect: idProyect, buscar: r.display_name, cantidad: r.quantity,
    } },
  });

  function estadoDe(r) {
    if (r.linked) {
      const falta = Math.max(0, r.quantity - r.in_stock);
      return falta === 0
        ? { clase: "cubierta", texto: t("material_needs.covered", "Hay suficiente en almacén") }
        : { clase: "falta", texto: `${t("material_needs.stock", "Hay")} ${r.in_stock} · ${t("material_needs.missing", "faltan")} ${falta}` };
    }
    if (r.returned) return { clase: "devuelto", texto: t("material_needs.returned", "Devuelto") };
    if (r.review_result === "buy") {
      return { clase: "compra", texto: t("material_needs.to_buy", "Se comprará") };
    }
    return { clase: "revisar", texto: t("material_needs.to_review", "Por revisar") };
  }

  const hayAyuda = sugerencias.materials.length > 0 || sugerencias.previous.length > 0;

  return (
    <section className="material-necesario">
      <h4>{t("material_needs.title", "Material necesario")}</h4>
      <p className="muted material-necesario-ayuda">
        {t("material_needs.help",
          "Lo que este proyecto necesita, con tus palabras. Puedes pedir más de lo que hay: así quien compra sabe qué falta.")}
      </p>

      {error && <p className="alert error">{error}</p>}
      {cargando && items.length === 0 && <p className="muted">{t("common.loading", "Cargando…")}</p>}

      {!cargando && items.length === 0 && (
        <p className="muted">{t("material_needs.empty", "Todavía no se ha pedido nada.")}</p>
      )}

      {items.length > 0 && (
        <ul className="necesidades-lista">
          {items.map((r) => {
            const estado = estadoDe(r);
            const unidad = r.unit || r.material?.unit;
            return (
              <li key={r.id_proyect_material_need}>
                <div className="necesidad-material">
                  <strong>{r.display_name || `#${r.id_proyect_material_need}`}</strong>
                  {r.linked && (
                    <small className="muted">{t("material_needs.in_catalog", "Del almacén")}</small>
                  )}
                  {r.note && <small className="muted">{r.note}</small>}
                </div>
                <label className="necesidad-cantidad">
                  <span>{t("material_needs.quantity", "Pide")}{unidad ? ` (${unidad})` : ""}</span>
                  {puedeEditar ? (
                    <input type="number" min="1" max={CANTIDAD_MAXIMA} defaultValue={r.quantity}
                           key={`${r.id_proyect_material_need}-${r.quantity}`}
                           onBlur={(e) => cambiarCantidad(r, e.target.value)} />
                  ) : <strong>{r.quantity}</strong>}
                </label>
                <span className={`necesidad-estado ${estado.clase}`}>{estado.texto}</span>
                {r.needed_by && (
                  <span className="muted necesidad-fecha">
                    {t("material_needs.needed_by", "Para")}{" "}
                    {new Date(`${r.needed_by}T00:00:00`).toLocaleDateString("es-MX")}
                  </span>
                )}
                {puedeEditar && (
                  <button type="button" className="vale-icono necesidad-quitar"
                          onClick={() => cancelar(r)}
                          aria-label={t("material_needs.remove", "Quitar de la lista")}
                          title={t("material_needs.remove", "Quitar de la lista")}>
                    <X size={14} />
                  </button>
                )}

                {r.linked && r.covered_by_stock && puedePedirEnAlmacen && !cerrado && (
                  <div className="necesidad-accion">
                    <p className="muted">
                      {t("material_needs.ask_help", "El almacén tiene lo que necesitas. Para llevártelo se pide con un prevale.")}
                    </p>
                    <button type="button" className="button button-quiet"
                            onClick={() => pedirEnAlmacen(r)}>
                      <PackageOpen size={14} />
                      {t("material_needs.ask_warehouse", "Pedir en almacén")}
                    </button>
                  </div>
                )}

                {r.returned && (
                  <div className="necesidad-devuelto">
                    <p>
                      <strong>{t("material_needs.returned_why", "Te lo devolvieron")}:</strong>{" "}
                      {r.review_note}
                    </p>
                    {puedeEditar && (
                      <div className="necesidad-correccion">
                        <input type="text" maxLength={200}
                               defaultValue={r.description}
                               onChange={(e) => setCorreccion((c) => ({
                                 ...c, [r.id_proyect_material_need]: e.target.value }))} />
                        <button type="button" className="button primary" onClick={() => reenviar(r)}>
                          {t("material_needs.resubmit", "Corregir y reenviar")}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {puedeCrear && (
        <form className="necesidad-formulario" onSubmit={agregar}>
          <div className="field necesidad-campo-material">
            <label htmlFor={`necesidad-texto-${idProyect}`}>
              {t("material_needs.what", "¿Qué necesitas?")}
            </label>
            {formulario.id_material ? (
              <div className="necesidad-vinculo">
                <span>
                  <strong>{formulario.material_label}</strong>
                  <small className="muted"> · {t("material_needs.in_catalog", "Del almacén")}</small>
                </span>
                <button type="button" className="vale-icono" onClick={quitarVinculo}
                        aria-label={t("material_needs.unlink", "Escribirlo con mis palabras")}
                        title={t("material_needs.unlink", "Escribirlo con mis palabras")}>
                  <X size={14} />
                </button>
              </div>
            ) : (
              <input id={`necesidad-texto-${idProyect}`} type="text" maxLength={200}
                     autoComplete="off" value={formulario.description}
                     aria-invalid={Boolean(motivoSospechoso)}
                     placeholder={t("material_needs.what_placeholder", "Ej. soldadura 6013, tornillos 1/4…")}
                     onChange={cambiar("description")} />
            )}
            {motivoSospechoso && (
              <p className="field-error">
                {t("errors.need_description_invalid", "Descríbelo con palabras, por ejemplo: soldadura 6013.")}
              </p>
            )}
            {hayAyuda && (
              <div className="necesidad-sugerencias">
                {sugerencias.previous.length > 0 && (
                  <>
                    <p className="muted">
                      {t("material_needs.already_asked", "Ya se pidió así antes. Úsalo para que se escriba igual.")}
                    </p>
                    <ul>
                      {sugerencias.previous.map((p) => (
                        <li key={p.description}>
                          <span>
                            <strong>{p.description}</strong>
                            {p.unit && <small className="muted"> · {p.unit}</small>}
                          </span>
                          <button type="button" className="button button-quiet"
                                  onClick={() => elegirYaPedido(p)}>
                            {t("material_needs.use_this_text", "Usar este texto")}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {sugerencias.materials.length > 0 && (
                  <>
                    <p className="muted">
                      {t("material_needs.suggestions", "El almacén tiene algo parecido. ¿Es lo que necesitas?")}
                    </p>
                    <ul>
                      {sugerencias.materials.map((s) => (
                        <li key={s.id_material}>
                          <span>
                            <strong>{s.material_description}</strong>
                            <small className="muted"> · {t("material_needs.stock", "Hay")} {s.in_stock}</small>
                          </span>
                          <button type="button" className="button button-quiet"
                                  onClick={() => elegirDelCatalogo(s)}>
                            {t("material_needs.use_this", "Usar este")}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}
          </div>
          <label className="field">
            <span>{t("material_needs.quantity_label", "Cantidad")}</span>
            <input type="number" min="1" max={CANTIDAD_MAXIMA} step="1" value={formulario.quantity}
                   onChange={cambiar("quantity")} />
          </label>
          {!formulario.id_material && (
            <label className="field">
              <span>{t("material_needs.unit", "Unidad")}</span>
              <select value={formulario.unit} onChange={cambiar("unit")}>
                <option value="">—</option>
                {UNIDADES.map((u) => <option key={u} value={u}>{u}</option>)}
              </select>
            </label>
          )}
          <label className="field">
            <span>{t("material_needs.needed_by_label", "Para cuándo")}</span>
            <input type="date" value={formulario.needed_by} onChange={cambiar("needed_by")} />
          </label>
          <label className="field necesidad-campo-nota">
            <span>{t("material_needs.note", "Nota")}</span>
            <input type="text" maxLength={300} value={formulario.note} onChange={cambiar("note")} />
          </label>
          <button type="submit" className="button primary" disabled={!listoParaAgregar || guardando}>
            <Plus size={15} />
            {t("material_needs.add", "Agregar")}
          </button>
        </form>
      )}
    </section>
  );
}

MaterialNecesario.propTypes = {
  idProyect: PropTypes.number.isRequired,
  estatus: PropTypes.string,
};
