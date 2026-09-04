import React, { useState } from "react";
import { AlertTriangle, Banknote, DoorClosed, DoorOpen } from "lucide-react";
import { useI18n } from "../../i18n";
import { posRequest } from "../../api";
import PosScreen, { dinero, listaDe, mensajeDeError, numero } from "./PosScreen";

/**
 * Apertura y cierre de turno de caja.
 *
 * El turno es lo primero y lo ultimo del dia del cajero, y por eso vive en su
 * propia pantalla en vez de escondido en un menu: sin turno abierto no se
 * puede cobrar, y sin cierre no hay corte que cuadrar.
 *
 * Dos decisiones que se ven aqui:
 *
 * * **El sistema no sugiere cuanto hay en el cajon.** Al cerrar se declara a
 *   ciegas lo contado y solo despues aparece la diferencia. Si la pantalla
 *   mostrara el esperado antes, la declaracion dejaria de ser un conteo y
 *   pasaria a ser una confirmacion, que es como un faltante se vuelve
 *   invisible.
 * * **El corte X no cierra.** Sirve para revisar a media jornada; el que cierra
 *   es el Z. Van separados y con nombre distinto porque confundirlos deja la
 *   caja cerrada a medio turno.
 */

const METODOS = ["cash", "card", "transfer", "mixed"];

