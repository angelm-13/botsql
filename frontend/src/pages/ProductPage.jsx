import { useEffect, useMemo, useState } from "react";
import { ArrowUpRight, RefreshCw, Search, Tags, Trash2, Pencil, History, PackagePlus, SlidersHorizontal } from "lucide-react";
import { Link } from "react-router-dom";
import FiltroBuscable from "../components/FiltroBuscable.jsx";
import { useI18n } from "../i18n";
import VisorDeFoto from "../components/VisorDeFoto";
import { getAllProduct, createProduct, updateProduct, deleteProduct, getAllEntityPermission, getAllNmFieldPermission, getAllField, resetUserMfa, uploadProductImage, getAllBrand, getAllProductFamily, getAllInventoryStatus, getAllLocation, getAllMaterial, urlDeArchivo } from "../api";
import { fetchAllPages } from "../utils/fetchAllPages";
import { colorDeEstatus } from "../utils/estatusDePieza";
import Pagination from "../components/Pagination.jsx";
import ProductHistory from "../components/ProductHistory.jsx";
import EntradaDeExistencia from "../components/EntradaDeExistencia.jsx";
import AjusteDeExistencia from "../components/AjusteDeExistencia.jsx";
import PageHeader from "../components/PageHeader.jsx";
import FormularioPlegable from "../components/FormularioPlegable.jsx";
import { inputPropsForField, validateForm, validationRules as allValidationRules } from "../utils/validation";
import { CAMPOS_DE_AUDITORIA } from "../utils/camposDeAuditoria";
import { descripcionValida, sugerirDescripcion } from "../utils/productDescription";
import { formatearFechaHora } from "../utils/fechas";
import { useDialogo } from "../dialogo/useDialogo.js";
import { CLASES_DE_ARTICULO } from "../utils/clasesDeProducto";

const emptyForm = { id_location: "", id_material: "", gross_price: "", color: "", is_directly_related_to_product_service: false, product_status: "", path_imagen: "", product_code: "", note: "", descripcion: "", cantidad: "", id_marca: "", id_familia: "", item_class: "" };
const validationRules = allValidationRules["product"] || {};
const ENTITY_KEY = "product";
const ACTION_CREATE = 1;
const ACTION_READ = 2;
const ACTION_UPDATE = 4;
const ACTION_DELETE = 8;
const SCOPE_FIELD_BY_BIT = { [ACTION_CREATE]: "scope_create", [ACTION_READ]: "scope_read", [ACTION_UPDATE]: "scope_update", [ACTION_DELETE]: "scope_delete" };
const FIELD_VISIBLE_BIT = 2;
const ALL_FIELD_NAMES = ['id_product', 'id_location', 'id_material', 'gross_price', 'color', 'is_directly_related_to_product_service', 'product_status', 'path_imagen', 'product_code'];

function hasBit(value, bit) {
  return (Number(value || 0) & bit) === bit;
}

function normalizeList(data) {
  return Array.isArray(data) ? data : (data?.items || data?.data || []);
}

function readCurrentUser() {
  try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch (_) { return {}; }
}

