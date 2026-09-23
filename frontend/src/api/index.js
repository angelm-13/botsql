import { request, requestBlob } from "./client";
export * from "./restaurant";

export const login = (payload) => request("/auth/login", { method: "POST", body: payload, skipAuth: true });
export const verifyMfaLogin = (payload) => request("/auth/mfa/verify-login", { method: "POST", body: payload, skipAuth: true });
export const setupMfa = () => request("/auth/mfa/setup", { method: "POST" });
export const enableMfa = (payload) => request("/auth/mfa/enable", { method: "POST", body: payload });
export const disableMfa = (payload) => request("/auth/mfa/disable", { method: "POST", body: payload });

// Cualquier usuario autenticado, sin importar su rol, cambia SU PROPIA
// contrasena -- ver POST /user/me/password.
export const changeMyPassword = (payload) => request("/user/me/password", { method: "POST", body: payload });
export const resetUserMfa = (targetUserId) => request(`/auth/mfa/reset/${targetUserId}`, { method: "POST" });
export const inventoryTrace = (params) => request("/inventory/trace", { params });

export const uploadProductImage = (id, file) => {
  const formData = new FormData();
  formData.append("file", file);
  return request(`/product/${id}/image`, { method: "POST", body: formData });
};

export const getDocuments = (params = {}) => request("/document/", { params });
export const getDocument = (id) => request(`/document/${id}`);
export const getDocumentCategories = () => request("/document/categories");
export const getDocumentEmployees = () => request("/document/employees");
export const uploadDocument = (payload, file) => {
  const formData = new FormData();
  Object.entries(payload).forEach(([key, value]) => { if (value !== undefined && value !== null && value !== "") formData.append(key, value); });
  formData.append("file", file);
  return request("/document/", { method: "POST", body: formData });
};
export const updateDocument = (id, payload) => request(`/document/${id}`, { method: "PUT", body: payload });
export const deleteDocument = (id) => request(`/document/${id}`, { method: "DELETE" });
export const downloadDocumentVersion = (id, version, download = true) => requestBlob(`/document/${id}/versions/${version}/content`, { params: { download: download ? 1 : 0 } });

export const getLaboratoryEquipment = (params = {}) => request("/laboratory-equipment/", { params });
export const createLaboratoryEquipment = (payload) => request("/laboratory-equipment/", { method: "POST", body: payload });
export const getLaboratoryOrders = (params = {}) => request("/laboratory-service-order/", { params });
export const getLaboratoryOrder = (id) => request(`/laboratory-service-order/${id}`);
export const createLaboratoryOrder = (payload) => request("/laboratory-service-order/", { method: "POST", body: payload });
export const updateLaboratoryDiagnosis = (id, payload) => request(`/laboratory-service-order/${id}/diagnosis`, { method: "PUT", body: payload });
export const transitionLaboratoryOrder = (id, payload) => request(`/laboratory-service-order/${id}/transition`, { method: "POST", body: payload });
export const getLaboratoryOrderHistory = (id) => request(`/laboratory-service-order/${id}/history`);
export const generateLaboratoryReport = (id) => request(`/laboratory-service-order/${id}/diagnostic-report`, { method: "POST" });
export const uploadSignedLaboratoryReport = (id, file, parentVersionId) => {
  const formData = new FormData();
  formData.append("file", file);
  if (parentVersionId) formData.append("id_parent_document_version", parentVersionId);
  return request(`/laboratory-service-order/${id}/diagnostic-report/signed`, { method: "POST", body: formData });
};
export const getPermissionCatalog = () => request("/security/permission-catalog");

export const getAppointmentProfiles = () => request("/appointments/profiles");
export const createAppointmentProfile = (payload) => request("/appointments/profiles", { method: "POST", body: payload });
export const createAppointmentType = (profileId, payload) => request(`/appointments/profiles/${profileId}/types`, { method: "POST", body: payload });
export const createAvailabilityRule = (profileId, payload) => request(`/appointments/profiles/${profileId}/availability-rules`, { method: "POST", body: payload });
export const createAvailabilityOverride = (profileId, payload) => request(`/appointments/profiles/${profileId}/availability-overrides`, { method: "POST", body: payload });
export const getAppointments = (params = {}) => request("/appointments/", { params });
export const getPublicCalendar = (code) => request(`/public/calendars/${encodeURIComponent(code)}`, { skipAuth: true });
export const getPublicCalendarSlots = (code, params) => request(`/public/calendars/${encodeURIComponent(code)}/slots`, { params, skipAuth: true });
export const createPublicAppointment = (code, payload) => request(`/public/calendars/${encodeURIComponent(code)}/appointments`, { method: "POST", body: payload, skipAuth: true });
export const cancelPublicAppointment = (token) => request(`/public/appointments/${encodeURIComponent(token)}/cancel`, { method: "POST", skipAuth: true });

function readStoredUserForPermissions() {
  try { return JSON.parse(localStorage.getItem("user") || "null") || {}; } catch (_) { return {}; }
}

function isPrivilegedPermissionUser() {
  const user = readStoredUserForPermissions();
  const bootstrapUsername = import.meta.env.VITE_BOOTSTRAP_ADMIN_USERNAME || "admin1";
  return Boolean(
    user?.is_superuser ||
    user?.is_bootstrap_admin ||
    user?.username === bootstrapUsername ||
    String(user?.user_type || "").toLowerCase() === "admin"
  );
}

let myPermissionsCache = null;
const MY_PERMISSIONS_CACHE_MS = 250;
export const clearMyPermissionsCache = () => { myPermissionsCache = null; };
export const getMyPermissions = () => {
  const user = readStoredUserForPermissions();
  const cacheKey = `${user?.id_user || ""}:${user?.id_permission || ""}:${user?.username || ""}`;
  const now = Date.now();
  if (myPermissionsCache?.key === cacheKey && myPermissionsCache.expiresAt > now) return Promise.resolve(myPermissionsCache.payload);
  return request("/security/my-permissions").then((payload) => {
    myPermissionsCache = { key: cacheKey, payload, expiresAt: Date.now() + MY_PERMISSIONS_CACHE_MS };
    return payload;
  });
};
export const logout = () => { clearMyPermissionsCache(); localStorage.removeItem("token"); localStorage.removeItem("user"); localStorage.removeItem("mfa_temp_token"); };

export const getAllBank = (params = {}) => request("/bank/", { params });
export const getBank = (id) => request(`/bank/${id}`);
export const createBank = (payload) => request("/bank/", { method: "POST", body: payload });
export const updateBank = (id, payload) => request(`/bank/${id}`, { method: "PUT", body: payload });
export const deleteBank = (id) => request(`/bank/${id}`, { method: "DELETE" });

export const getAllBankAccount = (params = {}) => request("/bank_account/", { params });
export const getBankStatements = (params = {}) => request("/bank-statements/", { params });
export const previewBankStatement = (body) => request("/bank-statements/preview", { method: "POST", body });
export const importBankStatement = (body) => request("/bank-statements/import", { method: "POST", body });
export const getBankStatementMovements = (id, params = {}) => request(`/bank-statements/${id}/movements`, { params });
export const matchBankStatementMovement = (id, payload) => request(`/bank-statements/movements/${id}/match`, { method: "PUT", body: payload });
export const deleteBankStatement = (id) => request(`/bank-statements/${id}`, { method: "DELETE" });
export const getBankAccount = (id) => request(`/bank_account/${id}`);
export const createBankAccount = (payload) => request("/bank_account/", { method: "POST", body: payload });
export const updateBankAccount = (id, payload) => request(`/bank_account/${id}`, { method: "PUT", body: payload });
export const deleteBankAccount = (id) => request(`/bank_account/${id}`, { method: "DELETE" });