export default function PosShiftPage() {
  const { t } = useI18n();
  const [caja, setCaja] = useState("Caja 1");
  const [fondo, setFondo] = useState("0");
  const [declarado, setDeclarado] = useState({});
  const [notas, setNotas] = useState("");
  const [retiro, setRetiro] = useState({ amount: "", reason: "" });
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState(null);
  const [corte, setCorte] = useState(null);

  const ejecutar = async (accion, recargar) => {
    setOcupado(true);
    setAviso(null);
    try {
      const resultado = await accion();
      await recargar();
      return resultado;
    } catch (error) {
      setAviso({ tipo: "error", texto: mensajeDeError(error, t) });
      return null;
    } finally {
      setOcupado(false);
    }
  };

  return (
    <PosScreen
      titulo={t("pos.shift_title", "Turno de caja")}
      descripcion={t("pos.shift_subtitle",
        "Abrir la caja, retirar efectivo y hacer el corte al terminar.")}
      recursos={{ abiertos: "cash/sessions/open", historial: "cash/sessions/history" }}
    >
      {(datos, { recargar }) => {
        const turno = listaDe(datos.abiertos)[0] || null;
        const historial = listaDe(datos.historial).slice(0, 12);

        const abrir = () => ejecutar(
          () => posRequest("cash/sessions/open", {
            method: "POST",
            body: { register_name: caja.trim(), opening_amount: Number(fondo || 0) },
          }), recargar);

        const retirar = () => ejecutar(
          () => posRequest(`cash/sessions/${turno.id}/withdrawals`, {
            method: "POST",
            body: { amount: Number(retiro.amount || 0), reason: retiro.reason.trim() },
          }).then((r) => { setRetiro({ amount: "", reason: "" }); return r; }), recargar);

        const cerrar = async (tipo) => {
          const montos = Object.fromEntries(
            Object.entries(declarado)
              .filter(([, v]) => String(v).trim() !== "")
              .map(([k, v]) => [k, Number(v)])
          );
          if (!Object.keys(montos).length) {
            setAviso({ tipo: "error", texto: t("pos.declare_at_least_one",
              "Declara al menos una forma de pago antes de cerrar.") });
            return;
          }
          const r = await ejecutar(
            () => posRequest(`cash/sessions/${turno.id}/close`, {
              method: "POST",
              body: { close_type: tipo, declared_amounts: montos, notes: notas.trim() || null },
            }), recargar);
          if (r) {
            setCorte({ tipo, ...r });
            if (tipo === "z") { setDeclarado({}); setNotas(""); }
          }
        };

        return (
          <>
            {aviso && <p className="error">{aviso.texto}</p>}

            {!turno ? (
              <section className="pos-panel pos-form">
                <h2 className="pos-section-title">
                  <DoorOpen size={17} /> {t("pos.open_shift", "Abrir turno")}
                </h2>
                <p className="muted">
                  {t("pos.open_shift_hint",
                    "Sin turno abierto no se puede cobrar. El fondo inicial es el efectivo con el que arranca el cajón.")}
                </p>
                <div className="pos-fields">
                  <label>
                    <span>{t("pos.register_name", "Caja")}</span>
                    <input value={caja} onChange={(e) => setCaja(e.target.value)} maxLength={50} />
                  </label>
                  <label>
                    <span>{t("pos.opening_amount", "Fondo inicial")}</span>
                    <input type="number" min="0" step="0.01" value={fondo}
                           onChange={(e) => setFondo(e.target.value)} />
                  </label>
                </div>
                <button className="button primary" disabled={ocupado || !caja.trim()} onClick={abrir}>
                  <DoorOpen size={16} /> {t("pos.open_shift", "Abrir turno")}
                </button>
              </section>
            ) : (
              <>
                <div className="pos-tally">
                  <div className="pos-tally-card ok">
                    <span className="pos-tally-count">{turno.register_name}</span>
                    <span className="pos-tally-label">{t("pos.open_since", "Abierta desde")}{" "}
                      {new Date(turno.opened_at).toLocaleString("es-MX")}</span>
                  </div>
                  <div className="pos-tally-card">
                    <span className="pos-tally-count">{dinero(turno.opening_amount)}</span>
                    <span className="pos-tally-label">{t("pos.opening_amount", "Fondo inicial")}</span>
                  </div>
                  <div className="pos-tally-card">
                    <span className="pos-tally-count">{dinero(turno.withdrawals_total)}</span>
                    <span className="pos-tally-label">{t("pos.withdrawals", "Retiros")}</span>
                  </div>
                </div>

                <div className="pos-columns">
                  <section className="pos-panel pos-form">
                    <h2 className="pos-section-title">
                      <Banknote size={17} /> {t("pos.withdrawal", "Retirar efectivo")}
                    </h2>
                    <p className="muted">
                      {t("pos.withdrawal_hint",
                        "Sacar dinero del cajón sin registrarlo aquí aparece después como faltante en el corte.")}
                    </p>
                    <div className="pos-fields">
                      <label>
                        <span>{t("pos.amount", "Importe")}</span>
                        <input type="number" min="0" step="0.01" value={retiro.amount}
                               onChange={(e) => setRetiro({ ...retiro, amount: e.target.value })} />
                      </label>
                      <label className="ancho">
                        <span>{t("pos.reason", "Motivo")}</span>
                        <input value={retiro.reason} maxLength={255}
                               onChange={(e) => setRetiro({ ...retiro, reason: e.target.value })} />
                      </label>
                    </div>
                    <button className="button" disabled={ocupado || !retiro.reason.trim()
                              || !(Number(retiro.amount) > 0)} onClick={retirar}>
                      <Banknote size={15} /> {t("pos.register_withdrawal", "Registrar retiro")}
                    </button>
                  </section>

                  <section className="pos-panel pos-form">
                    <h2 className="pos-section-title">
                      <DoorClosed size={17} /> {t("pos.close_shift", "Corte")}
                    </h2>
                    {/* Se declara a ciegas: la pantalla no dice cuanto deberia
                        haber. Ver el encabezado del archivo. */}
                    <p className="muted">
                      {t("pos.close_hint",
                        "Cuenta el cajón y declara lo que encontraste. La diferencia aparece después de cerrar.")}
                    </p>
                    <div className="pos-fields">
                      {METODOS.map((m) => (
                        <label key={m}>
                          <span>{t(`pos.method_${m}`, m)}</span>
                          <input type="number" min="0" step="0.01" value={declarado[m] ?? ""}
                                 placeholder="—"
                                 onChange={(e) => setDeclarado({ ...declarado, [m]: e.target.value })} />
                        </label>
                      ))}
                      <label className="ancho">
                        <span>{t("pos.notes", "Notas")}</span>
                        <input value={notas} onChange={(e) => setNotas(e.target.value)} />
                      </label>
                    </div>
                    <div className="pos-header-actions">
                      <button className="button" disabled={ocupado} onClick={() => cerrar("x")}>
                        {t("pos.close_x", "Corte X (revisión)")}
                      </button>
                      <button className="button primary" disabled={ocupado} onClick={() => cerrar("z")}>
                        <DoorClosed size={15} /> {t("pos.close_z", "Corte Z (cerrar)")}
                      </button>
                    </div>
                  </section>
                </div>
              </>
            )}

            {corte && (() => {
              // La respuesta del corte trae un diccionario por forma de pago,
              // no un total: {"cash": 350, "card": 0}. Se pinta asi y no
              // sumado, porque saber que faltan cincuenta pesos sirve poco si
              // no se sabe en que metodo; y el efectivo es el unico que se
              // cuenta a mano, o sea el unico donde un faltante significa algo.
              const metodos = Object.keys(corte.declared || {});
              const descuadrado = metodos.some((m) => Number(corte.discrepancy?.[m] || 0) !== 0);
              return (
                <section className={descuadrado ? "pos-warn" : "pos-panel pos-form"}>
                  {descuadrado ? <AlertTriangle size={16} /> : null}
                  <div>
                    <p><strong>
                      {corte.tipo === "x"
                        ? t("pos.x_done", "Corte X registrado. La caja sigue abierta.")
                        : t("pos.z_done", "Turno cerrado.")}
                    </strong></p>
                    <ul className="pos-cut-lines">
                      {metodos.map((m) => {
                        const dif = Number(corte.discrepancy?.[m] || 0);
                        return (
                          <li key={m}>
                            <span>{t(`pos.method_${m}`, m)}</span>
                            <span className="mono">
                              {t("pos.expected", "Esperado")} {dinero(corte.expected?.[m] ?? 0)}
                              {" · "}
                              {t("pos.declared", "Declarado")} {dinero(corte.declared?.[m])}
                            </span>
                            <strong className={dif ? "mono bajo" : "mono"}>
                              {dif > 0 ? "+" : ""}{dinero(dif)}
                            </strong>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                </section>
              );
            })()}

            <h2 className="pos-section-title">{t("pos.shift_history", "Cortes")}</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t("pos.register_name", "Caja")}</th>
                    <th>{t("pos.cut_type", "Tipo")}</th>
                    <th>{t("pos.closed_at", "Cerrado")}</th>
                    <th className="num">{t("pos.opening_amount", "Fondo")}</th>
                    <th className="num">{t("pos.expected", "Esperado")}</th>
                    <th className="num">{t("pos.declared", "Declarado")}</th>
                    <th className="num">{t("pos.difference", "Diferencia")}</th>
                  </tr>
                </thead>
                <tbody>
                  {historial.length === 0 && (
                    <tr><td colSpan="7" className="muted">
                      {t("pos.no_data", "Sin datos todavía.")}
                    </td></tr>
                  )}
                  {historial.map((s) => {
                    const dif = Number(s.difference || 0);
                    return (
                      <tr key={s.id}>
                        <td>{s.register_name}</td>
                        <td>
                          {/* Sin `closed_at` es un corte X: se reviso la caja
                              pero sigue abierta. */}
                          <span className={s.closed_at ? "pos-chip muted" : "pos-chip ok"}>
                            {s.closed_at ? t("pos.cut_z", "Cierre Z") : t("pos.cut_x", "Revisión X")}
                          </span>
                        </td>
                        <td className="mono">
                          {s.closed_at ? new Date(s.closed_at).toLocaleString("es-MX") : "—"}
                        </td>
                        <td className="num mono">{dinero(s.opening_amount)}</td>
                        <td className="num mono">{dinero(s.expected_amount)}</td>
                        <td className="num mono">{dinero(s.closing_amount)}</td>
                        <td className={dif ? "num mono bajo" : "num mono"}>
                          {dinero(s.difference)}
                          {s.notes && <p className="muted">{s.notes}</p>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p className="muted">
              {numero(historial.length)} {t("pos.shifts_shown", "cortes más recientes")}
            </p>
          </>
        );
      }}
    </PosScreen>
  );
}
