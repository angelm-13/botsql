import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { ArrowRight, Check, HelpCircle, Info, X } from "lucide-react";
import { PASOS_DE_ORDEN, conDatos, pasoDeOrden, queSigue } from "../utils/ordenDeCompra";
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

/** La explicacion corta al entrar a la pantalla. "Ya entendí" la esconde para ese usuario. */
export function GuiaDelModulo({ id, titulo, puntos }) {
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
  return (
    <aside className="guia-modulo" aria-label={titulo}>
      <Info size={18} className="guia-icono" />
      <div>
        <strong>{titulo}</strong>
        <ol>
          {puntos.filter(Boolean).map((p) => <li key={p}>{p}</li>)}
        </ol>
      </div>
      <button type="button" className="guia-cerrar" onClick={() => cambiar(true)}>
        <X size={14} /> {t("guide.got_it", "Ya entendí")}
      </button>
    </aside>
  );
}

GuiaDelModulo.propTypes = {
  id: PropTypes.string.isRequired,
  titulo: PropTypes.string.isRequired,
  puntos: PropTypes.arrayOf(PropTypes.string).isRequired,
};

/** La barra de pasos de una orden: lo hecho, el paso actual y lo que falta. */
export function PasosDeOrden({ estado = "draft" }) {
  const { t } = useI18n();
  const paso = pasoDeOrden(estado);
  return (
    <div className="oc-pasos-envoltura">
      <ol className={`oc-pasos${paso.desvio === "cancelled" ? " oc-pasos-cancelada" : ""}`}>
        {PASOS_DE_ORDEN.map((p, i) => {
          const hecho = paso.terminada ? i <= paso.indice : i < paso.indice;
          const actual = !paso.terminada && i === paso.indice;
          const clase = hecho ? "hecho" : actual ? (paso.desvio ? "desvio" : "actual") : "pendiente";
          return (
            <li key={p.clave} className={`oc-paso oc-paso-${clase}`} aria-current={actual ? "step" : undefined}>
              <span className="oc-paso-punto">{hecho ? <Check size={12} /> : i + 1}</span>
              <span className="oc-paso-nombre">{t(`order.step.${p.clave}`, p.etiqueta)}</span>
            </li>
          );
        })}
      </ol>
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
  return (
    <div className={`oc-que-sigue oc-que-sigue-${principal.tono}`} role="status">
      <ArrowRight size={16} className="oc-que-sigue-icono" />
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
