import React, { useCallback, useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  AlertTriangle, Camera, Crosshair, FilterX, History,
  ImageOff, MapPin, Package, Ruler, ShoppingCart, Tags, RefreshCw, Search,
  UserRound,
  Wrench,
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  getAssetStatusSummary, inventoryTrace, uploadProductImage, urlDeArchivo,
} from "../api";
import FiltroBuscable from "../components/FiltroBuscable.jsx";
import Pagination from "../components/Pagination.jsx";
import ProductHistory from "../components/ProductHistory.jsx";
import { useI18n } from "../i18n";
import VisorDeFoto from "../components/VisorDeFoto";
import "../styles/inventory-trace.css";
import { formatearFechaHora } from "../utils/fechas";
import { CLASES_DE_ARTICULO, etiquetaDeClase } from "../utils/clasesDeProducto";
import PageHeader from "../components/PageHeader.jsx";

/**
 * Localizar cualquier cosa del almacen.
 *
 * Contesta la pregunta que se hace primero en un almacen y que hasta ahora
 * requeria cuatro consultas distintas: se escribe un texto y sale donde esta,
 * cuanto hay en cada sitio, que le ha pasado, y -si se rastrea pieza por
 * pieza- en que estado esta cada una y quien la tiene.
 *
 * Tres decisiones que se ven en la pantalla:
 *
 * * **Se busca tambien por etiqueta de pieza.** Es lo que esta pegado en la
 *   herramienta: quien la tiene en la mano lee ese numero, no el codigo del
 *   producto.
 * * **La foto se sube desde aqui.** Un almacen con cuatrocientos articulos
 *   parecidos se cuenta mal sin foto, y obligar a ir a la pantalla de Producto
 *   para ponerla significa que nadie la pone.
 * * **Lo que el alcance esconde se cuenta.** Si hay coincidencias de otro
 *   proyecto, se dice cuantas. Quien busca algo que existe y no lo ve merece
 *   saber que el filtro es el alcance y no que no exista.
 * * **Buscar una pieza y buscar el producto se contestan distinto.** Son dos
 *   preguntas: "donde esta el taladro TAL-001-C" y "cuantos taladros tengo y
 *   como estan". Antes se contestaban igual -salia el producto con sus tres
 *   piezas y sin decir cual era la que se pidio-, asi que quien tenia el numero
 *   en la mano tenia que buscarlo a ojo en la lista. Ahora el servidor dice por
 *   que salio cada resultado (`match_kind`) y cual pieza coincide, y la pantalla
 *   ensena la pieza pedida arriba con su bitacora, y las demas unidades debajo.
 */

/**
 * Las dos naturalezas del material, y no un filtro mas.
 *
 * El almacen guarda dos cosas que se preguntan distinto: la mercancia que la
 * empresa distribuye -de ella importa el saldo- y la herramienta de uso interno
 * -de ella importa quien la tiene-. Como marco de la pantalla, cada una trae su
 * pregunta; como opcion dentro de un desplegable de seis, habia que saber que
 * estaba ahi.
 */
const NATURALEZAS = [
  { valor: "", clave: "all_purposes", texto: "Todo el almacén", icono: null },
  // El valor que viaja al servidor sigue siendo `mercancia`: es lo que hay en
  // `product.stock_purpose` en 2 221 filas, y renombrar la columna seria mover
  // datos para cambiar una etiqueta. Lo que cambia es como se lee, y
  // "Consumible" es la palabra que usa el resto del almacen -- la misma que
  // trae `familia.herramienta_consumible` del sistema anterior.
  { valor: "mercancia", clave: "consumable", texto: "Consumible",
    icono: ShoppingCart, ayuda: "Lo que se gasta y se repone. Se cuenta por cantidad." },
  { valor: "uso_interno", clave: "internal_use", texto: "Uso interno",
    icono: Wrench, ayuda: "Herramienta y equipo. Se rastrea pieza por pieza." },
];

// El orden en que se leen los estados: primero lo que se puede usar, luego lo
// que esta fuera, y al final lo que ya no vuelve.
const ORDEN_DE_ESTADOS = [
  "disponible", "en_uso", "prestada", "en_reparacion", "extraviada", "retirada",
];

// Los estados de una pieza, con el tono con el que se pintan. `disponible` es
// el unico que cuenta como existencia; el resto explica por que no esta.
// El estatus del producto tal como lo escribio el sistema anterior. Son los de
// `producto.estado`, que el importador guarda intactos en
// `product.product_status`: ENTRADA 1888, SALIDA 143, DESTRUCCION 86,
// EXTRAVIADO 65, DANADO 27 y EQ. DANADOS 11.
//
// El color va por GRAVEDAD y no uno por estatus, y a proposito: la paleta de
// esta pantalla tiene cinco tonos -- ok, info, warn, crit, muted -- y los siete
// estatus no caben en cinco sin inventar colores nuevos. Inventarlos seria
// romper la colorimetria justo para distinguir cosas que el texto de la
// etiqueta ya distingue. Asi el color contesta de un vistazo "esto esta bien /
// esto hay que atenderlo / esto se perdio", y la etiqueta dice cual es cual.
//
//   verde  esta en el almacen
//   azul   fuera, pero sin problema -- salio o esta rentado
//   ambar  hay que hacer algo -- danado o en reparacion
//   rojo   se perdio
//   gris   fin de vida -- se destruyo
// La simbologia de la tarjeta: que significa cada tono y que estatus lo llevan.
//
// Se declara aparte del mapa de arriba y no se deriva de el a proposito: en el
// mapa manda el estatus y aqui manda el TONO, y son cinco entradas -- una por
// color-, no ocho. Derivarla daria la lista de estatus por tono, que es la mitad
// util, pero no el "que quiere decir este color", que es la otra mitad y la que
// hace falta para leer la pantalla.
const SIMBOLOGIA = [
  { tono: "ok", clave: "in_stock", texto: "En el almacén", estatus: ["ENTRADA"] },
  { tono: "info", clave: "out_ok", texto: "Fuera, sin problema",
    estatus: ["SALIDA", "RENTA"] },
  { tono: "warn", clave: "needs_care", texto: "Hay que atenderlo",
    estatus: ["DAÑADO", "EQ. DAÑADOS", "REPARACIÓN"] },
  { tono: "crit", clave: "lost", texto: "Se perdió", estatus: ["EXTRAVIADO"] },
  { tono: "muted", clave: "end_of_life", texto: "Fin de vida",
    estatus: ["DESTRUCCIÓN"] },
];

