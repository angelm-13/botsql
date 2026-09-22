/**
 * La unica funcion que habla con el backend.
 *
 * Detalle que importa: el backend contesta con un JSON con forma de respuesta
 * INCLUSO cuando el codigo HTTP es 403, 422, 502 o 503 -- un rechazo por
 * seguridad o un modelo apagado no son "errores de red", son respuestas con
 * informacion. Por eso no se tira `throw` ante un codigo de error: se intenta
 * leer el cuerpo y se devuelve tal cual, para que la interfaz pueda explicar
 * que paso en vez de mostrar "algo salio mal".
 */

import type { RespuestaBI, ResumenDeEsquema } from "./types";

const BASE = import.meta.env.VITE_BI_API ?? "/api/v1/bi";

export class ErrorDeRed extends Error {}

export async function consultarBI(
  prompt: string,
  senal?: AbortSignal,
): Promise<RespuestaBI> {
  let r: Response;
  try {
    r = await fetch(`${BASE}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
      signal: senal,
    });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ErrorDeRed(
      "No se pudo contactar al servidor de BI. Revisa que este corriendo.",
    );
  }

  let cuerpo: unknown;
  try {
    cuerpo = await r.json();
  } catch {
    throw new ErrorDeRed(
      `El servidor contesto ${r.status} con algo que no es JSON.`,
    );
  }

  const datos = cuerpo as Partial<RespuestaBI>;
  if (!Array.isArray(datos.widgets)) {
    // Un 500 sin forma de respuesta. Se normaliza para que la interfaz tenga
    // siempre la misma estructura que dibujar.
    return {
      ok: false,
      pregunta: prompt,
      is_dashboard: false,
      dashboard_title: "",
      widgets: [],
      meta: {},
      error: (datos as { error?: RespuestaBI["error"] }).error ?? {
        tipo: "respuesta_inesperada",
        mensaje: `El servidor contesto ${r.status}.`,
      },
    };
  }
  return datos as RespuestaBI;
}

export async function obtenerEsquema(): Promise<ResumenDeEsquema> {
  const r = await fetch(`${BASE}/schema`);
  if (!r.ok) throw new ErrorDeRed(`No se pudo leer el esquema (${r.status}).`);
  return (await r.json()) as ResumenDeEsquema;
}

export interface Salud {
  ok: boolean;
  base_de_datos: { conecta: boolean; error: string; motor: string };
  modelo: { proveedor: string; nombre: string; disponible: boolean };
  advertencias: string[];
}

export async function obtenerSalud(): Promise<Salud> {
  const r = await fetch(`${BASE}/health`);
  return (await r.json()) as Salud;
}
