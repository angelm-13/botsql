import KronosDeviceConnection from "../components/KronosDeviceConnection";
import "../styles/kronos.css";
import "../styles/kronos-device.css";
import PageHeader from "../components/PageHeader.jsx";

export default function KronosDevicePage() {
  return <section className="entity-page kronos-page kronos-device-page">
    <PageHeader
      eyebrow={"CONTROL DE ACCESO"}
      titulo={"Conexión al dispositivo"}
      subtitulo={"Configura la comunicación con el dispositivo Hikvision para utilizar Kronos."}
    />
    <KronosDeviceConnection />
  </section>;
}