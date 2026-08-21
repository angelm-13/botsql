import React, { useDeferredValue, useMemo, useRef, useState } from "react";
import { Download, Pencil, Plus, RefreshCw, Search, Trash2, UsersRound } from "lucide-react";
import { deleteKronosPerson, getKronosAttendance, getKronosPeople, saveKronosPerson } from "../api";
import { loadKronosConnection } from "../utils/kronosConnection";
import "../styles/kronos.css";

function localDate(date) {
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
}

const today = new Date();
function formatTime(value) {
  return value ? String(value).slice(11, 19) : "—";
}

function formatMinutes(value) {
  return `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`;
}

function csvValue(value) {
  const normalized = String(value ?? "").replace(/^[=+\-@]/, "'$&").replaceAll('"', '""');
  return `"${normalized}"`;
}

function downloadCsv(rows) {
  const headers = ["Fecha", "Nombre", "Empleado", "Primera marca", "Última marca", "Marcaciones", "Puerta", "Verificación"];
  const lines = rows.map((row) => [row.date, row.name, row.employee, formatTime(row.firstEntry), formatTime(row.lastExit), row.marks, row.door, row.verification].map(csvValue).join(","));
  const blob = new Blob([`\uFEFF${headers.map(csvValue).join(",")}\n${lines.join("\n")}`], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `asistencias-${localDate(new Date())}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function emptyPerson() {
  return { employeeNo: "", name: "", userType: "normal", gender: "unknown", beginTime: localDate(today), endTime: "2037-12-31" };
}

export default function KronosPage() {
  const personDialog = useRef(null);
  const [view, setView] = useState("attendance");
  const [connection] = useState(loadKronosConnection);
  const [period, setPeriod] = useState({ startDate: localDate(new Date(today.getFullYear(), today.getMonth(), 1)), endDate: localDate(today), timezone: "-06:00" });
  const [report, setReport] = useState([]);
  const [statistics, setStatistics] = useState([]);
  const [eventsCount, setEventsCount] = useState(0);
  const [people, setPeople] = useState([]);
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query.trim().toLocaleLowerCase("es"));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [updatedAt, setUpdatedAt] = useState("");
  const [personForm, setPersonForm] = useState(emptyPerson());
  const [originalPerson, setOriginalPerson] = useState(null);

  const filteredReport = useMemo(() => report.filter((row) => String(row.employee).toLocaleLowerCase("es").includes(deferredQuery) || String(row.name).toLocaleLowerCase("es").includes(deferredQuery)), [report, deferredQuery]);
  const filteredPeople = useMemo(() => people.filter((person) => String(person.employeeNo).toLocaleLowerCase("es").includes(deferredQuery) || String(person.name).toLocaleLowerCase("es").includes(deferredQuery)), [people, deferredQuery]);

  function ensureConnection() {
    if (connection.deviceUrl && connection.username && connection.password) return true;
    setError("Configura la conexión al dispositivo desde el engrane de configuración.");
    return false;
  }

  function describeError(requestError) {
    if (requestError?.message === "errors.permission_denied") return "No tienes permisos para realizar esta operación.";
    if (requestError?.message === "errors.kronos_device_unavailable") return "No se pudo establecer comunicación con el dispositivo.";
    return "No se pudo completar la operación con el dispositivo.";
  }

  async function loadAttendance(event) {
    event.preventDefault();
    if (!ensureConnection()) return;
    setLoading(true);
    setError("");
    try {
      const data = await getKronosAttendance({ ...connection, startTime: `${period.startDate}T00:00:00${period.timezone}`, endTime: `${period.endDate}T23:59:59${period.timezone}` });
      setReport(data.report || []);
      setStatistics(data.statistics || []);
      setPeople(data.people || []);
      setEventsCount((data.events || []).length);
      setUpdatedAt(new Intl.DateTimeFormat("es-MX", { hour: "2-digit", minute: "2-digit" }).format(new Date()));
    } catch (requestError) {
      setError(describeError(requestError));
    } finally {
      setLoading(false);
    }
  }

  async function loadPeople() {
    if (!ensureConnection()) return;
    setLoading(true);
    setError("");
    try {
      const data = await getKronosPeople(connection);
      setPeople(data.people || []);
    } catch (requestError) {
      setError(describeError(requestError));
    } finally {
      setLoading(false);
    }
  }

  function openPerson(person = null) {
    setOriginalPerson(person);
    setPersonForm(person ? { employeeNo: person.employeeNo || "", name: person.name || "", userType: person.userType || "normal", gender: person.gender || "unknown", beginTime: person.Valid?.beginTime?.slice(0, 10) || localDate(today), endTime: person.Valid?.endTime?.slice(0, 10) || "2037-12-31" } : emptyPerson());
    personDialog.current?.showModal();
  }

  async function submitPerson(event) {
    event.preventDefault();
    if (!ensureConnection()) return;
    setLoading(true);
    setError("");
    const person = {
      ...(originalPerson || {}), employeeNo: personForm.employeeNo.trim(), name: personForm.name.trim(), userType: personForm.userType, gender: personForm.gender,
      Valid: { enable: true, beginTime: `${personForm.beginTime}T00:00:00`, endTime: `${personForm.endTime}T23:59:59`, timeType: "local" },
      doorRight: originalPerson?.doorRight || "1", RightPlan: originalPerson?.RightPlan || [{ doorNo: 1, planTemplateNo: "1" }],
    };
    try {
      await saveKronosPerson({ ...connection, person });
      personDialog.current?.close();
      await loadPeople();
    } catch (requestError) {
      setError(describeError(requestError));
      setLoading(false);
    }
  }

  async function removePerson(person) {
    if (!window.confirm(`¿Eliminar a ${person.name || person.employeeNo} del dispositivo?`) || !ensureConnection()) return;
    setLoading(true);
    setError("");
    try {
      await deleteKronosPerson(person.employeeNo, connection);
      await loadPeople();
    } catch (requestError) {
      setError(describeError(requestError));
      setLoading(false);
    }
  }

  return (
    <section className="entity-page kronos-page">
      <div className="page-heading kronos-heading">
        <div><p className="eyebrow">CONTROL DE ACCESO</p><h2>Kronos</h2><p>Asistencias y personas del dispositivo Hikvision.</p></div>
        <span className={`kronos-status ${loading ? "loading" : updatedAt ? "connected" : ""}`}>{loading ? "Consultando" : updatedAt ? "Conectado" : "Sin consultar"}</span>
      </div>
      <div className="kronos-tabs" role="tablist" aria-label="Secciones de Kronos">
        <button type="button" role="tab" aria-selected={view === "attendance"} className={view === "attendance" ? "active" : ""} onClick={() => { setView("attendance"); setQuery(""); }}>Asistencias</button>
        <button type="button" role="tab" aria-selected={view === "people"} className={view === "people" ? "active" : ""} onClick={() => { setView("people"); setQuery(""); }}>Personas</button>
      </div>
      {error && <div className="alert error" role="alert">{error}</div>}
      {view === "attendance" ? <>
        <form className="form-card kronos-filter" onSubmit={loadAttendance}>
          <label className="field">Desde<input required type="date" value={period.startDate} onChange={(event) => setPeriod((current) => ({ ...current, startDate: event.target.value }))} /></label>
          <label className="field">Hasta<input required type="date" value={period.endDate} onChange={(event) => setPeriod((current) => ({ ...current, endDate: event.target.value }))} /></label>
          <label className="field">Zona horaria<select value={period.timezone} onChange={(event) => setPeriod((current) => ({ ...current, timezone: event.target.value }))}><option>-06:00</option><option>-05:00</option><option>-04:00</option><option>+00:00</option></select></label>
          <button type="submit" className="button" disabled={loading}><RefreshCw size={16} /> Generar reporte</button>
        </form>
        <div className="kronos-metrics"><div><span>Personas</span><strong>{new Set(report.map((row) => row.employee)).size}</strong></div><div><span>Jornadas</span><strong>{report.length}</strong></div><div><span>Marcaciones</span><strong>{eventsCount}</strong></div><div><span>Actualización</span><strong>{updatedAt || "—"}</strong></div></div>
        <section className="table-card kronos-table-card"><div className="kronos-table-heading"><div><p className="eyebrow">RESUMEN POR PERSONA</p><h3>Estadísticas</h3></div></div><div className="kronos-table-scroll"><table><thead><tr><th>Empleado</th><th>Días</th><th>Marcas</th><th>Entrada promedio</th><th>Salida promedio</th><th>Horas estimadas</th></tr></thead><tbody>{statistics.length ? statistics.map((row) => <tr key={row.employee}><td><strong>{row.name || "Empleado"}</strong><small>{row.employee}</small></td><td>{row.days}</td><td>{row.marks}</td><td>{formatMinutes(row.averageEntryMinutes)}</td><td>{formatMinutes(row.averageExitMinutes)}</td><td>{row.estimatedHours.toFixed(1)} h</td></tr>) : <tr><td colSpan="6" className="kronos-empty">Genera el reporte para ver estadísticas.</td></tr>}</tbody></table></div></section>
        <section className="table-card kronos-table-card"><div className="kronos-table-heading"><div><p className="eyebrow">DETALLE DIARIO</p><h3>Asistencias</h3></div><div className="kronos-actions"><label className="kronos-search"><Search size={16} /><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar empleado" /></label><button type="button" className="button secondary" disabled={!report.length} onClick={() => downloadCsv(filteredReport)}><Download size={16} /> CSV</button></div></div><div className="kronos-table-scroll"><table><thead><tr><th>Fecha</th><th>Empleado</th><th>Primera marca</th><th>Última marca</th><th>Marcas</th><th>Puerta</th><th>Verificación</th></tr></thead><tbody>{filteredReport.length ? filteredReport.map((row) => <tr key={`${row.employee}-${row.date}`}><td>{row.date}</td><td><strong>{row.name || "Empleado"}</strong><small>{row.employee}</small></td><td>{formatTime(row.firstEntry)}</td><td>{formatTime(row.lastExit)}</td><td>{row.marks}</td><td>{row.door || "—"}</td><td>{row.verification || "—"}</td></tr>) : <tr><td colSpan="7" className="kronos-empty">No hay asistencias para mostrar.</td></tr>}</tbody></table></div></section>
      </> : <section className="table-card kronos-table-card"><div className="kronos-table-heading"><div><p className="eyebrow">DIRECTORIO DEL DISPOSITIVO</p><h3>Personas</h3></div><div className="kronos-actions"><label className="kronos-search"><Search size={16} /><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar persona" /></label><button type="button" className="button secondary" onClick={loadPeople} disabled={loading}><RefreshCw size={16} /> Consultar</button><button type="button" className="button" onClick={() => openPerson()}><Plus size={16} /> Nueva persona</button></div></div><div className="kronos-table-scroll"><table><thead><tr><th>Número</th><th>Nombre</th><th>Tipo</th><th>Género</th><th>Vigencia</th><th>Acciones</th></tr></thead><tbody>{filteredPeople.length ? filteredPeople.map((person) => <tr key={person.employeeNo}><td>{person.employeeNo}</td><td><strong>{person.name || "Sin nombre"}</strong></td><td>{person.userType || "normal"}</td><td>{person.gender || "—"}</td><td>{person.Valid?.enable ? `${person.Valid.beginTime?.slice(0, 10) || "—"} a ${person.Valid.endTime?.slice(0, 10) || "—"}` : "Sin límite"}</td><td><div className="kronos-row-actions"><button type="button" title="Editar persona" aria-label={`Editar ${person.name}`} onClick={() => openPerson(person)}><Pencil size={16} /></button><button type="button" className="danger" title="Eliminar persona" aria-label={`Eliminar ${person.name}`} onClick={() => removePerson(person)}><Trash2 size={16} /></button></div></td></tr>) : <tr><td colSpan="6" className="kronos-empty"><UsersRound size={20} /> Consulta el directorio del dispositivo.</td></tr>}</tbody></table></div></section>}
      <dialog ref={personDialog} className="kronos-dialog" onClose={() => setOriginalPerson(null)}><form onSubmit={submitPerson}><div className="kronos-dialog-heading"><div><p className="eyebrow">PERSONA</p><h3>{originalPerson ? "Editar persona" : "Nueva persona"}</h3></div><button type="button" className="button ghost" onClick={() => personDialog.current?.close()}>Cerrar</button></div><div className="kronos-person-grid"><label className="field">Número de empleado<input required maxLength="32" readOnly={Boolean(originalPerson)} value={personForm.employeeNo} onChange={(event) => setPersonForm((current) => ({ ...current, employeeNo: event.target.value }))} /></label><label className="field">Nombre<input required maxLength="96" value={personForm.name} onChange={(event) => setPersonForm((current) => ({ ...current, name: event.target.value }))} /></label><label className="field">Tipo<select value={personForm.userType} onChange={(event) => setPersonForm((current) => ({ ...current, userType: event.target.value }))}><option value="normal">Normal</option><option value="visitor">Visitante</option></select></label><label className="field">Género<select value={personForm.gender} onChange={(event) => setPersonForm((current) => ({ ...current, gender: event.target.value }))}><option value="unknown">No especificado</option><option value="female">Femenino</option><option value="male">Masculino</option></select></label><label className="field">Válido desde<input required type="date" value={personForm.beginTime} onChange={(event) => setPersonForm((current) => ({ ...current, beginTime: event.target.value }))} /></label><label className="field">Válido hasta<input required type="date" value={personForm.endTime} onChange={(event) => setPersonForm((current) => ({ ...current, endTime: event.target.value }))} /></label></div><div className="kronos-dialog-actions"><button type="button" className="button secondary" onClick={() => personDialog.current?.close()}>Cancelar</button><button type="submit" className="button" disabled={loading}>Guardar</button></div></form></dialog>
    </section>
  );
}