import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle, Banknote, CreditCard, Minus, Plus, RefreshCw, Search,
  ShoppingCart, Trash2, Unlock, X,
} from "lucide-react";
import { useI18n } from "../i18n";
import "../styles/pos-till.css";
import PageHeader from "../components/PageHeader.jsx";
import {
  posCheckout, posOpenCashSession, posRequest, posStatus,
} from "../api";

// Formas de pago que la caja acepta. El POS admite mas -credito local,
// puntos-, pero se ofrecen las tres de mostrador: agregar una forma sin la
// pantalla que la sustente deja al cajero cobrando a ciegas.
const FORMAS = [
  { clave: "cash", icono: Banknote },
  { clave: "card", icono: CreditCard },
  { clave: "transfer", icono: CreditCard },
];

// Tipos de venta que el POS acepta (SaleType en su modelo). No se inventan:
// mandar uno que no existe hace que el POS rechace la venta entera, y el cajero
// solo ve "tipo de venta invalido" sin saber cual poner.
const TIPOS_DE_VENTA = ["takeout", "dine_in", "delivery", "online"];

// El POS y el nucleo no comparten convencion de respuesta: uno devuelve el
// arreglo y el otro lo envuelve con la paginacion. Se acepta cualquiera.
const listaDe = (respuesta) => {
  if (Array.isArray(respuesta)) return respuesta;
  if (Array.isArray(respuesta?.items)) return respuesta.items;
  if (Array.isArray(respuesta?.products)) return respuesta.products;
  return [];
};

const dinero = (valor) => {
  const numero = Number(valor);
  return Number.isFinite(numero)
    ? numero.toLocaleString("es-MX", { style: "currency", currency: "MXN" })
    : "—";
};

