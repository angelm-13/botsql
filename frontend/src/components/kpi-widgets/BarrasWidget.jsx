import { useId, useState } from "react";
import PropTypes from "prop-types";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { DefinicionDePatrones } from "./PatronesSvg";
import { rellenoConPatron } from "../../kpi/kpiAccesibilidad";

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
  conPatrones, formatearEje, anchoEje, descripcion,
}) {
  const idBase = useId().replace(/:/g, "");
  // Con categorias de color fijo (rojo/verde...) cada barra lleva ademas un patron: el color no es la unica senal.
  const coloresDeFila = conPatrones && colorPorFila ? datos.map((fila) => colorPorFila(fila)) : null;
  // Las barras se dibujan UNA vez. Recharts las vuelve a animar cada vez que le llega un `datos` nuevo
  // (aqui se recalcula en cada render de la tarjeta), y con un filtro entre tarjetas eso hacia que las
  // barras "crecieran" de nuevo a cada clic.
  const [yaAnimo, setYaAnimo] = useState(false);
  return (
    <div role={descripcion ? "img" : undefined} aria-label={descripcion || undefined} title={descripcion || undefined}>
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={datos} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
        {coloresDeFila && <DefinicionDePatrones idBase={idBase} colores={coloresDeFila} />}
        <CartesianGrid strokeDasharray="3 3" stroke="var(--kpi-grid)" vertical={false} />
        <XAxis dataKey={campoEtiqueta} tick={{ fontSize: 11, fill: "var(--kpi-texto-suave)" }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: "var(--kpi-texto-suave)" }} axisLine={false} tickLine={false} tickFormatter={formatearEje || undefined} width={anchoEje} />
        <Tooltip content={<TooltipRico series={series} />} cursor={{ fill: "var(--kpi-hover-barra)" }} />
        {series.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
        {series.map((serie) => (
          <Bar
            key={serie.clave}
            dataKey={serie.clave}
            name={serie.nombre}
            fill={serie.color}
            radius={[4, 4, 0, 0]}
            isAnimationActive={animar && !yaAnimo}
            animationDuration={700}
            onAnimationEnd={() => setYaAnimo(true)}
            cursor={onBarClick ? "pointer" : "default"}
            onClick={onBarClick}
          >
            {datos.map((fila, indice) => (
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
};

BarrasWidget.defaultProps = {
  animar: true, onBarClick: null, barraResaltada: null, colorPorFila: null,
  conPatrones: false, formatearEje: null, anchoEje: 60, descripcion: "",
};
