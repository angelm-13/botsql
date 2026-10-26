// Lógica de los diálogos propios (confirmar / pedir texto / avisar), sin React.
//
// Reemplaza window.confirm / prompt / alert con el mismo contrato: cada
// llamada devuelve una promesa que se resuelve al cerrarse el diálogo.
//   confirmar  -> true (Aceptar) | false (Cancelar o Esc)
//   pedirTexto -> string (Aceptar) | null (Cancelar o Esc)
//   avisar     -> undefined (al cerrarlo)
// Si se abre uno mientras otro sigue en pantalla, queda en fila: el nativo
// bloqueaba, así que dos llamadas seguidas nunca se encimaban.

export function crearControlador() {
  let actual = null;
  let contador = 0;
  const cola = [];
  const oyentes = new Set();

  function emitir() {
    oyentes.forEach((oyente) => oyente(actual));
  }

  function siguiente() {
    actual = cola.shift() || null;
    emitir();
  }

  function abrir(peticion) {
    return new Promise((resolver) => {
      cola.push({ ...peticion, id: ++contador, resolver });
      if (!actual) siguiente();
    });
  }

  function cerrar(valor) {
    if (!actual) return;
    const { resolver } = actual;
    resolver(valor);
    siguiente();
  }

  return {
    confirmar: (mensaje) => abrir({ tipo: "confirmar", mensaje }),
    pedirTexto: (titulo, valorInicial = "") => abrir({ tipo: "texto", titulo, valorInicial }),
    avisar: (mensaje) => abrir({ tipo: "aviso", mensaje }),

    // Aceptar con texto vacío no hace nada (el diálogo sigue abierto).
    aceptar(texto = "") {
      if (!actual) return false;
      if (actual.tipo === "texto") {
        if (!texto.trim()) return false;
        cerrar(texto);
      } else if (actual.tipo === "confirmar") {
        cerrar(true);
      } else {
        cerrar(undefined);
      }
      return true;
    },

    cancelar() {
      if (!actual) return;
      cerrar(actual.tipo === "confirmar" ? false : actual.tipo === "texto" ? null : undefined);
    },

    suscribir(oyente) {
      oyentes.add(oyente);
      oyente(actual);
      return () => oyentes.delete(oyente);
    },
  };
}

// Esc cancela; Enter acepta, salvo sobre un botón (ahí Enter lo activa a él,
// como con el diálogo nativo: Enter sobre "Cancelar" cancela).
export function accionDeTecla({ key, enBoton = false }) {
  if (key === "Escape") return "cancelar";
  if (key === "Enter" && !enBoton) return "aceptar";
  return null;
}
