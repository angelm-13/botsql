import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import { Plus, X } from "lucide-react";
import {
  createPurchaseOrder, getMaterialNeedsToBuy, getPurchaseSuppliers, submitPurchaseOrder,
  updatePurchaseOrder,
} from "../api";
import { CANTIDAD_MAXIMA, UNIDADES, descripcionSospechosa } from "../utils/descripcionDeNecesidad";
import { dinero, totalDeRenglones } from "../utils/ordenDeCompra";
import { useI18n } from "../i18n";
import { CLASES_DE_ARTICULO } from "../utils/clasesDeProducto";
import { UNIDADES_DE_TARIFA, costoDeRenta, periodosDeRenta } from "../utils/rentaDeMaquinaria";
import "../styles/ordenes-de-compra.css";
import "../styles/renta-maquinaria.css";

const fechaCorta = (texto) => (texto
  ? new Date(`${String(texto).slice(0, 10)}T00:00:00`).toLocaleDateString("es-MX") : "—");

/** El costo unitario que cuenta: el capturado, o en una renta tarifa x periodos. */
function conCosto(r) {
  if (r.line_kind !== "rental") return r;
  const costo = costoDeRenta(r.rental_rate, r.rental_start, r.rental_end, r.rental_rate_unit);
  return { ...r, unit_cost: costo === null ? "" : String(costo) };
}

const LIBRE_VACIO = { description: "", quantity: "1", unit: "", unit_cost: "", item_class: "" };

function etiquetaDeProyecto(p) {
  if (!p) return "";
  const folio = p.folio ? `#${p.folio}` : `#${p.id_proyect}`;
  return p.title ? `${folio} — ${p.title}` : folio;
}

function desdeRenglon(l) {
  return {
    key: `l${l.id_purchase_order_line}`,
    id_proyect_material_need: l.id_proyect_material_need,
    id_proyect: l.id_proyect,
    id_material: l.id_material,
    item_class: l.item_class || "",
    description: l.description,
    unit: l.unit || "",
    quantity: String(l.quantity),
    unit_cost: l.unit_cost === null || l.unit_cost === undefined ? "" : String(l.unit_cost),
    proyecto: etiquetaDeProyecto(l.project),
    line_kind: l.line_kind || "purchase",
    rental_start: l.rental_start || "",
    rental_end: l.rental_end || "",
    rental_rate: l.rental_rate === null || l.rental_rate === undefined ? "" : String(l.rental_rate),
    rental_rate_unit: l.rental_rate_unit || "day",
  };
}

/**
 * Armar (o corregir) una orden de compra.
 *
 * Lo normal es armarla con lo que falta por comprar: cada renglon sale de la
 * necesidad de un proyecto, asi que la orden sabe a quien le toca que, y una misma
 * compra puede surtir a varias obras. Solo entran necesidades ya revisadas y que no
 * esten en otra orden; lo demas el servidor lo rechaza igual. Compras tambien puede
 * agregar un renglon por su cuenta (reponer almacen), que queda marcado como tal.
 *
 * El proveedor se escribe a mano; se sugieren los dados de alta y, si el nombre
 * coincide con uno, el servidor liga la orden a el (y compara el RFC de su factura).
 * Todo va en pesos (MXN): no se pregunta la moneda.
 */
