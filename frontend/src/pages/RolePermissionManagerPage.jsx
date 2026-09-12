import { useEffect, useMemo, useState } from "react";
import { Boxes, ClipboardList, FileText, Landmark, LayoutDashboard, Plus, Pencil, Save, Search, Settings, ShieldCheck, SlidersHorizontal, Trash2, Users, Utensils, X } from "lucide-react";
import {
  getPermissionCatalog,
  getAllPermission,
  createPermission,
  updatePermission,
  deletePermission,
  getAllEntityPermission,
  createEntityPermission,
  updateEntityPermission,
  deleteEntityPermission,
  getAllField,
  createField,
  getAllNmFieldPermission,
  createNmFieldPermission,
  updateNmFieldPermission,
  deleteNmFieldPermission,
  getAllUser,
  getAllDepartment,
  getAllSubdepartment,
  getAllLevel
} from "../api";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader.jsx";
import { fetchAllPages } from "../utils/fetchAllPages";

const ENTITY_ACTIONS = [
  { key: "create", bit: 1, label: "Crear" },
  { key: "read", bit: 2, label: "Leer" },
  { key: "update", bit: 4, label: "Actualizar" },
  { key: "delete", bit: 8, label: "Eliminar" }
];

const FIELD_VISIBLE_BIT = 2;
const INTERNAL_PERMISSION_ENTITIES = new Set(["entity_permission", "nm_field_permission", "user_mfa", "event_log"]);
const SYSTEM_FIELD_NAMES = new Set(["created_by", "creation_date", "last_update_date", "deletion_date"]);
const GROUP_ICON_OPTIONS = [
  { id: "landmark", label: "Banco", Icon: Landmark },
  { id: "file-text", label: "Documento", Icon: FileText },
  { id: "users", label: "Personas", Icon: Users },
  { id: "utensils", label: "Restaurante", Icon: Utensils },
  { id: "clipboard-list", label: "Operaciones", Icon: ClipboardList },
  { id: "boxes", label: "Inventario", Icon: Boxes },
  { id: "sliders-horizontal", label: "Controles", Icon: SlidersHorizontal },
  { id: "shield-check", label: "Seguridad", Icon: ShieldCheck },
  { id: "layout-dashboard", label: "Panel", Icon: LayoutDashboard },
  { id: "settings", label: "Configuración", Icon: Settings }
];
const DEFAULT_GROUP_ICON_IDS = {
  "Bancos": "landmark",
  "Contabilidad": "file-text",
  "Recursos humanos": "users",
  "Restaurante": "utensils",
  "Operaciones": "clipboard-list",
  "Inventario": "boxes",
  "Configuración": "sliders-horizontal"
};

function asItems(payload) {
  if (Array.isArray(payload)) return payload;
  return payload?.items || payload?.data || payload?.records || [];
}

function getEntityName(item) {
  return item?.entity_name || item?.table_name || item?.name || "";
}

function getFieldName(item) {
  return item?.field_name || item?.attributes_en || item?.name || "";
}

function normalizeKey(value) {
  return String(value || "").trim().toLowerCase();
}

function fieldRegistryKey(entityName, fieldName) {
  return `${normalizeKey(entityName)}.${normalizeKey(fieldName)}`;
}

