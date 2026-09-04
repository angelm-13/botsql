import React, { useState } from "react";
import { AlertTriangle, Link2, PackageCheck } from "lucide-react";
import { useI18n } from "../../i18n";
import { posSyncCatalog } from "../../api";
import PosScreen, { dinero, listaDe, mensajeDeError, numero } from "./PosScreen";

/**
 * Almacen del punto de venta, visto desde el inventario unico.
 *
 * Lo primero que muestra es lo que esta por acabarse, que es la unica pregunta
 * urgente de un almacen de mostrador. El resto -que hay y cuanto vale- va
 * despues.
 *
 * Tambien dice cuantos productos no descuentan del almacen de TYAKXA por falta
 * de enlace. Ese numero es la distancia entre "un solo inventario" y la
 * realidad, asi que va arriba y no escondido en una columna.
 */
export default function PosWarehousePage() {
  const { t } = useI18n();
  const [sincronizando, setSincronizando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState("");
  // El esquema del nucleo exige que un producto venga de una compra y sea de
  // algun tipo: `product.id_invoice` y `product.id_material` son obligatorios.
  // Se piden en vez de inventarse, porque fabricar una factura para cuadrar un
  // requisito seria meter un documento inexistente en la contabilidad.
  const [compra, setCompra] = useState("");
  const [material, setMaterial] = useState("");

  return (
    <PosScreen
      titulo={t("pos.warehouse_title", "Almacén del punto de venta")}
      descripcion={t("pos.warehouse_subtitle",
        "Lo que hay en mostrador y qué tanto está conectado al inventario de TYAKXA.")}
      recursos={{ productos: "products", bajos: "products/low-stock", enlaces: "@links" }}
    >
      {(datos, { recargar }) => {
        const productos = listaDe(datos.productos);
        const bajos = listaDe(datos.bajos);
        const enlazados = new Set(listaDe(datos.enlaces).map((e) => String(e.pos_product_id)));

        const sinEnlace = productos.filter((p) => !enlazados.has(String(p.id)));
        const valor = productos.reduce(
          (suma, p) => suma + Number(p.current_stock || 0) * Number(p.cost_price || 0), 0);

        const sincronizar = async () => {
          setSincronizando(true); setError(""); setResultado(null);
          try {
            const r = await posSyncCatalog({
              id_invoice: Number(compra), id_material: Number(material),
            });
            setResultado(r);
            await recargar();
          } catch (e) {
            setError(mensajeDeError(e, t));
          } finally {
            setSincronizando(false);
          }
        };

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
                <span className="pos-tally-label">{t("pos.stock_value", "Valor al costo")}</span>
              </div>
              {/* La distancia entre "un solo inventario" y la realidad. */}
              <div className={sinEnlace.length ? "pos-tally-card crit" : "pos-tally-card ok"}>
                <span className="pos-tally-count">{numero(sinEnlace.length)}</span>
                <span className="pos-tally-label">
                  {t("pos.unlinked_count", "Sin enlazar al almacén")}
                </span>
              </div>
            </div>

            {sinEnlace.length > 0 && (
              <p className="pos-warn">
                <AlertTriangle size={15} />
                {t("pos.unlinked_warning",
                  "Estos productos se venden sin descontar del inventario de TYAKXA. Hasta enlazarlos, los dos saldos van por separado.")}
              </p>
            )}

            {error && <p className="error">{error}</p>}

            <section className="pos-panel pos-form">
              <h2 className="pos-section-title">
                <Link2 size={17} /> {t("pos.sync_catalog", "Sincronizar con el almacén de TYAKXA")}
              </h2>
              <p className="muted">
                {t("pos.sync_hint",
                  "Da de alta en el almacén único los productos del punto de venta que aún no descuentan de nada, y les pone su saldo de apertura. A los que ya existen no les toca la existencia: si los dos saldos difieren, lo reporta para que alguien decida cuál es el bueno.")}
              </p>
              <div className="pos-fields">
                <label>
                  <span>{t("pos.purchase_invoice", "Factura de compra")}</span>
                  <input type="number" min="1" value={compra}
                         onChange={(e) => setCompra(e.target.value)} />
                </label>
                <label>
                  <span>{t("pos.material", "Material")}</span>
                  <input type="number" min="1" value={material}
                         onChange={(e) => setMaterial(e.target.value)} />
                </label>
              </div>
              <button className="button primary"
                      disabled={sincronizando || !compra || !material}
                      onClick={sincronizar}>
                <Link2 size={15} />
                {sincronizando ? t("common.loading", "Cargando…")
                               : t("pos.sync_now", "Sincronizar")}
              </button>

              {resultado && (
                <ul className="pos-cut-lines">
                  <li><span>{t("pos.created", "Creados")}</span>
                      <span className="mono">{numero(resultado.created?.length || 0)}</span><span /></li>
                  <li><span>{t("pos.linked_existing", "Enlazados")}</span>
                      <span className="mono">{numero(resultado.linked?.length || 0)}</span><span /></li>
                  <li><span>{t("pos.already", "Ya estaban")}</span>
                      <span className="mono">{numero(resultado.skipped?.length || 0)}</span><span /></li>
                  <li><span>{t("pos.mismatches", "Descuadres")}</span>
                      <span className="mono">{numero(resultado.discrepancies?.length || 0)}</span><span /></li>
                </ul>
              )}
              {resultado?.discrepancies?.length > 0 && (
                <p className="pos-warn">
                  <AlertTriangle size={15} />
                  {resultado.discrepancies.map((d) =>
                    `${d.name}: POS ${d.pos_stock} / TYAKXA ${d.core_stock}`).join(" · ")}
                </p>
              )}
            </section>

            <h2 className="pos-section-title">
              <AlertTriangle size={17} /> {t("pos.low_stock", "Por acabarse")}
            </h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t("pos.product", "Producto")}</th>
                    <th className="num">{t("pos.stock", "Existencia")}</th>
                    <th className="num">{t("pos.min_stock", "Mínimo")}</th>
                    <th className="num">{t("pos.critical", "Crítico")}</th>
                  </tr>
                </thead>
                <tbody>
                  {bajos.length === 0 && (
                    <tr><td colSpan="4" className="muted">
                      <PackageCheck size={15} />{" "}
                      {t("pos.nothing_low", "Nada por acabarse.")}
                    </td></tr>
                  )}
                  {bajos.map((p) => (
                    <tr key={p.id}>
                      <td><strong>{p.name}</strong></td>
                      <td className="num mono bajo">{numero(p.current_stock)}</td>
                      <td className="num mono">{numero(p.min_stock)}</td>
                      <td className="num mono">{numero(p.critical_stock)}</td>
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
                    <th className="num">{t("pos.stock", "Existencia")}</th>
                    <th className="num">{t("pos.cost", "Costo")}</th>
                    <th className="num">{t("pos.value", "Valor")}</th>
                    <th>{t("pos.linked", "Enlace al almacén")}</th>
                  </tr>
                </thead>
                <tbody>
                  {productos.map((p) => (
                    <tr key={p.id}>
                      <td>{p.name}</td>
                      <td className="num mono">{numero(p.current_stock)}</td>
                      <td className="num mono">{dinero(p.cost_price)}</td>
                      <td className="num mono">
                        {dinero(Number(p.current_stock || 0) * Number(p.cost_price || 0))}
                      </td>
                      <td>
                        <span className={enlazados.has(String(p.id))
                          ? "pos-chip ok" : "pos-chip warn"}>
                          {enlazados.has(String(p.id))
                            ? t("pos.linked_yes", "Enlazado")
                            : t("pos.not_linked", "Sin enlazar")}
                        </span>
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
