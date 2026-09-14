import { useEffect, useState } from "react";
import { PlugZap, Save } from "lucide-react";
import { getStampingConfig, saveStampingConfig, testStampingConfig } from "../api";
import { useI18n } from "../i18n";

function readableError(requestError) {
  const response = requestError?.payload || {};
  return response.error || response.error_key || requestError.message || "invoice_creation.error_request";
}

export default function FacturamaConfigPage() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState(null);
  const [config, setConfig] = useState({ provider: "fake", facturama_username: "", facturama_password: "", facturama_base_url: "", name_id: "1", has_password: false });

  useEffect(() => {
    let mounted = true;
    getStampingConfig()
      .then((payload) => { if (mounted && payload) setConfig((current) => ({ ...current, ...payload, facturama_password: "" })); })
      .catch((requestError) => { if (mounted) setError(readableError(requestError)); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, []);

  async function handleTest() {
    setTesting(true); setResult(null);
    try { setResult(await testStampingConfig(config)); }
    catch (requestError) { setResult({ ok: false, message: readableError(requestError) }); }
    finally { setTesting(false); }
  }

  async function handleSave() {
    setSaving(true); setError("");
    try {
      const saved = await saveStampingConfig(config);
      setConfig((current) => ({ ...current, ...saved, facturama_password: "" }));
      setResult({ ok: true, message: t("invoice_creation.config_saved") });
    } catch (requestError) { setError(readableError(requestError)); }
    finally { setSaving(false); }
  }

  if (loading) return <div className="empty">{t("invoice_creation.loading_form", "Cargando formulario fiscal...")}</div>;

  return (
    <div className="invoice-creation-workspace">
      <div className="invoice-creation-heading">
        <div>
          <p className="eyebrow">CFDI 4.0</p>
          <h3>{t("menu.facturama_config", "Configurar Facturama")}</h3>
        </div>
      </div>

      <section className="invoice-pac-panel">
        <div className="form-header"><PlugZap size={18} /><strong>{t("invoice_creation.stamping_connection", "Conexión de timbrado")}</strong></div>
        <div className="form-grid">
          <label className="field"><span>{t("invoice_creation.provider", "Proveedor")}</span>
            <select value={config.provider} onChange={(event) => setConfig((current) => ({ ...current, provider: event.target.value }))}>
              <option value="fake">{t("invoice_creation.provider_fake", "Simulado, sin validez fiscal")}</option>
              <option value="facturama_sandbox">{t("invoice_creation.provider_sandbox", "Facturama · Pruebas")}</option>
              <option value="facturama">{t("invoice_creation.provider_production", "Facturama · Producción")}</option>
            </select>
          </label>
          {config.provider !== "fake" && <>
            <label className="field"><span>{t("invoice_creation.facturama_user", "Usuario Facturama")}</span>
              <input value={config.facturama_username} onChange={(event) => setConfig((current) => ({ ...current, facturama_username: event.target.value }))} />
            </label>
            <label className="field"><span>{t("invoice_creation.password", "Contraseña")} {config.has_password && <small>{t("invoice_creation.saved", "guardada")}</small>}</span>
              <input type="password" autoComplete="new-password" placeholder={config.has_password ? t("invoice_creation.keep_saved_password", "Conservar contraseña guardada") : ""} value={config.facturama_password} onChange={(event) => setConfig((current) => ({ ...current, facturama_password: event.target.value }))} />
            </label>
            <label className="field"><span>{t("invoice_creation.name_id", "Name ID / perfil")}</span>
              <input value={config.name_id} onChange={(event) => setConfig((current) => ({ ...current, name_id: event.target.value }))} />
            </label>
          </>}
        </div>
        {config.provider !== "fake" && <p>{t("invoice_creation.expedition_place_hint", "El lugar de expedición y el CSD se toman del domicilio de la empresa marcada como \"Empresa principal\" en Contactos.")}</p>}
        {result && <div className={`alert ${result.ok ? "success" : "error"}`}>{result.message}</div>}
        {error && <div className="alert error">{t(error, error)}</div>}
        <div className="form-actions">
          <button className="button" type="button" disabled={testing} onClick={handleTest}><PlugZap size={16} />{testing ? t("invoice_creation.testing") : t("invoice_creation.test_connection")}</button>
          <button className="button primary" type="button" disabled={saving} onClick={handleSave}><Save size={16} />{saving ? t("invoice_creation.saving") : t("invoice_creation.save_config")}</button>
        </div>
      </section>
    </div>
  );
}
