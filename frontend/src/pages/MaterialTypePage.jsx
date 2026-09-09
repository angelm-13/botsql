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
import "../styles/material-type.css";

/**
 * Familias y tipos: la clasificacion del material, en una sola pantalla.
 *
 * Por que una y no dos
 * --------------------
 * Habia dos entradas de menu, "Familias de producto" y "Tipos de material", y
 * leidas por separado parecen la misma cosa dos veces. No lo son: son los DOS
 * NIVELES de una sola clasificacion.
 *
 *     familia "Desarmadores"  ->  tipos "Plano", "De cruz"
 *     familia "Cemento"       ->  tipos "Saco", "Granel"
 *
 * `material_type.id_product_family` es lo que lo sostiene en la base: un tipo
 * cuelga de una familia y no existe suelto. "Plano" no significa nada por si
 * mismo -es un tipo DE desarmador-, y por eso una pantalla propia de tipos no
 * se puede leer: cada renglon depende de algo que no esta a la vista.
 *
 * Las tablas siguen siendo dos, y deben seguirlo siendo: fundirlas obligaria a
 * repetir el nombre de la familia en cada tipo, y renombrar "Desarmadores"
 * seria renombrarlo en cada renglon -con la mitad sin renombrar en cuanto uno
 * falle-. Lo que se junta es la PANTALLA, que es donde estaba el problema.
 *
 * Un material se define por tres cosas: su familia, su tipo y su marca.
 *
 *     familia "Desarmadores" + tipo "Plano"   + marca "Truper"
 *     familia "Desarmadores" + tipo "De cruz" + marca "Lion Tools"
 *
 * De las tres, solo el tipo no tenia donde capturarse: vivia dentro del texto
 * de la descripcion del material, asi que se podia escribir pero no agrupar, ni
 * filtrar, ni contar cuantos desarmadores planos hay.
 *
 * Por que la lista va agrupada por familia y no plana
 * ---------------------------------------------------
 * "Plano" no significa nada por si mismo: es un tipo de desarmador. Una lista
 * plana de tipos -Plano, De cruz, Saco, Rollo- no se puede leer, porque cada
 * renglon depende de una familia que no se ve. Agrupada, la pantalla dice lo
 * que el modelo dice: estos son los tipos de esta familia.
 *
 * Y el alta va dentro del grupo: el boton de agregar esta en la cabecera de
 * cada familia, asi que la familia no se elige en un desplegable -no se puede
 * equivocar- porque ya la eligio el sitio donde se hizo clic.
 */

export default function MaterialTypePage() {
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
      <header className="page-header">
        <div>
          <p className="eyebrow">{t("material_type.eyebrow", "Inventario")}</p>
          <h1>{t("material_type.title", "Familias y tipos")}</h1>
          <p className="muted">
            {t("material_type.subtitle",
              "Los dos niveles de la clasificación: la familia agrupa —desarmadores, cemento— y el tipo distingue dentro de ella —plano, de cruz, en saco, a granel—.")}
          </p>
        </div>
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
      </header>

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
          {t("material_type.no_families",
            "No hay familias todavía. El tipo cuelga de una familia, así que se empieza por la familia: «Desarmadores», y dentro «Plano» y «De cruz».")}
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


function Tipo({ tipo, t, onEditar, onBorrar }) {
  return (
    <li>
      <span>{tipo.material_type_description}</span>
      <span className="mt-acciones">
        {onEditar && (
          <button className="mt-icono" onClick={onEditar}
                  title={t("common.edit", "Editar")}
                  aria-label={t("common.edit", "Editar")}>
            <Pencil size={14} />
          </button>
        )}
        <button className="mt-icono mt-icono-borrar" onClick={onBorrar}
                title={t("common.delete", "Eliminar")}
                aria-label={t("common.delete", "Eliminar")}>
          <Trash2 size={14} />
        </button>
      </span>
    </li>
  );
}

Tipo.propTypes = {
  tipo: PropTypes.shape({
    id_material_type: PropTypes.number,
    id_product_family: PropTypes.number,
    material_type_description: PropTypes.string,
  }).isRequired,
  t: PropTypes.func.isRequired,
  onEditar: PropTypes.func,
  onBorrar: PropTypes.func.isRequired,
};
