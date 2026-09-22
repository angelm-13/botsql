/**
 * La cascara: encabezado con el estado real del servicio, y la consola.
 *
 * El indicador de salud esta arriba a proposito. Las dos preguntas que se hace
 * quien estrena esto son siempre las mismas -- "¿está conectado a la base?" y
 * "¿está corriendo el modelo?" -- y la respuesta estaba escondida en un
 * endpoint que nadie abre. Ponerla a la vista ahorra la mitad de los reportes
 * de "no funciona".
 */

import { useEffect, useState } from "react";

import { obtenerSalud, type Salud } from "./api";
import { BIChat } from "./components/BIChat";
import { usarPaleta } from "./theme";

export function App() {
  const { tokens } = usarPaleta();
  const [salud, setSalud] = useState<Salud | null>(null);

  useEffect(() => {
    obtenerSalud().then(setSalud).catch(() => setSalud(null));
  }, []);

  return (
    <div className="flex h-screen flex-col">
      <header
        className="flex items-center justify-between border-b px-4 py-3"
        style={{ borderColor: tokens.borde, backgroundColor: tokens.superficie }}
      >
        <h1 className="text-sm font-semibold" style={{ color: tokens.tintaPrimaria }}>
          Inteligencia de Negocios
        </h1>
        <div className="flex items-center gap-4 text-xs" style={{ color: tokens.tintaSecundaria }}>
          <Indicador
            ok={salud?.base_de_datos.conecta ?? false}
            etiqueta={salud ? `Base (${salud.base_de_datos.motor})` : "Base"}
          />
          <Indicador
            ok={salud?.modelo.disponible ?? false}
            etiqueta={salud?.modelo.nombre || "Modelo"}
          />
        </div>
      </header>

      {salud?.advertencias?.length ? (
        <ul
          className="border-b px-4 py-2 text-xs"
          style={{ borderColor: tokens.borde, color: tokens.tintaSecundaria }}
        >
          {salud.advertencias.map((a, i) => (
            <li key={i}>⚠ {a}</li>
          ))}
        </ul>
      ) : null}

      <main className="min-h-0 flex-1">
        <BIChat />
      </main>
    </div>
  );
}

/**
 * Estado con forma y texto, no solo color.
 *
 * Un punto verde y uno rojo son el mismo punto gris para quien no distingue
 * esos dos tonos; el simbolo y la etiqueta hacen el trabajo, y el color solo
 * refuerza.
 */
function Indicador({ ok, etiqueta }: { ok: boolean; etiqueta: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span aria-hidden style={{ color: ok ? "#008300" : "#e34948" }}>
        {ok ? "●" : "▲"}
      </span>
      <span>
        {etiqueta}: {ok ? "ok" : "sin conexión"}
      </span>
    </span>
  );
}
