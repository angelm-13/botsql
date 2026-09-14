import { useI18n } from "../../i18n";
import PosScreen, { dinero, listaDe, numero } from "./PosScreen";

/**
 * Tablero del punto de venta.
 *
 * Dos horizontes distintos conviven aqui y estan separados a proposito: las
 * cifras de arriba son del dia (`today-summary`) y los desgloses de abajo son
 * historicos. Mezclarlos bajo un solo titulo "hoy" seria la clase de tablero que
 * se lee mal y se decide peor.
 *
 * Los importes vienen calculados del POS y se pintan tal cual; no se recalculan
 * aqui. Sumar en el navegador lo que el servidor ya sumo es como aparecen los
 * totales que discrepan por un centavo.
 *
 * Los nombres de campo no son adivinados: salen de la respuesta real del POS
 * (`gross_revenue`, `ticket_count`, `gross_sales`, `units_sold`...). El resumen
 * del dia no trae margen, asi que la cuarta cifra es el descuento otorgado, que
 * si trae; inventar un margen sumando otro endpoint con otro horizonte daria un
 * numero que parece del dia sin serlo.
 */

function Barra({ etiqueta, nota, valor, maximo }) {
  const ancho = maximo > 0 ? Math.max(2, (Number(valor) / maximo) * 100) : 0;
  return (
    <li className="pos-bar">
      <div className="pos-bar-head">
        <span>{etiqueta}{nota && <em className="muted"> · {nota}</em>}</span>
        <strong className="mono">{dinero(valor)}</strong>
      </div>
      <div className="pos-bar-track">
        <div className="pos-bar-fill" style={{ width: `${ancho}%` }} />
      </div>
    </li>
  );
}

export default function PosReportsPage() {
  const { t } = useI18n();

  return (
    <PosScreen
      titulo={t("pos.reports_title", "Tablero")}
      descripcion={t("pos.reports_subtitle", "Cómo va el día en el punto de venta.")}
      recursos={{
        hoy: "dashboard/today-summary",
        porCategoria: "dashboard/sales-by-category",
        porFormaDePago: "dashboard/revenue-by-payment-method",
        margen: "dashboard/product-margin",
      }}
    >
      {(datos) => {
        const hoy = datos.hoy || {};
        const categorias = listaDe(datos.porCategoria);
        const formas = listaDe(datos.porFormaDePago);
        const margenes = listaDe(datos.margen).slice(0, 10);

        const maxCategoria = Math.max(0, ...categorias.map((c) => Number(c.gross_sales || 0)));
        const maxForma = Math.max(0, ...formas.map((f) => Number(f.total_amount || 0)));

        return (
          <>
            <div className="pos-tally">
              <div className="pos-tally-card ok">
                <span className="pos-tally-count">{dinero(hoy.gross_revenue)}</span>
                <span className="pos-tally-label">{t("pos.revenue_today", "Ingresos de hoy")}</span>
              </div>
              <div className="pos-tally-card">
                <span className="pos-tally-count">{numero(hoy.ticket_count ?? 0)}</span>
                <span className="pos-tally-label">{t("pos.tickets", "Tickets")}</span>
              </div>
              <div className="pos-tally-card">
                <span className="pos-tally-count">{dinero(hoy.average_order_value)}</span>
                <span className="pos-tally-label">{t("pos.avg_ticket", "Ticket promedio")}</span>
              </div>
              <div className="pos-tally-card">
                <span className="pos-tally-count">{dinero(hoy.total_discounts)}</span>
                <span className="pos-tally-label">{t("pos.discounts", "Descuentos otorgados")}</span>
              </div>
            </div>

            {/* El horizonte cambia a partir de aqui y se dice, no se supone. */}
            <p className="pos-note">
              {t("pos.historic_note",
                "Los desgloses siguientes son del histórico acumulado, no solo de hoy.")}
            </p>

            <div className="pos-columns">
              <div className="pos-panel">
                <h2 className="pos-section-title">{t("pos.by_category", "Venta por categoría")}</h2>
                {categorias.length === 0 ? (
                  <p className="muted">{t("pos.no_data", "Sin datos todavía.")}</p>
                ) : (
                  <ul className="pos-bars">
                    {categorias.map((c, i) => (
                      <Barra
                        key={c.category_name || i}
                        etiqueta={c.category_name || "—"}
                        valor={c.gross_sales}
                        maximo={maxCategoria}
                      />
                    ))}
                  </ul>
                )}
              </div>

              <div className="pos-panel">
                <h2 className="pos-section-title">
                  {t("pos.by_payment", "Ingresos por forma de pago")}
                </h2>
                {formas.length === 0 ? (
                  <p className="muted">{t("pos.no_data", "Sin datos todavía.")}</p>
                ) : (
                  <ul className="pos-bars">
                    {formas.map((f, i) => (
                      <Barra
                        key={f.method || i}
                        etiqueta={t(`pos.method_${f.method}`, f.method || "—")}
                        nota={`${numero(f.sale_count)} ${t("pos.tickets_lower", "tickets")}`}
                        valor={f.total_amount}
                        maximo={maxForma}
                      />
                    ))}
                  </ul>
                )}
              </div>
            </div>

            <h2 className="pos-section-title">{t("pos.margin_by_product", "Margen por producto")}</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t("pos.product", "Producto")}</th>
                    <th>{t("pos.category", "Categoría")}</th>
                    <th className="num">{t("pos.sold", "Vendido")}</th>
                    <th className="num">{t("pos.revenue", "Ingreso")}</th>
                    <th className="num">{t("pos.gross_margin", "Margen bruto")}</th>
                    <th className="num">%</th>
                  </tr>
                </thead>
                <tbody>
                  {margenes.length === 0 && (
                    <tr><td colSpan="6" className="muted">
                      {t("pos.no_data", "Sin datos todavía.")}
                    </td></tr>
                  )}
                  {margenes.map((m, i) => (
                    <tr key={m.product_id || i}>
                      <td>
                        <strong>{m.product_name || "—"}</strong>
                        {m.sku && <p className="muted mono">{m.sku}</p>}
                      </td>
                      <td>{m.category_name || "—"}</td>
                      <td className="num mono">{numero(m.units_sold)}</td>
                      <td className="num mono">{dinero(m.gross_sales)}</td>
                      <td className="num mono">{dinero(m.gross_margin)}</td>
                      <td className="num mono">
                        {Number.isFinite(Number(m.gross_margin_pct))
                          ? `${Number(m.gross_margin_pct).toFixed(1)}%` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        );
      }}
    </PosScreen>
  );
}
