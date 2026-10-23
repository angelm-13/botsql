import { useEffect, useState } from "react";
import { Calendar, FileText, Image, Plus } from "lucide-react";
import {
  getSupervisorActivityLog,
  createSupervisorActivityLogEntry,
  getSupervisorProjectAttachments,
  getProyect,
  getMyPermissions,
} from "../api";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader.jsx";
import SupervisorDailyLog from "../components/SupervisorDailyLog.jsx";

export default function SupervisorDailyLogPage() {
  const { t } = useI18n();
  const [logs, setLogs] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [dateFrom, setDateFrom] = useState(
    new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split("T")[0]
  );
  const [dateTo, setDateTo] = useState(new Date().toISOString().split("T")[0]);
  const [attachmentsByLog, setAttachmentsByLog] = useState({});
  const [loading, setLoading] = useState(true);
  const [permissions, setPermissions] = useState([]);
  const [showNewEntryForm, setShowNewEntryForm] = useState(false);
  const [newEntryDate, setNewEntryDate] = useState(new Date().toISOString().split("T")[0]);
  const [newEntryContent, setNewEntryContent] = useState("");
  const [newEntryProject, setNewEntryProject] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const perms = await getMyPermissions();
      setPermissions(perms?.items || []);
      const result = await getSupervisorActivityLog({ sort: "-activity_date" });
      setLogs(result?.items || []);

      // Cargar adjuntos para cada log
      const attachmentsMap = {};
      for (const log of (result?.items || [])) {
        try {
          const attachments = await getSupervisorProjectAttachments(log.id_proyect, dateFrom, dateTo);
          attachmentsMap[log.id_supervisor_activity_log] = attachments?.items || [];
        } catch {
          attachmentsMap[log.id_supervisor_activity_log] = [];
        }
      }
      setAttachmentsByLog(attachmentsMap);
    } catch (error) {
      console.error("Error cargando bitácora:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateEntry = async () => {
    if (!newEntryDate || !newEntryContent) {
      alert("Completa la fecha y descripción");
      return;
    }

    try {
      const payload = {
        activity_date: newEntryDate,
        content: newEntryContent,
        id_proyect: newEntryProject ? parseInt(newEntryProject) : null,
      };
      await createSupervisorActivityLogEntry(payload);
      setNewEntryDate(new Date().toISOString().split("T")[0]);
      setNewEntryContent("");
      setNewEntryProject("");
      setShowNewEntryForm(false);
      loadData();
    } catch (error) {
      alert("Error creando entrada: " + error.message);
    }
  };

  const hasPermission = (entity) => {
    return permissions.some((p) => p.entity_name === entity && p.scope_read > 0);
  };

  if (!hasPermission("supervisor_activity_log")) {
    return <div className="p-4 text-red-600">No tienes permiso para ver la bitácora</div>;
  }

  return (
    <div className="flex flex-col gap-4 p-4 h-screen overflow-auto bg-gray-50">
      <PageHeader
        title="Bitácora Diaria del Supervisor"
        subtitle="Registro de actividades y adjuntos por día"
      />

      {/* Filtros */}
      <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
        <div className="grid grid-cols-4 gap-4 items-end">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Desde</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Hasta</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded"
            />
          </div>
          <button
            onClick={loadData}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Filtrar
          </button>
          <button
            onClick={() => setShowNewEntryForm(!showNewEntryForm)}
            className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
          >
            <Plus size={16} />
            Nueva Entrada
          </button>
        </div>
      </div>

      {/* Formulario de nueva entrada */}
      {showNewEntryForm && (
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
          <h3 className="font-semibold mb-3">Nueva Entrada de Bitácora</h3>
          <div className="grid grid-cols-4 gap-4 mb-4">
            <input
              type="date"
              value={newEntryDate}
              onChange={(e) => setNewEntryDate(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded text-sm"
            />
            <input
              type="text"
              placeholder="Descripción breve (opcional)"
              value={newEntryContent}
              onChange={(e) => setNewEntryContent(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded text-sm"
            />
            <button
              onClick={handleCreateEntry}
              className="px-4 py-2 bg-green-500 text-white rounded text-sm hover:bg-green-600"
            >
              Crear Entrada
            </button>
            <button
              onClick={() => setShowNewEntryForm(false)}
              className="px-4 py-2 bg-gray-300 text-gray-700 rounded text-sm hover:bg-gray-400"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* Listado de bitácoras */}
      {loading ? (
        <div className="text-center py-8 text-gray-500">Cargando...</div>
      ) : logs.length === 0 ? (
        <div className="text-center py-8 text-gray-500">Sin registros en el período</div>
      ) : (
        <div className="space-y-4">
          {logs.map((log) => (
            <div key={log.id_supervisor_activity_log} className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h4 className="font-semibold text-gray-800">{log.activity_date}</h4>
                  <p className="text-sm text-gray-600">{log.content || "Sin descripción"}</p>
                </div>
                {log.id_proyect && (
                  <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                    Proyecto #{log.id_proyect}
                  </span>
                )}
              </div>

              {/* Adjuntos para este log */}
              <SupervisorDailyLog
                id_supervisor_activity_log={log.id_supervisor_activity_log}
                attachments={attachmentsByLog[log.id_supervisor_activity_log] || []}
                onAttachmentsChange={() => loadData()}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