const TONO_DE_ESTATUS = {
  ENTRADA: "ok",
  SALIDA: "info",
  RENTA: "info",
  DANADO: "warn",
  "EQ. DANADOS": "warn",
  REPARACION: "warn",
  EXTRAVIADO: "crit",
  DESTRUCCION: "muted",
};

// Sin acentos y en mayusculas: en los datos conviven "DAÑADO" y "DANADO", y
// "DESTRUCCION" nunca trae tilde aunque se diga "destrucción".
function normalizarEstatus(valor) {
  return String(valor || "")
    .toUpperCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .trim();
}

// El estatus que se pinta lo calcula el backend (`effective_status`): el texto
// viejo de `product_status` corregido con las salidas abiertas. La regla vive
// alli para que cualquier pantalla la lea igual.
function estatusPintado(it) {
  return normalizarEstatus(it.effective_status ?? it.product_status);
}

const TONO_DE_ESTADO = {
  disponible: "ok",
  en_uso: "info",
  prestada: "warn",
  en_reparacion: "warn",
  extraviada: "crit",
  retirada: "muted",
};

// Como se pinta cada tipo de movimiento del historial. Entradas en verde,
// salidas normales en gris, y en rojo lo que se perdio sin venderse: eso es lo
// que hay que mirar.
const TONO_DE_HISTORIA = {
  comprado: "ok", recibido: "ok", devuelto: "ok",
  // La existencia con la que arranco el catalogo: ni buena ni mala noticia,
  // es el punto de partida.
  inicial: "muted",
  vendido: "info", entregado: "muted", trasladado: "muted", ajustado: "muted",
  prestado: "warn",
  danado: "crit", destruido: "crit", extraviado: "crit", caducado: "crit",
};

/**
 * Una pieza: su etiqueta, su estado, quien la tiene y -si es la que se
 * busco- todo lo que le ha pasado.
 *
 * La bitacora solo se ensena de la pieza pedida. El servidor tampoco la manda
 * para las demas: desplegar la historia de treinta piezas para ver una es
 * ruido, y la historia del producto -que si sale siempre- ya contesta la
 * pregunta general.
 */
function Pieza({ pieza, destacada, t }) {
  return (
    <li className={destacada ? "trace-asset-hit" : undefined}>
      <div className="trace-asset-line">
        {destacada && <Crosshair size={13} className="trace-hit-icon" />}
        <span className="mono">{pieza.asset_tag}</span>
        <span className={`trace-chip ${TONO_DE_ESTADO[pieza.status] || "muted"}`}>
          {t(`assets.status_${pieza.status}`, pieza.status)}
        </span>
        {/* Quien la tiene solo aplica cuando esta fuera de su sitio; en
            `disponible` el responsable es nadie. */}
        {pieza.holder_name && <span className="trace-holder">{pieza.holder_name}</span>}
        {(pieza.location_path_label || pieza.location_description) && (
          <span className="muted">
            <MapPin size={12} />{" "}
            {pieza.location_path_label || pieza.location_description}
          </span>
        )}
        {pieza.due_date && (
          <span className="muted">{t("trace.due", "regresa")} {pieza.due_date}</span>
        )}
        {/* Esta pantalla localiza; las acciones sobre la pieza -prestar,
            devolver, mandar a reparar, dar de baja- viven en su pantalla, que es
            donde estan sus transiciones de estado. Se enlaza en vez de
            repetirlas aqui: dos sitios que prestan la misma herramienta acaban
            discrepando. */}
        <Link className="trace-manage"
              to={`/assets?tag=${encodeURIComponent(pieza.asset_tag || "")}`}>
          {t("trace.manage_piece", "Gestionar")}
        </Link>
      </div>

      {destacada && pieza.timeline?.length > 0 && (
        <ol className="trace-timeline">
          {pieza.timeline.map((e) => (
            <li key={e.id_inventory_asset_event}>
              <span className="trace-when">
                {e.creation_date ? formatearFechaHora(e.creation_date, "es-MX") : ""}
              </span>
              <span className="trace-what">
                {t(`trace.event_${e.event_type}`, e.etiqueta)}
                {(e.holder_after_name || e.holder_before_name) && (
                  <strong> {e.holder_after_name || e.holder_before_name}</strong>
                )}
                {e.location_after_description && (
                  <em> · {e.location_after_description}</em>
                )}
              </span>
              {e.reason && <span className="muted">{e.reason}</span>}
            </li>
          ))}
        </ol>
      )}
    </li>
  );
}


Pieza.propTypes = {
  pieza: PropTypes.shape({
    id_inventory_asset: PropTypes.number,
    asset_tag: PropTypes.string,
    status: PropTypes.string,
    holder_name: PropTypes.string,
    location_description: PropTypes.string,
    location_path_label: PropTypes.string,
    due_date: PropTypes.string,
    timeline: PropTypes.arrayOf(PropTypes.object),
  }).isRequired,
  destacada: PropTypes.bool,
  t: PropTypes.func.isRequired,
};


// Cuantos resultados por pagina se pueden pedir. El servidor da 40 por omision
// y no acepta mas de 200: ofrecer 500 seria prometer algo que se recorta en
// silencio.
const TAMANOS_DE_PAGINA = [20, 40, 100, 200];

