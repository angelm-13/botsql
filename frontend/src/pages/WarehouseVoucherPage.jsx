import { useCallback, useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  AlertTriangle, ArrowLeft, ArrowRight, Check, ClipboardList, Package, Plus,
  RefreshCw, Search, Tag, Trash2, X,
} from "lucide-react";
import {
  closeWarehouseVoucherLine,
  createWarehouseVoucher,
  getAllIncidentType,
  getAllLocation,
  getAllUser,
  getOverdueVoucherLines,
  getWarehouseVoucher,
  listWarehouseVouchers,
  inventoryTrace,
} from "../api";
import Pagination from "../components/Pagination.jsx";
import { useI18n } from "../i18n";
import "../styles/warehouse-voucher.css";

/**
 * Vales de almacen: quien se llevo que, de donde, y si ya lo devolvio.
 *
 * Un vale es una incidencia con renglones. Tiene tipo -prestamo, salida a obra,
 * devolucion-, responsable, estado y fechas; y cada renglon une el vale con un
 * producto, con la pieza concreta si el material se rastrea una por una, y con
 * la ubicacion de la que sale.
 *
 * Tres cosas de esta pantalla que no son decoracion
 * -------------------------------------------------
 * **El estado del vale no se puede capturar.** No hay desplegable de estado, a
 * proposito: el estado se DERIVA de los renglones. Queda uno abierto y el vale
 * sigue abierto; se cierra el ultimo y el vale se cierra. Un desplegable
 * permitiria marcar "terminado" un vale con dos herramientas todavia fuera, que
 * es el estado que mas duele en un almacen.
 *
 * **La pieza se pide o no segun el producto.** Al elegir un producto
 * serializado, el renglon exige decir CUAL pieza -devolver "un desarmador" no
 * cierra el prestamo del desarmador que se llevaron-. Al elegir uno fungible,
 * pide cantidad y no ofrece piezas, porque no las tiene. La pantalla lo cambia
 * sola en vez de dejar que el servidor rechace la captura al final.
 *
 * **Lo vencido se abre primero.** Es la razon de llevar vales: lo que ya debio
 * volver y no ha vuelto. Si no hay nada vencido, la seccion no aparece.
 */

/**
 * Un vale es una SALIDA del almacén en calidad de préstamo, y eso es todo lo
 * que un vale es. Antes se podía elegir entre salida, entrada y traslado, así
 * que un traspaso entre racks se podía capturar como si fuera un vale y la
 * lista de «qué está fuera» contaba cosas que nunca salieron.
 *
 * Los renglones de ENTRADA existen, pero no los captura nadie: los escribe la
 * devolución, y por eso un vale devuelto tiene el doble de renglones.
 */
const SALIDA = "salida";

