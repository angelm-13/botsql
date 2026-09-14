import { AlertTriangle, PackageCheck } from "lucide-react";
import { useI18n } from "../../i18n";
import PosScreen, { dinero, listaDe, numero } from "./PosScreen";

/**
 * Almacén del punto de venta, que ya es el almacén y punto.
 *
 * Esta pantalla existía para medir la distancia entre "un solo inventario" y la
 * realidad: contaba cuántos productos del POS no descontaban de TYAKXA y traía
 * un formulario para sincronizar los dos catálogos.
 *
 * Esa distancia ya no existe. El punto de venta lee y escribe la misma tabla
 * `product` y el mismo libro que el almacén, así que no hay dos saldos que
 * puedan discrepar ni catálogos que emparejar. Lo que queda es lo único que un
 * almacén de mostrador necesita contestar: qué está por acabarse, y qué hay.
 */
export default function PosWarehousePage() {
  const { t } = useI18n();

  return (
    <PosScreen
      titulo={t("pos.warehouse_title", "Almacén del punto de venta")}
      descripcion={t("pos.warehouse_subtitle",
        "Lo que hay en mostrador. Es el mismo inventario que el resto de TYAKXA.")}
      recursos={{ productos: "products", bajos: "products/low-stock" }}
    >
      {(datos) => {
        const productos = listaDe(datos.productos);
        const bajos = listaDe(datos.bajos);
        const valor = productos.reduce(
          (suma, p) => suma + Number(p.current_stock || 0) * Number(p.price || 0), 0);

        return (
          <>
            <div className="pos-tally">
              <div className="pos-tally-card">
                <span className="pos-tally-count">{numero(productos.length)}</span>
                <span className="pos-tally-label">{t("pos.products", "Productos")}</span>
              </div>
              <div className={bajos.length ? "pos-tally-card warn" : "pos-tally-card"}>
                <span className="pos-tally-count">{numero(bajos.length)}</span>
                <span className="pos-tally-label">{t("pos.low_stock", "Por acabarse")}</span>
              </div>
              <div className="pos-tally-card">
                <span className="pos-tally-count">{dinero(valor)}</span>
                <span className="pos-tally-label">
                  {t("pos.stock_value_price", "Valor a precio de venta")}
                </span>
              </div>
            </div>

            <h2 className="pos-section-title">
              <AlertTriangle size={17} /> {t("pos.low_stock", "Por acabarse")}
            </h2>
            <p className="muted">
              {t("pos.low_stock_hint",
                "TYAKXA no guarda un mínimo por producto, así que aquí sale lo que tiene 5 piezas o menos.")}
            </p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t("pos.product", "Producto")}</th>
                    <th>SKU</th>
                    <th className="num">{t("pos.stock", "Existencia")}</th>
                  </tr>
                </thead>
                <tbody>
                  {bajos.length === 0 && (
                    <tr><td colSpan="3" className="muted">
                      <PackageCheck size={15} />{" "}
                      {t("pos.nothing_low", "Nada por acabarse.")}
                    </td></tr>
                  )}
                  {bajos.map((p) => (
                    <tr key={p.id}>
                      <td><strong>{p.name}</strong></td>
                      <td className="mono">{p.sku || "—"}</td>
                      <td className="num mono bajo">{numero(p.current_stock)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <h2 className="pos-section-title">{t("pos.all_stock", "Todo el almacén")}</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t("pos.product", "Producto")}</th>
                    <th>SKU</th>
                    <th className="num">{t("pos.stock", "Existencia")}</th>
                    <th className="num">{t("pos.price", "Precio")}</th>
                    <th className="num">{t("pos.value", "Valor")}</th>
                  </tr>
                </thead>
                <tbody>
                  {productos.length === 0 && (
                    <tr><td colSpan="5" className="muted">
                      {t("pos.no_data", "Sin datos todavía.")}
                    </td></tr>
                  )}
                  {productos.map((p) => (
                    <tr key={p.id}>
                      <td>{p.name}</td>
                      <td className="mono">{p.sku || "—"}</td>
                      <td className="num mono">{numero(p.current_stock)}</td>
                      <td className="num mono">{dinero(p.price)}</td>
                      <td className="num mono">
                        {dinero(Number(p.current_stock || 0) * Number(p.price || 0))}
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
