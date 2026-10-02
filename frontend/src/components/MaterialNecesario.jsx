import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import { Plus, X } from "lucide-react";
import {
  cancelMaterialNeed, createProyectMaterialNeed, getMaterialNeedSuggestions,
  getMyPermissions, getProyectMaterialNeeds, updateMaterialNeed,
} from "../api";
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

/**
 * Lo que el proyecto necesita, en el detalle del proyecto.
 *
 * Texto libre primero: el catalogo de este almacen es de herramienta y equipo, y lo
 * que una obra consume -tornillos, soldadura, discos- casi nunca esta ahi. Mientras
 * el supervisor escribe se le sugiere lo que el catalogo parece tener; si elige una
 * sugerencia el renglon queda vinculado (y se compara con la existencia), y si no,
 * queda como texto y alguien que conoce el almacen lo revisa en "Por comprar".
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
  const actor = useMemo(actorGuardado, []);
  const [items, setItems] = useState([]);
  const [permisos, setPermisos] = useState([]);
  const [formulario, setFormulario] = useState(FORMULARIO_VACIO);
  const [sugerencias, setSugerencias] = useState([]);
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
      setSugerencias([]);
      return undefined;
    }
    const numero = ++peticion.current;
    const temporizador = setTimeout(async () => {
      try {
        const lista = await getMaterialNeedSuggestions(texto);
        if (numero === peticion.current) setSugerencias(Array.isArray(lista) ? lista : []);
      } catch {
        if (numero === peticion.current) setSugerencias([]);
      }
    }, 300);
    return () => clearTimeout(temporizador);
  }, [formulario.description, formulario.id_material, puedeCrear]);

  const cambiar = (campo) => (e) => setFormulario((f) => ({ ...f, [campo]: e.target.value }));

  function elegirSugerencia(s) {
    setFormulario((f) => ({
      ...f, id_material: s.id_material, material_label: s.material_description,
      unit: f.unit || s.unit || "",
    }));
    setSugerencias([]);
  }

  const quitarVinculo = () => setFormulario((f) => ({ ...f, id_material: "", material_label: "" }));

  const listoParaAgregar = (formulario.id_material || formulario.description.trim())
    && Number(formulario.quantity) >= 1;

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
        unit: formulario.unit.trim() || undefined,
      };
      if (formulario.id_material) datos.id_material = Number(formulario.id_material);
      else datos.description = formulario.description.trim();
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

  function estadoDe(r) {
    if (r.linked) {
      const falta = Math.max(0, r.quantity - r.in_stock);
      return falta === 0
        ? { clase: "cubierta", texto: t("material_needs.covered", "Hay suficiente en almacén") }
        : { clase: "falta", texto: `${t("material_needs.stock", "Hay")} ${r.in_stock} · ${t("material_needs.missing", "faltan")} ${falta}` };
    }
    if (r.review_result === "buy") {
      return { clase: "compra", texto: t("material_needs.to_buy", "Se comprará") };
    }
    return { clase: "revisar", texto: t("material_needs.to_review", "Por revisar") };
  }

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
                    <input type="number" min="1" defaultValue={r.quantity}
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
                     placeholder={t("material_needs.what_placeholder", "Ej. soldadura 6013, tornillos 1/4…")}
                     onChange={cambiar("description")} />
            )}
            {sugerencias.length > 0 && (
              <div className="necesidad-sugerencias">
                <p className="muted">
                  {t("material_needs.suggestions", "El almacén tiene algo parecido. ¿Es lo que necesitas?")}
                </p>
                <ul>
                  {sugerencias.map((s) => (
                    <li key={s.id_material}>
                      <span>
                        <strong>{s.material_description}</strong>
                        <small className="muted"> · {t("material_needs.stock", "Hay")} {s.in_stock}</small>
                      </span>
                      <button type="button" className="button button-quiet"
                              onClick={() => elegirSugerencia(s)}>
                        {t("material_needs.use_this", "Usar este")}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <label className="field">
            <span>{t("material_needs.quantity_label", "Cantidad")}</span>
            <input type="number" min="1" step="1" value={formulario.quantity}
                   onChange={cambiar("quantity")} />
          </label>
          <label className="field">
            <span>{t("material_needs.unit", "Unidad")}</span>
            <input type="text" maxLength={40} value={formulario.unit}
                   placeholder={t("material_needs.unit_placeholder", "kg, pza, m…")}
                   onChange={cambiar("unit")} />
          </label>
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
