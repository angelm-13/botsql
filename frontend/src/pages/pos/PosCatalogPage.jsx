import { useState } from "react";
import { Plus, Search, Tag } from "lucide-react";
import { useI18n } from "../../i18n";
import { posRequest } from "../../api";
import PosScreen, { dinero, listaDe, mensajeDeError, numero } from "./PosScreen";

/**
 * Catalogo del punto de venta: que se vende, a que precio y con que existencia.
 *
 * Es el catalogo del almacen, no una copia suya. Antes esta pantalla marcaba
 * cada producto como "enlazado" o "sin enlazar" porque el POS tenia su propia
 * tabla y solo los emparejados descontaban del inventario. Con una sola tabla
 * `product` no hay nada que emparejar, asi que esa columna se retiro.
 */
const PRODUCTO_NUEVO = {
  sku: "", name: "", category_id: "", sale_price: "",
  current_stock: "", id_invoice: "", id_material: "",
};

export default function PosCatalogPage() {
  const { t } = useI18n();
  const [busqueda, setBusqueda] = useState("");
  const [categoria, setCategoria] = useState("");
  const [formulario, setFormulario] = useState(null);  // "producto" | "categoria" | null
  const [producto, setProducto] = useState(PRODUCTO_NUEVO);
  const [nuevaCategoria, setNuevaCategoria] = useState({ name: "" });
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");

  return (
    <PosScreen
      titulo={t("pos.catalog_title", "Catálogo")}
      descripcion={t("pos.catalog_subtitle",
        "Lo que el punto de venta ofrece, con su precio y su existencia.")}
      recursos={{ productos: "products", categorias: "products/categories" }}
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
        const filtrados = productos.filter((p) => {
          const texto = busqueda.trim().toLowerCase();
          const coincide = !texto
            || String(p.name || "").toLowerCase().includes(texto)
            || String(p.sku || "").toLowerCase().includes(texto)
            || String(p.sku || "").toLowerCase().includes(texto);
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
          sale_price: numeroOpcional(producto.sale_price),
          current_stock: numeroOpcional(producto.current_stock) ?? 0,
          // El nucleo exige que un producto venga de una compra y sea de algun
          // tipo: `product.id_invoice` e `id_material` son obligatorias. Se
          // piden en vez de inventarlas.
          id_invoice: numeroOpcional(producto.id_invoice),
          id_material: numeroOpcional(producto.id_material),
        }, () => setProducto(PRODUCTO_NUEVO));

        // Sin `color_hex`: `product_family` no tiene columna de color, y
        // agregarsela cambiaria el catalogo del almacen por un adorno de esta
        // pantalla.
        const altaCategoria = () => guardar("products/categories", {
          name: nuevaCategoria.name.trim(),
        }, () => setNuevaCategoria({ name: "" }));

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
                    "Se da de alta en el almacén de TYAKXA, que es el mismo que usa la caja. Por eso pide la compra de la que viene y su tipo de material: en TYAKXA un producto existe porque se compró.")}
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
                  <label><span>{t("pos.initial_stock", "Existencia inicial")}</span>
                    <input type="number" min="0" step="1" value={producto.current_stock}
                           onChange={(e) => setProducto({ ...producto, current_stock: e.target.value })} /></label>
                  <label><span>{t("pos.purchase_invoice", "Factura de compra")} *</span>
                    <input type="number" min="1" value={producto.id_invoice}
                           onChange={(e) => setProducto({ ...producto, id_invoice: e.target.value })} /></label>
                  <label><span>{t("pos.material", "Material")} *</span>
                    <input type="number" min="1" value={producto.id_material}
                           onChange={(e) => setProducto({ ...producto, id_material: e.target.value })} /></label>
                </div>
                <button className="button primary" onClick={altaProducto}
                        disabled={ocupado || !producto.name.trim()
                                  || !producto.id_invoice || !producto.id_material}>
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
                    <th className="num">{t("pos.stock", "Existencia")}</th>
                  </tr>
                </thead>
                <tbody>
                  {filtrados.length === 0 && (
                    <tr><td colSpan="4" className="muted">
                      {t("pos.no_products", "Sin resultados.")}
                    </td></tr>
                  )}
                  {filtrados.map((p) => {
                    // TYAKXA no guarda un minimo por producto, asi que "bajo"
                    // es el mismo umbral que usa la pantalla de Almacen.
                    const existencia = Number(p.current_stock ?? 0);
                    const bajo = existencia <= 5;
                    const familia = categorias.find(
                      (c) => String(c.id) === String(p.category_id));
                    return (
                      <tr key={p.id}>
                        <td>
                          <strong>{p.name}</strong>
                          {p.sku && <p className="muted mono">{p.sku}</p>}
                        </td>
                        <td>{familia?.name || "—"}</td>
                        <td className="num mono">{dinero(p.price)}</td>
                        <td className={bajo ? "num mono bajo" : "num mono"}>
                          {numero(existencia)}
                          {bajo && <span className="pos-chip warn">
                            {t("pos.low", "Bajo")}
                          </span>}
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
