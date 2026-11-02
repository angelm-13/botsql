// Pinta DonaWidget y BarrasWidget en servidor con la grafica de tamano fijo (ver graficasAnchoFijo.shim.jsx).
import { renderToStaticMarkup } from "react-dom/server";
import DonaWidget from "../components/kpi-widgets/DonaWidget.jsx";
import BarrasWidget from "../components/kpi-widgets/BarrasWidget.jsx";

export const pintarDona = (props) => renderToStaticMarkup(<DonaWidget animar={false} {...props} />);
export const pintarBarras = (props) => renderToStaticMarkup(<BarrasWidget animar={false} {...props} />);
