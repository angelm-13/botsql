import { useMemo, useState } from "react";
import PropTypes from "prop-types";
import { Boxes, Check, Hash, Search } from "lucide-react";
import { CATEGORICAL, colorEfectivoDeKpi, unidadInfo } from "../../kpi/kpiDatos.js";
import { agruparKpis, estadoDeOpcion } from "../../kpi/kpiSelector.js";

const TEXTOS_POR_OMISION = {
  buscar: "Buscar KPI…",
  sinResultados: "Ningún KPI coincide con la búsqueda.",
  variables: "Variables",
  variablesAyuda: "Sin desglose: sirven para combinar en un mismo gráfico.",
  elegirColor: "Elegir color",
};

/** El selector de KPI del editor: una sola lista con buscador, agrupada por
 * modulo, con las variables sueltas como un grupo mas.
 *
 * Cada opcion muestra nombre, unidad y descripcion. Al combinar varios KPIs
 * (`multiple`), los que no se pueden sumar a los ya elegidos -otra unidad, u
 * otra clase de KPI- salen DESHABILITADOS y con un tooltip que dice por que
 * (`textoDeBloqueo`); el tooltip va en la fila entera porque un boton
 * deshabilitado no siempre lo muestra. El color por KPI, cuando se combinan
 * varios, se elige aqui mismo con un circulo junto al KPI elegido. */
export default function SelectorDeKpi({
  catalogo, seleccionados, multiple, onAlternar, metaDeModulo, textoDeBloqueo,
  coloresKpi, onElegirColor, textos, busquedaInicial,
}) {
  const t = { ...TEXTOS_POR_OMISION, ...textos };
  const [busqueda, setBusqueda] = useState(busquedaInicial);
  const [colorAbierto, setColorAbierto] = useState(null);
  const grupos = useMemo(() => agruparKpis(catalogo, busqueda), [catalogo, busqueda]);

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

      {grupos.length === 0 && <p className="kpi-selector-vacio">{t.sinResultados}</p>}

      {grupos.map((grupo) => {
        const meta = grupo.esVariables ? { icon: Hash, label: t.variables } : metaDeModulo(grupo.modulo);
        const IconoGrupo = meta.icon || Boxes;
        return (
          <div key={grupo.clave} className="kpi-editor-grupo-modulo kpi-selector-grupo" data-grupo={grupo.clave}>
            <p className="kpi-editor-grupo-titulo">
              <IconoGrupo size={14} aria-hidden="true" /> {meta.label}
              <span className="kpi-selector-cuenta">{grupo.kpis.length}</span>
            </p>
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
};

SelectorDeKpi.defaultProps = {
  multiple: false,
  textoDeBloqueo: () => "No se puede combinar con los KPIs ya elegidos.",
  coloresKpi: {},
  onElegirColor: null,
  textos: null,
  busquedaInicial: "",
};
