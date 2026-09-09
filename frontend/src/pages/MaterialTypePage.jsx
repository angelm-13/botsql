import { useCallback, useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  ChevronDown, ChevronRight, Hammer, Layers, Package, Pencil, Plus, RefreshCw,
  Ruler, Trash2, X,
} from "lucide-react";
import {
  createMaterialType,
  createProductFamily,
  deleteMaterialType,
  deleteProductFamily,
  getAllMaterialType,
  getAllProductFamily,
  updateMaterialType,
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
  const [tipos, setTipos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  // El formulario abierto: { idFamilia, idTipo, descripcion }. `idTipo` nulo
  // significa alta; con valor, edicion.
  const [formulario, setFormulario] = useState(null);
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
      const [respFamilias, respTipos] = await Promise.all([
        getAllProductFamily({ per_page: 200 }),
        getAllMaterialType({ per_page: 500 }),
      ]);
      setFamilias(respFamilias?.items || []);
      setTipos(respTipos?.items || []);
    } catch (e) {
      setError(e?.payload?.error_key
        ? traducir.current(e.payload.error_key)
        : traducir.current("errors.request_failed", "No se pudo cargar el catálogo."));
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => { cargar(); }, [cargar]);

  const guardar = async (evento) => {
    evento.preventDefault();
    const descripcion = (formulario.descripcion || "").trim();
    if (!descripcion) return;

    setGuardando(true);
    setError("");
    try {
      const cuerpo = {
        id_product_family: formulario.idFamilia,
        material_type_description: descripcion,
      };
      if (formulario.idTipo) await updateMaterialType(formulario.idTipo, cuerpo);
      else await createMaterialType(cuerpo);
      setFormulario(null);
      await cargar();
    } catch (e) {
      // El error del servidor dice cual es el tipo repetido; se muestra tal
      // cual en vez de "no se pudo guardar", que no dice que corregir.
      setError(e?.payload?.error_key
        ? traducir.current(e.payload.error_key)
        : traducir.current("errors.request_failed", "No se pudo guardar."));
    } finally {
      setGuardando(false);
    }
  };

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
    // Borrar la familia dejaria sus tipos colgando de algo que ya no esta, y
    // esos tipos siguen puestos en materiales. Se avisa antes en lugar de
    // dejar que el servidor conteste `delete_has_related_records` a secas.
    const propios = porFamilia(familia.id_product_family);
    if (propios.length > 0) {
      setError(traducir.current(
        "material_type.family_has_types",
        "Esa familia tiene tipos dentro. Quita primero los tipos: si no, quedarían apuntando a una familia que ya no existe."));
      return;
    }
    try {
      await deleteProductFamily(familia.id_product_family);
      await cargar();
    } catch (e) {
      setError(e?.payload?.error_key
        ? traducir.current(e.payload.error_key)
        : traducir.current("errors.request_failed", "No se pudo eliminar la familia."));
    }
  };

  const borrar = async (tipo) => {
    setError("");
    try {
      await deleteMaterialType(tipo.id_material_type);
      await cargar();
    } catch (e) {
      // El caso normal: hay materiales usando ese tipo. El servidor lo dice
      // con `delete_has_related_records` y eso es informacion, no un fallo.
      setError(e?.payload?.error_key
        ? traducir.current(e.payload.error_key)
        : traducir.current("errors.request_failed", "No se pudo eliminar."));
    }
  };

  const verCaracteristicas = (id) => setConCaracteristicas((antes) => {
    const siguiente = new Set(antes);
    if (siguiente.has(id)) siguiente.delete(id); else siguiente.add(id);
    return siguiente;
  });

  const porFamilia = (idFamilia) => tipos
    .filter((x) => Number(x.id_product_family) === Number(idFamilia))
    .sort((a, b) => String(a.material_type_description || "")
      .localeCompare(String(b.material_type_description || "")));

  // Tipos cuya familia ya no esta en la lista. No deberia pasar, pero si pasa
  // hay que verlos: un tipo invisible sigue apareciendo en los materiales.
  const idsDeFamilias = new Set(familias.map((f) => Number(f.id_product_family)));
  const huerfanos = tipos.filter((x) => !idsDeFamilias.has(Number(x.id_product_family)));

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
            onClick={() => { setFormulario(null); setFormFamilia(
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
        {familias.map((familia) => {
          const propios = porFamilia(familia.id_product_family);
          const abierto = formulario
            && Number(formulario.idFamilia) === Number(familia.id_product_family);

          return (
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
                      onClick={() => { setFormulario(null); setFormFamilia({
                        idFamilia: familia.id_product_family,
                        descripcion: familia.product_family_description || "",
                        tipo: familia.type || "",
                      }); }}
                      title={t("material_type.rename_family", "Renombrar familia")}
                      aria-label={t("material_type.rename_family", "Renombrar familia")}
                    >
                      <Pencil size={13} />
                    </button>
                    {/* Solo si esta vacia. Con tipos dentro, borrarla los
                        dejaria apuntando a una familia que ya no existe. */}
                    {propios.length === 0 && (
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
                  <span className="muted">
                    {propios.length === 1
                      ? t("material_type.one_type", "1 tipo")
                      : `${propios.length} ${t("material_type.types", "tipos")}`}
                  </span>
                </div>
                {/* El alta va aqui y no en un formulario aparte: asi la familia
                    no se elige en un desplegable, ya la eligio el clic. */}
                <div className="mt-family-acciones">
                  <button
                    className="button button-quiet"
                    onClick={() => { setFormFamilia(null); setFormulario(
                      abierto && !formulario.idTipo
                        ? null
                        : { idFamilia: familia.id_product_family, idTipo: null, descripcion: "" }); }}
                  >
                    <Plus size={15} />
                    {t("material_type.add", "Agregar tipo")}
                  </button>
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

              {abierto && (
                <form className="mt-form" onSubmit={guardar}>
                  <input
                    autoFocus
                    value={formulario.descripcion}
                    maxLength={120}
                    onChange={(e) => setFormulario(
                      { ...formulario, descripcion: e.target.value })}
                    placeholder={t("material_type.placeholder",
                      "Nombre del tipo (por ejemplo: Plano)")}
                    aria-label={t("material_type.placeholder", "Nombre del tipo")}
                  />
                  <button className="button" type="submit"
                          disabled={guardando || !formulario.descripcion.trim()}>
                    {guardando
                      ? t("common.loading", "Guardando…")
                      : formulario.idTipo
                        ? t("common.save", "Guardar")
                        : t("common.create", "Crear")}
                  </button>
                  <button className="button button-quiet" type="button"
                          onClick={() => setFormulario(null)}>
                    <X size={15} />
                    {t("common.cancel", "Cancelar")}
                  </button>
                </form>
              )}

              {propios.length === 0 ? (
                <p className="muted mt-sin-tipos">
                  {t("material_type.none_yet",
                    "Sin tipos. Los materiales de esta familia se quedan sin distinguir entre sí.")}
                </p>
              ) : (
                <ul className="mt-types">
                  {propios.map((tipo) => (
                    <Tipo
                      key={tipo.id_material_type}
                      tipo={tipo}
                      t={t}
                      onEditar={() => setFormulario({
                        idFamilia: tipo.id_product_family,
                        idTipo: tipo.id_material_type,
                        descripcion: tipo.material_type_description || "",
                      })}
                      onBorrar={() => borrar(tipo)}
                    />
                  ))}
                </ul>
              )}
              {conCaracteristicas.has(String(familia.id_product_family)) && (
                <FamilyAttributes idFamily={familia.id_product_family} />
              )}
            </article>
          );
        })}
      </div>

      {huerfanos.length > 0 && (
        <article className="mt-family mt-orphans">
          <header className="mt-family-head">
            <div>
              <h2>{t("material_type.orphans", "Tipos sin familia visible")}</h2>
              <span className="muted">
                {t("material_type.orphans_hint",
                  "Su familia no aparece en la lista. Siguen apareciendo en los materiales que los usan.")}
              </span>
            </div>
          </header>
          <ul className="mt-types">
            {huerfanos.map((tipo) => (
              <Tipo key={tipo.id_material_type} tipo={tipo} t={t}
                    onBorrar={() => borrar(tipo)} />
            ))}
          </ul>
        </article>
      )}
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
