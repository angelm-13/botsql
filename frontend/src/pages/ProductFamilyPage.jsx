import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Pencil, RefreshCw, Search, Trash2,
} from "lucide-react";
import {
  createProductFamily,
  deleteProductFamily,
  getAllProductFamily,
  updateProductFamily,
} from "../api";
import FormularioPlegable from "../components/FormularioPlegable.jsx";
import PageHeader from "../components/PageHeader.jsx";
import Pagination from "../components/Pagination.jsx";
import { useI18n } from "../i18n";

/**
 * Familias de producto: cómo se agrupa el material.
 *
 * Qué quedó y qué se fue
 * ----------------------
 * Había DOS entradas de menú —«Familias de producto» y «Tipos de material»— y
 * leídas por separado parecían la misma cosa dos veces. Se juntaron en esta y
 * después el TIPO se retiró: en estos datos la descripción del material ya lo
 * trae —«BROCA HELICOIDAL 3/4», «DADO 3/16»—, así que un nivel aparte obligaba
 * a capturar dos veces lo mismo.
 *
 * También se fueron las CARACTERÍSTICAS por familia —largo, calibre, acabado—,
 * que eran un tercer nivel: la familia declaraba qué preguntar y cada material
 * lo contestaba. Es trabajo de captura que nadie estaba haciendo, y por el
 * mismo motivo que el tipo: la descripción del material ya trae el dato. Las
 * tablas siguen en la base (`material_attribute`, `material_attribute_option`,
 * `nm_material_attribute`) con sus servicios y sus pruebas; lo que se fue es la
 * pantalla.
 *
 * Qué hace la familia entonces
 * ----------------------------
 * Agrupa el material, y nada más. `material.id_product_family` es NOT NULL, así
 * que todo material cuelga de una.
 *
 * Y lleva su clase: `product_family.type` acepta `tool` o `consumable`, y
 * separa lo que se presta y vuelve de lo que se gasta. No es un invento nuestro
 * —viene del sistema anterior, donde la columna se llama
 * `familia.herramienta_consumible`: 150 familias «Maquinaria/Herramienta» y 11
 * «Consumible», ninguna vacía—. Es la misma división que
 * `product.stock_purpose` hace pieza por pieza, un nivel más arriba.
 *
 * Por qué esta pantalla se ve como las demás
 * ------------------------------------------
 * Antes era una lista de fichas con el alta metida dentro de cada una: propia,
 * y distinta de las otras veinte pantallas del almacén. Eso obliga a aprenderla
 * aparte —dónde se busca, dónde se crea, cómo se pagina— cuando hace lo mismo
 * que Marcas o Unidades. Ahora sigue el mismo orden que el resto: formulario
 * arriba, barra con buscador y cuántos ver, tabla, y la paginación compartida.
 *
 * Sin vista kanban, que es lo único del patrón que no se copia: las demás
 * agrupan sus renglones por una columna, y aquí esa columna sería el nombre de
 * la propia familia —una columna por familia, con una tarjeta dentro—. Sería
 * el patrón sin la utilidad.
 */

const CLASES = ["", "tool", "consumable"];

const formularioVacio = { descripcion: "", tipo: "" };

