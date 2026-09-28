/**
 * Un solo numero, grande.
 *
 * Cuando la respuesta es una cifra, una grafica de barras de una sola barra no
 * comunica nada: la altura no se compara con nada. El numero suelto, con su
 * etiqueta, es la forma correcta -- y el backend ya degrada a esta tarjeta
 * cuando una consulta devuelve una fila y una columna.
 *
 * Pero "una fila" no siempre es "una columna". Una pregunta del tipo "cual
 * empleado vendio mas" trae dos: el nombre y el monto -- y el modelo elige
 * `kpi_card` igual, porque sigue siendo un solo numero destacado, con un
 * "quien" al lado. Verificado en vivo: sin mostrar esa columna extra, la
 * tarjeta decia "65,791.68" sin decir de quien, aunque el dato del nombre
 * ya venia completo en la respuesta -- se perdia en la pantalla, no en el
 * calculo. Por eso se busca aqui cualquier columna que no sea la metrica y,
 * si hay una, se muestra como el sujeto del numero.
 */

import type { Widget } from "../types";
import { formatoCompleto, usarPaleta } from "../theme";

export function KPICard({ widget }: { widget: Widget }) {
  const { tokens } = usarPaleta();
  const vis = widget.visualization;

  const columna = vis.y_axis || widget.columnas[0];
  const fila = widget.filas[0];
  const valor = fila ? fila[columna] : null;

  // La primera columna que no sea la de la metrica: "de quien" o "de que"
  // es este numero, cuando la consulta trajo esa informacion.
  const columnaDelSujeto = widget.columnas.find((c) => c !== columna);
  const sujeto = columnaDelSujeto && fila ? fila[columnaDelSujeto] : null;

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

      {sujeto !== null && sujeto !== undefined && (
        <p
          className="mt-2 truncate text-lg font-semibold"
          style={{ color: tokens.tintaPrimaria }}
          title={String(sujeto)}
        >
          {formatoCompleto(sujeto)}
        </p>
      )}

      <p
        className="mt-2 text-4xl font-semibold tabular-nums tracking-tight"
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
