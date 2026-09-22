import { useEffect, useMemo, useState } from "react";
import { BarChart2, ShieldCheck } from "lucide-react";
import {
  getAllPermission,
  getAllKpiDefinitionUnfiltered,
  getPermissionKpi,
  createPermissionKpi,
  deletePermissionKpi
} from "../api";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader.jsx";

function asItems(payload) {
  if (Array.isArray(payload)) return payload;
  return payload?.items || payload?.data || payload?.records || [];
}

// Mismo fallback que ya usa `kpiModuleMeta` en Dashboard.jsx para un modulo
// sin meta propia: no se inventa una segunda tabla de iconos/etiquetas por
// modulo, solo se capitaliza la clave cruda ("facturacion" -> "Facturacion").
function humanizeModule(modulo) {
  return modulo ? modulo.charAt(0).toUpperCase() + modulo.slice(1) : "";
}

/**
 * Gestor de permisos por KPI (nm_permission_kpi): que rol ve que KPI del
 * dashboard. Sistema aparte del alcance CRUD (Propios/Mis grupos/Todos) de
 * `entity_permission` que administra RolePermissionManagerPage -- aqui solo
 * existe "ve" o "no ve" (`puede_ver`), sin niveles de alcance.
 */
export default function KpiPermissionManagerPage() {
  const { t } = useI18n();
  const [roles, setRoles] = useState([]);
  const [kpis, setKpis] = useState([]);
  const [selectedRoleId, setSelectedRoleId] = useState("");
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingAssignments, setLoadingAssignments] = useState(false);
  const [pendingKpiIds, setPendingKpiIds] = useState(() => new Set());
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true); setError("");
      try {
        const [rolesPayload, kpisPayload] = await Promise.all([
          getAllPermission({ per_page: 500 }),
          getAllKpiDefinitionUnfiltered()
        ]);
        if (!mounted) return;
        setRoles(asItems(rolesPayload));
        setKpis(asItems(kpisPayload));
      } catch (err) {
        if (mounted) setError(t(err.message, err.message || "No se pudo cargar el gestor"));
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    let mounted = true;
    async function loadAssignments() {
      if (!selectedRoleId) { setAssignments([]); return; }
      setLoadingAssignments(true); setError("");
      try {
        const payload = await getPermissionKpi(selectedRoleId);
        if (mounted) setAssignments(asItems(payload));
      } catch (err) {
        if (mounted) setError(t(err.message, err.message || "No se pudieron cargar los KPIs de este rol"));
      } finally {
        if (mounted) setLoadingAssignments(false);
      }
    }
    loadAssignments();
    return () => { mounted = false; };
  }, [selectedRoleId]);

  const roleOptions = useMemo(() => roles.map((role) => ({
    id: role.id_permission,
    label: role.permission_description || role.name || role.description || `#${role.id_permission}`
  })).filter((role) => role.id !== undefined && role.id !== null), [roles]);

  const assignmentByKpiId = useMemo(() => {
    const map = new Map();
    assignments.forEach((row) => map.set(Number(row.id_kpi_definition), row));
    return map;
  }, [assignments]);

  const kpisByModule = useMemo(() => {
    const groups = new Map();
    kpis.forEach((kpi) => {
      const moduleName = kpi.modulo || "";
      if (!groups.has(moduleName)) groups.set(moduleName, []);
      groups.get(moduleName).push(kpi);
    });
    return [...groups.entries()]
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([moduleName, items]) => ({
        moduleName,
        items: [...items].sort((left, right) => String(left.etiqueta || "").localeCompare(String(right.etiqueta || "")))
      }));
  }, [kpis]);

  async function toggleKpi(kpi, currentlyVisible) {
    if (!selectedRoleId) return;
    const roleId = Number(selectedRoleId);
    const kpiId = Number(kpi.id_kpi_definition);
    if (pendingKpiIds.has(kpiId)) return;

    const existing = assignmentByKpiId.get(kpiId) || null;
    setPendingKpiIds((prev) => new Set(prev).add(kpiId));
    setError(""); setNotice("");

    // Optimista: refleja el cambio de inmediato, revierte si la llamada falla.
    if (currentlyVisible) {
      setAssignments((prev) => prev.filter((row) => Number(row.id_kpi_definition) !== kpiId));
    } else {
      setAssignments((prev) => [...prev, { id_permission: roleId, id_kpi_definition: kpiId, puede_ver: true, id_nm_permission_kpi: null }]);
    }

    try {
      if (currentlyVisible) {
        if (existing?.id_nm_permission_kpi) await deletePermissionKpi(existing.id_nm_permission_kpi);
      } else {
        const created = await createPermissionKpi({ id_permission: roleId, id_kpi_definition: kpiId });
        setAssignments((prev) => prev.map((row) => (Number(row.id_kpi_definition) === kpiId ? created : row)));
      }
    } catch (err) {
      if (currentlyVisible) {
        setAssignments((prev) => [...prev, existing]);
      } else {
        setAssignments((prev) => prev.filter((row) => Number(row.id_kpi_definition) !== kpiId));
      }
      setError(t(err.message, err.message || "No se pudo actualizar el permiso del KPI"));
    } finally {
      setPendingKpiIds((prev) => { const next = new Set(prev); next.delete(kpiId); return next; });
    }
  }

  return (
    <section className="entity-page kpi-permission-manager">
      <PageHeader
        eyebrow={"RBAC"}
        titulo={t("common.kpi_permission_manager", "Permisos de KPIs")}
        subtitulo={t("common.kpi_permission_manager_body", "Elige qué KPIs del panel puede ver cada rol.")}
      />

      {notice && <div className="alert success">{notice}</div>}
      {error && <div className="alert error">{error}</div>}

      <article className="form-card">
        <div className="form-header"><ShieldCheck size={20} /><strong>{t("common.role", "Rol/perfil")}</strong></div>
        <div className="form-grid">
          <label className="field">
            <span>{t("common.select_role", "Seleccionar rol/perfil")}</span>
            <select value={selectedRoleId} onChange={(event) => setSelectedRoleId(event.target.value)} disabled={loading}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {roleOptions.map((role) => <option key={role.id} value={role.id}>{role.label}</option>)}
            </select>
          </label>
        </div>
      </article>

      <article className="table-card field-permission-panel">
        <div className="form-header"><BarChart2 size={20} /><strong>{t("common.kpi_catalog", "KPIs disponibles")}</strong></div>
        {loading ? (
          <div className="empty">{t("common.loading", "Cargando...")}</div>
        ) : !selectedRoleId ? (
          <div className="empty">{t("common.select_role", "Selecciona un rol/perfil")}</div>
        ) : loadingAssignments ? (
          <div className="empty">{t("common.loading", "Cargando...")}</div>
        ) : (
          <div className="field-permission-list kpi-permission-list">
            {kpisByModule.length === 0 && <div className="empty">{t("common.no_kpis_available", "No hay KPIs en el catálogo.")}</div>}
            {kpisByModule.map((group) => (
              <div className="kpi-permission-group" key={group.moduleName || "sin-modulo"}>
                <h4>{humanizeModule(group.moduleName) || t("common.no_module", "Sin módulo")}</h4>
                <div className="kpi-permission-header"><span>{t("common.kpi", "KPI")}</span><span>{t("common.visible", "Ver")}</span></div>
                {group.items.map((kpi) => {
                  const kpiId = Number(kpi.id_kpi_definition);
                  const visible = assignmentByKpiId.has(kpiId);
                  const pending = pendingKpiIds.has(kpiId);
                  return (
                    <div className="kpi-permission-row" key={kpiId}>
                      <span>{kpi.etiqueta || kpi.clave}</span>
                      <label className="checkbox-inline">
                        <input
                          type="checkbox"
                          checked={visible}
                          disabled={pending}
                          onChange={() => toggleKpi(kpi, visible)}
                          aria-label={`${t("common.visible", "Ver")} ${kpi.etiqueta || kpi.clave}`}
                        />
                      </label>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        )}
      </article>
    </section>
  );
}
