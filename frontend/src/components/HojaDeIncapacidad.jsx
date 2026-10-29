import { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Eye, Upload, X } from "lucide-react";
import { getEmployeeLeaveDocuments, openEmployeeLeaveDocument, uploadEmployeeLeaveDocument } from "../api";
import { useI18n } from "../i18n";

// Hojas de incapacidad de una ausencia: verlas y subir otra. Las ven solo el
// propio empleado y RH; a cualquier otro el backend le contesta 404
// (services/employee_leave_document_service.py). Se usa en "Mis vacaciones" y
// en "Vacaciones y permisos".

const TIPOS = ".pdf,.jpg,.jpeg,.png";

export default function HojaDeIncapacidad({ idAusencia, alCerrar }) {
  const { t } = useI18n();
  const [hojas, setHojas] = useState([]);
  const [archivo, setArchivo] = useState(null);
  const [error, setError] = useState("");
  const [subiendo, setSubiendo] = useState(false);

  const describir = (e) => t(e?.payload?.error_key || e?.message || "errors.request_failed", t("errors.request_failed"));

  const cargar = useCallback(async () => {
    try {
      setHojas((await getEmployeeLeaveDocuments(idAusencia))?.documents || []);
    } catch (e) {
      setError(t(e?.payload?.error_key || e?.message || "errors.request_failed", t("errors.request_failed")));
    }
  }, [idAusencia, t]);

  useEffect(() => { cargar(); }, [cargar]);

  async function subir(event) {
    event.preventDefault();
    if (!archivo) return;
    setError("");
    setSubiendo(true);
    try {
      await uploadEmployeeLeaveDocument(idAusencia, archivo);
      setArchivo(null);
      event.target.reset();
      await cargar();
    } catch (e) {
      setError(describir(e));
    } finally {
      setSubiendo(false);
    }
  }

  async function ver(version) {
    try {
      const blob = await openEmployeeLeaveDocument(idAusencia, version);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener");
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) {
      setError(describir(e));
    }
  }

  return (
    <div className="form-card">
      <div className="kronos-table-heading">
        <div><p className="eyebrow">{t("leave_sheet.eyebrow")}</p><h3>{t("leave_sheet.title")}</h3></div>
        <button className="button ghost" type="button" onClick={alCerrar}><X size={16} /> {t("common.close", "Cerrar")}</button>
      </div>
      <p className="muted">{t("leave_sheet.privacy")}</p>
      {error && <div className="alert error" role="alert">{error}</div>}
      {hojas.length ? (
        <table>
          <thead><tr><th>{t("leave_sheet.file")}</th><th>{t("leave_sheet.uploaded_by")}</th><th>{t("leave_sheet.date")}</th><th>{t("common.actions")}</th></tr></thead>
          <tbody>{hojas.map((h) => (
            <tr key={h.version}>
              <td><strong>{h.original_filename}</strong> <small className="muted">v{h.version} · {Math.max(1, Math.round(h.file_size / 1024))} KB</small></td>
              <td>{h.uploaded_by_name || `#${h.uploaded_by}`}</td>
              <td><small>{(h.creation_date || "").slice(0, 10)}</small></td>
              <td className="row-actions"><button type="button" title={t("leave_sheet.view")} aria-label={`${t("leave_sheet.view")} ${h.original_filename}`} onClick={() => ver(h.version)}><Eye size={15} /></button></td>
            </tr>
          ))}</tbody>
        </table>
      ) : <p className="muted">{t("leave_sheet.none")}</p>}
      <form className="form-actions" onSubmit={subir}>
        <input type="file" accept={TIPOS} aria-label={t("leave_sheet.choose")} onChange={(e) => setArchivo(e.target.files?.[0] || null)} />
        <button className="button primary" type="submit" disabled={!archivo || subiendo}><Upload size={16} /> {subiendo ? t("common.loading") : t("leave_sheet.upload")}</button>
        <small className="muted">{t("leave_sheet.types_hint")}</small>
      </form>
    </div>
  );
}

HojaDeIncapacidad.propTypes = {
  idAusencia: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
  alCerrar: PropTypes.func.isRequired,
};
