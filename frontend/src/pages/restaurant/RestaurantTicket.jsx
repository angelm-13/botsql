/* eslint-disable react/prop-types */
import { useI18n } from "../../i18n";
import { money } from "./RestaurantUi";

/**
 * Ticket de venta en formato de 80 mm.
 *
 * Se manda a la impresora con el dialogo del navegador: la hoja de estilos
 * de impresion (restaurant-print.css) oculta todo lo demas de la pagina y
 * deja solo este bloque. NO es un CFDI -- es el comprobante interno de
 * venta; la factura fiscal la emite el modulo de facturacion del core.
 */
export default function RestaurantTicket({ orders, label, payment, business }) {
  const { t } = useI18n();
  const lineas = orders.flatMap((orden) => (orden.items || []).map((item) => ({
    key: `${orden.id_restaurant_order}-${item.id_restaurant_order_item}`,
    diner: orden.diner_index,
    cantidad: item.quantity,
    titulo: item.dish?.title || "",
    guisados: [item.guisado_1?.name, item.guisado_2?.name].filter(Boolean).join(" / "),
    importe: Number(item.unit_price || 0) * (item.quantity || 0),
  })));
  const subtotal = orders.reduce((suma, o) => suma + Number(o.subtotal || 0), 0);
  const propina = orders.reduce((suma, o) => suma + Number(o.tip_amount || 0), 0);
  const total = Math.round((subtotal + propina) * 100) / 100;
  const variosComensales = new Set(orders.map((o) => o.diner_index)).size > 1;

  return <div className="rest-ticket-print" id="rest-ticket-print">
    <div className="rtp-head">
      <strong>{business?.name || t("restaurant.ticket_title")}</strong>
      {business?.address && <span>{business.address}</span>}
      <span>{new Date().toLocaleString()}</span>
      <span>{label}</span>
    </div>

    <div className="rtp-lines">
      {lineas.map((linea) => <div className="rtp-line" key={linea.key}>
        <div className="rtp-line-main">
          <span>{linea.cantidad}× {linea.titulo}</span>
          <b>{money(linea.importe)}</b>
        </div>
        {linea.guisados && <small>{linea.guisados}</small>}
        {variosComensales && <small>{t("restaurant.diner")} {linea.diner}</small>}
      </div>)}
      {!lineas.length && <div className="rtp-line"><small>{t("restaurant.empty_order")}</small></div>}
    </div>

    <div className="rtp-totals">
      <div><span>{t("restaurant.subtotal")}</span><span>{money(subtotal)}</span></div>
      {propina > 0 && <div><span>{t("restaurant.tip")}</span><span>{money(propina)}</span></div>}
      <div className="rtp-total"><span>{t("restaurant.total")}</span><span>{money(total)}</span></div>
      {payment?.payment_method && <div><span>{t(`restaurant.method_${payment.payment_method}`)}</span><span>{money(payment.cash_total ?? total)}</span></div>}
      {payment?.received_amount != null && <div><span>{t("restaurant.received")}</span><span>{money(payment.received_amount)}</span></div>}
      {payment?.change_amount > 0 && <div><span>{t("restaurant.change")}</span><span>{money(payment.change_amount)}</span></div>}
    </div>

    <div className="rtp-foot">
      <span>{t("restaurant.ticket_thanks")}</span>
      <small>{t("restaurant.ticket_not_invoice")}</small>
    </div>
  </div>;
}
