import { useCallback, useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  AlertTriangle, Hash, List, Plus, Ruler, Trash2, Type, X,
} from "lucide-react";
import {
  addMaterialAttributeOption,
  createMaterialAttribute,
  deleteMaterialAttribute,
  deleteMaterialAttributeOption,
  getFamilyAttributes,
} from "../api";
import { useI18n } from "../i18n";

/**
 * Las características que una familia declara.
 *
 * Por qué vive dentro de la familia
 * ---------------------------------
 * «Largo» no significa nada por sí mismo: es el largo DE un desarmador. Una
 * pantalla propia de características tendría que empezar preguntando de qué
 * familia son, y esa pregunta ya la contestó el sitio donde se hizo clic.
 *
 * Es el mismo criterio que el tipo de material, y por el mismo motivo: en el
 * menú, dos entradas para los niveles de una sola clasificación se leen como dos
 * módulos que hacen lo mismo.
 *
 * Qué resuelve
 * ------------
 * Con familia, tipo y marca se llega hasta «desarmador Truper plano». El resto
 * -el largo, el mango, el calibre, los litros- se escribía dentro de la
 * descripción, así que se podía leer y no se podía usar: nada de agrupar,
 * filtrar, ni contestar «cuántos de 6 pulgadas tengo».
 */

const TIPOS = [
  { valor: "texto", clave: "type_text", texto: "Texto", icono: Type,
    ayuda: "Lo que no se puede acotar de antemano." },
  { valor: "numero", clave: "type_number", texto: "Número", icono: Hash,
    ayuda: "Se guarda como número, así que «de 6 o más» compara de verdad." },
  { valor: "lista", clave: "type_list", texto: "Lista", icono: List,
    ayuda: "Solo los valores que declares. Evita «mate», «Mate» y «MATE»." },
];

const ICONO_DE_TIPO = {
  texto: Type,
  numero: Hash,
  lista: List,
};

