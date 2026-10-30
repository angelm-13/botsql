import { useEffect, useState } from "react";
import {
  AlertTriangle, ArrowRight, BookOpen, ClipboardList, Clock, Cpu, Database, History,
  LayoutDashboard, Package, Receipt, RotateCcw, Search, Sparkles, Zap,
} from "lucide-react";
import { biHealth, biQuery } from "../api";
import BiWidget from "../components/BiWidget";
import "../styles/bi-premium.css";

const SUGERENCIAS = [
  { q: "Top 8 productos por existencias", tipo: "Ranking", Icono: Package },
  { q: "¿Cuántas incidencias hay por tipo?", tipo: "Agrupación", Icono: ClipboardList },
  { q: "Total de facturas por cliente", tipo: "Facturación", Icono: Receipt },
  { q: "Dashboard general de operaciones", tipo: "Tablero", Icono: LayoutDashboard },
  { q: "¿Qué es un vale vencido?", tipo: "Ayuda", Icono: BookOpen },
];

const ERRORES = {
  no_autenticado: "Tu sesión expiró. Vuelve a iniciar sesión.",
  modelo_no_disponible: "El modelo de IA no está disponible en este momento.",
  directiva_invalida: "El modelo no logró interpretar la pregunta. Intenta reformularla.",
  rechazada_por_el_modelo: "El asistente no puede responder esa pregunta.",
  ninguna_consulta_ejecutable: "No se pudo obtener información con esa pregunta. Intenta reformularla con otros términos.",
  esquema_vacio: "Tu rol no tiene acceso a ninguna tabla para consultar.",
};

const CLAVE_HISTORIAL = "bi.historial";
const MAX_HISTORIAL = 6;

function leerHistorial() {
  try {
    const crudo = JSON.parse(localStorage.getItem(CLAVE_HISTORIAL) || "[]");
    return Array.isArray(crudo) ? crudo.filter((x) => x && typeof x.q === "string").slice(0, MAX_HISTORIAL) : [];
  } catch { return []; }
}

function guardarHistorial(lista) {
  try { localStorage.setItem(CLAVE_HISTORIAL, JSON.stringify(lista)); } catch { /* sin almacenamiento: no pasa nada */ }
}

const hora = (ts) => new Date(ts).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });

// Una sola consulta a /health informa de las dos cosas (modelo y base de datos) y se
// pausa con la pestaña oculta: antes eran dos sondeos idénticos cada 30 s.
function useSalud() {
  const [salud, setSalud] = useState(undefined); // undefined = consultando, null = sin respuesta
  useEffect(() => {
    let vivo = true;
    const probar = async () => {
      if (document.hidden) return;
      let h;
      try { h = await biHealth(); } catch (err) { h = err?.payload; } // con la base caída responde 503 con el cuerpo completo
      if (vivo) setSalud(h?.base_de_datos ? h : null);
    };
    probar();
    const t = setInterval(probar, 30000);
    const alVolver = () => { if (!document.hidden) probar(); };
    document.addEventListener("visibilitychange", alVolver);
    return () => { vivo = false; clearInterval(t); document.removeEventListener("visibilitychange", alVolver); };
  }, []);
  return salud;
}

function Pastilla({ Icono, etiqueta, estado, detalle }) {
  const clase = estado === undefined ? "" : estado ? "ok" : "bad";
  const texto = estado === undefined ? "consultando…" : estado ? "funcionando" : "no responde";
  return (
    <span className="bi-pill" role="status">
      <span className={`bi-dot ${clase}`} aria-hidden="true" />
      <Icono size={14} aria-hidden="true" />
      {etiqueta}: {texto}{detalle ? ` · ${detalle}` : ""}
    </span>
  );
}

