import { useState } from "react";
import PropTypes from "prop-types";
import { CalendarClock, Check, Truck, Undo2, X } from "lucide-react";
import { rentalArrive, rentalDecideExtension, rentalExtend, rentalReturn } from "../api";
import { etapaDeRenta } from "../utils/rentaDeMaquinaria";
import { useI18n } from "../i18n";
import "../styles/renta-maquinaria.css";

const fecha = (texto) => (texto
  ? new Date(`${String(texto).slice(0, 10)}T00:00:00`).toLocaleDateString("es-MX")
  : "—");

/**
 * Una renta de maquinaria: en que va y, si le toca a quien la ve, sus botones.
 *
 * Que botones salen lo decide el servidor (`renta.actions`): llega a obra y devuelta
 * los marca quien lleva la obra o quien recibe compras; la prorroga la pide quien la
 * lleva y la decide quien autoriza compras. Tras cada paso se llama `onCambio`.
 */
export default function RentaDeMaquinaria({ renta, onCambio, compacta = false }) {
  const { t } = useI18n();
  const [abierto, setAbierto] = useState(null); // "extend" | "decide" | "return"
  const [nuevaFecha, setNuevaFecha] = useState("");
  const [nota, setNota] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");

  if (!renta) return null;
  const etapa = etapaDeRenta(renta);
  const acciones = renta.actions || {};
  const id = renta.id_purchase_order_line;

  async function hacer(llamada, mensajeError) {
    setOcupado(true);
    setError("");
    try {
      const respuesta = await llamada();
      setAbierto(null);
      setNota("");
      setNuevaFecha("");
      onCambio?.(respuesta);
    } catch (e) {
      setError(e?.payload?.error_key ? t(e.payload.error_key, mensajeError) : mensajeError);
    } finally {
      setOcupado(false);
    }
  }

  const dias = renta.days_left;
  let cuando = null;
  if (renta.stage === "on_site" || renta.stage === "overdue") {
    cuando = dias < 0
      ? t("rental.overdue_by", "Venció hace {n} días").replace("{n}", String(-dias))
      : dias === 0 ? t("rental.due_today", "Vence hoy")
        : t("rental.days_left", "Quedan {n} días").replace("{n}", String(dias));
  }

  return (
    <div className={`renta ${compacta ? "renta-compacta" : ""}`}>
      <div className="renta-encabezado">
        <span className={`renta-etapa ${etapa.clase}`}>{t(etapa.clave, renta.stage)}</span>
        <span className="muted">
          {fecha(renta.rental_start)} → {fecha(renta.rental_end)}
          {cuando && <> · <strong>{cuando}</strong></>}
        </span>
        {renta.order_folio && !compacta && (
          <span className="muted">· {renta.order_folio}</span>
        )}
      </div>

      {renta.arrived_date && (
        <p className="muted renta-dato">
          {t("rental.arrived_on", "Llegó a obra el")} {fecha(renta.arrived_date)}
          {renta.returned_date && <> · {t("rental.returned_on", "devuelta el")} {fecha(renta.returned_date)}</>}
        </p>
      )}
      {renta.stage === "waiting_arrival" && !acciones.arrive && (
        <p className="muted renta-dato">
          {t("rental.waiting_hint", "Ya se contrató. Quien lleva la obra marca cuando llegue.")}
        </p>
      )}
      {renta.extension && (
        <p className="renta-prorroga">
          <CalendarClock size={14} />{" "}
          {t("rental.extension_pending", "Prórroga pedida hasta el")} {fecha(renta.extension.requested_end)}
          {renta.extension.note && <>: <em>{renta.extension.note}</em></>}
        </p>
      )}

      {error && <p className="alert error">{error}</p>}

      <div className="renta-acciones">
        {acciones.arrive && (
          <button type="button" className="button primary" disabled={ocupado}
                  onClick={() => hacer(() => rentalArrive(id), "No se pudo marcar la llegada.")}>
            <Truck size={14} /> {t("rental.arrive", "Llegó a obra")}
          </button>
        )}
        {acciones.return && abierto !== "return" && (
          <button type="button" className="button" disabled={ocupado}
                  onClick={() => setAbierto("return")}>
            <Undo2 size={14} /> {t("rental.return", "Devuelta al proveedor")}
          </button>
        )}
        {acciones.extend && abierto !== "extend" && (
          <button type="button" className="button button-quiet" disabled={ocupado}
                  onClick={() => setAbierto("extend")}>
            <CalendarClock size={14} /> {t("rental.extend", "Pedir prórroga")}
          </button>
        )}
        {acciones.decide_extension && abierto !== "decide" && (
          <button type="button" className="button primary" disabled={ocupado}
                  onClick={() => setAbierto("decide")}>
            {t("rental.decide", "Decidir prórroga")}
          </button>
        )}
      </div>

      {abierto === "return" && (
        <div className="renta-formulario">
          <label className="field">
            <span>{t("rental.return_note", "Nota (opcional): quién la recogió, estado en que se entregó")}</span>
            <input type="text" maxLength={300} value={nota} onChange={(e) => setNota(e.target.value)} />
          </label>
          <div className="renta-acciones">
            <button type="button" className="button primary" disabled={ocupado}
                    onClick={() => hacer(() => rentalReturn(id, { note: nota.trim() || undefined }),
                      "No se pudo marcar la devolución.")}>
              <Check size={14} /> {t("rental.confirm_return", "Confirmar devolución")}
            </button>
            <button type="button" className="button button-quiet" onClick={() => setAbierto(null)}>
              <X size={14} /> {t("common.cancel", "Cancelar")}
            </button>
          </div>
        </div>
      )}

      {abierto === "extend" && (
        <div className="renta-formulario">
          <label className="field">
            <span>{t("rental.new_end", "Nueva fecha de fin")}</span>
            <input type="date" min={renta.rental_end || undefined} value={nuevaFecha}
                   onChange={(e) => setNuevaFecha(e.target.value)} />
          </label>
          <label className="field">
            <span>{t("rental.extension_reason", "¿Por qué se necesita más tiempo?")}</span>
            <input type="text" maxLength={300} value={nota} onChange={(e) => setNota(e.target.value)} />
          </label>
          <p className="muted">
            {t("rental.extend_hint", "La decide quien autoriza compras. El costo extra va en la factura final.")}
          </p>
          <div className="renta-acciones">
            <button type="button" className="button primary"
                    disabled={ocupado || !nuevaFecha || nota.trim().length < 5}
                    onClick={() => hacer(() => rentalExtend(id, { new_end: nuevaFecha, note: nota.trim() }),
                      "No se pudo pedir la prórroga.")}>
              {t("rental.send_extension", "Pedir prórroga")}
            </button>
            <button type="button" className="button button-quiet" onClick={() => setAbierto(null)}>
              <X size={14} /> {t("common.cancel", "Cancelar")}
            </button>
          </div>
        </div>
      )}

      {abierto === "decide" && (
        <div className="renta-formulario">
          <label className="field">
            <span>{t("rental.decision_note", "Nota (obligatoria si la rechazas)")}</span>
            <input type="text" maxLength={300} value={nota} onChange={(e) => setNota(e.target.value)} />
          </label>
          <div className="renta-acciones">
            <button type="button" className="button primary" disabled={ocupado}
                    onClick={() => hacer(() => rentalDecideExtension(id, { approve: true, note: nota.trim() || undefined }),
                      "No se pudo aprobar la prórroga.")}>
              <Check size={14} /> {t("rental.approve", "Aprobar")}
            </button>
            <button type="button" className="button danger" disabled={ocupado || nota.trim().length < 5}
                    onClick={() => hacer(() => rentalDecideExtension(id, { approve: false, note: nota.trim() }),
                      "No se pudo rechazar la prórroga.")}>
              <X size={14} /> {t("rental.reject", "Rechazar")}
            </button>
            <button type="button" className="button button-quiet" onClick={() => setAbierto(null)}>
              {t("common.cancel", "Cancelar")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

RentaDeMaquinaria.propTypes = {
  renta: PropTypes.shape({
    stage: PropTypes.string,
    id_purchase_order_line: PropTypes.number,
    rental_start: PropTypes.string,
    rental_end: PropTypes.string,
    days_left: PropTypes.number,
    arrived_date: PropTypes.string,
    returned_date: PropTypes.string,
    order_folio: PropTypes.string,
    extension: PropTypes.shape({ requested_end: PropTypes.string, note: PropTypes.string }),
    actions: PropTypes.object,
  }),
  onCambio: PropTypes.func,
  compacta: PropTypes.bool,
};
