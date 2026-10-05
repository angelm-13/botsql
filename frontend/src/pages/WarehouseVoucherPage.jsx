import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import VisorDeFoto from "../components/VisorDeFoto";
import EmployeeVoucherHistory from "../components/EmployeeVoucherHistory.jsx";
import {
  AlertTriangle, ArrowLeft, ArrowRight, Check, ClipboardList, History, Package, Plus,
  ImageOff, Printer, RefreshCw, Search, Tag, Trash2, X,
} from "lucide-react";
import {
  authorizeWarehouseVoucher,
  downloadWarehouseVoucherPdf,
  closeWarehouseVoucherLine,
  deliverWarehouseVoucherLine,
  confirmWarehouseVoucherLineCustody,
  createWarehousePrevoucher,
  createWarehouseVoucher,
  getIncidentTypeOptions,
  getLocationOptions,
  getMyPermissions,
  getUserOptions,
  getOverdueVoucherLines,
  getProyectOptions,
  getWarehouseVoucher,
  urlDeArchivo,
  listWarehouseVouchers,
  inventoryTrace,
} from "../api";
import Pagination from "../components/Pagination.jsx";
import { agruparRenglones } from "../utils/renglonesDelVale";
import { useI18n } from "../i18n";
import "../styles/warehouse-voucher.css";
import PageHeader from "../components/PageHeader.jsx";

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
 * devolución, y por eso un vale devuelto tiene el doble de renglones a nivel
 * de base de datos. En pantalla se agrupan de vuelta a uno por prestamo real
 * -ver `agruparRenglones`, en `utils/renglonesDelVale.js`-, porque mostrar el
 * doble ahi confundía mas de lo que aclaraba.
 */

// Mismo patron que `ProjectManagementPage.jsx`: el actor y sus capacidades
// deciden que boton ofrecer. El servidor sigue siendo quien manda -cada ruta
// vuelve a comprobar la capacidad exacta-, pero un boton que el servidor
// siempre va a rechazar no debe estar ahi para empezar: confunde mas de lo
// que "cuida" un permiso que la pantalla ya conoce.
function actorGuardado() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch { return {}; }
}
function esPrivilegiado(actor) {
  return Boolean(actor.is_superuser || actor.is_bootstrap_admin || actor.username === "admin1");
}
function tieneCapacidad(permisos, entidad, campo = "scope_read") {
  const fila = permisos.find((p) => p.entity_name === entidad);
  return Number(fila?.[campo] || 0) !== 0;
}

// Los estados por los que se puede filtrar la lista. `borrador` va primero
// despues de "todos" porque es el que pide accion: un prevale sin autorizar es
// material que alguien esta esperando.
const ESTADOS_DE_VALE = [
  { valor: "", clave: "all", texto: "Todos" },
  { valor: "borrador", clave: "draft", texto: "Por autorizar" },
  { valor: "abierto", clave: "open", texto: "Abiertos" },
  { valor: "cerrado", clave: "closed", texto: "Cerrados" },
];