function humanizeLabel(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function hasBit(value, bit) {
  return (Number(value || 0) & bit) === bit;
}

function toggleBit(value, bit) {
  const current = Number(value || 0);
  return hasBit(current, bit) ? current & ~bit : current | bit;
}

function getFieldKey(field) {
  const entityName = field?.entity_name || field?.table_name || "";
  const fieldName = getFieldName(field);
  return `virtual:${fieldRegistryKey(entityName, fieldName)}`;
}

function getFieldId(field) {
  return field?.id_field ?? field?.id ?? null;
}

export default function RolePermissionManagerPage() {
  const { t } = useI18n();
  const currentUser = JSON.parse(localStorage.getItem("user") || "null");
  const [catalog, setCatalog] = useState([]);
  const [roles, setRoles] = useState([]);
  const [fields, setFields] = useState([]);
  const [entityPermissions, setEntityPermissions] = useState([]);
  const [fieldPermissions, setFieldPermissions] = useState([]);
  const [users, setUsers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [subdepartments, setSubdepartments] = useState([]);
  const [levels, setLevels] = useState([]);
  const [selectedRoleId, setSelectedRoleId] = useState("");
  const [selectedEntity, setSelectedEntity] = useState("");
  const [entityMatrix, setEntityMatrix] = useState({});
  const [navigationMatrix, setNavigationMatrix] = useState({});
  const [fieldMatrix, setFieldMatrix] = useState({});
  const [roleFormOpen, setRoleFormOpen] = useState(false);
  const [editingRoleId, setEditingRoleId] = useState(null);
  const [roleForm, setRoleForm] = useState({ permission_description: "", authorized_by: "", id_department: "", id_subdepartment: "", id_level: "" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingRole, setSavingRole] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [moduleFilter, setModuleFilter] = useState("");
  const [groupFilter, setGroupFilter] = useState("");

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true); setError("");
      try {
        const [catalogPayload, rolesPayload, entityPermPayload, fieldPayload, fieldPermPayload, usersPayload, departmentsPayload, subdepartmentsPayload, levelsPayload] = await Promise.all([
          getPermissionCatalog(),
          getAllPermission({ per_page: 500 }),
          fetchAllPages(getAllEntityPermission),
          fetchAllPages(getAllField),
          fetchAllPages(getAllNmFieldPermission),
          getAllUser({ per_page: 500 }),
          getAllDepartment({ per_page: 500 }),
          getAllSubdepartment({ per_page: 500 }),
          getAllLevel({ per_page: 500 })
        ]);
        if (!mounted) return;
        const nextCatalog = asItems(catalogPayload?.entities || catalogPayload).filter((item) => {
          const name = getEntityName(item);
          return name && !INTERNAL_PERMISSION_ENTITIES.has(name);
        });
        const nextRoles = asItems(rolesPayload);
        setCatalog(nextCatalog);
        setRoles(nextRoles);
        setEntityPermissions(asItems(entityPermPayload));
        setFields(asItems(fieldPayload));
        setFieldPermissions(asItems(fieldPermPayload));
        setUsers(asItems(usersPayload));
        setDepartments(asItems(departmentsPayload));
        setSubdepartments(asItems(subdepartmentsPayload));
        setLevels(asItems(levelsPayload));
        if (!selectedEntity && nextCatalog.length) setSelectedEntity(getEntityName(nextCatalog[0]));
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
    if (!selectedRoleId) {
      setEntityMatrix({}); setNavigationMatrix({}); setFieldMatrix({});
      return;
    }
    const roleId = Number(selectedRoleId);
    const nextEntityMatrix = {};
    const nextNavigationMatrix = {};
    entityPermissions.filter((row) => Number(row.id_permission) === roleId).forEach((row) => {
      nextEntityMatrix[row.entity_name] = Number(row.control_type || 0);
      nextNavigationMatrix[row.entity_name] = {
        menu_location: row.menu_location || "sidebar",
        menu_group: row.menu_group || "",
        menu_group_icon: row.menu_group_icon || "",
        menu_label: row.menu_label || "",
        menu_order: Number(row.menu_order ?? 100)
      };
    });
    const fieldsById = new Map();
    fields.forEach((field) => {
      const id = field.id_field ?? field.id;
      const table = field.table_name || field.entity_name || field.table || "";
      const name = getFieldName(field);
      if (id && table && name) fieldsById.set(Number(id), { table, name });
    });
    const nextFieldMatrix = {};
    fieldPermissions.filter((row) => Number(row.id_permission) === roleId).forEach((row) => {
      const registry = fieldsById.get(Number(row.id_field));
      if (registry) nextFieldMatrix[`virtual:${fieldRegistryKey(registry.table, registry.name)}`] = Number(row.control_type || 0);
    });
    setEntityMatrix(nextEntityMatrix);
    setNavigationMatrix(nextNavigationMatrix);
    setFieldMatrix(nextFieldMatrix);
  }, [selectedRoleId, entityPermissions, fieldPermissions, fields]);

  const roleOptions = useMemo(() => roles.map((role) => ({
    id: role.id_permission,
    label: role.permission_description || role.name || role.description || `#${role.id_permission}`,
    source: role
  })).filter((role) => role.id !== undefined && role.id !== null), [roles]);

  const selectedCatalogEntity = useMemo(() => catalog.find((item) => getEntityName(item) === selectedEntity), [catalog, selectedEntity]);

  const fieldsByKey = useMemo(() => {
    const map = new Map();
    fields.forEach((field) => {
      const table = field.table_name || field.entity_name || field.table || "";
      const name = getFieldName(field);
      if (!table || !name) return;
      const key = fieldRegistryKey(table, name);
      map.set(key, field);
    });
    return map;
  }, [fields]);

  const catalogFieldsForEntity = (entityName) => {
    const entity = catalog.find((item) => getEntityName(item) === entityName);
    const catalogFields = entity?.fields || [];
    const seen = new Set();
    return catalogFields
      .filter((field) => {
        const name = getFieldName(field);
        const sourceEntity = field.entity_name || field.table_name || entityName;
        if (!name || !entityName) return false;
        if (normalizeKey(sourceEntity) !== normalizeKey(entityName)) return false;
        if (name === "supervisor" && entityName !== "user") return false;
        if (field.is_primary || field.is_system_field || SYSTEM_FIELD_NAMES.has(name)) return false;
        const key = fieldRegistryKey(entityName, name);
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .map((field) => {
        const name = getFieldName(field);
        const registry = fieldsByKey.get(fieldRegistryKey(entityName, name)) || {};
        const idField = field.id_field || registry.id_field || registry.id;
        return { ...field, entity_name: entityName, table_name: entityName, field_name: name, id_field: idField };
      });
  };

  const selectedFields = useMemo(() => catalogFieldsForEntity(selectedEntity), [catalog, fieldsByKey, selectedEntity]);
  const selectedEntityUsesActionsOnly = selectedCatalogEntity?.permission_scope === "actions_only";

  const navigationGroups = useMemo(() => {
    const groups = new Map();
    catalog.forEach((entity) => {
      const entityName = getEntityName(entity);
      const navigation = navigationMatrix[entityName] || {};
      const groupName = String(navigation.menu_group || "").trim();
      if (!groupName || Number(entityMatrix[entityName] || 0) <= 0 || (navigation.menu_location || "sidebar") !== "sidebar") return;
      const current = groups.get(groupName) || {
        name: groupName,
        icon: navigation.menu_group_icon || DEFAULT_GROUP_ICON_IDS[groupName] || "sliders-horizontal",
        modules: 0
      };
      current.modules += 1;
      if (navigation.menu_group_icon) current.icon = navigation.menu_group_icon;
      groups.set(groupName, current);
    });
    return [...groups.values()].sort((left, right) => left.name.localeCompare(right.name));
  }, [catalog, entityMatrix, navigationMatrix]);

  const moduleGroupOptions = useMemo(() => {
    const groups = new Set();
    let hasUngroupedModules = false;
    catalog.forEach((entity) => {
      const entityName = getEntityName(entity);
      const groupName = String(navigationMatrix[entityName]?.menu_group || "").trim();
      if (groupName) groups.add(groupName);
      else hasUngroupedModules = true;
    });
    return {
      groups: [...groups].sort((left, right) => left.localeCompare(right)),
      hasUngroupedModules
    };
  }, [catalog, navigationMatrix]);

  const filteredCatalog = useMemo(() => {
    const needle = normalizeKey(moduleFilter);
    return catalog
      .filter((entity) => {
        const entityName = getEntityName(entity);
        const navigation = navigationMatrix[entityName] || {};
        const groupName = String(navigation.menu_group || "").trim();
        const label = navigation.menu_label || t(`menu.${entityName}`, entity?.label || humanizeLabel(entityName));
        const matchesModule = !needle || [entityName, label].some((value) => normalizeKey(value).includes(needle));
        const matchesGroup = !groupFilter || (groupFilter === "__ungrouped__" ? !groupName : groupName === groupFilter);
        return matchesModule && matchesGroup;
      })
      .sort((left, right) => {
        const leftName = getEntityName(left);
        const rightName = getEntityName(right);
        const leftNavigation = navigationMatrix[leftName] || {};
        const rightNavigation = navigationMatrix[rightName] || {};
        const groupComparison = String(leftNavigation.menu_group || "").localeCompare(String(rightNavigation.menu_group || ""));
        if (groupComparison) return groupComparison;
          const leftLabel = leftNavigation.menu_label || t(`menu.${leftName}`, left?.label || humanizeLabel(leftName));
          const rightLabel = rightNavigation.menu_label || t(`menu.${rightName}`, right?.label || humanizeLabel(rightName));
          return String(leftLabel).localeCompare(String(rightLabel));
      });
        }, [catalog, groupFilter, moduleFilter, navigationMatrix, t]);

  const allManagedFields = useMemo(() => {
    const rows = [];
    catalog.forEach((entity) => rows.push(...catalogFieldsForEntity(getEntityName(entity))));
    return rows;
  }, [catalog, fieldsByKey]);

  function roleIdNumber() { return Number(selectedRoleId); }

  function roleLabel(role) {
    return role.permission_description || role.name || role.description || `#${role.id_permission}`;
  }

  function defaultRoleForm() {
    const currentUserId = currentUser?.id_user || currentUser?.id || "";
    return {
      permission_description: "",
      authorized_by: currentUserId || users[0]?.id_user || users[0]?.id || "",
      id_department: departments[0]?.id_department || departments[0]?.id || "",
      id_subdepartment: subdepartments[0]?.id_subdepartment || subdepartments[0]?.id || "",
      id_level: levels[0]?.id_level || levels[0]?.id || ""
    };
  }

  function openNewRole() {
    setEditingRoleId(null);
    setRoleForm(defaultRoleForm());
    setRoleFormOpen(true);
    setNotice(""); setError("");
  }

  function openEditRole() {
    const selected = roles.find((role) => Number(role.id_permission) === Number(selectedRoleId));
    if (!selected) { setError(t("errors.validation_failed", "Selecciona un rol/perfil")); return; }
    setEditingRoleId(selected.id_permission);
    setRoleForm({
      permission_description: selected.permission_description || "",
      authorized_by: selected.authorized_by || defaultRoleForm().authorized_by,
      id_department: selected.id_department || defaultRoleForm().id_department,
      id_subdepartment: selected.id_subdepartment || defaultRoleForm().id_subdepartment,
      id_level: selected.id_level || defaultRoleForm().id_level
    });
    setRoleFormOpen(true);
    setNotice(""); setError("");
  }

  async function refreshRoles(nextSelectedId = selectedRoleId) {
    const payload = await getAllPermission({ per_page: 500 });
    const nextRoles = asItems(payload);
    setRoles(nextRoles);
    if (nextSelectedId) setSelectedRoleId(String(nextSelectedId));
  }

  async function handleSaveRole(event) {
    event.preventDefault();
    if (!roleForm.permission_description || !roleForm.authorized_by || !roleForm.id_department || !roleForm.id_subdepartment || !roleForm.id_level) {
      setError(t("errors.validation_failed", "Completa los campos obligatorios"));
      return;
    }
    setSavingRole(true); setError(""); setNotice("");
    try {
      const payload = {
        permission_description: roleForm.permission_description,
        authorized_by: Number(roleForm.authorized_by),
        id_department: Number(roleForm.id_department),
        id_subdepartment: Number(roleForm.id_subdepartment),
        id_level: Number(roleForm.id_level)
      };
      let saved = null;
      if (editingRoleId) saved = await updatePermission(editingRoleId, payload);
      else saved = await createPermission(payload);
      const nextId = saved?.id_permission || editingRoleId;
      await refreshRoles(nextId);
      setRoleFormOpen(false);
      setNotice(t("common.role_saved", "Rol guardado correctamente"));
    } catch (err) {
      setError(t(err.message, err.message || "No se pudo guardar el rol"));
    } finally {
      setSavingRole(false);
    }
  }

  async function handleDeleteRole() {
    if (!selectedRoleId) {
      setError(t("errors.validation_failed", "Selecciona un rol/perfil"));
      return;
    }
    const selected = roles.find((role) => Number(role.id_permission) === Number(selectedRoleId));
    const label = selected ? roleLabel(selected) : selectedRoleId;
    if (!window.confirm(t("common.confirm_delete_role", `¿Eliminar rol ${label}? Se eliminarán también sus permisos configurados.`))) return;
    setSavingRole(true); setError(""); setNotice("");
    try {
      const roleId = Number(selectedRoleId);
      const fieldRows = fieldPermissions.filter((row) => Number(row.id_permission) === roleId);
      const entityRows = entityPermissions.filter((row) => Number(row.id_permission) === roleId);
      for (const row of fieldRows) {
        if (row.id_nm_field_permission) await deleteNmFieldPermission(row.id_nm_field_permission);
      }
      for (const row of entityRows) {
        if (row.id_entity_permission) await deleteEntityPermission(row.id_entity_permission);
      }
      await deletePermission(roleId);
      setSelectedRoleId("");
      setEntityMatrix({});
      setFieldMatrix({});
      setRoleFormOpen(false);
      await refreshRoles("");
      const [entityPermPayload, fieldPermPayload] = await Promise.all([
        fetchAllPages(getAllEntityPermission),
        fetchAllPages(getAllNmFieldPermission)
      ]);
      setEntityPermissions(asItems(entityPermPayload));
      setFieldPermissions(asItems(fieldPermPayload));
      setNotice(t("common.role_deleted", "Rol eliminado correctamente"));
    } catch (err) {
      setError(t(err.message, err.message || "No se pudo eliminar el rol"));
    } finally {
      setSavingRole(false);
    }
  }

  function clearFieldsForEntity(entityName) {
    const fieldKeys = catalogFieldsForEntity(entityName).map((field) => getFieldKey(field));
    if (!fieldKeys.length) return;
    setFieldMatrix((prev) => {
      const next = { ...prev };
      fieldKeys.forEach((fieldKey) => { delete next[fieldKey]; });
      return next;
    });
  }

  function setEntityBit(entityName, bit) {
    setEntityMatrix((prev) => {
      const nextValue = toggleBit(prev[entityName], bit);
      if (nextValue === 0) clearFieldsForEntity(entityName);
      return { ...prev, [entityName]: nextValue };
    });
    setSelectedEntity(entityName);
  }

  function setNavigationValue(entityName, field, value) {
    setNavigationMatrix((prev) => ({
      ...prev,
      [entityName]: {
        menu_location: "sidebar",
        menu_group: "",
        menu_group_icon: "",
        menu_label: "",
        menu_order: 100,
        ...(prev[entityName] || {}),
        [field]: field === "menu_order" ? Number(value || 0) : value
      }
    }));
  }

  function updateNavigationGroup(groupName, changes) {
    setNavigationMatrix((prev) => {
      const next = { ...prev };
      Object.entries(prev).forEach(([entityName, navigation]) => {
        if (String(navigation.menu_group || "").trim() !== groupName) return;
        next[entityName] = { ...navigation, ...changes };
      });
      return next;
    });
  }

  function setFieldVisible(fieldKey) {
    if (!fieldKey) return;
    setFieldMatrix((prev) => {
      const isVisible = hasBit(prev[fieldKey], FIELD_VISIBLE_BIT);
      return { ...prev, [fieldKey]: isVisible ? 0 : FIELD_VISIBLE_BIT };
    });
  }

  function setAllFieldsForSelectedEntity(visible) {
    if (!selectedRoleId || !selectedEntity || Number(entityMatrix[selectedEntity] || 0) <= 0) return;
    const fieldKeys = selectedFields.map((field) => getFieldKey(field));
    setFieldMatrix((prev) => {
      const next = { ...prev };
      fieldKeys.forEach((fieldKey) => {
        if (visible) next[fieldKey] = FIELD_VISIBLE_BIT;
        else delete next[fieldKey];
      });
      return next;
    });
  }

  function applyBulkEntityAction(actionKey) {
    if (!selectedRoleId || !actionKey) return;
    const actionValues = {
      all_crud: 15,
      clear_everything: 0,
      only_read: 2,
      only_create: 1,
      only_update: 4,
      only_delete: 8
    };
    if (!(actionKey in actionValues)) return;
    const nextValue = actionValues[actionKey];
    setEntityMatrix((prev) => {
      const next = { ...prev };
      catalog.forEach((entity) => {
        const entityName = getEntityName(entity);
        if (entityName) next[entityName] = nextValue;
      });
      return next;
    });
    if (nextValue === 0) {
      setFieldMatrix((prev) => {
        const next = { ...prev };
        allManagedFields.forEach((field) => { delete next[getFieldKey(field)]; });
        return next;
      });
    }
  }

  function validateVisibleFieldsBeforeSave() {
    const invalidEntities = [];
    catalog.forEach((entity) => {
      const entityName = getEntityName(entity);
      const controlType = Number(entityMatrix[entityName] || 0);
      if (!entityName || controlType <= 0) return;
      const entityFields = catalogFieldsForEntity(entityName);
      if (!entityFields.length) return;
      const visibleCount = entityFields.filter((field) => hasBit(fieldMatrix[getFieldKey(field)], FIELD_VISIBLE_BIT)).length;
      if (visibleCount === 0) invalidEntities.push(entityLabel(entity));
    });
    if (invalidEntities.length) {
      setError(t(
        "errors.role_module_without_visible_fields",
        `Selecciona al menos un campo visible para estos módulos antes de guardar: ${invalidEntities.join(", ")}. También puedes desactivar el módulo si fue seleccionado por error.`
      ));
      return false;
    }
    return true;
  }

  async function saveEntityPermission(entityName, controlType) {
    const roleId = roleIdNumber();
    const existing = entityPermissions.find((row) => Number(row.id_permission) === roleId && row.entity_name === entityName);
    if (controlType > 0) {
      const navigation = navigationMatrix[entityName] || {};
      const payload = {
        id_permission: roleId,
        entity_name: entityName,
        control_type: controlType,
        menu_location: navigation.menu_location || "sidebar",
        menu_group: String(navigation.menu_group || "").trim() || null,
        menu_group_icon: String(navigation.menu_group_icon || "").trim() || null,
        menu_label: String(navigation.menu_label || "").trim() || null,
        menu_order: Number(navigation.menu_order ?? 100)
      };
      if (existing?.id_entity_permission) await updateEntityPermission(existing.id_entity_permission, payload);
      else await createEntityPermission(payload);
    } else if (existing?.id_entity_permission) {
      await deleteEntityPermission(existing.id_entity_permission);
    }
  }

  async function resolveFieldRecord(field, createdFields) {
    const existingId = getFieldId(field);
    if (existingId) return existingId;
    const entityName = field.entity_name || field.table_name || selectedEntity;
    const fieldName = getFieldName(field);
    const registryKey = fieldRegistryKey(entityName, fieldName);
    if (createdFields.has(registryKey)) return createdFields.get(registryKey);
    const payload = { table_name: entityName, field_name: fieldName };
    const created = await createField(payload);
    const createdId = created?.id_field || created?.id;
    if (createdId) {
      createdFields.set(registryKey, createdId);
      setFields((prev) => [...prev, { ...field, id_field: createdId, table_name: entityName, field_name: fieldName }]);
    }
    return createdId;
  }

  async function saveFieldPermission(fieldId, controlType) {
    const roleId = roleIdNumber();
    if (!fieldId) return;
    const existing = fieldPermissions.find((row) => Number(row.id_permission) === roleId && Number(row.id_field) === Number(fieldId));
    if (controlType > 0) {
      const payload = { id_permission: roleId, id_field: Number(fieldId), control_type: String(FIELD_VISIBLE_BIT) };
      if (existing?.id_nm_field_permission) await updateNmFieldPermission(existing.id_nm_field_permission, payload);
      else await createNmFieldPermission(payload);
    } else if (existing?.id_nm_field_permission) {
      await deleteNmFieldPermission(existing.id_nm_field_permission);
    }
  }

  async function handleSave() {
    if (!selectedRoleId) {
      setError(t("errors.validation_failed", "Selecciona un rol/perfil"));
      return;
    }
    if (!validateVisibleFieldsBeforeSave()) return;
    setSaving(true); setError(""); setNotice("");
    try {
      for (const entity of catalog) {
        const entityName = getEntityName(entity);
        if (entityName) await saveEntityPermission(entityName, Number(entityMatrix[entityName] || 0));
      }
      const createdFields = new Map();
      for (const field of allManagedFields) {
        const entityName = field.entity_name || field.table_name;
        const entityEnabled = Number(entityMatrix[entityName] || 0) > 0;
        const fieldKey = getFieldKey(field);
        const controlType = entityEnabled ? Number(fieldMatrix[fieldKey] || 0) : 0;
        if (controlType > 0 || getFieldId(field)) {
          const fieldId = await resolveFieldRecord(field, createdFields);
          if (fieldId) await saveFieldPermission(fieldId, controlType);
        }
      }
      const [entityPermPayload, fieldPermPayload, fieldPayload] = await Promise.all([
        fetchAllPages(getAllEntityPermission),
        fetchAllPages(getAllNmFieldPermission),
        fetchAllPages(getAllField)
      ]);
      setEntityPermissions(asItems(entityPermPayload));
      setFieldPermissions(asItems(fieldPermPayload));
      setFields(asItems(fieldPayload));
      setNotice(t("common.permissions_saved", "Permisos guardados correctamente"));
    } catch (err) {
      setError(t(err.message, err.message || "No se pudieron guardar los permisos"));
    } finally {
      setSaving(false);
    }
  }

  function entityLabel(entity) {
    const name = getEntityName(entity);
    return t(`menu.${name}`, entity?.label || humanizeLabel(name));
  }

  function fieldLabel(field) {
    const name = getFieldName(field);
    const entityName = field?.entity_name || field?.table_name || selectedEntity;
    return t(`fields.${entityName}.${name}`, field?.label || humanizeLabel(name));
  }

  return (
    <section className="entity-page role-permission-manager">
      <PageHeader
        eyebrow={"RBAC"}
        titulo={t("common.role_permission_manager", "Gestor de roles y permisos")}
        subtitulo={t("common.role_permission_manager_body", "Configura módulos, acciones y campos visibles para cada rol desde una sola pantalla.")}
      >
        <button className="button primary" onClick={handleSave} disabled={saving || !selectedRoleId}>
        <Save size={16} /> {saving ? t("common.loading", "Cargando...") : t("common.save_permissions", "Guardar permisos")}
        </button>
      </PageHeader>

      {notice && <div className="alert success">{notice}</div>}
      {error && <div className="alert error">{error}</div>}

      <article className="form-card">
        <div className="form-header"><ShieldCheck size={20} /><strong>{t("common.role", "Rol/perfil")}</strong></div>
        <div className="form-grid">
          <label className="field">
            <span>{t("common.select_role", "Seleccionar rol/perfil")}</span>
            <select value={selectedRoleId} onChange={(event) => { setSelectedRoleId(event.target.value); setRoleFormOpen(false); }}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {roleOptions.map((role) => <option key={role.id} value={role.id}>{role.label}</option>)}
            </select>
          </label>
        </div>
        <div className="form-actions">
          <button className="button" type="button" onClick={openNewRole}><Plus size={16} />{t("common.new_role", "Nuevo rol")}</button>
          <button className="button" type="button" onClick={openEditRole} disabled={!selectedRoleId}><Pencil size={16} />{t("common.edit_role", "Editar rol")}</button>
          <button className="button" type="button" onClick={handleDeleteRole} disabled={!selectedRoleId || savingRole}><Trash2 size={16} />{t("common.delete_role", "Eliminar rol")}</button>
        </div>
        {roleFormOpen && (
          <form className="form-card" onSubmit={handleSaveRole}>
            <div className="form-header"><strong>{editingRoleId ? t("common.edit_role", "Editar rol") : t("common.new_role", "Nuevo rol")}</strong><button className="button ghost" type="button" onClick={() => setRoleFormOpen(false)}><X size={16} /></button></div>
            <div className="form-grid">
              <label className="field"><span>{t("common.role_description", "Nombre o descripción del rol")}</span><input required value={roleForm.permission_description} onChange={(event) => setRoleForm((prev) => ({ ...prev, permission_description: event.target.value }))} /></label>
              <label className="field"><span>{t("fields.permission.authorized_by", "Autorizado por")}</span><select required value={roleForm.authorized_by} onChange={(event) => setRoleForm((prev) => ({ ...prev, authorized_by: event.target.value }))}><option value="">{t("common.select_option", "Selecciona una opción")}</option>{users.map((item) => <option key={item.id_user ?? item.id} value={item.id_user ?? item.id}>{item.username || item.full_name || item.email || item.id_user || item.id}</option>)}</select></label>
              <label className="field"><span>{t("fields.permission.id_department", "Departamento")}</span><select required value={roleForm.id_department} onChange={(event) => setRoleForm((prev) => ({ ...prev, id_department: event.target.value }))}><option value="">{t("common.select_option", "Selecciona una opción")}</option>{departments.map((item) => <option key={item.id_department ?? item.id} value={item.id_department ?? item.id}>{item.department_description || item.name || item.id_department || item.id}</option>)}</select></label>
              <label className="field"><span>{t("fields.permission.id_subdepartment", "Subdepartamento")}</span><select required value={roleForm.id_subdepartment} onChange={(event) => setRoleForm((prev) => ({ ...prev, id_subdepartment: event.target.value }))}><option value="">{t("common.select_option", "Selecciona una opción")}</option>{subdepartments.map((item) => <option key={item.id_subdepartment ?? item.id} value={item.id_subdepartment ?? item.id}>{item.subdepartment_description || item.name || item.id_subdepartment || item.id}</option>)}</select></label>
              <label className="field"><span>{t("fields.permission.id_level", "Nivel")}</span><select required value={roleForm.id_level} onChange={(event) => setRoleForm((prev) => ({ ...prev, id_level: event.target.value }))}><option value="">{t("common.select_option", "Selecciona una opción")}</option>{levels.map((item) => <option key={item.id_level ?? item.id} value={item.id_level ?? item.id}>{item.level_description || item.name || item.id_level || item.id}</option>)}</select></label>
            </div>
            <div className="form-actions"><button className="button primary" type="submit" disabled={savingRole}>{savingRole ? t("common.loading", "Cargando...") : t("common.save_role", "Guardar rol")}</button><button className="button" type="button" onClick={() => setRoleFormOpen(false)}>{t("common.cancel", "Cancelar")}</button></div>
          </form>
        )}
      </article>

      <article className="form-card navigation-group-manager">
        <div className="form-header"><SlidersHorizontal size={20} /><strong>{t("common.navigation_groups", "Grupos del menú")}</strong></div>
        <p className="muted-text">{t("common.navigation_groups_hint", "Cambia el nombre y el icono que representa cada grupo cuando la barra lateral está comprimida.")}</p>
        {!selectedRoleId ? <div className="empty">{t("common.select_role", "Selecciona un rol/perfil")}</div> : navigationGroups.length ? <div className="navigation-group-list">{navigationGroups.map((group) => (
            <section className="navigation-group-row" key={group.name}>
              <label className="field navigation-group-name">
                <span>{t("common.group_name", "Nombre del grupo")} · {group.modules} {group.modules === 1 ? "módulo" : "módulos"}</span>
                <input defaultValue={group.name} maxLength={80} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); event.currentTarget.blur(); } }} onBlur={(event) => { const nextName = event.target.value.trim(); if (nextName && nextName !== group.name) updateNavigationGroup(group.name, { menu_group: nextName }); else event.target.value = group.name; }} />
              </label>
              <div className="navigation-icon-picker" role="group" aria-label={`Icono para ${group.name}`}>
                {GROUP_ICON_OPTIONS.map(({ id, label, Icon }) => <button key={id} type="button" className={group.icon === id ? "active" : ""} title={label} aria-label={label} aria-pressed={group.icon === id} onClick={() => updateNavigationGroup(group.name, { menu_group_icon: id })}><Icon size={19} /></button>)}
              </div>
            </section>
        ))}</div> : <div className="empty">{t("common.no_navigation_groups", "Activa módulos en el menú vertical y asigna un grupo para administrarlo aquí.")}</div>}
      </article>

      {loading ? <div className="empty">{t("common.loading", "Cargando...")}</div> : (
        <div className="permission-workspace">
          <article className="table-card permission-matrix-card">
            <div className="permission-toolbar">
              <label className="field compact-field">
                <span>{t("common.bulk_module_actions", "Acciones masivas de módulos")}</span>
                <select value="" onChange={(event) => { applyBulkEntityAction(event.target.value); event.target.value = ""; }} disabled={!selectedRoleId}>
                  <option value="">{t("common.select_bulk_action", "Selecciona una acción")}</option>
                  <option value="all_crud">{t("common.mark_all_crud", "Marcar todo CRUD")}</option>
                  <option value="clear_everything">{t("common.clear_everything", "Desmarcar todo")}</option>
                  <option value="only_read">{t("common.mark_only_read", "Marcar solo Leer")}</option>
                  <option value="only_create">{t("common.mark_only_create", "Marcar solo Crear")}</option>
                  <option value="only_update">{t("common.mark_only_update", "Marcar solo Actualizar")}</option>
                  <option value="only_delete">{t("common.mark_only_delete", "Marcar solo Eliminar")}</option>
                </select>
                <small className="muted-text">{t("common.bulk_actions_all_modules_hint", "Se aplican a todos los módulos, aunque haya filtros activos.")}</small>
              </label>
            </div>
            <div className="permission-module-filters" role="search" aria-label={t("common.module_filters", "Filtros de módulos")}>
              <label className="field permission-module-search">
                <span>{t("common.filter_by_module", "Filtrar por módulo")}</span>
                <span className="search-box"><Search size={16} /><input value={moduleFilter} onChange={(event) => setModuleFilter(event.target.value)} placeholder={t("common.module_filter_placeholder", "Nombre o clave del módulo")} /></span>
              </label>
              <label className="field compact-field">
                <span>{t("common.filter_by_group", "Filtrar por grupo")}</span>
                <select value={groupFilter} onChange={(event) => setGroupFilter(event.target.value)}>
                  <option value="">{t("common.all_groups", "Todos los grupos")}</option>
                  {moduleGroupOptions.groups.map((groupName) => <option key={groupName} value={groupName}>{groupName}</option>)}
                  {moduleGroupOptions.hasUngroupedModules && <option value="__ungrouped__">{t("common.ungrouped", "Sin grupo")}</option>}
                </select>
              </label>
              <div className="permission-filter-summary" aria-live="polite">
                <strong>{filteredCatalog.length}</strong> {t("common.of", "de")} {catalog.length} {t("common.modules", "módulos")}
                {(moduleFilter || groupFilter) && <button className="button ghost" type="button" onClick={() => { setModuleFilter(""); setGroupFilter(""); }}><X size={15} />{t("common.clear_filters", "Limpiar filtros")}</button>}
              </div>
            </div>
            <div className="permission-matrix-scroll">
              <table>
                <thead>
                  <tr><th>{t("common.module", "Módulo")}</th>{ENTITY_ACTIONS.map((action) => <th key={action.key}>{t(`common.${action.key}`, action.label)}</th>)}<th>{t("common.location", "Ubicación")}</th><th>{t("common.group", "Grupo")}</th><th>{t("common.label", "Etiqueta")}</th><th>{t("common.order", "Orden")}</th></tr>
                </thead>
                <tbody>
                {filteredCatalog.map((entity) => {
                  const entityName = getEntityName(entity);
                  const value = Number(entityMatrix[entityName] || 0);
                  const navigation = navigationMatrix[entityName] || {};
                  const navigationDisabled = !selectedRoleId || value === 0;
                  return (
                    <tr key={entityName} className={selectedEntity === entityName ? "selected-row" : ""} onClick={() => setSelectedEntity(entityName)}>
                      <td><strong>{entityLabel(entity)}</strong>{value === 0 && <small className="muted-text"> {t("common.hidden_module", "Oculto")}</small>}</td>
                      {ENTITY_ACTIONS.map((action) => <td key={action.key}><input type="checkbox" checked={hasBit(value, action.bit)} onChange={() => setEntityBit(entityName, action.bit)} onClick={(event) => event.stopPropagation()} disabled={!selectedRoleId} /></td>)}
                      <td><select aria-label={`${t("common.location", "Ubicación")} ${entityLabel(entity)}`} value={navigation.menu_location || "sidebar"} onChange={(event) => setNavigationValue(entityName, "menu_location", event.target.value)} onClick={(event) => event.stopPropagation()} disabled={navigationDisabled}><option value="sidebar">{t("common.vertical_menu", "Menú vertical")}</option><option value="settings">{t("common.settings_menu", "Engrane")}</option><option value="hidden">{t("common.do_not_show", "No mostrar")}</option></select></td>
                      <td><input aria-label={`${t("common.group", "Grupo")} ${entityLabel(entity)}`} placeholder={t("common.group_placeholder", "Ej. Contabilidad")} value={navigation.menu_group || ""} onChange={(event) => setNavigationValue(entityName, "menu_group", event.target.value)} onClick={(event) => event.stopPropagation()} disabled={navigationDisabled} /></td>
                      <td><input aria-label={`${t("common.label", "Etiqueta")} ${entityLabel(entity)}`} placeholder={entityLabel(entity)} value={navigation.menu_label || ""} onChange={(event) => setNavigationValue(entityName, "menu_label", event.target.value)} onClick={(event) => event.stopPropagation()} disabled={navigationDisabled} /></td>
                      <td><input className="menu-order-input" aria-label={`${t("common.order", "Orden")} ${entityLabel(entity)}`} type="number" min="0" value={navigation.menu_order ?? 100} onChange={(event) => setNavigationValue(entityName, "menu_order", event.target.value)} onClick={(event) => event.stopPropagation()} disabled={navigationDisabled} /></td>
                    </tr>
                  );
                })}
                {filteredCatalog.length === 0 && <tr><td colSpan={9}><div className="empty"><strong>{t("common.no_matching_modules", "No hay módulos que coincidan")}</strong><p>{t("common.adjust_module_filters", "Ajusta el nombre o el grupo seleccionado.")}</p></div></td></tr>}
                </tbody>
              </table>
            </div>
          </article>

          <article className="form-card field-permission-panel">
            <div className="form-header"><ShieldCheck size={20} /><strong>{selectedCatalogEntity ? entityLabel(selectedCatalogEntity) : t("common.defined_fields", "Campos definidos")}</strong></div>
            {!selectedEntity ? <p>{t("common.no_module_selected", "Selecciona un módulo para configurar sus campos.")}</p> : (
              <div className="field-permission-list">
                {selectedEntityUsesActionsOnly ? <div className="empty"><strong>{t("common.actions_only_module", "Permisos administrados por acción")}</strong><p>{t("common.actions_only_hint", "Este espacio de trabajo no expone permisos por campo. Usa Crear, Leer, Actualizar y Eliminar en la tabla superior para controlar sus funciones.")}</p></div> : <p className="muted-text">{Number(entityMatrix[selectedEntity] || 0) > 0 ? t("common.field_visibility_hint", "Marca los campos que serán visibles para este rol. Los no marcados quedarán ocultos.") : t("common.module_hidden_hint", "Este módulo no tiene acciones seleccionadas; quedará oculto y sus campos no se mostrarán.")}</p>}
                {!selectedEntityUsesActionsOnly && <div className="field-bulk-actions">
                  <button className="button" type="button" onClick={() => setAllFieldsForSelectedEntity(true)} disabled={!selectedRoleId || Number(entityMatrix[selectedEntity] || 0) <= 0 || selectedFields.length === 0}>{t("common.select_all_fields", "Seleccionar todos los campos")}</button>
                  <button className="button" type="button" onClick={() => setAllFieldsForSelectedEntity(false)} disabled={!selectedRoleId || Number(entityMatrix[selectedEntity] || 0) <= 0 || selectedFields.length === 0}>{t("common.clear_fields", "Quitar campos")}</button>
                </div>}
                {!selectedEntityUsesActionsOnly && <div className="field-permission-header"><span>{t("common.defined_fields", "Campos definidos")}</span><span>{t("common.visible", "Ver")}</span></div>}
                {!selectedEntityUsesActionsOnly && selectedFields.length === 0 && <div className="empty">{t("common.no_fields_available", "No hay campos configurables para este módulo.")}</div>}
                {!selectedEntityUsesActionsOnly && selectedFields.map((field) => {
                  const fieldKey = getFieldKey(field);
                  const value = Number(fieldMatrix[fieldKey] || 0);
                  const entityEnabled = Number(entityMatrix[selectedEntity] || 0) > 0;
                  return (
                    <div className="field-permission-row" key={fieldKey}>
                      <span>{fieldLabel(field)}</span>
                      <label className="checkbox-inline"><input type="checkbox" checked={hasBit(value, FIELD_VISIBLE_BIT)} onChange={() => setFieldVisible(fieldKey)} disabled={!selectedRoleId || !entityEnabled} /></label>
                    </div>
                  );
                })}
              </div>
            )}
          </article>
        </div>
      )}
    </section>
  );
}
