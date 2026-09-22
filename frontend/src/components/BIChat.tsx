/**
 * La consola de BI: se escribe una pregunta y aparece el tablero.
 *
 * Tres decisiones de comportamiento
 * ---------------------------------
 *  * **La conversacion se conserva.** Cada pregunta deja su tablero en la
 *    pantalla. Comparar "ventas por mes" con "ventas por vendedor" es el uso
 *    real de una herramienta asi, y borrar la respuesta anterior en cada turno
 *    lo impide.
 *  * **La pregunta en vuelo se puede cancelar.** Un modelo local puede tardar
 *    decenas de segundos; sin `AbortController` la unica salida es recargar.
 *  * **Un error se explica, no se disculpa.** Si el modelo esta apagado, si la
 *    consulta no paso la revision o si el JSON vino mal, se dice cual de las
 *    tres fue: son tres arreglos distintos.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { consultarBI, ErrorDeRed } from "../api";
import type { Turno } from "../types";
import { usarPaleta } from "../theme";
import { DashboardGrid } from "./DashboardGrid";

const EJEMPLOS = [
  "¿Cuánto vendimos en total?",
  "Ventas por mes de este año",
  "Top 5 productos por importe",
  "Ventas por ciudad",
  "Hazme un dashboard general de ventas",
];

export function BIChat() {
  const [texto, setTexto] = useState("");
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const enVuelo = useRef<AbortController | null>(null);
  const finDeLista = useRef<HTMLDivElement>(null);
  const { tokens } = usarPaleta();

  const cargando = turnos.some((t) => t.estado === "cargando");

  useEffect(() => {
    finDeLista.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turnos]);

  const preguntar = useCallback(async (pregunta: string) => {
    const limpia = pregunta.trim();
    if (!limpia || enVuelo.current) return;

    const id = crypto.randomUUID();
    setTurnos((prev) => [...prev, { id, pregunta: limpia, estado: "cargando" }]);
    setTexto("");

    const control = new AbortController();
    enVuelo.current = control;

    try {
      const respuesta = await consultarBI(limpia, control.signal);
      setTurnos((prev) =>
        prev.map((t) => (t.id === id ? { ...t, estado: "listo", respuesta } : t)),
      );
    } catch (e) {
      const abortada = (e as Error).name === "AbortError";
      setTurnos((prev) =>
        prev.map((t) =>
          t.id === id
            ? {
                ...t,
                estado: "fallo",
                mensajeDeRed: abortada
                  ? "Cancelada."
                  : e instanceof ErrorDeRed
                    ? e.message
                    : "Error inesperado.",
              }
            : t,
        ),
      );
    } finally {
      enVuelo.current = null;
    }
  }, []);

  return (
    <div className="flex h-full flex-col">
      <div className="min-h-0 flex-1 space-y-8 overflow-y-auto px-4 py-6">
        {turnos.length === 0 && <Bienvenida alElegir={preguntar} />}

        {turnos.map((turno) => (
          <article key={turno.id} className="space-y-3">
            <h2
              className="text-sm font-medium"
              style={{ color: tokens.tintaSecundaria }}
            >
              <span style={{ color: tokens.tintaTenue }}>Pregunta ·</span>{" "}
              {turno.pregunta}
            </h2>

            {turno.estado === "cargando" && (
              <p className="animate-pulse text-sm" style={{ color: tokens.tintaTenue }}>
                Traduciendo a SQL y ejecutando…
              </p>
            )}

            {turno.estado === "fallo" && (
              <Aviso texto={turno.mensajeDeRed ?? "Falló la consulta."} />
            )}

            {turno.estado === "listo" && turno.respuesta && (
              <>
                {turno.respuesta.error && (
                  <Aviso
                    texto={
                      turno.respuesta.error.tipo === "rechazada_por_el_modelo"
                        ? `El asistente se negó: ${turno.respuesta.error.mensaje}`
                        : (turno.respuesta.error.mensaje ?? turno.respuesta.error.tipo)
                    }
                  />
                )}
                <DashboardGrid
                  widgets={turno.respuesta.widgets}
                  titulo={
                    turno.respuesta.is_dashboard
                      ? turno.respuesta.dashboard_title
                      : undefined
                  }
                />
                <PieDeMeta turno={turno} />
              </>
            )}
          </article>
        ))}
        <div ref={finDeLista} />
      </div>

      <form
        className="flex gap-2 border-t px-4 py-3"
        style={{ borderColor: tokens.borde }}
        onSubmit={(e) => {
          e.preventDefault();
          void preguntar(texto);
        }}
      >
        <input
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          // El Enter se maneja explicitamente en vez de dejarlo al envio
          // implicito del formulario, que depende de que el boton de envio no
          // este deshabilitado -- y aqui lo esta mientras el campo va vacio.
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void preguntar(e.currentTarget.value);
            }
          }}
          placeholder="Pregunta por tus datos: “ventas por mes de este año”"
          className="flex-1 rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2"
          style={{
            borderColor: tokens.borde,
            backgroundColor: tokens.superficie,
            color: tokens.tintaPrimaria,
          }}
          aria-label="Pregunta en lenguaje natural"
        />
        {cargando ? (
          <button
            type="button"
            onClick={() => enVuelo.current?.abort()}
            className="rounded-lg border px-4 py-2 text-sm"
            style={{ borderColor: tokens.borde, color: tokens.tintaSecundaria }}
          >
            Cancelar
          </button>
        ) : (
          <button
            type="submit"
            disabled={!texto.trim()}
            className="rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
            style={{ backgroundColor: "#2a78d6" }}
          >
            Preguntar
          </button>
        )}
      </form>
    </div>
  );
}

function Bienvenida({ alElegir }: { alElegir: (p: string) => void }) {
  const { tokens } = usarPaleta();
  return (
    <div className="mx-auto max-w-xl py-12 text-center">
      <h2 className="text-lg font-semibold" style={{ color: tokens.tintaPrimaria }}>
        Pregúntale a tus datos
      </h2>
      <p className="mt-2 text-sm" style={{ color: tokens.tintaSecundaria }}>
        Se traduce a SQL de solo lectura, se ejecuta acotado y se dibuja. Siempre
        puedes ver la consulta exacta que corrió.
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        {EJEMPLOS.map((e) => (
          <button
            key={e}
            type="button"
            onClick={() => alElegir(e)}
            className="rounded-full border px-3 py-1.5 text-xs"
            style={{ borderColor: tokens.borde, color: tokens.tintaSecundaria }}
          >
            {e}
          </button>
        ))}
      </div>
    </div>
  );
}

function Aviso({ texto }: { texto: string }) {
  const { tokens } = usarPaleta();
  return (
    <p
      className="rounded-lg border border-dashed px-3 py-2 text-sm"
      style={{ borderColor: tokens.borde, color: tokens.tintaSecundaria }}
      role="status"
    >
      {texto}
    </p>
  );
}

function PieDeMeta({ turno }: { turno: Turno }) {
  const { tokens } = usarPaleta();
  const m = turno.respuesta?.meta;
  if (!m?.modelo) return null;
  return (
    <p className="text-xs" style={{ color: tokens.tintaTenue }}>
      {m.modelo} · {m.ms_modelo} ms de modelo · {m.ms_total} ms en total
      {m.motor ? ` · ${m.motor}` : ""}
    </p>
  );
}
