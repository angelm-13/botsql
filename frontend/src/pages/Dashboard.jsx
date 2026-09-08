/* eslint-disable react/prop-types */
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Pencil, Plus, RefreshCw, Trash2, X } from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, LineChart, Line, AreaChart, Area,
  PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from "recharts";
import { useI18n } from "../i18n";
import {
  getAllKpiDashboard, createKpiDashboard, updateKpiDashboard, deleteKpiDashboard,
  getAllKpiDashboardWidget, createKpiDashboardWidget, updateKpiDashboardWidget, deleteKpiDashboardWidget,
  getAllKpiDefinition, queryKpiSnapshot, getAllUser,
} from "../api";
import "../styles/kpi-dashboard.css";

const CHART_TYPES = [
  { value: "numero", label: "Número" },
  { value: "barras", label: "Barras" },
  { value: "linea", label: "Línea" },
  { value: "area", label: "Área" },
  { value: "dona", label: "Dona" },
];

// Orden categorico validado (dataviz skill): identidad, nunca ciclado.
const CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"];
const COLOR_A = CATEGORICAL[0];
const COLOR_B = CATEGORICAL[1];
const COLOR_OTHERS = "#898781";
const AXIS_TICK = { fontSize: 11, fill: "#898781" };

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgoIso(n) {
  const fecha = new Date();
  fecha.setDate(fecha.getDate() - n);
  return fecha.toISOString().slice(0, 10);
}

function listOf(data) {
  return Array.isArray(data) ? data : data?.items || [];
}

function localeFor(lang) {
  return lang === "ja" ? "ja-JP" : lang === "en" ? "en-US" : lang === "pt" ? "pt-BR" : lang === "de" ? "de-DE" : "es-MX";
}

function buildSeriesData(snapshot, userLabel, empleadosFiltro) {
  const porA = snapshot?.rango_a?.por_empleado || {};
  const porB = snapshot?.rango_b?.por_empleado || {};
  let ids = Array.from(new Set([...Object.keys(porA), ...Object.keys(porB)]));
  if (Array.isArray(empleadosFiltro) && empleadosFiltro.length) {
    const orden = empleadosFiltro.map(String);
    ids = orden.filter((id) => ids.includes(id));
  } else {
    ids.sort((x, y) => (porA[y] ?? 0) - (porA[x] ?? 0));
  }
  return ids.map((id) => ({
    name: userLabel(id),
    a: porA[id] ?? 0,
    b: id in porB ? porB[id] : undefined,
  }));
}

function buildPieData(snapshot, userLabel, othersLabel) {
  const porA = snapshot?.rango_a?.por_empleado || {};
  const entradas = Object.entries(porA).sort((x, y) => y[1] - x[1]);
  const principales = entradas.slice(0, CATEGORICAL.length);
  const restoTotal = entradas.slice(CATEGORICAL.length).reduce((suma, [, valor]) => suma + valor, 0);
  const data = principales.map(([id, valor]) => ({ name: userLabel(id), value: valor }));
  if (restoTotal > 0) data.push({ name: othersLabel, value: restoTotal });
  return data;
}

