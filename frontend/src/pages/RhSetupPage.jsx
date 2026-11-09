import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, Circle, RefreshCw } from "lucide-react";
import { getRhSetup } from "../api";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader.jsx";

// Primeros pasos de RH (revision de usabilidad, 2026-11-05): cuantos de los 9 pasos
// de la puesta en marcha estan listos, con los datos reales, y a que pantalla ir
// para cada uno. Solo lectura; la regla de "listo" vive en services/primeros_pasos_rh.py.

export default function RhSetupPage() {
  const { t } = useI18n();
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState("");

  async function cargar() {
    setError("");
    try {
      setDatos(await getRhSetup());
    } catch (e) {
      const clave = e?.payload?.error_key || e?.message;
      setError(clave ? t(clave, t("errors.request_failed")) : t("errors.request_failed"));
    }
  }

  useEffect(() => { cargar(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const avance = datos ? Math.round((datos.done / datos.total) * 100) : 0;

  return (
    <section className="entity-page">
      <PageHeader eyebrow={t("rh_setup.eyebrow")} titulo={t("rh_setup.title")} subtitulo={t("rh_setup.subtitle")}>
        <button type="button" className="button ghost" onClick={cargar}><RefreshCw size={16} /> {t("common.refresh")}</button>
      </PageHeader>
      {error && <div className="alert error" role="alert">{error}</div>}
      {datos && (
        <div className="form-card">
          <h3 style={{ marginTop: 0 }}>{t("rh_setup.progress").replace("{n}", datos.done).replace("{total}", datos.total)}</h3>
          <div style={{ background: "#e2e8f0", borderRadius: 999, height: 10, overflow: "hidden", marginBottom: 18 }}
            role="progressbar" aria-valuemin={0} aria-valuemax={datos.total} aria-valuenow={datos.done}>
            <div style={{ width: `${avance}%`, height: "100%", background: "#1b7a60" }} />
          </div>
          <ol style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 10 }}>
            {datos.steps.map((p, i) => (
              <li key={p.key} style={{ display: "flex", gap: 12, alignItems: "flex-start", padding: "12px 14px", border: "1px solid #e2e8f0", borderRadius: 14, background: p.done ? "#f0fdf4" : "#fff" }}>
                {p.done ? <CheckCircle2 size={22} color="#1b7a60" aria-label={t("rh_setup.ready")} /> : <Circle size={22} color="#94a3b8" aria-label={t("rh_setup.pending")} />}
                <div style={{ flex: 1 }}>
                  <strong>{i + 1}. {t(`rh_setup.step_${p.key}`)}</strong>
                  <div className="muted" style={{ fontSize: 13 }}>{t(`rh_setup.how_${p.key}`)}</div>
                  {!p.done && p.count > 0 && (
                    <small className="field-error">
                      {t(`rh_setup.missing_${p.key}`, "").replace("{n}", p.count)}
                      {p.names?.length > 0 && `: ${p.names.join(", ")}${p.count > p.names.length ? "…" : ""}`}
                    </small>
                  )}
                </div>
                <Link className="button ghost" to={p.path}>{t("rh_setup.go")} <ArrowRight size={14} /></Link>
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}
