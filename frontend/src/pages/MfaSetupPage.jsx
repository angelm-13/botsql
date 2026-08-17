import { useState } from "react";
import QRCode from "qrcode";
import { KeyRound, QrCode, ShieldCheck } from "lucide-react";
import { setupMfa, enableMfa, disableMfa } from "../api";
import { useI18n } from "../i18n";

export default function MfaSetupPage() {
  const { t } = useI18n();
  const currentUser = JSON.parse(localStorage.getItem("user") || "null");
  const isBootstrapAdmin = Boolean(currentUser?.is_bootstrap_admin || currentUser?.is_superuser);
  const initialMfaEnabled = Boolean(currentUser?.mfa_enabled);
  const [setup, setSetup] = useState(null);
  const [qrDataUrl, setQrDataUrl] = useState("");
  const [code, setCode] = useState("");
  const [confirmed, setConfirmed] = useState(!isBootstrapAdmin && initialMfaEnabled);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function handleSetup() {
    if (!isBootstrapAdmin && confirmed) {
      setNotice(t("common.mfa_already_enabled", "Tu MFA ya está activo. No puedes regenerar el QR ni modificarlo desde esta pantalla."));
      return;
    }
    setLoading(true); setError(""); setNotice("");
    try {
      const payload = await setupMfa();
      if (!payload.otpauth_uri) throw new Error("errors.request_failed");
      const nextQr = await QRCode.toDataURL(payload.otpauth_uri, { margin: 2, width: 240 });
      setSetup(payload);
      setQrDataUrl(nextQr);
      setCode("");
      setConfirmed(false);
      setNotice(t("common.mfa_setup_ready", "QR generado. Escanéalo y escribe el código actual para activar MFA."));
    } catch (err) {
      if (err.message === "auth.mfa_already_enabled") {
        setConfirmed(true);
        setError("");
        setNotice(t("common.mfa_already_enabled", "Tu MFA ya está activo. No puedes regenerar el QR ni modificarlo desde esta pantalla."));
      } else {
        setError(t(err.message, err.message || "No se pudo generar el QR"));
      }
    } finally { setLoading(false); }
  }

  async function handleEnable(event) {
    event.preventDefault();
    if (!setup) { setError(t("common.mfa_setup_missing", "Primero genera el QR de configuración MFA.")); return; }
    setLoading(true); setError(""); setNotice("");
    try {
      await enableMfa({ code });
      setNotice(t(isBootstrapAdmin ? "common.mfa_enabled" : "common.mfa_confirmed", isBootstrapAdmin ? "MFA activado correctamente" : "MFA confirmado correctamente"));
      setCode("");
      if (!isBootstrapAdmin) {
        setConfirmed(true);
        const updatedUser = { ...(currentUser || {}), mfa_enabled: true };
        localStorage.setItem("user", JSON.stringify(updatedUser));
      }
    } catch (err) {
      setError(t(err.message, err.message || "Código MFA inválido"));
    } finally { setLoading(false); }
  }

  async function handleDisable() {
    if (!isBootstrapAdmin) return;
    setLoading(true); setError(""); setNotice("");
    try {
      await disableMfa({});
      setNotice(t("common.mfa_disabled", "MFA desactivado correctamente"));
      setCode("");
      setConfirmed(false);
    } catch (err) {
      setError(t(err.message, err.message || "No se pudo desactivar MFA"));
    } finally { setLoading(false); }
  }

  async function copySecret() {
    if (!setup?.secret) return;
    try {
      await navigator.clipboard.writeText(setup.secret);
      setNotice(t("common.mfa_secret_copied", "Clave copiada al portapapeles"));
    } catch {
      setNotice(setup.secret);
    }
  }

  return (
    <section className="entity-page mfa-setup-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">MFA · TOTP</p>
          <h2>{t("common.mfa_setup_title", "Configurar autenticación MFA")}</h2>
          <p>{t("common.mfa_setup_subtitle", "Genera un QR, escanéalo con Authenticator y confirma el código de 6 dígitos.")}</p>
        </div>
        {(isBootstrapAdmin || !confirmed) && (
          <button className="button primary" type="button" onClick={handleSetup} disabled={loading}>
            <QrCode size={16} />{setup ? t("common.mfa_regenerate_qr", "Regenerar QR") : t("common.mfa_generate_qr", "Generar QR")}
          </button>
        )}
      </div>
      {notice && <div className="alert success">{notice}</div>}
      {error && <div className="alert error">{error}</div>}
      <div className="mfa-grid">
        <article className="form-card mfa-card">
          <div className="form-header"><ShieldCheck size={20} /><strong>{t("common.mfa_setup", "Configurar MFA")}</strong></div>
          {!isBootstrapAdmin && confirmed ? (
            <div className="empty"><ShieldCheck size={34} /><h3>{t("common.mfa_active_title", "Autenticación MFA activa")}</h3><p>{t("common.mfa_active_body", "Tu cuenta ya tiene autenticación multifactor configurada. En próximos inicios de sesión se solicitará el código de tu app Authenticator. Si necesitas restablecerla, contacta a un administrador.")}</p></div>
          ) : qrDataUrl ? (
            <>
              <p>{t("common.mfa_scan_qr", "Escanea este QR con tu app Authenticator.")}</p>
              <div className="mfa-qr-box"><img src={qrDataUrl} alt="MFA QR" /></div>
              {setup?.secret && (
                <div className="mfa-secret-box">
                  <span>{t("common.mfa_manual_secret", "Clave manual")}</span>
                  <code>{setup.secret}</code>
                  <button className="button ghost" type="button" onClick={copySecret}>{t("common.mfa_copy_secret", "Copiar clave")}</button>
                </div>
              )}
            </>
          ) : (
            <div className="empty"><QrCode size={34} /><p>{t("common.mfa_setup_subtitle", "Genera un QR, escanéalo con Authenticator y confirma el código de 6 dígitos.")}</p></div>
          )}
        </article>
        <form className="form-card mfa-card" onSubmit={handleEnable}>
          <div className="form-header"><KeyRound size={20} /><strong>{t("common.verify_code", "Verificar código")}</strong></div>
          {!isBootstrapAdmin && confirmed ? (
            <div className="empty"><ShieldCheck size={34} /><p>{t("common.mfa_confirmed_body", "Tu MFA quedó confirmado. En próximos inicios de sesión se solicitará el código del Authenticator.")}</p></div>
          ) : (
            <>
              <label className="field">
                <span>{t("common.mfa_code", "Código MFA")}</span>
                <input inputMode="numeric" pattern="[0-9]{6}" maxLength="6" value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="000000" />
              </label>
              <div className="form-actions">
                <button className="button primary" type="submit" disabled={loading || code.length !== 6}>{isBootstrapAdmin ? t("common.mfa_enable", "Activar MFA") : t("common.mfa_confirm_code", "Confirmar código")}</button>
                {isBootstrapAdmin && <button className="button ghost" type="button" onClick={handleDisable} disabled={loading}>{t("common.mfa_disable", "Desactivar MFA")}</button>}
              </div>
            </>
          )}
        </form>
      </div>
    </section>
  );
}
