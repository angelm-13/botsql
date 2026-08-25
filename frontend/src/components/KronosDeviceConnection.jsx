/* eslint-disable react/prop-types */
import React, { useState } from "react";
import { Save, ShieldCheck } from "lucide-react";
import { loadKronosConnection, saveKronosConnection } from "../utils/kronosConnection";
import { useI18n } from "../i18n";

export default function KronosDeviceConnection({ onSaved }) {
  const { t } = useI18n();
  const [connection, setConnection] = useState(loadKronosConnection);
  const [saved, setSaved] = useState(false);

  function updateConnection(event) {
    const { name, type, checked, value } = event.target;
    setSaved(false);
    setConnection((current) => ({ ...current, [name]: type === "checkbox" ? checked : value }));
  }

  function submit(event) {
    event.preventDefault();
    saveKronosConnection(connection);
    setSaved(true);
    onSaved?.(connection);
  }

  return <form className="form-card kronos-device-form" onSubmit={submit}>
    <div className="kronos-device-intro">
      <ShieldCheck size={22} />
      <div><h3>{t('kronos.device.heading')}</h3><p>{t('kronos.device.note')}</p></div>
    </div>
    <div className="kronos-form-grid">
      <label className="field kronos-url">{t('kronos.device.url_label')}<input required type="url" name="deviceUrl" value={connection.deviceUrl} onChange={updateConnection} placeholder={t('kronos.device.url_placeholder')} /></label>
      <label className="field">{t('kronos.device.username')}<input required name="username" autoComplete="username" value={connection.username} onChange={updateConnection} /></label>
      <label className="field">{t('kronos.device.password')}<input required type="password" name="password" autoComplete="current-password" value={connection.password} onChange={updateConnection} /></label>
      <label className="field">{t('kronos.device.session_tag')} <small>{t('kronos.device.optional')}</small><input name="sessionTag" value={connection.sessionTag} onChange={updateConnection} /></label>
      <label className="field">{t('kronos.device.cookie')} <small>{t('kronos.device.optional')}</small><input name="cookie" value={connection.cookie} onChange={updateConnection} /></label>
      <label className="kronos-check"><input type="checkbox" name="allowSelfSigned" checked={connection.allowSelfSigned} onChange={updateConnection} /> {t('kronos.device.allow_self_signed')}</label>
    </div>
    <div className="kronos-device-actions">
      {saved && <span role="status">{t('kronos.device.saved_status')}</span>}
      <button type="submit" className="button"><Save size={16} /> {t('kronos.device.save_button')}</button>
    </div>
  </form>;
}