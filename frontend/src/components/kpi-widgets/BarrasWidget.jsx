import { useId, useState } from "react";
import PropTypes from "prop-types";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { patronesDeRelleno } from "./patronesDeRelleno";
import { rellenoConPatron } from "../../kpi/kpiAccesibilidad";
import {
  ANCHO_GRAFICA_POR_OMISION, ANGULO_ETIQUETA, disenoDeBarras, recortarEtiqueta,
} from "../../kpi/kpiEtiquetasEje";

// Hasta cuantas barras llevan cada una su propio patron; con mas, todas la misma textura fina.
export const MAXIMO_DE_PATRONES_DISTINTOS = 6;

export function TooltipRico({ active, payload, label, series }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="kpi-preview-tooltip">
      <strong>{label}</strong>
      {payload.map((entrada) => {
        // Cada serie puede traer su propio formato (unidades distintas en un
        // mismo grafico); sin `formatear` se muestra el valor crudo.
        const formatear = series.find((serie) => serie.clave === entrada.dataKey)?.formatear;
        return (
          <div key={entrada.dataKey} className="kpi-preview-tooltip-fila">
            <span className="kpi-preview-tooltip-dot" style={{ background: entrada.color }} />
            <span>{entrada.name}</span>
            <strong>{formatear ? formatear(entrada.value) : entrada.value}</strong>
          </div>
        );
      })}
    </div>
  );
}

TooltipRico.propTypes = {
  active: PropTypes.bool,
  payload: PropTypes.arrayOf(PropTypes.object),
  label: PropTypes.string,
  series: PropTypes.arrayOf(PropTypes.object),
};
TooltipRico.defaultProps = { active: false, payload: null, label: "", series: [] };

/** Recharts ya trae animacion de dibujo (`isAnimationActive`) -- no hace
 * falta ninguna libreria de animacion aparte para "la grafica se dibuja al
 * aparecer". `onBarClick` es opcional: lo usa el widget de empleados para
 * resaltar la tabla de material prestado (interaccion entre widgets). */
