/**
 * Un solo numero, grande.
 *
 * Cuando la respuesta es una cifra, una grafica de barras de una sola barra no
 * comunica nada: la altura no se compara con nada. El numero suelto, con su
 * etiqueta, es la forma correcta -- y el backend ya degrada a esta tarjeta
 * cuando una consulta devuelve una fila y una columna.
 */

import type { Widget } from "../types";
import { formatoCompleto, usarPaleta } from "../theme";

export function KPICard({ widget }: { widget: Widget }) {
  const { tokens } = usarPaleta();
  const vis = widget.visualization;

  const columna = vis.y_axis || widget.columnas[0];
  const fila = widget.filas[0];
  const valor = fila ? fila[columna] : null;

  return (
    <figure
      className="flex h-full flex-col justify-between rounded-xl border p-5"
      style={{ borderColor: tokens.borde, backgroundColor: tokens.superficie }}
    >
      <figcaption
        className="text-sm font-medium"
        style={{ color: tokens.tintaSecundaria }}
      >
        {vis.title || vis.metric_label || columna}
      </figcaption>

      <p
        className="mt-4 text-4xl font-semibold tabular-nums tracking-tight"
        style={{ color: tokens.tintaPrimaria }}
      >
        {formatoCompleto(valor)}
      </p>

      {vis.metric_label && vis.metric_label !== vis.title && (
        <p className="mt-1 text-xs" style={{ color: tokens.tintaTenue }}>
          {vis.metric_label}
        </p>
      )}
    </figure>
  );
}