export default function Dashboard() {
  const { lang, t } = useI18n();
  const tx = useCallback((key, fallback) => t(`kpi_dashboard.${key}`, fallback), [t]);
  const locale = localeFor(lang);
  const formatNumber = useCallback((value) => new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(value || 0), [locale]);

  const [dashboards, setDashboards] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [loadingDashboards, setLoadingDashboards] = useState(true);
  const [dashboardsError, setDashboardsError] = useState("");

  const [widgets, setWidgets] = useState([]);
  const [loadingWidgets, setLoadingWidgets] = useState(false);
  const [widgetsError, setWidgetsError] = useState("");

  const [kpiCatalog, setKpiCatalog] = useState([]);
  const [users, setUsers] = useState([]);

  const [widgetForm, setWidgetForm] = useState(null);

  const loadDashboards = useCallback(async (preferredId) => {
    setLoadingDashboards(true);
    setDashboardsError("");
    try {
      const data = await getAllKpiDashboard({ per_page: 200 });
      const items = listOf(data);
      setDashboards(items);
      setActiveId((current) => {
        const target = preferredId !== undefined ? preferredId : current;
        if (target && items.some((item) => item.id_kpi_dashboard === target)) return target;
        return items[0]?.id_kpi_dashboard ?? null;
      });
    } catch (error) {
      setDashboardsError(error.message || "errors.request_failed");
    } finally {
      setLoadingDashboards(false);
    }
  }, []);

  const loadWidgets = useCallback(async (dashboardId) => {
    if (!dashboardId) { setWidgets([]); return; }
    setLoadingWidgets(true);
    setWidgetsError("");
    try {
      const data = await getAllKpiDashboardWidget(dashboardId);
      setWidgets(listOf(data));
    } catch (error) {
      setWidgetsError(error.message || "errors.request_failed");
      setWidgets([]);
    } finally {
      setLoadingWidgets(false);
    }
  }, []);

  useEffect(() => { loadDashboards(); }, [loadDashboards]);
  useEffect(() => { loadWidgets(activeId); }, [activeId, loadWidgets]);

  useEffect(() => {
    let cancelado = false;
    getAllKpiDefinition().then((data) => { if (!cancelado) setKpiCatalog(listOf(data)); }).catch(() => { if (!cancelado) setKpiCatalog([]); });
    getAllUser({ per_page: 500 }).then((data) => { if (!cancelado) setUsers(listOf(data)); }).catch(() => { if (!cancelado) setUsers([]); });
    return () => { cancelado = true; };
  }, []);

  const userLabel = useCallback((idUser) => {
    const found = users.find((user) => String(user.id_user) === String(idUser));
    return found?.full_name || found?.username || `#${idUser}`;
  }, [users]);

  function notifyError(error) {
    window.alert(t(error.message || "errors.request_failed", error.message || "errors.request_failed"));
  }

  async function handleCreateDashboard() {
    const nombre = window.prompt(tx("new_dashboard_prompt", "Nombre del nuevo tablero"));
    if (nombre === null) return;
    const trimmed = nombre.trim();
    if (!trimmed) return;
    try {
      const created = await createKpiDashboard({ nombre: trimmed });
      await loadDashboards(created.id_kpi_dashboard);
    } catch (error) {
      notifyError(error);
    }
  }

  async function handleRenameDashboard(dashboard) {
    const nombre = window.prompt(tx("rename_dashboard_prompt", "Nuevo nombre del tablero"), dashboard.nombre);
    if (nombre === null) return;
    const trimmed = nombre.trim();
    if (!trimmed || trimmed === dashboard.nombre) return;
    try {
      await updateKpiDashboard(dashboard.id_kpi_dashboard, { nombre: trimmed });
      await loadDashboards(activeId);
    } catch (error) {
      notifyError(error);
    }
  }

  async function handleDeleteDashboard(dashboard) {
    const pregunta = tx("delete_dashboard_confirm", `¿Eliminar el tablero "${dashboard.nombre}"? Esta acción no se puede deshacer.`);
    if (!window.confirm(pregunta)) return;
    try {
      await deleteKpiDashboard(dashboard.id_kpi_dashboard);
      await loadDashboards();
    } catch (error) {
      notifyError(error);
    }
  }

  async function handleDeleteWidget(widget) {
    if (!window.confirm(tx("delete_widget_confirm", "¿Quitar este gráfico del tablero?"))) return;
    try {
      await deleteKpiDashboardWidget(widget.id_kpi_dashboard_widget);
      await loadWidgets(activeId);
    } catch (error) {
      notifyError(error);
    }
  }

  async function handleSaveWidget(payload, editingWidget) {
    if (editingWidget) {
      await updateKpiDashboardWidget(editingWidget.id_kpi_dashboard_widget, payload);
    } else {
      await createKpiDashboardWidget(activeId, payload);
    }
    setWidgetForm(null);
    await loadWidgets(activeId);
  }

  const activeDashboard = useMemo(
    () => dashboards.find((item) => item.id_kpi_dashboard === activeId) || null,
    [dashboards, activeId],
  );

  return (
    <section className="dashboard kpi-dashboard">
      <div className="page-heading">
        <div>
          <p className="eyebrow">{t("common.dashboard")}</p>
          <h2>{tx("title", "Tableros de KPIs")}</h2>
        </div>
        <button className="button ghost" onClick={() => loadDashboards()} disabled={loadingDashboards}>
          <RefreshCw size={16} />{loadingDashboards ? t("common.loading") : t("common.refresh")}
        </button>
      </div>

      {dashboardsError && <div className="alert error">{t(dashboardsError, dashboardsError)}</div>}

      {!loadingDashboards && dashboards.length > 0 && (
        <div className="kpi-tabs" role="tablist">
          {dashboards.map((dashboard) => (
            <div className={`kpi-tab ${dashboard.id_kpi_dashboard === activeId ? "active" : ""}`} key={dashboard.id_kpi_dashboard}>
              <button
                type="button"
                role="tab"
                aria-selected={dashboard.id_kpi_dashboard === activeId}
                className="kpi-tab-label"
                onClick={() => setActiveId(dashboard.id_kpi_dashboard)}
                title={dashboard.nombre}
              >
                {dashboard.nombre}
              </button>
              <button type="button" className="kpi-tab-icon" title={t("common.edit")} onClick={() => handleRenameDashboard(dashboard)}>
                <Pencil size={13} />
              </button>
              <button type="button" className="kpi-tab-icon danger" title={t("common.delete")} onClick={() => handleDeleteDashboard(dashboard)}>
                <Trash2 size={13} />
              </button>
            </div>
          ))}
          <button type="button" className="kpi-tab-add" onClick={handleCreateDashboard} title={tx("new_dashboard", "Nuevo tablero")}>
            <Plus size={16} />
          </button>
        </div>
      )}

      {!loadingDashboards && dashboards.length === 0 && !dashboardsError && (
        <div className="empty">
          <strong>{tx("empty_dashboards_title", "Todavía no tienes tableros")}</strong>
          <p>{tx("empty_dashboards_body", "Crea tu primer tablero para empezar a armar tus gráficos de KPIs.")}</p>
          <button className="button primary" onClick={handleCreateDashboard}><Plus size={16} />{tx("new_dashboard", "Nuevo tablero")}</button>
        </div>
      )}

      {activeDashboard && (
        <div className="kpi-dashboard-body">
          <div className="kpi-dashboard-toolbar">
            <button className="button primary" onClick={() => setWidgetForm({ editing: null })}>
              <Plus size={16} />{tx("add_widget", "Agregar gráfico")}
            </button>
          </div>

          {widgetsError && <div className="alert error">{t(widgetsError, widgetsError)}</div>}
          {loadingWidgets && <div className="alert">{t("common.loading")}</div>}

          {!loadingWidgets && !widgetsError && widgets.length === 0 && (
            <div className="empty">
              <strong>{tx("empty_widgets_title", "Este tablero no tiene gráficos todavía")}</strong>
              <p>{tx("empty_widgets_body", "Usa \"Agregar gráfico\" para elegir un KPI y visualizarlo aquí.")}</p>
            </div>
          )}

          {!loadingWidgets && widgets.length > 0 && (
            <div className="kpi-widget-grid">
              {widgets.map((widget) => (
                <KpiWidgetCard
                  key={widget.id_kpi_dashboard_widget}
                  widget={widget}
                  kpiCatalog={kpiCatalog}
                  userLabel={userLabel}
                  formatNumber={formatNumber}
                  onEdit={() => setWidgetForm({ editing: widget })}
                  onDelete={() => handleDeleteWidget(widget)}
                  t={t}
                  tx={tx}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {widgetForm && (
        <KpiWidgetFormModal
          editing={widgetForm.editing}
          kpiCatalog={kpiCatalog}
          users={users}
          onCancel={() => setWidgetForm(null)}
          onSave={handleSaveWidget}
          t={t}
          tx={tx}
        />
      )}
    </section>
  );
}

function KpiWidgetCard({ widget, kpiCatalog, userLabel, formatNumber, onEdit, onDelete, t, tx }) {
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const kpiInfo = kpiCatalog.find((kpi) => kpi.id_kpi_definition === widget.id_kpi_definition);
  const parametros = widget.parametros || {};
  const fechaInicio = parametros.fecha_inicio;
  const fechaFin = parametros.fecha_fin;
  const fechaInicioB = parametros.fecha_inicio_b;
  const fechaFinB = parametros.fecha_fin_b;
  const empleadosKey = Array.isArray(parametros.empleados) ? parametros.empleados.join(",") : "";

  useEffect(() => {
    let cancelado = false;
    async function cargar() {
      if (!fechaInicio || !fechaFin) {
        setLoading(false);
        setSnapshot(null);
        setError("missing_range");
        return;
      }
      setLoading(true);
      setError("");
      try {
        const params = { id_kpi_definition: widget.id_kpi_definition, fecha_inicio: fechaInicio, fecha_fin: fechaFin };
        if (fechaInicioB && fechaFinB) {
          params.fecha_inicio_b = fechaInicioB;
          params.fecha_fin_b = fechaFinB;
        }
        if (empleadosKey) params.empleados = empleadosKey;
        const data = await queryKpiSnapshot(params);
        if (!cancelado) setSnapshot(data);
      } catch (err) {
        if (!cancelado) { setError(err.message || "errors.request_failed"); setSnapshot(null); }
      } finally {
        if (!cancelado) setLoading(false);
      }
    }
    cargar();
    return () => { cancelado = true; };
  }, [widget.id_kpi_definition, fechaInicio, fechaFin, fechaInicioB, fechaFinB, empleadosKey]);

  const chartTypeLabel = CHART_TYPES.find((opt) => opt.value === widget.tipo_grafica)?.label || widget.tipo_grafica;
  const rangoTexto = fechaInicio && fechaFin ? `${fechaInicio} → ${fechaFin}` : tx("missing_range", "Sin rango de fechas configurado");
  const rangoBTexto = fechaInicioB && fechaFinB ? `${fechaInicioB} → ${fechaFinB}` : "";

  return (
    <article className="kpi-widget-card">
      <div className="kpi-widget-card-header">
        <div>
          <h4>{kpiInfo?.etiqueta || tx("unknown_kpi", `KPI #${widget.id_kpi_definition}`)}</h4>
          <p className="kpi-widget-meta">{tx(`chart_type_${widget.tipo_grafica}`, chartTypeLabel)}</p>
          <p className="kpi-widget-meta">{rangoTexto}</p>
          {rangoBTexto && <p className="kpi-widget-meta">{tx("vs_label", "vs.")} {rangoBTexto}</p>}
        </div>
        <div className="kpi-widget-card-actions">
          <button type="button" className="kpi-icon-button" title={t("common.edit")} onClick={onEdit}><Pencil size={15} /></button>
          <button type="button" className="kpi-icon-button danger" title={t("common.delete")} onClick={onDelete}><Trash2 size={15} /></button>
        </div>
      </div>

      <div className="kpi-chart-box">
        {loading && <p className="kpi-empty-inline">{t("common.loading")}</p>}
        {!loading && error === "missing_range" && (
          <p className="kpi-empty-inline">{tx("widget_missing_range", "A este gráfico le falta un rango de fechas. Edítalo para configurarlo.")}</p>
        )}
        {!loading && error && error !== "missing_range" && (
          <p className="kpi-error-inline">{t(error, error)}</p>
        )}
        {!loading && !error && snapshot && (
          <KpiChartBody widget={widget} snapshot={snapshot} kpiInfo={kpiInfo} userLabel={userLabel} formatNumber={formatNumber} tx={tx} />
        )}
      </div>
    </article>
  );
}

function KpiChartBody({ widget, snapshot, kpiInfo, userLabel, formatNumber, tx }) {
  const hasCompare = Boolean(snapshot?.rango_b);

  if (widget.tipo_grafica === "numero") {
    const total = snapshot.rango_a.total;
    const totalB = snapshot.rango_b?.total;
    const unidad = kpiInfo?.unidad ? ` ${kpiInfo.unidad}` : "";
    const delta = hasCompare ? total - totalB : null;
    const deltaPct = hasCompare && totalB ? (delta / Math.abs(totalB)) * 100 : null;
    return (
      <div className="kpi-number-widget">
        <strong>{formatNumber(total)}{unidad}</strong>
        {delta !== null && (
          <span className={`kpi-delta ${delta >= 0 ? "up" : "down"}`}>
            {delta >= 0 ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
            {formatNumber(Math.abs(delta))}{unidad}
            {deltaPct !== null && Number.isFinite(deltaPct) ? ` (${deltaPct >= 0 ? "+" : ""}${deltaPct.toFixed(1)}%)` : ""}
            {" "}{tx("vs_compare", "vs. periodo anterior")}
          </span>
        )}
      </div>
    );
  }

  if (widget.tipo_grafica === "dona") {
    const data = buildPieData(snapshot, userLabel, tx("others", "Otros"));
    if (!data.length) return <p className="kpi-empty-inline">{tx("no_data", "Sin datos en el rango seleccionado.")}</p>;
    return (
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Tooltip formatter={(value) => formatNumber(value)} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Pie data={data} dataKey="value" nameKey="name" innerRadius="55%" outerRadius="80%" paddingAngle={2}>
            {data.map((entry, index) => (
              <Cell key={entry.name} fill={index < CATEGORICAL.length ? CATEGORICAL[index] : COLOR_OTHERS} stroke="#fff" strokeWidth={2} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    );
  }

  const data = buildSeriesData(snapshot, userLabel, widget.parametros?.empleados);
  if (!data.length) return <p className="kpi-empty-inline">{tx("no_data", "Sin datos en el rango seleccionado.")}</p>;

  if (widget.tipo_grafica === "barras") {
    return (
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e1e0d9" vertical={false} />
          <XAxis dataKey="name" tick={AXIS_TICK} axisLine={{ stroke: "#c3c2b7" }} tickLine={false} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={44} />
          <Tooltip formatter={(value) => formatNumber(value)} />
          {hasCompare && <Legend wrapperStyle={{ fontSize: 12 }} />}
          <Bar dataKey="a" name={tx("range_a", "Periodo A")} fill={COLOR_A} radius={[4, 4, 0, 0]} />
          {hasCompare && <Bar dataKey="b" name={tx("range_b", "Periodo B")} fill={COLOR_B} radius={[4, 4, 0, 0]} />}
        </BarChart>
      </ResponsiveContainer>
    );
  }

  if (widget.tipo_grafica === "linea") {
    return (
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e1e0d9" vertical={false} />
          <XAxis dataKey="name" tick={AXIS_TICK} axisLine={{ stroke: "#c3c2b7" }} tickLine={false} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={44} />
          <Tooltip formatter={(value) => formatNumber(value)} />
          {hasCompare && <Legend wrapperStyle={{ fontSize: 12 }} />}
          <Line type="monotone" dataKey="a" name={tx("range_a", "Periodo A")} stroke={COLOR_A} strokeWidth={2} dot={{ r: 4 }} />
          {hasCompare && <Line type="monotone" dataKey="b" name={tx("range_b", "Periodo B")} stroke={COLOR_B} strokeWidth={2} dot={{ r: 4 }} />}
        </LineChart>
      </ResponsiveContainer>
    );
  }

  if (widget.tipo_grafica === "area") {
    return (
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e1e0d9" vertical={false} />
          <XAxis dataKey="name" tick={AXIS_TICK} axisLine={{ stroke: "#c3c2b7" }} tickLine={false} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={44} />
          <Tooltip formatter={(value) => formatNumber(value)} />
          {hasCompare && <Legend wrapperStyle={{ fontSize: 12 }} />}
          <Area type="monotone" dataKey="a" name={tx("range_a", "Periodo A")} stroke={COLOR_A} fill={COLOR_A} fillOpacity={0.25} strokeWidth={2} />
          {hasCompare && <Area type="monotone" dataKey="b" name={tx("range_b", "Periodo B")} stroke={COLOR_B} fill={COLOR_B} fillOpacity={0.25} strokeWidth={2} />}
        </AreaChart>
      </ResponsiveContainer>
    );
  }

  return null;
}

function KpiWidgetFormModal({ editing, kpiCatalog, users, onCancel, onSave, t, tx }) {
  const parametrosIniciales = editing?.parametros || {};
  const [idKpiDefinition, setIdKpiDefinition] = useState(editing?.id_kpi_definition ? String(editing.id_kpi_definition) : "");
  const [tipoGrafica, setTipoGrafica] = useState(editing?.tipo_grafica || "numero");
  const [fechaInicio, setFechaInicio] = useState(parametrosIniciales.fecha_inicio || daysAgoIso(30));
  const [fechaFin, setFechaFin] = useState(parametrosIniciales.fecha_fin || todayIso());
  const [comparar, setComparar] = useState(Boolean(parametrosIniciales.fecha_inicio_b && parametrosIniciales.fecha_fin_b));
  const [fechaInicioB, setFechaInicioB] = useState(parametrosIniciales.fecha_inicio_b || "");
  const [fechaFinB, setFechaFinB] = useState(parametrosIniciales.fecha_fin_b || "");
  const [empleadosSeleccionados, setEmpleadosSeleccionados] = useState(
    Array.isArray(parametrosIniciales.empleados) ? parametrosIniciales.empleados.map(String) : [],
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function toggleEmpleado(idUser) {
    setEmpleadosSeleccionados((prev) => (prev.includes(idUser) ? prev.filter((item) => item !== idUser) : [...prev, idUser]));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    if (!idKpiDefinition) { setError(tx("kpi_required", "Elige un KPI.")); return; }
    if (!fechaInicio || !fechaFin) { setError(tx("range_required", "Elige el rango de fechas.")); return; }
    if (comparar && (!fechaInicioB || !fechaFinB)) { setError(tx("range_b_required", "Elige el rango de comparación o desactívala.")); return; }

    const parametros = { fecha_inicio: fechaInicio, fecha_fin: fechaFin };
    if (comparar) { parametros.fecha_inicio_b = fechaInicioB; parametros.fecha_fin_b = fechaFinB; }
    if (empleadosSeleccionados.length) parametros.empleados = empleadosSeleccionados.map(Number);

    const payload = { id_kpi_definition: Number(idKpiDefinition), tipo_grafica: tipoGrafica, parametros };
    setSaving(true);
    try {
      await onSave(payload, editing);
    } catch (err) {
      setError(t(err.message || "errors.request_failed", err.message || "errors.request_failed"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="kpi-modal-backdrop" role="presentation">
      <form className="kpi-modal" onSubmit={handleSubmit}>
        <header>
          <div>
            <p className="eyebrow">{tx("widget", "Gráfico")}</p>
            <h3>{editing ? tx("edit_widget", "Editar gráfico") : tx("add_widget", "Agregar gráfico")}</h3>
          </div>
          <button type="button" className="kpi-icon-button" onClick={onCancel} aria-label={t("common.cancel")}><X size={18} /></button>
        </header>

        {kpiCatalog.length === 0 ? (
          <div className="empty">
            <strong>{tx("no_kpis_title", "No tienes KPIs asignados")}</strong>
            <p>{tx("no_kpis_body", "Pide a un administrador que te asigne permiso sobre algún KPI para poder graficarlo aquí.")}</p>
          </div>
        ) : (
          <>
            <div className="form-grid">
              <label className="field">
                <span>{tx("kpi", "KPI")}</span>
                <select value={idKpiDefinition} onChange={(event) => setIdKpiDefinition(event.target.value)} required>
                  <option value="">{tx("select_kpi", "Selecciona un KPI")}</option>
                  {kpiCatalog.map((kpi) => (
                    <option key={kpi.id_kpi_definition} value={kpi.id_kpi_definition}>{kpi.etiqueta || kpi.clave}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>{tx("chart_type", "Tipo de gráfico")}</span>
                <select value={tipoGrafica} onChange={(event) => setTipoGrafica(event.target.value)}>
                  {CHART_TYPES.map((opt) => (
                    <option key={opt.value} value={opt.value}>{tx(`chart_type_${opt.value}`, opt.label)}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>{tx("start_date", "Fecha inicio")}</span>
                <input type="date" value={fechaInicio} max={fechaFin || undefined} onChange={(event) => setFechaInicio(event.target.value)} required />
              </label>
              <label className="field">
                <span>{tx("end_date", "Fecha fin")}</span>
                <input type="date" value={fechaFin} min={fechaInicio || undefined} onChange={(event) => setFechaFin(event.target.value)} required />
              </label>
            </div>

            <label className="field checkbox-field">
              <input type="checkbox" checked={comparar} onChange={(event) => setComparar(event.target.checked)} />
              <span>{tx("compare_toggle", "Comparar contra otro periodo")}</span>
            </label>

            {comparar && (
              <div className="form-grid">
                <label className="field">
                  <span>{tx("start_date_b", "Fecha inicio (comparación)")}</span>
                  <input type="date" value={fechaInicioB} max={fechaFinB || undefined} onChange={(event) => setFechaInicioB(event.target.value)} required={comparar} />
                </label>
                <label className="field">
                  <span>{tx("end_date_b", "Fecha fin (comparación)")}</span>
                  <input type="date" value={fechaFinB} min={fechaInicioB || undefined} onChange={(event) => setFechaFinB(event.target.value)} required={comparar} />
                </label>
              </div>
            )}

            {users.length > 0 && (
              <div className="kpi-employee-picker">
                <span className="kpi-employee-picker-label">{tx("employees_filter", "Filtrar por empleados (opcional)")}</span>
                <div className="kpi-employee-list">
                  {users.map((user) => (
                    <label className="kpi-employee-chip" key={user.id_user}>
                      <input
                        type="checkbox"
                        checked={empleadosSeleccionados.includes(String(user.id_user))}
                        onChange={() => toggleEmpleado(String(user.id_user))}
                      />
                      <span>{user.full_name || user.username || `#${user.id_user}`}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {error && <div className="alert error">{error}</div>}

        <footer>
          <button type="button" className="button" onClick={onCancel}>{t("common.cancel")}</button>
          {kpiCatalog.length > 0 && <button type="submit" className="button primary" disabled={saving}>{t("common.save")}</button>}
        </footer>
      </form>
    </div>
  );
}