export default function WarehouseVoucherPage() {
  const { t } = useI18n();
  const actor = useMemo(actorGuardado, []);
  const privilegiado = esPrivilegiado(actor);
  const [permisos, setPermisos] = useState([]);
  // Puede abrir el vale directo -- saca material de inmediato, capacidad
  // `warehouse_voucher` (Almacenista). Sin ella solo queda pedir un borrador.
  const puedeAbrirValeDirecto = privilegiado || tieneCapacidad(permisos, "warehouse_voucher", "scope_create");
  // Autorizar y entregar es OTRA capacidad, aparte de abrir el vale a
  // proposito (separacion de deberes: quien pide no autoriza lo suyo).
  const puedeAutorizar = privilegiado || tieneCapacidad(permisos, "warehouse_voucher_authorize", "scope_create");
  // Cerrar un renglon (`/return`, "Marcar devuelto") lo guarda la ruta con
  // `warehouse_voucher` en UPDATE -- quien no puede abrir un vale tampoco
  // puede cerrarlo, aunque sea el suyo.
  const puedeCerrarRenglon = privilegiado || tieneCapacidad(permisos, "warehouse_voucher", "scope_update");
  // Sin `warehouse_voucher` pero con `warehouse_prevoucher`: solo puede pedir
  // material, nunca surtirlo. Es el caso de Supervisor -y de Administrator
  // real, que tiene la misma separacion-, nunca el de Almacenista.
  const soloPuedeSolicitar = !puedeAbrirValeDirecto
    && (privilegiado || tieneCapacidad(permisos, "warehouse_prevoucher", "scope_create"));
  const [vencidos, setVencidos] = useState([]);
  const [tipos, setTipos] = useState([]);
  const [ubicaciones, setUbicaciones] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  // Las obras a las que se le puede ligar un vale. Se pide con `/options`,
  // que no exige el modulo `operaciones` -- el Almacenista no lo tiene.
  const [proyectos, setProyectos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");

  // El vale que se esta capturando, y el que se esta consultando.
  const [borrador, setBorrador] = useState(null);
  const [consultado, setConsultado] = useState(null);
  const [imprimiendo, setImprimiendo] = useState(false);
  // La foto que se esta mirando en grande, o null. Vive aqui y no en
  // cada ficha para que solo pueda haber una abierta.
  const [fotoAmpliada, setFotoAmpliada] = useState(null);
  // El empleado cuyo historial se esta mirando, o null. Vive aqui por el
  // mismo motivo que la foto: una sola ficha abierta a la vez.
  const [historialEmpleado, setHistorialEmpleado] = useState(null);
  // La lista: lo que se ve sin tener que saberse un numero de memoria.
  const [lista, setLista] = useState(null);
  const [pagina, setPagina] = useState(1);
  const [soloAbiertos, setSoloAbiertos] = useState(true);
  // El estado por el que se filtra la lista. "" es todos.
  //
  // `borrador` es el que hacia falta: los prevales pendientes de autorizar no
  // se pueden encontrar de otra forma -- no tienen material fuera, asi que el
  // filtro de "solo con material fuera" los esconde, que es justo al reves de
  // lo que necesita quien tiene que autorizarlos.
  const [estado, setEstado] = useState("");
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
      // Cada llamada se atrapa por separado: un rol de almacen no lee todas
      // estas entidades por igual (ej. antes de hoy, ninguno tenia lectura
      // de incident_type -- por eso los tipos vienen de `/incident_type/options`,
      // sin permiso de entidad, como usuarios y proyectos), y un solo 403 aqui tumbaba las demas tambien --
      // dejaba "Levantar vale" deshabilitado por falta de tipos aunque
      // ubicaciones/usuarios si hubieran cargado bien.
      const [venc, tip, ubi, usr, permisosPayload] = await Promise.all([
        getOverdueVoucherLines().catch(() => ({ items: [] })),
        getIncidentTypeOptions().catch(() => []),
        // `/location/options`, no `/location/`: la lista completa exige leer
        // `location` (modulo de inventario) y un Supervisor, que solo pide
        // material, se quedaba sin nombres -- el "Sale de" salia en blanco.
        getLocationOptions().catch(() => []),
        getUserOptions().catch(() => []),
        privilegiado
          ? Promise.resolve({ entity_permissions: [] })
          : getMyPermissions().catch(() => ({ entity_permissions: [] })),
      ]);
      setVencidos(venc?.items || []);
      setTipos(Array.isArray(tip) ? tip : tip?.items || []);
      setUbicaciones(Array.isArray(ubi) ? ubi : ubi?.items || []);
      setUsuarios(Array.isArray(usr) ? usr : usr?.items || []);
      const filasPermiso = permisosPayload.entity_permissions || [];
      setPermisos(filasPermiso);

      // La lista de proyectos depende de la capacidad que se acaba de leer:
      // quien solo puede SOLICITAR material -Supervisor, o Administrator
      // real- pide `mine=1` y ve nada mas los suyos, porque el es siempre el
      // responsable. Almacenista sigue viendo la lista completa -- necesita
      // reconocer cualquier obra que le mencionen al surtir.
      const soloSolicitaAhora = !(privilegiado
          || tieneCapacidad(filasPermiso, "warehouse_voucher", "scope_create"))
        && (privilegiado || tieneCapacidad(filasPermiso, "warehouse_prevoucher", "scope_create"));
      const proy = await getProyectOptions(soloSolicitaAhora ? { mine: 1 } : {})
        .catch(() => []);
      setProyectos(Array.isArray(proy) ? proy : proy?.items || []);
    } catch (e) {
      decirError(e, "No se pudo cargar la pantalla de vales.");
    } finally {
      setCargando(false);
    }
  }, [privilegiado]);

  useEffect(() => { cargar(); }, [cargar]);

  const abrirBorrador = () => setBorrador({
    id_incident_type: tipos[0]?.id_incident_type || "",
    // Por omision, quien pide el prevale es su propio responsable -- el caso
    // mas comun -- pero NO es fijo (pedido de negocio, 2026-09-30): el
    // supervisor no siempre puede salir de planta, y a veces manda a alguien
    // mas -un operador- por la herramienta. Sigue siendo el mismo quien
    // captura el prevale (`created_by`, sin cambios); solo el responsable
    // ante almacen puede ser otra persona.
    id_user: soloPuedeSolicitar ? String(actor.id_user || "") : "",
    // El proyecto al que va el material. Vacio por opcion: no todo prestamo
    // es de un proyecto -- una herramienta para el propio taller no lo es.
    id_proyect: "",
    due_date: "",
    note: "",
    lines: [],
  });

  const listar = useCallback(async () => {
    setError("");
    try {
      setLista(await listWarehouseVouchers({
        q: idBuscado.trim() || undefined,
        // Los dos filtros no se combinan: un borrador no tiene nada fuera, asi
        // que pedir "borrador" y "solo con material fuera" a la vez no
        // devolveria nada. Al elegir un estado, el otro filtro se ignora.
        only_open: (soloAbiertos && !estado) ? 1 : undefined,
        status: estado || undefined,
        page: pagina,
        per_page: 15,
      }));
    } catch (e) {
      setLista(null);
      decirError(e, "No se pudo cargar la lista de vales.");
    }
  }, [idBuscado, soloAbiertos, estado, pagina]);

  // Al escribir se espera: una peticion por tecla con 139 vales detras es
  // pedirle al servidor una consulta que nadie va a leer.
  useEffect(() => {
    const temporizador = setTimeout(() => { listar(); }, 300);
    return () => clearTimeout(temporizador);
  }, [listar]);

  // Cambiar el texto o el filtro vuelve a la primera pagina: quien esta en la 7
  // y escribe algo nuevo no quiere la pagina 7 de otro resultado.
  useEffect(() => { setPagina(1); }, [idBuscado, soloAbiertos, estado]);

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

  /**
   * Guarda el vale, o lo deja en borrador.
   *
   * `comoPrevale` elige la ruta, y con ella el permiso: `/prevouchers` pide
   * `warehouse_prevoucher` y no mueve el almacen; `/vouchers` pide
   * `warehouse_voucher` y saca el material. El servidor sigue siendo quien
   * decide de verdad -esta funcion no cambia-, pero el boton de "Abrir vale"
   * ya no se ofrece a quien la pantalla sabe que no tiene esa capacidad: ver
   * un boton que siempre va a rechazar el servidor confunde mas de lo que
   * "protege" un permiso que ya se conoce de antemano.
   */
  const guardar = async (comoPrevale = false) => {
    if (!borrador.lines.length) return;
    setError("");
    setAviso("");
    const alta = comoPrevale ? createWarehousePrevoucher : createWarehouseVoucher;
    try {
      const creado = await alta({
        ...borrador,
        id_proyect: borrador.id_proyect || undefined,
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
      setAviso(`${comoPrevale
        ? t("voucher.drafted", "Prevale guardado, pendiente de autorizar")
        : t("voucher.created", "Vale abierto")} #${creado.voucher.id_incident}`);
      await cargar();
    } catch (e) {
      decirError(e, comoPrevale
        ? "No se pudo guardar el prevale."
        : "No se pudo abrir el vale.");
    }
  };

  /** Autoriza un borrador: lo abre y saca el material. */
  const autorizar = async (idVale) => {
    setError("");
    setAviso("");
    try {
      const r = await authorizeWarehouseVoucher(idVale);
      setConsultado(await getWarehouseVoucher(r.voucher.id_incident));
      setAviso(t("voucher.authorized",
        "Vale autorizado: el material salió del almacén."));
      await cargar();
    } catch (e) {
      decirError(e, "No se pudo autorizar el vale.");
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

  // A que operador u otro supervisor se le entrega esta pieza -- sin sacarla
  // del almacen otra vez ni cerrar el prestamo, solo constancia de por donde
  // anda mientras el vale sigue abierto.
  const entregarA = async (idLinea, idUsuarioEntrega) => {
    if (!idUsuarioEntrega) return;
    setError("");
    try {
      const r = await deliverWarehouseVoucherLine(idLinea, { id_user: idUsuarioEntrega });
      setConsultado(await getWarehouseVoucher(r.id_incident));
    } catch (e) {
      decirError(e, "No se pudo registrar la entrega.");
    }
  };

  // El supervisor dueño del vale confirma que ya recupero la pieza de manos
  // del operador al que se la habia entregado.
  const confirmarCustodia = async (idLinea) => {
    setError("");
    try {
      const r = await confirmWarehouseVoucherLineCustody(idLinea);
      setConsultado(await getWarehouseVoucher(r.id_incident));
    } catch (e) {
      decirError(e, "No se pudo confirmar la recepción.");
    }
  };

  // Quien puede entregar una pieza a un operador o confirmar que la
  // recupero: el responsable DE ESTE vale (normalmente Supervisor, que solo
  // tiene `warehouse_prevoucher`, nunca `warehouse_voucher`) o quien opera
  // el almacen. Se calcula por vale, no una vez -- el mismo actor es
  // responsable de unos y no de otros.
  const puedeGestionarCustodia = (vale) => privilegiado
    || Number(vale?.id_user) === Number(actor.id_user)
    || puedeCerrarRenglon;

  const nombreDe = (idUsuario) => {
    const u = usuarios.find((x) => Number(x.id_user) === Number(idUsuario));
    return u?.full_name || u?.username || (idUsuario ? `#${idUsuario}` : "");
  };
  const sitioDe = (idUbicacion) => {
    const u = ubicaciones.find((x) => Number(x.id_location) === Number(idUbicacion));
    return u?.location_description || (idUbicacion ? `#${idUbicacion}` : "");
  };

  // El vale en papel. Se abre en una pestana en vez de descargarse: casi
  // siempre se quiere imprimir y firmar en el momento, no guardarlo.
  async function imprimir(id) {
    setImprimiendo(true);
    try {
      const blob = await downloadWarehouseVoucherPdf(id);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener");
      // Se libera tarde: revocarlo de inmediato deja la pestana en blanco.
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) {
      decirError(e, "No se pudo generar el PDF del vale.");
    } finally {
      setImprimiendo(false);
    }
  }

  return (
    <section className="page vale-page">
      <PageHeader
        eyebrow={t("voucher.eyebrow", "Almacén")}
        titulo={t("voucher.title", "Vales de almacén")}
        subtitulo={t("voucher.subtitle",
              "Quién se llevó qué, de dónde, y si ya lo devolvió. El vale se cierra solo cuando vuelve su último renglón.")}
      >
        <div className="vale-acciones-cabecera">
        <button className="button" onClick={cargar} disabled={cargando}>
        <RefreshCw size={16} />
        {cargando ? t("common.loading", "Cargando…") : t("common.refresh", "Actualizar")}
        </button>
        <button className="button button-primary" onClick={abrirBorrador}
        disabled={cargando || !tipos.length}>
        <Plus size={16} />
        {soloPuedeSolicitar
          ? t("voucher.draft_new", "Levantar prevale")
          : t("voucher.new", "Levantar vale")}
        </button>
        </div>
      </PageHeader>

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
                  {t("voucher.voucher_n", "Vale")}{" "}
                  #{linea.voucher_folio || linea.id_incident}
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
                {/* Quien solo puede pedir material (Supervisor) no lo recibe
                    ni lo suelta: marcarlo devuelto es lo mismo derecho de
                    `warehouse_voucher` que abrir el vale. */}
                {puedeCerrarRenglon && (
                  <button className="button button-quiet"
                          onClick={() => cerrar(linea.id_nm_incident_product)}>
                    <Check size={14} />
                    {t("voucher.close_line", "Marcar devuelto")}
                  </button>
                )}
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
          proyectos={proyectos}
          onGuardar={guardar}
          onCancelar={() => setBorrador(null)}
          onAmpliar={setFotoAmpliada}
          puedeAbrirValeDirecto={puedeAbrirValeDirecto}
          soloPuedeSolicitar={soloPuedeSolicitar}
          actorIdUser={actor.id_user}
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
              {/* El estado, en botones y no en un desplegable: son cuatro y el
                  que importa a diario -- "por autorizar" -- tiene que estar a
                  un clic, no escondido tras abrir una lista. */}
              <div className="vale-filtro-estado" role="group"
                   aria-label={t("voucher.filter_status", "Filtrar por estado")}>
                {ESTADOS_DE_VALE.map(({ valor, clave, texto }) => (
                  <button
                    key={valor || "todos"}
                    type="button"
                    className={`button button-quiet ${estado === valor ? "activo" : ""}`}
                    onClick={() => setEstado(valor)}
                  >
                    {t(`voucher.filter_${clave}`, texto)}
                  </button>
                ))}
              </div>
              <label className="vale-solo-abiertos">
                <input type="checkbox" checked={soloAbiertos} disabled={Boolean(estado)}
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
                      {/* La obra, como la nombra el resto de la pantalla: el
                          proyecto ligado si lo hay; si no, la nota del vale,
                          que es donde los vales migrados de Adser guardan su
                          obra (lo mismo que agrupa el historial del empleado). */}
                      <span className="vale-lista-proyecto"
                            title={v.proyect?.title || v.note || undefined}>
                        {v.proyect
                          ? `${v.proyect.folio ? `#${v.proyect.folio}` : `#${v.proyect.id_proyect}`}${v.proyect.title ? ` — ${v.proyect.title}` : ""}`
                          : (v.note || "").trim()
                            || t("voucher.no_project", "Sin proyecto asignado")}
                      </span>
                      <span className={`vale-lista-estado ${v.incident_status}`}>
                        {t(`voucher.status_${v.incident_status}`, v.incident_status)}
                      </span>
                      <span className="vale-lista-cuenta">
                        <span className={`vale-marca-mini ${v.open_lines > 0 ? "fuera" : "devuelto"}`}>
                          {v.open_lines > 0
                            ? `${v.open_lines} ${t("voucher.out", "fuera")}`
                            : t("voucher.all_back", "todo devuelto")}
                        </span>
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
            <Vale vale={consultado} onCerrar={cerrar} onAutorizar={autorizar}
                  onImprimir={imprimir} imprimiendo={imprimiendo}
                  onAmpliar={setFotoAmpliada}
                  onVerHistorial={(idUser, nombre) => setHistorialEmpleado({ idUser, nombre })}
                  puedeAutorizar={puedeAutorizar}
                  puedeCerrarRenglon={puedeCerrarRenglon}
                  onEntregar={entregarA} onConfirmarCustodia={confirmarCustodia}
                  privilegiado={privilegiado} actorIdUser={actor.id_user}
                  usuarios={usuarios}
                  nombreDe={nombreDe} sitioDe={sitioDe} t={t} />
          </>
        )}
      </section>

      {fotoAmpliada && (
        <VisorDeFoto
          src={fotoAmpliada.src}
          titulo={fotoAmpliada.titulo}
          descripcion={fotoAmpliada.descripcion}
          onCerrar={() => setFotoAmpliada(null)}
        />
      )}

      {historialEmpleado && (
        <EmployeeVoucherHistory
          idUser={historialEmpleado.idUser}
          nombre={historialEmpleado.nombre}
          onCerrar={() => setHistorialEmpleado(null)}
          // Cerrar la ficha y abrir ESE vale: quien esta viendo "que trae
          // Fulano" casi siempre quiere terminar en uno de esos vales, no
          // solo leerlo.
          onAbrirVale={(id) => { setHistorialEmpleado(null); consultar(id); }}
        />
      )}
    </section>
  );
}

/** El vale con sus renglones, y el estado derivado bien visible. */
function Vale({ vale, onCerrar, onAutorizar, onImprimir, imprimiendo, onAmpliar,
               onVerHistorial, puedeAutorizar, puedeCerrarRenglon,
               onEntregar, onConfirmarCustodia, privilegiado, actorIdUser, usuarios,
               nombreDe, sitioDe, t }) {
  const cabecera = vale.voucher || {};
  const estado = String(cabecera.incident_status || "");
  const cerrado = estado === "cerrado";
  // El borrador es el prevale: material pedido, todavia en el almacen.
  const borrador = estado === "borrador";
  // Quien puede entregar una pieza a un operador o confirmar que la
  // recupero: el responsable DE ESTE vale (normalmente Supervisor, que solo
  // tiene `warehouse_prevoucher`, nunca `warehouse_voucher`) o quien opera
  // el almacen.
  const puedeGestionarCustodia = privilegiado
    || Number(cabecera.id_user) === Number(actorIdUser)
    || puedeCerrarRenglon;
  const [entregaEnCaptura, setEntregaEnCaptura] = useState({});

  // Un prestamo real por renglon, no una fila de tabla: la devolucion agrega
  // un renglon de ENTRADA en vez de reescribir el de SALIDA (asi queda el
  // libro, a proposito), y sin agrupar aqui el mismo producto se veria dos
  // veces -una vez devuelto, otra vez como una fila suelta de "entrada"-,
  // que es exactamente el tipo de cosa que no se entiende sin conocer el
  // sistema por dentro. `vale.open_lines`/`vale.total_lines` cuentan filas
  // crudas por el mismo motivo y por eso NO se usan aqui abajo.
  const renglonesAgrupados = agruparRenglones(vale.lines);
  const totalReal = renglonesAgrupados.length;
  const fueraReal = renglonesAgrupados.filter(
    ({ salida }) => salida && !salida.close_date).length;

  return (
    <article className={`vale-tarjeta ${
      borrador ? "vale-borrador" : (cerrado ? "vale-cerrado" : "vale-abierto")}`}>
      <header>
        <div>
          {/* El MISMO numero que la lista: el folio con el que la gente lo
              conoce -- el del sistema anterior cuando lo trae -- y no el
              id interno. Mostraban cosas distintas, y buscar "95" para acabar
              en una pantalla titulada "#513" parece otro vale. El id sigue a
              la vista, en pequeno, porque es lo que hace falta para pedir
              ayuda o para mirarlo en la base. */}
          <h3>
            <ClipboardList size={16} />
            {t("voucher.voucher_n", "Vale")} #{cabecera.external_folio || cabecera.id_incident}
            {cabecera.external_folio && (
              <span className="vale-registro">
                {t("voucher.record_n", "registro")} {cabecera.id_incident}
              </span>
            )}
          </h3>
          <p className="muted">
            {t("voucher.holder", "Responsable")}: <strong>{nombreDe(cabecera.id_user)}</strong>
            {cabecera.id_user && (
              <button type="button" className="vale-ver-historial"
                      onClick={() => onVerHistorial(
                        cabecera.id_user, nombreDe(cabecera.id_user))}>
                <History size={13} />
                {t("voucher.view_history", "Ver historial")}
              </button>
            )}
            {cabecera.note && <> · {cabecera.note}</>}
          </p>
          {/* La obra a la que va este material -- el porque de todo el vale.
              El proyecto ya viene resuelto con nombre desde el servidor: no
              se busca en una lista local que puede no traerlo si el proyecto
              esta cerrado y no aparece en `/proyect/options`. */}
          {vale.proyect && (
            <p className="vale-obra">
              <ClipboardList size={13} />
              {t("voucher.for_project", "Obra")}:{" "}
              <strong>
                {vale.proyect.folio ? `#${vale.proyect.folio}` : `#${vale.proyect.id_proyect}`}
                {vale.proyect.title ? ` — ${vale.proyect.title}` : ""}
              </strong>
            </p>
          )}
          {/* Imprimir esta junto al encabezado y no al final: quien abre un
              vale para entregarlo material en mano lo primero que hace es
              sacarlo en papel para que lo firmen. */}
          <button className="button button-quiet vale-imprimir"
                  disabled={imprimiendo} onClick={() => onImprimir(cabecera.id_incident)}>
            <Printer size={14} />
            {imprimiendo
              ? t("common.loading", "Cargando…")
              : t("voucher.print", "Imprimir vale")}
          </button>
        </div>
        {/* El estado se muestra, no se elige: lo derivan los renglones -- con
            una excepcion, el borrador, que no habla de los renglones sino de
            que todavia nadie autorizo la salida. */}
        <span className={`vale-estado ${
          borrador ? "es-borrador" : (cerrado ? "es-cerrado" : "es-abierto")}`}>
          {borrador
            ? t("voucher.status_draft", "Borrador")
            : (cerrado
              ? t("voucher.status_closed", "Cerrado")
              : t("voucher.status_open", "Abierto"))}
          <em>
            {borrador
              ? t("voucher.nothing_left_yet", "nada ha salido todavía")
              : `${fueraReal} ${t("voucher.of", "de")} ${totalReal} ${
                t("voucher.open_lines", "sin devolver")}`}
          </em>
        </span>
      </header>

      {/* Autorizar es lo que saca el material, asi que va arriba y solo cuando
          hay algo que autorizar -y solo a quien de verdad puede: Supervisor
          pidio este prevale y por eso mismo no puede ser quien lo suelte, la
          misma separacion de deberes que ya impone el servidor. */}
      {borrador && puedeAutorizar && (
        <p className="vale-autorizar">
          <button className="button button-primary"
                  onClick={() => onAutorizar(cabecera.id_incident)}>
            {t("voucher.authorize", "Autorizar y entregar")}
          </button>
          <span className="muted">
            {t("voucher.authorize_help",
              "Al autorizar sale el material del almacén. Lo hace el jefe de almacén, y no puede ser quien pidió el vale.")}
          </span>
        </p>
      )}

      <div className="vale-tabla-marco">
        <table className="vale-tabla">
          <thead>
            <tr>
              <th>{t("voucher.col_id", "ID")}</th>
              <th>{t("voucher.col_code", "Código")}</th>
              <th>{t("voucher.col_description", "Descripción")}</th>
              <th>{t("voucher.quantity", "Cantidad")}</th>
              <th>{t("voucher.col_status", "Estado")}</th>
              <th>{t("voucher.col_note", "Nota")}</th>
              <th>{t("voucher.col_type", "Tipo")}</th>
              <th>{t("voucher.col_location", "Ubicación")}</th>
              <th>{t("voucher.col_created", "Fecha creación")}</th>
              <th>{t("voucher.col_closed", "Fecha cierre")}</th>
            </tr>
          </thead>
          <tbody>
            {renglonesAgrupados.map(({ salida, entrada }) => {
              // `linea` trae los datos del producto/pieza, iguales en las dos
              // filas cuando existen las dos. `abierto` exige la salida en
              // concreto: una entrada huerfana (ver `agruparRenglones`) nace
              // siempre cerrada, y no tiene boton de "marcar devuelto" porque no
              // hay nada que cerrar en ella.
              const linea = salida || entrada;
              const abierto = Boolean(salida) && !salida.close_date;
              const vencido = abierto && salida.due_date
                && new Date(salida.due_date) < new Date();
              // A donde volvio, solo cuando dice algo distinto de "al mismo
              // sitio del que salio" -- si coincide, repetirlo es ruido.
              const destino = entrada?.id_location_to;
              const origen = salida?.id_location_from ?? linea.id_location_from;
              const mostrarDestino = destino && String(destino) !== String(origen);

              return (
                <tr key={linea.id_nm_incident_product}
                    className={abierto ? "vale-renglon-fuera" : "vale-renglon-devuelto"}>
                  <td className="mono muted">{linea.id_nm_incident_product}</td>
                  <td className="mono">
                    {linea.product?.product_code || `#${linea.id_product}`}
                  </td>
                  {/* Que es lo que salio. Antes aqui solo iba "producto #6847":
                      un numero que no dice si lo que se llevaron fue un taladro
                      o un saco de cemento, y quien mira un vale para reclamar
                      material necesita saber QUE es. */}
                  <td><FichaDeProducto producto={linea.product} onAmpliar={onAmpliar} t={t} /></td>
                  <td className="mono">
                    {linea.id_inventory_asset
                      ? `${t("voucher.piece", "pieza")} #${linea.id_inventory_asset}`
                      : linea.quantity}
                  </td>
                  {/* La pregunta que importa a simple vista, en rojo o en
                      verde y nada mas: ¿ya volvio o no? Lo vencido sigue
                      teniendo su propia alarma arriba de todo (la seccion de
                      vencidos); aqui se distingue con la palabra, no con un
                      tercer color -un color mas es un significado mas que
                      aprender, y el objetivo es que se entienda sin
                      explicacion. */}
                  <td className="vale-tabla-estado">
                    {abierto ? (
                      <>
                        <span className={`vale-marca fuera ${vencido ? "vencida" : ""}`}>
                          <AlertTriangle size={13} />
                          {t("voucher.out", "fuera")}
                          {vencido && <> · {t("history.overdue", "vencido")}</>}
                        </span>
                        {puedeCerrarRenglon && (
                          <button className="button button-quiet"
                                  onClick={() => onCerrar(salida.id_nm_incident_product)}>
                            <Check size={14} />
                            {t("voucher.close_line", "Marcar devuelto")}
                          </button>
                        )}
                        {/* A quien se le entrega la pieza -- un operador o
                            otro supervisor, distinto del responsable del
                            vale -- y la confirmacion de que ya la recupero.
                            Es un paso INTERMEDIO: la pieza sigue "fuera"
                            hasta que alguien la devuelva de verdad con
                            "Marcar devuelto". */}
                        {puedeGestionarCustodia && !linea.id_user_delivered_to && (
                          <span className="vale-custodia">
                            <select
                              value={entregaEnCaptura[linea.id_nm_incident_product] || ""}
                              onChange={(e) => setEntregaEnCaptura({
                                ...entregaEnCaptura,
                                [linea.id_nm_incident_product]: e.target.value,
                              })}
                              aria-label={t("voucher.deliver_to", "Entregar a")}
                            >
                              <option value="">{t("voucher.deliver_to", "Entregar a…")}</option>
                              {usuarios.map((u) => (
                                <option key={u.id_user} value={u.id_user}>
                                  {u.full_name || u.username}
                                </option>
                              ))}
                            </select>
                            <button className="button button-quiet"
                                    disabled={!entregaEnCaptura[linea.id_nm_incident_product]}
                                    onClick={() => onEntregar(
                                      linea.id_nm_incident_product,
                                      entregaEnCaptura[linea.id_nm_incident_product])}>
                              {t("voucher.assign_delivery", "Asignar")}
                            </button>
                          </span>
                        )}
                        {linea.id_user_delivered_to && !linea.custody_confirmed_date && (
                          <span className="vale-custodia">
                            <span className="muted">
                              {t("voucher.delivered_to", "Con")}: {nombreDe(linea.id_user_delivered_to)}
                            </span>
                            {puedeGestionarCustodia && (
                              <button className="button button-quiet"
                                      onClick={() => onConfirmarCustodia(linea.id_nm_incident_product)}>
                                <Check size={14} />
                                {t("voucher.confirm_custody", "Confirmar recepción")}
                              </button>
                            )}
                          </span>
                        )}
                        {linea.id_user_delivered_to && linea.custody_confirmed_date && (
                          <span className="vale-custodia muted">
                            {t("voucher.custody_confirmed", "Recuperado de")} {nombreDe(linea.id_user_delivered_to)}
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="vale-marca devuelto">
                        <Check size={13} />
                        {t("history.returned", "devuelto")}
                      </span>
                    )}
                  </td>
                  <td className="vale-tabla-nota muted">{linea.note || "—"}</td>
                  <td>{t(`voucher.direction_${linea.direction}`, linea.direction)}</td>
                  <td className="muted">
                    {sitioDe(origen)}
                    {mostrarDestino && (
                      <>
                        {" "}<ArrowRight size={12} />{" "}
                        {sitioDe(destino)}
                      </>
                    )}
                  </td>
                  <td className="mono muted">
                    {/* `creation_date` de respaldo cuando falta `start_date`: lo
                        migrado de Adser nunca tuvo `start_date` (concepto propio
                        del vale rediseñado), pero si trae su fecha de alta real
                        del sistema anterior en `creation_date`. */}
                    {(linea.start_date || linea.creation_date)
                      ? new Date(linea.start_date || linea.creation_date).toLocaleString("es-MX")
                      : "—"}
                  </td>
                  <td className="mono muted">
                    {/* La entrada pareada manda cuando existe -es la devolucion
                        hecha desde esta app-, pero lo migrado de Adser cerraba
                        el renglon de salida directo, sin una entrada aparte: sin
                        este respaldo, todo lo cerrado antes de esta app se veria
                        para siempre sin fecha de cierre. */}
                    {!abierto && (entrada?.close_date || salida?.close_date)
                      ? new Date(entrada?.close_date || salida?.close_date).toLocaleString("es-MX")
                      : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </article>
  );
}

Vale.propTypes = {
  onAutorizar: PropTypes.func.isRequired,
  vale: PropTypes.shape({
    voucher: PropTypes.object,
    proyect: PropTypes.shape({
      id_proyect: PropTypes.any,
      folio: PropTypes.string,
      title: PropTypes.string,
    }),
    lines: PropTypes.array,
    open_lines: PropTypes.number,
    total_lines: PropTypes.number,
  }).isRequired,
  onCerrar: PropTypes.func.isRequired,
  onImprimir: PropTypes.func.isRequired,
  imprimiendo: PropTypes.bool,
  onAmpliar: PropTypes.func,
  onVerHistorial: PropTypes.func.isRequired,
  puedeAutorizar: PropTypes.bool,
  puedeCerrarRenglon: PropTypes.bool,
  nombreDe: PropTypes.func.isRequired,
  sitioDe: PropTypes.func.isRequired,
  t: PropTypes.func.isRequired,
};

/**
 * Que es el producto de un renglon: su foto, su codigo y su clasificacion.
 *
 * La foto va pequeña y con su hueco cuando falta -- no se esconde el marco --
 * para que la lista de renglones no cambie de alto segun cuales tengan
 * imagen: una lista que se descuadra al cargar se lee peor que una con
 * huecos. Y para reconocer una herramienta hace falta verla: por eso la
 * miniatura abre la foto en grande al pulsarla.
 *
 * La URL la arma `urlDeArchivo` y no se pinta `path_imagen` en crudo. Dos
 * motivos, los dos medidos: con el backend en otro puerto -- desarrollo -- una
 * ruta relativa no resuelve, y los 2 221 productos migrados traen la carpeta
 * del sistema anterior en SINGULAR (`/uploads/producto/225.png`) mientras la
 * aplicacion sirve `/uploads/products/`. El helper traduce las dos cosas.
 *
 * Aun asi se conserva el marcador para cuando el archivo no exista: se cae a el
 * en vez de dejar el icono de imagen rota del navegador, que se lee como un
 * fallo de la aplicacion.
 */
function FichaDeProducto({ producto, onAmpliar, t }) {
  const [fotoRota, setFotoRota] = useState(false);
  if (!producto) return null;
  // Cada rasgo con su etiqueta -"Marca: X", no solo "X"-: unos puntos
  // separando valores sueltos obligan a saberse de memoria el orden para
  // distinguir la marca del material, y ese es justo el conocimiento que no
  // se le puede pedir a quien no ha usado el sistema antes.
  const rasgos = [
    producto.brand && `${t("inventory.brand", "Marca")}: ${producto.brand}`,
    producto.material && `${t("voucher.material", "Material")}: ${producto.material}`,
    producto.color && `${t("inventory.color", "Color")}: ${producto.color}`,
    producto.unit && `${t("voucher.unit", "Unidad")}: ${producto.unit}`,
  ].filter(Boolean);
  const foto = fotoRota ? "" : urlDeArchivo(producto.path_imagen);

  return (
    <span className="vale-ficha">
      <span className="vale-ficha-foto">
        {foto ? (
          <img src={foto} alt={producto.descripcion || ""}
               className="foto-ampliable" loading="lazy"
               title={t("photo.click_to_zoom", "Clic para verla en grande")}
               onClick={() => onAmpliar && onAmpliar({
                 src: foto,
                 titulo: producto.descripcion || "",
                 descripcion: producto.product_code || "",
               })}
               onError={() => setFotoRota(true)} />
        ) : (
          <ImageOff size={16} />
        )}
      </span>
      <span className="vale-ficha-datos">
        <strong>{producto.descripcion || `#${producto.id_product}`}</strong>
        <span className="muted mono">
          {t("voucher.col_code", "Código")}: {producto.product_code || `#${producto.id_product}`}
          {producto.tracking_mode === "serializado"
            && ` · ${t("voucher.serialized", "pieza por pieza")}`}
        </span>
        {rasgos.length > 0 && <span className="muted">{rasgos.join("  ·  ")}</span>}
      </span>
    </span>
  );
}

FichaDeProducto.propTypes = {
  producto: PropTypes.object,
  onAmpliar: PropTypes.func,
  t: PropTypes.func.isRequired,
};
FichaDeProducto.defaultProps = { producto: null, onAmpliar: null };

/**
 * Adapta un resultado de `inventoryTrace` (Localizar) a lo que `FichaDeProducto`
 * espera. Son dos formas distintas del mismo dato: el vale ya resuelto trae
 * `brand`/`material`/`unit` planos (`_fichas_de_producto` en el backend), y el
 * rastreo los trae anidados bajo `classification` -viene de la misma tabla
 * `material`, pero por un camino que ademas compara contra el catalogo publico.
 * Sin este ajuste, el buscador del prevale se veia solo con codigo y
 * descripcion mientras Almacen/Localizar ya mostraban foto y clasificacion
 * para el mismo producto.
 */
function comoFichaDeProducto(candidato) {
  return {
    id_product: candidato.id_product,
    product_code: candidato.product_code,
    descripcion: candidato.descripcion,
    path_imagen: candidato.path_imagen,
    tracking_mode: candidato.tracking_mode,
    brand: candidato.classification?.brand,
    material: candidato.classification?.material,
    unit: candidato.classification?.unit,
  };
}

/** La captura de un vale: cabecera y renglones. */
function Borrador({ borrador, setBorrador, tipos, ubicaciones, usuarios,
                    proyectos, onGuardar, onCancelar, onAmpliar,
                    puedeAbrirValeDirecto, soloPuedeSolicitar,
                    actorIdUser, t }) {
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
        // Donde hay existencia de este producto, con su ruta. Es lo que se
        // ofrece a quien solo pide material: no elige "de donde" entre todas
        // las ubicaciones, sale de donde el producto esta.
        sitios: producto.locations || [],
        sitio_etiqueta: pieza
          ? (pieza.location_path_label || pieza.location_description || "")
          : "",
      }],
    });
    setBusqueda("");
    setCandidatos([]);
  };

  // Cuanto hay para ESTE renglon: la existencia del producto en la ubicacion de
  // la que sale, menos lo que ya piden los otros renglones del mismo producto y
  // sitio. Lo serializado no cuenta -una pieza es una pieza-. El buscador ya
  // trae la existencia por sitio, asi que no hace falta otra consulta.
  const disponibleDe = (linea, indice) => {
    if (linea.serializado) return null;
    const sitio = (linea.sitios || []).find(
      (s) => String(s.id_location) === String(linea.id_location_from));
    const hay = Number(sitio?.quantity) || 0;
    const yaPedido = borrador.lines.reduce((suma, otra, i) => (
      i !== indice && !otra.serializado
        && otra.id_product === linea.id_product
        && String(otra.id_location_from) === String(linea.id_location_from)
        ? suma + (Number(otra.quantity) || 0) : suma), 0);
    return Math.max(0, hay - yaPedido);
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
    && borrador.lines.every((l, i) => l.serializado || (
      l.id_location_from && Number(l.quantity) >= 1
      && Number(l.quantity) <= disponibleDe(l, i)));

  return (
    <section className="vale-borrador">
      <header>
        <h2><Plus size={16} />
          {soloPuedeSolicitar
            ? t("voucher.draft_new", "Levantar prevale")
            : t("voucher.new", "Levantar vale")}
        </h2>
        <button className="vale-icono" onClick={onCancelar}
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
          {/* Por omision es quien pide el prevale (preseleccionado abajo),
              pero deja elegir a alguien mas -pedido de negocio, 2026-09-30-:
              el supervisor no siempre puede salir de planta, y manda a un
              operador por la herramienta. Ese operador queda como
              responsable ante almacen -el que firma y el que debe
              devolverlo-, sin importar quien haya capturado el prevale. */}
          <select value={borrador.id_user}
                  onChange={(e) => setBorrador({ ...borrador, id_user: e.target.value })}>
            <option value="">{t("voucher.pick_holder", "Elige a quién se le entrega")}</option>
            {usuarios.map((u) => (
              <option key={u.id_user} value={u.id_user}>
                {u.full_name || u.username || `#${u.id_user}`}
                {soloPuedeSolicitar && Number(u.id_user) === Number(actorIdUser)
                  ? ` ${t("voucher.holder_is_you", "(tú)")}` : ""}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>{t("voucher.project", "Proyecto")}</span>
          <select value={borrador.id_proyect}
                  onChange={(e) => setBorrador({ ...borrador, id_proyect: e.target.value })}>
            <option value="">{t("voucher.no_project", "Sin proyecto asignado")}</option>
            {proyectos.map((p) => (
              <option key={p.id_proyect} value={p.id_proyect}>
                {p.folio ? `#${p.folio}` : `#${p.id_proyect}`}
                {p.title ? ` — ${p.title}` : ""}
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
                {/* Misma ficha -foto, codigo, marca/material/unidad- que ya
                    usan Almacen y Localizar para el mismo producto: un
                    "#9001" a secas no dice si lo que se pide es un taladro o
                    un saco de cemento. */}
                <FichaDeProducto producto={comoFichaDeProducto(p)} onAmpliar={onAmpliar} t={t} />
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
                  <input type="number" min="1"
                         max={Math.max(1, disponibleDe(linea, indice))}
                         value={linea.quantity}
                         onChange={(e) => cambiar(indice, {
                           // Sin pasarse de lo que hay: el servidor lo rechaza
                           // igual, esto evita llegar hasta el error.
                           quantity: Math.min(
                             Number(e.target.value) || 1,
                             Math.max(1, disponibleDe(linea, indice))),
                         })} />
                  <small className={disponibleDe(linea, indice) === 0 ? "vale-sin-existencia" : "muted"}>
                    {disponibleDe(linea, indice) === 0
                      ? t("voucher.no_stock_here", "Sin existencia aquí")
                      : `${t("voucher.available", "Disponible")}: ${disponibleDe(linea, indice)}`}
                  </small>
                </label>
              )}

              {/* De donde sale. En una pieza se sabe -es donde esta- pero en
                  lo fungible hay que decirlo: descontar 5 sacos "del almacen"
                  sin decir de cual deja el saldo por ubicacion mintiendo, y ese
                  es el dato con el que alguien va a buscarlos. */}
              {/* Quien solo PIDE material (Supervisor) no elige de donde sale:
                  eso ya esta definido por donde esta el producto, y se le
                  muestra. Solo si el producto esta repartido en varios sitios
                  se le ofrecen ESOS sitios -no todas las ubicaciones-. */}
              {soloPuedeSolicitar
                && (linea.serializado || (linea.sitios || []).length === 1) ? (
                <div className="vale-mini">
                  <span>{t("voucher.from", "Sale de")}</span>
                  <strong>
                    {linea.sitio_etiqueta
                      || linea.sitios?.[0]?.path_label
                      || linea.sitios?.[0]?.location_description
                      || ubicaciones.find((u) => Number(u.id_location)
                        === Number(linea.id_location_from))?.location_description
                      || "—"}
                  </strong>
                </div>
              ) : (
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
                    {(soloPuedeSolicitar && (linea.sitios || []).length > 1
                      ? (linea.sitios || []).map((s) => ({
                        id_location: s.id_location,
                        location_description: s.path_label || s.location_description,
                      }))
                      : ubicaciones).map((u) => (
                      <option key={u.id_location} value={u.id_location}>
                        {u.location_description}
                      </option>
                    ))}
                  </select>
                </label>
              )}

              <button className="vale-icono vale-icono-borrar" onClick={() => quitar(indice)}
                      aria-label={t("common.delete", "Quitar")}>
                <Trash2 size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}

      <footer className="vale-pie">
        {/* Dos salidas para el mismo formulario, porque son dos actos: pedir y
            surtir. El prevale queda en borrador y no mueve nada; abrir el vale
            saca el material y necesita `warehouse_voucher`.

            "Abrir vale" solo se ofrece a quien de verdad puede surtir: quien
            solo pide material (Supervisor) no tiene mas que una salida, asi
            que esa es la primaria. El servidor sigue negando la ruta que no
            le toca de cualquier forma -esto es UX, no el permiso de verdad. */}
        <button
          className={`button ${puedeAbrirValeDirecto ? "" : "button-primary"}`}
          onClick={() => onGuardar(true)}
          disabled={!listo}
          title={t("voucher.draft_help",
            "Deja el material pedido, sin sacarlo. Lo autoriza el jefe de almacén.")}
        >
          {t("voucher.draft", "Solicitar vale")}
        </button>
        {puedeAbrirValeDirecto && (
          <button className="button button-primary" onClick={() => onGuardar(false)} disabled={!listo}>
            {t("voucher.open", "Abrir vale")}
          </button>
        )}
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
    id_proyect: PropTypes.any,
    due_date: PropTypes.string,
    note: PropTypes.string,
    lines: PropTypes.array,
  }).isRequired,
  setBorrador: PropTypes.func.isRequired,
  tipos: PropTypes.array.isRequired,
  ubicaciones: PropTypes.array.isRequired,
  usuarios: PropTypes.array.isRequired,
  proyectos: PropTypes.array.isRequired,
  onGuardar: PropTypes.func.isRequired,
  onCancelar: PropTypes.func.isRequired,
  onAmpliar: PropTypes.func,
  puedeAbrirValeDirecto: PropTypes.bool,
  soloPuedeSolicitar: PropTypes.bool,
  actorIdUser: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  t: PropTypes.func.isRequired,
};
