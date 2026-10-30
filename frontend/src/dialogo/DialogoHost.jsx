import { useEffect, useRef, useState } from "react";
import { useI18n } from "../i18n";
import { accionDeTecla } from "./dialogoControl.js";
import { controlador } from "./useDialogo.js";
import "../styles/dialogo.css";

function Dialogo() {
  const { t } = useI18n();
  const [peticion, setPeticion] = useState(null);
  const [texto, setTexto] = useState("");
  const entrada = useRef(null);
  const aceptar = useRef(null);
  const caja = useRef(null);

  useEffect(() => controlador.suscribir((nueva) => {
    setPeticion(nueva);
    setTexto(nueva?.valorInicial || "");
  }), []);

  const id = peticion?.id;
  useEffect(() => {
    if (!id) return undefined;
    const previo = document.activeElement;
    (entrada.current || aceptar.current)?.focus();
    entrada.current?.select();
    return () => previo?.focus?.();
  }, [id]);

  if (!peticion) return null;

  function alTeclear(evento) {
    const accion = accionDeTecla({ key: evento.key, enBoton: evento.target.tagName === "BUTTON" });
    if (accion === "cancelar") { evento.preventDefault(); controlador.cancelar(); }
    else if (accion === "aceptar") { evento.preventDefault(); controlador.aceptar(texto); }
    else if (evento.key === "Tab") {
      // El foco se queda dentro del diálogo.
      const foco = [...caja.current.querySelectorAll("input, button:not(:disabled)")];
      const primero = foco[0];
      const ultimo = foco[foco.length - 1];
      if (evento.shiftKey && document.activeElement === primero) { evento.preventDefault(); ultimo.focus(); }
      else if (!evento.shiftKey && document.activeElement === ultimo) { evento.preventDefault(); primero.focus(); }
    }
  }

  const esTexto = peticion.tipo === "texto";

  return (
    <div className="dialogo-fondo" onMouseDown={(e) => { if (e.target === e.currentTarget && peticion.tipo !== "aviso") controlador.cancelar(); }}>
      <div className="dialogo" role="dialog" aria-modal="true" aria-labelledby="dialogo-mensaje" ref={caja} onKeyDown={alTeclear}>
        <p id="dialogo-mensaje" className="dialogo-mensaje">{esTexto ? peticion.titulo : peticion.mensaje}</p>
        {esTexto && (
          <input ref={entrada} className="dialogo-entrada" type="text" value={texto} onChange={(e) => setTexto(e.target.value)} aria-labelledby="dialogo-mensaje" />
        )}
        <div className="dialogo-acciones">
          {peticion.tipo !== "aviso" && (
            <button type="button" className="button" onClick={() => controlador.cancelar()}>{t("common.cancel", "Cancelar")}</button>
          )}
          <button type="button" ref={aceptar} className="button dialogo-aceptar" disabled={esTexto && !texto.trim()} onClick={() => controlador.aceptar(texto)}>
            {t("common.accept", "Aceptar")}
          </button>
        </div>
      </div>
    </div>
  );
}

export default Dialogo;