export default function OrdenDeCompraEditor({ orden, precargar, onGuardada, onCancelar }) {
  const { t } = useI18n();
  const traducir = useRef(t);
  traducir.current = t;
  const [proveedores, setProveedores] = useState([]);
  const [disponibles, setDisponibles] = useState([]);
  const [form, setForm] = useState(() => ({
    supplier_name: orden?.supplier?.name || orden?.supplier_name || "",
    description: orden?.description || "",
    expected_date: orden?.expected_date || "",
    // Las ordenes viejas en otra moneda la conservan; las nuevas van en pesos.
    currency: orden?.currency || "MXN",
  }));
  const [renglones, setRenglones] = useState(() => (orden?.lines || []).map(desdeRenglon));
  const [libre, setLibre] = useState(LIBRE_VACIO);
  const [errorLibre, setErrorLibre] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const precargado = useRef(false);

  const decirError = useCallback((e, porOmision) => setError(
    e?.payload?.error_key
      ? traducir.current(e.payload.error_key, porOmision)
      : traducir.current("errors.request_failed", porOmision)), []);

  useEffect(() => {
    let vivo = true;
    getPurchaseSuppliers("")
      .then((r) => { if (vivo) setProveedores(r || []); })
      .catch(() => { if (vivo) setProveedores([]); });
    // Solo lo que se puede comprar: revisado y sin orden. Lo que ya esta en ESTA orden
    // se ve en los renglones de arriba.
    getMaterialNeedsToBuy({ only_missing: 0 })
      .then((r) => {
        if (!vivo) return;
        const lista = [];
        for (const g of r?.items || []) {
          for (const p of g.projects || []) {
            if (p.purchasable === false || p.order) continue;
            lista.push({
              id: p.id_proyect_material_need,
              nombre: g.linked ? g.material?.material_description : g.description,
              unidad: g.unit || "",
              id_material: g.linked ? g.material?.id_material : null,
              cantidad: p.quantity,
              id_proyect: p.id_proyect,
              proyecto: etiquetaDeProyecto(p),
              renta: g.need_kind === "rental"
                ? { rental_start: g.rental_start, rental_end: g.rental_end } : null,
            });
          }
        }
        setDisponibles(lista);
      })
      .catch(() => { if (vivo) setDisponibles([]); });
    return () => { vivo = false; };
  }, []);

  const yaEstan = useMemo(
    () => new Set(renglones.map((r) => r.id_proyect_material_need).filter(Boolean)),
    [renglones]);
  const porAgregar = disponibles.filter((d) => !yaEstan.has(d.id));
  const total = totalDeRenglones(renglones.map(conCosto));

  const agregarNecesidad = useCallback((d) => {
    setRenglones((actuales) => (actuales.some((r) => r.id_proyect_material_need === d.id)
      ? actuales
      : [...actuales, {
        key: `n${d.id}`, id_proyect_material_need: d.id, id_proyect: d.id_proyect,
        id_material: d.id_material, description: d.nombre, unit: d.unidad,
        quantity: String(d.cantidad), maxQuantity: d.cantidad, unit_cost: "",
        proyecto: d.proyecto,
        ...(d.renta ? {
          line_kind: "rental", rental_start: d.renta.rental_start, rental_end: d.renta.rental_end,
          rental_rate: "", rental_rate_unit: "day",
        } : { line_kind: "purchase" }),
      }]));
  }, []);

  // Si se llego desde "Por comprar", las necesidades escogidas ya vienen puestas.
  useEffect(() => {
    if (precargado.current || !precargar?.length || disponibles.length === 0) return;
    precargado.current = true;
    disponibles.filter((d) => precargar.includes(d.id)).forEach(agregarNecesidad);
  }, [precargar, disponibles, agregarNecesidad]);

  const cambiarRenglon = (key, campo, valor) => setRenglones(
    (rs) => rs.map((r) => (r.key === key ? { ...r, [campo]: valor } : r)));
  const quitarRenglon = (key) => setRenglones((rs) => rs.filter((r) => r.key !== key));

  function agregarLibre() {
    setErrorLibre("");
    const descripcion = libre.description.trim();
    if (!descripcion) return;
    if (descripcionSospechosa(descripcion)) {
      setErrorLibre(t("errors.need_description_invalid", "Descríbelo con palabras, por ejemplo: guantes de carnaza."));
      return;
    }
    const cantidad = Number(libre.quantity);
    if (!Number.isInteger(cantidad) || cantidad < 1 || cantidad > CANTIDAD_MAXIMA) {
      setErrorLibre(t("order.bad_quantity", "La cantidad tiene que ser un entero mayor que cero."));
      return;
    }
    setRenglones((rs) => [...rs, {
      key: `f${Date.now()}`, id_proyect_material_need: null, id_proyect: null, id_material: null,
      description: descripcion, unit: libre.unit, quantity: String(cantidad),
      unit_cost: libre.unit_cost, item_class: libre.item_class, proyecto: "",
    }]);
    setLibre(LIBRE_VACIO);
  }

  function cuerpo() {
    return {
      supplier_name: form.supplier_name.trim(),
      description: form.description,
      expected_date: form.expected_date || null,
      currency: form.currency,
      lines: renglones.map((r) => {
        // En una renta el costo lo calcula el servidor con la tarifa y el periodo.
        const base = r.line_kind === "rental" ? {
          quantity: r.quantity, line_kind: "rental",
          rental_rate: r.rental_rate === "" ? null : r.rental_rate,
          rental_rate_unit: r.rental_rate_unit, rental_start: r.rental_start,
          rental_end: r.rental_end,
        } : {
          quantity: r.quantity, unit_cost: r.unit_cost === "" ? null : r.unit_cost,
          item_class: r.item_class || null,
        };
        if (r.id_proyect_material_need) return { id_proyect_material_need: r.id_proyect_material_need, ...base };
        return {
          description: r.description, unit: r.unit || null, id_proyect: r.id_proyect || null,
          id_material: r.id_material || null, ...base,
        };
      }),
    };
  }

  async function guardar(enviar) {
    setGuardando(true);
    setError("");
    let guardada = null;
    try {
      guardada = orden
        ? await updatePurchaseOrder(orden.id_purchase_order, cuerpo())
        : await createPurchaseOrder(cuerpo());
      if (enviar) guardada = await submitPurchaseOrder(guardada.id_purchase_order);
      onGuardada(guardada);
    } catch (e) {
      decirError(e, "No se pudo guardar la orden.");
      // Si se guardo pero no se pudo enviar, la orden existe: se muestra para corregirla.
      if (guardada) onGuardada(guardada);
    } finally {
      setGuardando(false);
    }
  }

  const sinProveedor = form.supplier_name.trim().length < 2;
  const sinRenglones = renglones.length === 0;
  const sinCostos = total === null;
  // Lo que falta para poder enviarla, dicho en voz alta (el boton solo se apaga).
  const faltantes = [
    sinProveedor && t("order.missing_supplier", "escribir el proveedor"),
    sinRenglones && t("order.missing_lines", "agregar al menos un renglón"),
    !sinRenglones && sinCostos && t("order.missing_costs", "capturar el costo de cada renglón"),
  ].filter(Boolean);

  return (
    <div className="oc-editor">
      <h3>{orden
        ? `${t("order.editing", "Corregir orden")} ${orden.folio}`
        : t("order.new", "Nueva orden de compra")}</h3>

      {error && <div className="alert error">{error}</div>}

      <div className="oc-form-grid">
        <label>
          <span>{t("order.supplier", "Proveedor")}</span>
          <input type="text" maxLength={200} list="oc-proveedores" autoComplete="off"
                 value={form.supplier_name}
                 placeholder={t("order.supplier_placeholder", "Ej. Ferretería El Clavo")}
                 onChange={(e) => setForm({ ...form, supplier_name: e.target.value })} />
          {/* Los dados de alta salen como sugerencia; se puede escribir cualquiera. */}
          <datalist id="oc-proveedores">
            {proveedores.map((p) => <option key={p.id_customer_supplier} value={p.name} />)}
          </datalist>
          <small className="muted">
            {t("order.supplier_hint", "Escríbelo como aparece en su factura o ticket.")}
          </small>
        </label>
        <label>
          <span>{t("order.expected_date", "Se espera el")}</span>
          <input type="date" value={form.expected_date}
                 onChange={(e) => setForm({ ...form, expected_date: e.target.value })} />
        </label>
        <label className="oc-campo-ancho">
          <span>{t("order.description", "Para qué es")}</span>
          <input type="text" maxLength={300} value={form.description}
                 placeholder={t("order.description_placeholder", "Ej. Material de las obras de agosto")}
                 onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </label>
      </div>

      <h4>{t("order.lines", "Renglones")}</h4>
      {sinRenglones ? (
        <p className="muted">{t("order.no_lines", "Todavía no hay renglones. Agrega lo que falta por comprar o un renglón propio.")}</p>
      ) : (
        <div className="table-card">
          <table className="oc-tabla-renglones">
            <thead>
              <tr>
                <th>{t("order.col_what", "Qué")}</th>
                <th>{t("order.col_project", "Proyecto")}</th>
                <th>{t("item_class.label", "Clase")}</th>
                <th>{t("order.col_qty", "Cantidad")}</th>
                <th>{t("order.col_unit_cost", "Costo unitario")}</th>
                <th>{t("order.col_subtotal", "Subtotal")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {renglones.map((r) => {
                const esRenta = r.line_kind === "rental";
                const costo = conCosto(r).unit_cost;
                const subtotal = costo === "" ? null : Number(r.quantity) * Number(costo);
                const periodos = esRenta
                  ? periodosDeRenta(r.rental_start, r.rental_end, r.rental_rate_unit) : null;
                return (
                  <tr key={r.key}>
                    <td>
                      <strong>{r.description}</strong>
                      {r.unit && <span className="muted"> · {r.unit}</span>}
                      {esRenta && (
                        <>
                          {" "}<span className="renta-marca">{t("rental.badge", "Renta")}</span>
                          <small className="muted" style={{ display: "block" }}>
                            {fechaCorta(r.rental_start)} → {fechaCorta(r.rental_end)}
                          </small>
                        </>
                      )}
                      {!r.id_proyect_material_need && (
                        <span className="oc-etiqueta oc-etiqueta-propio">
                          {t("order.own_line", "agregado por Compras")}
                        </span>
                      )}
                    </td>
                    <td>{r.proyecto || <span className="muted">—</span>}</td>
                    <td>
                      {esRenta ? <span className="muted">—</span> : (
                        <select value={r.item_class} aria-label={t("item_class.label", "Clase")}
                                onChange={(e) => cambiarRenglon(r.key, "item_class", e.target.value)}>
                          <option value="">—</option>
                          {CLASES_DE_ARTICULO.map((c) => (
                            <option key={c.clave} value={c.clave}>{t(`item_class.${c.clave}`, c.etiqueta)}</option>
                          ))}
                        </select>
                      )}
                    </td>
                    <td>
                      <input type="number" min="1" max={r.maxQuantity || CANTIDAD_MAXIMA} step="1"
                             className="oc-numero" value={r.quantity}
                             onChange={(e) => cambiarRenglon(r.key, "quantity", e.target.value)} />
                    </td>
                    <td>
                      {esRenta ? (
                        <div className="oc-tarifa">
                          <input type="number" min="0" step="0.01" className="oc-numero oc-numero-ancho"
                                 value={r.rental_rate} placeholder="0.00"
                                 aria-label={t("rental.rate", "Tarifa")}
                                 onChange={(e) => cambiarRenglon(r.key, "rental_rate", e.target.value)} />
                          <select value={r.rental_rate_unit} aria-label={t("rental.rate_unit", "Por")}
                                  onChange={(e) => cambiarRenglon(r.key, "rental_rate_unit", e.target.value)}>
                            {UNIDADES_DE_TARIFA.map((u) => (
                              <option key={u} value={u}>{t(`rental.per_${u}`, u)}</option>
                            ))}
                          </select>
                          {periodos !== null && (
                            <small className="muted">
                              × {periodos} {t(`rental.unit_${r.rental_rate_unit}`, r.rental_rate_unit)}
                            </small>
                          )}
                        </div>
                      ) : (
                        <input type="number" min="0" step="0.01" className="oc-numero oc-numero-ancho"
                               value={r.unit_cost} placeholder="0.00"
                               onChange={(e) => cambiarRenglon(r.key, "unit_cost", e.target.value)} />
                      )}
                    </td>
                    <td className="mono">{subtotal === null || Number.isNaN(subtotal)
                      ? <span className="muted">—</span> : dinero(subtotal, form.currency)}</td>
                    <td>
                      <button type="button" className="button button-quiet" onClick={() => quitarRenglon(r.key)}
                              title={t("common.remove", "Quitar")}>
                        <X size={14} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={5} className="oc-total-etiqueta">{t("order.total", "Total cotizado")}</td>
                <td className="mono oc-total">{total === null ? "—" : dinero(total, form.currency)}</td>
                <td />
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      <details className="oc-agregar" open={porAgregar.length > 0 && sinRenglones}>
        <summary>
          {t("order.add_from_needs", "Agregar lo que falta por comprar")}
          {" "}<span className="muted">({porAgregar.length})</span>
        </summary>
        {porAgregar.length === 0 ? (
          <p className="muted">{t("order.nothing_to_add", "No hay nada más por comprar: lo que está revisado ya está en una orden.")}</p>
        ) : (
          <ul className="oc-disponibles">
            {porAgregar.map((d) => (
              <li key={d.id}>
                <span>
                  <strong>{d.nombre}</strong>
                  {d.renta && <> <span className="renta-marca">{t("rental.badge", "Renta")}</span></>}
                  {d.unidad && <span className="muted"> · {d.unidad}</span>}
                  <small className="muted"> {d.proyecto} · {d.cantidad}</small>
                </span>
                <button type="button" className="button button-quiet" onClick={() => agregarNecesidad(d)}>
                  <Plus size={14} /> {t("order.add", "Agregar")}
                </button>
              </li>
            ))}
          </ul>
        )}
      </details>

      <details className="oc-agregar">
        <summary>{t("order.add_own", "Agregar un renglón propio (sin que lo pida un proyecto)")}</summary>
        <div className="oc-libre">
          <label className="oc-campo-ancho">
            <span>{t("order.col_what", "Qué")}</span>
            <input type="text" maxLength={200} value={libre.description}
                   onChange={(e) => setLibre({ ...libre, description: e.target.value })} />
          </label>
          <label>
            <span>{t("order.col_qty", "Cantidad")}</span>
            <input type="number" min="1" step="1" className="oc-numero" value={libre.quantity}
                   onChange={(e) => setLibre({ ...libre, quantity: e.target.value })} />
          </label>
          <label>
            <span>{t("order.unit", "Unidad")}</span>
            <select value={libre.unit} onChange={(e) => setLibre({ ...libre, unit: e.target.value })}>
              <option value="">—</option>
              {UNIDADES.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </label>
          <label>
            <span>{t("item_class.label", "Clase")}</span>
            <select value={libre.item_class} onChange={(e) => setLibre({ ...libre, item_class: e.target.value })}>
              <option value="">—</option>
              {CLASES_DE_ARTICULO.map((c) => (
                <option key={c.clave} value={c.clave}>{t(`item_class.${c.clave}`, c.etiqueta)}</option>
              ))}
            </select>
          </label>
          <label>
            <span>{t("order.col_unit_cost", "Costo unitario")}</span>
            <input type="number" min="0" step="0.01" className="oc-numero oc-numero-ancho"
                   value={libre.unit_cost} onChange={(e) => setLibre({ ...libre, unit_cost: e.target.value })} />
          </label>
          <button type="button" className="button" onClick={agregarLibre}
                  disabled={!libre.description.trim()}>
            <Plus size={14} /> {t("order.add", "Agregar")}
          </button>
          {errorLibre && <p className="oc-error-libre">{errorLibre}</p>}
        </div>
      </details>

      <div className="oc-acciones">
        <button type="button" className="button" disabled={guardando || sinProveedor}
                onClick={() => guardar(false)}>
          {t("order.save_draft", "Guardar borrador")}
        </button>
        <button type="button" className="button primary"
                disabled={guardando || sinProveedor || sinRenglones || sinCostos}
                title={sinCostos && !sinRenglones ? t("order.costs_needed", "Falta el costo de algún renglón.") : undefined}
                onClick={() => guardar(true)}>
          {t("order.save_and_send", "Guardar y enviar a autorización")}
        </button>
        <button type="button" className="button button-quiet" onClick={onCancelar} disabled={guardando}>
          {t("common.cancel", "Cancelar")}
        </button>
      </div>
      <p className={`oc-ayuda ${faltantes.length ? "oc-faltan" : "muted"}`}>
        {faltantes.length
          ? `${t("order.missing_to_send", "Para enviarla a autorización falta:")} ${faltantes.join(", ")}.`
          : t("order.ready_to_send", "Lista para enviar. También puedes guardarla como borrador y terminarla después.")}
      </p>
    </div>
  );
}

OrdenDeCompraEditor.propTypes = {
  orden: PropTypes.shape({
    id_purchase_order: PropTypes.number, folio: PropTypes.string,
    id_customer_supplier: PropTypes.number, description: PropTypes.string,
    expected_date: PropTypes.string, currency: PropTypes.string, lines: PropTypes.array,
  }),
  precargar: PropTypes.arrayOf(PropTypes.number),
  onGuardada: PropTypes.func.isRequired,
  onCancelar: PropTypes.func.isRequired,
};

OrdenDeCompraEditor.defaultProps = { orden: null, precargar: [] };
