import { useState } from "react";
import PropTypes from "prop-types";
import { Banknote, CalendarClock, CircleDollarSign, FileText, TriangleAlert } from "lucide-react";
import { useI18n } from "../i18n";
import {
  addProyectPayment, deleteProyectPayment, settleProyectPayment,
  transitionProyectManagement,
} from "../api";
import "../styles/proyecto-expediente.css";

/**
 * El expediente de un proyecto de taller: la orden de trabajo, el cobro y todo
 * lo que cuelga de él.
 *
 * Por qué vive aparte del panel de detalle
 * ----------------------------------------
 * El panel de detalle ya contaba dos cosas —las tareas y la bitácora— y estas
 * son cuatro más. Meterlas dentro habría hecho ilegible un bloque que ya era
 * largo, y estas secciones se leen juntas: quien abre un proyecto para saber
 * "cómo va" mira la orden, el cobro y los pendientes de una vez.
 *
 * Las dos vidas del proyecto
 * --------------------------
 * El estado de TALLER lo mueve el panel de detalle, con las transiciones que ya
 * tenía. El estado COMERCIAL se mueve aquí, y son máquinas distintas a
 * propósito: un proyecto entregado puede seguir sin cobrar, y con una sola
 * columna eso no se podría ni representar. Las transiciones válidas las manda
 * el servidor en el catálogo; esta pantalla no lleva su propia copia.
 */
