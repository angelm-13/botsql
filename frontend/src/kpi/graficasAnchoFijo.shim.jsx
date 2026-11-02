// Solo para pruebas (ver patronesDeRelleno.test.mjs): reemplaza el ResponsiveContainer de Recharts por uno de tamano fijo.
// El real mide 0 sin navegador y no dibuja la grafica, asi que una prueba en servidor no veria ninguna marca.
import { cloneElement } from "react";

export {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, Tooltip, XAxis, YAxis,
} from "recharts";

export function ResponsiveContainer({ children, height }) {
  return cloneElement(children, { width: 420, height: typeof height === "number" ? height : 220 });
}
