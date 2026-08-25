import React from "react";
import KronosDeviceConnection from "../components/KronosDeviceConnection";
import "../styles/kronos.css";
import "../styles/kronos-device.css";

export default function KronosDevicePage() {
  return <section className="entity-page kronos-page kronos-device-page">
    <div className="page-heading kronos-heading">
      <div><p className="eyebrow">CONTROL DE ACCESO</p><h2>Conexión al dispositivo</h2><p>Configura la comunicación con el dispositivo Hikvision para utilizar Kronos.</p></div>
    </div>
    <KronosDeviceConnection />
  </section>;
}