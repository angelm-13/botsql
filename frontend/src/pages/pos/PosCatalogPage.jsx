import { useState } from "react";
import { Link2, Plus, Search, Tag } from "lucide-react";
import { useI18n } from "../../i18n";
import { posRequest } from "../../api";
import PosScreen, { dinero, listaDe, mensajeDeError, numero } from "./PosScreen";

/**
 * Catalogo del punto de venta: que se vende, a que precio y con que existencia.
 *
 * Ademas del listado, muestra si cada producto esta enlazado al inventario del
 * nucleo. Ese dato no es decorativo: un producto sin enlace se vende sin
 * descontar del almacen unico, y sin verlo aqui el descuadre solo aparece al
 * contar el estante.
 */
const PRODUCTO_NUEVO = {
  sku: "", name: "", category_id: "", sale_price: "", cost_price: "",
  min_stock: "", critical_stock: "", current_stock: "", barcode: "",
};

export default function PosCatalogPage() {
  const { t } = useI18n();
  const [busqueda, setBusqueda] = useState("");
  const [categoria, setCategoria] = useState("");
  const [formulario, setFormulario] = useState(null);  // "producto" | "categoria" | null
  const [producto, setProducto] = useState(PRODUCTO_NUEVO);
  const [nuevaCategoria, setNuevaCategoria] = useState({ name: "", color_hex: "#3b82f6" });
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");

  return (
    <PosScreen
      titulo={t("pos.catalog_title", "Catálogo")}
      descripcion={t("pos.catalog_subtitle",
        "Lo que el punto de venta ofrece, con su precio y su existencia.")}
      recursos={{ productos: "products", categorias: "products/categories", enlaces: "@links" }}
      acciones={
        <>
          <button className="button" onClick={() => setFormulario(
            (v) => (v === "producto" ? null : "producto"))}>
            <Plus size={16} /> {t("pos.new_product", "Nuevo producto")}
          </button>
          <button className="button" onClick={() => setFormulario(
            (v) => (v === "categoria" ? null : "categoria"))}>
            <Tag size={16} /> {t("pos.new_category", "Nueva categoria")}
          </button>
        </>
      }
    >
      {(datos, { recargar }) => {
        const productos = listaDe(datos.productos);
        const categorias = listaDe(datos.categorias);
        // Que productos del POS descuentan del almacen unico y cuales no.
        const enlazados = new Set(listaDe(datos.enlaces).map((e) => String(e.pos_product_id)));

        const filtrados = productos.filter((p) => {
          const texto = busqueda.trim().toLowerCase();
          const coincide = !texto
            || String(p.name || "").toLowerCase().includes(texto)
            || String(p.sku || "").toLowerCase().includes(texto)
            || String(p.barcode || "").includes(texto);
          const deLaCategoria = !categoria || String(p.category_id) === categoria;
          return coincide && deLaCategoria;
        });

        const guardar = async (ruta, cuerpo, limpiar) => {
          setOcupado(true); setError("");
          try {
            await posRequest(ruta, { method: "POST", body: cuerpo });
            limpiar(); setFormulario(null); await recargar();
          } catch (e) {
            setError(mensajeDeError(e, t));
          } finally {
            setOcupado(false);
          }
        };

        // Los numericos vacios no se mandan como cero: el POS distingue "no lo
        // fije" de "vale cero", y mandar cero pondria un minimo de existencia
        // que nadie pidio y con el que nada avisa nunca.
        const numeroOpcional = (v) => (String(v).trim() === "" ? undefined : Number(v));

        const altaProducto = () => guardar("products", {
          sku: producto.sku.trim(),
          name: producto.name.trim(),
          category_id: producto.category_id || undefined,
          barcode: producto.barcode.trim() || undefined,
          sale_price: numeroOpcional(producto.sale_price),
          cost_price: numeroOpcional(producto.cost_price),
          min_stock: numeroOpcional(producto.min_stock),
          critical_stock: numeroOpcional(producto.critical_stock),
          current_stock: numeroOpcional(producto.current_stock) ?? 0,
        }, () => setProducto(PRODUCTO_NUEVO));

        const altaCategoria = () => guardar("products/categories", {
          name: nuevaCategoria.name.trim(),
          color_hex: nuevaCategoria.color_hex,
        }, () => setNuevaCategoria({ name: "", color_hex: "#3b82f6" }));

        return (
          <>
            {error && <p className="error">{error}</p>}

            {formulario === "producto" && (
              <section className="pos-panel pos-form">
                <h2 className="pos-section-title">
                  <Plus size={17} /> {t("pos.new_product", "Nuevo producto")}
                </h2>
                <p className="muted">
                  {t("pos.new_product_hint",
                    "Se da de alta en el punto de venta. Para que su venta descuente del almacen de TYAKXA hay que sincronizar el catalogo desde la pantalla de Almacen.")}
                </p>
                <div className="pos-fields">
                  <label><span>SKU *</span>
                    <input value={producto.sku} maxLength={64}
                           onChange={(e) => setProducto({ ...producto, sku: e.target.value })} /></label>
                  <label className="ancho"><span>{t("pos.name", "Nombre")} *</span>
                    <input value={producto.name} maxLength={200}
                           onChange={(e) => setProducto({ ...producto, name: e.target.value })} /></label>
                  <label><span>{t("pos.category", "Categoria")}</span>
                    <select value={producto.category_id}
                            onChange={(e) => setProducto({ ...producto, category_id: e.target.value })}>
                      <option value="">—</option>
                      {categorias.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </select></label>
                  <label><span>{t("pos.price", "Precio")}</span>
                    <input type="number" min="0" step="0.01" value={producto.sale_price}
                           onChange={(e) => setProducto({ ...producto, sale_price: e.target.value })} /></label>
                  <label><span>{t("pos.cost", "Costo")}</span>
                    <input type="number" min="0" step="0.01" value={producto.cost_price}
                           onChange={(e) => setProducto({ ...producto, cost_price: e.target.value })} /></label>
                  <label><span>{t("pos.initial_stock", "Existencia inicial")}</span>
                    <input type="number" min="0" step="1" value={producto.current_stock}
                           onChange={(e) => setProducto({ ...producto, current_stock: e.target.value })} /></label>
                  <label><span>{t("pos.min_stock", "Minimo")}</span>
                    <input type="number" min="0" step="1" value={producto.min_stock}
                           onChange={(e) => setProducto({ ...producto, min_stock: e.target.value })} /></label>
                  <label><span>{t("pos.critical", "Critico")}</span>
                    <input type="number" min="0" step="1" value={producto.critical_stock}
                           onChange={(e) => setProducto({ ...producto, critical_stock: e.target.value })} /></label>
                  <label><span>{t("pos.barcode", "Codigo de barras")}</span>
                    <input value={producto.barcode} maxLength={64}
                           onChange={(e) => setProducto({ ...producto, barcode: e.target.value })} /></label>
                </div>
                <button className="button primary" onClick={altaProducto}
                        disabled={ocupado || !producto.sku.trim() || !producto.name.trim()}>
                  {t("common.save", "Guardar")}
                </button>
              </section>
            )}

            {formulario === "categoria" && (
              <section className="pos-panel pos-form">
                <h2 className="pos-section-title">
                  <Tag size={17} /> {t("pos.new_category", "Nueva categoria")}
                </h2>
                <div className="pos-fields">
                  <label className="ancho"><span>{t("pos.name", "Nombre")} *</span>
                    <input value={nuevaCategoria.name} maxLength={100}
                           onChange={(e) => setNuevaCategoria({ ...nuevaCategoria, name: e.target.value })} /></label>
                  <label><span>{t("pos.color", "Color")}</span>
                    <input type="color" value={nuevaCategoria.color_hex}
                           onChange={(e) => setNuevaCategoria({ ...nuevaCategoria, color_hex: e.target.value })} /></label>
                </div>
                <button className="button primary" onClick={altaCategoria}
                        disabled={ocupado || !nuevaCategoria.name.trim()}>
                  {t("common.save", "Guardar")}
                </button>
              </section>
            )}

            <div className="pos-toolbar">
              <div className="pos-search">
                <Search size={16} />
                <input
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  placeholder={t("pos.search_catalog", "Buscar por nombre, SKU o código")}
                  aria-label={t("pos.search_catalog", "Buscar por nombre, SKU o código")}
                />
              </div>
              <select value={categoria} onChange={(e) => setCategoria(e.target.value)}
                      aria-label={t("pos.category", "Categoría")}>
                <option value="">{t("pos.all_categories", "Todas las categorías")}</option>
                {categorias.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
              <span className="pos-count">
                {numero(filtrados.length)} {t("pos.of", "de")} {numero(productos.length)}
              </span>
            </div>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t("pos.product", "Producto")}</th>
                    <th>{t("pos.category", "Categoría")}</th>
                    <th className="num">{t("pos.price", "Precio")}</th>
                    <th className="num">{t("pos.cost", "Costo")}</th>
                    <th className="num">{t("pos.stock", "Existencia")}</th>
                    <th>{t("pos.linked", "Enlace al almacén")}</th>
                  </tr>
                </thead>
                <tbody>
                  {filtrados.length === 0 && (
                    <tr><td colSpan="6" className="muted">
                      {t("pos.no_products", "Sin resultados.")}
                    </td></tr>
                  )}
                  {filtrados.map((p) => {
                    const existencia = Number(p.current_stock ?? 0);
                    const minimo = Number(p.min_stock ?? 0);
                    const bajo = minimo > 0 && existencia <= minimo;
                    return (
                      <tr key={p.id}>
                        <td>
                          <strong>{p.name}</strong>
                          {p.sku && <p className="muted mono">{p.sku}</p>}
                        </td>
                        <td>{p.category || "—"}</td>
                        <td className="num mono">{dinero(p.sale_price ?? p.price)}</td>
                        <td className="num mono">{dinero(p.cost_price)}</td>
                        <td className={bajo ? "num mono bajo" : "num mono"}>
                          {numero(existencia)}
                          {bajo && <span className="pos-chip warn">
                            {t("pos.low", "Bajo")}
                          </span>}
                        </td>
                        <td>
                          {/* Sin enlace la venta no descuenta del almacen unico.
                              Se marca aqui porque es donde se ve y se corrige;
                              si no, el descuadre aparece al contar el estante. */}
                          {enlazados.has(String(p.id)) ? (
                            <span className="pos-chip ok">
                              <Link2 size={12} /> {t("pos.linked_yes", "Enlazado")}
                            </span>
                          ) : (
                            <span className="pos-chip warn" title={t("pos.link_hint",
                              "Sin enlace, la venta no descuenta del inventario de TYAKXA.")}>
                              <Link2 size={12} /> {t("pos.not_linked", "Sin enlazar")}
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        );
      }}
    </PosScreen>
  );
}
