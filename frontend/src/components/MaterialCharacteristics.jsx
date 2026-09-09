import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { getFamilyAttributes, getMaterialAttributes } from "../api";
import { useI18n } from "../i18n";
import "../styles/material-characteristics.css";

/**
 * Las características del material, en el alta del material.
 *
 * Por qué aquí y no en su propia pantalla
 * ---------------------------------------
 * La familia DECLARA qué se pregunta —un desarmador tiene largo y calibre— y
 * eso vive en la pantalla de familias, porque es configuración y se hace una
 * vez. Pero el VALOR —«6 pulgadas»— es del material, y el momento de
 * contestarlo es cuando se está dando de alta ese material: pedirlo en otra
 * pantalla obliga a acordarse de volver, y lo que no se contesta al capturar no
 * se contesta nunca.
 *
 * Antes ese dato se escribía dentro de la descripción —«BROCA HELICOIDAL 3/4»—,
 * así que se podía leer pero no agrupar, ni filtrar, ni contar cuántas de 3/4
 * hay.
 *
 * Los campos salen de la familia elegida
 * --------------------------------------
 * Sin familia no hay nada que preguntar, y al cambiar de familia las preguntas
 * cambian: son las de la familia nueva. Lo ya escrito se descarta a propósito
 * —un valor de «largo» de desarmadores no significa lo mismo colgando de
 * «cemento»—, y el servidor lo rechazaría de todas formas
 * (`errors.material_attribute_not_in_family`).
 */
export default function MaterialCharacteristics({
  idFamily, idMaterial, valores, onChange,
}) {
  const { t } = useI18n();
  const [campos, setCampos] = useState([]);
  const [cargando, setCargando] = useState(false);

  // Lo que la familia pregunta.
  useEffect(() => {
    let vivo = true;
    if (!idFamily) { setCampos([]); return undefined; }
    setCargando(true);
    getFamilyAttributes(idFamily)
      .then((r) => { if (vivo) setCampos(r?.items || []); })
      .catch(() => { if (vivo) setCampos([]); })
      .finally(() => { if (vivo) setCargando(false); });
    return () => { vivo = false; };
  }, [idFamily]);

  // Y lo que este material ya contestó, si no es nuevo.
  useEffect(() => {
    let vivo = true;
    if (!idMaterial) return undefined;
    getMaterialAttributes(idMaterial)
      .then((r) => {
        if (!vivo) return;
        const previos = {};
        (r?.values || []).forEach((v) => {
          previos[String(v.id_material_attribute)] = v.id_material_attribute_option
            ? String(v.id_material_attribute_option)
            : (v.value_text ?? (v.value_number ?? ""));
        });
        onChange(previos);
      })
      .catch(() => {});
    return () => { vivo = false; };
    // `onChange` cambia de identidad en cada render del padre; incluirlo aquí
    // vuelve a pedir los valores sin parar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idMaterial]);

  if (!idFamily) {
    return (
      <p className="muted caracteristicas-aviso">
        {t("attribute.pick_family_first",
          "Elige una familia y aquí aparecerán sus características.")}
      </p>
    );
  }
  if (cargando) return <p className="muted">{t("common.loading", "Cargando…")}</p>;
  if (campos.length === 0) {
    return (
      <p className="muted caracteristicas-aviso">
        {t("attribute.family_declares_none",
          "Esta familia no declara características. Se declaran una sola vez en «Familias de producto».")}
      </p>
    );
  }

  const escribir = (id, valor) => onChange({ ...valores, [String(id)]: valor });

  return (
    <div className="caracteristicas-campos">
      {campos.map((campo) => {
        const id = String(campo.id_material_attribute);
        const actual = valores[id] ?? "";
        return (
          <label className="field" key={id}>
            <span>
              {campo.attribute_name}
              {campo.unit_label ? ` (${campo.unit_label})` : ""}
              {campo.is_required ? " *" : ""}
            </span>
            {campo.data_type === "lista" ? (
              <select value={String(actual)} onChange={(e) => escribir(id, e.target.value)}>
                <option value="">{t("common.select", "Selecciona…")}</option>
                {(campo.options || []).map((o) => (
                  <option
                    key={o.id_material_attribute_option}
                    value={String(o.id_material_attribute_option)}
                  >
                    {o.option_value}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type={campo.data_type === "numero" ? "number" : "text"}
                step={campo.data_type === "numero" ? "any" : undefined}
                value={String(actual)}
                onChange={(e) => escribir(id, e.target.value)}
              />
            )}
          </label>
        );
      })}
    </div>
  );
}

MaterialCharacteristics.propTypes = {
  idFamily: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  idMaterial: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  valores: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
};

MaterialCharacteristics.defaultProps = {
  idFamily: "",
  idMaterial: null,
};
