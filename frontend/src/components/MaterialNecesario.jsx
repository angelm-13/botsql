import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import { Plus, X } from "lucide-react";
import FiltroBuscable from "./FiltroBuscable.jsx";
import {
  cancelMaterialNeed, createProyectMaterialNeed, getMaterialNeedOptions,
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

const FORMULARIO_VACIO = { id_material: "", quantity: "1", needed_by: "", note: "" };

/**
 * Lo que el proyecto necesita de material, en el detalle del proyecto.
 *
 * El supervisor declara aqui que le hace falta; quien compra lo ve junto con el de
 * los demas proyectos en "Por comprar". Se puede pedir MAS de lo que hay en el
 * almacen: la lista sirve justo para avisar el faltante, a diferencia del prevale,
 * que es recoger material fisico y no pasa de la existencia.
 *
 * "Hay N" es la existencia de hoy, sin reservar: no descuenta lo que piden otros
 * proyectos. Quien compra ve el total de todos en su pantalla.
 */
export default function MaterialNecesario({ idProyect, estatus }) {
  const { t } = useI18n();
  // `t` cambia de identidad en cada render: como dependencia de `cargar` lo
  // volvia a llamar sin parar (200 peticiones en segundos). Se lee por referencia.
  const traducir = useRef(t);
  traducir.current = t;
  const actor = useMemo(actorGuardado, []);
  const [items, setItems] = useState([]);
  const [materiales, setMateriales] = useState([]);
  const [permisos, setPermisos] = useState([]);
  const [formulario, setFormulario] = useState(FORMULARIO_VACIO);
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");

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

  // Las opciones solo se piden cuando hay formulario que llenar: quien nada mas
  // lee la lista no necesita bajar el catalogo.
  useEffect(() => {
    if (!puedeCrear) return undefined;
    let vivo = true;
    getMaterialNeedOptions()
      .then((m) => { if (vivo) setMateriales(Array.isArray(m) ? m : []); })
      .catch(() => { if (vivo) setMateriales([]); });
    return () => { vivo = false; };
  }, [puedeCrear]);

  const yaPedidos = useMemo(() => new Set(items.map((i) => String(i.id_material))), [items]);
  const opciones = useMemo(() => materiales
    .filter((m) => !yaPedidos.has(String(m.id_material)))
    .map((m) => ({
      value: m.id_material,
      label: m.unit ? `${m.material_description} (${m.unit})` : m.material_description,
    })), [materiales, yaPedidos]);

  async function agregar(evento) {
    evento.preventDefault();
    if (!formulario.id_material || guardando) return;
    setGuardando(true);
    setError("");
    try {
      await createProyectMaterialNeed(idProyect, {
        id_material: Number(formulario.id_material),
        quantity: Number(formulario.quantity),
        needed_by: formulario.needed_by || undefined,
        note: formulario.note.trim() || undefined,
      });
      setFormulario(FORMULARIO_VACIO);
      await cargar();
    } catch (e) {
      decirError(e, "No se pudo agregar el material.");
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
      decirError(e, "No se pudo quitar el material.");
    }
  }

  return (
    <section className="material-necesario">
      <h4>{t("material_needs.title", "Material necesario")}</h4>
      <p className="muted material-necesario-ayuda">
        {t("material_needs.help",
          "Lo que este proyecto necesita. Puedes pedir más de lo que hay: así quien compra sabe qué falta.")}
      </p>

      {error && <p className="alert error">{error}</p>}
      {cargando && <p className="muted">{t("common.loading", "Cargando…")}</p>}

      {!cargando && items.length === 0 && (
        <p className="muted">{t("material_needs.empty", "Todavía no se ha pedido material.")}</p>
      )}

      {items.length > 0 && (
        <ul className="necesidades-lista">
          {items.map((r) => {
            const falta = Math.max(0, r.quantity - r.in_stock);
            return (
              <li key={r.id_proyect_material_need}>
                <div className="necesidad-material">
                  <strong>{r.material?.material_description || `#${r.id_material}`}</strong>
                  {r.material?.unit && <span className="muted"> · {r.material.unit}</span>}
                  {r.note && <small className="muted">{r.note}</small>}
                </div>
                <label className="necesidad-cantidad">
                  <span>{t("material_needs.quantity", "Pide")}</span>
                  {puedeEditar ? (
                    <input type="number" min="1" defaultValue={r.quantity}
                           key={`${r.id_proyect_material_need}-${r.quantity}`}
                           onBlur={(e) => cambiarCantidad(r, e.target.value)} />
                  ) : <strong>{r.quantity}</strong>}
                </label>
                <span className={`necesidad-estado ${falta === 0 ? "cubierta" : "falta"}`}>
                  {falta === 0
                    ? t("material_needs.covered", "Hay suficiente")
                    : `${t("material_needs.stock", "Hay")} ${r.in_stock} · ${t("material_needs.missing", "faltan")} ${falta}`}
                </span>
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
          <label className="field necesidad-campo-material">
            <span>{t("material_needs.material", "Material")}</span>
            <FiltroBuscable
              valor={formulario.id_material}
              opciones={opciones}
              onChange={(v) => setFormulario((f) => ({ ...f, id_material: v }))}
              etiqueta={t("material_needs.material", "Material")}
              todas={t("common.select_option", "Selecciona una opción")}
            />
          </label>
          <label className="field">
            <span>{t("material_needs.quantity", "Cantidad")}</span>
            <input type="number" min="1" step="1" value={formulario.quantity}
                   onChange={(e) => setFormulario((f) => ({ ...f, quantity: e.target.value }))} />
          </label>
          <label className="field">
            <span>{t("material_needs.needed_by_label", "Para cuándo")}</span>
            <input type="date" value={formulario.needed_by}
                   onChange={(e) => setFormulario((f) => ({ ...f, needed_by: e.target.value }))} />
          </label>
          <label className="field necesidad-campo-nota">
            <span>{t("material_needs.note", "Nota")}</span>
            <input type="text" maxLength={300} value={formulario.note}
                   onChange={(e) => setFormulario((f) => ({ ...f, note: e.target.value }))} />
          </label>
          <button type="submit" className="button primary"
                  disabled={!formulario.id_material || !(Number(formulario.quantity) >= 1) || guardando}>
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
