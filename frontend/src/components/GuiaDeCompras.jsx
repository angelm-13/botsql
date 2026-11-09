import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import {
  AlertTriangle, ArrowRight, Check, CheckCircle2, ClipboardList, Clock, HelpCircle, Lightbulb,
  ListChecks, PackageCheck, Receipt, Search, ShoppingCart, Truck, UserCheck, X,
} from "lucide-react";
import { PASOS_DE_ORDEN, conDatos, pasoDeOrden, queSigue } from "../utils/ordenDeCompra";

// El dibujo de cada paso. El color y el porque viven en utils/ordenDeCompra.js.
const ICONO_DEL_PASO = {
  draft: ClipboardList, pending_authorization: UserCheck, authorized: Receipt,
  purchased: Truck, received: PackageCheck,
  request: ClipboardList, review: Search, order: ShoppingCart, follow: ListChecks,
};
const ICONO_DEL_TONO = { accion: ArrowRight, alerta: AlertTriangle, ok: CheckCircle2, neutro: Clock, info: ArrowRight };

/** Una linea corta de "por que" junto a un campo: el foco y el texto, sin estorbar. */
export function PorQue({ children }) {
  return (
    <p className="guia-porque">
      <Lightbulb size={15} aria-hidden="true" />
      <span>{children}</span>
    </p>
  );
}

PorQue.propTypes = { children: PropTypes.node.isRequired };
import { useI18n } from "../i18n";
import "../styles/guia-compras.css";

/**
 * Las piezas de guia de Compras: que entienda el proceso quien entra por primera vez
 * y que en cada paso sepa que sigue. La logica (que paso, que frase) vive en
 * `utils/ordenDeCompra.js`; aqui solo se pinta.
 */

function llaveDeGuia(id) {
  let usuario = "";
  try { usuario = JSON.parse(localStorage.getItem("user") || "{}").id_user || ""; } catch { /* sin sesion guardada */ }
  return `guia-oculta:${id}:${usuario}`;
}

function guiaOculta(id) {
  try { return localStorage.getItem(llaveDeGuia(id)) === "1"; } catch { return false; }
}

/**
 * La explicacion corta al entrar a la pantalla: los pasos dibujados (icono, color y por
 * que) y debajo lo que le toca a quien mira. La X la esconde para ese usuario.
 */
export function GuiaDelModulo({ id, titulo, pasos = [], prefijo = "order.step", puntos }) {
  const { t } = useI18n();
  const [oculta, setOculta] = useState(() => guiaOculta(id));
  const cambiar = (valor) => {
    setOculta(valor);
    try {
      if (valor) localStorage.setItem(llaveDeGuia(id), "1");
      else localStorage.removeItem(llaveDeGuia(id));
    } catch { /* sin almacenamiento: solo dura esta visita */ }
  };
  if (oculta) {
    return (
      <button type="button" className="guia-reabrir" onClick={() => cambiar(false)}>
        <HelpCircle size={15} /> {t("guide.how_it_works", "¿Cómo funciona?")}
      </button>
    );
  }
  const conTexto = puntos.filter(Boolean);
  return (
    <aside className="guia-modulo" aria-label={titulo}>
      <button type="button" className="guia-cerrar" onClick={() => cambiar(true)}
              aria-label={t("guide.close", "Cerrar guía")} title={t("guide.close", "Cerrar guía")}>
        <X size={16} />
      </button>
      <strong className="guia-titulo">{titulo}</strong>
      {pasos.length > 0 && (
        <ol className="guia-pasos">
          {pasos.map((p, i) => {
            const Icono = ICONO_DEL_PASO[p.clave] || ArrowRight;
            return (
              <li key={p.clave} className={`guia-paso tono-${p.tono}`}>
                <Icono size={24} aria-hidden="true" />
                <b>{i + 1}. {t(`${prefijo}.${p.clave}`, p.etiqueta)}</b>
                <span>{t(`${prefijo}_why.${p.clave}`, p.porque)}</span>
              </li>
            );
          })}
        </ol>
      )}
      {conTexto.length > 0 && (
        <ul className="guia-puntos">
          {conTexto.map((p) => (
            <li key={p}><Lightbulb size={15} aria-hidden="true" /><span>{p}</span></li>
          ))}
        </ul>
      )}
    </aside>
  );
}

