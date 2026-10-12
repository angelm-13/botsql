// El backend responde 201 aunque el PAC rechace el timbrado: el resultado real
// viaja en `operation.status`. Una pantalla solo puede dar el timbrado por
// bueno si ese estatus es "stamped".

export function stampingProviderMessage(operation) {
  const raw = operation?.response_metadata?.provider_response;
  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      if (parsed?.Message) return String(parsed.Message);
    } catch {
      /* el PAC no siempre responde JSON */
    }
    return String(raw);
  }
  return operation?.error_code || "";
}

// Devuelve { ok: true } o { ok: false, message } con el motivo para mostrar.
export function stampingOutcome(result) {
  const operation = result?.operation;
  if (operation?.status === "stamped") return { ok: true };
  if (operation?.status === "uncertain") {
    return {
      ok: false,
      message: "El PAC no confirmó el timbrado (sin respuesta). No se dio por timbrada; revisa antes de reintentar.",
    };
  }
  const detail = stampingProviderMessage(operation);
  return { ok: false, message: `El PAC rechazó el timbrado${detail ? `: ${detail}` : "."}` };
}
