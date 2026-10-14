import { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { Boxes, Check, Hash, Search } from "lucide-react";
import { CATEGORICAL, colorEfectivoDeKpi, unidadInfo } from "../../kpi/kpiDatos.js";
import { normalizarBusqueda } from "../../kpi/kpiDatos.js";
import {
  agruparKpis, colorDeModulo, estadoDeOpcion, grupoInicial, resumenDeModulos,
} from "../../kpi/kpiSelector.js";

const TEXTOS_POR_OMISION = {
  buscar: "Buscar KPI…",
  sinResultados: "Ningún KPI coincide con la búsqueda.",
  variables: "Variables",
  variablesAyuda: "Sin desglose: sirven para combinar en un mismo gráfico.",
  elegirColor: "Elegir color",
  ejemplo: "Ejemplo",
  motivoSinPermiso: "No disponible para tu rol.",
  motivoModulo: "Módulo no habilitado.",
  modulos: "Módulos",
  elegidosEnModulo: "elegidos en este módulo",
};

/** El selector de KPI del editor: una fila de botones de modulo y, debajo, la lista
 * de los KPIs del modulo elegido, con un buscador que recorre todos.
 *
 * - Los botones (icono, nombre y cuantos KPIs tiene) usan el estilo de los de tipo
 *   de grafica. Las variables sueltas son un boton mas. Con un solo modulo en el
 *   catalogo no hay botones; un modulo sin KPIs visibles -por plan o permiso- no
 *   llega en el catalogo y por lo tanto no tiene boton.
 * - Abre en el modulo del primer KPI ya elegido, o en el primero de la lista. Los
 *   KPIs elegidos se conservan al cambiar de modulo: cada boton avisa cuantos de
 *   los suyos estan elegidos.
 * - Con texto en el buscador se muestran los resultados de TODOS los modulos,
 *   agrupados por modulo; elegir un boton de modulo borra la busqueda.
 *
 * Cada opcion muestra nombre, unidad y descripcion. Al combinar varios KPIs
 * (`multiple`), los que no se pueden sumar a los ya elegidos -otra unidad, u
 * otra clase de KPI- salen DESHABILITADOS y con un tooltip que dice por que
 * (`textoDeBloqueo`); el tooltip va en la fila entera porque un boton
 * deshabilitado no siempre lo muestra. El color por KPI, cuando se combinan
 * varios, se elige aqui mismo con un circulo junto al KPI elegido. */
export default function SelectorDeKpi({
  catalogo, seleccionados, multiple, onAlternar, metaDeModulo, textoDeBloqueo,
  coloresKpi, onElegirColor, textos, busquedaInicial, moduloInicial,
}) {
  const t = { ...TEXTOS_POR_OMISION, ...textos };
  const [busqueda, setBusqueda] = useState(busquedaInicial);
  const [colorAbierto, setColorAbierto] = useState(null);
  const hayBusqueda = normalizarBusqueda(busqueda) !== "";
  const resumen = useMemo(() => resumenDeModulos(catalogo, busqueda, seleccionados), [catalogo, busqueda, seleccionados]);
  // El modulo en el que se abre solo se calcula una vez; despues manda la persona.
  const [moduloElegido, setModuloElegido] = useState(
    () => moduloInicial || grupoInicial(agruparKpis(catalogo), catalogo, seleccionados),
  );
  // Si el modulo elegido dejo de existir en el catalogo, se cae al primero.
  const moduloActivo = resumen.some((modulo) => modulo.clave === moduloElegido) ? moduloElegido : resumen[0]?.clave;
  const grupos = useMemo(() => {
    const todos = agruparKpis(catalogo, hayBusqueda ? busqueda : "");
    return hayBusqueda ? todos : todos.filter((grupo) => grupo.clave === moduloActivo);
  }, [catalogo, busqueda, hayBusqueda, moduloActivo]);
  const hayFilaDeModulos = resumen.length > 1;
  const metaDe = (modulo) => (modulo.esVariables ? { icon: Hash, label: t.variables } : metaDeModulo(modulo.modulo));

  // El popover de color se cierra al hacer clic fuera de el, no solo al elegir.
  useEffect(() => {
    if (!colorAbierto) return undefined;
    function alHacerClic(evento) {
      if (!evento.target.closest(".kpi-color-swatch-wrap")) setColorAbierto(null);
    }
    document.addEventListener("mousedown", alHacerClic);
    return () => document.removeEventListener("mousedown", alHacerClic);
  }, [colorAbierto]);

  return (
    <div className="kpi-selector">
      <div className="kpi-editor-buscador">
        <Search size={15} aria-hidden="true" />
        <input
          type="search"
          placeholder={t.buscar}
          aria-label={t.buscar}
          value={busqueda}
          onChange={(evento) => setBusqueda(evento.target.value)}
        />
      </div>

      {hayFilaDeModulos && (
        <div className="kpi-icon-option-group kpi-selector-modulos" role="group" aria-label={t.modulos}>
          {resumen.map((modulo) => {
            const meta = metaDe(modulo);
            const Icono = meta.icon || Boxes;
            const activo = !hayBusqueda && modulo.clave === moduloActivo;
            const sinCoincidencias = hayBusqueda && modulo.coincidencias === 0;
            return (
              <button
                type="button"
                key={modulo.clave}
                className={`kpi-icon-option ${activo ? "active" : ""}`}
                style={{ "--tinte": colorDeModulo(modulo.clave) }}
                aria-pressed={activo}
                data-modulo={modulo.clave}
                disabled={sinCoincidencias}
                onClick={() => { setBusqueda(""); setModuloElegido(modulo.clave); }}
              >
                {modulo.elegidos > 0 && (
                  <span
                    className="kpi-selector-modulo-elegidos"
                    title={`${modulo.elegidos} ${t.elegidosEnModulo}`}
                  >
                    {modulo.elegidos}
                  </span>
                )}
                <Icono size={20} aria-hidden="true" />
                <span className="kpi-selector-modulo-etiqueta">
                  {meta.label}
                  <em className="kpi-selector-modulo-cuenta">{hayBusqueda ? modulo.coincidencias : modulo.total}</em>
                </span>
                {activo && <Check size={13} className="kpi-editor-tipo-check" aria-hidden="true" />}
              </button>
            );
          })}
        </div>
      )}

      {grupos.length === 0 && <p className="kpi-selector-vacio">{t.sinResultados}</p>}

      {grupos.map((grupo) => {
        const meta = grupo.esVariables ? { icon: Hash, label: t.variables } : metaDeModulo(grupo.modulo);
        const IconoGrupo = meta.icon || Boxes;
        return (
          <div key={grupo.clave} className="kpi-editor-grupo-modulo kpi-selector-grupo" data-grupo={grupo.clave}>
            {(hayBusqueda || !hayFilaDeModulos) && (
              <p className="kpi-editor-grupo-titulo">
                <IconoGrupo size={14} aria-hidden="true" /> {meta.label}
                <span className="kpi-selector-cuenta">{grupo.kpis.length}</span>
              </p>
            )}
            {grupo.esVariables && <p className="kpi-selector-ayuda">{t.variablesAyuda}</p>}
            <div className="kpi-editor-kpi-lista">
              {grupo.kpis.map((kpi) => {
                const id = String(kpi.id_kpi_definition);
                const { elegida, motivo } = estadoDeOpcion({ kpi, seleccionados, catalogo, multiple });
                const bloqueo = motivo ? textoDeBloqueo(kpi, motivo) : undefined;
                const posicion = seleccionados.indexOf(id);
                const color = colorEfectivoDeKpi(id, coloresKpi);
                return (
                  <div
                    key={id}
                    className={`kpi-selector-fila ${motivo ? "bloqueada" : ""}`}
                    title={bloqueo}
                  >
                    <button
                      type="button"
                      className={`kpi-editor-kpi-opcion ${elegida ? "activo" : ""}`}
                      aria-pressed={elegida}
                      disabled={Boolean(motivo)}
                      onClick={() => onAlternar(id)}
                    >
                      <span className="kpi-editor-kpi-nombre">
                        {multiple && elegida && <span className="kpi-chip-badge">{posicion + 1}</span>}
                        {kpi.etiqueta || kpi.clave}
                        {kpi.esEjemplo && (
                          <span
                            className="kpi-editor-kpi-ejemplo"
                            title={kpi.motivo === "modulo_no_habilitado" ? t.motivoModulo : t.motivoSinPermiso}
                          >
                            {t.ejemplo}
                          </span>
                        )}
                        {elegida && <Check size={13} className="kpi-selector-check" aria-hidden="true" />}
                      </span>
                      <span className="kpi-editor-kpi-unidad">{unidadInfo(kpi.unidad).etiquetaSelector}</span>
                      {kpi.descripcion && <span className="kpi-editor-kpi-descripcion">{kpi.descripcion}</span>}
                    </button>
                    {multiple && elegida && onElegirColor && (
                      <div className="kpi-color-swatch-wrap">
                        <button
                          type="button"
                          className="kpi-color-swatch"
                          style={{ background: color }}
                          title={t.elegirColor}
                          aria-label={t.elegirColor}
                          aria-expanded={colorAbierto === id}
                          onClick={() => setColorAbierto((actual) => (actual === id ? null : id))}
                        />
                        {colorAbierto === id && (
                          <div className="kpi-color-popover" role="menu">
                            {CATEGORICAL.map((opcion) => (
                              <button
                                type="button"
                                key={opcion}
                                className={`kpi-color-option ${color === opcion ? "active" : ""}`}
                                style={{ background: opcion }}
                                aria-label={opcion}
                                role="menuitemradio"
                                aria-checked={color === opcion}
                                onClick={() => { onElegirColor(id, opcion); setColorAbierto(null); }}
                              />
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

SelectorDeKpi.propTypes = {
  catalogo: PropTypes.arrayOf(PropTypes.object).isRequired,
  // ids (string) de los KPIs elegidos, en el orden en que se eligieron
  seleccionados: PropTypes.arrayOf(PropTypes.string).isRequired,
  // true: varios KPIs por grafico (barras, linea, area); false: uno solo
  multiple: PropTypes.bool,
  onAlternar: PropTypes.func.isRequired,
  // modulo -> { icon, label }
  metaDeModulo: PropTypes.func.isRequired,
  // (kpi, motivo) -> texto del tooltip de una opcion bloqueada
  textoDeBloqueo: PropTypes.func,
  coloresKpi: PropTypes.objectOf(PropTypes.string),
  onElegirColor: PropTypes.func,
  textos: PropTypes.objectOf(PropTypes.string),
  busquedaInicial: PropTypes.string,
  // Clave del modulo con el que abre (solo para pruebas): por omision, el del primer
  // KPI ya elegido o el primero de la lista.
  moduloInicial: PropTypes.string,
};

SelectorDeKpi.defaultProps = {
  multiple: false,
  textoDeBloqueo: () => "No se puede combinar con los KPIs ya elegidos.",
  coloresKpi: {},
  onElegirColor: null,
  textos: null,
  busquedaInicial: "",
  moduloInicial: null,
};
