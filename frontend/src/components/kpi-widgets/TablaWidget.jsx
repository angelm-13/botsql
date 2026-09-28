import { useMemo, useState } from "react";
import PropTypes from "prop-types";
import { ArrowDown, ArrowUp, ArrowUpDown, TriangleAlert } from "lucide-react";

const UMBRAL_ATRASADO_DIAS = 14;

const COLUMNAS = [
  { campo: "articulo", etiqueta: "Artículo" },
  { campo: "responsable", etiqueta: "Responsable" },
  { campo: "fecha_prestamo", etiqueta: "Fecha del vale" },
  { campo: "dias_prestado", etiqueta: "Días prestado" },
];

/** El acento cobre (`--kpi-atrasado`) es SOLO para lo atrasado, y nunca es la
 * unica senal: siempre lo acompana el icono de alerta y el texto "días". */
export default function TablaWidget({ filas, resaltarResponsable, onFilaClick }) {
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

  const maximoDias = Math.max(...filas.map((fila) => fila.dias_prestado), 1);

  return (
    <div className="kpi-preview-tabla-wrap">
      <table className="kpi-preview-tabla">
        <thead>
          <tr>
            {COLUMNAS.map((columna) => (
              <th key={columna.campo}>
                <button type="button" className="kpi-preview-tabla-orden" onClick={() => alternarOrden(columna.campo)}>
                  {columna.etiqueta}
                  {orden.campo === columna.campo ? (
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
            const atrasado = fila.dias_prestado >= UMBRAL_ATRASADO_DIAS;
            const resaltada = resaltarResponsable && fila.responsable === resaltarResponsable;
            return (
              <tr
                key={fila.id}
                className={`${atrasado ? "kpi-preview-fila-atrasada" : ""} ${resaltada ? "kpi-preview-fila-resaltada" : ""}`.trim()}
                onClick={onFilaClick ? () => onFilaClick(fila) : undefined}
              >
                <td>{fila.articulo}</td>
                <td>{fila.responsable}</td>
                <td>{fila.fecha_prestamo}</td>
                <td>
                  <div className="kpi-preview-dias-celda">
                    {atrasado && <TriangleAlert size={13} className="kpi-preview-icono-atrasado" aria-hidden="true" />}
                    <span>{fila.dias_prestado} días</span>
                    <div className="kpi-preview-barra-progreso">
                      <div
                        className={`kpi-preview-barra-progreso-relleno ${atrasado ? "atrasado" : ""}`}
                        style={{ width: `${Math.min(100, (fila.dias_prestado / maximoDias) * 100)}%` }}
                      />
                    </div>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

TablaWidget.propTypes = {
  filas: PropTypes.arrayOf(PropTypes.object).isRequired,
  resaltarResponsable: PropTypes.string,
  onFilaClick: PropTypes.func,
};

TablaWidget.defaultProps = { resaltarResponsable: null, onFilaClick: null };
