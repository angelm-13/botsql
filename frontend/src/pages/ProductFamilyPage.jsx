import { useCallback, useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  ChevronDown, ChevronRight, Hammer, Layers, Package, Pencil, Plus, RefreshCw,
  Ruler, Trash2, X,
} from "lucide-react";
import {
  createProductFamily,
  deleteProductFamily,
  getAllProductFamily,
  updateProductFamily,
} from "../api";
import FamilyAttributes from "../components/FamilyAttributes.jsx";
import { useI18n } from "../i18n";
import "../styles/product-family.css";
import PageHeader from "../components/PageHeader.jsx";

/**
 * Familias de producto: cómo se clasifica el material, en una sola pantalla.
 *
 * Qué quedó y qué se fue
 * ----------------------
 * Había DOS entradas de menú —«Familias de producto» y «Tipos de material»— y
 * leídas por separado parecían la misma cosa dos veces. Se juntaron en esta y
 * después el TIPO se retiró del todo: en estos datos la descripción del
 * material ya lo trae —«BROCA HELICOIDAL 3/4», «DADO 3/16»—, así que un nivel
 * aparte obligaba a capturar dos veces lo mismo. La tabla `material_type` sigue
 * en la base con sus filas; lo que se fue es la pantalla y el paso de captura.
 *
 * Qué hace la familia entonces
 * ----------------------------
 * Dos cosas, y las dos se ven aquí:
 *
 *   * AGRUPA el material. `material.id_product_family` es NOT NULL, así que
 *     todo material cuelga de una; y
 *   * DECLARA qué se le pregunta a cada material de esa familia —largo,
 *     calibre, acabado—. Eso es `material_attribute`, y es el botón
 *     «Características» de cada renglón.
 *
 * La declaración vive aquí porque es configuración y se hace una vez. El VALOR
 * —«6 pulgadas»— se contesta al dar de alta el material, en su propia pantalla:
 * es ahí donde alguien lo sabe.
 *
 * `product_family.type` no es el tipo que se retiró: solo acepta `tool` o
 * `consumable` y separa lo que se presta y vuelve de lo que se gasta. Es la
 * misma división que `product.stock_purpose` hace pieza por pieza, un nivel más
 * arriba.
 */