const SIN_FILTROS = {
  stock_purpose: "",
  id_product_family: "",
  id_brand: "",
  id_location: "",
  asset_status: "",
  id_material: "",
  item_class: "",
};

export default function InventoryTracePage() {
  const { t } = useI18n();
  const [consulta, setConsulta] = useState("");
  // Los filtros viven juntos en un objeto porque van juntos a la peticion y se
  // limpian juntos. Sueltos, cada uno nuevo obliga a tocar el efecto, la
  // llamada y el boton de limpiar, y se olvida uno.
  const [filtros, setFiltros] = useState(SIN_FILTROS);
  const [pagina, setPagina] = useState(1);
  // Cuantos ver de golpe. 40 es lo que el servidor da por omision; el tope de
  // alla son 200, asi que las opciones no prometen mas de lo que puede dar.
  const [porPagina, setPorPagina] = useState(40);
  const [datos, setDatos] = useState(null);
  // El panorama de estatus. Solo tiene sentido con uso interno: lo fungible no
  // tiene piezas, asi que no tiene estados que contar.
  const [panorama, setPanorama] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [subiendo, setSubiendo] = useState(null);
  // Fotos cuya ruta existe pero el archivo no. Pasa con datos de semilla y con
  // un archivo borrado a mano: el navegador ensena su icono de imagen rota, que
  // se lee como un fallo de la aplicacion. Se cae al marcador de "sin foto",
  // que es la verdad.
  const [fotosRotas, setFotosRotas] = useState(() => new Set());
  // La foto que se esta mirando en grande, o null.
  const [fotoAmpliada, setFotoAmpliada] = useState(null);
  // El producto cuya ficha esta abierta, o null. Se guarda el renglon entero y
  // no solo el id para poder titular la ventana sin volver a pedirlo.
  const [ficha, setFicha] = useState(null);

  // `t` cambia de identidad en cada render; si entra en las dependencias del
  // efecto la pantalla se repide sin parar hasta que el navegador rechaza
  // peticiones. Se guarda en una referencia.
  const traducir = useRef(t);
  traducir.current = t;

  const buscar = useCallback(async (texto, activos, numeroDePagina, cuantos) => {
    setCargando(true);
    setError("");
    try {
      // Los vacios no se mandan: `?id_brand=` es un filtro que el servidor
      // tiene que aprender a ignorar, y una direccion llena de parametros
      // huecos no se puede leer ni compartir.
      const params = { q: texto, page: numeroDePagina || 1 };
      if (cuantos) params.per_page = cuantos;
      Object.entries(activos || {}).forEach(([clave, valor]) => {
        if (valor) params[clave] = valor;
      });
      setDatos(await inventoryTrace(params));

      // El panorama de estatus, acotado a la naturaleza que se este mirando.
      // Tambien en mercancia: un producto serializado que la empresa distribuye
      // tiene piezas, y una de ellas puede estar extraviada igual que un
      // taladro. El servidor solo cuenta lo que el usuario alcanza a ver.
      try {
        const proposito = (activos || {}).stock_purpose;
        setPanorama(await getAssetStatusSummary(
          proposito ? { stock_purpose: proposito } : {}));
      } catch {
        // Que falle el panorama no puede tumbar la busqueda: es un resumen de
        // apoyo, no el resultado.
        setPanorama(null);
      }
    } catch (e) {
      setError(e?.payload?.error_key
        ? traducir.current(e.payload.error_key)
        : traducir.current("errors.request_failed", "No se pudo completar la búsqueda."));
    } finally {
      setCargando(false);
    }
  }, []);

  // Se espera a que deje de escribir: una peticion por tecla convierte una
  // busqueda de seis letras en seis consultas al almacen.
  useEffect(() => {
    const temporizador = setTimeout(
      () => buscar(consulta, filtros, pagina, porPagina), 350);
    return () => clearTimeout(temporizador);
  }, [consulta, filtros, pagina, porPagina, buscar]);

  // Cambiar el texto o un filtro vuelve a la primera pagina. Sin esto, quien
  // esta en la pagina 7 y escribe algo nuevo pide la pagina 7 de un resultado
  // distinto: el servidor la acota a la ultima, y parece que la busqueda
  // devolvio poco cuando lo que paso es que se salto lo de delante.
  const cambiarFiltro = (clave, valor) => {
    setPagina(1);
    setFiltros((antes) => ({ ...antes, [clave]: valor }));
  };
  const cambiarConsulta = (valor) => {
    setPagina(1);
    setConsulta(valor);
  };
  const cambiarTamano = (cuantos) => {
    setPagina(1);
    setPorPagina(cuantos);
  };
  const filtrosActivos = Object.values(filtros).filter(Boolean).length;

  const subirFoto = async (idProducto, archivo) => {
    if (!archivo) return;
    setSubiendo(idProducto);
    setError("");
    try {
      await uploadProductImage(idProducto, archivo);
      setFotosRotas((antes) => {
        const siguiente = new Set(antes);
        siguiente.delete(idProducto);
        return siguiente;
      });
      await buscar(consulta, filtros, pagina, porPagina);
    } catch (e) {
      setError(e?.payload?.error_key
        ? traducir.current(e.payload.error_key)
        : traducir.current("errors.request_failed", "No se pudo subir la fotografía."));
    } finally {
      setSubiendo(null);
    }
  };

  // La lista llega ya recortada. Antes se filtraba aqui por estado de pieza, y
  // entonces el conteo, el aviso de "hay mas resultados" y los desplegables
  // hablaban de un conjunto y la lista de otro, sin forma de saber cual de los
  // tres numeros era el bueno.
  const items = datos?.items || [];
  const catalogo = datos?.catalog
    || { families: [], brands: [], warehouses: [], materials: [], locations: [] };

  return (
    <section className="page trace-page">
      <PageHeader
        eyebrow={t("trace.eyebrow", "Almacén")}
        titulo={t("trace.title", "Localizar")}
        subtitulo={t("trace.subtitle",
              "Busca cualquier producto o herramienta y mira dónde está, qué le pasó y quién la tiene.")}
      >
        <button className="button" onClick={() => buscar(consulta, filtros, pagina, porPagina)} disabled={cargando}>
        <RefreshCw size={16} />
        {cargando ? t("common.loading", "Cargando…") : t("common.refresh", "Actualizar")}
        </button>
      </PageHeader>

      {/* El marco: que clase de material se esta buscando. Va ARRIBA del
          buscador porque cambia el sentido de todo lo que sigue -de la
          mercancia importa el saldo, de la herramienta quien la tiene-. */}
      <div className="trace-naturalezas" role="group"
           aria-label={t("trace.purpose", "Clase de material")}>
        {NATURALEZAS.map(({ valor, clave, texto, icono: Icono, ayuda }) => (
          <button
            key={valor || "todo"}
            type="button"
            className={`trace-naturaleza ${filtros.stock_purpose === valor ? "activa" : ""}`}
            onClick={() => cambiarFiltro("stock_purpose", valor)}
            title={ayuda ? t(`trace.${clave}_help`, ayuda) : undefined}
          >
            {Icono && <Icono size={15} />}
            {t(`trace.${clave}`, texto)}
          </button>
        ))}
      </div>

      {/* La clase del articulo -herramienta, consumible, sobrante, recargable-:
          otro recorte, independiente de la naturaleza de arriba. */}
      <div className="trace-naturalezas" role="group"
           aria-label={t("item_class.label", "Clase")}>
        {[{ clave: "", etiqueta: "Todas" }, ...CLASES_DE_ARTICULO].map((c) => (
          <button key={c.clave || "todas"} type="button"
                  className={`trace-naturaleza ${filtros.item_class === c.clave ? "activa" : ""}`}
                  onClick={() => cambiarFiltro("item_class", c.clave)}>
            {c.clave ? t(`item_class.${c.clave}`, c.etiqueta) : t("item_class.all", "Todas las clases")}
          </button>
        ))}
      </div>

      {/* El panorama de estatus: la pregunta de la manana en un almacen de
          herramienta. Cada cifra filtra, asi que ver "3 prestadas" y saber
          cuales es el mismo gesto. */}
      {panorama && panorama.total > 0 && (
        <div className="trace-panorama">
          {ORDEN_DE_ESTADOS.map((estado) => {
            const cuantas = panorama.by_status?.[estado] || 0;
            if (!cuantas && filtros.asset_status !== estado) return null;
            return (
              <button
                key={estado}
                type="button"
                className={[
                  "trace-cifra",
                  TONO_DE_ESTADO[estado] || "muted",
                  filtros.asset_status === estado ? "activa" : "",
                ].filter(Boolean).join(" ")}
                onClick={() => cambiarFiltro(
                  "asset_status", filtros.asset_status === estado ? "" : estado)}
              >
                <strong>{cuantas}</strong>
                <span>{t(`assets.status_${estado}`, estado)}</span>
              </button>
            );
          })}
          {/* Lo vencido va aparte y no como un estado: una pieza vencida esta
              prestada, asi que contarla como estado propio la sumaria dos
              veces. */}
          {panorama.overdue > 0 && (
            <span className="trace-cifra vencidas" title={t("trace.overdue_help",
              "Préstamos que ya debieron volver. Están contados dentro de «prestada».")}>
              <AlertTriangle size={13} />
              <strong>{panorama.overdue}</strong>
              <span>{t("trace.overdue_short", "vencidas")}</span>
            </span>
          )}
        </div>
      )}

      <div className="trace-toolbar">
        <div className="trace-search">
          <Search size={16} />
          <input
            value={consulta}
            onChange={(e) => cambiarConsulta(e.target.value)}
            placeholder={t("trace.search_placeholder",
              "Nombre, código o etiqueta de la pieza (por ejemplo TAL-001)")}
            aria-label={t("trace.search_placeholder", "Buscar en el almacén")}
          />
        </div>

        {/* Familia, marca y almacen salen de lo que el texto encontro, con
            cuantos productos hay detras de cada opcion. Un desplegable que
            ofrece treinta familias y veintiocho estan vacias hace perder mas
            tiempo del que ahorra. */}
        {/* Buscables porque con los datos de verdad son 146 familias, 84
            marcas y 562 materiales: un desplegable plano de ese tamano no es un
            filtro, es una lista donde hay que bajar a ojo. */}
        <FiltroBuscable
          valor={filtros.id_product_family}
          opciones={catalogo.families.map((f) => ({
            value: f.id_product_family, label: `${f.family} (${f.products})` }))}
          onChange={(v) => cambiarFiltro("id_product_family", v)}
          etiqueta={t("trace.by_family", "Por familia")}
          todas={t("trace.any_family", "Cualquier familia")}
        />
        <FiltroBuscable
          valor={filtros.id_brand}
          opciones={catalogo.brands.map((b) => ({
            value: b.id_brand, label: `${b.brand} (${b.products})` }))}
          onChange={(v) => cambiarFiltro("id_brand", v)}
          etiqueta={t("trace.by_brand", "Por marca")}
          todas={t("trace.any_brand", "Cualquier marca")}
        />
        {/* El material: es el nivel por el que la gente busca de verdad -"arco
            con segueta"- y el servidor ya aceptaba `id_material`; lo que
            faltaba era que el catalogo lo ofreciera. */}
        <FiltroBuscable
          valor={filtros.id_material}
          opciones={(catalogo.materials || []).map((m) => ({
            value: m.id_material, label: `${m.material} (${m.products})` }))}
          onChange={(v) => cambiarFiltro("id_material", v)}
          etiqueta={t("trace.by_material", "Por material")}
          todas={t("trace.any_material", "Cualquier material")}
        />
        {/* La ubicacion, no solo el almacen. El servidor filtra por cualquiera
            e incluye lo que cuelga debajo, asi que ofrecer solo las dos naves
            dejaba sin poder pedirse los estantes. Con la ruta entera, porque
            "E1" no dice de que nave es. */}
        <FiltroBuscable
          valor={filtros.id_location}
          opciones={(catalogo.locations || []).map((u) => ({
            value: u.id_location, label: u.path_label || u.location_description }))}
          onChange={(v) => cambiarFiltro("id_location", v)}
          etiqueta={t("trace.by_warehouse", "Por ubicación")}
          todas={t("trace.any_warehouse", "Cualquier ubicación")}
        />
      </div>

      {/* Cuantos hay y con que se esta filtrando. El numero va aqui y no en la
          lista porque con el tope de resultados lo que se ve puede ser menos
          que lo que hay, y ese es justo el caso en el que hace falta saberlo. */}
      {datos && (
        <p className="trace-count">
          <strong>{datos.matches ?? items.length}</strong>{" "}
          {(datos.matches ?? items.length) === 1
            ? t("trace.one_match", "producto encontrado")
            : t("trace.many_matches", "productos encontrados")}
          {filtrosActivos > 0 && (
            <button type="button" className="trace-clear"
                    onClick={() => { setPagina(1); setFiltros(SIN_FILTROS); }}>
              <FilterX size={13} />
              {t("trace.clear_filters", "Quitar filtros")} ({filtrosActivos})
            </button>
          )}
        </p>
      )}

      {/* Que quiere decir el color del borde de cada tarjeta. Va aqui, pegada a
          la lista que explica, y no en una ayuda aparte: una leyenda que hay que
          ir a buscar no se usa. Cada tono lleva los estatus que le tocan, porque
          el color va por gravedad y varios estatus comparten tono. */}
      {items.length > 0 && (
        <div className="trace-simbologia" role="note"
             aria-label={t("trace.legend", "Qué significa el color de cada tarjeta")}>
          <span className="trace-simbologia-titulo muted">
            {t("trace.legend", "Qué significa el color")}
          </span>
          {SIMBOLOGIA.map(({ tono, clave, texto, estatus }) => (
            <span className="trace-simbologia-item" key={tono}>
              <i className={`trace-muestra ${tono}`} aria-hidden="true" />
              <strong>{t(`trace.legend_${clave}`, texto)}</strong>
              <span className="muted">{estatus.join(" · ")}</span>
            </span>
          ))}
        </div>
      )}

      {error && <p className="error">{error}</p>}

      {datos?.hidden_by_scope > 0 && (
        <p className="trace-warn">
          <AlertTriangle size={15} />
          {t("trace.hidden_by_scope",
            "Hay coincidencias en proyectos a los que no tienes acceso:")}{" "}
          <strong>{datos.hidden_by_scope}</strong>
        </p>
      )}

      {!cargando && items.length === 0 && (
        <p className="muted trace-empty">
          {consulta
            ? t("trace.nothing_found", "Nada coincide con esa búsqueda.")
            : t("trace.empty_warehouse", "El almacén no tiene productos registrados.")}
        </p>
      )}

      {/* Arriba tambien, no solo al pie. Cada ficha de resultado es alta -foto,
          piezas, historia-, asi que con 40 en pantalla el pie queda a varios
          scrolls: cambiar de pagina o de tamano obligaba a bajar hasta el
          final y volver a subir. */}
      {datos && datos.pages > 1 && (
        <Pagination
          page={datos.page}
          pages={datos.pages}
          total={datos.matches}
          perPage={datos.per_page}
          loading={cargando}
          onChange={setPagina}
          opcionesDeTamano={TAMANOS_DE_PAGINA}
          onTamano={cambiarTamano}
          etiquetaDeTotal={t("trace.many_matches", "productos encontrados")}
        />
      )}

      <div className="trace-list">
        {items.map((it) => {
          const historia = Object.entries(it.history || {})
            .sort((a, b) => b[1].unidades - a[1].unidades);
          // El servidor recorto los PRODUCTOS que tienen al menos una pieza en
          // ese estado; aqui se recortan las PIEZAS a las de ese estado. Son
          // dos cortes distintos y hacen falta los dos: sin el primero salen
          // productos sin ninguna pieza asi, y sin el segundo sale el producto
          // entero cuando lo que se pidio fue "ensename lo extraviado".
          const piezas = filtros.asset_status
            ? (it.assets || []).filter((a) => a.status === filtros.asset_status)
            : (it.assets || []);
          // La pieza que se pidio y las demas unidades del mismo producto. El
          // servidor ya las marca y las manda ordenadas; aqui solo se separan
          // para poder titularlas distinto.
          const pedidas = piezas.filter((a) => a.matched);
          const resto = piezas.filter((a) => !a.matched);
          const foto = fotosRotas.has(it.id_product) ? "" : urlDeArchivo(it.path_imagen);

          return (
            <article
              className={`trace-card estatus-${
                TONO_DE_ESTATUS[estatusPintado(it)] || "sin"}`}
              key={it.id_product}
            >
              <div className="trace-photo">
                {foto ? (
                  <img
                    src={foto}
                    alt={it.descripcion || ""}
                    className="foto-ampliable"
                    loading="lazy"
                    title={t("photo.click_to_zoom", "Clic para verla en grande")}
                    onClick={() => setFotoAmpliada({
                      src: foto,
                      titulo: it.descripcion || "",
                      descripcion: it.product_code || "",
                    })}
                    onError={() => setFotosRotas((antes) => {
                      const siguiente = new Set(antes);
                      siguiente.add(it.id_product);
                      return siguiente;
                    })}
                  />
                ) : (
                  <span className="trace-no-photo"><ImageOff size={22} /></span>
                )}
                <label className="trace-upload">
                  <Camera size={14} />
                  <span>
                    {subiendo === it.id_product
                      ? t("common.loading", "Subiendo…")
                      : foto
                        ? t("trace.replace_photo", "Cambiar")
                        : t("trace.add_photo", "Añadir foto")}
                  </span>
                  <input type="file" accept="image/*" disabled={subiendo === it.id_product}
                         onChange={(e) => subirFoto(it.id_product, e.target.files?.[0])} />
                </label>
              </div>

              <div className="trace-body">
                <header className="trace-head">
                  <div>
                    <h2>{it.descripcion || t("trace.unnamed", "Sin descripción")}</h2>
                    <p className="muted mono">
                      {it.product_code || `#${it.id_product}`}
                      {" · "}
                      {t(`trace.purpose_${it.stock_purpose}`, it.stock_purpose)}
                      {it.item_class && <> · {etiquetaDeClase(it.item_class, t)}</>}
                      {it.tracking_mode === "serializado" && (
                        <> · <Wrench size={12} /> {t("trace.serialized", "pieza por pieza")}</>
                      )}
                    </p>

                    {/* El estatus, escrito. El color de la tarjeta dice la
                        gravedad de un vistazo -- verde esta, ambar hay que
                        atenderlo, rojo se perdio -- pero el color solo no dice
                        CUAL: rentado y salido comparten azul, y danado comparte
                        ambar con en reparacion. Y hay quien no distingue esos
                        tonos: el color nunca puede ser el unico portador del
                        dato. */}
                    {(it.effective_status || it.product_status) && (
                      <p className="trace-estatus">
                        <span className={`trace-chip ${
                          TONO_DE_ESTATUS[estatusPintado(it)] || "muted"}`}>
                          {t(`trace.status_${estatusPintado(it)
                            .toLowerCase().replace(/[^a-z]+/g, "_")}`,
                          it.effective_status || it.product_status)}
                        </span>
                        {/* La condicion (nuevo / usado) no pinta el color -ese lo
                            decide donde esta la pieza-, pero se sigue diciendo. */}
                        {["NUEVO", "USADO"].includes(normalizarEstatus(it.product_status)) && (
                          <span className="trace-chip muted">
                            {t(`trace.condition_${normalizarEstatus(it.product_status).toLowerCase()}`,
                              normalizarEstatus(it.product_status) === "NUEVO" ? "Nuevo" : "Usado")}
                          </span>
                        )}
                      </p>
                    )}

                    {/* A que pertenece. Todo esto ya estaba en la base, a dos
                        saltos -producto, material, y de ahi familia, marca y
                        unidad-, asi que para saber la familia de lo que se
                        acababa de encontrar habia que abrir dos pantallas mas.
                        Cada eslabon filtra: se hace clic en la familia y la
                        lista se queda con esa familia. */}
                    {it.classification && (
                      <p className="trace-chain">
                        <Tags size={13} />
                        {/* Cada eslabon con su etiqueta -"Familia:", no solo
                            el valor-: la miga de pan (familia › tipo › marca
                            › material) da el orden correcto para quien ya
                            sabe que es cada nivel, pero no para quien no ha
                            usado el sistema, que no tiene forma de saber que
                            "ESCUADRA" es la familia y "TRUPER" la marca solo
                            por su posicion. */}
                        {it.classification.family && (
                          <span className="trace-chain-item">
                            {t("inventory.family", "Familia")}:{" "}
                            <button type="button" className="trace-link"
                                    onClick={() => cambiarFiltro(
                                      "id_product_family",
                                      String(it.classification.id_product_family))}>
                              {it.classification.family}
                            </button>
                          </span>
                        )}
                        {/* El tipo, detras de la familia porque cuelga de
                            ella: es el nivel que distingue un desarmador plano
                            de uno de cruz. Faltaba en la miga entera, asi que
                            se leia "familia > marca > material" y el segundo
                            nivel no aparecia en ningun sitio. */}
                        {it.classification.material_type && (
                          <>
                            <span className="trace-sep">›</span>
                            <span className="trace-chain-item">
                              {t("trace.material_type", "Tipo")}:{" "}
                              <span className="trace-tipo">
                                {it.classification.material_type}
                              </span>
                            </span>
                          </>
                        )}
                        {it.classification.brand && (
                          <>
                            <span className="trace-sep">›</span>
                            <span className="trace-chain-item">
                              {t("inventory.brand", "Marca")}:{" "}
                              <button type="button" className="trace-link"
                                      onClick={() => cambiarFiltro(
                                        "id_brand", String(it.classification.id_brand))}>
                                {it.classification.brand}
                              </button>
                            </span>
                          </>
                        )}
                        {it.classification.material && (
                          <>
                            <span className="trace-sep">›</span>
                            <span className="trace-chain-item">
                              {t("voucher.material", "Material")}: {it.classification.material}
                            </span>
                          </>
                        )}
                        {it.classification.unit && (
                          <span className="trace-unit">
                            <Ruler size={12} /> {t("voucher.unit", "Unidad")}: {it.classification.unit}
                          </span>
                        )}
                      </p>
                    )}

                    {/* La familia del catalogo publico no es la del material.
                        Cuando discrepan se dice: es un dato mal capturado, y
                        esconderlo es como no tenerlo. */}
                    {it.classification?.catalog_mismatch && (
                      <>
                        {/* Un aviso por eje, diciendo cual es: antes decia solo
                            "lo clasifica distinto" junto a la marca aunque el
                            problema fuera la familia. */}
                        {[
                          ["family", "familia", it.classification.catalog_mismatch.family,
                            it.classification.catalog_mismatch.family?.family,
                            it.classification.catalog_mismatch.family?.id_product_family],
                          ["brand", "marca", it.classification.catalog_mismatch.brand,
                            it.classification.catalog_mismatch.brand?.brand,
                            it.classification.catalog_mismatch.brand?.id_brand],
                        ].filter(([, , dato]) => dato).map(([eje, , , nombre, id]) => {
                          const texto = nombre
                            ? t(`trace.catalog_other_${eje}`,
                                eje === "family"
                                  ? "El catálogo público tiene otra familia: {name}. Si no es la correcta, puedes cambiarla editando el producto."
                                  : "El catálogo público tiene otra marca: {name}. Si no es la correcta, puedes cambiarla editando el producto.")
                                .replace("{name}", nombre)
                            : t(`trace.catalog_missing_${eje}`,
                                eje === "family"
                                  ? "La familia del catálogo público (id {id}) ya no existe. Puedes elegir otra editando el producto."
                                  : "La marca del catálogo público (id {id}) ya no existe. Puedes elegir otra editando el producto.")
                                .replace("{id}", id);
                          return (
                            <p key={eje} className="trace-mismatch">
                              <AlertTriangle size={13} /> {texto}
                            </p>
                          );
                        })}
                      </>
                    )}
                  </div>
                  <div className="trace-total">
                    <strong>{it.total}</strong>
                    <span>{t("trace.in_stock", "en existencia")}</span>
                    {/* Tres piezas de las que solo una sirve no es "tres" ni es
                        "una": la existencia cuenta lo utilizable y las unidades
                        cuentan lo que se tiene. Las dos hacen falta. */}
                    {it.unit_count > 0 && (
                      <em className="trace-units">
                        {it.available_units}/{it.unit_count}{" "}
                        {t("trace.usable_units", "unidades utilizables")}
                      </em>
                    )}
                    {/* El historial, desde aqui y en una ventana: la pregunta
                        -"y esto de donde salio"- se hace sobre el renglon que se
                        tiene delante, y navegar a otra pantalla obligaria a
                        volver y rehacer la busqueda. */}
                    <button
                      type="button"
                      className="button button-quiet trace-historial"
                      onClick={() => setFicha(it)}
                    >
                      <History size={14} />
                      {t("trace.open_history", "Historial")}
                    </button>
                  </div>
                </header>

                {/* Por que salio este resultado. Sin esto, buscar la
                    etiqueta de una pieza y buscar el codigo del producto dan la
                    misma pantalla, y no hay forma de saber si lo que se ve es la
                    pieza que se pidio o el inventario entero de ese modelo. */}
                {it.match_kind === "asset_tag" && it.matched_asset_tags?.length > 0 && (
                  <p className="trace-level trace-level-piece">
                    <Crosshair size={14} />
                    {t("trace.level_piece", "Buscaste una pieza:")}{" "}
                    <strong className="mono">{it.matched_asset_tags.join(", ")}</strong>
                  </p>
                )}
                {it.match_kind === "product_code" && it.unit_count > 0 && (
                  <p className="trace-level trace-level-product">
                    <Package size={14} />
                    {t("trace.level_product", "Buscaste el producto: se muestran sus")}{" "}
                    <strong>{it.unit_count}</strong>{" "}
                    {t("trace.level_product_units", "unidades")}
                  </p>
                )}

                <h3 className="trace-section">
                  <MapPin size={14} /> {t("trace.where", "Dónde está")}
                </h3>
                {/* La ubicacion de la ficha del producto frente a donde estan
                    de verdad las unidades. Cuando no coinciden hay que saberlo:
                    quien va al sitio que dice la ficha no encuentra nada, y sin
                    este aviso lo unico que puede pensar es que se perdio. */}
                {it.home_location?.label
                  && it.locations.length > 0
                  && !it.locations.some((u) => u.id_location === it.home_location.segments?.at(-1)?.id_location) && (
                  <p className="trace-note">
                    <AlertTriangle size={13} />
                    {t("trace.home_differs", "Su ficha dice")}{" "}
                    <strong>{it.home_location.label}</strong>
                    {", "}
                    {t("trace.but_stock_elsewhere", "pero las unidades están en otro sitio.")}
                  </p>
                )}

                {/* Lo que esta fuera, con nombre y con vale. Antes un producto
                    prestado salia con cero en todo y "sin existencia en ninguna
                    ubicacion": el saldo bajo -correctamente, salio del almacen-
                    y nada decia donde fue. La pieza serializada si se veia,
                    porque tiene estado y responsable; lo fungible no. */}
                {it.on_loan && it.on_loan.quantity > 0 && (
                  <div className={`trace-prestado ${it.on_loan.overdue ? "vencido" : ""}`}>
                    <p>
                      <UserRound size={14} />
                      <strong>{it.on_loan.quantity}</strong>{" "}
                      {t("trace.on_loan", "fuera del almacén")}
                      {it.on_loan.overdue && (
                        <em className="trace-prestado-vencido">
                          <AlertTriangle size={12} />
                          {t("trace.on_loan_overdue", "con préstamo vencido")}
                        </em>
                      )}
                    </p>
                    <ul>
                      {it.on_loan.holders.map((h, i) => (
                        <li key={`${h.id_incident}-${i}`}
                            className={h.overdue ? "vencido" : ""}>
                          <strong>{h.holder_name
                            || t("trace.unknown_holder", "sin responsable")}</strong>
                          <span className="muted">
                            {" · "}{t("trace.voucher", "vale")}{" "}
                            <Link className="mono" to={`/vouchers?abrir=${h.id_incident}`}>{h.voucher_folio}</Link>
                            {h.quantity > 1 && ` · ${h.quantity}`}
                            {h.due_date && (
                              <>
                                {" · "}
                                {h.overdue
                                  ? t("trace.was_due", "debió volver el")
                                  : t("trace.due_on", "vence el")}{" "}
                                {new Date(h.due_date).toLocaleDateString("es-MX")}
                              </>
                            )}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {it.locations.length === 0 ? (
                  <p className="muted">
                    {it.on_loan && it.on_loan.quantity > 0
                      ? t("trace.all_on_loan",
                          "Nada en el almacén: todo está fuera.")
                      : t("trace.nowhere", "Sin existencia en ninguna ubicación.")}
                  </p>
                ) : (
                  <ul className="trace-locations">
                    {it.locations.map((u) => (
                      <li key={u.id_location}>
                        {/* La rama entera, no solo el sitio final: "Rack A-1"
                            no dice donde esta el rack, y con cuatro naves hay
                            un Rack A-1 en cada una. */}
                        <span className="trace-path">
                          {(u.path?.length ? u.path : [{
                            id_location: u.id_location,
                            location_description: u.location_description,
                          }]).map((s, i) => (
                            <React.Fragment key={s.id_location}>
                              {i > 0 && <span className="trace-sep">›</span>}
                              {s.is_warehouse ? (
                                <button type="button" className="trace-link"
                                        onClick={() => cambiarFiltro(
                                          "id_location", String(s.id_location))}>
                                  {s.location_description}
                                </button>
                              ) : (
                                <span>{s.location_description}</span>
                              )}
                            </React.Fragment>
                          ))}
                          {u.id_module && <em className="trace-module">{u.id_module}</em>}
                        </span>
                        <strong className="mono">{u.quantity}</strong>
                        {u.reserved > 0 && (
                          <em className="muted">
                            {" "}({u.reserved} {t("trace.reserved", "apartado(s) en un vale")})
                          </em>
                        )}
                      </li>
                    ))}
                  </ul>
                )}

                <h3 className="trace-section">
                  <History size={14} />{" "}
                  {it.unit_count > 0
                    ? t("trace.what_happened_all", "Qué le ha pasado al producto (todas sus unidades)")
                    : t("trace.what_happened", "Qué le ha pasado")}
                </h3>
                {historia.length === 0 ? (
                  <p className="muted">{t("trace.no_history", "Sin movimientos registrados.")}</p>
                ) : (
                  <ul className="trace-history">
                    {historia.map(([clase, dato]) => (
                      <li key={clase} className={TONO_DE_HISTORIA[clase] || "muted"}>
                        <strong className="mono">{dato.unidades}</strong>
                        <span>{t(`trace.kind_${clase}`, clase)}</span>
                        <em>{dato.veces} {dato.veces === 1
                          ? t("trace.time", "vez") : t("trace.times", "veces")}</em>
                      </li>
                    ))}
                  </ul>
                )}

                {pedidas.length > 0 && (
                  <>
                    <h3 className="trace-section">
                      <Crosshair size={14} />{" "}
                      {pedidas.length === 1
                        ? t("trace.the_piece", "La pieza que buscas")
                        : t("trace.the_pieces", "Las piezas que buscas")}
                    </h3>
                    <ul className="trace-assets">
                      {pedidas.map((a) => (
                        <Pieza key={a.id_inventory_asset || a.asset_tag}
                               pieza={a} destacada t={t} />
                      ))}
                    </ul>
                  </>
                )}

                {resto.length > 0 && (
                  <>
                    <h3 className="trace-section">
                      <Wrench size={14} />{" "}
                      {pedidas.length > 0
                        ? t("trace.other_units", "Las otras unidades de este producto")
                        : t("trace.pieces", "Sus piezas")}
                      {" "}<span className="muted">({resto.length})</span>
                    </h3>
                    <ul className="trace-assets">
                      {resto.map((a) => (
                        <Pieza key={a.id_inventory_asset || a.asset_tag} pieza={a} t={t} />
                      ))}
                    </ul>
                  </>
                )}

                {it.last_movement && (
                  <p className="trace-last muted">
                    {t("trace.last_movement", "Último movimiento")}:{" "}
                    {t(`trace.kind_${it.last_movement.clasificacion}`, it.last_movement.clasificacion)}
                    {" "}({it.last_movement.quantity_delta}){" "}
                    {it.last_movement.reason && <>· {it.last_movement.reason} </>}
                    · {formatearFechaHora(it.last_movement.creation_date, "es-MX")}
                  </p>
                )}
              </div>
            </article>
          );
        })}
      </div>

      {/* Paginacion. Antes aqui decia "se muestran los primeros resultados,
          afina la busqueda", que no es una respuesta cuando el filtro ya esta
          puesto y aun quedan doscientas coincidencias: no hay nada que afinar
          y no habia forma de ver el resto. */}
      {/* La misma paginacion que el resto del sistema. La barra propia que
          habia aqui no acotaba el salto: dos clics rapidos en "Siguiente"
          adelantaban el contador mas alla de la ultima pagina y los clics de
          vuelta no hacian nada visible hasta volver al rango. */}
      {datos && (
        <Pagination
          page={datos.page}
          pages={datos.pages}
          total={datos.matches}
          perPage={datos.per_page}
          loading={cargando}
          onChange={setPagina}
          opcionesDeTamano={TAMANOS_DE_PAGINA}
          onTamano={cambiarTamano}
          etiquetaDeTotal={t("trace.many_matches", "productos encontrados")}
        />
      )}

      {ficha && (
        <ProductHistory
          idProduct={ficha.id_product}
          titulo={[ficha.product_code, ficha.descripcion].filter(Boolean).join(" · ")}
          onCerrar={() => setFicha(null)}
        />
      )}

      {fotoAmpliada && (
        <VisorDeFoto
          src={fotoAmpliada.src}
          titulo={fotoAmpliada.titulo}
          descripcion={fotoAmpliada.descripcion}
          onCerrar={() => setFotoAmpliada(null)}
        />
      )}
    </section>
  );
}
