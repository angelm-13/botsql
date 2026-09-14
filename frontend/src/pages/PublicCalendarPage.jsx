import { useEffect, useState } from "react";
import { ArrowLeft, CalendarDays, Check, Clock3, Globe2, Video } from "lucide-react";
import { useParams } from "react-router-dom";
import { createPublicAppointment, getPublicCalendar, getPublicCalendarSlots } from "../api";
import { useI18n } from "../i18n";
import "../styles/appointments.css";

function localDate(date) {
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
}

function formatSlot(value, lang) {
  return new Intl.DateTimeFormat(lang, { hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

export default function PublicCalendarPage() {
  const { code } = useParams();
  const { lang, t } = useI18n();
  const [calendar, setCalendar] = useState(null);
  const [selectedType, setSelectedType] = useState(null);
  const [selectedDate, setSelectedDate] = useState(localDate(new Date()));
  const [slots, setSlots] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState("");
  const [form, setForm] = useState({ guest_name: "", guest_email: "", guest_notes: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [confirmation, setConfirmation] = useState(null);

  useEffect(() => {
    getPublicCalendar(code).then((payload) => { setCalendar(payload); setSelectedType(payload.appointment_types?.[0] || null); }).catch(() => setError("appointments.public_error_unavailable")).finally(() => setLoading(false));
  }, [code]);

  useEffect(() => {
    if (!selectedType || !selectedDate) return;
    setLoading(true); setSelectedSlot("");
    getPublicCalendarSlots(code, { appointment_type_id: selectedType.id_appointment_type, date_from: selectedDate, date_to: selectedDate })
      .then((payload) => setSlots(payload.slots || []))
      .catch(() => { setSlots([]); setError("appointments.public_error_slots"); })
      .finally(() => setLoading(false));
  }, [code, selectedDate, selectedType]);

  async function submitBooking(event) {
    event.preventDefault();
    setLoading(true); setError("");
    try {
      const payload = await createPublicAppointment(code, { ...form, id_appointment_type: selectedType.id_appointment_type, starts_at: selectedSlot, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || calendar.timezone });
      setConfirmation(payload);
    } catch (requestError) {
      setError(requestError.status === 409 ? "appointments.public_error_slot_taken" : "appointments.public_error_confirm");
    } finally { setLoading(false); }
  }

  if (loading && !calendar) return <main className="public-calendar-page"><div className="public-calendar-loading">{t("appointments.public_checking_availability", "Consultando disponibilidad…")}</div></main>;
  if (error && !calendar) return <main className="public-calendar-page"><div className="public-calendar-message"><CalendarDays size={32} /><h1>{t("appointments.public_unavailable_title", "Calendario no disponible")}</h1><p>{t(error, error)}</p></div></main>;
  if (confirmation) return <main className="public-calendar-page"><section className="booking-confirmation"><span><Check size={26} /></span><p className="eyebrow">{t("appointments.public_confirmed", "CITA CONFIRMADA")}</p><h1>{t("appointments.public_see_you", "Nos vemos pronto")}</h1><p>{t("appointments.public_reserved_prefix", "Tu cita con")} {calendar.display_name} {t("appointments.public_reserved_suffix", "quedó reservada.")}</p><dl><div><dt>{t("appointments.date", "Fecha")}</dt><dd>{new Intl.DateTimeFormat(lang, { dateStyle: "full", timeStyle: "short" }).format(new Date(confirmation.starts_at))}</dd></div><div><dt>{t("appointments.timezone", "Zona horaria")}</dt><dd>{confirmation.guest_timezone}</dd></div></dl></section></main>;

  return <main className="public-calendar-page">
    <header className="public-calendar-brand"><CalendarDays size={24} /><strong>TYAKXA</strong></header>
    <div className="public-booking-layout">
      <aside className="public-calendar-summary"><p className="eyebrow">{t("appointments.public_agenda", "AGENDA")}</p><h1>{calendar.display_name}</h1>{selectedType && <><h2>{selectedType.name}</h2><p>{selectedType.description || t("appointments.public_select_help", "Selecciona el horario que mejor te funcione.")}</p><ul><li><Clock3 size={17} /> {selectedType.duration_minutes} {t("appointments.minutes", "minutos")}</li><li><Globe2 size={17} /> {calendar.timezone}</li>{selectedType.meeting_provider !== "none" && <li><Video size={17} /> {selectedType.meeting_provider}</li>}</ul></>}</aside>
      <section className="public-booking-workspace">
        <div className="public-booking-types" role="tablist" aria-label={t("appointments.appointment_types", "Tipos de cita")}>{calendar.appointment_types.map((item) => <button type="button" role="tab" aria-selected={selectedType?.id_appointment_type === item.id_appointment_type} className={selectedType?.id_appointment_type === item.id_appointment_type ? "active" : ""} onClick={() => setSelectedType(item)} key={item.id_appointment_type}>{item.name}<span>{item.duration_minutes} min</span></button>)}</div>
        <label className="public-date-picker">{t("appointments.date", "Fecha")}<input type="date" min={localDate(new Date())} value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)} /></label>
        <div className="public-slots" aria-live="polite">{loading ? <p>{t("appointments.public_checking_slots", "Consultando horarios…")}</p> : slots.length ? slots.map((slot) => <button type="button" className={selectedSlot === slot ? "selected" : ""} onClick={() => setSelectedSlot(slot)} key={slot}>{formatSlot(slot, lang)}{selectedSlot === slot && <Check size={15} />}</button>) : <p>{t("appointments.public_no_slots", "No hay horarios disponibles para este día.")}</p>}</div>
        {selectedSlot && <form className="public-booking-form" onSubmit={submitBooking}><button type="button" className="public-back-button" onClick={() => setSelectedSlot("")}><ArrowLeft size={16} /> {t("appointments.public_choose_another", "Elegir otro horario")}</button><div className="appointments-form-grid"><label className="field">{t("appointments.name", "Nombre")}<input required maxLength="150" autoComplete="name" value={form.guest_name} onChange={(event) => setForm((current) => ({ ...current, guest_name: event.target.value }))} /></label><label className="field">{t("appointments.email", "Correo")}<input required type="email" maxLength="254" autoComplete="email" value={form.guest_email} onChange={(event) => setForm((current) => ({ ...current, guest_email: event.target.value }))} /></label></div><label className="field">{t("appointments.optional_notes", "Notas opcionales")}<textarea rows="3" maxLength="2000" value={form.guest_notes} onChange={(event) => setForm((current) => ({ ...current, guest_notes: event.target.value }))} /></label>{error && <div className="alert error" role="alert">{t(error, error)}</div>}<button className="public-confirm-button" disabled={loading}>{t("appointments.public_confirm", "Confirmar cita")}</button></form>}
      </section>
    </div>
  </main>;
}