import { useMemo, useState } from "react";
import PropTypes from "prop-types";
import {
  AlertTriangle, ArrowDown, ArrowUp, CheckCircle2, Clock, List, PackageCheck, Users,
} from "lucide-react";
import {
  RENGLONES_VISIBLES, agruparPorResponsable, anchoDeBarra,
  etiquetaDeDias, filtrarPorResponsable, gravedadDeDias, ordenarFilas, recortar, recortarGrupos,
  resumenDePrestamos, responsablesDe,
} from "../../kpi/kpiPrestamos.js";

const CAMPOS = ["articulo", "responsable", "fecha_prestamo", "dias_prestado"];

// Textos por omision (español): el Dashboard real pasa los suyos, ya traducidos, en
// `etiquetas`. Los que llevan {n}, {responsable}... se rellenan con `llenar`.
const ETIQUETAS_POR_OMISION = {
  articulo: "Artículo",
  responsable: "Responsable",
  fecha_prestamo: "Fecha del vale",
  dias_prestado: "Días prestado",
  vale_del: "vale del",
  sin_responsable: "Sin asignar",
  vacio_titulo: "Todo el material está en el almacén",
  vacio: "No hay artículos prestados sin devolver en este momento.",
  sin_resultados: "Ningún renglón de {responsable}.",
  quitar_filtro: "Ver todos los responsables",
  ordenar: "Ordenar por",
  invertir_orden: "Invertir el orden",
  filtro_responsable: "Responsable",
  todos_los_responsables: "Todos los responsables",
  vista_lista: "Lista",
  vista_agrupada: "Por responsable",
  vistas: "Vista",
  ver_todos: "Ver todos ({n})",
  ver_menos: "Ver menos",
  mostrando: "Mostrando",
  de: "de",
  renglon: "renglón",
  renglones: "renglones",
  responsable_uno: "responsable",
  responsables: "responsables",
  mas_antiguo: "el más antiguo",
  mas_renglones: "{n} más",
  nivel_ok: "Reciente",
  nivel_atencion: "Requiere atención",
  nivel_critico: "Atrasado",
  grupo_renglones: "{n} renglones",
};

const llenar = (texto, valores) => texto.replace(/\{(\w+)\}/g, (_, clave) => String(valores[clave] ?? ""));

// Cada nivel de gravedad lleva su propio icono y su propio texto: el color (verde, ambar,
// coral) NUNCA es la unica senal.
const NIVELES = {
  ok: { Icono: CheckCircle2, clave: "nivel_ok" },
  atencion: { Icono: Clock, clave: "nivel_atencion" },
  critico: { Icono: AlertTriangle, clave: "nivel_critico" },
};

function ChipDeDias({ dias, textos }) {
  const nivel = gravedadDeDias(dias);
  const { Icono, clave } = NIVELES[nivel];
  return (
    <span
      className={`kpi-prestamos-chip nivel-${nivel}`}
      title={`${textos[clave]}: ${etiquetaDeDias(dias)}`}
    >
      <Icono size={13} aria-hidden="true" />
      <span className="kpi-prestamos-chip-texto">{etiquetaDeDias(dias)}</span>
      <span className="kpi-prestamos-sr">{textos[clave]}</span>
    </span>
  );
}

ChipDeDias.propTypes = { dias: PropTypes.number.isRequired, textos: PropTypes.objectOf(PropTypes.string).isRequired };

function Renglon({ fila, maximo, textos, resaltada, onFilaClick }) {
  const nivel = gravedadDeDias(fila.dias_prestado);
  return (
    <tr
      className={`kpi-prestamos-fila nivel-${nivel} ${resaltada ? "kpi-preview-fila-resaltada" : ""}`.trim()}
      onClick={onFilaClick ? () => onFilaClick(fila) : undefined}
    >
      <td className="kpi-prestamos-articulo" data-label={textos.articulo}>{fila.articulo}</td>
      <td className="kpi-prestamos-responsable" data-label={textos.responsable}>{fila.responsable}</td>
      <td className="kpi-prestamos-fecha" data-label={textos.fecha_prestamo} data-prefijo={textos.vale_del}>{fila.fecha_prestamo}</td>
      <td className="kpi-prestamos-dias" data-label={textos.dias_prestado}>
        <ChipDeDias dias={fila.dias_prestado} textos={textos} />
        <span className="kpi-prestamos-barra" aria-hidden="true">
          <span className={`kpi-prestamos-barra-relleno nivel-${nivel}`} style={{ width: `${anchoDeBarra(fila.dias_prestado, maximo)}%` }} />
        </span>
      </td>
    </tr>
  );
}

