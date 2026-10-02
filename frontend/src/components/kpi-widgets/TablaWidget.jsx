import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import PropTypes from "prop-types";
import {
  AlertTriangle, ArrowDown, ArrowUp, CheckCircle2, Clock, List, PackageCheck, Search, Users, X,
} from "lucide-react";
import {
  RENGLONES_VISIBLES, agruparPorResponsable, anchoDeBarra, buscarEnFilas, escalaDeBarras,
  etiquetaDeDias, filtrarPorResponsable, filtrarPorUsuario, gravedadDeDias, ordenarFilas, recortar,
  recortarGrupos, resumenDePrestamos, responsablesDe,
} from "../../kpi/kpiPrestamos.js";
import {
  TAMANO_PAGINA_PANEL, TAMANO_PAGINA_TARJETA, agruparContiguos, opcionesDeResponsables, resumenDeServidor,
  totalDeResponsables,
} from "../../kpi/kpiPrestamosServidor.js";
import { filasTablaPrestamo } from "../../kpi/kpiAdaptadores.js";
import useTablaServidor from "./useTablaServidor.js";

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
  cerrar: "Cerrar",
  panel_titulo: "Material prestado ahora",
  buscar: "Buscar",
  buscar_pista: "Artículo, responsable, fecha…",
  sin_coincidencias: "Ningún renglón coincide con la búsqueda.",
  limpiar_busqueda: "Limpiar la búsqueda",
  filtrando: "Filtrando",
  quitar_filtro_externo: "Quitar el filtro",
  sin_prestamos_de: "{responsable} no tiene material prestado.",
  mostrando: "Mostrando",
  de: "de",
  renglon: "renglón",
  renglones: "renglones",
  responsable_uno: "responsable",
  responsables: "responsables",
  mas_antiguo: "el más antiguo",
  mas_renglones: "{n} más",
  cargando: "Cargando…",
  cargando_mas: "Cargando más…",
  mostrar_mas: "Mostrar más",
  error_carga: "No se pudo cargar la lista.",
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

/** Contenido de la tabla de "Material prestado ahora" (KPI en vivo). Lo usan la tarjeta del
 * tablero (`enPanel` falso) y el panel "Ver todos" (`enPanel`), cada uno con su propio estado
 * de filtro, orden y busqueda.
 *
 * - Arriba, un resumen: renglones, responsables distintos y el mas antiguo.
 * - Cada renglon: articulo en negritas; debajo "responsable · vale del <fecha>"; debajo
 *   la barra de dias con su chip. La gravedad es por dias -hasta 30 verde, 31 a 90
 *   ambar, mas de 90 coral- y el chip lleva icono, texto y los dias en años y meses.
 *   La barra se dibuja contra el renglon mas antiguo (nunca menos de 365 dias).
 * - En la tarjeta se ven 10 renglones y el resto queda tras "Ver todos", que abre el panel
 *   con la lista completa (busqueda, responsable, orden) sin agrandar la tarjeta. La lista
 *   se desplaza por dentro con el encabezado fijo.
 * - Orden por dias (el que mas lleva, primero); se puede cambiar por columna.
 * - Responsivo por el ANCHO DEL CONTENEDOR (container queries, kpi-widgets.css): ancho es
 *   una tabla de cuatro columnas; angosto, renglones compactos sin etiquetas repetidas. */
