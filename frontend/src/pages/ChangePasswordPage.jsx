import { useState } from "react";
import { KeyRound } from "lucide-react";
import { changeMyPassword } from "../api";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader.jsx";

export default function ChangePasswordPage() {
  const { t } = useI18n();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setError(""); setNotice("");
    if (newPassword !== confirmPassword) {
      setError(t("change_password.mismatch", "La confirmación no coincide con la contraseña nueva."));
      return;
    }
    setLoading(true);
    try {
      await changeMyPassword({ current_password: currentPassword, new_password: newPassword });
      setNotice(t("change_password.success", "Contraseña actualizada correctamente."));
      setCurrentPassword(""); setNewPassword(""); setConfirmPassword("");
    } catch (err) {
      setError(t(err.message, err.message || "No se pudo cambiar la contraseña"));
    } finally { setLoading(false); }
  }

  return (
    <section className="entity-page change-password-page">
      <PageHeader
        eyebrow={t("change_password.eyebrow", "MI CUENTA")}
        titulo={t("change_password.title", "Cambiar contraseña")}
        subtitulo={t("change_password.subtitle", "Disponible para cualquier usuario, sin importar su rol: solo cambia la tuya.")}
      />
      {notice && <div className="alert success">{notice}</div>}
      {error && <div className="alert error">{error}</div>}
      <form className="form-card change-password-card" onSubmit={handleSubmit}>
        <div className="form-header"><KeyRound size={20} /><strong>{t("change_password.title", "Cambiar contraseña")}</strong></div>
        <label className="field">
          <span>{t("change_password.current", "Contraseña actual")}</span>
          <input required type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} />
        </label>
        <label className="field">
          <span>{t("change_password.new", "Contraseña nueva")}</span>
          <input required type="password" autoComplete="new-password" minLength={8} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
        </label>
        <label className="field">
          <span>{t("change_password.confirm", "Confirmar contraseña nueva")}</span>
          <input required type="password" autoComplete="new-password" minLength={8} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
        </label>
        <p className="muted">{t("change_password.hint", "Mínimo 8 caracteres, con al menos una letra y un número.")}</p>
        <div className="form-actions">
          <button className="button primary" type="submit" disabled={loading}>{t("change_password.submit", "Guardar contraseña")}</button>
        </div>
      </form>
    </section>
  );
}
