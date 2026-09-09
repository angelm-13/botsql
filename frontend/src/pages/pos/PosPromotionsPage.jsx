import { useState } from "react";
import { Percent, Plus } from "lucide-react";
import { useI18n } from "../../i18n";
import { posRequest } from "../../api";
import PosScreen, { listaDe, mensajeDeError, numero } from "./PosScreen";

/**
 * Promociones del punto de venta.
 *
 * Cada regla se configura distinto -un porcentaje no se parametriza como un
 * 3x2- asi que el formulario cambia sus campos segun `rule_type` y arma el
 * `config` que espera el motor de reglas. Un solo campo de JSON libre habria
 * sido menos codigo y mas errores: el motor valida al vender, o sea que una
 * llave mal escrita se descubre con el cliente enfrente.
 *
 * La lista muestra `times_used` porque es el dato que dice si una promocion
 * sirve. Una con cero usos en un mes no esta funcionando, este activa o no.
 */

const REGLAS = {
  percent_discount: [["percent", "Porcentaje", "number"]],
  fixed_discount: [["amount", "Importe", "number"]],
  buy_x_get_y: [["buy_qty", "Compra", "number"], ["get_qty", "Llévate", "number"]],
  nth_unit_free: [["nth", "Unidad gratis (n)", "number"]],
  happy_hour: [["percent", "Porcentaje", "number"],
               ["from_hour", "Desde (hora)", "number"], ["to_hour", "Hasta (hora)", "number"]],
  bundle_price: [["bundle_price", "Precio del combo", "number"]],
};

export default function PosPromotionsPage() {
  const { t } = useI18n();
  const [abierto, setAbierto] = useState(false);
  const [regla, setRegla] = useState("percent_discount");
  const [nombre, setNombre] = useState("");
  const [config, setConfig] = useState({});
  const [prioridad, setPrioridad] = useState("0");
  const [acumulable, setAcumulable] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");

  const campos = REGLAS[regla] || [];

  return (
    <PosScreen
      titulo={t("pos.promotions_title", "Promociones")}
      descripcion={t("pos.promotions_subtitle",
        "Las reglas que descuentan solas al cobrar, y cuánto se han usado.")}
      recursos={{ promociones: "promotions", categorias: "products/categories" }}
      acciones={
        <button className="button" onClick={() => setAbierto((v) => !v)}>
          <Plus size={16} /> {t("pos.new_promotion", "Nueva promoción")}
        </button>
      }
    >
      {(datos, { recargar }) => {
        const promociones = listaDe(datos.promociones);
        const categorias = listaDe(datos.categorias);
        const nombreDeCategoria = new Map(categorias.map((c) => [String(c.id), c.name]));

        const crear = async () => {
          setOcupado(true); setError("");
          try {
            const numerico = Object.fromEntries(
              campos.map(([k]) => [k, Number(config[k] || 0)]).filter(([, v]) => !Number.isNaN(v))
            );
            await posRequest("promotions", {
              method: "POST",
              body: {
                name: nombre.trim(),
                rule_type: regla,
                config: numerico,
                priority: Number(prioridad || 0),
                is_stackable: acumulable,
              },
            });
            setNombre(""); setConfig({}); setAbierto(false);
            await recargar();
          } catch (e) {
            setError(mensajeDeError(e, t));
          } finally {
            setOcupado(false);
          }
        };

        return (
          <>
            {error && <p className="error">{error}</p>}

            {abierto && (
              <section className="pos-panel pos-form">
                <h2 className="pos-section-title">
                  <Percent size={17} /> {t("pos.new_promotion", "Nueva promoción")}
                </h2>
                <div className="pos-fields">
                  <label className="ancho">
                    <span>{t("pos.name", "Nombre")}</span>
                    <input value={nombre} maxLength={150}
                           onChange={(e) => setNombre(e.target.value)} />
                  </label>
                  <label>
                    <span>{t("pos.rule_type", "Tipo de regla")}</span>
                    <select value={regla} onChange={(e) => { setRegla(e.target.value); setConfig({}); }}>
                      {Object.keys(REGLAS).map((r) => (
                        <option key={r} value={r}>{t(`pos.rule_${r}`, r)}</option>
                      ))}
                    </select>
                  </label>
                  {/* Los campos cambian con la regla: cada una se parametriza
                      distinto y el motor valida al vender, o sea con el cliente
                      enfrente. Mejor no dejar escribir una llave inventada. */}
                  {campos.map(([clave, etiqueta, tipo]) => (
                    <label key={clave}>
                      <span>{t(`pos.cfg_${clave}`, etiqueta)}</span>
                      <input type={tipo} value={config[clave] ?? ""}
                             onChange={(e) => setConfig({ ...config, [clave]: e.target.value })} />
                    </label>
                  ))}
                  <label>
                    <span>{t("pos.priority", "Prioridad")}</span>
                    <input type="number" value={prioridad}
                           onChange={(e) => setPrioridad(e.target.value)} />
                  </label>
                  <label className="casilla">
                    <input type="checkbox" checked={acumulable}
                           onChange={(e) => setAcumulable(e.target.checked)} />
                    <span>{t("pos.stackable", "Se acumula con otras")}</span>
                  </label>
                </div>
                <button className="button primary" disabled={ocupado || !nombre.trim()} onClick={crear}>
                  {t("common.save", "Guardar")}
                </button>
              </section>
            )}

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t("pos.name", "Promoción")}</th>
                    <th>{t("pos.rule_type", "Regla")}</th>
                    <th>{t("pos.applies_to", "Aplica a")}</th>
                    <th className="num">{t("pos.priority", "Prioridad")}</th>
                    <th className="num">{t("pos.times_used", "Usos")}</th>
                    <th>{t("pos.state", "Estado")}</th>
                  </tr>
                </thead>
                <tbody>
                  {promociones.length === 0 && (
                    <tr><td colSpan="6" className="muted">
                      {t("pos.no_promotions", "Sin promociones.")}
                    </td></tr>
                  )}
                  {promociones.map((p) => {
                    const cats = (p.applicable_category_ids || [])
                      .map((id) => nombreDeCategoria.get(String(id)) || "—");
                    const prods = (p.applicable_product_ids || []).length;
                    return (
                      <tr key={p.id}>
                        <td>
                          <strong>{p.name}</strong>
                          {p.config && Object.keys(p.config).length > 0 && (
                            <p className="muted mono">
                              {Object.entries(p.config).map(([k, v]) => `${k}: ${v}`).join(" · ")}
                            </p>
                          )}
                        </td>
                        <td>{t(`pos.rule_${p.rule_type}`, p.rule_type)}</td>
                        <td>
                          {cats.length ? cats.join(", ")
                            : prods ? `${numero(prods)} ${t("pos.products", "productos").toLowerCase()}`
                            : t("pos.everything", "Todo")}
                        </td>
                        <td className="num mono">{numero(p.priority)}</td>
                        <td className="num mono">{numero(p.times_used)}</td>
                        <td>
                          <span className={p.is_active ? "pos-chip ok" : "pos-chip muted"}>
                            {p.is_active ? t("pos.active", "Activa") : t("pos.inactive", "Inactiva")}
                          </span>
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
