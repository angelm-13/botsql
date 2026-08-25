import React, { useEffect, useState } from "react";
import { CalendarDays, Clock3, Copy, ExternalLink, Plus, RefreshCw } from "lucide-react";
import {
  createAppointmentProfile,
  createAppointmentType,
  createAvailabilityRule,
  getAppointmentProfiles,
  getAppointments,
} from "../api";
import { useI18n } from "../i18n";
import "../styles/appointments.css";

function formatAppointment(value, lang) {
  return new Intl.DateTimeFormat(lang, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function AppointmentsPage() {
  const { lang, t } = useI18n();
  const [profiles, setProfiles] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [profileForm, setProfileForm] = useState({ display_name: "", calendar_code: "", timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC" });
  const [typeForm, setTypeForm] = useState({ name: "", duration_minutes: 30, buffer_before_minutes: 0, buffer_after_minutes: 0, minimum_notice_minutes: 120, booking_horizon_days: 60, meeting_provider: "none" });
  const [ruleForm, setRuleForm] = useState({ weekday: 0, start_time: "09:00", end_time: "17:00" });
  const profile = profiles[0];

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [profilePayload, appointmentPayload] = await Promise.all([getAppointmentProfiles(), getAppointments()]);
      setProfiles(profilePayload.items || []);
      setAppointments(appointmentPayload.items || []);
    } catch (requestError) {
      setError(requestError.message === "errors.permission_denied" ? "appointments.error_permission" : "appointments.error_load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadData(); }, []);

  async function submitProfile(event) {
    event.preventDefault();
    setSaving(true); setError("");
    try {
      await createAppointmentProfile(profileForm);
      setNotice("appointments.notice_profile_created");
      await loadData();
    } catch (_) { setError("appointments.error_create_profile"); }
    finally { setSaving(false); }
  }

  async function submitType(event) {
    event.preventDefault();
    setSaving(true); setError("");
    try {
      await createAppointmentType(profile.id_calendar_profile, typeForm);
      setTypeForm((current) => ({ ...current, name: "" }));
      setNotice("appointments.notice_type_created");
      await loadData();
    } catch (_) { setError("appointments.error_save_type"); }
    finally { setSaving(false); }
  }

  async function submitRule(event) {
    event.preventDefault();
    setSaving(true); setError("");
    try {
      await createAvailabilityRule(profile.id_calendar_profile, ruleForm);
      setNotice("appointments.notice_rule_created");
      await loadData();
    } catch (_) { setError("appointments.error_save_rule"); }
    finally { setSaving(false); }
  }

  async function copyPublicLink() {
    await navigator.clipboard.writeText(`${window.location.origin}/calendar/${profile.calendar_code}`);
    setNotice("appointments.notice_link_copied");
  }

  const weekdays = [
    t("appointments.weekday_monday", "Lunes"),
    t("appointments.weekday_tuesday", "Martes"),
    t("appointments.weekday_wednesday", "Miércoles"),
    t("appointments.weekday_thursday", "Jueves"),
    t("appointments.weekday_friday", "Viernes"),
    t("appointments.weekday_saturday", "Sábado"),
    t("appointments.weekday_sunday", "Domingo"),
  ];

  if (loading) return <section className="appointments-page"><div className="appointments-loading"><RefreshCw size={20} /> {t("appointments.loading", "Cargando agenda")}</div></section>;

  return (
    <section className="entity-page appointments-page">
      <div className="page-heading appointments-heading">
        <div><p className="eyebrow">{t("appointments.operations", "OPERACIONES")}</p><h2>{t("appointments.title", "Agenda")}</h2><p>{t("appointments.subtitle", "Configura disponibilidad y revisa las próximas citas.")}</p></div>
        {profile && <div className="appointments-heading-actions"><button type="button" className="button secondary" onClick={copyPublicLink}><Copy size={16} /> {t("appointments.copy_link", "Copiar enlace")}</button><a className="button" href={`/calendar/${profile.calendar_code}`} target="_blank" rel="noreferrer"><ExternalLink size={16} /> {t("appointments.open_page", "Abrir página")}</a></div>}
      </div>
      {error && <div className="alert error" role="alert">{t(error, error)}</div>}
      {notice && <div className="alert success" role="status">{t(notice, notice)}</div>}

      {!profile ? <form className="appointments-onboarding" onSubmit={submitProfile}>
        <div><CalendarDays size={28} /><p className="eyebrow">{t("appointments.initial_setup", "CONFIGURACIÓN INICIAL")}</p><h3>{t("appointments.create_link_title", "Crea tu enlace de citas")}</h3><p>{t("appointments.timezone_help", "La zona horaria define cómo se interpretan tus horarios de trabajo.")}</p></div>
        <div className="appointments-form-grid">
          <label className="field">{t("appointments.public_name", "Nombre público")}<input required maxLength="150" value={profileForm.display_name} onChange={(event) => setProfileForm((current) => ({ ...current, display_name: event.target.value }))} placeholder={t("appointments.public_name_placeholder", "Equipo comercial")} /></label>
          <label className="field">{t("appointments.link_code", "Código del enlace")}<input required maxLength="80" pattern="[a-zA-Z0-9-]+" value={profileForm.calendar_code} onChange={(event) => setProfileForm((current) => ({ ...current, calendar_code: event.target.value.toLowerCase() }))} placeholder={t("appointments.link_code_placeholder", "equipo-comercial")} /></label>
          <label className="field">{t("appointments.timezone", "Zona horaria")}<input required value={profileForm.timezone} onChange={(event) => setProfileForm((current) => ({ ...current, timezone: event.target.value }))} /></label>
        </div>
        <button className="button" disabled={saving}><Plus size={16} /> {t("appointments.create_calendar", "Crear agenda")}</button>
      </form> : <>
        <div className="appointments-summary">
          <div><span>{t("appointments.public_link", "Enlace público")}</span><strong>/calendar/{profile.calendar_code}</strong></div>
          <div><span>{t("appointments.timezone", "Zona horaria")}</span><strong>{profile.timezone}</strong></div>
          <div><span>{t("appointments.appointment_types", "Tipos de cita")}</span><strong>{profile.appointment_types.length}</strong></div>
          <div><span>{t("appointments.upcoming", "Próximas citas")}</span><strong>{appointments.filter((item) => item.status === "confirmed" && new Date(item.starts_at) > new Date()).length}</strong></div>
        </div>

        <div className="appointments-config-grid">
          <form className="appointments-section" onSubmit={submitType}>
            <div className="appointments-section-heading"><div><p className="eyebrow">{t("appointments.services", "SERVICIOS")}</p><h3>{t("appointments.appointment_types", "Tipos de cita")}</h3></div><Clock3 size={20} /></div>
            <label className="field">{t("appointments.name", "Nombre")}<input required maxLength="120" value={typeForm.name} onChange={(event) => setTypeForm((current) => ({ ...current, name: event.target.value }))} placeholder={t("appointments.type_name_placeholder", "Consulta inicial")} /></label>
            <div className="appointments-form-grid compact"><label className="field">{t("appointments.duration", "Duración")}<input required type="number" min="5" max="480" step="5" value={typeForm.duration_minutes} onChange={(event) => setTypeForm((current) => ({ ...current, duration_minutes: Number(event.target.value) }))} /></label><label className="field">{t("appointments.minimum_notice", "Anticipación (min)")}<input required type="number" min="0" value={typeForm.minimum_notice_minutes} onChange={(event) => setTypeForm((current) => ({ ...current, minimum_notice_minutes: Number(event.target.value) }))} /></label></div>
            <label className="field">{t("appointments.video_call", "Videollamada")}<select value={typeForm.meeting_provider} onChange={(event) => setTypeForm((current) => ({ ...current, meeting_provider: event.target.value }))}><option value="none">{t("appointments.no_video_call", "Sin videollamada")}</option><option value="google" disabled>Google Meet</option><option value="microsoft" disabled>Microsoft Teams</option><option value="zoom" disabled>Zoom</option></select></label>
            <button className="button secondary" disabled={saving}><Plus size={16} /> {t("appointments.add_type", "Agregar tipo")}</button>
            <div className="appointments-items">{profile.appointment_types.map((item) => <div key={item.id_appointment_type}><strong>{item.name}</strong><span>{item.duration_minutes} min · {item.meeting_provider === "none" ? t("appointments.no_video_call", "Sin videollamada") : item.meeting_provider}</span></div>)}</div>
          </form>

          <form className="appointments-section" onSubmit={submitRule}>
            <div className="appointments-section-heading"><div><p className="eyebrow">{t("appointments.availability", "DISPONIBILIDAD")}</p><h3>{t("appointments.weekly_schedule", "Horario semanal")}</h3></div><CalendarDays size={20} /></div>
            <label className="field">{t("appointments.day", "Día")}<select value={ruleForm.weekday} onChange={(event) => setRuleForm((current) => ({ ...current, weekday: Number(event.target.value) }))}>{weekdays.map((day, index) => <option value={index} key={day}>{day}</option>)}</select></label>
            <div className="appointments-form-grid compact"><label className="field">{t("appointments.from", "Desde")}<input required type="time" value={ruleForm.start_time} onChange={(event) => setRuleForm((current) => ({ ...current, start_time: event.target.value }))} /></label><label className="field">{t("appointments.to", "Hasta")}<input required type="time" value={ruleForm.end_time} onChange={(event) => setRuleForm((current) => ({ ...current, end_time: event.target.value }))} /></label></div>
            <button className="button secondary" disabled={saving}><Plus size={16} /> {t("appointments.add_schedule", "Agregar horario")}</button>
            <div className="appointments-items">{profile.availability_rules.map((item) => <div key={item.id_availability_rule}><strong>{weekdays[item.weekday]}</strong><span>{String(item.start_time).slice(0, 5)}–{String(item.end_time).slice(0, 5)}</span></div>)}</div>
          </form>
        </div>

        <section className="table-card appointments-table"><div className="appointments-table-heading"><div><p className="eyebrow">{t("appointments.bookings", "RESERVAS")}</p><h3>{t("appointments.appointments", "Citas")}</h3></div><button type="button" className="icon-button" title={t("appointments.refresh", "Actualizar citas")} aria-label={t("appointments.refresh", "Actualizar citas")} onClick={loadData}><RefreshCw size={17} /></button></div><div className="appointments-table-scroll"><table><thead><tr><th>{t("appointments.date", "Fecha")}</th><th>{t("appointments.guest", "Invitado")}</th><th>{t("appointments.status", "Estado")}</th><th>{t("appointments.provider", "Proveedor")}</th></tr></thead><tbody>{appointments.length ? appointments.map((item) => <tr key={item.id_appointment}><td><strong>{formatAppointment(item.starts_at, lang)}</strong><small>{item.guest_timezone}</small></td><td><strong>{item.guest_name}</strong><small>{item.guest_email}</small></td><td><span className={`appointment-status ${item.status}`}>{t(`appointments.status_${item.status}`, item.status)}</span></td><td>{item.meeting_provider === "none" ? "—" : item.meeting_provider}</td></tr>) : <tr><td colSpan="4" className="appointments-empty">{t("appointments.empty", "Aún no hay citas reservadas.")}</td></tr>}</tbody></table></div></section>
      </>}
    </section>
  );
}