/* eslint-disable react/prop-types */
import React, { useMemo, useState } from "react";
import { Banknote, CreditCard, Landmark, Printer, Split, X } from "lucide-react";
import { useI18n } from "../../i18n";
import { money } from "./RestaurantUi";

const METODOS = [
  { key: "efectivo", icon: Banknote },
  { key: "tarjeta", icon: CreditCard },
  { key: "transferencia", icon: Landmark },
  { key: "mixto", icon: Split },
];

// Atajos de billetes para no teclear el monto recibido en la prisa del cobro.
const BILLETES = [50, 100, 200, 500, 1000];

/**
 * Ventana de cobro. Sirve para una sola cuenta o para la mesa completa:
 * `orders` es la lista de cuentas que se van a liquidar juntas.
 */
export default function RestaurantPaymentModal({ orders, label, onCancel, onConfirm, onPrint }) {
  const { t } = useI18n();
  const [metodo, setMetodo] = useState("efectivo");
  const [tipoPropina, setTipoPropina] = useState("porcentaje");
  const [propinaPorcentaje, setPropinaPorcentaje] = useState(10);
  const [propinaMonto, setPropinaMonto] = useState(0);
  const [recibido, setRecibido] = useState("");
  const [efectivoMixto, setEfectivoMixto] = useState("");
  const [enviando, setEnviando] = useState(false);

  const subtotal = useMemo(
    () => orders.reduce((suma, orden) => suma + Number(orden.subtotal || 0), 0),
    [orders]
  );
  const propina = tipoPropina === "porcentaje"
    ? Math.round(subtotal * (Number(propinaPorcentaje) || 0)) / 100
    : Number(propinaMonto) || 0;
  const total = Math.round((subtotal + propina) * 100) / 100;

  // Cuanto tiene que entrar en efectivo: todo, nada, o la parte capturada.
  const debidoEnEfectivo = metodo === "efectivo"
    ? total
    : metodo === "mixto" ? Math.min(Number(efectivoMixto) || 0, total) : 0;
  const recibidoNum = Number(recibido) || 0;
  const cambio = Math.round(Math.max(recibidoNum - debidoEnEfectivo, 0) * 100) / 100;
  const faltante = Math.round(Math.max(debidoEnEfectivo - recibidoNum, 0) * 100) / 100;
  const pideRecibido = metodo === "efectivo" || metodo === "mixto";
  const puedeCobrar = !enviando && (!pideRecibido || (recibido !== "" && faltante === 0));

  const confirmar = async () => {
    setEnviando(true);
    try {
      await onConfirm({
        payment_method: metodo,
        tip_type: tipoPropina,
        ...(tipoPropina === "porcentaje"
          ? { tip_percent: Number(propinaPorcentaje) || 0 }
          : { tip_amount: Number(propinaMonto) || 0 }),
        ...(metodo === "mixto" ? { cash_amount: Number(efectivoMixto) || 0 } : {}),
        ...(pideRecibido && recibido !== "" ? { received_amount: recibidoNum } : {}),
      });
    } finally {
      setEnviando(false);
    }
  };

  return <div className="rest-modal-backdrop" role="dialog" aria-modal="true">
    <div className="rest-modal">
      <div className="rest-panel-heading">
        <div><span>{t("restaurant.charge")}</span><h2>{label}</h2></div>
        <button className="rest-icon-button" title={t("restaurant.cancel")} onClick={onCancel}><X size={18} /></button>
      </div>

      <div className="rest-modal-body">
        <div className="rest-modal-lines">
          {orders.map((orden) => <div className="rest-ticket-row" key={orden.id_restaurant_order}>
            <span>{t("restaurant.diner")} {orden.diner_index} · {orden.items?.length || 0} {t("restaurant.items")}</span>
            <b>{money(orden.subtotal)}</b>
          </div>)}
        </div>

        <label className="rest-field">
          <span>{t("restaurant.payment_method")}</span>
          <div className="rest-method-grid">
            {METODOS.map((item) => {
              const Icon = item.icon;
              return <button
                type="button"
                key={item.key}
                className={metodo === item.key ? "is-selected" : ""}
                onClick={() => setMetodo(item.key)}
              ><Icon size={16} />{t(`restaurant.method_${item.key}`)}</button>;
            })}
          </div>
        </label>

        <div className="rest-modal-grid">
          <label className="rest-field">
            <span>{t("restaurant.tip")}</span>
            <select value={tipoPropina} onChange={(e) => setTipoPropina(e.target.value)}>
              <option value="porcentaje">{t("restaurant.tip_percent")}</option>
              <option value="manual">{t("restaurant.tip_fixed")}</option>
            </select>
          </label>
          {tipoPropina === "porcentaje"
            ? <label className="rest-field"><span>%</span><input type="number" min="0" step="1" value={propinaPorcentaje} onChange={(e) => setPropinaPorcentaje(e.target.value)} /></label>
            : <label className="rest-field"><span>{t("restaurant.amount")}</span><input type="number" min="0" step="0.01" value={propinaMonto} onChange={(e) => setPropinaMonto(e.target.value)} /></label>}
        </div>

        {metodo === "mixto" && <label className="rest-field">
          <span>{t("restaurant.cash_part")}</span>
          <input type="number" min="0" max={total} step="0.01" value={efectivoMixto} onChange={(e) => setEfectivoMixto(e.target.value)} />
          <small className="rest-muted">{t("restaurant.card_part")}: {money(Math.max(total - (Number(efectivoMixto) || 0), 0))}</small>
        </label>}

        {pideRecibido && <label className="rest-field">
          <span>{t("restaurant.received")}</span>
          <input type="number" min="0" step="0.01" value={recibido} onChange={(e) => setRecibido(e.target.value)} autoFocus />
          <div className="rest-quick-cash">
            <button type="button" onClick={() => setRecibido(String(debidoEnEfectivo))}>{t("restaurant.exact")}</button>
            {BILLETES.filter((b) => b >= debidoEnEfectivo).slice(0, 3).map((b) =>
              <button type="button" key={b} onClick={() => setRecibido(String(b))}>{money(b)}</button>)}
          </div>
        </label>}

        <div className="rest-modal-totals">
          <div><span>{t("restaurant.subtotal")}</span><b>{money(subtotal)}</b></div>
          <div><span>{t("restaurant.tip")}</span><b>{money(propina)}</b></div>
          <div className="is-total"><span>{t("restaurant.total")}</span><strong>{money(total)}</strong></div>
          {pideRecibido && recibido !== "" && (faltante > 0
            ? <div className="is-missing"><span>{t("restaurant.missing")}</span><strong>{money(faltante)}</strong></div>
            : <div className="is-change"><span>{t("restaurant.change")}</span><strong>{money(cambio)}</strong></div>)}
        </div>
      </div>

      <div className="rest-modal-actions">
        <button className="rest-secondary" onClick={onCancel} disabled={enviando}>{t("restaurant.cancel")}</button>
        {onPrint && <button className="rest-secondary" onClick={onPrint}><Printer size={16} /> {t("restaurant.print_ticket")}</button>}
        <button className="rest-primary" onClick={confirmar} disabled={!puedeCobrar}>
          {enviando ? t("restaurant.charging") : `${t("restaurant.charge")} ${money(total)}`}
        </button>
      </div>
    </div>
  </div>;
}