export default function ProductPage() {
  const { lang, t } = useI18n();
  const dialogo = useDialogo();
  const [items, setItems] = useState([]);
  const [formData, setFormData] = useState(emptyForm);
  const [fieldErrors, setFieldErrors] = useState({});
  const [editingId, setEditingId] = useState(null);
  // El producto cuya ficha de historial esta abierta, o null.
  const [ficha, setFicha] = useState(null);
  // El producto al que se le esta registrando una entrada de existencia, o null.
  const [entrada, setEntrada] = useState(null);
  // El producto al que se le esta ajustando la existencia (quitar o corregir), o null.
  const [ajuste, setAjuste] = useState(null);
  const [query, setQuery] = useState("");
  const [view, setView] = useState("table");
  const [page, setPage] = useState(1);
  const [paginacion, setPaginacion] = useState({ total: 0, pages: 1, perPage: 0 });
  const [perPage, setPerPage] = useState(10);
  const [loading, setLoading] = useState(false);
  const [errorKey, setErrorKey] = useState("");
  const [errorMeta, setErrorMeta] = useState(null);
  const [selectedImageFile, setSelectedImageFile] = useState(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState("");
  // Los productos cuya foto no cargo (archivo que no existe): se recuerdan para
  // pintar el marcador en lugar del icono de imagen rota.
  const [fotosRotas, setFotosRotas] = useState(() => new Set());
  // La foto que se esta mirando en grande, o null.
  const [fotoAmpliada, setFotoAmpliada] = useState(null);
  const ampliarFoto = (item) => setFotoAmpliada({
    src: urlDeArchivo(item.path_imagen),
    titulo: item.descripcion || item.product_code || `#${item.id_product}`,
    descripcion: item.product_code || "",
  });
  const marcarFotoRota = (idProduct) => setFotosRotas((antes) => new Set(antes).add(idProduct));
  const currentUser = useMemo(() => readCurrentUser(), []);
  const isSuperUser = Boolean(currentUser?.is_superuser || currentUser?.is_bootstrap_admin || currentUser?.username === "admin1");
  const currentRoleId = currentUser?.id_permission;
  const [modulePermission, setModulePermission] = useState(null);
  const [visibleFieldNames, setVisibleFieldNames] = useState(new Set());
  const [permissionReady, setPermissionReady] = useState(false);
  const canRead = canUseAction(ACTION_READ);
  const canCreate = canUseAction(ACTION_CREATE);
  const canUpdate = canUseAction(ACTION_UPDATE);
  const canDelete = canUseAction(ACTION_DELETE);
  const canSubmitForm = editingId ? canUpdate : canCreate;
  const showRowActions = canRead && (canUpdate || canDelete);
  const [locationOptions, setLocationOptions] = useState([]);
  const [materialOptions, setMaterialOptions] = useState([]);
  const [brandOptions, setBrandOptions] = useState([]);
  const [productFamilyOptions, setProductFamilyOptions] = useState([]);
  const [inventoryStatusOptions, setInventoryStatusOptions] = useState([]);

  async function loadData() {
    if (!permissionReady || !canRead) {
      setItems([]);
      setLoading(false);
      return;
    }
    setLoading(true); setErrorKey(""); setErrorMeta(null);
    try {
      const data = await getAllProduct({ page, per_page: perPage, q: query || undefined });
      setItems(Array.isArray(data) ? data : (data.items || data.data || []));
      // La respuesta ya traia el total y el numero de paginas; antes se
      // tiraban aqui, y por eso "Siguiente" no sabia cuando parar.
      setPaginacion({
        total: Array.isArray(data) ? 0 : (data.total ?? 0),
        pages: Array.isArray(data) ? 1 : (data.pages ?? 1),
        perPage: Array.isArray(data) ? 0 : (data.per_page ?? perPage),
      });
    } catch (error) {
      setErrorKey(error.message || "errors.request_failed");
      setErrorMeta(error.payload?.meta || null);
    } finally {
      setLoading(false);
    }
  }

  // Se espera a que deje de teclear: una peticion por tecla convierte una
  // busqueda de seis letras en seis consultas.
  useEffect(() => {
    const temporizador = setTimeout(() => { loadData(); }, 300);
    return () => clearTimeout(temporizador);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, perPage, permissionReady, canRead, query]);
  useEffect(() => { setPage(1); }, [query]);
  useEffect(() => {
    async function loadFormOptions() {
      if (!permissionReady || (!canSubmitForm && !canRead)) return;
      if (canSeeField("id_location")) {
        try {
          const locationData = await getAllLocation({ page: 1, per_page: 100 });
          setLocationOptions(Array.isArray(locationData) ? locationData : (locationData.items || []));
        } catch (_) {
          setLocationOptions([]);
        }
      }
      if (canSeeField("id_material")) {
        try {
          // Todos los materiales, no solo los primeros 100: el selector busca
          // sobre lo que tiene cargado, y con mas de 100 los materiales
          // nuevos (ids altos) no se podian ni encontrar ni elegir.
          const materialData = await fetchAllPages(getAllMaterial, { sort: "material_description" });
          setMaterialOptions(materialData.items);
        } catch (_) {
          setMaterialOptions([]);
        }
      }
      if (canSeeField("id_marca")) {
        try {
          const brandData = await getAllBrand({ page: 1, per_page: 1000, sort: "brand_description" });
          setBrandOptions(Array.isArray(brandData) ? brandData : (brandData.items || []));
        } catch (_) {
          setBrandOptions([]);
        }
      }
      if (canSeeField("id_familia")) {
        try {
          const productFamilyData = await getAllProductFamily({ page: 1, per_page: 500 });
          setProductFamilyOptions(Array.isArray(productFamilyData) ? productFamilyData : (productFamilyData.items || []));
        } catch (_) {
          setProductFamilyOptions([]);
        }
      }
      if (canSeeField("product_status")) {
        try {
          const inventoryStatusData = await getAllInventoryStatus({ page: 1, per_page: 500, entity_scope: "product", flow_scope: "inventory" });
          const inventoryStatusItems = Array.isArray(inventoryStatusData) ? inventoryStatusData : (inventoryStatusData.items || []);
          setInventoryStatusOptions(inventoryStatusItems.filter((item) => {
            const active = item.is_active === true || item.is_active === "true" || item.is_active === 1 || item.is_active === "1";
            return active && String(item.entity_scope || "").toLowerCase() === "product" && String(item.flow_scope || "").toLowerCase() === "inventory";
          }));
        } catch (_) {
          setInventoryStatusOptions([]);
        }
      }
    }
    loadFormOptions();
  }, [permissionReady, canSubmitForm, canRead, visibleFieldNames]);

  useEffect(() => {
    async function loadRolePermissions() {
      if (isSuperUser) {
        setModulePermission({ scope_create: 4, scope_read: 4, scope_update: 4, scope_delete: 4 });
        setVisibleFieldNames(new Set(ALL_FIELD_NAMES));
        setPermissionReady(true);
        return;
      }
      if (!currentRoleId) {
        setModulePermission(null);
        setVisibleFieldNames(new Set());
        setPermissionReady(true);
        return;
      }
      try {
        const [entityPermissionData, fieldPermissionData, fieldData] = await Promise.all([
          fetchAllPages(getAllEntityPermission),
          fetchAllPages(getAllNmFieldPermission),
          fetchAllPages(getAllField)
        ]);
        const entityPermissions = normalizeList(entityPermissionData);
        const fieldPermissions = normalizeList(fieldPermissionData);
        const fieldsMeta = normalizeList(fieldData);
        const moduleRow = entityPermissions.find((row) =>
          String(row.id_permission ?? "") === String(currentRoleId) &&
          String(row.entity_name ?? "") === ENTITY_KEY
        );
        setModulePermission(moduleRow || null);
        const fieldNameById = new Map();
        fieldsMeta.forEach((field) => {
          if (String(field.table_name || "") === ENTITY_KEY && field.id_field) {
            fieldNameById.set(String(field.id_field), String(field.field_name || ""));
          }
        });
        const allowed = new Set();
        fieldPermissions.forEach((row) => {
          if (String(row.id_permission ?? "") !== String(currentRoleId)) return;
          if (!hasBit(row.control_type, FIELD_VISIBLE_BIT)) return;
          const fieldName = fieldNameById.get(String(row.id_field));
          if (fieldName) allowed.add(fieldName);
        });
        setVisibleFieldNames(allowed);
      } catch (error) {
        setModulePermission(null);
        setVisibleFieldNames(new Set());
      } finally {
        setPermissionReady(true);
      }
    }
    loadRolePermissions();
  }, [currentRoleId, isSuperUser]);

  function canUseAction(bit) {
    if (isSuperUser) return true;
    return Number(modulePermission?.[SCOPE_FIELD_BY_BIT[bit]] || 0) !== 0;
  }

  function canSeeField(fieldName) {
    if (isSuperUser) return true;
    if (!permissionReady) return false;
    return CAMPOS_DE_AUDITORIA.has(fieldName) || visibleFieldNames.has(fieldName);
  }


  function clearProductImageSelection() {
    setSelectedImageFile(null);
    setImagePreviewUrl("");
  }

  function handleProductImageFileChange(event) {
    const file = event.target.files?.[0] || null;
    setSelectedImageFile(file);
    setImagePreviewUrl(file ? URL.createObjectURL(file) : "");
    setFieldErrors((prev) => {
      if (!prev.path_imagen) return prev;
      const next = { ...prev };
      delete next.path_imagen;
      return next;
    });
  }

  function productKanbanDisplayLabel(options, idField, entityName, value) {
    if (value === null || value === undefined || value === "") return "";
    const match = (options || []).find((item) => String(item?.[idField] ?? item?.id ?? "") === String(value));
    return match ? getOptionLabel(match, entityName) : formatTableValue(value);
  }

  function productInventoryStatusLabel(item) {
    if (!item) return "";
    const description = item.inventory_status_description || item.inventory_status_code || "";
    const department = item.department_description || item.id_department_label || "";
    return [description, department].filter(Boolean).join(" - ");
  }

  function productStatusMeta(value) {
    if (value === null || value === undefined || value === "") return null;
    const target = String(value).trim().toLowerCase();
    return (inventoryStatusOptions || []).find((item) => {
      const code = String(item?.inventory_status_code ?? "").trim().toLowerCase();
      const description = String(item?.inventory_status_description ?? "").trim().toLowerCase();
      return code === target || description === target;
    }) || null;
  }

  // El estado que se pinta: el del servidor (`effective_status`, la misma regla de
  // Localizar) y, si no vino, el texto guardado. `product_status` se sigue usando
  // para editar: ahi se cambia lo que esta guardado.
  function estadoQueSePinta(item) {
    return item?.effective_status ?? item?.product_status;
  }

  function productStatusDisplayLabel(value) {
    if (value === null || value === undefined || value === "") return "";
    if (String(value).trim().toUpperCase() === "ENTRADA") return t("product.status_in_warehouse", "En almacén");
    const match = productStatusMeta(value);
    return match ? productInventoryStatusLabel(match) : formatTableValue(value);
  }

  function productStatusColor(value) {
    // El color que el administrador le puso al estado en el catalogo manda; si el
    // texto no coincide con ninguna fila (ENTRADA, SALIDA, DESTRUCCION... no la
    // tienen), se cae a la paleta por gravedad de `estatusDePieza.js`.
    const color = String(productStatusMeta(value)?.color || "").trim();
    if (/^#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i.test(color)) return color;
    return colorDeEstatus(value);
  }

  function productHexToRgba(hex, alpha) {
    const raw = String(hex || "").replace("#", "");
    const normalized = raw.length === 3 ? raw.split("").map((char) => char + char).join("") : raw.slice(0, 6);
    if (!/^[0-9a-f]{6}$/i.test(normalized)) return "";
    const value = parseInt(normalized, 16);
    const red = (value >> 16) & 255;
    const green = (value >> 8) & 255;
    const blue = value & 255;
    return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
  }

  function productStatusBadgeStyle(value) {
    const color = productStatusColor(value);
    const baseStyle = {
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      border: "1px solid #cbd5e1",
      borderRadius: "999px",
      padding: "6px 10px",
      fontWeight: 800,
      fontSize: "12px",
      lineHeight: 1.1,
      background: "#f8fafc",
      color: "#0f172a",
      whiteSpace: "nowrap",
    };
    if (!color) return baseStyle;
    return {
      ...baseStyle,
      borderColor: color,
      background: productHexToRgba(color, 0.14) || baseStyle.background,
      boxShadow: `inset 4px 0 0 ${color}`,
    };
  }

  function productStatusCardStyle(value) {
    const color = productStatusColor(value);
    return color ? { borderLeftColor: color } : {};
  }

  function handleChange(event) {
    const { name, type, checked, value } = event.target;
    setFormData((prev) => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
    setFieldErrors((prev) => {
      if (!prev[name]) return prev;
      const next = { ...prev };
      delete next[name];
      return next;
    });
  }

  function isBlankValue(value) {
    return value === null || value === undefined || (typeof value === "string" && value.trim() === "");
  }

  function buildSubmitPayload() {
    const payload = { ...formData };
    if (ENTITY_KEY === "user" && editingId && isBlankValue(payload.password)) {
      delete payload.password;
    }
    delete payload.path_imagen;
    // La existencia no se escribe desde aqui al editar: se mueve con la entrada
    // de existencia, el vale o el ajuste (la cantidad inicial solo al dar de alta).
    if (editingId) delete payload.cantidad;
    return payload;
  }

  function formatFieldError(fieldName) {
    const messageKey = fieldErrors[fieldName];
    if (!messageKey) return "";
    const fieldLabel = t(`fields.product.${fieldName}`, fieldName);
    if (messageKey === "validations.user.password.strong" || String(messageKey).endsWith(".password.strong")) {
      return t("errors.password_strong", "La contraseña debe tener mínimo 8 caracteres e incluir mayúscula, minúscula, número y símbolo.");
    }
    if (messageKey === "validations.user.password.required") {
      return t("errors.password_required", "La contraseña es obligatoria al crear un usuario.");
    }
    if (messageKey === "validations.user.username.required") {
      return t("errors.username_required", "El nombre de usuario es obligatorio.");
    }
    if (String(messageKey).endsWith(".required")) return `${t("errors.required_field", "Campo obligatorio")}: ${fieldLabel}`;
    return t(messageKey, messageKey);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setErrorKey("");
    setErrorMeta(null);
    const submitPayload = buildSubmitPayload();
    const validation = validateForm("product", submitPayload, validationRules);
    const nextFieldErrors = { ...validation.errors };
    // El formato de oracion se exige al capturar o al CAMBIAR la descripcion; un
    // producto migrado en mayusculas se puede seguir editando sin tocarla.
    const descripcionOriginal = editingId ? items.find((it) => it.id_product === editingId)?.descripcion : undefined;
    if (!descripcionValida(submitPayload.descripcion) && submitPayload.descripcion !== descripcionOriginal) {
      nextFieldErrors.descripcion = "errors.product_description_format";
    }
    if (ENTITY_KEY === "user" && !editingId) {
      if (isBlankValue(submitPayload.username)) nextFieldErrors.username = "validations.user.username.required";
      if (isBlankValue(submitPayload.password)) nextFieldErrors.password = "validations.user.password.required";
    }
    if (Object.keys(nextFieldErrors).length > 0) {
      setFieldErrors(nextFieldErrors);
      setErrorKey("errors.validation_failed");
      return;
    }
    setFieldErrors({});
    try {
      if (editingId && !canUpdate) return;
      if (!editingId && !canCreate) return;
      let savedRecord = null;
      if (editingId) {
        savedRecord = await updateProduct(editingId, submitPayload);
        if (selectedImageFile && canSeeField("path_imagen")) {
          savedRecord = await uploadProductImage(editingId, selectedImageFile);
        }
      } else {
        savedRecord = await createProduct(submitPayload);
        const createdId = savedRecord?.id_product ?? savedRecord?.id;
        if (selectedImageFile && canSeeField("path_imagen") && createdId) {
          savedRecord = await uploadProductImage(createdId, selectedImageFile);
        }
      }
      setFormData(emptyForm); setEditingId(null); clearProductImageSelection(); await loadData();
    } catch (error) {
      const meta = error.payload?.meta || null;
      setErrorKey(error.message || "errors.request_failed");
      setErrorMeta(meta);
      if (meta?.field) setFieldErrors((prev) => ({ ...prev, [meta.field]: error.message || "errors.invalid_field" }));
    }
  }

  function startEdit(item) {
    if (!canUpdate) return;
    setEditingId(item.id_product);
    const editData = { ...emptyForm, ...item };
    if (ENTITY_KEY === "user") editData.password = "";
    setFormData(editData);
    setSelectedImageFile(null);
    setImagePreviewUrl(item.path_imagen ? urlDeArchivo(item.path_imagen) : "");
    setFieldErrors({});
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function removeItem(item) {
    if (!canDelete) return;
    if (!(await dialogo.confirmar(t("common.confirm_delete")))) return;
    try { await deleteProduct(item.id_product); await loadData(); } catch (error) { setErrorKey(error.message || "errors.request_failed"); setErrorMeta(error.payload?.meta || null); }
  }



  async function resetMfaForItem(item) {
    if (ENTITY_KEY !== "user") return;
    const targetId = item.id_user ?? item.id;
    if (!targetId) return;
    if (!(await dialogo.confirmar(t("common.mfa_reset_confirm", "¿Restablecer MFA de este usuario?")))) return;
    setErrorKey("");
    setErrorMeta(null);
    try {
      await resetUserMfa(targetId);
      await loadData();
    } catch (error) {
      setErrorKey(error.message || "common.mfa_reset_error");
      setErrorMeta(error.payload?.meta || null);
    }
  }

  function formatTableValue(value) {
    if (value === null || value === undefined) return "";
    const locale = lang === "ja" ? "ja-JP" : lang === "en" ? "en-US" : lang === "pt" ? "pt-BR" : lang === "de" ? "de-DE" : "es-MX";
    if (typeof value === "boolean") {
      const labels = {
        es: { yes: "Sí", no: "No" },
        en: { yes: "Yes", no: "No" },
        pt: { yes: "Sim", no: "Não" },
        de: { yes: "Ja", no: "Nein" },
        ja: { yes: "はい", no: "いいえ" },
      };
      const selected = labels[lang] || labels.es;
      return value ? selected.yes : selected.no;
    }
    if (typeof value === "number") return new Intl.NumberFormat(locale).format(value);
    if (typeof value === "string" && /^[0-9]{4}-[0-9]{2}-[0-9]{2}T/.test(value)) {
      const formateada = formatearFechaHora(value, locale);
      if (formateada) return formateada;
    }
    if (Array.isArray(value)) return value.map((item) => formatTableValue(item)).filter(Boolean).join(", ");
    if (typeof value === "object") {
      try {
        return Object.entries(value)
          .filter(([, val]) => val !== null && val !== undefined && val !== "")
          .slice(0, 6)
          .map(([key, val]) => `${key}: ${typeof val === "object" ? JSON.stringify(val) : String(val)}`)
          .join(", ");
      } catch (_) {
        return String(value);
      }
    }
    return String(value);
  }

  function getOptionLabel(item, entityName = "") {
    if (!item) return "";
    const normalized = String(entityName || "").toLowerCase();
    const specificFields = {
      user: ["full_name", "username", "email", "first_name", "last_name_father"],
      permission: ["permission_description"],
      department: ["department_description"],
      subdepartment: ["subdepartment_description"],
      level: ["level_description"],
      bank: ["bank_name"],
      brand: ["brand_description", "brand_name"],
      unit: ["unit_name", "unit_code", "unit_description", "symbol"],
      material: ["material_description", "material_code"],
      product: ["product_code", "descripcion", "note"],
      product_family: ["product_family_description", "type"],
      location: ["location_description"],
      location_type: ["location_type_description"],
      status: ["status_description", "category"],
      incident_type: ["incident_type_description"],
      payroll_concept: ["payroll_concept_description", "payroll_code"],
      proyect: ["proyect_description", "title"],
      project: ["project_description", "title"],
      service: ["service_description"],
      customer_supplier: ["name", "business_name", "commercial_name", "contact_name", "title"],
      field: ["field_name", "table_name"],
      template: ["template_description"],
      survey_question: ["question", "title"],
      survey_multiple_answer: ["survey_answer_description"],
      task: ["task_description", "task_code", "title"],
    };
    const candidates = [
      ...(specificFields[normalized] || []),
      `${normalized}_description`,
      `${normalized}_name`,
      `${normalized}_code`,
      "description",
      "name",
      "title",
      "code",
      "email",
      "username",
      "full_name",
      "business_name",
      "commercial_name",
      "contact_name",
    ];
    for (const key of candidates) {
      const value = item[key];
      if (value !== null && value !== undefined && String(value).trim() !== "") return String(value);
    }
    const idKey = normalized ? `id_${normalized}` : "";
    const idValue = idKey ? item[idKey] : undefined;
    return String(idValue ?? item.id ?? "");
  }

  function renderError() {
    if (!errorKey) return "";
    const fieldLabel = errorMeta?.field ? t(`fields.product.${errorMeta.field}`, errorMeta.field) : "";
    if (errorKey === "errors.field_too_long" && errorMeta?.field) {
      return `${t(errorKey, errorKey)}: ${fieldLabel} (${errorMeta.actual_length}/${errorMeta.max_length})`;
    }
    if (errorKey === "errors.invalid_field" && errorMeta?.field) {
      return `${t(errorKey, errorKey)}: ${fieldLabel}`;
    }
    return t(errorKey, errorKey);
  }

  const filtered = useMemo(() => {
    const needle = query.toLowerCase().trim();
    if (!needle) return items;
    return items.filter((item) => {
      const values = Object.values(item || {}).map((value) => String(value ?? ""));
      if (canSeeField("product_status")) values.push(productStatusDisplayLabel(estadoQueSePinta(item)));
      if (canSeeField("id_location")) values.push(productKanbanDisplayLabel(locationOptions, "id_location", "location", item.id_location));
      if (canSeeField("id_material")) values.push(productKanbanDisplayLabel(materialOptions, "id_material", "material", item.id_material));
      if (canSeeField("id_marca")) values.push(productKanbanDisplayLabel(brandOptions, "id_brand", "brand", item.id_marca));
      if (canSeeField("id_familia")) values.push(productKanbanDisplayLabel(productFamilyOptions, "id_product_family", "product_family", item.id_familia));
      return values.join(" ").toLowerCase().includes(needle);
    });
  }, [items, query, inventoryStatusOptions, locationOptions, materialOptions, brandOptions, productFamilyOptions]);

  const groups = useMemo(() => filtered.reduce((acc, item) => {
    const key = String(estadoQueSePinta(item) ?? t("common.unclassified"));
    acc[key] = acc[key] || []; acc[key].push(item); return acc;
  }, {}), [filtered, lang]);

  return (
    <section className="entity-page">
      <PageHeader
        eyebrow={t("common.module")}
        titulo={t("menu.product")}
        subtitulo={t("page.product.subtitle", "")}
      >
        <button className="button ghost" onClick={loadData} disabled={!canRead}><RefreshCw size={16} />{loading ? t("common.loading") : t("common.refresh")}</button>
      </PageHeader>

      {canSubmitForm && (
      <FormularioPlegable
        titulo={editingId ? t("common.edit") : t("common.new")}
        abrirSi={editingId}
        onSubmit={handleSubmit}
      >
        <div className="form-grid">
          {canSeeField("id_location") && (
          <label className="field">
            <span>{t("fields.product.id_location")}</span>
            <select name="id_location" value={formData.id_location ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["id_location"])} {...inputPropsForField("id_location", validationRules["id_location"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {locationOptions.map((item) => (
                <option key={item.id_location ?? item.id ?? JSON.stringify(item)} value={item.id_location ?? item.id ?? ""}>
                  {getOptionLabel(item, "location")}
                </option>
              ))}
            </select>
            {fieldErrors["id_location"] && <span className="field-error">{formatFieldError("id_location")}</span>}
          </label>
          )}
          {canSeeField("gross_price") && (
          <label className="field">
            <span>{t("fields.product.gross_price")}</span>
            <input name="gross_price" type="number" value={formData.gross_price ?? ""} onChange={handleChange} placeholder={t("fields.product.gross_price")} aria-invalid={Boolean(fieldErrors["gross_price"])} {...inputPropsForField("gross_price", validationRules["gross_price"], "number")} />
            {fieldErrors["gross_price"] && <span className="field-error">{formatFieldError("gross_price")}</span>}
          </label>
          )}
          {canSeeField("color") && (
          <label className="field">
            <span>{t("fields.product.color")}</span>
            <input name="color" type="text" maxLength={100} value={formData.color ?? ""} onChange={handleChange} placeholder={t("fields.product.color")} aria-invalid={Boolean(fieldErrors["color"])} {...inputPropsForField("color", validationRules["color"], "text")} />
            {fieldErrors["color"] && <span className="field-error">{formatFieldError("color")}</span>}
          </label>
          )}
          {canSeeField("is_directly_related_to_product_service") && (
          <label className="field checkbox-field">
            <span>{t("fields.product.is_directly_related_to_product_service")}</span>
            <input name="is_directly_related_to_product_service" type="checkbox" checked={Boolean(formData.is_directly_related_to_product_service)} onChange={handleChange} aria-invalid={Boolean(fieldErrors["is_directly_related_to_product_service"])} {...inputPropsForField("is_directly_related_to_product_service", validationRules["is_directly_related_to_product_service"], "checkbox")} />
            {fieldErrors["is_directly_related_to_product_service"] && <span className="field-error">{formatFieldError("is_directly_related_to_product_service")}</span>}
          </label>
          )}
          {canSeeField("product_status") && (
          <label className="field">
            <span>{t("fields.product.product_status")}</span>
            <select name="product_status" value={formData.product_status ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["product_status"])} {...inputPropsForField("product_status", validationRules["product_status"], "select")}>
              <option value="">{t("common.select_option", "Selecciona una opción")}</option>
              {/* ENTRADA no es un estado del catalogo sino "esta en el almacen": sin esta opcion no habia como devolver a disponible una pieza marcada extraviada o con salida. */}
              <option value="ENTRADA">{t("product.status_in_warehouse", "En almacén")}</option>
              {inventoryStatusOptions.map((item) => (
                <option key={item.id_inventory_status ?? item.inventory_status_code ?? JSON.stringify(item)} value={item.inventory_status_code ?? ""}>
                  {productInventoryStatusLabel(item)}
                </option>
              ))}
            </select>
            {fieldErrors["product_status"] && <span className="field-error">{formatFieldError("product_status")}</span>}
          </label>
          )}
          {canSeeField("item_class") && (
          <label className="field">
            <span>{t("fields.product.item_class", "Clase")}</span>
            <select name="item_class" value={formData.item_class ?? ""} onChange={handleChange} aria-invalid={Boolean(fieldErrors["item_class"])}>
              <option value="">{t("item_class.from_material", "La de su material")}</option>
              {CLASES_DE_ARTICULO.map((c) => (
                <option key={c.clave} value={c.clave}>{t(`item_class.${c.clave}`, c.etiqueta)}</option>
              ))}
            </select>
            {fieldErrors["item_class"] && <span className="field-error">{formatFieldError("item_class")}</span>}
          </label>
          )}
          {canSeeField("path_imagen") && (
          <label className="field image-field">
            <span>{t("common.image", "Imagen")}</span>
            <input name="path_imagen_file" type="file" accept="image/png,image/jpeg,image/webp" onChange={handleProductImageFileChange} aria-invalid={Boolean(fieldErrors["path_imagen"])} />
            <small>{t("common.select_image", "Selecciona una imagen JPG, PNG o WEBP")}</small>
            {imagePreviewUrl && <img className="image-preview" src={imagePreviewUrl} alt={t("common.image", "Imagen")} />}
            {formData.path_imagen && !imagePreviewUrl && <small>{formData.path_imagen}</small>}
            {fieldErrors["path_imagen"] && <span className="field-error">{formatFieldError("path_imagen")}</span>}
          </label>
          )}
          {canSeeField("product_code") && (
          <label className="field">
            <span>{t("fields.product.product_code")}</span>
            <input name="product_code" type="text" maxLength={30} value={formData.product_code ?? ""} onChange={handleChange} placeholder={t("fields.product.product_code")} aria-invalid={Boolean(fieldErrors["product_code"])} {...inputPropsForField("product_code", validationRules["product_code"], "text")} />
            {fieldErrors["product_code"] && <span className="field-error">{formatFieldError("product_code")}</span>}
          </label>
          )}
          {canSeeField("note") && (
          <label className="field">
            <span>{t("fields.product.note")}</span>
            <input name="note" type="text" maxLength={300} value={formData.note ?? ""} onChange={handleChange} placeholder={t("fields.product.note")} aria-invalid={Boolean(fieldErrors["note"])} {...inputPropsForField("note", validationRules["note"], "text")} />
            {fieldErrors["note"] && <span className="field-error">{formatFieldError("note")}</span>}
          </label>
          )}
          {canSeeField("descripcion") && (
          <label className="field">
            <span>{t("fields.product.descripcion")}</span>
            <input name="descripcion" type="text" maxLength={250} list="product-descripcion-sugeridas" autoComplete="off" value={formData.descripcion ?? ""} onChange={handleChange} placeholder={t("fields.product.descripcion_ejemplo", "Ej. Pulidor chico 3/4")} aria-invalid={Boolean(fieldErrors["descripcion"])} {...inputPropsForField("descripcion", validationRules["descripcion"], "text")} />
            <datalist id="product-descripcion-sugeridas">
              {[...new Set(items.map((it) => it.descripcion).filter(Boolean))].map((d) => <option key={d} value={d} />)}
            </datalist>
            {formData.descripcion && !descripcionValida(formData.descripcion) && (
              <button type="button" className="button-link" onClick={() => handleChange({ target: { name: "descripcion", type: "text", value: sugerirDescripcion(formData.descripcion) } })}>
                {t("fields.product.descripcion_sugerencia", "¿Quisiste decir")} «{sugerirDescripcion(formData.descripcion)}»?
              </button>
            )}
            {fieldErrors["descripcion"] && <span className="field-error">{formatFieldError("descripcion")}</span>}
          </label>
          )}
          {/* Solo un producto que se lleva por cantidad (fungible) tiene cantidad; el
              que se rastrea pieza por pieza tiene una fila por unidad. Al editar es de
              solo lectura: lo que entra va por "Registrar entrada". */}
          {canSeeField("cantidad") && (formData.tracking_mode || "fungible") === "fungible" && (
          <label className="field">
            <span>{t("fields.product.cantidad")}</span>
            <input name="cantidad" type="number" min="0" step="1" value={formData.cantidad ?? ""} onChange={handleChange} readOnly={Boolean(editingId)} placeholder={t("fields.product.cantidad")} aria-invalid={Boolean(fieldErrors["cantidad"])} {...inputPropsForField("cantidad", validationRules["cantidad"], "number")} />
            {editingId && <span className="field-hint">{t("stock_entry.edit_hint", "Para sumar usa «Registrar entrada»; para quitar o corregir, «Ajustar existencia». Los dos están en la fila del producto.")}</span>}
            {fieldErrors["cantidad"] && <span className="field-error">{formatFieldError("cantidad")}</span>}
          </label>
          )}
        </div>

        {/* La clasificacion, aparte. No es un campo del producto como su color
            o su precio: es a que grupo pertenece, y eso vive en sus propias
            pantallas. Los tres son buscables porque con los datos de verdad son
            562 materiales, 161 familias y 158 marcas, y hasta hace un momento la
            marca y la familia se capturaban tecleando su NUMERO. */}
        {(canSeeField("id_material") || canSeeField("id_familia")
          || canSeeField("id_marca")) && (
          <fieldset className="clasificacion">
            <legend>
              <Tags size={14} />
              {t("product.classification", "Clasificación")}
              <Link to="/product_family" className="clasificacion-enlace">
                {t("product.see_families", "ver familias y tipos")}
                <ArrowUpRight size={12} />
              </Link>
            </legend>
            <p className="muted clasificacion-ayuda">
              {t("product.classification_help",
                "La familia agrupa, el tipo distingue dentro de ella y el material es la cosa concreta. Si falta alguna, se da de alta en Familias y tipos.")}
            </p>
            <div className="clasificacion-campos">
              {canSeeField("id_material") && (
                <label className="field">
                  <span>{t("fields.product.id_material")}</span>
                  <FiltroBuscable
                    valor={formData.id_material ?? ""}
                    opciones={materialOptions.map((m) => ({
                      value: m.id_material ?? m.id ?? "",
                      label: getOptionLabel(m, "material"),
                    }))}
                    onChange={(v) => setFormData((prev) => ({ ...prev, id_material: v }))}
                    etiqueta={t("fields.product.id_material")}
                    todas={t("common.select_option", "Selecciona una opción")}
                  />
                  {fieldErrors["id_material"] && (
                    <span className="field-error">{formatFieldError("id_material")}</span>
                  )}
                </label>
              )}
              {canSeeField("id_familia") && (
                <label className="field">
                  <span>{t("fields.product.id_familia")}</span>
                  <FiltroBuscable
                    valor={formData.id_familia ?? ""}
                    opciones={productFamilyOptions.map((f) => ({
                      value: f.id_product_family ?? f.id ?? "",
                      label: getOptionLabel(f, "product_family"),
                    }))}
                    onChange={(v) => setFormData((prev) => ({ ...prev, id_familia: v }))}
                    etiqueta={t("fields.product.id_familia")}
                    todas={t("common.select_option", "Selecciona una opción")}
                  />
                  {fieldErrors["id_familia"] && (
                    <span className="field-error">{formatFieldError("id_familia")}</span>
                  )}
                </label>
              )}
              {canSeeField("id_marca") && (
                <label className="field">
                  <span>{t("fields.product.id_marca")}</span>
                  <FiltroBuscable
                    valor={formData.id_marca ?? ""}
                    opciones={brandOptions.map((b) => ({
                      value: b.id_brand ?? b.id ?? "",
                      label: getOptionLabel(b, "brand"),
                    }))}
                    onChange={(v) => setFormData((prev) => ({ ...prev, id_marca: v }))}
                    etiqueta={t("fields.product.id_marca")}
                    todas={t("common.select_option", "Selecciona una opción")}
                  />
                  {fieldErrors["id_marca"] && (
                    <span className="field-error">{formatFieldError("id_marca")}</span>
                  )}
                </label>
              )}
            </div>
          </fieldset>
        )}

        <div className="form-actions">
          <button className="button primary" type="submit">{t("common.save")}</button>
          <button className="button" type="button" onClick={() => { setFormData(emptyForm); setEditingId(null); setFieldErrors({}); clearProductImageSelection(); }}>{t("common.cancel")}</button>
        </div>
      </FormularioPlegable>
      )}

      {canRead && <div className="toolbar">
        <div className="search-box"><Search size={16} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("common.search")} /></div>
        <select value={perPage} onChange={(e) => { setPerPage(Number(e.target.value)); setPage(1); }}>
          <option value="10">10 {t("common.per_page")}</option><option value="25">25 {t("common.per_page")}</option><option value="50">50 {t("common.per_page")}</option>
        </select>
        <button className={view === "table" ? "button active" : "button"} onClick={() => setView("table")}>{t("common.table")}</button>
        <button className={view === "kanban" ? "button active" : "button"} onClick={() => setView("kanban")}>{t("common.kanban")}</button>
      </div>}

      {errorKey && <div className="alert error">{renderError()}</div>}
      {loading && <div className="alert">{t("common.loading")}</div>}
      {permissionReady && !canRead && !canCreate && <div className="empty"><strong>{t("security.permission.read_denied", "Sin permiso de lectura")}</strong><p>{t("common.module_hidden_hint", "Este módulo no tiene acciones seleccionadas; quedará oculto y sus campos no se mostrarán.")}</p></div>}
      {canRead && !loading && filtered.length === 0 && <div className="empty"><strong>{t("common.empty_title")}</strong><p>{t("common.empty_body")}</p></div>}


      {canRead && view === "table" && filtered.length > 0 && <div className="table-card"><table><thead><tr>{showRowActions && <th>{t("common.actions")}</th>}
              {canSeeField("id_product") && <th>{t("fields.product.id_product")}</th>}
              {canSeeField("id_location") && <th>{t("fields.product.id_location")}</th>}
              {canSeeField("id_material") && <th>{t("fields.product.id_material")}</th>}
              {canSeeField("gross_price") && <th>{t("fields.product.gross_price")}</th>}
              {canSeeField("color") && <th>{t("fields.product.color")}</th>}
              {canSeeField("is_directly_related_to_product_service") && <th>{t("fields.product.is_directly_related_to_product_service")}</th>}
              {canSeeField("product_status") && <th>{t("fields.product.product_status")}</th>}
              {canSeeField("path_imagen") && <th>{t("fields.product.path_imagen")}</th>}
              {canSeeField("product_code") && <th>{t("fields.product.product_code")}</th>}
        </tr></thead><tbody>{filtered.map((item) => <tr key={item.id_product}>{showRowActions && <td className="row-actions">{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{canUpdate && <button type="button" onClick={() => setEntrada(item)} title={t("stock_entry.title", "Registrar entrada")}><PackagePlus size={15} /></button>}{canUpdate && <button type="button" onClick={() => setAjuste(item)} title={t("stock_adjust.title", "Ajustar existencia")}><SlidersHorizontal size={15} /></button>}<button type="button" onClick={() => setFicha(item)} title={t("history.title", "Historial del producto")}><History size={15} /></button>{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</td>}
              {canSeeField("id_product") && <td><pre className="cell-value">{formatTableValue(item.id_product)}</pre></td>}
              {canSeeField("id_location") && <td><pre className="cell-value">{productKanbanDisplayLabel(locationOptions, "id_location", "location", item.id_location)}</pre></td>}
              {canSeeField("id_material") && <td><pre className="cell-value">{productKanbanDisplayLabel(materialOptions, "id_material", "material", item.id_material)}</pre></td>}
              {canSeeField("gross_price") && <td><pre className="cell-value">{formatTableValue(item.gross_price)}</pre></td>}
              {canSeeField("color") && <td><pre className="cell-value">{formatTableValue(item.color)}</pre></td>}
              {canSeeField("is_directly_related_to_product_service") && <td><pre className="cell-value">{formatTableValue(item.is_directly_related_to_product_service)}</pre></td>}
              {canSeeField("product_status") && <td><span style={productStatusBadgeStyle(estadoQueSePinta(item))}>{productStatusDisplayLabel(estadoQueSePinta(item))}</span></td>}
              {canSeeField("path_imagen") && <td>{item.path_imagen && !fotosRotas.has(item.id_product) ? <img className="table-image foto-ampliable" src={urlDeArchivo(item.path_imagen)} alt={t("common.image", "Imagen")} title={t("photo.click_to_zoom", "Clic para verla en grande")} onClick={() => ampliarFoto(item)} onError={() => marcarFotoRota(item.id_product)} /> : <span className="muted">-</span>}</td>}
              {canSeeField("product_code") && <td><pre className="cell-value">{formatTableValue(item.product_code)}</pre></td>}
        </tr>)}</tbody></table></div>}

      {canRead && view === "kanban" && filtered.length > 0 && <div className="kanban">{Object.entries(groups).map(([key, groupItems]) => <div className="kanban-column" key={key}><h3>{key} <span>{groupItems.length}</span></h3>{groupItems.map((item) => <article className="kanban-card product-kanban-card" style={productStatusCardStyle(item.product_status)} key={item.id_product}>{canSeeField("path_imagen") && item.path_imagen && !fotosRotas.has(item.id_product) && <img className="kanban-image foto-ampliable" src={urlDeArchivo(item.path_imagen)} alt={t("common.image", "Imagen")} title={t("photo.click_to_zoom", "Clic para verla en grande")} onClick={() => ampliarFoto(item)} onError={() => marcarFotoRota(item.id_product)} />}<strong>{String(item.product_code ?? item.id_product)}</strong><small>#{item.id_product}</small><div className="product-kanban-details product-kanban-compact">
          {canSeeField("product_status") && estadoQueSePinta(item) && <p><span>{t("fields.product.product_status", "Estado")}:</span> <strong style={productStatusBadgeStyle(estadoQueSePinta(item))}>{productStatusDisplayLabel(estadoQueSePinta(item))}</strong></p>}
          {canSeeField("descripcion") && item.descripcion && <p className="wide"><span>{t("fields.product.descripcion", "Descripcion")}:</span> <strong>{formatTableValue(item.descripcion)}</strong></p>}
          {canSeeField("id_location") && item.id_location && <p><span>{t("fields.product.id_location", "Ubicacion")}:</span> <strong>{productKanbanDisplayLabel(locationOptions, "id_location", "location", item.id_location)}</strong></p>}
          {canSeeField("id_material") && item.id_material && <p><span>{t("fields.product.id_material", "Material")}:</span> <strong>{productKanbanDisplayLabel(materialOptions, "id_material", "material", item.id_material)}</strong></p>}
          {canSeeField("id_marca") && item.id_marca && <p><span>{t("fields.product.id_marca", "Marca")}:</span> <strong>{productKanbanDisplayLabel(brandOptions, "id_brand", "brand", item.id_marca)}</strong></p>}
          {canSeeField("id_familia") && item.id_familia && <p><span>{t("fields.product.id_familia", "Familia")}:</span> <strong>{productKanbanDisplayLabel(productFamilyOptions, "id_product_family", "product_family", item.id_familia)}</strong></p>}
          {canSeeField("product_code") && item.product_code && <p><span>{t("fields.product.product_code", "Codigo")}:</span> <strong>{formatTableValue(item.product_code)}</strong></p>}
          {canSeeField("color") && item.color && <p><span>{t("fields.product.color", "Color")}:</span> <strong>{formatTableValue(item.color)}</strong></p>}
          {canSeeField("cantidad") && item.cantidad !== null && item.cantidad !== undefined && item.cantidad !== "" && <p><span>{t("fields.product.cantidad", "Cantidad")}:</span> <strong>{formatTableValue(item.cantidad)}</strong></p>}
          {canSeeField("last_update_date") && item.last_update_date && <p><span>{t("fields.product.last_update_date", "Actualizacion")}:</span> <strong>{formatTableValue(item.last_update_date)}</strong></p>}
          {canSeeField("note") && item.note && <p className="wide"><span>{t("fields.product.note", "Nota")}:</span> <strong>{formatTableValue(item.note)}</strong></p>}
        </div>{showRowActions && <div>{canUpdate && <button onClick={() => startEdit(item)} title={t("common.edit")}><Pencil size={15} /></button>}{canDelete && <button onClick={() => removeItem(item)} title={t("common.delete")}><Trash2 size={15} /></button>}{canUpdate && <button type="button" onClick={() => setEntrada(item)} title={t("stock_entry.title", "Registrar entrada")}><PackagePlus size={15} /></button>}{canUpdate && <button type="button" onClick={() => setAjuste(item)} title={t("stock_adjust.title", "Ajustar existencia")}><SlidersHorizontal size={15} /></button>}<button type="button" onClick={() => setFicha(item)} title={t("history.title", "Historial del producto")}><History size={15} /></button>{ENTITY_KEY === "user" && canUpdate && <button type="button" onClick={() => resetMfaForItem(item)} title={t("common.mfa_reset", "Restablecer MFA")}>{t("common.mfa_reset", "MFA")}</button>}</div>}</article>)}</div>)}</div>}

      {fotoAmpliada && (
        <VisorDeFoto
          src={fotoAmpliada.src}
          titulo={fotoAmpliada.titulo}
          descripcion={fotoAmpliada.descripcion}
          onCerrar={() => setFotoAmpliada(null)}
        />
      )}

      <Pagination
        page={page}
        pages={paginacion.pages}
        total={paginacion.total}
        perPage={paginacion.perPage}
        loading={loading}
        onChange={setPage}
      />
      {entrada && (
        <EntradaDeExistencia
          producto={entrada}
          onCerrar={() => setEntrada(null)}
          onRegistrada={() => loadData()}
        />
      )}
      {ajuste && (
        <AjusteDeExistencia
          producto={ajuste}
          onCerrar={() => setAjuste(null)}
          onRegistrada={() => loadData()}
        />
      )}
      {ficha && (
        <ProductHistory
          idProduct={ficha.id_product}
          titulo={[ficha.product_code, ficha.descripcion].filter(Boolean).join(" · ")}
          onCerrar={() => setFicha(null)}
        />
      )}
    </section>
  );
}