function ContenidoPrestamos({
  filas, resaltarResponsable, onFilaClick, total, textos, filtroExterno, onQuitarFiltroExterno, enPanel, onVerTodos,
  servidor,
}) {
  const [orden, setOrden] = useState({ campo: "dias_prestado", direccion: "desc" });
  const [responsable, setResponsable] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [agrupada, setAgrupada] = useState(false);

  // MODO SERVIDOR (`servidor` presente): el filtro por responsable, la busqueda, el orden y los conteos los
  // hace el backend sobre TODOS los renglones prestados y la tabla pide el resto por paginas (ver
  // kpi/kpiPrestamosServidor.js). Sin `servidor` (la vista previa con datos demo) corre el modo LOCAL de
  // siempre sobre `filas`, sin ningun cambio: sus variables se llaman `...Local`.
  const enServidor = Boolean(servidor);
  const srv = useTablaServidor({
    habilitado: enServidor,
    cargar: servidor?.cargar,
    onListo: enPanel ? undefined : servidor?.onListo,
    tamano: enPanel ? TAMANO_PAGINA_PANEL : TAMANO_PAGINA_TARJETA,
    idUser: responsable,
    ambito: filtroExterno?.id,
    busqueda,
    orden,
    agrupada,
  });
  const opcionesServidor = useMemo(() => opcionesDeResponsables(srv.responsables), [srv.responsables]);
  const totalServidor = useMemo(() => totalDeResponsables(srv.responsables), [srv.responsables]);
  const filasServidor = useMemo(
    () => filasTablaPrestamo(srv.items, servidor?.sinAsignar),
    [srv.items, servidor?.sinAsignar],
  );
  // Si el responsable filtrado ya no tiene renglones (se devolvio todo su material), se quita el filtro en
  // vez de dejar una tabla vacia.
  useEffect(() => {
    if (enServidor && responsable && !srv.cargando && !opcionesServidor.some((opcion) => opcion.valor === responsable)) {
      setResponsable("");
    }
  }, [enServidor, responsable, srv.cargando, opcionesServidor]);

  // El filtro que llega de otra tarjeta (clic en una barra) recorta ANTES de todo lo demas.
  const base = useMemo(() => (filtroExterno ? filtrarPorUsuario(filas, filtroExterno.id) : filas), [filas, filtroExterno]);
  const responsables = useMemo(() => responsablesDe(base), [base]);
  // Si el responsable filtrado ya no esta en los datos (se devolvio todo su material),
  // el filtro se ignora en vez de dejar una tabla vacia.
  const filtroLocal = responsables.includes(responsable) ? responsable : "";
  const filtro = enServidor ? (opcionesServidor.some((opcion) => opcion.valor === responsable) ? responsable : "") : filtroLocal;
  const filtradasLocal = useMemo(
    () => buscarEnFilas(filtrarPorResponsable(base, filtroLocal), busqueda),
    [base, filtroLocal, busqueda],
  );
  const ordenadasLocal = useMemo(() => ordenarFilas(filtradasLocal, orden.campo, orden.direccion), [filtradasLocal, orden]);
  const hayRecorte = Boolean(filtroLocal || filtroExterno || busqueda);
  const resumenLocal = useMemo(() => resumenDePrestamos(filtradasLocal, hayRecorte ? 0 : total), [filtradasLocal, hayRecorte, total]);
  const escalaLocal = useMemo(() => escalaDeBarras(filtradasLocal), [filtradasLocal]);

  // Lo que se pinta: lo del servidor (ya filtrado, buscado y ordenado alla) o lo local.
  const filtradas = enServidor ? filasServidor : filtradasLocal;
  const ordenadas = enServidor ? filasServidor : ordenadasLocal;
  const resumen = useMemo(
    () => (enServidor ? resumenDeServidor(srv.resumen) : resumenLocal),
    [enServidor, srv.resumen, resumenLocal],
  );
  const escala = enServidor
    ? Math.max(escalaDeBarras(filasServidor), srv.resumen?.mas_antiguo?.dias || 0)
    : escalaLocal;

  const limite = enPanel ? Infinity : RENGLONES_VISIBLES;
  const visibles = recortar(ordenadas, enPanel, limite);
  const grupos = useMemo(() => {
    if (!agrupada) return [];
    const agrupados = enServidor ? agruparContiguos(filasServidor, srv.responsables) : agruparPorResponsable(filtradasLocal);
    return recortarGrupos(agrupados, enPanel, limite);
  }, [agrupada, enServidor, filasServidor, srv.responsables, filtradasLocal, enPanel, limite]);
  const hayMasQueElLimite = (enServidor ? srv.total : filtradas.length) > RENGLONES_VISIBLES;
  // Las opciones del desplegable y su "(n)": reales (del servidor) o contadas sobre lo local.
  const opciones = enServidor
    ? opcionesServidor
    : responsables.map((nombre) => ({ valor: nombre, nombre, renglones: filtrarPorResponsable(base, nombre).length }));
  const totalDeOpciones = enServidor ? totalServidor : base.length;

  // Panel "Ver todos" en modo servidor: al llegar al final de lo cargado se pide la pagina siguiente.
  const centinela = useRef(null);
  const { hayMas, cargarMas } = srv;
  useEffect(() => {
    if (!enServidor || !enPanel || !hayMas || typeof IntersectionObserver === "undefined") return undefined;
    const nodo = centinela.current;
    if (!nodo) return undefined;
    const observador = new IntersectionObserver((entradas) => {
      if (entradas.some((entrada) => entrada.isIntersecting)) cargarMas();
    });
    observador.observe(nodo);
    return () => observador.disconnect();
  }, [enServidor, enPanel, hayMas, cargarMas, srv.items.length]);

  function alternarOrden(campo) {
    setOrden((actual) => ({ campo, direccion: actual.campo === campo && actual.direccion === "desc" ? "asc" : "desc" }));
  }

  if (enServidor && !srv.resumen) {
    return srv.error
      ? <p className="kpi-error-inline" role="alert">{textos.error_carga}</p>
      : <p className="kpi-prestamos-cargando" role="status">{textos.cargando}</p>;
  }
  // Sin ningun renglon prestado: con el filtro de otra tarjeta puesto no se sabe si es de TODOS o solo de esa
  // persona, y se dice lo segundo (mas abajo, `sinPrestamosDelFiltrado`).
  if (enServidor ? (totalServidor === 0 && !filtroExterno) : filas.length === 0) {
    return (
      <div className="kpi-prestamos-vacio">
        <PackageCheck size={30} aria-hidden="true" />
        <strong>{textos.vacio_titulo}</strong>
        <p>{textos.vacio}</p>
      </div>
    );
  }

  // El filtro de otra tarjeta dejo la lista en blanco porque esa persona no debe nada (no porque
  // la busqueda o el responsable no coincidan): se dice asi, con un solo boton para quitarlo.
  const sinPrestamosDelFiltrado = Boolean(filtroExterno) && (enServidor ? totalServidor : base.length) === 0;
  const plural = (n, uno, varios) => `${n} ${n === 1 ? textos[uno] : textos[varios]}`;
  const renglonesTexto = resumen.renglones > resumen.cargados
    ? `${resumen.cargados} ${textos.de} ${resumen.renglones} ${textos.renglones}`
    : plural(resumen.renglones, "renglon", "renglones");
  const cuerpo = (lista) => lista.map((fila) => (
    <Renglon
      key={fila.id}
      fila={fila}
      maximo={escala}
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
    <div
      className={`kpi-preview-tabla-wrap kpi-prestamos ${enPanel ? "en-panel" : ""}`.trim()}
      aria-busy={enServidor && (srv.cargando || srv.cargandoMas) ? "true" : undefined}
    >
      {filtroExterno && (
        <div className="kpi-prestamos-filtro-externo">
          <span>{textos.filtrando}: <strong>{filtroExterno.nombre}</strong></span>
          <button type="button" onClick={onQuitarFiltroExterno} aria-label={`${textos.quitar_filtro_externo}: ${filtroExterno.nombre}`} title={textos.quitar_filtro_externo}>
            <X size={13} aria-hidden="true" />
          </button>
        </div>
      )}
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
        {enPanel && (
          <label className="kpi-prestamos-control kpi-prestamos-buscador">
            <span>{textos.buscar}</span>
            <span className="kpi-prestamos-buscador-caja">
              <Search size={14} aria-hidden="true" />
              <input
                type="search"
                value={busqueda}
                placeholder={textos.buscar_pista}
                onChange={(evento) => setBusqueda(evento.target.value)}
              />
            </span>
          </label>
        )}
        <label className="kpi-prestamos-control">
          <span>{textos.filtro_responsable}</span>
          <select value={filtro} onChange={(evento) => setResponsable(evento.target.value)}>
            <option value="">{textos.todos_los_responsables} ({totalDeOpciones})</option>
            {opciones.map((opcion) => (
              <option key={opcion.valor} value={opcion.valor}>{opcion.nombre} ({opcion.renglones})</option>
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

      {filtradas.length === 0 && !(enServidor && srv.cargando) && (
        <div className="kpi-prestamos-vacio">
          {sinPrestamosDelFiltrado ? (
            <>
              <p>{llenar(textos.sin_prestamos_de, { responsable: filtroExterno.nombre })}</p>
              <button type="button" className="button ghost" onClick={onQuitarFiltroExterno}>{textos.quitar_filtro_externo}</button>
            </>
          ) : (
            <>
              <p>{busqueda ? textos.sin_coincidencias : llenar(textos.sin_resultados, { responsable: opciones.find((opcion) => opcion.valor === responsable)?.nombre || responsable })}</p>
              <button
                type="button"
                className="button ghost"
                onClick={() => { setResponsable(""); setBusqueda(""); }}
              >
                {busqueda ? textos.limpiar_busqueda : textos.quitar_filtro}
              </button>
            </>
          )}
        </div>
      )}

      {filtradas.length > 0 && (
        <div className="kpi-prestamos-lista">
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
          {/* Fin de lo cargado, DENTRO de la lista que se desplaza: cuando el usuario llega aqui se pide la pagina
              siguiente. Fuera de la lista (junto al boton) estaria siempre a la vista y cargaria todo de golpe. */}
          {enServidor && enPanel && hayMas && <div ref={centinela} className="kpi-prestamos-centinela" aria-hidden="true" />}
        </div>
      )}

      {!enPanel && hayMasQueElLimite && (
        <button type="button" className="kpi-prestamos-ver-todos" aria-haspopup="dialog" onClick={onVerTodos}>
          {llenar(textos.ver_todos, { n: enServidor ? srv.total : filtradas.length })}
        </button>
      )}
      {enServidor && enPanel && (
        <>
          {srv.error && <p className="kpi-error-inline" role="alert">{textos.error_carga}</p>}
          {hayMas && (
            <>
              <p className="kpi-preview-tabla-total">{textos.mostrando} {srv.items.length} {textos.de} {srv.total}</p>
              <button type="button" className="button ghost kpi-prestamos-mostrar-mas" onClick={cargarMas} disabled={srv.cargandoMas}>
                {srv.cargandoMas ? textos.cargando_mas : textos.mostrar_mas}
              </button>
            </>
          )}
        </>
      )}
      {!enServidor && total > filas.length && (
        <p className="kpi-preview-tabla-total">{textos.mostrando} {filas.length} {textos.de} {total}</p>
      )}
    </div>
  );
}

const PROPS_FILAS = PropTypes.arrayOf(PropTypes.shape({
  id: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  id_user: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  articulo: PropTypes.string,
  responsable: PropTypes.string,
  fecha_prestamo: PropTypes.string,
  dias_prestado: PropTypes.number,
}));

ContenidoPrestamos.propTypes = {
  filas: PROPS_FILAS.isRequired,
  resaltarResponsable: PropTypes.string,
  onFilaClick: PropTypes.func,
  total: PropTypes.number,
  textos: PropTypes.objectOf(PropTypes.string).isRequired,
  filtroExterno: PropTypes.shape({ id: PropTypes.oneOfType([PropTypes.number, PropTypes.string]), nombre: PropTypes.string }),
  onQuitarFiltroExterno: PropTypes.func,
  enPanel: PropTypes.bool,
  onVerTodos: PropTypes.func,
  servidor: PropTypes.shape({ cargar: PropTypes.func.isRequired, onListo: PropTypes.func, sinAsignar: PropTypes.string }),
};
ContenidoPrestamos.defaultProps = {
  resaltarResponsable: null, onFilaClick: null, total: 0, filtroExterno: null, onQuitarFiltroExterno: null, enPanel: false, onVerTodos: null,
  servidor: null,
};

const ENFOCABLES = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

/** Ventana con la lista completa. Se pinta en `document.body` (no dentro de la tarjeta, que
 * recorta y tiene transform por el arrastre); Escape o un clic afuera la cierran, el foco
 * entra a la ventana, Tab no se sale de ella y al cerrar vuelve al boton que la abrio. */
function PanelDePrestamos({ onCerrar, textos, children }) {
  const ventana = useRef(null);
  useEffect(() => {
    const previo = document.activeElement;
    ventana.current?.querySelector("input, button")?.focus();
    const alTeclear = (evento) => {
      if (evento.key === "Escape") { evento.stopPropagation(); onCerrar(); return; }
      if (evento.key !== "Tab" || !ventana.current) return;
      const dentro = [...ventana.current.querySelectorAll(ENFOCABLES)].filter((el) => !el.disabled && el.offsetParent !== null);
      if (!dentro.length) return;
      const primero = dentro[0];
      const ultimo = dentro[dentro.length - 1];
      if (evento.shiftKey && document.activeElement === primero) { evento.preventDefault(); ultimo.focus(); }
      else if (!evento.shiftKey && document.activeElement === ultimo) { evento.preventDefault(); primero.focus(); }
    };
    document.addEventListener("keydown", alTeclear, true);
    const desbordeAnterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", alTeclear, true);
      document.body.style.overflow = desbordeAnterior;
      if (previo && typeof previo.focus === "function") previo.focus();
    };
  }, [onCerrar]);

  return createPortal(
    <div
      className="kpi-prestamos-modal-raiz"
      data-theme={document.querySelector(".kpi-dashboard")?.getAttribute("data-theme") || undefined}
    >
      <div className="kpi-prestamos-modal-fondo" onMouseDown={(evento) => { if (evento.target === evento.currentTarget) onCerrar(); }}>
        <div ref={ventana} className="kpi-prestamos-modal" role="dialog" aria-modal="true" aria-label={textos.panel_titulo}>
          <header className="kpi-prestamos-modal-cabecera">
            <h3>{textos.panel_titulo}</h3>
            <button type="button" className="kpi-icon-button" onClick={onCerrar} aria-label={textos.cerrar} title={textos.cerrar}>
              <X size={16} aria-hidden="true" />
            </button>
          </header>
          <div className="kpi-prestamos-modal-cuerpo">{children}</div>
        </div>
      </div>
    </div>,
    document.body,
  );
}

PanelDePrestamos.propTypes = {
  onCerrar: PropTypes.func.isRequired,
  textos: PropTypes.objectOf(PropTypes.string).isRequired,
  children: PropTypes.node.isRequired,
};

export default function TablaWidget({
  filas, resaltarResponsable, onFilaClick, total, etiquetas, filtroExterno, onQuitarFiltroExterno, servidor,
}) {
  const textos = { ...ETIQUETAS_POR_OMISION, ...etiquetas };
  const [panelAbierto, setPanelAbierto] = useState(false);
  const cerrar = useMemo(() => () => setPanelAbierto(false), []);
  const compartidas = { filas, resaltarResponsable, onFilaClick, total, textos, filtroExterno, onQuitarFiltroExterno, servidor };
  return (
    <>
      <ContenidoPrestamos {...compartidas} onVerTodos={() => setPanelAbierto(true)} />
      {panelAbierto && (
        <PanelDePrestamos onCerrar={cerrar} textos={textos}>
          <ContenidoPrestamos {...compartidas} enPanel />
        </PanelDePrestamos>
      )}
    </>
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
  // Filtro que llega de otra tarjeta (clic en una barra de "abiertas por responsable").
  filtroExterno: PropTypes.shape({ id: PropTypes.oneOfType([PropTypes.number, PropTypes.string]), nombre: PropTypes.string }),
  onQuitarFiltroExterno: PropTypes.func,
  // Modo servidor: { cargar(parametros) -> Promise, onListo(), sinAsignar }. Sin el, modo local sobre `filas`.
  servidor: PropTypes.shape({ cargar: PropTypes.func.isRequired, onListo: PropTypes.func, sinAsignar: PropTypes.string }),
};

TablaWidget.defaultProps = {
  resaltarResponsable: null, onFilaClick: null, total: 0, etiquetas: null, filtroExterno: null, onQuitarFiltroExterno: null,
  servidor: null,
};