export default function ProyectoExpediente({ detalle, catalogo, onCambio }) {
  const { t } = useI18n();
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");
  const [pago, setPago] = useState({ payment_date: "", amount: "", agreed_percent: "", notes: "" });

  const resumen = detalle.payment_summary || {};
  const pagos = detalle.payments || [];
  const incidencias = detalle.incidents || [];
  const citas = detalle.appointments || [];

  // Del servidor, nunca de una copia local: una lista escrita aquí ofrecería
  // transiciones que el servidor rechaza.
  const comercialActual = detalle.management_status || "pendiente_orden_compra";
  const destinos = catalogo?.proyect?.management_transitions?.[comercialActual] || [];

  const etiqueta = (clave, porOmision) => t(`project_management.${clave}`, porOmision);
  const dinero = (v) => new Intl.NumberFormat("es-MX", {
    style: "currency", currency: "MXN",
  }).format(Number(v || 0));

  async function ejecutar(accion) {
    setOcupado(true); setError("");
    try {
      await accion();
      await onCambio();
    } catch (e) {
      setError(e?.payload?.error_key || e?.message || "errors.request_failed");
    } finally {
      setOcupado(false);
    }
  }

  const guardarPago = (evento) => {
    evento.preventDefault();
    return ejecutar(async () => {
      await addProyectPayment(detalle.id_proyect, {
        payment_date: pago.payment_date,
        amount: Number(pago.amount),
        agreed_percent: pago.agreed_percent === "" ? undefined : Number(pago.agreed_percent),
        notes: pago.notes.trim() || undefined,
      });
      setPago({ payment_date: "", amount: "", agreed_percent: "", notes: "" });
    });
  };

  return (
    <div className="expediente">
      {error && <p className="error">{t(error, error)}</p>}

      {/* --- la orden de trabajo --- */}
      <h4><FileText size={15} /> {etiqueta("work_order", "Orden de trabajo")}</h4>
      <dl className="expediente-datos">
        <Dato etiqueta={etiqueta("folio", "Folio")} valor={detalle.folio} />
        <Dato etiqueta={etiqueta("requested_by", "Lo pidió")} valor={detalle.requested_by} />
        <Dato etiqueta={etiqueta("quotation", "Cotización")}
              valor={detalle.id_quotation && `#${detalle.id_quotation}`} />
        <Dato etiqueta={etiqueta("purchase_order", "Orden de compra")}
              valor={detalle.purchase_order} />
        <Dato etiqueta={etiqueta("purchase_order_item", "Partida")}
              valor={detalle.purchase_order_item} />
        <Dato etiqueta={etiqueta("delivery_date", "Entrega")} valor={detalle.delivery_date} />
      </dl>

      {/* --- el recorrido comercial --- */}
      <h4><CircleDollarSign size={15} /> {etiqueta("management", "Gerencia")}</h4>
      <p className="expediente-comercial">
        <span className={`expediente-estado ${comercialActual}`}>
          {etiqueta(`management_${comercialActual}`, comercialActual.replaceAll("_", " "))}
        </span>
        {destinos.map((destino) => (
          <button key={destino} type="button" className="button button-quiet"
                  disabled={ocupado}
                  onClick={() => ejecutar(() => transitionProyectManagement(
                    detalle.id_proyect, { management_status: destino }))}>
            {etiqueta(`management_${destino}`, destino.replaceAll("_", " "))}
          </button>
        ))}
        {destinos.length === 0 && (
          <span className="muted">{etiqueta("management_final", "Sin más movimientos.")}</span>
        )}
      </p>

      {/* --- las parcialidades --- */}
      <h4><Banknote size={15} /> {etiqueta("payments", "Parcialidades de pago")}</h4>
      {pagos.length > 0 && (
        <>
          <div className="table-wrap">
            <table className="expediente-tabla">
              <thead>
                <tr>
                  <th>{etiqueta("payment_date", "Acordado")}</th>
                  <th className="num">{etiqueta("amount", "Monto")}</th>
                  <th className="num">{etiqueta("percent", "% pactado")}</th>
                  <th>{etiqueta("paid_at", "Cobrado")}</th>
                  <th>{etiqueta("notes", "Nota")}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {pagos.map((p) => (
                  <tr key={p.id_proyect_payment} className={p.paid_at ? "cobrado" : ""}>
                    <td className="mono">{p.payment_date}</td>
                    <td className="num mono">{dinero(p.amount)}</td>
                    <td className="num mono">
                      {p.agreed_percent === null || p.agreed_percent === undefined
                        ? <span className="muted">—</span> : `${p.agreed_percent}%`}
                    </td>
                    <td>
                      {/* Marcar cobrado con la fecha REAL, que no tiene por qué
                          ser la acordada: un pago que cae tarde sigue siendo el
                          pago de su fecha, y guardar una sola borra el retraso. */}
                      {p.paid_at ? (
                        <button type="button" className="expediente-cobrado" disabled={ocupado}
                                title={etiqueta("unsettle", "Quitar el cobro")}
                                onClick={() => ejecutar(() => settleProyectPayment(
                                  p.id_proyect_payment, { paid_at: null }))}>
                          {p.paid_at}
                        </button>
                      ) : (
                        <input type="date" disabled={ocupado}
                               aria-label={etiqueta("settle", "Fecha de cobro")}
                               onChange={(e) => e.target.value && ejecutar(
                                 () => settleProyectPayment(p.id_proyect_payment,
                                                            { paid_at: e.target.value }))} />
                      )}
                    </td>
                    <td className="muted">{p.notes || "—"}</td>
                    <td>
                      <button type="button" className="icon-button" disabled={ocupado}
                              title={etiqueta("delete", "Quitar")}
                              onClick={() => ejecutar(
                                () => deleteProyectPayment(p.id_proyect_payment))}>×</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <ul className="expediente-resumen">
            <li><span>{etiqueta("agreed", "Acordado")}</span>
                <strong className="mono">{dinero(resumen.agreed_total)}</strong></li>
            <li><span>{etiqueta("collected", "Cobrado")}</span>
                <strong className="mono ok">{dinero(resumen.collected_total)}</strong></li>
            <li><span>{etiqueta("pending", "Pendiente")}</span>
                <strong className="mono pendiente">{dinero(resumen.pending_total)}</strong></li>
            {/* Los porcentajes se muestran tal como se pactaron, aunque no
                sumen 100: que falten es un dato -falta acordar una
                parcialidad-, y cuadrarlo aquí lo escondería. */}
            <li><span>{etiqueta("percent_agreed", "% pactado")}</span>
                <strong className="mono">{Number(resumen.agreed_percent_total || 0)}%</strong></li>
          </ul>
        </>
      )}

      <form className="expediente-alta" onSubmit={guardarPago}>
        <label className="field">
          <span>{etiqueta("payment_date", "Fecha acordada")} *</span>
          <input type="date" required value={pago.payment_date}
                 onChange={(e) => setPago({ ...pago, payment_date: e.target.value })} />
        </label>
        <label className="field">
          <span>{etiqueta("amount", "Monto")} *</span>
          <input type="number" min="0.01" step="0.01" required value={pago.amount}
                 onChange={(e) => setPago({ ...pago, amount: e.target.value })} />
        </label>
        <label className="field">
          <span>{etiqueta("percent", "% pactado")}</span>
          <input type="number" min="0.01" max="100" step="0.01" value={pago.agreed_percent}
                 onChange={(e) => setPago({ ...pago, agreed_percent: e.target.value })} />
        </label>
        <label className="field ancho">
          <span>{etiqueta("notes", "Nota")}</span>
          <input value={pago.notes} maxLength={200}
                 onChange={(e) => setPago({ ...pago, notes: e.target.value })} />
        </label>
        <button className="button primary" disabled={ocupado || !pago.payment_date || !pago.amount}>
          {etiqueta("add_payment", "Acordar parcialidad")}
        </button>
      </form>

      {/* --- lo que cuelga del proyecto --- */}
      {incidencias.length > 0 && (
        <>
          <h4><TriangleAlert size={15} /> {etiqueta("incidents", "Incidencias")}</h4>
          <ul className="expediente-lista">
            {incidencias.map((i) => (
              <li key={i.id_incident}>
                <strong>#{i.external_folio || i.id_incident}</strong>
                <span>{i.note || "—"}</span>
                <span className="muted">{i.incident_status}</span>
              </li>
            ))}
          </ul>
        </>
      )}

      {citas.length > 0 && (
        <>
          <h4><CalendarClock size={15} /> {etiqueta("appointments", "Calendario")}</h4>
          <ul className="expediente-lista">
            {citas.map((c) => (
              <li key={c.id_appointment}>
                <strong className="mono">
                  {c.starts_at ? new Date(c.starts_at).toLocaleString("es-MX") : "—"}
                </strong>
                <span>{c.guest_name || "—"}</span>
                <span className="muted">{c.status}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

/** Un dato de la orden, con su hueco cuando falta. */
function Dato({ etiqueta, valor }) {
  return (
    <>
      <dt>{etiqueta}</dt>
      <dd>{valor === null || valor === undefined || valor === ""
        ? <span className="muted">—</span> : valor}</dd>
    </>
  );
}

Dato.propTypes = {
  etiqueta: PropTypes.string.isRequired,
  valor: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
};
Dato.defaultProps = { valor: null };

ProyectoExpediente.propTypes = {
  detalle: PropTypes.object.isRequired,
  catalogo: PropTypes.object,
  onCambio: PropTypes.func.isRequired,
};
ProyectoExpediente.defaultProps = { catalogo: null };
