/**
 * La tabla. Es a la vez un tipo de visualizacion y la red de seguridad de
 * todos los demas.
 *
 * Cumple dos papeles:
 *
 *  * `chart_type: "table"` cuando el resultado es un detalle y no una medida.
 *  * La "via de relieve" de cualquier grafica: tres de los tonos de la paleta
 *    quedan por debajo de 3:1 contra la superficie clara, y la regla dice que
 *    en ese caso la identidad no puede depender solo del color. Por eso toda
 *    grafica trae esta tabla a un clic.
 */

import type { Fila } from "../types";
import { formatoCompleto, usarPaleta } from "../theme";

interface Props {
  columnas: string[];
  filas: Fila[];
  maxAlto?: string;
}

export function DataTable({ columnas, filas, maxAlto = "20rem" }: Props) {
  const { tokens } = usarPaleta();

  if (filas.length === 0) {
    return (
      <p className="py-8 text-center text-sm" style={{ color: tokens.tintaTenue }}>
        La consulta no devolvio filas.
      </p>
    );
  }

  return (
    <div className="overflow-auto rounded-lg border" style={{ borderColor: tokens.borde, maxHeight: maxAlto }}>
      <table className="w-full border-collapse text-sm">
        <thead className="sticky top-0" style={{ backgroundColor: tokens.superficie }}>
          <tr>
            {columnas.map((c) => (
              <th
                key={c}
                scope="col"
                className="whitespace-nowrap border-b px-3 py-2 text-left font-medium"
                style={{ borderColor: tokens.borde, color: tokens.tintaSecundaria }}
              >
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filas.map((fila, i) => (
            <tr key={i} style={{ borderTop: i === 0 ? undefined : `1px solid ${tokens.rejilla}` }}>
              {columnas.map((c) => {
                const v = fila[c];
                const esNumero = typeof v === "number";
                return (
                  <td
                    key={c}
                    className={`px-3 py-1.5 ${esNumero ? "text-right tabular-nums" : "text-left"}`}
                    style={{ color: tokens.tintaPrimaria }}
                  >
                    {formatoCompleto(v)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
