import { useMemo, useState } from "react";
import PropTypes from "prop-types";
import { AlertTriangle, ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";

const UMBRAL_ATRASADO_DIAS = 14;

const CAMPOS = ["articulo", "responsable", "fecha_prestamo", "dias_prestado"];

// Textos por omision (español): el Dashboard real pasa los suyos, ya
// traducidos, en `etiquetas`.
const ETIQUETAS_POR_OMISION = {
  articulo: "Artículo",
  responsable: "Responsable",
  fecha_prestamo: "Fecha del vale",
  dias_prestado: "Días prestado",
  dias: "días",
  vacio: "No hay artículos prestados sin devolver en este momento.",
  ordenar: "Ordenar por",
  invertir_orden: "Invertir el orden",
  mostrando: "Mostrando",
  de: "de",
};

/** El acento ambar (`--kpi-atrasado`) es SOLO para lo atrasado, y nunca es la
 * unica senal: siempre lo acompana el icono de alerta y el texto "días".
 *
 * Responsivo por el ANCHO DE LA TARJETA, no de la ventana (container queries,
 * ver kpi-widgets.css): la misma tabla en una tarjeta angosta de una ventana
 * enorme y en una ventana angosta se ve igual -tarjeta por renglon, sin scroll
 * horizontal-. En ese modo desaparece la cabecera, asi que el orden se elige
 * con un selector propio. */
export default function TablaWidget({
  filas, resaltarResponsable, onFilaClick, total, umbralDias, etiquetas,
}) {
  const textos = { ...ETIQUETAS_POR_OMISION, ...etiquetas };
  const [orden, setOrden] = useState({ campo: "dias_prestado", direccion: "desc" });

  const filasOrdenadas = useMemo(() => {
    const copia = [...filas];
    copia.sort((a, b) => {
      const valorA = a[orden.campo];
      const valorB = b[orden.campo];
      const comparacion = typeof valorA === "number"
        ? valorA - valorB
        : String(valorA).localeCompare(String(valorB));
      return orden.direccion === "asc" ? comparacion : -comparacion;
    });
    return copia;
  }, [filas, orden]);

  function alternarOrden(campo) {
    setOrden((actual) => ({
      campo,
      direccion: actual.campo === campo && actual.direccion === "desc" ? "asc" : "desc",
    }));
  }

  if (filas.length === 0) return <p className="kpi-empty-inline">{textos.vacio}</p>;

  return (
    <div className="kpi-preview-tabla-wrap">
      <div className="kpi-preview-orden-movil">
        <label>
          <span>{textos.ordenar}</span>
          <select value={orden.campo} onChange={(evento) => setOrden((actual) => ({ ...actual, campo: evento.target.value }))}>
            {CAMPOS.map((campo) => <option key={campo} value={campo}>{textos[campo]}</option>)}
          </select>
        </label>
        <button
          type="button"
          className="kpi-preview-tabla-orden"
          aria-label={textos.invertir_orden}
          title={textos.invertir_orden}
          onClick={() => setOrden((actual) => ({ ...actual, direccion: actual.direccion === "desc" ? "asc" : "desc" }))}
        >
          {orden.direccion === "desc" ? <ArrowDown size={14} aria-hidden="true" /> : <ArrowUp size={14} aria-hidden="true" />}
        </button>
      </div>
      <table className="kpi-preview-tabla">
        <thead>
          <tr>
            {CAMPOS.map((campo) => (
              <th key={campo}>
                <button type="button" className="kpi-preview-tabla-orden" onClick={() => alternarOrden(campo)}>
                  {textos[campo]}
                  {orden.campo === campo ? (
                    orden.direccion === "desc" ? <ArrowDown size={12} aria-hidden="true" /> : <ArrowUp size={12} aria-hidden="true" />
                  ) : (
                    <ArrowUpDown size={12} className="kpi-preview-tabla-orden-inactivo" aria-hidden="true" />
                  )}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filasOrdenadas.map((fila) => {
            const atrasado = fila.dias_prestado >= umbralDias;
            const resaltada = resaltarResponsable && fila.responsable === resaltarResponsable;
            return (
              <tr
                key={fila.id}
                className={`${atrasado ? "kpi-preview-fila-atrasada" : ""} ${resaltada ? "kpi-preview-fila-resaltada" : ""}`.trim()}
                onClick={onFilaClick ? () => onFilaClick(fila) : undefined}
              >
                <td data-label={textos.articulo}>{fila.articulo}</td>
                <td data-label={textos.responsable}>{fila.responsable}</td>
                <td data-label={textos.fecha_prestamo}>{fila.fecha_prestamo}</td>
                <td data-label={textos.dias_prestado}>
                  <div className="kpi-preview-dias-celda">
                    {atrasado && <AlertTriangle size={13} className="kpi-preview-icono-atrasado" aria-hidden="true" />}
                    <span>{fila.dias_prestado} {textos.dias}</span>
                    <div className="kpi-preview-barra-progreso">
                      <div
                        className={`kpi-preview-barra-progreso-relleno ${atrasado ? "atrasado" : ""}`}
                        style={{ width: `${Math.min(100, (fila.dias_prestado / umbralDias) * 100)}%` }}
                      />
                    </div>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {total > filas.length && (
        <p className="kpi-preview-tabla-total">{textos.mostrando} {filas.length} {textos.de} {total}</p>
      )}
    </div>
  );
}

TablaWidget.propTypes = {
  filas: PropTypes.arrayOf(PropTypes.object).isRequired,
  resaltarResponsable: PropTypes.string,
  onFilaClick: PropTypes.func,
  // Total real en el servidor cuando `filas` es solo la primera pagina.
  total: PropTypes.number,
  umbralDias: PropTypes.number,
  etiquetas: PropTypes.objectOf(PropTypes.string),
};

TablaWidget.defaultProps = {
  resaltarResponsable: null, onFilaClick: null, total: 0, umbralDias: UMBRAL_ATRASADO_DIAS, etiquetas: null,
};