GuiaDelModulo.propTypes = {
  id: PropTypes.string.isRequired,
  titulo: PropTypes.string.isRequired,
  pasos: PropTypes.arrayOf(PropTypes.shape({
    clave: PropTypes.string, etiqueta: PropTypes.string, tono: PropTypes.string, porque: PropTypes.string,
  })),
  prefijo: PropTypes.string,
  puntos: PropTypes.arrayOf(PropTypes.oneOfType([PropTypes.string, PropTypes.bool])).isRequired,
};

/** La barra de pasos de una orden: lo hecho, el paso actual y lo que falta. */
export function PasosDeOrden({ estado = "draft" }) {
  const { t } = useI18n();
  const paso = pasoDeOrden(estado);
  const actualDelPaso = paso.terminada ? null : PASOS_DE_ORDEN[paso.indice];
  return (
    <div className="oc-pasos-envoltura">
      <ol className={`oc-pasos${paso.desvio === "cancelled" ? " oc-pasos-cancelada" : ""}`}>
        {PASOS_DE_ORDEN.map((p, i) => {
          const hecho = paso.terminada ? i <= paso.indice : i < paso.indice;
          const actual = !paso.terminada && i === paso.indice;
          const clase = hecho ? "hecho" : actual ? (paso.desvio ? "desvio" : "actual") : "pendiente";
          const Icono = ICONO_DEL_PASO[p.clave] || ArrowRight;
          return (
            <li key={p.clave} className={`oc-paso oc-paso-${clase} tono-${p.tono}`} aria-current={actual ? "step" : undefined}>
              <span className="oc-paso-punto">{hecho ? <Check size={14} /> : <Icono size={15} aria-hidden="true" />}</span>
              <span className="oc-paso-nombre">{t(`order.step.${p.clave}`, p.etiqueta)}</span>
              {actual && !paso.desvio && <span className="oc-paso-aqui">{t("order.step.you_are_here", "aquí va")}</span>}
            </li>
          );
        })}
      </ol>
      {actualDelPaso && !paso.desvio && (
        <PorQue>{t(`order.step_why.${actualDelPaso.clave}`, actualDelPaso.porque)}</PorQue>
      )}
      {paso.desvio === "rejected" && (
        <small className="oc-pasos-nota">{t("order.step.rejected_note", "Rechazada: regresó a corregirse.")}</small>
      )}
      {paso.desvio === "cancelled" && (
        <small className="oc-pasos-nota">{t("order.step.cancelled_note", "Cancelada: el proceso se detuvo.")}</small>
      )}
    </div>
  );
}

PasosDeOrden.propTypes = { estado: PropTypes.string };

/** El recuadro "Qué sigue" de una orden, dicho a quien la esta viendo. */
export function QueSigue({ orden }) {
  const { t } = useI18n();
  const { principal, extra } = queSigue(orden);
  const decir = (f) => conDatos(t(f.clave, f.texto), f.datos);
  const Icono = ICONO_DEL_TONO[principal.tono] || ArrowRight;
  return (
    <div className={`oc-que-sigue oc-que-sigue-${principal.tono}`} role="status">
      <span className="oc-que-sigue-icono"><Icono size={18} aria-hidden="true" /></span>
      <div>
        <span className="oc-que-sigue-titulo">{t("order.next.title", "Qué sigue")}</span>
        <p>{decir(principal)}</p>
        {extra && <p className="oc-que-sigue-extra">{decir(extra)}</p>}
      </div>
    </div>
  );
}

QueSigue.propTypes = { orden: PropTypes.object.isRequired };

/** Aviso pequeño despues de una accion; se va solo. `aviso` = {clave, texto, datos}. */
export function AvisoFlotante({ aviso = null, onCerrar }) {
  const { t } = useI18n();
  useEffect(() => {
    if (!aviso) return undefined;
    const reloj = setTimeout(onCerrar, 7000);
    return () => clearTimeout(reloj);
  }, [aviso, onCerrar]);
  if (!aviso) return null;
  return (
    <div className="aviso-flotante" role="status" aria-live="polite">
      <Check size={16} />
      <span>{conDatos(t(aviso.clave, aviso.texto), aviso.datos)}</span>
      <button type="button" onClick={onCerrar} aria-label={t("common.close", "Cerrar")}><X size={14} /></button>
    </div>
  );
}

AvisoFlotante.propTypes = {
  aviso: PropTypes.shape({ clave: PropTypes.string, texto: PropTypes.string, datos: PropTypes.object }),
  onCerrar: PropTypes.func.isRequired,
};
