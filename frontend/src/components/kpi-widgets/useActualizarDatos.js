import { useCallback, useEffect, useRef, useState } from "react";
import { recalcularKpiDashboard } from "../../api";
import { ESPERA_TRAS_EXITO_MS, idsAlDia, itemsAActualizar, resultadoFinal } from "../../kpi/kpiActualizar.js";

// El boton "Actualizar datos" de un tablero: recalcula un indicador por llamada, en secuencia (asi el "n de N" es real),
// y al terminar avisa para que las tarjetas vuelvan a pedir sus datos. La logica de que se pide y como se resume vive
// en kpi/kpiActualizar.js (con pruebas); aqui solo esta el estado de pantalla.
//
// `recalculados` recuerda, solo en esta sesion de pantalla, los indicadores que quedaron al dia: un indicador sin
// eventos no escribe filas, asi que su fecha de calculo sigue vieja aunque se acabe de recalcular.
export default function useActualizarDatos({ idTablero, widgets, kpiCatalog, alTerminar }) {
  const [estado, setEstado] = useState({ fase: "inactivo" });
  const [enEspera, setEnEspera] = useState(false);
  const [recalculados, setRecalculados] = useState({});
  const corriendo = useRef(false);
  const temporizador = useRef(null);

  useEffect(() => () => clearTimeout(temporizador.current), []);
  useEffect(() => {
    clearTimeout(temporizador.current);
    setEstado({ fase: "inactivo" });
    setEnEspera(false);
  }, [idTablero]);

  const actualizar = useCallback(async () => {
    if (corriendo.current || !idTablero) return;
    const items = itemsAActualizar(widgets, kpiCatalog);
    if (items.length === 0) {
      setEstado({ fase: "final", resultado: resultadoFinal({ total: 0, respuestas: [] }) });
      return;
    }
    corriendo.current = true;
    const respuestas = [];
    let fallo = null;
    setEstado({ fase: "corriendo", hechos: 0, total: items.length });
    for (const item of items) {
      try {
        respuestas.push(await recalcularKpiDashboard(idTablero, { items: [item] }));
      } catch (error) {
        fallo = error?.message || "errors.request_failed";
        break;
      }
      setEstado({ fase: "corriendo", hechos: respuestas.length, total: items.length });
    }
    const resultado = resultadoFinal({ total: items.length, respuestas, fallo });
    const alDia = idsAlDia(respuestas);
    if (alDia.length > 0) {
      const cuando = respuestas[respuestas.length - 1]?.recalculado_en || null;
      setRecalculados((actual) => ({ ...actual, ...Object.fromEntries(alDia.map((id) => [id, cuando])) }));
      alTerminar?.();
    }
    if (resultado.tipo === "listo" || resultado.tipo === "ya_al_dia") {
      setEnEspera(true);
      temporizador.current = setTimeout(() => setEnEspera(false), ESPERA_TRAS_EXITO_MS);
    }
    setEstado({ fase: "final", resultado });
    corriendo.current = false;
  }, [idTablero, widgets, kpiCatalog, alTerminar]);

  return { estado, enEspera, recalculados, actualizar };
}
