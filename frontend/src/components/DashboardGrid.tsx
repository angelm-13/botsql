/**
 * La cuadricula del tablero.
 *
 * Se usa cuando `is_dashboard` es verdadero, pero tambien para el caso de un
 * solo widget: asi hay una sola forma de dibujar una respuesta y no dos
 * caminos que se tienen que mantener iguales a mano.
 *
 * El reparto no es uniforme a proposito. Una tarjeta de KPI es un numero y
 * ocupa una columna; una grafica necesita ancho para que el eje X se lea; una
 * tabla quiere todo el ancho disponible. Darle el mismo hueco a los tres deja
 * tarjetas enormes y vacias al lado de graficas apretadas.
 */

import type { Widget } from "../types";
import { DynamicChartViewer } from "./DynamicChartViewer";
import { usarPaleta } from "../theme";

function columnasQueOcupa(w: Widget): string {
  if (!w.ok) return "md:col-span-2";
  switch (w.visualization.chart_type) {
    case "kpi_card":
      return "md:col-span-1";
    case "table":
      return "md:col-span-4";
    default:
      return "md:col-span-2";
  }
}

interface Props {
  widgets: Widget[];
  titulo?: string;
}

export function DashboardGrid({ widgets, titulo }: Props) {
  const { tokens } = usarPaleta();
  if (widgets.length === 0) return null;

  return (
    <section>
      {titulo && (
        <h2
          className="mb-3 text-base font-semibold"
          style={{ color: tokens.tintaPrimaria }}
        >
          {titulo}
        </h2>
      )}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        {widgets.map((w, i) => (
          <div key={i} className={columnasQueOcupa(w)}>
            <DynamicChartViewer widget={w} />
          </div>
        ))}
      </div>
    </section>
  );
}
