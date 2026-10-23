import { useEffect, useRef, useState } from "react";
import { biHealth, biQuery } from "../api";
import BiWidget from "../components/BiWidget";
import "../styles/bi-premium.css";

const SUGERENCIAS = [
  "Top 8 productos por existencias",
  "¿Cuántas incidencias hay por tipo?",
  "Total de facturas por cliente",
  "Dashboard general de operaciones",
  "¿Qué es un vale vencido?",
];

const ERRORES = {
  no_autenticado: "Tu sesión expiró. Vuelve a iniciar sesión.",
  modelo_no_disponible: "El modelo de IA no está disponible en este momento.",
  directiva_invalida: "El modelo no logró interpretar la pregunta. Intenta reformularla.",
  rechazada_por_el_modelo: "El asistente no puede responder esa pregunta.",
  ninguna_consulta_ejecutable: "No se pudo obtener información con esa pregunta. Intenta reformularla con otros términos.",
  esquema_vacio: "Tu rol no tiene acceso a ninguna tabla para consultar.",
};

// Una sola llamada a /health informa de las dos cosas; cada etiqueta muestra su parte.
const PARTES = {
  modelo: { etiqueta: "Modelo de IA", ok: (h) => h.modelo?.disponible, detalle: (h) => `${h.modelo?.proveedor || ""} ${h.modelo?.nombre || ""}`.trim() },
  bd: { etiqueta: "PostgreSQL", ok: (h) => h.base_de_datos?.conecta, detalle: (h) => h.base_de_datos?.conecta ? h.base_de_datos.motor : h.base_de_datos?.error },
};

function EtiquetaSalud({ parte }) {
  const { etiqueta, ok, detalle } = PARTES[parte];
  const [estado, setEstado] = useState(null); // null = consultando

  useEffect(() => {
    let vivo = true;
    const probar = async () => {
      let h;
      try { h = await biHealth(); } catch (err) { h = err?.payload; } // con la base caida responde 503 con el cuerpo completo
      if (!vivo) return;
      setEstado(h?.base_de_datos ? { ok: !!ok(h), texto: detalle(h) } : { ok: false, texto: "Sin respuesta del servidor" });
    };
    probar();
    const t = setInterval(probar, 30000);
    return () => { vivo = false; clearInterval(t); };
  }, []);

  const color = estado === null ? "#9e9e9e" : estado.ok ? "#2e7d32" : "#c62828";
  return (
    <span role="status" style={{ marginRight: 16, color }}>
      ● {etiqueta}: {estado === null ? "consultando…" : estado.ok ? "funcionando" : "no responde"}
      {estado?.texto ? ` (${estado.texto})` : ""}
    </span>
  );
}