export default function PosTillPage() {
  const { t } = useI18n();
  const [puente, setPuente] = useState(null);
  const [turno, setTurno] = useState(null);
  const [productos, setProductos] = useState([]);
  const [busqueda, setBusqueda] = useState("");
  const [carrito, setCarrito] = useState([]);
  const [forma, setForma] = useState("cash");
  const [tipoVenta, setTipoVenta] = useState("takeout");
  const [recibido, setRecibido] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [errorTexto, setErrorTexto] = useState("");
  const [ticket, setTicket] = useState(null);
  const campoBusqueda = useRef(null);

  // `t` cambia de identidad en cada render, asi que no puede estar en las
  // dependencias de `cargar`: con ella, el efecto que lo llama se re-disparaba
  // sin parar y el navegador acababa rechazando peticiones por agotamiento
  // (ERR_INSUFFICIENT_RESOURCES). Se guarda en una referencia, que no cambia.
  const traducir = useRef(t);
  traducir.current = t;

  const reportar = useCallback((error) => {
    // El POS manda su propio mensaje; se muestra tal cual porque describe el
    // problema mejor que cualquier texto generico del puente -"sin existencia
    // de tal producto" en lugar de "error al cobrar"-.
    const detalle = error?.payload?.error || error?.payload?.message;
    setErrorTexto(detalle || traducir.current(error?.message || "errors.request_failed"));
  }, []);

  const cargar = useCallback(async () => {
    setOcupado(true);
    setErrorTexto("");
    try {
      const estado = await posStatus();
      setPuente(estado);
      if (!estado.configured || !estado.reachable) return;

      const [catalogo, sesion] = await Promise.all([
        posRequest("products", { params: { per_page: 200 } }),
        posRequest("cash/sessions/open").catch(() => null),
      ]);
      // El POS devuelve un arreglo directo, no la envoltura paginada que usa
      // el nucleo. Se aceptan las dos formas en vez de suponer una: son dos
      // sistemas distintos y su contrato no tiene por que coincidir.
      setProductos(listaDe(catalogo));
      setTurno(sesion?.session || sesion || null);
    } catch (error) {
      reportar(error);
    } finally {
      setOcupado(false);
    }
  }, [reportar]);

  useEffect(() => { cargar(); }, [cargar]);

  const filtrados = useMemo(() => {
    const texto = busqueda.trim().toLowerCase();
    if (!texto) return productos.slice(0, 40);
    return productos
      .filter((p) =>
        String(p.name || p.description || "").toLowerCase().includes(texto) ||
        String(p.barcode || "").includes(texto) ||
        String(p.sku || "").toLowerCase().includes(texto))
      .slice(0, 40);
  }, [productos, busqueda]);

  const total = useMemo(
    () => carrito.reduce((suma, linea) => suma + Number(linea.unit_price || 0) * linea.quantity, 0),
    [carrito]
  );

  const cambio = useMemo(() => {
    const entregado = Number(recibido);
    return Number.isFinite(entregado) ? entregado - total : null;
  }, [recibido, total]);

  function agregar(producto) {
    setCarrito((actual) => {
      const existente = actual.find((l) => l.product_id === producto.id);
      if (existente) {
        return actual.map((l) =>
          l.product_id === producto.id ? { ...l, quantity: l.quantity + 1 } : l);
      }
      return [...actual, {
        product_id: producto.id,
        name: producto.name || producto.description,
        unit_price: Number(producto.sale_price ?? producto.price ?? producto.unit_price ?? 0),
        quantity: 1,
      }];
    });
    setBusqueda("");
    campoBusqueda.current?.focus();
  }

  function cambiarCantidad(id, delta) {
    setCarrito((actual) => actual
      .map((l) => (l.product_id === id ? { ...l, quantity: l.quantity + delta } : l))
      .filter((l) => l.quantity > 0));
  }

  async function abrirTurno() {
    setOcupado(true);
    setErrorTexto("");
    try {
      const abierta = await posOpenCashSession({ opening_amount: 0 });
      setTurno(abierta?.session || abierta);
    } catch (error) {
      reportar(error);
    } finally {
      setOcupado(false);
    }
  }

  async function cobrar(evento) {
    evento.preventDefault();
    if (!carrito.length) return;
    setOcupado(true);
    setErrorTexto("");
    try {
      const recibo = await posCheckout({
        sale_type: tipoVenta,
        items: carrito.map((l) => ({ product_id: l.product_id, quantity: l.quantity })),
        payments: [{ method: forma, amount: total }],
        ...(turno?.id ? { cash_register_session_id: turno.id } : {}),
      });
      setTicket(recibo);
      setCarrito([]);
      setRecibido("");
    } catch (error) {
      reportar(error);
    } finally {
      setOcupado(false);
    }
  }

  // --- el puente no esta listo -------------------------------------------
  if (puente && (!puente.configured || !puente.reachable)) {
    return (
      <section className="page till-page">
        <h1>{t("pos.till_title", "Caja")}</h1>
        <div className="till-blocked">
          <AlertTriangle size={20} />
          <div>
            <p>
              <strong>
                {puente.configured
                  ? t("pos.unreachable", "El punto de venta no responde.")
                  : t("pos.not_configured", "El puente con el punto de venta no está configurado.")}
              </strong>
            </p>
            <p className="muted">
              {puente.detail || t(
                "pos.bridge_hint",
                "Hacen falta POS_API_URL, POS_SERVICE_USER y POS_SERVICE_PASSWORD en la configuración del servidor."
              )}
            </p>
            <button className="button" onClick={cargar}>
              <RefreshCw size={15} />{t("common.refresh", "Reintentar")}
            </button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="page till-page">
      <PageHeader
        eyebrow={t("pos.eyebrow", "Punto de venta")}
        titulo={t("pos.till_title", "Caja")}
      >
        <div className="till-session">
        {turno ? (
        <span className="till-chip abierta">
        {t("pos.session_open", "Turno abierto")}
        {turno.opened_at ? ` · ${String(turno.opened_at).slice(0, 16).replace("T", " ")}` : ""}
        </span>
        ) : (
        <button className="button" onClick={abrirTurno} disabled={ocupado}>
        <Unlock size={15} />
        {t("pos.open_session", "Abrir turno de caja")}
        </button>
        )}
        <button className="button ghost" onClick={cargar} disabled={ocupado}>
        <RefreshCw size={15} />
        </button>
        </div>
      </PageHeader>

      {errorTexto && <p className="error">{errorTexto}</p>}

      {/* Cobrar sin turno abierto deja el dinero fuera de todo arqueo: el
          corte solo suma lo cobrado desde que se abrio la caja. */}
      {!turno && !ocupado && (
        <p className="till-warn">
          <AlertTriangle size={15} />
          {t(
            "pos.no_session_warning",
            "Sin turno abierto, lo que cobres queda fuera del corte de caja."
          )}
        </p>
      )}

      <div className="till-layout">
        <div className="till-catalog">
          <div className="till-search">
            <Search size={16} />
            <input
              ref={campoBusqueda}
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder={t("pos.search_product", "Buscar o escanear código de barras")}
              aria-label={t("pos.search_product", "Buscar producto")}
              autoFocus
            />
          </div>
          <div className="till-grid">
            {filtrados.map((producto) => (
              <button
                key={producto.id}
                type="button"
                className="till-product"
                onClick={() => agregar(producto)}
              >
                <span className="till-product-name">{producto.name || producto.description}</span>
                <span className="till-product-price">
                  {dinero(producto.sale_price ?? producto.price ?? producto.unit_price)}
                </span>
                {(producto.current_stock ?? producto.stock) !== undefined && (
                  <span className="till-product-stock">
                    {t("pos.stock", "Existencia")}: {Number(producto.current_stock ?? producto.stock)}
                  </span>
                )}
              </button>
            ))}
            {filtrados.length === 0 && (
              <p className="muted">
                {ocupado ? t("common.loading") : t("pos.no_products", "Sin resultados.")}
              </p>
            )}
          </div>
        </div>

        <form className="till-cart" onSubmit={cobrar}>
          <h2><ShoppingCart size={18} /> {t("pos.cart", "Venta")}</h2>

          {carrito.length === 0 && (
            <p className="muted till-cart-empty">
              {t("pos.cart_empty", "Toca un producto para agregarlo.")}
            </p>
          )}

          <ul className="till-lines">
            {carrito.map((linea) => (
              <li key={linea.product_id}>
                <div className="till-line-main">
                  <span className="till-line-name">{linea.name}</span>
                  <span className="mono">{dinero(Number(linea.unit_price) * linea.quantity)}</span>
                </div>
                <div className="till-line-qty">
                  <button type="button" onClick={() => cambiarCantidad(linea.product_id, -1)}
                          aria-label={t("pos.less", "Quitar uno")}>
                    <Minus size={14} />
                  </button>
                  <span className="mono">{linea.quantity}</span>
                  <button type="button" onClick={() => cambiarCantidad(linea.product_id, 1)}
                          aria-label={t("pos.more", "Agregar uno")}>
                    <Plus size={14} />
                  </button>
                  <button type="button" className="peligro"
                          onClick={() => cambiarCantidad(linea.product_id, -linea.quantity)}
                          aria-label={t("common.remove", "Quitar")}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </li>
            ))}
          </ul>

          <div className="till-total">
            <span>{t("pos.total", "Total")}</span>
            <strong className="mono">{dinero(total)}</strong>
          </div>

          <div className="field">
            <label htmlFor="till-tipo">{t("pos.sale_type", "Tipo de venta")}</label>
            <select id="till-tipo" value={tipoVenta} onChange={(e) => setTipoVenta(e.target.value)}>
              {TIPOS_DE_VENTA.map((tipo) => (
                <option key={tipo} value={tipo}>{t(`pos.sale_type_${tipo}`, tipo)}</option>
              ))}
            </select>
          </div>

          <div className="till-methods">
            {FORMAS.map(({ clave, icono: Icono }) => (
              <button
                key={clave}
                type="button"
                className={forma === clave ? "till-method activa" : "till-method"}
                onClick={() => setForma(clave)}
              >
                <Icono size={15} />
                {t(`pos.method_${clave}`, clave)}
              </button>
            ))}
          </div>

          {forma === "cash" && (
            <div className="field">
              <label htmlFor="till-recibido">{t("pos.received", "Recibido")}</label>
              <input
                id="till-recibido"
                type="number" step="0.01" min="0"
                value={recibido}
                onChange={(e) => setRecibido(e.target.value)}
              />
              {/* El cambio se calcula en pantalla porque es lo que el cajero
                  necesita en la mano; el importe que se cobra sigue siendo el
                  total que calcula el servidor. */}
              {cambio !== null && recibido !== "" && (
                <p className={cambio < 0 ? "till-change falta" : "till-change"}>
                  {cambio < 0
                    ? `${t("pos.missing", "Faltan")} ${dinero(-cambio)}`
                    : `${t("pos.change", "Cambio")} ${dinero(cambio)}`}
                </p>
              )}
            </div>
          )}

          <button
            className="button primary till-charge"
            type="submit"
            disabled={ocupado || carrito.length === 0 || (forma === "cash" && cambio !== null && cambio < 0)}
          >
            {t("pos.charge", "Cobrar")} {dinero(total)}
          </button>
        </form>
      </div>

      {ticket && (
        <div className="till-receipt-backdrop" role="dialog" aria-modal="true">
          <div className="till-receipt">
            <header>
              <h2>{t("pos.sale_done", "Venta registrada")}</h2>
              <button className="button ghost" onClick={() => setTicket(null)}
                      aria-label={t("common.close", "Cerrar")}>
                <X size={16} />
              </button>
            </header>
            <p className="mono till-folio">{ticket.folio || ticket.id}</p>
            <p className="mono till-receipt-total">{dinero(ticket.total ?? total)}</p>
            <button className="button primary" onClick={() => setTicket(null)}>
              {t("pos.next_sale", "Siguiente venta")}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