Renglon.propTypes = {
  fila: PropTypes.shape({
    articulo: PropTypes.string, responsable: PropTypes.string, fecha_prestamo: PropTypes.string, dias_prestado: PropTypes.number,
  }).isRequired,
  maximo: PropTypes.number.isRequired,
  textos: PropTypes.objectOf(PropTypes.string).isRequired,
  resaltada: PropTypes.bool,
  onFilaClick: PropTypes.func,
};
Renglon.defaultProps = { resaltada: false, onFilaClick: null };

/** La tabla de "Material prestado ahora" (KPI en vivo).
 *
 * - Arriba, un resumen: renglones, responsables distintos y el mas antiguo.
 * - Cada renglon: articulo en negritas; debajo "responsable · vale del <fecha>"; debajo
 *   la barra de dias con su chip. La gravedad es por dias -hasta 30 verde, 31 a 90
 *   ambar, mas de 90 coral- y el chip lleva icono, texto y los dias en años y meses.
 * - Solo se ven 10 renglones hasta pulsar "Ver todos", que los muestra en una lista con
 *   scroll interno y encabezado fijo. Filtro por responsable y vista agrupada.
 * - Orden por dias (el que mas lleva, primero); se puede cambiar por columna.
 * - Responsivo por el ANCHO DE LA TARJETA (container queries, kpi-widgets.css): en una
 *   tarjeta ancha es una tabla de cuatro columnas; en una angosta, renglones compactos
 *   sin etiquetas repetidas. Sin scroll horizontal en ningun caso. */