export const getAllBrand = (params = {}) => request("/brand/", { params });
export const getBrand = (id) => request(`/brand/${id}`);
export const createBrand = (payload) => request("/brand/", { method: "POST", body: payload });
export const updateBrand = (id, payload) => request(`/brand/${id}`, { method: "PUT", body: payload });
export const deleteBrand = (id) => request(`/brand/${id}`, { method: "DELETE" });

export const getAllCustomerSupplier = (params = {}) => request("/customer_supplier/", { params });
// Solo id+nombre, para selectores (ej. "Cliente" al crear un proyecto) --
// no exige el permiso de lectura completo de customer_supplier, a diferencia
// de getAllCustomerSupplier.
export const getCustomerSupplierOptions = () => request("/customer_supplier/options");
export const getCustomerSupplier = (id) => request(`/customer_supplier/${id}`);
export const createCustomerSupplier = (payload) => request("/customer_supplier/", { method: "POST", body: payload });
export const updateCustomerSupplier = (id, payload) => request(`/customer_supplier/${id}`, { method: "PUT", body: payload });
export const deleteCustomerSupplier = (id) => request(`/customer_supplier/${id}`, { method: "DELETE" });

// El "Cliente" del proyecto: contacto (empresa + persona) fusionado, ya no
// solo la empresa -- ver customer_contact_service.py.
export const getCustomerContactOptions = () => request("/customer_contact/options");

// Solo id+folio+cliente+estatus, para el selector de "Cotizacion" al crear o
// editar un proyecto -- no exige el permiso completo de invoice, igual que
// getCustomerSupplierOptions no exige el de customer_supplier.
export const getQuotationOptions = () => request("/invoice/quotation_options");
export const getAllCustomerContact = (params = {}) => request("/customer_contact/", { params });
export const createCustomerContact = (payload) => request("/customer_contact/", { method: "POST", body: payload });
export const updateCustomerContact = (id, payload) => request(`/customer_contact/${id}`, { method: "PUT", body: payload });
export const deleteCustomerContact = (id) => request(`/customer_contact/${id}`, { method: "DELETE" });

