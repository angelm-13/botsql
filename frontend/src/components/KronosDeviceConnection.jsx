/* eslint-disable react/prop-types */
import React, { useState } from "react";
import { Save, ShieldCheck } from "lucide-react";
import { loadKronosConnection, saveKronosConnection } from "../utils/kronosConnection";

export default function KronosDeviceConnection({ onSaved }) {
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
      <div><h3>Credenciales del dispositivo</h3><p>Se conservan únicamente durante esta sesión del navegador.</p></div>
    </div>
    <div className="kronos-form-grid">
      <label className="field kronos-url">URL del dispositivo<input required type="url" name="deviceUrl" value={connection.deviceUrl} onChange={updateConnection} placeholder="https://192.168.0.203/ISAPI/AccessControl/AcsEvent?format=json" /></label>
      <label className="field">Usuario<input required name="username" autoComplete="username" value={connection.username} onChange={updateConnection} /></label>
      <label className="field">Contraseña<input required type="password" name="password" autoComplete="current-password" value={connection.password} onChange={updateConnection} /></label>
      <label className="field">SessionTag <small>Opcional</small><input name="sessionTag" value={connection.sessionTag} onChange={updateConnection} /></label>
      <label className="field">Cookie <small>Opcional</small><input name="cookie" value={connection.cookie} onChange={updateConnection} /></label>
      <label className="kronos-check"><input type="checkbox" name="allowSelfSigned" checked={connection.allowSelfSigned} onChange={updateConnection} /> Permitir certificado autofirmado</label>
    </div>
    <div className="kronos-device-actions">
      {saved && <span role="status">Configuración guardada para esta sesión.</span>}
      <button type="submit" className="button"><Save size={16} /> Guardar conexión</button>
    </div>
  </form>;
}