export default function TablaWidget({
  filas, resaltarResponsable, onFilaClick, total, etiquetas,
}) {
  const textos = { ...ETIQUETAS_POR_OMISION, ...etiquetas };
  const [orden, setOrden] = useState({ campo: "dias_prestado", direccion: "desc" });
  const [responsable, setResponsable] = useState("");
  const [agrupada, setAgrupada] = useState(false);
  const [verTodos, setVerTodos] = useState(false);

  const responsables = useMemo(() => responsablesDe(filas), [filas]);
  // Si el responsable filtrado ya no esta en los datos (se devolvio todo su material),
  // el filtro se ignora en vez de dejar una tabla vacia.
  const filtro = responsables.includes(responsable) ? responsable : "";
  const filtradas = useMemo(() => filtrarPorResponsable(filas, filtro), [filas, filtro]);
  const ordenadas = useMemo(() => ordenarFilas(filtradas, orden.campo, orden.direccion), [filtradas, orden]);
  const resumen = useMemo(() => resumenDePrestamos(filtradas, filtro ? 0 : total), [filtradas, filtro, total]);
  const maximo = useMemo(() => Math.max(0, ...filtradas.map((fila) => fila.dias_prestado)), [filtradas]);

  const visibles = recortar(ordenadas, verTodos);
  const grupos = useMemo(() => (agrupada ? recortarGrupos(agruparPorResponsable(filtradas), verTodos) : []), [agrupada, filtradas, verTodos]);
  const hayMasQueElLimite = filtradas.length > RENGLONES_VISIBLES;

  function alternarOrden(campo) {
    setOrden((actual) => ({ campo, direccion: actual.campo === campo && actual.direccion === "desc" ? "asc" : "desc" }));
  }

  if (filas.length === 0) {
    return (
      <div className="kpi-prestamos-vacio">
        <PackageCheck size={30} aria-hidden="true" />
        <strong>{textos.vacio_titulo}</strong>
        <p>{textos.vacio}</p>
      </div>
    );
  }

  const plural = (n, uno, varios) => `${n} ${n === 1 ? textos[uno] : textos[varios]}`;
  const renglonesTexto = resumen.renglones > resumen.cargados
    ? `${resumen.cargados} ${textos.de} ${resumen.renglones} ${textos.renglones}`
    : plural(resumen.renglones, "renglon", "renglones");
  const cuerpo = (lista) => lista.map((fila) => (
    <Renglon
      key={fila.id}
      fila={fila}
      maximo={maximo}
      textos={textos}
      resaltada={Boolean(resaltarResponsable) && fila.responsable === resaltarResponsable}
      onFilaClick={onFilaClick}
    />
  ));
  const encabezado = (
    <thead>
      <tr>
        {CAMPOS.map((campo) => (
          <th key={campo}>
            <button type="button" className="kpi-preview-tabla-orden" onClick={() => alternarOrden(campo)}>
              {textos[campo]}
              {orden.campo === campo
                ? (orden.direccion === "desc" ? <ArrowDown size={12} aria-hidden="true" /> : <ArrowUp size={12} aria-hidden="true" />)
                : <span className="kpi-preview-tabla-orden-inactivo kpi-prestamos-orden-espacio" aria-hidden="true" />}
            </button>
          </th>
        ))}
      </tr>
    </thead>
  );

  return (
    <div className="kpi-preview-tabla-wrap kpi-prestamos">
      <p className="kpi-prestamos-resumen">
        <span><strong>{renglonesTexto}</strong></span>
        <span>{plural(resumen.responsables, "responsable_uno", "responsables")}</span>
        {resumen.masAntiguo && (
          <span className="kpi-prestamos-resumen-antiguo">
            {textos.mas_antiguo}: <ChipDeDias dias={resumen.masAntiguo.dias} textos={textos} />
          </span>
        )}
      </p>

      <div className="kpi-prestamos-controles">
        <label className="kpi-prestamos-control">
          <span>{textos.filtro_responsable}</span>
          <select value={filtro} onChange={(evento) => { setResponsable(evento.target.value); setVerTodos(false); }}>
            <option value="">{textos.todos_los_responsables} ({filas.length})</option>
            {responsables.map((nombre) => (
              <option key={nombre} value={nombre}>{nombre} ({filtrarPorResponsable(filas, nombre).length})</option>
            ))}
          </select>
        </label>
        <div className="kpi-prestamos-vistas" role="group" aria-label={textos.vistas}>
          <button type="button" aria-pressed={!agrupada} onClick={() => setAgrupada(false)}>
            <List size={14} aria-hidden="true" /> {textos.vista_lista}
          </button>
          <button type="button" aria-pressed={agrupada} onClick={() => setAgrupada(true)}>
            <Users size={14} aria-hidden="true" /> {textos.vista_agrupada}
          </button>
        </div>
        <div className="kpi-preview-orden-movil">
          <label>
            <span>{textos.ordenar}</span>
            <select value={orden.campo} onChange={(evento) => setOrden((actual) => ({ ...actual, campo: evento.target.value }))}>
              {CAMPOS.map((campo) => <option key={campo} value={campo}>{textos[campo]}</option>)}
            </select>
          </label>
          <button
            type="button"
            className="kpi-preview-tabla-orden"
            aria-label={textos.invertir_orden}
            title={textos.invertir_orden}
            onClick={() => setOrden((actual) => ({ ...actual, direccion: actual.direccion === "desc" ? "asc" : "desc" }))}
          >
            {orden.direccion === "desc" ? <ArrowDown size={14} aria-hidden="true" /> : <ArrowUp size={14} aria-hidden="true" />}
          </button>
        </div>
      </div>

      {filtradas.length === 0 && (
        <div className="kpi-prestamos-vacio">
          <p>{llenar(textos.sin_resultados, { responsable })}</p>
          <button type="button" className="button ghost" onClick={() => setResponsable("")}>{textos.quitar_filtro}</button>
        </div>
      )}

      {filtradas.length > 0 && (
        <div className={`kpi-prestamos-lista ${verTodos && hayMasQueElLimite ? "con-scroll" : ""}`}>
          {!agrupada && (
            <table className="kpi-preview-tabla kpi-prestamos-tabla">
              {encabezado}
              <tbody>{cuerpo(visibles)}</tbody>
            </table>
          )}
          {agrupada && grupos.map((grupo) => (
            <section key={grupo.responsable} className="kpi-prestamos-grupo">
              <header className="kpi-prestamos-grupo-cabecera">
                <strong>{grupo.responsable}</strong>
                <span>{llenar(textos.grupo_renglones, { n: grupo.filas.length + (grupo.ocultos || 0) })}</span>
                <ChipDeDias dias={grupo.masAntiguo} textos={textos} />
              </header>
              <table className="kpi-preview-tabla kpi-prestamos-tabla">
                <tbody>{cuerpo(grupo.filas)}</tbody>
              </table>
            </section>
          ))}
        </div>
      )}

      {hayMasQueElLimite && (
        <button type="button" className="kpi-prestamos-ver-todos" aria-expanded={verTodos} onClick={() => setVerTodos((actual) => !actual)}>
          {verTodos ? textos.ver_menos : llenar(textos.ver_todos, { n: filtradas.length })}
        </button>
      )}
      {total > filas.length && (
        <p className="kpi-preview-tabla-total">{textos.mostrando} {filas.length} {textos.de} {total}</p>
      )}
    </div>
  );
}

TablaWidget.propTypes = {
  filas: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    articulo: PropTypes.string,
    responsable: PropTypes.string,
    fecha_prestamo: PropTypes.string,
    dias_prestado: PropTypes.number,
  })).isRequired,
  resaltarResponsable: PropTypes.string,
  onFilaClick: PropTypes.func,
  // Total real en el servidor cuando `filas` es solo la primera pagina.
  total: PropTypes.number,
  etiquetas: PropTypes.objectOf(PropTypes.string),
};

TablaWidget.defaultProps = { resaltarResponsable: null, onFilaClick: null, total: 0, etiquetas: null };
