import NumeroWidget from "./NumeroWidget";
import BarrasWidget from "./BarrasWidget";
import LineaAreaWidget from "./LineaAreaWidget";
import TablaWidget from "./TablaWidget";
import DonaWidget from "./DonaWidget";

/** El mapa tipo_grafica -> componente. Un tipo nuevo es un archivo nuevo y
 * una entrada aqui, no mas líneas en el componente que arma la cuadrícula
 * (Dashboard.jsx lo consulta para pintar cada tarjeta). "linea" y "area"
 * comparten componente: solo cambia si se rellena debajo del trazo. */
const TIPO_GRAFICA_COMPONENTE = {
  numero: NumeroWidget,
  barras: BarrasWidget,
  linea: LineaAreaWidget,
  area: LineaAreaWidget,
  tabla: TablaWidget,
  dona: DonaWidget,
};

export default TIPO_GRAFICA_COMPONENTE;