export default function FamilyAttributes({ idFamily, canWrite }) {
  const { t } = useI18n();
  const [atributos, setAtributos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [borrador, setBorrador] = useState(null);
  const [guardando, setGuardando] = useState(false);
  // El valor que se está agregando a una lista ya declarada, por característica.
  const [nuevaOpcion, setNuevaOpcion] = useState({});

  // `t` cambia de identidad en cada render; si entra en las dependencias del
  // efecto la pantalla se repide sin parar.
  const traducir = useRef(t);
  traducir.current = t;

  const cargar = useCallback(async () => {
    setCargando(true);
    setError("");
    try {
      const r = await getFamilyAttributes(idFamily);
      setAtributos(r?.items || []);
    } catch (e) {
      setError(e?.payload?.error_key
        ? traducir.current(e.payload.error_key)
        : traducir.current("errors.request_failed",
          "No se pudieron cargar las características."));
    } finally {
      setCargando(false);
    }
  }, [idFamily]);

  useEffect(() => { cargar(); }, [cargar]);

  const decirError = (e, porOmision) => setError(
    e?.payload?.error_key
      ? traducir.current(e.payload.error_key)
      : traducir.current("errors.request_failed", porOmision));

  const declarar = async (evento) => {
    evento.preventDefault();
    const nombre = (borrador.attribute_name || "").trim();
    if (!nombre) return;
    setGuardando(true);
    setError("");
    try {
      await createMaterialAttribute({
        id_product_family: idFamily,
        attribute_name: nombre,
        data_type: borrador.data_type,
        unit_label: borrador.unit_label || undefined,
        is_required: borrador.is_required,
        // Las opciones se mandan solo en la lista: en los otros tipos el
        // servidor las rechaza, y con razón.
        options: borrador.data_type === "lista"
          ? borrador.options.split(",").map((x) => x.trim()).filter(Boolean)
          : undefined,
      });
      setBorrador(null);
      await cargar();
    } catch (e) {
      decirError(e, "No se pudo declarar la característica.");
    } finally {
      setGuardando(false);
    }
  };

  const retirar = async (atributo) => {
    setError("");
    try {
      await deleteMaterialAttribute(atributo.id_material_attribute);
      await cargar();
    } catch (e) {
      decirError(e, "No se pudo retirar la característica.");
    }
  };

  const agregarOpcion = async (atributo) => {
    const valor = (nuevaOpcion[atributo.id_material_attribute] || "").trim();
    if (!valor) return;
    setError("");
    try {
      await addMaterialAttributeOption(atributo.id_material_attribute,
        { option_value: valor });
      setNuevaOpcion({ ...nuevaOpcion, [atributo.id_material_attribute]: "" });
      await cargar();
    } catch (e) {
      decirError(e, "No se pudo agregar el valor.");
    }
  };

  const quitarOpcion = async (idOpcion) => {
    setError("");
    try {
      await deleteMaterialAttributeOption(idOpcion);
      await cargar();
    } catch (e) {
      decirError(e, "No se pudo quitar el valor.");
    }
  };

  const nuevo = () => setBorrador({
    attribute_name: "",
    data_type: "texto",
    unit_label: "",
    is_required: false,
    options: "",
  });

  return (
    <div className="mt-caracteristicas">
      <header>
        <h4>
          <Ruler size={14} />
          {t("attribute.title", "Características")}
          {atributos.length > 0 && <em>{atributos.length}</em>}
        </h4>
        {canWrite && !borrador && (
          <button className="button button-quiet" onClick={nuevo}>
            <Plus size={14} />
            {t("attribute.add", "Agregar característica")}
          </button>
        )}
      </header>

      {error && <p className="error">{error}</p>}

      {!cargando && atributos.length === 0 && !borrador && (
        <p className="muted mt-sin-tipos">
          {t("attribute.none_yet",
            "Sin características. El tamaño, el calibre o el acabado se quedan escritos dentro de la descripción, donde no se pueden filtrar ni contar.")}
        </p>
      )}

      {borrador && (
        <form className="mt-form mt-form-atributo" onSubmit={declarar}>
          <input
            autoFocus
            value={borrador.attribute_name}
            maxLength={80}
            onChange={(e) => setBorrador({ ...borrador, attribute_name: e.target.value })}
            placeholder={t("attribute.name_placeholder",
              "Nombre (por ejemplo: Largo)")}
            aria-label={t("attribute.name_placeholder", "Nombre de la característica")}
          />

          {/* El tipo se elige como botones y no en un desplegable porque cada
              uno cambia lo que se puede preguntar después, y eso hay que verlo
              al elegir: el número compara, la lista acota, el texto no hace ni
              lo uno ni lo otro. Y no se puede cambiar después. */}
          <div className="mt-tipos" role="group"
               aria-label={t("attribute.data_type", "Tipo de dato")}>
            {TIPOS.map(({ valor, clave, texto, icono: Icono, ayuda }) => (
              <button
                key={valor}
                type="button"
                className={`mt-tipo ${borrador.data_type === valor ? "activo" : ""}`}
                onClick={() => setBorrador({ ...borrador, data_type: valor })}
                title={t(`attribute.${clave}_help`, ayuda)}
              >
                <Icono size={13} />
                {t(`attribute.${clave}`, texto)}
              </button>
            ))}
          </div>

          {borrador.data_type === "numero" && (
            <input
              value={borrador.unit_label}
              maxLength={20}
              onChange={(e) => setBorrador({ ...borrador, unit_label: e.target.value })}
              placeholder={t("attribute.unit_placeholder", "Unidad (in, mm, L)")}
              aria-label={t("attribute.unit_placeholder", "Unidad")}
            />
          )}

          {borrador.data_type === "lista" && (
            <input
              value={borrador.options}
              onChange={(e) => setBorrador({ ...borrador, options: e.target.value })}
              placeholder={t("attribute.options_placeholder",
                "Valores permitidos, separados por comas: Goma, Plástico")}
              aria-label={t("attribute.options_placeholder", "Valores permitidos")}
            />
          )}

          <label className="mt-obligatoria">
            <input
              type="checkbox"
              checked={borrador.is_required}
              onChange={(e) => setBorrador({ ...borrador, is_required: e.target.checked })}
            />
            {t("attribute.required", "Obligatoria")}
          </label>

          <button className="button" type="submit"
                  disabled={guardando || !borrador.attribute_name.trim()
                    || (borrador.data_type === "lista" && !borrador.options.trim())}>
            {guardando ? t("common.loading", "Guardando…") : t("common.create", "Crear")}
          </button>
          <button className="button button-quiet" type="button"
                  onClick={() => setBorrador(null)}>
            <X size={15} />
            {t("common.cancel", "Cancelar")}
          </button>

          {/* El tipo no se cambia después, así que se dice al elegirlo y no
              cuando el servidor lo rechace. */}
          <p className="inv-ruta-ayuda mt-aviso-tipo">
            <AlertTriangle size={12} />
            {t("attribute.type_is_fixed",
              "El tipo de dato no se cambia después: los valores ya capturados quedarían en la forma del tipo viejo.")}
          </p>
        </form>
      )}

      {atributos.length > 0 && (
        <ul className="mt-atributos">
          {atributos.map((atributo) => {
            const Icono = ICONO_DE_TIPO[atributo.data_type] || Type;
            return (
              <li key={atributo.id_material_attribute}>
                <span className="mt-atributo-nombre">
                  <Icono size={13} />
                  {atributo.attribute_name}
                  {atributo.unit_label && <em>({atributo.unit_label})</em>}
                  {atributo.is_required && (
                    <strong className="mt-obligatoria-marca"
                            title={t("attribute.required", "Obligatoria")}>*</strong>
                  )}
                </span>

                {atributo.data_type === "lista" && (
                  <span className="mt-opciones">
                    {atributo.options.map((opcion) => (
                      <span className="mt-opcion" key={opcion.id_material_attribute_option}>
                        {opcion.option_value}
                        {canWrite && (
                          <button
                            className="mt-opcion-quitar"
                            onClick={() => quitarOpcion(opcion.id_material_attribute_option)}
                            title={t("common.delete", "Eliminar")}
                            aria-label={`${t("common.delete", "Eliminar")} ${opcion.option_value}`}
                          >
                            <X size={11} />
                          </button>
                        )}
                      </span>
                    ))}
                    {canWrite && (
                      <span className="mt-opcion-nueva">
                        <input
                          value={nuevaOpcion[atributo.id_material_attribute] || ""}
                          maxLength={120}
                          placeholder={t("attribute.new_option", "otro valor")}
                          aria-label={t("attribute.new_option", "Agregar valor")}
                          onChange={(e) => setNuevaOpcion({
                            ...nuevaOpcion,
                            [atributo.id_material_attribute]: e.target.value,
                          })}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              agregarOpcion(atributo);
                            }
                          }}
                        />
                      </span>
                    )}
                  </span>
                )}

                {/* Cuántos materiales la usan. Va aquí porque es lo que hace
                    falta para decidir si se puede retirar: «usada por 14» es una
                    respuesta, «no se pudo eliminar» no. */}
                <span className="muted mt-usos">
                  {atributo.materials_using_it === 0
                    ? t("attribute.unused", "sin usar")
                    : `${atributo.materials_using_it} ${t("attribute.in_use", "materiales")}`}
                </span>

                {canWrite && atributo.materials_using_it === 0 && (
                  <button className="mt-icono mt-icono-borrar"
                          onClick={() => retirar(atributo)}
                          title={t("common.delete", "Eliminar")}
                          aria-label={`${t("common.delete", "Eliminar")} ${atributo.attribute_name}`}>
                    <Trash2 size={13} />
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

FamilyAttributes.propTypes = {
  idFamily: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
  canWrite: PropTypes.bool,
};

FamilyAttributes.defaultProps = {
  canWrite: true,
};
