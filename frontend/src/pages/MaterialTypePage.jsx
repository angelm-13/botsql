import React, { useCallback, useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import { Layers, Pencil, Plus, RefreshCw, Trash2, X } from "lucide-react";
import {
  createMaterialType,
  deleteMaterialType,
  getAllMaterialType,
  getAllProductFamily,
  updateMaterialType,
} from "../api";
import { useI18n } from "../i18n";
import "../styles/material-type.css";

/**
 * Tipos de material, agrupados por su familia.
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
          <h1>{t("material_type.title", "Tipos de material")}</h1>
          <p className="muted">
            {t("material_type.subtitle",
              "El tipo dentro de cada familia: un desarmador es plano o de cruz, un cemento viene en saco o a granel.")}
          </p>
        </div>
        <button className="button" onClick={cargar} disabled={cargando}>
          <RefreshCw size={16} />
          {cargando ? t("common.loading", "Cargando…") : t("common.refresh", "Actualizar")}
        </button>
      </header>

      {error && <p className="error">{error}</p>}

      {!cargando && familias.length === 0 && (
        <p className="muted mt-empty">
          {t("material_type.no_families",
            "No hay familias de producto todavía. El tipo cuelga de una familia, así que primero hay que crear la familia.")}
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
                    <Layers size={15} />
                    {familia.product_family_description
                      || `#${familia.id_product_family}`}
                  </h2>
                  <span className="muted">
                    {propios.length === 1
                      ? t("material_type.one_type", "1 tipo")
                      : `${propios.length} ${t("material_type.types", "tipos")}`}
                  </span>
                </div>
                {/* El alta va aqui y no en un formulario aparte: asi la familia
                    no se elige en un desplegable, ya la eligio el clic. */}
                <button
                  className="button button-quiet"
                  onClick={() => setFormulario(
                    abierto && !formulario.idTipo
                      ? null
                      : { idFamilia: familia.id_product_family, idTipo: null, descripcion: "" })}
                >
                  <Plus size={15} />
                  {t("material_type.add", "Agregar tipo")}
                </button>
              </header>

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