export default function ProductFamilyPage() {
  const { t } = useI18n();
  const [familias, setFamilias] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  // El formulario de la FAMILIA: { idFamilia, descripcion, tipo }. `idFamilia`
  // nulo es alta. Va aparte del de tipos para que abrir uno cierre el otro sin
  // ambiguedad: son dos niveles distintos y editarlos a la vez confunde.
  const [formFamilia, setFormFamilia] = useState(null);
  // Las familias con sus caracteristicas a la vista. Se cargan al abrir y no al
  // abrir la pantalla: son una peticion por familia, y con veinte familias
  // serian veinte peticiones para pintar algo que casi nadie mira.
  const [conCaracteristicas, setConCaracteristicas] = useState(() => new Set());
  const [guardando, setGuardando] = useState(false);

  // `t` cambia de identidad en cada render; si entra en las dependencias del
  // efecto la pantalla se repide sin parar.
  const traducir = useRef(t);
  traducir.current = t;

  const cargar = useCallback(async () => {
    setCargando(true);
    setError("");
    try {
      const respFamilias = await getAllProductFamily({ per_page: 200 });
      setFamilias(respFamilias?.items || []);
    } catch (e) {
      setError(e?.payload?.error_key
        ? traducir.current(e.payload.error_key)
        : traducir.current("errors.request_failed", "No se pudo cargar el catálogo."));
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => { cargar(); }, [cargar]);

  const guardarFamilia = async (evento) => {
    evento.preventDefault();
    const descripcion = (formFamilia.descripcion || "").trim();
    if (!descripcion) return;

    setGuardando(true);
    setError("");
    try {
      const cuerpo = {
        product_family_description: descripcion,
        // El unico valor que la columna acepta ademas de vacio. Distingue la
        // herramienta que se presta del consumible que se gasta, que es la
        // misma division que `product.stock_purpose` hace mas abajo.
        type: formFamilia.tipo || null,
      };
      if (formFamilia.idFamilia) await updateProductFamily(formFamilia.idFamilia, cuerpo);
      else await createProductFamily(cuerpo);
      setFormFamilia(null);
      await cargar();
    } catch (e) {
      setError(e?.payload?.error_key
        ? traducir.current(e.payload.error_key)
        : traducir.current("errors.request_failed", "No se pudo guardar la familia."));
    } finally {
      setGuardando(false);
    }
  };

  const borrarFamilia = async (familia) => {
    setError("");
    try {
      await deleteProductFamily(familia.id_product_family);
      await cargar();
    } catch (e) {
      setError(e?.payload?.error_key
        ? traducir.current(e.payload.error_key)
        : traducir.current("errors.request_failed", "No se pudo eliminar la familia."));
    }
  };

  const verCaracteristicas = (id) => setConCaracteristicas((antes) => {
    const siguiente = new Set(antes);
    if (siguiente.has(id)) siguiente.delete(id); else siguiente.add(id);
    return siguiente;
  });


  return (
    <section className="page mt-page">
      <PageHeader
        eyebrow={t("material_type.eyebrow", "Inventario")}
        titulo={t("product_family.title", "Familias de producto")}
        subtitulo={t("product_family.subtitle",
              "La familia agrupa el material —desarmadores, cemento— y declara qué se le pregunta a cada uno: largo, calibre, acabado.")}
      >
        <div className="mt-cabecera-acciones">
        <button
        className="button primary"
        onClick={() => { setFormFamilia(
        formFamilia && !formFamilia.idFamilia
        ? null
        : { idFamilia: null, descripcion: "", tipo: "" }); }}
        >
        <Plus size={16} />
        {t("material_type.add_family", "Nueva familia")}
        </button>
        <button className="button" onClick={cargar} disabled={cargando}>
        <RefreshCw size={16} />
        {cargando ? t("common.loading", "Cargando…") : t("common.refresh", "Actualizar")}
        </button>
        </div>
      </PageHeader>

      {/* El alta de familia, arriba: es el nivel de arriba y sin ella no hay
          donde colgar un tipo. */}
      {formFamilia && !formFamilia.idFamilia && (
        <FormularioDeFamilia
          valor={formFamilia}
          guardando={guardando}
          onCambiar={setFormFamilia}
          onGuardar={guardarFamilia}
          onCancelar={() => setFormFamilia(null)}
          t={t}
        />
      )}

      {error && <p className="error">{error}</p>}

      {!cargando && familias.length === 0 && !formFamilia && (
        <p className="muted mt-empty">
          {t("product_family.no_families",
            "No hay familias todavía. Se empieza por la familia —«Desarmadores»— y dentro se declaran sus características: largo, calibre, punta.")}
        </p>
      )}

      <div className="mt-list">
        {familias.map((familia) => (
            <article className="mt-family" key={familia.id_product_family}>
              <header className="mt-family-head">
                <div>
                  <h2>
                    {/* El icono dice de que clase es la familia: la
                        herramienta se presta y vuelve, el consumible se gasta.
                        Es la misma division que hace `stock_purpose`. */}
                    {familia.type === "tool" ? <Hammer size={15} />
                      : familia.type === "consumable" ? <Package size={15} />
                        : <Layers size={15} />}
                    {familia.product_family_description
                      || `#${familia.id_product_family}`}
                    <button
                      className="mt-icono"
                      onClick={() => { setFormFamilia({
                        idFamilia: familia.id_product_family,
                        descripcion: familia.product_family_description || "",
                        tipo: familia.type || "",
                      }); }}
                      title={t("material_type.rename_family", "Renombrar familia")}
                      aria-label={t("material_type.rename_family", "Renombrar familia")}
                    >
                      <Pencil size={13} />
                    </button>
                    {/* Si tiene materiales dentro, el servidor lo dice con
                        `delete_has_related_records` y eso es informacion, no un
                        fallo: se muestra tal cual. */}
                    {(
                      <button
                        className="mt-icono mt-icono-borrar"
                        onClick={() => borrarFamilia(familia)}
                        title={t("material_type.delete_family", "Eliminar familia")}
                        aria-label={t("material_type.delete_family", "Eliminar familia")}
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </h2>
                </div>
                {/* El alta va aqui y no en un formulario aparte: asi la familia
                    no se elige en un desplegable, ya la eligio el clic. */}
                <div className="mt-family-acciones">
                  {/* Las caracteristicas de la familia -largo, calibre,
                      acabado-. Es el tercer nivel: la familia agrupa, el tipo
                      distingue dentro de ella, y la caracteristica es lo que
                      antes se escribia dentro de la descripcion. */}
                  <button
                    className="button button-quiet"
                    onClick={() => verCaracteristicas(String(familia.id_product_family))}
                    aria-expanded={conCaracteristicas.has(String(familia.id_product_family))}
                  >
                    {conCaracteristicas.has(String(familia.id_product_family))
                      ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
                    <Ruler size={14} />
                    {t("attribute.title", "Características")}
                  </button>
                </div>
              </header>

              {formFamilia
                && Number(formFamilia.idFamilia) === Number(familia.id_product_family) && (
                <FormularioDeFamilia
                  valor={formFamilia}
                  guardando={guardando}
                  onCambiar={setFormFamilia}
                  onGuardar={guardarFamilia}
                  onCancelar={() => setFormFamilia(null)}
                  t={t}
                />
              )}

              {conCaracteristicas.has(String(familia.id_product_family)) && (
                <FamilyAttributes idFamily={familia.id_product_family} />
              )}
            </article>
        ))}
      </div>

    </section>
  );
}

/**
 * El formulario de una familia: su nombre y de que clase es.
 *
 * `product_family.type` solo acepta `tool` o `consumable` -o nada-, y no es
 * decorativo: separa lo que se presta y vuelve de lo que se gasta. Es la misma
 * division que `product.stock_purpose` hace pieza por pieza, un nivel mas
 * arriba.
 */
function FormularioDeFamilia({ valor, guardando, onCambiar, onGuardar, onCancelar, t }) {
  return (
    <form className="mt-form mt-form-familia" onSubmit={onGuardar}>
      <input
        autoFocus
        value={valor.descripcion}
        maxLength={200}
        onChange={(e) => onCambiar({ ...valor, descripcion: e.target.value })}
        placeholder={t("material_type.family_placeholder",
          "Nombre de la familia (por ejemplo: Desarmadores)")}
        aria-label={t("material_type.family_placeholder", "Nombre de la familia")}
      />
      <select
        value={valor.tipo || ""}
        onChange={(e) => onCambiar({ ...valor, tipo: e.target.value })}
        aria-label={t("material_type.family_kind", "Clase de familia")}
      >
        <option value="">{t("material_type.kind_none", "Sin clasificar")}</option>
        <option value="tool">{t("material_type.kind_tool", "Herramienta — se presta y vuelve")}</option>
        <option value="consumable">{t("material_type.kind_consumable", "Consumible — se gasta")}</option>
      </select>
      <button className="button" type="submit"
              disabled={guardando || !valor.descripcion.trim()}>
        {guardando
          ? t("common.loading", "Guardando…")
          : valor.idFamilia ? t("common.save", "Guardar") : t("common.create", "Crear")}
      </button>
      <button className="button button-quiet" type="button" onClick={onCancelar}>
        <X size={15} />
        {t("common.cancel", "Cancelar")}
      </button>
    </form>
  );
}

FormularioDeFamilia.propTypes = {
  valor: PropTypes.shape({
    idFamilia: PropTypes.number,
    descripcion: PropTypes.string,
    tipo: PropTypes.string,
  }).isRequired,
  guardando: PropTypes.bool.isRequired,
  onCambiar: PropTypes.func.isRequired,
  onGuardar: PropTypes.func.isRequired,
  onCancelar: PropTypes.func.isRequired,
  t: PropTypes.func.isRequired,
};
