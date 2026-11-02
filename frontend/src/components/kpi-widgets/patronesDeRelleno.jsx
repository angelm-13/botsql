import { patronDeIndice } from "../../kpi/kpiAccesibilidad";

// Los trazos de cada patron, sobre el color de la categoria. El relleno sigue siendo el color de siempre: el trazo
// (blanco, semitransparente) es el segundo canal para quien no distingue rojo de verde.
const TRAZO = { stroke: "#fff", strokeOpacity: 0.85, strokeWidth: 1.6 };
function trazos(patron) {
  switch (patron) {
    case "diagonal": return <path d="M-1,9 l2,-2 M0,8 l8,-8 M7,9 l2,-2" {...TRAZO} />;
    case "diagonal_inversa": return <path d="M-1,-1 l2,2 M0,0 l8,8 M7,-1 l2,2" {...TRAZO} />;
    case "horizontal": return <path d="M0,2 h8 M0,6 h8" {...TRAZO} />;
    case "vertical": return <path d="M2,0 v8 M6,0 v8" {...TRAZO} />;
    case "cruz": return <path d="M4,0 v8 M0,4 h8" {...TRAZO} />;
    default: return <circle cx="4" cy="4" r="1.4" fill="#fff" fillOpacity="0.85" />;
  }
}

/** Los `<pattern>` de un patron por categoria, SIN envolver en `<defs>`. El id de cada uno es `${idBase}-${indice}`.
 *
 * Es una funcion y no un componente a proposito: Recharts solo conserva un `<defs>` escrito como hijo directo de la
 * grafica, y descarta un componente que lo devuelva. Quien la usa pone el `<defs>` literal:
 * `<defs>{patronesDeRelleno(idBase, colores)}</defs>`. Sin eso el `fill="url(#id)"` apunta a un patron que no existe y
 * la marca no se dibuja. */
export function patronesDeRelleno(idBase, colores) {
  return colores.map((color, indice) => (
    <pattern key={`${idBase}-${color}-${indice}`} id={`${idBase}-${indice}`} width="8" height="8" patternUnits="userSpaceOnUse">
      <rect width="8" height="8" fill={color} />
      {trazos(patronDeIndice(indice))}
    </pattern>
  ));
}