export default function ProductFamilyPage() {
  const { t } = useI18n();
  const [familias, setFamilias] = useState([]);
  const [paginacion, setPaginacion] = useState({ total: 0, pages: 1, perPage: 0 });
  const [pagina, setPagina] = useState(1);
  const [porPagina, setPorPagina] = useState(25);
  const [consulta, setConsulta] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);
  // `null` en `editando` es alta; un id es edición. El formulario es el mismo:
  // dos formularios para la misma tabla se desincronizan en cuanto uno cambia.
  const [editando, setEditando] = useState(null);
  const [formulario, setFormulario] = useState(formularioVacio);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError("");
    try {
      const datos = await getAllProductFamily({ page: pagina, per_page: porPagina });
      setFamilias(datos?.items || []);
      setPaginacion({
        total: datos?.total ?? 0,
        pages: datos?.pages ?? 1,
        perPage: datos?.per_page ?? porPagina,
      });
    } catch (e) {
      setError(e?.payload?.error_key || "errors.request_failed");
    } finally {
      setCargando(false);
    }
  }, [pagina, porPagina]);

  useEffect(() => { cargar(); }, [cargar]);

  // El buscador filtra lo que ya está en pantalla, igual que el resto de los
  // módulos: la paginación la resuelve el servidor.
  const filtradas = useMemo(() => {
    const aguja = consulta.trim().toLowerCase();
    if (!aguja) return familias;
    return familias.filter((f) => Object.values(f || {})
      .some((v) => String(v ?? "").toLowerCase().includes(aguja)));
  }, [familias, consulta]);

  const limpiar = () => { setEditando(null); setFormulario(formularioVacio); };

  const guardar = async (evento) => {
    evento.preventDefault();
    const descripcion = formulario.descripcion.trim();
    if (!descripcion) return;
    setGuardando(true);
    setError("");
    try {
      const cuerpo = {
        product_family_description: descripcion,
        // El único valor que la columna acepta además de vacío.
        type: formulario.tipo || null,
      };
      if (editando) await updateProductFamily(editando, cuerpo);
      else await createProductFamily(cuerpo);
      limpiar();
      await cargar();
    } catch (e) {
      setError(e?.payload?.error_key || "errors.request_failed");
    } finally {
      setGuardando(false);
    }
  };

  const editar = (familia) => {
    setEditando(familia.id_product_family);
    setFormulario({
      descripcion: familia.product_family_description || "",
      tipo: familia.type || "",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const borrar = async (familia) => {
    if (!window.confirm(t("common.confirm_delete", "¿Eliminar?"))) return;
    setError("");
    try {
      await deleteProductFamily(familia.id_product_family);
      await cargar();
    } catch (e) {
      setError(e?.payload?.error_key || "errors.request_failed");
    }
  };


  return (
    <section className="entity-page">
      <PageHeader
        eyebrow={t("product_family.eyebrow", "Inventario")}
        titulo={t("product_family.title", "Familias de producto")}
        subtitulo={t("product_family.subtitle",
          "El grupo al que pertenece cada material —desarmadores, cemento— y si es herramienta que se presta o consumible que se gasta.")}
      >
        <button className="button ghost" onClick={cargar} disabled={cargando}>
          <RefreshCw size={16} />
          {cargando ? t("common.loading", "Cargando…") : t("common.refresh", "Actualizar")}
        </button>
      </PageHeader>

      <FormularioPlegable
        titulo={editando ? t("common.edit", "Editar") : t("common.new", "Nuevo")}
        abrirSi={editando}
        onSubmit={guardar}
      >
        <div className="form-grid">
          <label className="field">
            <span>{t("fields.product_family.product_family_description", "Familia")}</span>
            <input
              type="text"
              maxLength={200}
              value={formulario.descripcion}
              onChange={(e) => setFormulario({ ...formulario, descripcion: e.target.value })}
              placeholder={t("product_family.family_placeholder",
                "Nombre de la familia (por ejemplo: Desarmadores)")}
            />
          </label>
          <label className="field">
            <span>{t("fields.product_family.type", "Clase")}</span>
            <select
              value={formulario.tipo}
              onChange={(e) => setFormulario({ ...formulario, tipo: e.target.value })}
            >
              {CLASES.map((clase) => (
                <option key={clase || "none"} value={clase}>
                  {claseEnPalabras(clase, t)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="form-actions">
          <button className="button primary" type="submit" disabled={guardando}>
            {guardando ? t("common.loading", "Cargando…") : t("common.save", "Guardar")}
          </button>
          <button className="button" type="button" onClick={limpiar}>
            {t("common.cancel", "Cancelar")}
          </button>
        </div>
      </FormularioPlegable>

      <div className="toolbar">
        <div className="search-box">
          <Search size={16} />
          <input
            value={consulta}
            onChange={(e) => setConsulta(e.target.value)}
            placeholder={t("common.search", "Buscar")}
          />
        </div>
        <select
          value={porPagina}
          onChange={(e) => { setPorPagina(Number(e.target.value)); setPagina(1); }}
        >
          {[10, 25, 50].map((cuantos) => (
            <option key={cuantos} value={cuantos}>
              {cuantos} {t("common.per_page", "por página")}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="alert error">{t(error, error)}</div>}
      {cargando && <div className="alert">{t("common.loading", "Cargando…")}</div>}

      {!cargando && filtradas.length === 0 && (
        <div className="empty">
          <strong>{t("common.empty_title", "Nada que mostrar")}</strong>
          <p>
            {t("product_family.no_families",
              "No hay familias todavía. La familia es el grupo del material: «Desarmadores», «Cemento».")}
          </p>
        </div>
      )}

      {!cargando && filtradas.length > 0 && (
        <div className="table-card">
          <table>
            <thead>
              <tr>
                <th>{t("common.actions", "Acciones")}</th>
                <th>{t("fields.product_family.id_product_family", "#")}</th>
                <th>{t("fields.product_family.product_family_description", "Familia")}</th>
                <th>{t("fields.product_family.type", "Clase")}</th>
              </tr>
            </thead>
            <tbody>
              {filtradas.map((familia) => (
                <tr key={familia.id_product_family}>
                  <td className="row-actions">
                    <button
                      type="button"
                      onClick={() => editar(familia)}
                      title={t("common.edit", "Editar")}
                    >
                      <Pencil size={15} />
                    </button>
                    <button
                      type="button"
                      onClick={() => borrar(familia)}
                      title={t("common.delete", "Eliminar")}
                    >
                      <Trash2 size={15} />
                    </button>
                  </td>
                  <td><pre className="cell-value">{familia.id_product_family}</pre></td>
                  <td>
                    <pre className="cell-value">
                      {familia.product_family_description}
                    </pre>
                  </td>
                  <td><pre className="cell-value">{claseEnPalabras(familia.type || "", t)}</pre></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Pagination
        page={pagina}
        pages={paginacion.pages}
        total={paginacion.total}
        perPage={paginacion.perPage}
        loading={cargando}
        onChange={setPagina}
      />
    </section>
  );
}

/**
 * La clase de la familia, en palabras.
 *
 * `tool` y `consumable` son los dos únicos valores que la columna acepta, y
 * enseñarlos en crudo en la tabla dejaba una columna en inglés en medio de una
 * pantalla en español.
 */
function claseEnPalabras(valor, t) {
  if (valor === "tool") {
    return t("product_family.kind_tool", "Herramienta — se presta y vuelve");
  }
  if (valor === "consumable") {
    return t("product_family.kind_consumable", "Consumible — se gasta");
  }
  return t("product_family.kind_none", "Sin clasificar");
}