export default function BarrasWidget({
  datos, series, campoEtiqueta, animar, onBarClick, barraResaltada, colorPorFila,
  conPatrones, formatearEje, anchoEje, descripcion, porPeriodo, textoRecorte, etiquetasCortas, soloEnteros, orientacion,
}) {
  const idBase = useId().replace(/:/g, "");
  // Ancho real de la grafica: las etiquetas solo se inclinan cuando no caben rectas (ver kpiEtiquetasEje).
  const [anchoGrafica, setAnchoGrafica] = useState(ANCHO_GRAFICA_POR_OMISION);
  // Cuantas categorias caben y como (ver kpiEtiquetasEje): muchas pasan a horizontal, con varias series se corta a 12.
  // En una grafica por persona el eje rotula el nombre corto; `datos`, el tooltip y la descripcion conservan el completo.
  const rotulo = (nombre) => etiquetasCortas?.[nombre] ?? nombre;
  const diseno = disenoDeBarras({
    etiquetas: datos.map((fila) => rotulo(String(fila[campoEtiqueta] ?? ""))), cantidadSeries: series.length, porPeriodo, anchoEje, anchoGrafica, orientacion,
  });
  const visibles = datos.slice(0, diseno.mostradas);
  const horizontal = diseno.modo === "horizontal";
  // Con categorias de color fijo (rojo/verde...) cada barra lleva ademas un patron: el color no es la unica senal.
  const coloresDeFila = conPatrones && colorPorFila ? visibles.map((fila) => colorPorFila(fila)) : null;
  // Con pocas categorias cada barra lleva un patron distinto; con muchas, UNA textura fina para todas (ver patronesDeRelleno).
  const texturaFina = visibles.length > MAXIMO_DE_PATRONES_DISTINTOS;
  // Las barras se dibujan UNA vez. Recharts las vuelve a animar cada vez que le llega un `datos` nuevo
  // (aqui se recalcula en cada render de la tarjeta), y con un filtro entre tarjetas eso hacia que las
  // barras "crecieran" de nuevo a cada clic.
  const [yaAnimo, setYaAnimo] = useState(false);
  const marcaDeEje = { fontSize: 11, fill: "var(--kpi-texto-suave)" };
  // Un conteo no tiene marcas con decimales: el eje numerico solo marca enteros y arranca en 0 (el tope lo redondea Recharts: 0, 25, 50, 75, no el maximo exacto).
  const ejeNumerico = soloEnteros ? { allowDecimals: false, domain: [0, "auto"] } : {};
  const recortar = (valor) => recortarEtiqueta(rotulo(valor), diseno.maxCaracteres);
  return (
    <>
      <div role={descripcion ? "img" : undefined} aria-label={descripcion || undefined} title={descripcion || undefined}>
        <ResponsiveContainer
          width="100%" height={diseno.alto}
          onResize={(ancho) => { if (ancho > 0) setAnchoGrafica((previo) => (Math.abs(previo - ancho) >= 2 ? Math.round(ancho) : previo)); }}
        >
          <BarChart
            data={visibles}
            layout={horizontal ? "vertical" : "horizontal"}
            margin={horizontal ? { top: 4, right: 16, left: 0, bottom: 0 } : { top: 4, right: 8, left: diseno.margenIzquierdo, bottom: 0 }}
          >
            {coloresDeFila && <defs>{patronesDeRelleno(idBase, coloresDeFila, { fino: texturaFina })}</defs>}
            <CartesianGrid strokeDasharray="2 4" stroke="var(--kpi-grid)" vertical={horizontal} horizontal={!horizontal} />
            {horizontal ? (
              <>
                <XAxis type="number" tick={marcaDeEje} axisLine={false} tickLine={false} tickFormatter={formatearEje || undefined} {...ejeNumerico} />
                <YAxis
                  type="category" dataKey={campoEtiqueta} width={diseno.anchoEjeCategorias} interval={0}
                  tick={marcaDeEje} axisLine={false} tickLine={false} tickFormatter={recortar}
                />
              </>
            ) : (
              <>
                <XAxis
                  dataKey={campoEtiqueta} tick={marcaDeEje} axisLine={false} tickLine={false} tickFormatter={recortar}
                  interval={diseno.todasLasEtiquetas ? 0 : undefined} height={diseno.altoEjeX}
                  angle={diseno.inclinar ? ANGULO_ETIQUETA : 0} textAnchor={diseno.inclinar ? "end" : "middle"}
                />
                <YAxis tick={marcaDeEje} axisLine={false} tickLine={false} tickFormatter={formatearEje || undefined} width={anchoEje} {...ejeNumerico} />
              </>
            )}
            <Tooltip content={<TooltipRico series={series} />} cursor={{ fill: "var(--kpi-hover-barra)" }} />
            {series.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
            {series.map((serie) => (
              <Bar
                key={serie.clave}
                dataKey={serie.clave}
                name={serie.nombre}
                fill={serie.color}
                radius={horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]}
                isAnimationActive={animar && !yaAnimo}
                animationDuration={700}
                onAnimationEnd={() => setYaAnimo(true)}
                cursor={onBarClick ? "pointer" : "default"}
                onClick={onBarClick}
              >
                {visibles.map((fila, indice) => (
                  <Cell
                    key={fila.id ?? fila[campoEtiqueta]}
                    fill={coloresDeFila ? rellenoConPatron(idBase, indice) : (colorPorFila ? colorPorFila(fila) : serie.color)}
                    fillOpacity={barraResaltada && fila[campoEtiqueta] !== barraResaltada ? 0.35 : (serie.opacidad ?? 1)}
                  />
                ))}
              </Bar>
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      {diseno.recortado && <p className="kpi-barras-recorte">{textoRecorte(diseno.mostradas, diseno.total)}</p>}
    </>
  );
}

BarrasWidget.propTypes = {
  datos: PropTypes.arrayOf(PropTypes.object).isRequired,
  series: PropTypes.arrayOf(PropTypes.shape({
    clave: PropTypes.string.isRequired,
    nombre: PropTypes.string.isRequired,
    color: PropTypes.string.isRequired,
    opacidad: PropTypes.number,
    formatear: PropTypes.func,
  })).isRequired,
  campoEtiqueta: PropTypes.string.isRequired,
  animar: PropTypes.bool,
  onBarClick: PropTypes.func,
  barraResaltada: PropTypes.string,
  // fila -> color: para categorias fijas (estado), donde cada barra lleva SU
  // color en vez del de la serie.
  colorPorFila: PropTypes.func,
  // Agrega un patron por barra a las categorias de color fijo (segundo canal ademas del color).
  conPatrones: PropTypes.bool,
  // Marcas del eje Y con la unidad; sin ella, el numero crudo de siempre.
  formatearEje: PropTypes.func,
  anchoEje: PropTypes.number,
  // Lo que lee un lector de pantalla (y el tooltip del navegador) en lugar de una imagen sin nombre.
  descripcion: PropTypes.string,
  // El eje son fechas (agrupado por periodo): no se recorta ni pasa a horizontal.
  porPeriodo: PropTypes.bool,
  // (mostradas, total) -> "Mostrando 12 de 30"; lo pone la pantalla para poder traducirlo.
  textoRecorte: PropTypes.func,
  // nombre completo -> nombre corto, solo para rotular el eje (grafica por persona).
  etiquetasCortas: PropTypes.objectOf(PropTypes.string),
  // El eje numerico marca solo enteros (la unidad es un conteo).
  soloEnteros: PropTypes.bool,
  // "auto" (por omision: horizontal desde 13 categorias de una serie), "horizontal" o "vertical" (la elige el usuario por widget).
  orientacion: PropTypes.oneOf(["auto", "horizontal", "vertical"]),
};

BarrasWidget.defaultProps = {
  animar: true, onBarClick: null, barraResaltada: null, colorPorFila: null,
  conPatrones: false, formatearEje: null, anchoEje: 60, descripcion: "", porPeriodo: false, etiquetasCortas: null, soloEnteros: false, orientacion: "auto",
  textoRecorte: (mostradas, total) => `Mostrando ${mostradas} de ${total}`,
};