export default function WarehouseVoucherPage() {
  const { t } = useI18n();
  const [vencidos, setVencidos] = useState([]);
  const [tipos, setTipos] = useState([]);
  const [ubicaciones, setUbicaciones] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");

  // El vale que se esta capturando, y el que se esta consultando.
  const [borrador, setBorrador] = useState(null);
  const [consultado, setConsultado] = useState(null);
  // La lista: lo que se ve sin tener que saberse un numero de memoria.
  const [lista, setLista] = useState(null);
  const [pagina, setPagina] = useState(1);
  const [soloAbiertos, setSoloAbiertos] = useState(true);
  const [idBuscado, setIdBuscado] = useState("");

  const traducir = useRef(t);
  traducir.current = t;

  const decirError = (e, porOmision) => setError(e?.payload?.error_key
    ? traducir.current(e.payload.error_key)
    : traducir.current("errors.request_failed", porOmision));

  const cargar = useCallback(async () => {
    setCargando(true);
    setError("");
    try {
      const [venc, tip, ubi, usr] = await Promise.all([
        getOverdueVoucherLines(),
        getAllIncidentType({ per_page: 100 }),
        getAllLocation({ per_page: 200 }),
        getAllUser({ per_page: 200 }),
      ]);
      setVencidos(venc?.items || []);
      setTipos(tip?.items || []);
      setUbicaciones(ubi?.items || []);
      setUsuarios(usr?.items || []);
    } catch (e) {
      decirError(e, "No se pudo cargar la pantalla de vales.");
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => { cargar(); }, [cargar]);

  const abrirBorrador = () => setBorrador({
    id_incident_type: tipos[0]?.id_incident_type || "",
    id_user: "",
    due_date: "",
    note: "",
    lines: [],
  });

  const listar = useCallback(async () => {
    setError("");
    try {
      setLista(await listWarehouseVouchers({
        q: idBuscado.trim() || undefined,
        only_open: soloAbiertos ? 1 : undefined,
        page: pagina,
        per_page: 15,
      }));
    } catch (e) {
      setLista(null);
      decirError(e, "No se pudo cargar la lista de vales.");
    }
  }, [idBuscado, soloAbiertos, pagina]);

  // Al escribir se espera: una peticion por tecla con 139 vales detras es
  // pedirle al servidor una consulta que nadie va a leer.
  useEffect(() => {
    const temporizador = setTimeout(() => { listar(); }, 300);
    return () => clearTimeout(temporizador);
  }, [listar]);

  // Cambiar el texto o el filtro vuelve a la primera pagina: quien esta en la 7
  // y escribe algo nuevo no quiere la pagina 7 de otro resultado.
  useEffect(() => { setPagina(1); }, [idBuscado, soloAbiertos]);

  const consultar = async (id) => {
    const numero = String(id || "").trim();
    if (!numero) return;
    setError("");
    try {
      setConsultado(await getWarehouseVoucher(numero));
    } catch (e) {
      setConsultado(null);
      decirError(e, "No se encontró ese vale.");
    }
  };

  const guardar = async () => {
    if (!borrador.lines.length) return;
    setError("");
    setAviso("");
    try {
      const creado = await createWarehouseVoucher({
        ...borrador,
        lines: borrador.lines.map((l) => ({
          id_product: l.id_product,
          id_inventory_asset: l.id_inventory_asset || undefined,
          quantity: l.id_inventory_asset ? undefined : l.quantity,
          id_location_from: l.id_location_from || undefined,
          note: l.note || undefined,
        })),
      });
      setBorrador(null);
      setConsultado(await getWarehouseVoucher(creado.voucher.id_incident));
      setAviso(`${t("voucher.created", "Vale abierto")} #${creado.voucher.id_incident}`);
      await cargar();
    } catch (e) {
      decirError(e, "No se pudo abrir el vale.");
    }
  };

  const cerrar = async (idLinea) => {
    setError("");
    try {
      const r = await closeWarehouseVoucherLine(idLinea);
      setConsultado(await getWarehouseVoucher(r.voucher.id_incident));
      setAviso(r.closed_the_voucher
        ? t("voucher.closed_all", "Era el último renglón: el vale queda cerrado.")
        : t("voucher.closed_one", "Renglón cerrado. El vale sigue abierto."));
      await cargar();
    } catch (e) {
      decirError(e, "No se pudo cerrar el renglón.");
    }
  };

  const nombreDe = (idUsuario) => {
    const u = usuarios.find((x) => Number(x.id_user) === Number(idUsuario));
    return u?.full_name || u?.username || (idUsuario ? `#${idUsuario}` : "");
  };
  const sitioDe = (idUbicacion) => {
    const u = ubicaciones.find((x) => Number(x.id_location) === Number(idUbicacion));
    return u?.location_description || (idUbicacion ? `#${idUbicacion}` : "");
  };

  return (
    <section className="page vale-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">{t("voucher.eyebrow", "Almacén")}</p>
          <h1>{t("voucher.title", "Vales de almacén")}</h1>
          <p className="muted">
            {t("voucher.subtitle",
              "Quién se llevó qué, de dónde, y si ya lo devolvió. El vale se cierra solo cuando vuelve su último renglón.")}
          </p>
        </div>
        <div className="vale-acciones-cabecera">
          <button className="button" onClick={cargar} disabled={cargando}>
            <RefreshCw size={16} />
            {cargando ? t("common.loading", "Cargando…") : t("common.refresh", "Actualizar")}
          </button>
          <button className="button button-primary" onClick={abrirBorrador}
                  disabled={cargando || !tipos.length}>
            <Plus size={16} />
            {t("voucher.new", "Levantar vale")}
          </button>
        </div>
      </header>

      {error && <p className="error">{error}</p>}
      {aviso && <p className="vale-aviso"><Check size={15} />{aviso}</p>}

      {/* Lo vencido primero: es la razon de llevar vales. Si no hay nada, la
          seccion no aparece en vez de decir "0 vencidos", que es ruido. */}
      {vencidos.length > 0 && (
        <section className="vale-vencidos">
          <h2>
            <AlertTriangle size={16} />
            {t("voucher.overdue", "Ya debió volver y no ha vuelto")}
            <span>{vencidos.length}</span>
          </h2>
          <ul>
            {vencidos.map((linea) => (
              <li key={linea.id_nm_incident_product}>
                <button className="vale-enlace"
                        onClick={() => consultar(linea.id_incident)}>
                  {t("voucher.voucher_n", "Vale")} #{linea.id_incident}
                </button>
                <span className="mono">
                  {linea.id_inventory_asset
                    ? `${t("voucher.piece", "pieza")} #${linea.id_inventory_asset}`
                    : `${linea.quantity} ${t("voucher.units", "unidades")}`}
                </span>
                <span className="muted">
                  {t("voucher.was_due", "vencía")}{" "}
                  {new Date(linea.due_date).toLocaleDateString("es-MX")}
                </span>
                <button className="button button-quiet"
                        onClick={() => cerrar(linea.id_nm_incident_product)}>
                  <Check size={14} />
                  {t("voucher.close_line", "Marcar devuelto")}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {borrador && (
        <Borrador
          borrador={borrador}
          setBorrador={setBorrador}
          tipos={tipos}
          ubicaciones={ubicaciones}
          usuarios={usuarios}
          onGuardar={guardar}
          onCancelar={() => setBorrador(null)}
          t={t}
        />
      )}

      <section className="vale-consulta">
        <h2>{t("voucher.lookup", "Vales")}</h2>
        <form className="vale-buscador"
              onSubmit={(e) => { e.preventDefault(); consultar(idBuscado); }}>
          <Search size={16} />
          <input
            value={idBuscado}
            onChange={(e) => setIdBuscado(e.target.value)}
            placeholder={t("voucher.lookup_placeholder",
              "Folio del vale o nombre del responsable")}
            aria-label={t("voucher.lookup_placeholder", "Buscar un vale")}
          />
          <button className="button" type="submit">
            {t("common.search", "Buscar")}
          </button>
        </form>

        {/* La lista. El buscador de arriba la filtra y tambien abre un vale
            concreto: el mismo campo sirve para "vale 112" -con el papel en la
            mano- y para "que trae Maximino". */}
        {lista && !consultado && (
          <>
            <div className="vale-lista-cabecera">
              <label className="vale-solo-abiertos">
                <input type="checkbox" checked={soloAbiertos}
                       onChange={(e) => setSoloAbiertos(e.target.checked)} />
                {t("voucher.only_open", "Solo con material fuera")}
              </label>
              <span className="muted">
                <strong>{lista.total}</strong>{" "}
                {lista.total === 1
                  ? t("voucher.one_voucher", "vale")
                  : t("voucher.many_vouchers", "vales")}
                {lista.scoped_to_actor && (
                  <em>{" · "}{t("voucher.only_mine", "solo los tuyos")}</em>
                )}
              </span>
            </div>

            {lista.items.length === 0 ? (
              <p className="muted">
                {idBuscado.trim()
                  ? t("voucher.no_matches",
                      "Ningún vale con ese folio ni con ese responsable.")
                  : t("voucher.none_open",
                      "No hay vales con material fuera.")}
              </p>
            ) : (
              <ul className="vale-lista">
                {lista.items.map((v) => (
                  <li key={v.id_incident}>
                    <button type="button" onClick={() => consultar(v.id_incident)}>
                      {/* El folio es el numero con el que la gente lo conoce:
                          el del sistema anterior cuando lo trae. */}
                      <strong className="mono">{v.folio}</strong>
                      <span className="vale-lista-quien">
                        {v.holder_name || t("voucher.no_holder", "sin responsable")}
                      </span>
                      <span className={`vale-lista-estado ${v.incident_status}`}>
                        {t(`voucher.status_${v.incident_status}`, v.incident_status)}
                      </span>
                      <span className="muted vale-lista-cuenta">
                        {v.open_lines > 0
                          ? `${v.open_lines} ${t("voucher.out", "fuera")}`
                          : t("voucher.all_back", "todo devuelto")}
                        {" · "}{v.total_lines} {t("voucher.lines", "renglones")}
                      </span>
                      {v.incident_date && (
                        <span className="muted">
                          {new Date(v.incident_date).toLocaleDateString("es-MX")}
                        </span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}

            <Pagination
              page={lista.page}
              pages={lista.pages}
              total={lista.total}
              perPage={lista.per_page}
              onChange={setPagina}
              etiquetaDeTotal={t("voucher.many_vouchers", "vales")}
            />
          </>
        )}

        {consultado && (
          <>
            <button className="button button-quiet vale-volver"
                    onClick={() => setConsultado(null)}>
              <ArrowLeft size={15} />
              {t("voucher.back_to_list", "Volver a la lista")}
            </button>
            <Vale vale={consultado} onCerrar={cerrar} nombreDe={nombreDe}
                  sitioDe={sitioDe} t={t} />
          </>
        )}
      </section>
    </section>
  );
}

/** El vale con sus renglones, y el estado derivado bien visible. */
function Vale({ vale, onCerrar, nombreDe, sitioDe, t }) {
  const cabecera = vale.voucher || {};
  const cerrado = String(cabecera.incident_status || "") === "cerrado";

  return (
    <article className={`vale-tarjeta ${cerrado ? "vale-cerrado" : "vale-abierto"}`}>
      <header>
        <div>
          <h3>
            <ClipboardList size={16} />
            {t("voucher.voucher_n", "Vale")} #{cabecera.id_incident}
          </h3>
          <p className="muted">
            {t("voucher.holder", "Responsable")}: <strong>{nombreDe(cabecera.id_user)}</strong>
            {cabecera.note && <> · {cabecera.note}</>}
          </p>
        </div>
        {/* El estado se muestra, no se elige: lo derivan los renglones. */}
        <span className={`vale-estado ${cerrado ? "es-cerrado" : "es-abierto"}`}>
          {cerrado
            ? t("voucher.status_closed", "Cerrado")
            : t("voucher.status_open", "Abierto")}
          <em>
            {vale.open_lines} {t("voucher.of", "de")} {vale.total_lines}{" "}
            {t("voucher.open_lines", "sin devolver")}
          </em>
        </span>
      </header>

      <ul className="vale-renglones">
        {(vale.lines || []).map((linea) => {
          const abierto = !linea.close_date;
          return (
            <li key={linea.id_nm_incident_product}
                className={[
                  abierto ? "" : "devuelto",
                  linea.direction === SALIDA ? "vale-salida" : "vale-entrada",
                ].filter(Boolean).join(" ")}>
              <span className="vale-que">
                {linea.id_inventory_asset ? <Tag size={13} /> : <Package size={13} />}
                {linea.id_inventory_asset
                  ? `${t("voucher.piece", "pieza")} #${linea.id_inventory_asset}`
                  : `${linea.quantity} ${t("voucher.units", "unidades")}`}
                <em className="muted">
                  {t("voucher.product", "producto")} #{linea.id_product}
                </em>
              </span>
              <span className="vale-donde muted">
                {sitioDe(linea.id_location_from)}
                {linea.id_location_to && (
                  <>
                    {" "}<ArrowRight size={12} />{" "}
                    {sitioDe(linea.id_location_to)}
                  </>
                )}
              </span>
              {/* La existencia del producto, que es la cifra con la que se
                  firma: "salen 5 de 40" y "salen 5 de 5" son la misma linea con
                  consecuencias distintas. */}
              <span className="muted vale-existencia">
                {t("voucher.on_hand", "quedan")} <strong>{linea.stock_on_hand}</strong>
              </span>
              {abierto ? (
                <button className="button button-quiet"
                        onClick={() => onCerrar(linea.id_nm_incident_product)}>
                  <Check size={14} />
                  {t("voucher.close_line", "Marcar devuelto")}
                </button>
              ) : (
                <span className="vale-devuelto">
                  <Check size={13} />
                  {new Date(linea.close_date).toLocaleDateString("es-MX")}
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </article>
  );
}

Vale.propTypes = {
  vale: PropTypes.shape({
    voucher: PropTypes.object,
    lines: PropTypes.array,
    open_lines: PropTypes.number,
    total_lines: PropTypes.number,
  }).isRequired,
  onCerrar: PropTypes.func.isRequired,
  nombreDe: PropTypes.func.isRequired,
  sitioDe: PropTypes.func.isRequired,
  t: PropTypes.func.isRequired,
};

/** La captura de un vale: cabecera y renglones. */
function Borrador({ borrador, setBorrador, tipos, ubicaciones, usuarios,
                    onGuardar, onCancelar, t }) {
  const [busqueda, setBusqueda] = useState("");
  const [candidatos, setCandidatos] = useState([]);
  const [buscando, setBuscando] = useState(false);

  // Se busca en el almacen con el mismo rastreo de la pantalla de Localizar:
  // devuelve el producto, su modo de rastreo y sus piezas, que es exactamente
  // lo que el renglon necesita para saber si pedir pieza o cantidad.
  useEffect(() => {
    if (busqueda.trim().length < 2) { setCandidatos([]); return undefined; }
    const temporizador = setTimeout(async () => {
      setBuscando(true);
      try {
        const r = await inventoryTrace({ q: busqueda, per_page: 8 });
        setCandidatos(r?.items || []);
      } catch { setCandidatos([]); } finally { setBuscando(false); }
    }, 350);
    return () => clearTimeout(temporizador);
  }, [busqueda]);

  const agregar = (producto, pieza) => {
    const serializado = producto.tracking_mode === "serializado";
    setBorrador({
      ...borrador,
      lines: [...borrador.lines, {
        clave: `${producto.id_product}-${pieza?.id_inventory_asset || Date.now()}`,
        id_product: producto.id_product,
        etiqueta: producto.product_code || `#${producto.id_product}`,
        descripcion: producto.descripcion || "",
        id_inventory_asset: pieza?.id_inventory_asset || null,
        asset_tag: pieza?.asset_tag || null,
        quantity: serializado ? 1 : 1,
        serializado,
        id_location_from: pieza?.id_location
          || producto.locations?.[0]?.id_location || "",
      }],
    });
    setBusqueda("");
    setCandidatos([]);
  };

  const cambiar = (indice, cambios) => setBorrador({
    ...borrador,
    lines: borrador.lines.map((l, i) => (i === indice ? { ...l, ...cambios } : l)),
  });
  const quitar = (indice) => setBorrador({
    ...borrador,
    lines: borrador.lines.filter((_, i) => i !== indice),
  });

  // La fecha de regreso y el motivo van siempre, y el origen en lo fungible.
  // Se comprueba aqui para decirlo antes de mandar, no despues de que el
  // servidor conteste; el servidor lo exige igual, que es lo que cuenta.
  const listo = borrador.lines.length > 0 && borrador.id_incident_type
    && borrador.id_user && borrador.due_date && borrador.note.trim()
    && borrador.lines.every((l) => l.serializado || l.id_location_from);

  return (
    <section className="vale-borrador">
      <header>
        <h2><Plus size={16} />{t("voucher.new", "Levantar vale")}</h2>
        <button className="mt-icono" onClick={onCancelar}
                aria-label={t("common.cancel", "Cancelar")}>
          <X size={16} />
        </button>
      </header>

      <div className="vale-cabecera">
        <label className="field">
          <span>{t("voucher.type", "Tipo de vale")}</span>
          <select value={borrador.id_incident_type}
                  onChange={(e) => setBorrador(
                    { ...borrador, id_incident_type: e.target.value })}>
            {tipos.map((x) => (
              <option key={x.id_incident_type} value={x.id_incident_type}>
                {x.incident_type_description}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>{t("voucher.holder", "Responsable")}</span>
          <select value={borrador.id_user}
                  onChange={(e) => setBorrador({ ...borrador, id_user: e.target.value })}>
            <option value="">{t("voucher.pick_holder", "Elige a quién se le entrega")}</option>
            {usuarios.map((u) => (
              <option key={u.id_user} value={u.id_user}>
                {u.full_name || u.username || `#${u.id_user}`}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          {/* Sin fecha de regreso el vale nunca esta vencido, asi que nadie lo
              reclama: un prestamo sin fecha es una baja disfrazada. */}
          <span>{t("voucher.due", "Debe volver el")}</span>
          <input type="date" value={borrador.due_date} required
                 min={new Date().toISOString().slice(0, 10)}
                 onChange={(e) => setBorrador({ ...borrador, due_date: e.target.value })} />
        </label>
        <label className="field field-ancho">
          <span>{t("voucher.note", "Motivo")} *</span>
          <input value={borrador.note} maxLength={300} required
                 placeholder={t("voucher.note_placeholder", "Por ejemplo: Obra Norte")}
                 onChange={(e) => setBorrador({ ...borrador, note: e.target.value })} />
        </label>
      </div>

      <h3>{t("voucher.what", "Qué se lleva")}</h3>
      <div className="vale-buscador vale-buscador-producto">
        <Search size={16} />
        <input
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          placeholder={t("voucher.search_product",
            "Busca por código, descripción o etiqueta de la pieza")}
          aria-label={t("voucher.search_product", "Buscar producto")}
        />
        {buscando && <span className="muted">{t("common.loading", "…")}</span>}
      </div>

      {candidatos.length > 0 && (
        <ul className="vale-candidatos">
          {candidatos.map((p) => (
            <li key={p.id_product}>
              <div className="vale-candidato-cabecera">
                <strong className="mono">{p.product_code || `#${p.id_product}`}</strong>
                <span>{p.descripcion}</span>
                <em className="muted">
                  {p.tracking_mode === "serializado"
                    ? t("voucher.by_piece", "por pieza")
                    : `${p.total} ${t("voucher.in_stock", "en existencia")}`}
                </em>
                {/* Lo fungible se agrega directo; lo serializado obliga a
                    elegir la pieza, porque devolver "un desarmador" no cierra
                    el prestamo del que se llevaron. */}
                {p.tracking_mode !== "serializado" && (
                  <button className="button button-quiet" onClick={() => agregar(p)}>
                    <Plus size={14} />{t("common.add", "Agregar")}
                  </button>
                )}
              </div>
              {p.tracking_mode === "serializado" && (
                <ul className="vale-piezas">
                  {(p.assets || []).filter((a) => a.status === "disponible").length === 0 ? (
                    <li className="muted">
                      {t("voucher.no_available",
                        "Ninguna pieza disponible: están prestadas, en reparación o extraviadas.")}
                    </li>
                  ) : (p.assets || [])
                    .filter((a) => a.status === "disponible")
                    .map((a) => (
                      <li key={a.id_inventory_asset}>
                        <span className="mono">{a.asset_tag}</span>
                        <span className="muted">{a.location_path_label
                          || a.location_description || ""}</span>
                        <button className="button button-quiet"
                                onClick={() => agregar(p, a)}>
                          <Plus size={14} />{t("common.add", "Agregar")}
                        </button>
                      </li>
                    ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      )}

      {borrador.lines.length === 0 ? (
        <p className="muted">
          {t("voucher.no_lines_yet", "Sin renglones. Un vale vacío no se puede abrir.")}
        </p>
      ) : (
        <ul className="vale-renglones vale-renglones-edicion">
          {borrador.lines.map((linea, indice) => (
            <li key={linea.clave}>
              <span className="vale-que">
                {linea.serializado ? <Tag size={13} /> : <Package size={13} />}
                <strong className="mono">{linea.etiqueta}</strong>
                {linea.asset_tag && <span className="mono">{linea.asset_tag}</span>}
              </span>

              {/* La cantidad solo existe para lo fungible: una pieza es una
                  pieza, y el servidor y la base lo garantizan igual. */}
              {!linea.serializado && (
                <label className="vale-mini">
                  <span>{t("voucher.quantity", "Cantidad")}</span>
                  <input type="number" min="1" value={linea.quantity}
                         onChange={(e) => cambiar(indice,
                           { quantity: Number(e.target.value) || 1 })} />
                </label>
              )}

              {/* De donde sale. En una pieza se sabe -es donde esta- pero en
                  lo fungible hay que decirlo: descontar 5 sacos "del almacen"
                  sin decir de cual deja el saldo por ubicacion mintiendo, y ese
                  es el dato con el que alguien va a buscarlos. */}
              <label className={`vale-mini ${!linea.serializado
                && !linea.id_location_from ? "vale-falta" : ""}`}>
                <span>
                  {t("voucher.from", "Sale de")}
                  {!linea.serializado && " *"}
                </span>
                <select value={linea.id_location_from}
                        onChange={(e) => cambiar(indice,
                          { id_location_from: e.target.value })}>
                  <option value="">—</option>
                  {ubicaciones.map((u) => (
                    <option key={u.id_location} value={u.id_location}>
                      {u.location_description}
                    </option>
                  ))}
                </select>
              </label>

              <button className="mt-icono mt-icono-borrar" onClick={() => quitar(indice)}
                      aria-label={t("common.delete", "Quitar")}>
                <Trash2 size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}

      <footer className="vale-pie">
        <button className="button button-primary" onClick={onGuardar} disabled={!listo}>
          {t("voucher.open", "Abrir vale")}
        </button>
        <button className="button button-quiet" onClick={onCancelar}>
          {t("common.cancel", "Cancelar")}
        </button>
        {!listo && borrador.lines.length > 0 && (
          <span className="muted">
            {t("voucher.missing",
              "Falta el responsable, o el destino de un renglón que cambia de ubicación.")}
          </span>
        )}
      </footer>
    </section>
  );
}

Borrador.propTypes = {
  borrador: PropTypes.shape({
    id_incident_type: PropTypes.any,
    id_user: PropTypes.any,
    due_date: PropTypes.string,
    note: PropTypes.string,
    lines: PropTypes.array,
  }).isRequired,
  setBorrador: PropTypes.func.isRequired,
  tipos: PropTypes.array.isRequired,
  ubicaciones: PropTypes.array.isRequired,
  usuarios: PropTypes.array.isRequired,
  onGuardar: PropTypes.func.isRequired,
  onCancelar: PropTypes.func.isRequired,
  t: PropTypes.func.isRequired,
};
