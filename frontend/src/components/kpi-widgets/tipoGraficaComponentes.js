import NumeroWidget from "./NumeroWidget";
import BarrasWidget from "./BarrasWidget";
import TablaWidget from "./TablaWidget";
import DonaWidget from "./DonaWidget";

/** El mapa tipo_grafica -> componente que pide la tarea, para que un tipo
 * nuevo sea un archivo nuevo y una entrada aqui, no mas líneas en el
 * componente que arma la cuadrícula. "linea"/"area" quedan pendientes de su
 * propio componente -- ningún KPI de Adser los usa en el tablero fijo de
 * este preview; se agregan en Paso 3 con el mismo patrón. */
const TIPO_GRAFICA_COMPONENTE = {
  numero: NumeroWidget,
  barras: BarrasWidget,
  tabla: TablaWidget,
  dona: DonaWidget,
};

export default TIPO_GRAFICA_COMPONENTE;
