import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { Download, Pencil, Plus, RefreshCw, Save, Search, Trash2, UsersRound } from "lucide-react";
import { deleteKronosPerson, getAttendanceEmployeeOptions, getEmployeeLinks, getKronosAttendance, getKronosPeople, getSavedAttendance, importKronosAttendance, linkEmployee, saveKronosPerson, unlinkEmployee } from "../api";
import { loadKronosConnection } from "../utils/kronosConnection";
import "../styles/kronos.css";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader.jsx";

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

function downloadCsv(rows, t) {
  const headers = [
    t("kronos.csv.headers.date"),
    t("kronos.csv.headers.name"),
    t("kronos.csv.headers.employee"),
    t("kronos.csv.headers.first"),
    t("kronos.csv.headers.last"),
    t("kronos.csv.headers.marks"),
    t("kronos.csv.headers.door"),
    t("kronos.csv.headers.verification"),
  ];
  const lines = rows.map((row) => [
    row.date,
    row.name,
    row.employee,
    formatTime(row.firstEntry),
    formatTime(row.lastExit),
    row.marks,
    row.door,
    row.verification,
  ].map(csvValue).join(","));
  const blob = new Blob([`\uFEFF${headers.map(csvValue).join(",")}\n${lines.join("\n")}`], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${t("kronos.csv.filename_prefix")}-${localDate(new Date())}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function emptyPerson() {
  return { employeeNo: "", name: "", userType: "normal", gender: "unknown", beginTime: localDate(today), endTime: "2037-12-31" };
}

export default function KronosPage() {
  const personDialog = useRef(null);
  const { lang, t } = useI18n();
  const [view, setView] = useState("attendance");
  const [connection] = useState(loadKronosConnection);
  const [period, setPeriod] = useState({ startDate: localDate(new Date(today.getFullYear(), today.getMonth(), 1)), endDate: localDate(today), timezone: "-06:00" });
  const [report, setReport] = useState([]);
  const [statistics, setStatistics] = useState([]);
  const [eventsCount, setEventsCount] = useState(0);
  const [people, setPeople] = useState([]);
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query.trim().toLocaleLowerCase(lang));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  // "device": se le pregunta al checador en vivo. "saved": se lee lo guardado
  // en la base, sin necesitar el checador.
  const [source, setSource] = useState("device");
  const [notice, setNotice] = useState("");
  const [updatedAt, setUpdatedAt] = useState("");
  // Que empleado del sistema es cada numero del checador:
  // { employee_no: { id_user, full_name } }.
  // `null` mientras no se sabe si el rol puede ver los vinculos; sin permiso la
  // columna no se muestra.
  const [links, setLinks] = useState(null);
  const [userOptions, setUserOptions] = useState([]);
  const [personForm, setPersonForm] = useState(emptyPerson());
  const [originalPerson, setOriginalPerson] = useState(null);

  const filteredReport = useMemo(() => report.filter((row) => String(row.employee).toLocaleLowerCase(lang).includes(deferredQuery) || String(row.name).toLocaleLowerCase(lang).includes(deferredQuery)), [report, deferredQuery, lang]);
  const filteredPeople = useMemo(() => people.filter((person) => String(person.employeeNo).toLocaleLowerCase(lang).includes(deferredQuery) || String(person.name).toLocaleLowerCase(lang).includes(deferredQuery)), [people, deferredQuery, lang]);

  function ensureConnection() {
    if (connection.deviceUrl && connection.username && connection.password) return true;
    setError(t("kronos.errors.missing_connection"));
    return false;
  }

  function describeError(requestError) {
    if (requestError?.message === "errors.permission_denied") return t("kronos.errors.permission_denied");
    if (requestError?.message === "errors.kronos_device_unavailable") return t("kronos.errors.unavailable");
    return t("kronos.errors.generic");
  }

  async function loadLinks() {
    try {
      const data = await getEmployeeLinks();
      setLinks(Object.fromEntries((data.links || []).map((link) => [String(link.employee_no), { id_user: link.id_user, full_name: link.full_name }])));
    } catch {
      setLinks(null);
    }
  }

  useEffect(() => {
    loadLinks();
    // Solo empleados: el backend tampoco deja ligar a quien no lo es.
    getAttendanceEmployeeOptions().then((data) => setUserOptions(data.employees || [])).catch(() => setUserOptions([]));
  }, []);

  async function changeLink(employeeNo, idUser) {
    setLoading(true);
    setError("");
    setNotice("");
    try {
      if (idUser) await linkEmployee(employeeNo, Number(idUser));
      else await unlinkEmployee(employeeNo);
      setNotice(idUser ? t("kronos.link.done") : t("kronos.link.removed"));
      await loadLinks();
      // Lo guardado muestra el nombre del sistema: se vuelve a leer para verlo.
      if (source === "saved" && report.length) await fetchAttendance();
    } catch (requestError) {
      setError(describeError(requestError));
    } finally {
      setLoading(false);
    }
  }

  function linkSelect(employeeNo, label) {
    if (links === null) return null;
    const link = links[String(employeeNo)];
    const value = link?.id_user ?? "";
    // Un vinculo hecho antes de que la persona dejara de ser empleado se sigue
    // mostrando, para no esconder a quien tiene las checadas.
    const fueraDeLaLista = link && !userOptions.some((user) => user.id_user === link.id_user);
    return (
      <select aria-label={`${t("kronos.link.column")} ${label || employeeNo}`} value={value} disabled={loading} onChange={(event) => changeLink(String(employeeNo), event.target.value)}>
        <option value="">{t("kronos.link.none")}</option>
        {fueraDeLaLista && <option value={link.id_user}>{link.full_name || link.id_user}</option>}
        {userOptions.map((user) => <option key={user.id_user} value={user.id_user}>{user.full_name || user.username}</option>)}
      </select>
    );
  }

  function devicePeriod() {
    return { startTime: `${period.startDate}T00:00:00${period.timezone}`, endTime: `${period.endDate}T23:59:59${period.timezone}` };
  }

  async function loadAttendance(event) {
    event.preventDefault();
    if (source === "device" && !ensureConnection()) return;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      await fetchAttendance();
    } catch (requestError) {
      setError(describeError(requestError));
    } finally {
      setLoading(false);
    }
  }

  async function fetchAttendance() {
    const data = source === "saved"
      ? await getSavedAttendance(period)
      : await getKronosAttendance({ ...connection, ...devicePeriod() });
    setReport(data.report || []);
    setStatistics(data.statistics || []);
    // Lo guardado no trae el directorio del checador: no se borra el que ya habia.
    if (data.people) setPeople(data.people);
    setEventsCount((data.events || []).length);
    setUpdatedAt(new Intl.DateTimeFormat(lang, { hour: "2-digit", minute: "2-digit" }).format(new Date()));
  }

  async function saveAttendance() {
    if (!ensureConnection()) {
      setError(t("kronos.import.needs_connection"));
      return;
    }
    setLoading(true);
    setError("");
    setNotice("");
    try {
      const result = await importKronosAttendance({ ...connection, ...devicePeriod() });
      setNotice(`${t("kronos.import.done")}: ${t("kronos.import.saved")} ${result.saved} · ${t("kronos.import.already_saved")} ${result.already_saved} · ${t("kronos.import.skipped")} ${result.skipped}`);
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
    if (!window.confirm(`${t('kronos.action.delete_person')} ${person.name || person.employeeNo}?`) || !ensureConnection()) return;
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
      <PageHeader
        eyebrow={t('kronos.page.eyebrow')}
        titulo={t('kronos.page.title')}
        subtitulo={t('kronos.page.description')}
      >
        <span className={`kronos-status ${loading ? 'loading' : updatedAt ? 'connected' : ''}`}>
        {loading ? t('kronos.status.loading') : updatedAt ? t('kronos.status.connected') : t('kronos.status.idle')}
        </span>
      </PageHeader>

      <div className="kronos-tabs" role="tablist" aria-label={t('kronos.tabs.aria_label')}>
        <button type="button" role="tab" aria-selected={view === 'attendance'} className={view === 'attendance' ? 'active' : ''} onClick={() => { setView('attendance'); setQuery(''); }}>{t('kronos.tabs.attendance')}</button>
        <button type="button" role="tab" aria-selected={view === 'people'} className={view === 'people' ? 'active' : ''} onClick={() => { setView('people'); setQuery(''); }}>{t('kronos.tabs.people')}</button>
      </div>

      {error && <div className="alert error" role="alert">{error}</div>}
      {notice && <div className="alert success" role="status">{notice}</div>}

      {view === 'attendance' ? (
        <>
          <form className="form-card kronos-filter" onSubmit={loadAttendance}>
            <label className="field">{t('kronos.filter.from')}<input required type="date" value={period.startDate} onChange={(event) => setPeriod((current) => ({ ...current, startDate: event.target.value }))} /></label>
            <label className="field">{t('kronos.filter.to')}<input required type="date" value={period.endDate} onChange={(event) => setPeriod((current) => ({ ...current, endDate: event.target.value }))} /></label>
            <label className="field">{t('kronos.filter.source')}<select value={source} onChange={(event) => setSource(event.target.value)}><option value="device">{t('kronos.filter.source_device')}</option><option value="saved">{t('kronos.filter.source_saved')}</option></select></label>
            {source === 'device' && <label className="field">{t('kronos.filter.timezone')}<select value={period.timezone} onChange={(event) => setPeriod((current) => ({ ...current, timezone: event.target.value }))}><option>-06:00</option><option>-05:00</option><option>-04:00</option><option>+00:00</option></select></label>}
            <div className="kronos-filter-actions">
              <button type="submit" className="button" disabled={loading}><RefreshCw size={16} /> {t('kronos.filter.generate')}</button>
              {source === 'device' && <button type="button" className="button secondary" disabled={loading} onClick={saveAttendance}><Save size={16} /> {t('kronos.filter.save')}</button>}
            </div>
          </form>

          <div className="kronos-metrics">
            <div><span>{t('kronos.metrics.people')}</span><strong>{new Set(report.map((row) => row.employee)).size}</strong></div>
            <div><span>{t('kronos.metrics.days')}</span><strong>{report.length}</strong></div>
            <div><span>{t('kronos.metrics.marks')}</span><strong>{eventsCount}</strong></div>
            <div><span>{t('kronos.metrics.updated_at')}</span><strong>{updatedAt || '—'}</strong></div>
          </div>

          <section className="table-card kronos-table-card">
            <div className="kronos-table-heading">
              <div>
                <p className="eyebrow">{t('kronos.summary.eyebrow')}</p>
                <h3>{t('kronos.summary.title')}</h3>
              </div>
            </div>
            <div className="kronos-table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>{t('kronos.table.stats.employee')}</th>
                    <th>{t('kronos.table.stats.days')}</th>
                    <th>{t('kronos.table.stats.marks')}</th>
                    <th>{t('kronos.table.stats.avg_entry')}</th>
                    <th>{t('kronos.table.stats.avg_exit')}</th>
                    <th>{t('kronos.table.stats.hours')}</th>
                    {links !== null && <th>{t('kronos.link.column')}</th>}
                  </tr>
                </thead>
                <tbody>
                  {statistics.length ? statistics.map((row) => (
                    <tr key={row.employee}>
                      <td><strong>{row.name || t('kronos.table.stats.default_employee')}</strong><small>{row.employee}</small></td>
                      <td>{row.days}</td>
                      <td>{row.marks}</td>
                      <td>{formatMinutes(row.averageEntryMinutes)}</td>
                      <td>{formatMinutes(row.averageExitMinutes)}</td>
                      <td>{row.estimatedHours.toFixed(1)} h</td>
                      {links !== null && <td>{linkSelect(row.employee, row.name)}</td>}
                    </tr>
                  )) : (
                    <tr><td colSpan={links !== null ? 7 : 6} className="kronos-empty">{t('kronos.summary.empty')}</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section className="table-card kronos-table-card">
            <div className="kronos-table-heading">
              <div>
                <p className="eyebrow">{t('kronos.detail.eyebrow')}</p>
                <h3>{t('kronos.detail.title')}</h3>
              </div>
              <div className="kronos-actions">
                <label className="kronos-search"><Search size={16} /><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t('kronos.search.placeholder_employee')} /></label>
                <button type="button" className="button secondary" disabled={!report.length} onClick={() => downloadCsv(filteredReport, t)}><Download size={16} /> {t('kronos.csv.button')}</button>
              </div>
            </div>
            <div className="kronos-table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>{t('kronos.csv.headers.date')}</th>
                    <th>{t('kronos.csv.headers.name')}</th>
                    <th>{t('kronos.csv.headers.first')}</th>
                    <th>{t('kronos.csv.headers.last')}</th>
                    <th>{t('kronos.csv.headers.marks')}</th>
                    <th>{t('kronos.csv.headers.door')}</th>
                    <th>{t('kronos.csv.headers.verification')}</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredReport.length ? filteredReport.map((row) => (
                    <tr key={`${row.employee}-${row.date}`}>
                      <td>{row.date}</td>
                      <td><strong>{row.name || t('kronos.person.no_name')}</strong><small>{row.employee}</small></td>
                      <td>{formatTime(row.firstEntry)}</td>
                      <td>{formatTime(row.lastExit)}</td>
                      <td>{row.marks}</td>
                      <td>{row.door || '—'}</td>
                      <td>{row.verification || '—'}</td>
                    </tr>
                  )) : (
                    <tr><td colSpan="7" className="kronos-empty">{t('kronos.empty.attendances')}</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : (
        <section className="table-card kronos-table-card">
          <div className="kronos-table-heading">
            <div>
              <p className="eyebrow">{t('kronos.directory.eyebrow')}</p>
              <h3>{t('kronos.directory.title')}</h3>
            </div>
            <div className="kronos-actions">
              <label className="kronos-search"><Search size={16} /><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t('kronos.search.placeholder_person')} /></label>
              <button type="button" className="button secondary" onClick={loadPeople} disabled={loading}><RefreshCw size={16} /> {t('kronos.actions.refresh')}</button>
              <button type="button" className="button" onClick={() => openPerson()}><Plus size={16} /> {t('kronos.actions.new_person')}</button>
            </div>
          </div>
          <div className="kronos-table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{t('kronos.table.person.number')}</th>
                  <th>{t('kronos.table.person.name')}</th>
                  <th>{t('kronos.table.person.type')}</th>
                  <th>{t('kronos.table.person.gender')}</th>
                  <th>{t('kronos.table.person.validity')}</th>
                  {links !== null && <th>{t('kronos.link.column')}</th>}
                  <th>{t('kronos.table.person.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {filteredPeople.length ? filteredPeople.map((person) => (
                  <tr key={person.employeeNo}>
                    <td>{person.employeeNo}</td>
                    <td><strong>{person.name || t('kronos.person.no_name')}</strong></td>
                    <td>{t(`kronos.form.type.options.${person.userType}`) || person.userType}</td>
                    <td>{t(`kronos.form.gender.options.${person.gender}`) || person.gender || '—'}</td>
                    <td>{person.Valid?.enable ? `${person.Valid.beginTime?.slice(0, 10) || '—'} ${t('kronos.form.validity.to')} ${person.Valid.endTime?.slice(0, 10) || '—'}` : t('kronos.form.validity.none')}</td>
                    {links !== null && <td>{linkSelect(person.employeeNo, person.name)}</td>}
                    <td>
                      <div className="kronos-row-actions">
                        <button type="button" title={t('kronos.action.edit_person')} aria-label={`${t('kronos.action.edit_person')} ${person.name}`} onClick={() => openPerson(person)}><Pencil size={16} /></button>
                        <button type="button" className="danger" title={t('kronos.action.delete_person')} aria-label={`${t('kronos.action.delete_person')} ${person.name}`} onClick={() => removePerson(person)}><Trash2 size={16} /></button>
                      </div>
                    </td>
                  </tr>
                )) : (
                  <tr><td colSpan={links !== null ? 7 : 6} className="kronos-empty"><UsersRound size={20} /> {t('kronos.empty.directory')}</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <dialog ref={personDialog} className="kronos-dialog" onClose={() => setOriginalPerson(null)}>
        <form onSubmit={submitPerson}>
          <div className="kronos-dialog-heading">
            <div>
              <p className="eyebrow">{t('kronos.dialog.eyebrow')}</p>
              <h3>{originalPerson ? t('kronos.dialog.title.edit') : t('kronos.dialog.title.new')}</h3>
            </div>
            <button type="button" className="button ghost" onClick={() => personDialog.current?.close()}>{t('kronos.dialog.close')}</button>
          </div>
          <div className="kronos-person-grid">
            <label className="field">{t('kronos.form.employee_no')}<input required maxLength="32" readOnly={Boolean(originalPerson)} value={personForm.employeeNo} onChange={(event) => setPersonForm((current) => ({ ...current, employeeNo: event.target.value }))} /></label>
            <label className="field">{t('kronos.form.name')}<input required maxLength="96" value={personForm.name} onChange={(event) => setPersonForm((current) => ({ ...current, name: event.target.value }))} /></label>
            <label className="field">{t('kronos.form.type_label')}<select value={personForm.userType} onChange={(event) => setPersonForm((current) => ({ ...current, userType: event.target.value }))}><option value="normal">{t('kronos.form.type.options.normal')}</option><option value="visitor">{t('kronos.form.type.options.visitor')}</option></select></label>
            <label className="field">{t('kronos.form.gender_label')}<select value={personForm.gender} onChange={(event) => setPersonForm((current) => ({ ...current, gender: event.target.value }))}><option value="unknown">{t('kronos.form.gender.options.unknown')}</option><option value="female">{t('kronos.form.gender.options.female')}</option><option value="male">{t('kronos.form.gender.options.male')}</option></select></label>
            <label className="field">{t('kronos.form.valid_from')}<input required type="date" value={personForm.beginTime} onChange={(event) => setPersonForm((current) => ({ ...current, beginTime: event.target.value }))} /></label>
            <label className="field">{t('kronos.form.valid_to')}<input required type="date" value={personForm.endTime} onChange={(event) => setPersonForm((current) => ({ ...current, endTime: event.target.value }))} /></label>
          </div>
          <div className="kronos-dialog-actions">
            <button type="button" className="button secondary" onClick={() => personDialog.current?.close()}>{t('kronos.dialog.cancel')}</button>
            <button type="submit" className="button">{t('kronos.dialog.save')}</button>
          </div>
        </form>
      </dialog>
    </section>
  );
}