export const getAllLogisticsContact = (params = {}) => request("/logistics_contact/", { params });
export const createLogisticsContact = (payload) => request("/logistics_contact/", { method: "POST", body: payload });
export const updateLogisticsContact = (id, payload) => request(`/logistics_contact/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsContact = (id) => request(`/logistics_contact/${id}`, { method: "DELETE" });

export const getAllLogisticsAddress = (params = {}) => request("/logistics_address/", { params });
export const getLogisticsAddress = (id) => request(`/logistics_address/${id}`);
export const createLogisticsAddress = (payload) => request("/logistics_address/", { method: "POST", body: payload });
export const updateLogisticsAddress = (id, payload) => request(`/logistics_address/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsAddress = (id) => request(`/logistics_address/${id}`, { method: "DELETE" });

export const getAllLogisticsContract = (params = {}) => request("/logistics_contract/", { params });
export const getLogisticsContract = (id) => request(`/logistics_contract/${id}`);
export const createLogisticsContract = (payload) => request("/logistics_contract/", { method: "POST", body: payload });
export const updateLogisticsContract = (id, payload) => request(`/logistics_contract/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsContract = (id) => request(`/logistics_contract/${id}`, { method: "DELETE" });

export const getAllLogisticsRate = (params = {}) => request("/logistics_rate/", { params });
export const getLogisticsRate = (id) => request(`/logistics_rate/${id}`);
export const createLogisticsRate = (payload) => request("/logistics_rate/", { method: "POST", body: payload });
export const updateLogisticsRate = (id, payload) => request(`/logistics_rate/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsRate = (id) => request(`/logistics_rate/${id}`, { method: "DELETE" });

export const getAllLogisticsUnit = (params = {}) => request("/logistics_unit/", { params });
export const getLogisticsUnit = (id) => request(`/logistics_unit/${id}`);
export const createLogisticsUnit = (payload) => request("/logistics_unit/", { method: "POST", body: payload });
export const updateLogisticsUnit = (id, payload) => request(`/logistics_unit/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsUnit = (id) => request(`/logistics_unit/${id}`, { method: "DELETE" });

export const getAllLogisticsTrailer = (params = {}) => request("/logistics_trailer/", { params });
export const getLogisticsTrailer = (id) => request(`/logistics_trailer/${id}`);
export const createLogisticsTrailer = (payload) => request("/logistics_trailer/", { method: "POST", body: payload });
export const updateLogisticsTrailer = (id, payload) => request(`/logistics_trailer/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsTrailer = (id) => request(`/logistics_trailer/${id}`, { method: "DELETE" });

export const getAllLogisticsOperator = (params = {}) => request("/logistics_operator/", { params });
export const getLogisticsOperator = (id) => request(`/logistics_operator/${id}`);
export const createLogisticsOperator = (payload) => request("/logistics_operator/", { method: "POST", body: payload });
export const updateLogisticsOperator = (id, payload) => request(`/logistics_operator/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsOperator = (id) => request(`/logistics_operator/${id}`, { method: "DELETE" });

export const getAllLogisticsMaintenance = (params = {}) => request("/logistics_maintenance/", { params });
export const getLogisticsMaintenance = (id) => request(`/logistics_maintenance/${id}`);
export const createLogisticsMaintenance = (payload) => request("/logistics_maintenance/", { method: "POST", body: payload });
export const updateLogisticsMaintenance = (id, payload) => request(`/logistics_maintenance/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsMaintenance = (id) => request(`/logistics_maintenance/${id}`, { method: "DELETE" });

export const getAllLogisticsQuotation = (params = {}) => request("/logistics_quotation/", { params });
export const getLogisticsQuotation = (id) => request(`/logistics_quotation/${id}`);
export const createLogisticsQuotation = (payload) => request("/logistics_quotation/", { method: "POST", body: payload });
export const updateLogisticsQuotation = (id, payload) => request(`/logistics_quotation/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsQuotation = (id) => request(`/logistics_quotation/${id}`, { method: "DELETE" });

export const getAllLogisticsServiceRequest = (params = {}) => request("/logistics_service_request/", { params });
export const getLogisticsServiceRequest = (id) => request(`/logistics_service_request/${id}`);
export const createLogisticsServiceRequest = (payload) => request("/logistics_service_request/", { method: "POST", body: payload });
export const updateLogisticsServiceRequest = (id, payload) => request(`/logistics_service_request/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsServiceRequest = (id) => request(`/logistics_service_request/${id}`, { method: "DELETE" });

export const getAllLogisticsTrip = (params = {}) => request("/logistics_trip/", { params });
export const getLogisticsTrip = (id) => request(`/logistics_trip/${id}`);
export const createLogisticsTrip = (payload) => request("/logistics_trip/", { method: "POST", body: payload });
export const updateLogisticsTrip = (id, payload) => request(`/logistics_trip/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsTrip = (id) => request(`/logistics_trip/${id}`, { method: "DELETE" });

export const getAllLogisticsEvidence = (params = {}) => request("/logistics_evidence/", { params });
export const getLogisticsEvidence = (id) => request(`/logistics_evidence/${id}`);
export const createLogisticsEvidence = (payload) => request("/logistics_evidence/", { method: "POST", body: payload });
export const updateLogisticsEvidence = (id, payload) => request(`/logistics_evidence/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsEvidence = (id) => request(`/logistics_evidence/${id}`, { method: "DELETE" });

export const getAllLogisticsIncident = (params = {}) => request("/logistics_incident/", { params });
export const getLogisticsIncident = (id) => request(`/logistics_incident/${id}`);
export const createLogisticsIncident = (payload) => request("/logistics_incident/", { method: "POST", body: payload });
export const updateLogisticsIncident = (id, payload) => request(`/logistics_incident/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsIncident = (id) => request(`/logistics_incident/${id}`, { method: "DELETE" });

export const getAllLogisticsShipment = (params = {}) => request("/logistics_shipment/", { params });
export const createLogisticsShipment = (payload) => request("/logistics_shipment/", { method: "POST", body: payload });
export const updateLogisticsShipment = (id, payload) => request(`/logistics_shipment/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsShipment = (id) => request(`/logistics_shipment/${id}`, { method: "DELETE" });

export const getAllLogisticsBranch = (params = {}) => request("/logistics_branch/", { params });
export const createLogisticsBranch = (payload) => request("/logistics_branch/", { method: "POST", body: payload });
export const updateLogisticsBranch = (id, payload) => request(`/logistics_branch/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsBranch = (id) => request(`/logistics_branch/${id}`, { method: "DELETE" });

export const getAllLogisticsReceivable = (params = {}) => request("/logistics_receivable/", { params });
export const createLogisticsReceivable = (payload) => request("/logistics_receivable/", { method: "POST", body: payload });
export const updateLogisticsReceivable = (id, payload) => request(`/logistics_receivable/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsReceivable = (id) => request(`/logistics_receivable/${id}`, { method: "DELETE" });

export const getAllLogisticsFile = (params = {}) => request("/logistics_file/", { params });
export const createLogisticsFile = (payload) => request("/logistics_file/", { method: "POST", body: payload });
export const updateLogisticsFile = (id, payload) => request(`/logistics_file/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsFile = (id) => request(`/logistics_file/${id}`, { method: "DELETE" });

export const getAllLogisticsWarehouse = (params = {}) => request("/logistics_warehouse/", { params });
export const getLogisticsWarehouse = (id) => request(`/logistics_warehouse/${id}`);
export const createLogisticsWarehouse = (payload) => request("/logistics_warehouse/", { method: "POST", body: payload });
export const updateLogisticsWarehouse = (id, payload) => request(`/logistics_warehouse/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsWarehouse = (id) => request(`/logistics_warehouse/${id}`, { method: "DELETE" });

export const getAllLogisticsLocation = (params = {}) => request("/logistics_location/", { params });
export const getLogisticsLocation = (id) => request(`/logistics_location/${id}`);
export const createLogisticsLocation = (payload) => request("/logistics_location/", { method: "POST", body: payload });
export const updateLogisticsLocation = (id, payload) => request(`/logistics_location/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsLocation = (id) => request(`/logistics_location/${id}`, { method: "DELETE" });

export const getAllLogisticsInventory = (params = {}) => request("/logistics_inventory/", { params });
export const getLogisticsInventory = (id) => request(`/logistics_inventory/${id}`);
export const createLogisticsInventory = (payload) => request("/logistics_inventory/", { method: "POST", body: payload });
export const updateLogisticsInventory = (id, payload) => request(`/logistics_inventory/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsInventory = (id) => request(`/logistics_inventory/${id}`, { method: "DELETE" });

export const getAllLogisticsRack = (params = {}) => request("/logistics_rack/", { params });
export const getLogisticsRack = (id) => request(`/logistics_rack/${id}`);
export const createLogisticsRack = (payload) => request("/logistics_rack/", { method: "POST", body: payload });
export const updateLogisticsRack = (id, payload) => request(`/logistics_rack/${id}`, { method: "PUT", body: payload });
export const deleteLogisticsRack = (id) => request(`/logistics_rack/${id}`, { method: "DELETE" });

export const getAllDepartment = (params = {}) => request("/department/", { params });
export const getDepartment = (id) => request(`/department/${id}`);
export const createDepartment = (payload) => request("/department/", { method: "POST", body: payload });
export const updateDepartment = (id, payload) => request(`/department/${id}`, { method: "PUT", body: payload });
export const deleteDepartment = (id) => request(`/department/${id}`, { method: "DELETE" });

export const getAllEntityPermission = (params = {}) => isPrivilegedPermissionUser() ? request("/entity_permission/", { params }) : getMyPermissions().then((payload) => ({ items: payload.entity_permissions || [], page: 1, pages: 1, per_page: (payload.entity_permissions || []).length, total: (payload.entity_permissions || []).length }));
export const getEntityPermission = (id) => request(`/entity_permission/${id}`);
export const createEntityPermission = (payload) => request("/entity_permission/", { method: "POST", body: payload });
export const updateEntityPermission = (id, payload) => request(`/entity_permission/${id}`, { method: "PUT", body: payload });
export const deleteEntityPermission = (id) => request(`/entity_permission/${id}`, { method: "DELETE" });

export const getAllTeam = (params = {}) => request("/team/", { params });
export const getTeam = (id) => request(`/team/${id}`);
export const createTeam = (payload) => request("/team/", { method: "POST", body: payload });
export const updateTeam = (id, payload) => request(`/team/${id}`, { method: "PUT", body: payload });
export const deleteTeam = (id) => request(`/team/${id}`, { method: "DELETE" });

export const getAllNmTeamUser = (params = {}) => request("/nm_team_user/", { params });
export const getNmTeamUser = (id) => request(`/nm_team_user/${id}`);
export const createNmTeamUser = (payload) => request("/nm_team_user/", { method: "POST", body: payload });
export const updateNmTeamUser = (id, payload) => request(`/nm_team_user/${id}`, { method: "PUT", body: payload });
export const deleteNmTeamUser = (id) => request(`/nm_team_user/${id}`, { method: "DELETE" });

export const getAllEventLog = (params = {}) => request("/event_log/", { params });
export const getEventLog = (id) => request(`/event_log/${id}`);
export const createEventLog = (payload) => request("/event_log/", { method: "POST", body: payload });
export const updateEventLog = (id, payload) => request(`/event_log/${id}`, { method: "PUT", body: payload });
export const deleteEventLog = (id) => request(`/event_log/${id}`, { method: "DELETE" });

export const getAllField = (params = {}) => isPrivilegedPermissionUser() ? request("/field/", { params }) : getMyPermissions().then((payload) => ({ items: payload.fields || [], page: 1, pages: 1, per_page: (payload.fields || []).length, total: (payload.fields || []).length }));
export const getField = (id) => request(`/field/${id}`);
export const createField = (payload) => request("/field/", { method: "POST", body: payload });
export const updateField = (id, payload) => request(`/field/${id}`, { method: "PUT", body: payload });
export const deleteField = (id) => request(`/field/${id}`, { method: "DELETE" });

export const getAllFiscalAccount = (params = {}) => request("/fiscal_account/", { params });
export const getFiscalAccount = (id) => request(`/fiscal_account/${id}`);
export const createFiscalAccount = (payload) => request("/fiscal_account/", { method: "POST", body: payload });
export const updateFiscalAccount = (id, payload) => request(`/fiscal_account/${id}`, { method: "PUT", body: payload });
export const deleteFiscalAccount = (id) => request(`/fiscal_account/${id}`, { method: "DELETE" });

export const getAllIncident = (params = {}) => request("/incident/", { params });
export const getIncident = (id) => request(`/incident/${id}`);
export const createIncident = (payload) => request("/incident/", { method: "POST", body: payload });
export const updateIncident = (id, payload) => request(`/incident/${id}`, { method: "PUT", body: payload });
export const deleteIncident = (id) => request(`/incident/${id}`, { method: "DELETE" });

export const getAllIncidentDetail = (params = {}) => request("/incident_detail/", { params });
export const getIncidentDetail = (id) => request(`/incident_detail/${id}`);
export const createIncidentDetail = (payload) => request("/incident_detail/", { method: "POST", body: payload });
export const updateIncidentDetail = (id, payload) => request(`/incident_detail/${id}`, { method: "PUT", body: payload });
export const deleteIncidentDetail = (id) => request(`/incident_detail/${id}`, { method: "DELETE" });

export const getAllIncidentType = (params = {}) => request("/incident_type/", { params });
export const getIncidentType = (id) => request(`/incident_type/${id}`);
export const createIncidentType = (payload) => request("/incident_type/", { method: "POST", body: payload });
export const updateIncidentType = (id, payload) => request(`/incident_type/${id}`, { method: "PUT", body: payload });
export const deleteIncidentType = (id) => request(`/incident_type/${id}`, { method: "DELETE" });

export const getAllInventoryStatus = (params = {}) => request("/inventory_status/", { params });
export const getInventoryStatus = (id) => request(`/inventory_status/${id}`);
export const createInventoryStatus = (payload) => request("/inventory_status/", { method: "POST", body: payload });
export const updateInventoryStatus = (id, payload) => request(`/inventory_status/${id}`, { method: "PUT", body: payload });
export const deleteInventoryStatus = (id) => request(`/inventory_status/${id}`, { method: "DELETE" });

export const getAllInvoice = (params = {}) => request("/invoice/", { params });
export const getInvoiceLines = (id) => request(`/invoice/${id}/lines`);
export const getInvoice = (id) => request(`/invoice/${id}`);
export const createInvoice = (payload) => request("/invoice/", { method: "POST", body: payload });
export const updateInvoice = (id, payload) => request(`/invoice/${id}`, { method: "PUT", body: payload });
export const transitionQuotation = (id, status) => request(`/invoice/${id}/quotation-transition`, { method: "PATCH", body: { status } });
// A diferencia de transitionQuotation (que solo cambia la etiqueta de
// estatus), este endpoint recalcula subtotal/impuesto/total contra las
// partidas autorizadas y deja la factura en 'pendiente', lista para
// timbrar. Es el paso real de "convertir a factura" -- transitionQuotation
// nunca debe usarse para el destino "converted".
export const convertQuotationToInvoice = (id, conversionNote) => request(`/invoice/convert-quotation/${id}`, { method: "PATCH", body: conversionNote ? { conversion_note: conversionNote } : {} });
export const deleteInvoice = (id) => request(`/invoice/${id}`, { method: "DELETE" });
export const getInvoiceCatalogs = () => request("/invoice/catalogs");
export const previewManualInvoice = (payload) => request("/invoice/manual/preview", { method: "POST", body: payload });
export const createManualInvoice = (payload) => request("/invoice/manual", { method: "POST", body: payload });
export const stampInvoice = (id, idempotencyKey = crypto.randomUUID()) => request(`/stamping/invoices/${id}`, { method: "POST", body: { idempotency_key: idempotencyKey } });
export const preflightInvoiceStamping = (id, includeXml = false) => request(`/stamping/invoices/${id}/preflight`, { params: includeXml ? { include_xml: "1" } : {} });
export const getStampingConfig = () => request("/stamping/config");
export const saveStampingConfig = (payload) => request("/stamping/config", { method: "PUT", body: payload });
export const testStampingConfig = (payload) => request("/stamping/config/test", { method: "POST", body: payload });
export const downloadInvoiceXml = (id) => requestBlob(`/invoice/${id}/xml`);
export const downloadInvoicePdf = (id, document = "") => requestBlob(`/invoice/${id}/pdf`, { params: { document } });

export const getInventoryMovements = (id, params = {}) => request(`/product/${id}/inventory-movements`, { params });
export const createInventoryMovement = (id, payload) => request(`/product/${id}/inventory-movements`, { method: "POST", body: { idempotency_key: crypto.randomUUID(), ...payload } });
export const getInventoryReconciliation = (id) => request(`/product/${id}/inventory-reconciliation`);
export const createInventoryTransfer = (id, payload) => request(`/product/${id}/inventory-transfers`, { method: "POST", body: { idempotency_key: crypto.randomUUID(), ...payload } });
export const getProductStock = (id) => request(`/product/${id}/inventory-stock`);

// --- la trazabilidad del vale ---
//
// Las tres existian como servicio desde la carga del sistema anterior y ninguna
// tenia ruta, asi que el dato estaba en la base sin forma de verlo. Salen de
// `nm_incident_product` -los renglones del vale-, no del libro de inventario:
// el libro dice cuanto entro y salio, esto dice QUIEN se lo llevo.
export const getProductLoanHistory = (id) =>
  request(`/vouchers/products/${id}/history`);
export const getVoucherHolders = (params = {}) =>
  request("/vouchers/holders", { params });
export const getVoucherRequests = (params = {}) =>
  request("/vouchers/requests", { params });
export const downloadVoucherRequestsPdf = (params = {}) =>
  requestBlob("/vouchers/requests/pdf", { params });
export const getLocationTree = () => request("/location/tree");
export const getWarehouseStock = (id) => request(`/location/${id}/stock`);
export const getInvoiceInventoryPreview = (id, params = {}) => request(`/invoice/${id}/inventory`, { params });
// --- Punto de venta --------------------------------------------------------
// Ya no hay puente: el punto de venta corre dentro de TYAKXA y contra la misma
// base. Las rutas conservan el prefijo `/pos/api/` que tenian cuando se
// reenviaban, para no tocar las pantallas por un cambio que no cambia nada
// para ellas.
//
// Se retiraron `posLinks`, `posLinkProduct` y `posSyncCatalog`: emparejaban un
// producto del POS con uno del almacen, y compartiendo la tabla `product` no
// hay dos catalogos que emparejar.
export const posStatus = () => request("/pos/status");
export const deploymentPlan = () => request("/security/plan");

export const posRequest = (ruta, opciones = {}) => request(`/pos/api/${ruta}`, opciones);
export const posCheckout = (payload) =>
  request("/pos/api/checkout", { method: "POST", body: payload });
export const posOpenCashSession = (payload) =>
  request("/pos/api/cash/sessions/open", { method: "POST", body: payload });

// --- Rastreo de piezas: herramienta, equipo, activo de uso -----------------
// El inventario por cantidades no puede decir donde esta el taladro A-014; estas
// rutas trabajan sobre la pieza concreta.
export const getAssets = (params = {}) => request("/assets", { params });
export const getOverdueAssets = () => request("/assets/overdue");
export const getAssetByTag = (tag) => request(`/assets/by-tag/${encodeURIComponent(tag)}`);
export const getAssetHistory = (id) => request(`/assets/${id}`);
export const getProductAssetSummary = (id) => request(`/product/${id}/asset-summary`);
export const createAsset = (payload) => request("/assets", { method: "POST", body: payload });
const accionDePieza = (accion) => (id, payload = {}) =>
  request(`/assets/${id}/${accion}`, { method: "POST", body: payload });
export const assignAsset = accionDePieza("assign");
export const lendAsset = accionDePieza("lend");
export const returnAsset = accionDePieza("return");
export const sendAssetToRepair = accionDePieza("send-to-repair");
export const backAssetFromRepair = accionDePieza("back-from-repair");
export const reportAssetLost = accionDePieza("report-lost");
export const retireAsset = accionDePieza("retire");
export const moveAsset = accionDePieza("move");

export const applyInvoiceInventory = (id, payload = {}) => request(`/invoice/${id}/inventory`, { method: "POST", body: payload });

// --- Cancelacion de CFDI ---------------------------------------------------
// El backend exige llave de idempotencia en cada acto fiscal: una cancelacion
// reintentada por un doble clic no debe llegar dos veces al SAT.
export const getInvoiceCancellation = (id) => request(`/invoice/${id}/cancellation`);
export const requestInvoiceCancellation = (id, payload = {}) =>
  request(`/invoice/${id}/cancellation`, {
    method: "POST",
    body: { idempotency_key: crypto.randomUUID(), ...payload }
  });
export const refreshInvoiceCancellation = (idCancellation) =>
  request(`/invoice/cancellations/${idCancellation}/refresh`, { method: "POST" });

// --- Abonos y complemento de pago ----------------------------------------
export const getInvoiceStatement = (id) => request(`/invoice/${id}/payments`);
export const registerInvoicePayment = (id, payload = {}) =>
  request(`/invoice/${id}/payments`, {
    method: "POST",
    body: { idempotency_key: crypto.randomUUID(), ...payload }
  });
export const getPaymentComplement = (idPayment) =>
  request(`/invoice/payments/${idPayment}/complement`);
export const stampPaymentComplement = (idPayment) =>
  request(`/stamping/invoices/payments/${idPayment}/stamp`, {
    method: "POST",
    body: { idempotency_key: crypto.randomUUID() }
  });

// --- Notas de credito -----------------------------------------------------
export const getInvoiceCreditNotes = (id) => request(`/invoice/${id}/credit-notes`);
export const createInvoiceCreditNote = (id, payload = {}) =>
  request(`/invoice/${id}/credit-notes`, {
    method: "POST",
    body: { idempotency_key: crypto.randomUUID(), ...payload }
  });
export const getInvoiceRelations = (id) => request(`/invoice/${id}/relations`);
export const searchSatProductKeys = (q, limit = 12) => request("/sat/clave-prod-serv", { params: { q, limit } });
export const getSatCatalogStatus = () => request("/sat/clave-prod-serv/status");

export const getAllInvoiceMaterialService = (params = {}) => request("/invoice_material_service/", { params });
export const getInvoiceMaterialService = (id) => request(`/invoice_material_service/${id}`);
export const createInvoiceMaterialService = (payload) => request("/invoice_material_service/", { method: "POST", body: payload });
export const updateInvoiceMaterialService = (id, payload) => request(`/invoice_material_service/${id}`, { method: "PUT", body: payload });
export const deleteInvoiceMaterialService = (id) => request(`/invoice_material_service/${id}`, { method: "DELETE" });

export const getAllKpiDefinition = () => request("/kpi_definition/");
export const queryKpiSnapshot = (params = {}) => request("/kpi_snapshot/query", { params });

// Catalogo completo de KPIs, sin el filtro de permiso puntual -- para poblar
// el selector del gestor de permisos por KPI, no el dashboard.
export const getAllKpiDefinitionUnfiltered = () => request("/kpi_definition/all");
export const getPermissionKpi = (idPermission) => request("/permission_kpi/", { params: { id_permission: idPermission } });
export const createPermissionKpi = (payload) => request("/permission_kpi/", { method: "POST", body: payload });
export const deletePermissionKpi = (id) => request(`/permission_kpi/${id}`, { method: "DELETE" });

export const getAllKpiDashboard = (params = {}) => request("/kpi_dashboard/", { params });
export const createKpiDashboard = (payload) => request("/kpi_dashboard/", { method: "POST", body: payload });
export const updateKpiDashboard = (id, payload) => request(`/kpi_dashboard/${id}`, { method: "PUT", body: payload });
export const deleteKpiDashboard = (id) => request(`/kpi_dashboard/${id}`, { method: "DELETE" });

export const getAllKpiDashboardWidget = (idDashboard) => request(`/kpi_dashboard/${idDashboard}/widgets/`);
export const createKpiDashboardWidget = (idDashboard, payload) => request(`/kpi_dashboard/${idDashboard}/widgets/`, { method: "POST", body: payload });
export const updateKpiDashboardWidget = (id, payload) => request(`/kpi_dashboard_widget/${id}`, { method: "PUT", body: payload });
export const deleteKpiDashboardWidget = (id) => request(`/kpi_dashboard_widget/${id}`, { method: "DELETE" });

export const getAllLevel = (params = {}) => request("/level/", { params });
export const getLevel = (id) => request(`/level/${id}`);
export const createLevel = (payload) => request("/level/", { method: "POST", body: payload });
export const updateLevel = (id, payload) => request(`/level/${id}`, { method: "PUT", body: payload });
export const deleteLevel = (id) => request(`/level/${id}`, { method: "DELETE" });

export const getAllLocation = (params = {}) => request("/location/", { params });
export const getLocation = (id) => request(`/location/${id}`);
export const createLocation = (payload) => request("/location/", { method: "POST", body: payload });
export const updateLocation = (id, payload) => request(`/location/${id}`, { method: "PUT", body: payload });
export const deleteLocation = (id) => request(`/location/${id}`, { method: "DELETE" });

export const getAllLocationType = (params = {}) => request("/location_type/", { params });
export const getLocationType = (id) => request(`/location_type/${id}`);
export const createLocationType = (payload) => request("/location_type/", { method: "POST", body: payload });
export const updateLocationType = (id, payload) => request(`/location_type/${id}`, { method: "PUT", body: payload });
export const deleteLocationType = (id) => request(`/location_type/${id}`, { method: "DELETE" });

// --- tipos de material -----------------------------------------------------
// El tercer eje del material, junto a la familia y la marca.
// Los tipos DE UNA FAMILIA: es lo que necesita el alta de un material, porque
// ofrecer los de todas permite capturar "Cemento de tipo De cruz".

// --- vales de almacen ------------------------------------------------------
export const createWarehouseVoucher = (payload) => request("/vouchers", { method: "POST", body: payload });
// El PREVALE: el material pedido, en borrador, sin mover el almacen. Ruta
// aparte y no una bandera en el cuerpo, porque cada camino lleva su permiso --
// `warehouse_prevoucher` aqui, `warehouse_voucher` en el de arriba.
export const createWarehousePrevoucher = (payload) => request("/prevouchers", { method: "POST", body: payload });
// Y el acto que convierte el borrador en vale, que es el que saca el material.
// Lo guarda `warehouse_voucher_authorize`, que solo tiene el jefe de almacen.
export const authorizeWarehouseVoucher = (id, payload = {}) =>
  request(`/vouchers/${id}/authorize`, { method: "POST", body: payload });
export const getWarehouseVoucher = (id) => request(`/vouchers/${id}`);

// El vale para imprimir y firmar. Pide `read`, la misma que ver el vale en
// pantalla: quien puede leerlo puede imprimirlo, porque es el mismo dato.
export const downloadWarehouseVoucherPdf = (id) => requestBlob(`/vouchers/${id}/pdf`);
export const getOverdueVoucherLines = () => request("/vouchers/overdue");
// Cuantas piezas hay en cada estado, ahora mismo. Una consulta agrupada, no
// una por estado: la pantalla del almacen se abre muchas veces al dia.
export const getAssetStatusSummary = (params = {}) => request("/assets/summary", { params });
export const closeWarehouseVoucherLine = (idLine, payload = {}) =>
  request(`/vouchers/lines/${idLine}/close`, { method: "POST", body: payload });

export const getAllMaterial = (params = {}) => request("/material/", { params });
export const getMaterial = (id) => request(`/material/${id}`);
export const createMaterial = (payload) => request("/material/", { method: "POST", body: payload });
export const updateMaterial = (id, payload) => request(`/material/${id}`, { method: "PUT", body: payload });
export const deleteMaterial = (id) => request(`/material/${id}`, { method: "DELETE" });

export const getAllMaterialComponent = (params = {}) => request("/material_component/", { params });
export const getMaterialComponent = (id) => request(`/material_component/${id}`);
export const createMaterialComponent = (payload) => request("/material_component/", { method: "POST", body: payload });
export const updateMaterialComponent = (id, payload) => request(`/material_component/${id}`, { method: "PUT", body: payload });
export const deleteMaterialComponent = (id) => request(`/material_component/${id}`, { method: "DELETE" });

export const getAllMovement = (params = {}) => request("/movement/", { params });
export const getMovement = (id) => request(`/movement/${id}`);
export const createMovement = (payload) => request("/movement/", { method: "POST", body: payload });
export const updateMovement = (id, payload) => request(`/movement/${id}`, { method: "PUT", body: payload });
export const deleteMovement = (id) => request(`/movement/${id}`, { method: "DELETE" });

export const getAllNmFieldPermission = (params = {}) => isPrivilegedPermissionUser() ? request("/nm_field_permission/", { params }) : getMyPermissions().then((payload) => ({ items: payload.field_permissions || [], page: 1, pages: 1, per_page: (payload.field_permissions || []).length, total: (payload.field_permissions || []).length }));
export const getNmFieldPermission = (id) => request(`/nm_field_permission/${id}`);
export const createNmFieldPermission = (payload) => request("/nm_field_permission/", { method: "POST", body: payload });
export const updateNmFieldPermission = (id, payload) => request(`/nm_field_permission/${id}`, { method: "PUT", body: payload });
export const deleteNmFieldPermission = (id) => request(`/nm_field_permission/${id}`, { method: "DELETE" });

export const getAllNmIncidentProduct = (params = {}) => request("/nm_incident_product/", { params });
export const getNmIncidentProduct = (id) => request(`/nm_incident_product/${id}`);
export const createNmIncidentProduct = (payload) => request("/nm_incident_product/", { method: "POST", body: payload });
export const updateNmIncidentProduct = (id, payload) => request(`/nm_incident_product/${id}`, { method: "PUT", body: payload });
export const deleteNmIncidentProduct = (id) => request(`/nm_incident_product/${id}`, { method: "DELETE" });

export const getAllNmSurveyUser = (params = {}) => request("/nm_survey_user/", { params });
export const getNmSurveyUser = (id) => request(`/nm_survey_user/${id}`);
export const createNmSurveyUser = (payload) => request("/nm_survey_user/", { method: "POST", body: payload });
export const updateNmSurveyUser = (id, payload) => request(`/nm_survey_user/${id}`, { method: "PUT", body: payload });
export const deleteNmSurveyUser = (id) => request(`/nm_survey_user/${id}`, { method: "DELETE" });

export const getAllNmTemplateTask = (params = {}) => request("/nm_template_task/", { params });
export const getNmTemplateTask = (id) => request(`/nm_template_task/${id}`);
export const createNmTemplateTask = (payload) => request("/nm_template_task/", { method: "POST", body: payload });
export const updateNmTemplateTask = (id, payload) => request(`/nm_template_task/${id}`, { method: "PUT", body: payload });
export const deleteNmTemplateTask = (id) => request(`/nm_template_task/${id}`, { method: "DELETE" });

export const getAllPayrollConcept = (params = {}) => request("/payroll_concept/", { params });
export const getPayrollConcept = (id) => request(`/payroll_concept/${id}`);
export const createPayrollConcept = (payload) => request("/payroll_concept/", { method: "POST", body: payload });
export const updatePayrollConcept = (id, payload) => request(`/payroll_concept/${id}`, { method: "PUT", body: payload });
export const deletePayrollConcept = (id) => request(`/payroll_concept/${id}`, { method: "DELETE" });

export const getAllPayrollDetail = (params = {}) => request("/payroll_detail/", { params });
export const getPayrollDetail = (id) => request(`/payroll_detail/${id}`);
export const createPayrollDetail = (payload) => request("/payroll_detail/", { method: "POST", body: payload });
export const updatePayrollDetail = (id, payload) => request(`/payroll_detail/${id}`, { method: "PUT", body: payload });
export const deletePayrollDetail = (id) => request(`/payroll_detail/${id}`, { method: "DELETE" });

export const getAllPayrollMovement = (params = {}) => request("/payroll_movement/", { params });
export const getPayrollMovement = (id) => request(`/payroll_movement/${id}`);
export const createPayrollMovement = (payload) => request("/payroll_movement/", { method: "POST", body: payload });
export const updatePayrollMovement = (id, payload) => request(`/payroll_movement/${id}`, { method: "PUT", body: payload });
export const deletePayrollMovement = (id) => request(`/payroll_movement/${id}`, { method: "DELETE" });

export const getAllPayrollPeriod = (params = {}) => request("/payroll_period/", { params });
export const getPayrollPeriod = (id) => request(`/payroll_period/${id}`);
export const createPayrollPeriod = (payload) => request("/payroll_period/", { method: "POST", body: payload });
export const updatePayrollPeriod = (id, payload) => request(`/payroll_period/${id}`, { method: "PUT", body: payload });
export const deletePayrollPeriod = (id) => request(`/payroll_period/${id}`, { method: "DELETE" });

export const getAllPermission = (params = {}) => request("/permission/", { params });
export const getPermission = (id) => request(`/permission/${id}`);
export const createPermission = (payload) => request("/permission/", { method: "POST", body: payload });
export const updatePermission = (id, payload) => request(`/permission/${id}`, { method: "PUT", body: payload });
export const deletePermission = (id) => request(`/permission/${id}`, { method: "DELETE" });

export const getAllProduct = (params = {}) => request("/product/", { params });
export const getProduct = (id) => request(`/product/${id}`);
export const createProduct = (payload) => request("/product/", { method: "POST", body: payload });
export const updateProduct = (id, payload) => request(`/product/${id}`, { method: "PUT", body: payload });
export const deleteProduct = (id) => request(`/product/${id}`, { method: "DELETE" });

export const getAllProductFamily = (params = {}) => request("/product_family/", { params });
export const getProductFamily = (id) => request(`/product_family/${id}`);
export const createProductFamily = (payload) => request("/product_family/", { method: "POST", body: payload });
export const updateProductFamily = (id, payload) => request(`/product_family/${id}`, { method: "PUT", body: payload });
export const deleteProductFamily = (id) => request(`/product_family/${id}`, { method: "DELETE" });

export const getAllProductSaleConfig = (params = {}) => request("/product_sale_config/", { params });
export const getProductSaleConfig = (id) => request(`/product_sale_config/${id}`);
export const createProductSaleConfig = (payload) => request("/product_sale_config/", { method: "POST", body: payload });
export const updateProductSaleConfig = (id, payload) => request(`/product_sale_config/${id}`, { method: "PUT", body: payload });
export const deleteProductSaleConfig = (id) => request(`/product_sale_config/${id}`, { method: "DELETE" });

export const getAllProyect = (params = {}) => request("/proyect/", { params });

// Solo id+folio+titulo, sin permiso de entidad -- igual que `getUserOptions` --
// para que el selector de "Obra" en un vale funcione con roles que no tienen
// el modulo operaciones (Almacenista).
export const getProyectOptions = () => request("/proyect/options");
export const getProyect = (id) => request(`/proyect/${id}`);
export const createProyect = (payload) => request("/proyect/", { method: "POST", body: payload });
export const updateProyect = (id, payload) => request(`/proyect/${id}`, { method: "PUT", body: payload });
export const deleteProyect = (id) => request(`/proyect/${id}`, { method: "DELETE" });
export const transitionProyect = (id, payload) => request(`/proyect/${id}/transition`, { method: "POST", body: payload });
export const addProyectMessage = (id, payload) => request(`/proyect/${id}/messages`, { method: "POST", body: payload });
// El supervisor se hace cargo del proyecto, y lo suelta. No es un PUT sobre
// `id_supervisor` a proposito: el servidor pone al actor, nunca a quien diga el
// cuerpo, que es lo que hace que sea TOMAR y no asignar.
export const takeProyect = (id) => request(`/proyect/${id}/take`, { method: "POST" });
export const releaseProyect = (id) => request(`/proyect/${id}/release`, { method: "POST" });

// Adjuntos de requerimientos (PDF/DOCX), aparte del modulo /document generico
// -- ver el comentario de `add_project_document` en el backend.
export const getProyectDocuments = (id) => request(`/proyect/${id}/documents`);
export const uploadProyectDocument = (id, file, title) => {
  const formData = new FormData();
  formData.append("file", file);
  if (title) formData.append("title", title);
  return request(`/proyect/${id}/documents`, { method: "POST", body: formData });
};
export const deleteProyectDocument = (id) => request(`/proyect/documents/${id}`, { method: "DELETE" });
export const downloadProyectDocument = (id) => requestBlob(`/proyect/documents/${id}/content`);

// El recorrido de GERENCIA, aparte del de taller: un proyecto puede estar
// entregado y sin cobrar, y son dos maquinas de estados distintas.
export const transitionProyectManagement = (id, payload) =>
  request(`/proyect/${id}/management-transition`, { method: "POST", body: payload });

// Las parcialidades de pago. Cuelgan del proyecto porque lo que se acuerda es
// "40% al pedir ESTE trabajo": fuera del proyecto la cifra no dice nada.
export const getProyectPayments = (id) => request(`/proyect/${id}/payments`);
export const addProyectPayment = (id, payload) =>
  request(`/proyect/${id}/payments`, { method: "POST", body: payload });
export const settleProyectPayment = (idPago, payload) =>
  request(`/proyect/payments/${idPago}`, { method: "PUT", body: payload });
export const deleteProyectPayment = (idPago) =>
  request(`/proyect/payments/${idPago}`, { method: "DELETE" });

export const getAllPublicApiKey = (params = {}) => request("/public_api_key/", { params });
export const getPublicApiKey = (id) => request(`/public_api_key/${id}`);
export const createPublicApiKey = (payload) => request("/public_api_key/", { method: "POST", body: payload });
export const updatePublicApiKey = (id, payload) => request(`/public_api_key/${id}`, { method: "PUT", body: payload });
export const deletePublicApiKey = (id) => request(`/public_api_key/${id}`, { method: "DELETE" });

export const getAllService = (params = {}) => request("/service/", { params });
export const getService = (id) => request(`/service/${id}`);
export const createService = (payload) => request("/service/", { method: "POST", body: payload });
export const updateService = (id, payload) => request(`/service/${id}`, { method: "PUT", body: payload });
export const deleteService = (id) => request(`/service/${id}`, { method: "DELETE" });

export const getAllStatus = (params = {}) => request("/status/", { params });
export const getStatus = (id) => request(`/status/${id}`);
export const createStatus = (payload) => request("/status/", { method: "POST", body: payload });
export const updateStatus = (id, payload) => request(`/status/${id}`, { method: "PUT", body: payload });
export const deleteStatus = (id) => request(`/status/${id}`, { method: "DELETE" });

export const getAllSubdepartment = (params = {}) => request("/subdepartment/", { params });
export const getSubdepartment = (id) => request(`/subdepartment/${id}`);
export const createSubdepartment = (payload) => request("/subdepartment/", { method: "POST", body: payload });
export const updateSubdepartment = (id, payload) => request(`/subdepartment/${id}`, { method: "PUT", body: payload });
export const deleteSubdepartment = (id) => request(`/subdepartment/${id}`, { method: "DELETE" });

export const getAllSurveyMultipleAnswer = (params = {}) => request("/survey_multiple_answer/", { params });
export const getSurveyMultipleAnswer = (id) => request(`/survey_multiple_answer/${id}`);
export const createSurveyMultipleAnswer = (payload) => request("/survey_multiple_answer/", { method: "POST", body: payload });
export const updateSurveyMultipleAnswer = (id, payload) => request(`/survey_multiple_answer/${id}`, { method: "PUT", body: payload });
export const deleteSurveyMultipleAnswer = (id) => request(`/survey_multiple_answer/${id}`, { method: "DELETE" });

export const getAllSurveyQuestion = (params = {}) => request("/survey_question/", { params });
export const getSurveyQuestion = (id) => request(`/survey_question/${id}`);
export const createSurveyQuestion = (payload) => request("/survey_question/", { method: "POST", body: payload });
export const updateSurveyQuestion = (id, payload) => request(`/survey_question/${id}`, { method: "PUT", body: payload });
export const deleteSurveyQuestion = (id) => request(`/survey_question/${id}`, { method: "DELETE" });

export const getAllTask = (params = {}) => request("/task/", { params });
export const getTask = (id) => request(`/task/${id}`);
export const createTask = (payload) => request("/task/", { method: "POST", body: payload });
export const updateTask = (id, payload) => request(`/task/${id}`, { method: "PUT", body: payload });
export const deleteTask = (id) => request(`/task/${id}`, { method: "DELETE" });

export const getAllTaskNote = (params = {}) => request("/task_note/", { params });
export const getTaskNote = (id) => request(`/task_note/${id}`);
export const createTaskNote = (payload) => request("/task_note/", { method: "POST", body: payload });
export const updateTaskNote = (id, payload) => request(`/task_note/${id}`, { method: "PUT", body: payload });
export const deleteTaskNote = (id) => request(`/task_note/${id}`, { method: "DELETE" });

export const getAllTaskType = (params = {}) => request("/task_type/", { params });
export const getTaskType = (id) => request(`/task_type/${id}`);
export const createTaskType = (payload) => request("/task_type/", { method: "POST", body: payload });
export const updateTaskType = (id, payload) => request(`/task_type/${id}`, { method: "PUT", body: payload });
export const deleteTaskType = (id) => request(`/task_type/${id}`, { method: "DELETE" });

export const getAllTemplate = (params = {}) => request("/template/", { params });
export const getTemplate = (id) => request(`/template/${id}`);
export const createTemplate = (payload) => request("/template/", { method: "POST", body: payload });
export const updateTemplate = (id, payload) => request(`/template/${id}`, { method: "PUT", body: payload });
export const deleteTemplate = (id) => request(`/template/${id}`, { method: "DELETE" });

export const getAllTheme = (params = {}) => request("/theme/", { params });
export const getTheme = (id) => request(`/theme/${id}`);
export const createTheme = (payload) => request("/theme/", { method: "POST", body: payload });
export const updateTheme = (id, payload) => request(`/theme/${id}`, { method: "PUT", body: payload });
export const deleteTheme = (id) => request(`/theme/${id}`, { method: "DELETE" });

export const getAllTicket = (params = {}) => request("/ticket/", { params });
export const getTicket = (id) => request(`/ticket/${id}`);
export const createTicket = (payload) => request("/ticket/", { method: "POST", body: payload });
export const updateTicket = (id, payload) => request(`/ticket/${id}`, { method: "PUT", body: payload });
export const deleteTicket = (id) => request(`/ticket/${id}`, { method: "DELETE" });

export const getAllUnit = (params = {}) => request("/unit/", { params });
export const getUnit = (id) => request(`/unit/${id}`);
export const createUnit = (payload) => request("/unit/", { method: "POST", body: payload });
export const updateUnit = (id, payload) => request(`/unit/${id}`, { method: "PUT", body: payload });
export const deleteUnit = (id) => request(`/unit/${id}`, { method: "DELETE" });

export const getAllUser = (params = {}) => request("/user/", { params });
// Solo id+nombre, para selectores (ej. "Responsable" en un vale de almacen
// o el lider de un proyecto) -- cualquier usuario autenticado puede
// llamarlo, sin exigir el permiso de lectura completo de user.
export const getUserOptions = () => request("/user/options");
export const getUser = (id) => request(`/user/${id}`);
export const createUser = (payload) => request("/user/", { method: "POST", body: payload });
export const updateUser = (id, payload) => request(`/user/${id}`, { method: "PUT", body: payload });
export const deleteUser = (id) => request(`/user/${id}`, { method: "DELETE" });

export const getAllUserMfa = (params = {}) => request("/user_mfa/", { params });
export const getUserMfa = (id) => request(`/user_mfa/${id}`);
export const createUserMfa = (payload) => request("/user_mfa/", { method: "POST", body: payload });
export const updateUserMfa = (id, payload) => request(`/user_mfa/${id}`, { method: "PUT", body: payload });
export const deleteUserMfa = (id) => request(`/user_mfa/${id}`, { method: "DELETE" });
export const updateInvoiceLineAuthorization = (id, payload) => request(`/invoice/line-authorization/${id}`, { method: "PATCH", body: payload });
export const getSalesCatalogProducts = (params = {}) => request("/sales-catalog/products", { params });
export const previewSalesCatalogProductPrice = (id) => request(`/sales-catalog/products/${id}/preview-price`);
export const upsertSalesCatalogProductConfig = (id, payload) => request(`/sales-catalog/products/${id}/config`, { method: "PATCH", body: payload });
export const bulkSalesCatalogMargin = (payload) => request("/sales-catalog/products/bulk-margin", { method: "POST", body: payload });
export const bulkSalesCatalogPublish = (payload) => request("/sales-catalog/products/bulk-publish", { method: "POST", body: payload });
export const getSalesCatalogApiKeys = () => request("/sales-catalog/api-keys");
export const createSalesCatalogApiKey = (payload) => request("/sales-catalog/api-keys", { method: "POST", body: payload });
export const updateSalesCatalogApiKey = (id, payload) => request(`/sales-catalog/api-keys/${id}`, { method: "PATCH", body: payload });
export const revokeSalesCatalogApiKey = (id) => request(`/sales-catalog/api-keys/${id}/revoke`, { method: "POST" });
export const getWebShoppers = (params = {}) => request("/web-shoppers", { params });
export const getWebShopper = (id) => request(`/web-shoppers/${id}`);
export const deactivateWebShopper = (id) => request(`/web-shoppers/${id}/deactivate`, { method: "PATCH" });
export const reactivateWebShopper = (id) => request(`/web-shoppers/${id}/reactivate`, { method: "PATCH" });
export const getKronosAttendance = (payload) => request("/kronos/attendance", { method: "POST", body: payload });
export const getKronosPeople = (payload) => request("/kronos/people", { method: "POST", body: payload });
export const saveKronosPerson = (payload) => request("/kronos/people", { method: "PUT", body: payload });
export const deleteKronosPerson = (employeeNo, payload) => request(`/kronos/people/${encodeURIComponent(employeeNo)}`, { method: "DELETE", body: payload });
export { urlDeArchivo } from "./client";

// --- operaciones: catalogo, transiciones y bitacora de tarea ---------------
// De la otra corriente de trabajo. Se perdieron al separar los cambios de
// inventario de los de operaciones y se devuelven tal como estaban.
// Las maquinas de estado de Operaciones -proyecto, tarea e incidencia- tal como
// las valida el servidor. La pantalla de proyectos llevaba su propia copia del
// mapa de transiciones en JavaScript: dos copias divergen y la interfaz acaba
// ofreciendo un paso que el servidor rechaza.
export const getOperationsCatalog = () => request("/operations/catalog");
// Cambio de estatus guiado por la maquina de estados del servidor, igual que
// `transitionProyect`. El PUT suelto sobre `task_status` sigue existiendo, pero
// no valida la transicion ni guarda el motivo.
export const transitionTask = (id, payload) => request(`/task/${id}/transition`, { method: "POST", body: payload });
// La bitacora de UNA tarea. La relacion la pone la ruta, asi que la pantalla no
// tiene que saber que la columna del padre se llama `id_task`.
export const getTaskNotes = (id) => request(`/task/${id}/notes`);
export const addTaskNote = (id, payload) => request(`/task/${id}/notes`, { method: "POST", body: payload });

// --- lotes y caducidad ---
//
// El lote no tiene un POST propio: lo crea la entrada de mercancia al nombrarlo.
// Encender el control SI es una operacion aparte, porque si el producto ya tiene
// existencia hay que meterla en un lote de apertura o se queda fuera de todo
// lote, y entonces no se puede despachar.
export const getProductLots = (idProduct) => request(`/product/${idProduct}/lots`);
export const getExpiringStock = (params = {}) => request("/inventory/expiring", { params });
export const getLotReconciliation = (idProduct) =>
  request(`/product/${idProduct}/lots/reconciliation`);
export const enableLotControl = (idProduct, payload = {}) =>
  request(`/product/${idProduct}/lot-control`, { method: "POST", body: payload });
export const disableLotControl = (idProduct) =>
  request(`/product/${idProduct}/lot-control`, { method: "DELETE" });

// La lista de vales, buscable por folio o por responsable. El folio es el
// numero con el que la gente conoce el papel: el del sistema anterior cuando lo
// trae, y si no el identificador.
export const listWarehouseVouchers = (params = {}) => request("/vouchers", { params });