export default function BiPage() {
  const [pregunta, setPregunta] = useState("");
  const [cargando, setCargando] = useState(false);
  const [segundos, setSegundos] = useState(0);
  const [respuesta, setRespuesta] = useState(null);
  const [error, setError] = useState(null);
  const [historial, setHistorial] = useState([]);
  const reloj = useRef(null);

  useEffect(() => () => clearInterval(reloj.current), []);

  async function enviar(e, texto) {
    e?.preventDefault();
    const q = (texto ?? pregunta).trim();
    if (!q || cargando) return;
    setPregunta(q);
    setCargando(true);
    setError(null);
    setRespuesta(null);
    setSegundos(0);
    reloj.current = setInterval(() => setSegundos((s) => s + 1), 1000);
    try {
      const r = await biQuery(q);
      setRespuesta(r);
      setHistorial((h) => [{ q, hora: new Date().toLocaleTimeString() }, ...h.filter((x) => x.q !== q)].slice(0, 6));
    } catch (err) {
      // El backend devuelve {ok:false, error:{tipo,mensaje}} con un 4xx/5xx.
      const cuerpo = err?.payload || {};
      // 422/502: el servidor si contesto con widgets; se muestran sus errores.
      if (Array.isArray(cuerpo.widgets)) { setRespuesta(cuerpo); return; }
      const tipo = cuerpo?.error?.tipo;
      setError(ERRORES[tipo] || cuerpo?.error?.mensaje || err?.message || "No se pudo completar la consulta.");
    } finally {
      clearInterval(reloj.current);
      setCargando(false);
    }
  }

  return (
    <div className="bi-container">
      <div className="bi-header">
        <div className="bi-header-content">
          <div className="bi-header-text">
            <h1 className="bi-title"><span className="bi-icon">✨</span> Análisis inteligente de datos</h1>
            <p className="bi-subtitle">Pregunta por tus datos o por cómo funciona el sistema. Solo ves lo que tu rol permite.</p>
            <div style={{ marginTop: 10 }}><EtiquetaSalud parte="modelo" /><EtiquetaSalud parte="bd" /></div>
          </div>
        </div>
      </div>

      <div className="bi-main">
        <div className="bi-query-section">
          <form onSubmit={enviar} className="bi-form">
            <div className="bi-input-wrapper">
              <input
                type="text"
                value={pregunta}
                onChange={(e) => setPregunta(e.target.value)}
                placeholder="¿Cuál es tu pregunta? (ej: Top 8 productos con más existencias)"
                className={`bi-input ${cargando ? "bi-input-disabled" : ""}`}
                disabled={cargando}
                maxLength={1000}
              />
              <button type="submit" className={`bi-submit-btn ${cargando ? "bi-submit-loading" : ""}`} disabled={cargando}>
                {cargando ? (<><span className="bi-spinner"></span>Analizando… {segundos}s</>) : (<><span className="bi-submit-icon">→</span>Analizar</>)}
              </button>
            </div>
          </form>

          {cargando && segundos > 8 && (
            <p className="bi-progress-text">El modelo está pensando; en equipos sin GPU puede tardar uno o dos minutos.</p>
          )}

          {!respuesta && !cargando && (
            <div className="bi-suggestions">
              <p className="bi-suggestions-title">Sugerencias:</p>
              <div className="bi-suggestion-chips">
                {SUGERENCIAS.map((q, i) => (
                  <button key={q} type="button" onClick={() => enviar(null, q)} className="bi-suggestion-chip"
                    style={{ animationDelay: `${i * 0.1}s` }}>{q}</button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="bi-content">
          {error && (
            <div className="bi-error-box">
              <span className="bi-error-icon">⚠️</span>
              <div><p className="bi-error-title">No se pudo completar</p><p className="bi-error-message">{error}</p></div>
            </div>
          )}

          {respuesta && (
            <div className="bi-results-section">
              <div className="bi-results-header">
                <h2 className="bi-results-title">{respuesta.dashboard_title || respuesta.widgets?.[0]?.visualization?.title || "Resultados"}</h2>
                <div className="bi-metrics">
                  <div className="bi-metric">
                    <span className="bi-metric-label">Tiempo</span>
                    <span className="bi-metric-value">{((respuesta.meta?.ms_total || 0) / 1000).toFixed(1)} s</span>
                  </div>
                  {respuesta.meta?.desde_cache && (
                    <div className="bi-metric"><span className="bi-metric-label">Origen</span><span className="bi-metric-value">caché</span></div>
                  )}
                </div>
              </div>
              {(respuesta.widgets || []).map((w, i) => <BiWidget key={i} widget={w} />)}
              {!respuesta.ok && respuesta.error && (
                <div className="bi-error-box">
                  <span className="bi-error-icon">⚠️</span>
                  <div><p className="bi-error-message">{ERRORES[respuesta.error.tipo] || respuesta.error.mensaje}</p></div>
                </div>
              )}
              <button type="button" className="button ghost" onClick={() => setRespuesta(null)}>Nueva consulta</button>
            </div>
          )}

          {historial.length > 0 && !respuesta && !cargando && (
            <div className="bi-history-section">
              <h3 className="bi-history-title">Historial reciente</h3>
              <div className="bi-history-list">
                {historial.map((h) => (
                  <button key={h.q} type="button" className="bi-history-item" onClick={() => setPregunta(h.q)}>
                    <span className="bi-history-question">{h.q}</span>
                    <span className="bi-history-time">{h.hora}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