// El reloj vive aquí para que cada segundo no vuelva a pintar toda la página.
function Cargando() {
  const [segundos, setSegundos] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setSegundos((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="bi-loading" role="status" aria-live="polite">
      <div className="bi-loading-head">
        <span>Analizando tu pregunta…</span>
        <span className="bi-loading-time">{segundos} s</span>
      </div>
      <div className="bi-progress" aria-hidden="true" />
      <div className="bi-skeleton" aria-hidden="true"><span /><span /><span /><span /></div>
      {segundos > 8 && (
        <p className="bi-loading-hint">El modelo está pensando; en equipos sin GPU puede tardar uno o dos minutos. Las preguntas repetidas responden al instante.</p>
      )}
    </div>
  );
}

function Origen({ meta }) {
  if (meta?.desde_cache) return <span className="bi-chip fast"><Zap size={13} /> Caché</span>;
  if (meta?.modelo === "receta") return <span className="bi-chip fast"><Zap size={13} /> Respuesta instantánea</span>;
  if (meta?.ms_modelo > 0) return <span className="bi-chip model"><Cpu size={13} /> Modelo de IA</span>;
  return null;
}

function mensajeDeError(r) {
  return ERRORES[r.error?.tipo] || r.error?.mensaje;
}

export default function BiPage() {
  const [pregunta, setPregunta] = useState("");
  const [cargando, setCargando] = useState(false);
  const [respuesta, setRespuesta] = useState(null);
  const [error, setError] = useState(null);
  const [historial, setHistorial] = useState(leerHistorial);
  const salud = useSalud();

  async function enviar(e, texto) {
    e?.preventDefault();
    const q = (texto ?? pregunta).trim();
    if (!q || cargando) return;
    setPregunta(q);
    setCargando(true);
    setError(null);
    setRespuesta(null);
    try {
      const r = await biQuery(q);
      setRespuesta(r);
      setHistorial((h) => {
        const nuevo = [{ q, ts: Date.now() }, ...h.filter((x) => x.q !== q)].slice(0, MAX_HISTORIAL);
        guardarHistorial(nuevo);
        return nuevo;
      });
    } catch (err) {
      // El backend devuelve {ok:false, error:{tipo,mensaje}} con un 4xx/5xx.
      const cuerpo = err?.payload || {};
      // 422/502: el servidor sí contestó con widgets; se muestran sus errores.
      if (Array.isArray(cuerpo.widgets)) { setRespuesta(cuerpo); return; }
      setError(ERRORES[cuerpo?.error?.tipo] || cuerpo?.error?.mensaje || err?.message || "No se pudo completar la consulta.");
    } finally {
      setCargando(false);
    }
  }

  const modelo = salud?.modelo;
  const titulo = respuesta?.dashboard_title || respuesta?.widgets?.[0]?.visualization?.title || "Resultados";

  return (
    <div className="bi-page">
      <header className="bi-hero">
        <span className="bi-eyebrow">
          <span className="bi-eyebrow-icon"><Sparkles size={13} aria-hidden="true" /></span>
          Inteligencia de negocios
        </span>
        <h1 className="bi-title">Pregunta lo que quieras <em>sobre tus datos</em></h1>
        <p className="bi-subtitle">Escribe en lenguaje natural y obtén tablas, gráficas e indicadores al momento. Solo ves lo que tu rol permite.</p>
        <div className="bi-status-row">
          <Pastilla Icono={Cpu} etiqueta="Modelo de IA" estado={salud === undefined ? undefined : !!modelo?.disponible}
            detalle={modelo?.nombre} />
          <Pastilla Icono={Database} etiqueta="PostgreSQL" estado={salud === undefined ? undefined : !!salud?.base_de_datos?.conecta}
            detalle={salud?.base_de_datos?.conecta ? salud.base_de_datos.motor : undefined} />
        </div>
      </header>

      <form className="bi-ask" onSubmit={enviar}>
        <div className="bi-ask-box">
          <Search size={20} className="bi-ask-icon" aria-hidden="true" />
          <input
            type="text"
            className="bi-input"
            value={pregunta}
            onChange={(e) => setPregunta(e.target.value)}
            placeholder="Ej. Top 8 productos con más existencias"
            aria-label="Tu pregunta"
            disabled={cargando}
            maxLength={1000}
            autoFocus
          />
          <button type="submit" className="bi-submit" disabled={cargando || !pregunta.trim()}>
            {cargando
              ? <><span className="bi-spinner" aria-hidden="true" /><span className="bi-submit-text">Analizando…</span></>
              : <><span className="bi-submit-text">Analizar</span><ArrowRight size={18} aria-hidden="true" /></>}
          </button>
        </div>
      </form>

      {cargando && <Cargando />}

      {error && !cargando && (
        <div className="bi-error-box" role="alert" style={{ marginTop: 22 }}>
          <AlertTriangle size={20} className="bi-error-icon" aria-hidden="true" />
          <div><p className="bi-error-title">No se pudo completar</p><p className="bi-error-message">{error}</p></div>
        </div>
      )}

      {respuesta && !cargando && (
        <section className="bi-results" aria-label="Resultados">
          <div className="bi-results-head">
            <div>
              <h2 className="bi-results-title">{titulo}</h2>
              <p className="bi-results-question">“{respuesta.pregunta || pregunta}”</p>
            </div>
            <div className="bi-chips">
              <Origen meta={respuesta.meta} />
              <span className="bi-chip"><Clock size={13} aria-hidden="true" /> {((respuesta.meta?.ms_total || 0) / 1000).toFixed(1)} s</span>
            </div>
          </div>
          {(respuesta.widgets || []).map((w, i) => <BiWidget key={i} widget={w} />)}
          {!respuesta.ok && respuesta.error && !(respuesta.widgets || []).length && (
            <div className="bi-error-box" role="alert">
              <AlertTriangle size={20} className="bi-error-icon" aria-hidden="true" />
              <div><p className="bi-error-message">{mensajeDeError(respuesta)}</p></div>
            </div>
          )}
          <div className="bi-actions">
            <button type="button" className="bi-btn" onClick={() => { setRespuesta(null); setPregunta(""); }}>
              <RotateCcw size={16} aria-hidden="true" /> Nueva consulta
            </button>
          </div>
        </section>
      )}

      {!respuesta && !cargando && (
        <>
          <div className="bi-section-label"><Sparkles size={14} aria-hidden="true" /> Prueba con una de estas</div>
          <div className="bi-suggestions">
            {SUGERENCIAS.map(({ q, tipo, Icono }, i) => (
              <button key={q} type="button" className="bi-suggestion" style={{ animationDelay: `${i * 45}ms` }}
                onClick={() => enviar(null, q)}>
                <span className="bi-suggestion-icon"><Icono size={19} aria-hidden="true" /></span>
                <span className="bi-suggestion-kind">{tipo}</span>
                <span className="bi-suggestion-text">{q}</span>
              </button>
            ))}
          </div>

          {historial.length > 0 && (
            <>
              <div className="bi-section-label"><History size={14} aria-hidden="true" /> Consultas recientes</div>
              <div className="bi-history">
                {historial.map((h) => (
                  <button key={h.q} type="button" className="bi-history-item" onClick={() => enviar(null, h.q)}>
                    <Clock size={15} aria-hidden="true" />
                    <span className="bi-history-q">{h.q}</span>
                    <span className="bi-history-time">{hora(h.ts)}</span>
                  </button>
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
