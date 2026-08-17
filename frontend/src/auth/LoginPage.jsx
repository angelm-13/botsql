import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { KeyRound, Lock, ShieldCheck, UserRound } from "lucide-react";
import { login, verifyMfaLogin, clearMyPermissionsCache } from "../api";
import { useI18n } from "../i18n";

const initialCredentials = { username: "", password: "" };

function normalizeUser(payload) {
  return payload.user || payload.current_user || {
    id_user: payload.id_user,
    username: payload.username,
    user_type: payload.user_type,
    id_permission: payload.id_permission,
    is_bootstrap_admin: payload.is_bootstrap_admin,
    is_superuser: payload.is_superuser,
    mfa_enabled: payload.mfa_enabled
  };
}

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { t, lang, setLanguage } = useI18n();
  const [step, setStep] = useState("credentials");
  const [credentials, setCredentials] = useState(initialCredentials);
  const [mfaCode, setMfaCode] = useState("");
  const [tempToken, setTempToken] = useState(localStorage.getItem("mfa_temp_token") || "");
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const redirectTo = location.state?.from?.pathname || "/";

  useEffect(() => {
    if (localStorage.getItem("token")) navigate(redirectTo, { replace: true });
    if (tempToken) setStep("mfa");
  }, [navigate, redirectTo, tempToken]);

  function persistSession(payload) {
    const token = payload.token || payload.access_token;
    if (!token) throw new Error("errors.request_failed");
    clearMyPermissionsCache();
    localStorage.setItem("token", token);
    localStorage.setItem("user", JSON.stringify(normalizeUser(payload)));
    localStorage.removeItem("mfa_temp_token");
    navigate(redirectTo, { replace: true });
  }

  async function handleLogin(event) {
    event.preventDefault();
    setLoading(true); setError(""); setNotice("");
    try {
      const payload = await login(credentials);
      if (payload.mfa_required) {
        const nextTempToken = payload.temp_token || payload.mfa_token || payload.token;
        if (!nextTempToken) throw new Error("errors.request_failed");
        localStorage.setItem("mfa_temp_token", nextTempToken);
        setTempToken(nextTempToken);
        setStep("mfa");
        setNotice(t("common.mfa_required", "Se requiere verificación MFA"));
        return;
      }
      persistSession(payload);
    } catch (err) {
      setError(t(err.message, err.message || "Credenciales inválidas"));
    } finally { setLoading(false); }
  }

  async function handleMfaSubmit(event) {
    event.preventDefault();
    setLoading(true); setError("");
    try {
      const payload = await verifyMfaLogin({ temp_token: tempToken, code: mfaCode });
      persistSession(payload);
    } catch (err) {
      setError(t(err.message, err.message || "Código MFA inválido"));
    } finally { setLoading(false); }
  }

  function backToLogin(event) {
    event?.preventDefault?.();
    clearMyPermissionsCache();
    localStorage.removeItem("mfa_temp_token");
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setTempToken("");
    setMfaCode("");
    setStep("credentials");
    setNotice("");
    setError("");
    navigate("/login", { replace: true, state: null });
  }

  return (
    <main className="auth-page">
      <section className="auth-visual">
        <div className="brand auth-brand"><img src="/tyakxa-logo.png" alt={t("common.app_title", "TYAKXA ERP CRM SCM")} className="brand-logo" /><span>{t("common.app_title", "TYAKXA ERP CRM SCM")}</span></div>
        <p className="eyebrow">ERP · CRM · SCM</p>
        <h1>{step === "mfa" ? t("common.mfa_title", "Verificación MFA") : t("common.login_title", "Acceso seguro")}</h1>
        <p>{step === "mfa" ? t("common.mfa_subtitle", "Ingresa el código de 6 dígitos de tu app autenticadora") : t("common.login_subtitle", "Ingresa a tu ERP CRM SCM empresarial")}</p>
        <div className="auth-security-grid">
          <article><ShieldCheck /><strong>MFA</strong><span>2FA/TOTP</span></article>
          <article><Lock /><strong>RBAC</strong><span>CRUD</span></article>
          <article><KeyRound /><strong>JWT</strong><span>Secure API</span></article>
        </div>
      </section>
      <section className="auth-card">
        <div className="auth-card-header"><ShieldCheck size={28} /><div><p className="eyebrow">{t("common.secure_session", "Sesión protegida")}</p><h2>{step === "mfa" ? t("common.mfa_title", "Verificación MFA") : t("common.sign_in", "Iniciar sesión")}</h2></div></div>
        <label className="language-picker auth-language">{t("common.language", "Idioma")}<select value={lang} onChange={(event) => setLanguage(event.target.value)}><option value="es">ES</option><option value="en">EN</option><option value="pt">PT</option><option value="de">DE</option><option value="ja">日本語</option></select></label>
        {notice && <div className="alert success">{notice}</div>}
        {error && <div className="alert error">{error}</div>}
        {step === "credentials" ? (
          <form className="auth-form" onSubmit={handleLogin}>
            <label className="field"><span>{t("common.username", "Usuario")}</span><div className="input-icon"><UserRound size={18} /><input autoFocus name="username" value={credentials.username} onChange={(event) => setCredentials((prev) => ({ ...prev, username: event.target.value }))} autoComplete="username" required /></div></label>
            <label className="field"><span>{t("common.password", "Contraseña")}</span><div className="input-icon"><Lock size={18} /><input name="password" type="password" value={credentials.password} onChange={(event) => setCredentials((prev) => ({ ...prev, password: event.target.value }))} autoComplete="current-password" required /></div></label>
            <button className="button primary auth-submit" type="submit" disabled={loading}>{loading ? t("common.loading", "Cargando...") : t("common.sign_in", "Iniciar sesión")}</button>
          </form>
        ) : (
          <form className="auth-form" onSubmit={handleMfaSubmit}>
            <label className="field"><span>{t("common.mfa_code", "Código MFA")}</span><div className="input-icon"><KeyRound size={18} /><input autoFocus inputMode="numeric" pattern="[0-9]{6}" maxLength="6" value={mfaCode} onChange={(event) => setMfaCode(event.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="000000" required /></div></label>
            <button className="button primary auth-submit" type="submit" disabled={loading || mfaCode.length !== 6}>{loading ? t("common.loading", "Cargando...") : t("common.verify_code", "Verificar código")}</button>
            <button className="button ghost auth-submit" type="button" onClick={backToLogin}>{t("common.back_to_login", "Volver al login")}</button>
          </form>
        )}
      </section>
    </main>
  );
}
