import { useState } from "react";
import { Upload, Trash2, FileText, Image, X } from "lucide-react";
import {
  uploadSupervisorDailyAttachment,
  getSupervisorDailyAttachments,
  deleteSupervisorDailyAttachment,
} from "../api";
import { useI18n } from "../i18n";

export default function SupervisorDailyLog({ id_supervisor_activity_log, attachments = [], onAttachmentsChange }) {
  const { t } = useI18n();
  const [uploading, setUploading] = useState(false);
  const [localAttachments, setLocalAttachments] = useState(attachments);
  const [fileInput, setFileInput] = useState(null);
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");

  const handleFileSelect = async (event) => {
    const files = Array.from(event.target.files);
    if (!files.length) return;

    setUploading(true);
    setError("");

    for (const file of files) {
      try {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("id_supervisor_activity_log", id_supervisor_activity_log);
        if (description) formData.append("description", description);

        const result = await uploadSupervisorDailyAttachment(formData);
        setLocalAttachments((prev) => [...prev, result]);
      } catch (err) {
        setError(`Error subiendo ${file.name}: ${err.message}`);
      }
    }

    setUploading(false);
    setDescription("");
    if (fileInput) fileInput.value = "";
    if (onAttachmentsChange) onAttachmentsChange(localAttachments);
  };

  const handleDelete = async (id) => {
    if (!window.confirm("¿Eliminar adjunto?")) return;

    try {
      await deleteSupervisorDailyAttachment(id);
      setLocalAttachments((prev) => prev.filter((a) => a.id_supervisor_daily_attachment !== id));
      if (onAttachmentsChange) onAttachmentsChange(localAttachments);
    } catch (err) {
      setError(`Error eliminando: ${err.message}`);
    }
  };

  const getFileIcon = (extension) => {
    if ([".png", ".jpg", ".jpeg", ".gif", ".bmp"].includes(extension.toLowerCase())) {
      return <Image size={16} className="text-blue-500" />;
    }
    return <FileText size={16} className="text-gray-500" />;
  };

  return (
    <div className="border rounded-lg p-4 bg-gray-50">
      <h3 className="font-semibold text-sm mb-3">Adjuntos de la Bitácora</h3>

      {error && <div className="text-red-600 text-sm mb-2 p-2 bg-red-50 rounded">{error}</div>}

      <div className="mb-4">
        <label className="block text-xs text-gray-700 mb-2">Descripción (opcional)</label>
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Ej: Foto del soldado completado"
          className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
          disabled={uploading}
        />
      </div>

      <div className="mb-4">
        <label className="flex items-center gap-2 px-3 py-2 bg-blue-500 text-white rounded cursor-pointer hover:bg-blue-600 text-sm font-medium w-fit">
          <Upload size={16} />
          {uploading ? "Subiendo..." : "Seleccionar archivos"}
          <input
            type="file"
            multiple
            accept=".txt,.docx,.pdf,.png,.jpg,.jpeg,.gif,.bmp"
            onChange={handleFileSelect}
            ref={setFileInput}
            className="hidden"
            disabled={uploading}
          />
        </label>
        <p className="text-xs text-gray-500 mt-1">
          Permitidos: TXT, DOCX, PDF, PNG, JPG, GIF, BMP (máx 25MB)
        </p>
      </div>

      {localAttachments.length > 0 ? (
        <div className="space-y-2">
          {localAttachments.map((attachment) => (
            <div
              key={attachment.id_supervisor_daily_attachment}
              className="flex items-center gap-2 p-2 bg-white border border-gray-200 rounded text-sm"
            >
              {getFileIcon(attachment.extension)}
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-800 truncate">{attachment.original_filename}</p>
                {attachment.description && <p className="text-xs text-gray-600">{attachment.description}</p>}
                <p className="text-xs text-gray-500">
                  {(attachment.file_size / 1024).toFixed(1)}KB · {new Date(attachment.creation_date).toLocaleString()}
                </p>
              </div>
              <button
                onClick={() => handleDelete(attachment.id_supervisor_daily_attachment)}
                className="p-1 text-red-600 hover:bg-red-50 rounded"
                title="Eliminar"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-500 italic">Sin adjuntos aún</p>
      )}
    </div>
  );
}
