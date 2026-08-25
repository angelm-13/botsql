// Cliente HTTP central de la app: todas las llamadas al backend pasan por
// request(), que manda la cookie de sesion (credentials:'include'), agrega
// el header CSRF en peticiones que mutan datos, y convierte cualquier
// respuesta de error del backend ({error:{message,code,status}}, ver
// backend/app/utils/errors.py) en un Error de JS normal, para poder usar
// try/catch en los componentes.
import type {
  User, Table, Visit, Dish, Guisado, Category, Order, OrderItem, CashSession,
  StaffMember, AuditLog, InventoryItem, InventoryMovement, Invoice, Company, PacConfig,
  Paginated, DashboardData, KpisData, SalesReport, InventorySummary, InvoiceSalesSummary,
  PayVisitResult, DemoStatus,
} from '../types/api'

const API_URL = import.meta.env.VITE_API_URL || '/api'

export const storage = {
  setSession(user: User): void { localStorage.setItem('user', JSON.stringify(user)) },
  clear(): void { localStorage.removeItem('user') },
  user(): User | null { try { return JSON.parse(localStorage.getItem('user') || 'null') } catch { return null } },
  // Bandera que se guarda justo antes de recargar la pagina por sesion
  // expirada, para que el Login pueda mostrar un aviso amigable una sola vez.
  consumeExpiredFlag(): boolean {
    const was = sessionStorage.getItem(SESSION_EXPIRED_FLAG) === '1'
    sessionStorage.removeItem(SESSION_EXPIRED_FLAG)
    return was
  },
}

const SESSION_EXPIRED_FLAG = 'app_session_expired'
// Codigos que el backend devuelve cuando el JWT ya no sirve (ver
// app/__init__.py: expired_token_loader/invalid_token_loader/unauthorized_loader;
// una cookie CSRF ausente o invalida tambien cae en 'token_missing', ver
// unauthorized_loader).
const AUTH_ERROR_CODES = ['token_expired', 'token_invalid', 'token_missing']

// El JWT viaja en una cookie httpOnly (invisible para JS, ver
// backend/app/routes/auth.py:login) protegida con el patron de doble-submit
// de Flask-JWT-Extended: una segunda cookie NO-httpOnly (csrf_access_token,
// esta si legible por JS) que hay que reenviar en un header en cada
// peticion que MUTA datos -- el backend solo la exige en POST/PUT/PATCH/
// DELETE (JWT_CSRF_METHODS), nunca en GET, asi que el polling normal de la
// app no necesita este header.
const CSRF_COOKIE_NAME = 'csrf_access_token'
const CSRF_HEADER_NAME = 'X-CSRF-TOKEN'
const MUTATING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

const REFRESH_CSRF_COOKIE_NAME = 'csrf_refresh_token'

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

// Promesa del refresco EN VUELO, compartida por todas las peticiones que
// fallen a la vez. Sin esto, la app dispararia una avalancha de refrescos:
// varias pantallas hacen polling cada 3-8 segundos (mesas, tablero de
// cocina, entregas, KPIs), asi que en el instante en que el token de acceso
// expira hay media docena de peticiones fallando al mismo tiempo, y cada
// una pediria su propio token nuevo.
let refreshInFlight: Promise<boolean> | null = null

/** Pide un token de acceso nuevo usando la cookie de refresco. Devuelve si
 * lo logro. Nunca lanza: quien la llama decide que hacer si falla. */
function refreshAccessToken(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight
  refreshInFlight = (async () => {
    try {
      const headers: Record<string, string> = {}
      // /auth/refresh es POST, asi que exige CSRF -- y usa la cookie CSRF
      // del token de REFRESCO, no la del de acceso (son dos distintas).
      const csrf = readCookie(REFRESH_CSRF_COOKIE_NAME)
      if (csrf) headers[CSRF_HEADER_NAME] = csrf
      const res = await fetch(`${API_URL}/auth/refresh`, { method: 'POST', headers, credentials: 'include' })
      return res.ok
    } catch {
      return false
    } finally {
      // Se limpia SIEMPRE para que un fallo temporal (red intermitente) no
      // deje la app sin poder volver a intentar el refresco nunca mas.
      refreshInFlight = null
    }
  })()
  return refreshInFlight
}

/** Hace un fetch a `${API_URL}${path}` mandando la cookie de sesion (credentials:'include'),
 * agrega el header CSRF en peticiones que mutan datos, y lanza un Error legible si la
 * respuesta no fue exitosa. */
async function request<T>(path: string, options: RequestInit = {}, isRetry = false): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(options.headers as Record<string, string> || {}) }
  const method = (options.method || 'GET').toUpperCase()
  if (MUTATING_METHODS.has(method)) {
    const csrfToken = readCookie(CSRF_COOKIE_NAME)
    if (csrfToken) headers[CSRF_HEADER_NAME] = csrfToken
  }
  const res = await fetch(`${API_URL}${path}`, { ...options, headers, credentials: 'include' })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const code = data?.error?.code
    // El token de acceso dura 30 minutos (ver JWT_ACCESS_MINUTES en
    // backend/app/config.py), asi que expirar a mitad de un turno es lo
    // NORMAL, no una anomalia: se intenta renovarlo con la cookie de
    // refresco y se reintenta la peticion una sola vez, sin que el usuario
    // note nada. `isRetry` corta cualquier posibilidad de bucle infinito si
    // el token nuevo tambien viniera rechazado.
    if (code === 'token_expired' && !isRetry && storage.user()) {
      if (await refreshAccessToken()) return request<T>(path, options, true)
    }
    // Antes esto se perdia como un error generico ("API error") en cualquier
    // pantalla que hiciera polling, dejandola vacia sin explicacion. Ahora se
    // detecta la sesion invalida/expirada, se limpia y se manda al login con
    // un aviso claro (ver Login() en main.jsx). Se compara contra storage.user()
    // (ya no hay un token legible por JS que revisar) para no disparar este
    // flujo si nunca hubo sesion en primer lugar.
    if (storage.user() && AUTH_ERROR_CODES.includes(code)) {
      sessionStorage.setItem(SESSION_EXPIRED_FLAG, '1')
      storage.clear()
      window.location.reload()
      return new Promise<T>(() => {}) // evita que el resto del componente siga con datos a medias
    }
    throw new Error(data?.error?.message || 'API error')
  }
  return data as T
}

export const api = {
  // auth
  login: (username: string, password: string) =>
    request<{ user: User }>('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  logout: () => request<{ message: string }>('/auth/logout', { method: 'POST' }),
  // Publico (no requiere sesion, ver backend/app/routes/demo.py) -- el banner
  // de la version freemium se muestra hasta en la pantalla de login.
  demoStatus: () => request<DemoStatus>('/demo/status'),
  changePassword: (current_password: string, new_password: string) =>
    request<{ message: string }>('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password, new_password }),
    }),

  // mesas
  tables: () => request<{ items: Table[] }>('/tables'),

  // visitas (mesa atendida por el mesero)
  visits: (params = '') => request<{ items: Visit[] }>(`/visits${params}`),
  visit: (id: number) => request<Visit>(`/visits/${id}`),
  // tz_offset_minutes viaja en cada alta (mesa/para llevar/comensal) para
  // que el folio diario (daily_number) del backend reinicie exactamente a
  // la medianoche LOCAL del dispositivo, no a la medianoche UTC del servidor.
  createVisit: (table_number: number, diners_count: number) =>
    request<Visit>('/visits', { method: 'POST', body: JSON.stringify({ table_number, diners_count, tz_offset_minutes: new Date().getTimezoneOffset() }) }),
  createTakeoutVisit: (customer_name: string) =>
    request<Visit>('/visits', { method: 'POST', body: JSON.stringify({ is_takeout: true, customer_name, tz_offset_minutes: new Date().getTimezoneOffset() }) }),
  addDiner: (visitId: number) =>
    request<Visit>(`/visits/${visitId}/diners`, { method: 'POST', body: JSON.stringify({ tz_offset_minutes: new Date().getTimezoneOffset() }) }),
  removeDiner: (visitId: number, dinerIndex: number) => request<Visit>(`/visits/${visitId}/diners/${dinerIndex}`, { method: 'DELETE' }),
  closeVisit: (visitId: number) => request<Visit>(`/visits/${visitId}/close`, { method: 'POST' }),
  payVisit: (visitId: number, payload: Record<string, unknown>) => request<PayVisitResult>(`/visits/${visitId}/pay`, { method: 'POST', body: JSON.stringify(payload) }),
  unpayVisit: (visitId: number, orderIds: number[], reason: string) =>
    request<{ visit: Visit; orders_reverted: number[] }>(`/visits/${visitId}/unpay`, { method: 'POST', body: JSON.stringify({ order_ids: orderIds, reason }) }),

  // menu
  dishes: (params = '') => request<Paginated<Dish>>(`/menu/dishes${params}`),
  createDish: (payload: Partial<Dish>) => request<Dish>('/menu/dishes', { method: 'POST', body: JSON.stringify(payload) }),
  updateDish: (id: number, payload: Partial<Dish>) => request<Dish>(`/menu/dishes/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteDish: (id: number) => request<{ deleted: true }>(`/menu/dishes/${id}`, { method: 'DELETE' }),
  guisados: () => request<{ items: Guisado[] }>('/menu/guisados'),
  createGuisado: (name: string) => request<Guisado>('/menu/guisados', { method: 'POST', body: JSON.stringify({ name }) }),
  updateGuisado: (id: number, payload: Partial<Guisado>) => request<Guisado>(`/menu/guisados/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteGuisado: (id: number) => request<{ deleted: true }>(`/menu/guisados/${id}`, { method: 'DELETE' }),
  categories: () => request<{ items: Category[] }>('/menu/categories'),
  createCategory: (payload: Partial<Category>) => request<Category>('/menu/categories', { method: 'POST', body: JSON.stringify(payload) }),
  updateCategory: (id: number, payload: Partial<Category>) => request<Category>(`/menu/categories/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteCategory: (id: number) => request<{ deleted: true }>(`/menu/categories/${id}`, { method: 'DELETE' }),

  // ordenes (ticket de un comensal)
  orders: (params = '') => request<Paginated<Order>>(`/orders${params}`),
  order: (id: number) => request<Order>(`/orders/${id}`),
  addItem: (orderId: number, payload: Record<string, unknown>) =>
    request<Order & { reopened_for_kitchen: boolean }>(`/orders/${orderId}/items`, { method: 'POST', body: JSON.stringify(payload) }),
  removeItem: (orderId: number, itemId: number) => request<Order>(`/orders/${orderId}/items/${itemId}`, { method: 'DELETE' }),
  sendToKitchen: (orderId: number) => request<Order>(`/orders/${orderId}/send`, { method: 'POST' }),
  updateOrderStatus: (id: number, status: string) => request<Order>(`/orders/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  updateItemStatus: (orderId: number, itemId: number, status: string) =>
    request<Order>(`/orders/${orderId}/items/${itemId}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  cancelItem: (orderId: number, itemId: number, reason: string) =>
    request<Order>(`/orders/${orderId}/items/${itemId}/cancel`, { method: 'PATCH', body: JSON.stringify({ reason }) }),
  cancelledItems: (limit = 50) => request<{ items: OrderItem[] }>(`/orders/cancelled?limit=${limit}`),
  pay: (id: number, payload: Record<string, unknown>) => request<Order>(`/orders/${id}/pay`, { method: 'POST', body: JSON.stringify(payload) }),
  unpay: (id: number, reason: string) => request<Order>(`/orders/${id}/unpay`, { method: 'POST', body: JSON.stringify({ reason }) }),

  // cocina
  // `truncated`: true si hay mas platillos activos que el limite del tablero
  // (ver KITCHEN_BOARD_LIMIT en backend/app/routes/kitchen.py) -- el
  // querystring ?per_page= de aqui se quito porque el backend nunca lo leia
  // (era un limite fijo en el codigo), asi que mandarlo era enganoso.
  kitchenBoard: () => request<{ items: OrderItem[]; truncated: boolean }>('/kitchen/board'),

  // caja / administracion
  // Mandamos el desfase de zona horaria del navegador (en minutos) para que
  // el backend calcule 'hoy' y las horas de los pedidos con la hora local
  // real del dispositivo del usuario, no con el reloj UTC del servidor.
  kpis: () => request<KpisData>(`/cashier/kpis?tz_offset_minutes=${new Date().getTimezoneOffset()}`),
  dashboard: () => request<DashboardData>(`/cashier/dashboard?tz_offset_minutes=${new Date().getTimezoneOffset()}`),
  reports: (params = '') => request<SalesReport>(`/cashier/reports${params}`),
  registerCurrent: () => request<CashSession | null>('/cashier/register/current'),
  registerHistory: () => request<{ items: CashSession[] }>('/cashier/register/history'),
  openRegister: (opening_amount: number) => request<CashSession>('/cashier/register/open', { method: 'POST', body: JSON.stringify({ opening_amount }) }),
  closeRegister: (closing_amount: number, notes?: string) =>
    request<CashSession>('/cashier/register/close', { method: 'POST', body: JSON.stringify({ closing_amount, notes }) }),

  // administracion de usuarios (solo rol admin): alta/baja de meseros/cajeros/etc,
  // sin tener que editar .env ni volver a correr seed.py.
  staff: () => request<{ items: StaffMember[] }>('/admin/staff'),
  createStaff: (payload: Record<string, unknown>) => request<StaffMember>('/admin/staff', { method: 'POST', body: JSON.stringify(payload) }),
  updateStaff: (userId: number, payload: Record<string, unknown>) => request<StaffMember>(`/admin/staff/${userId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deactivateStaff: (userId: number) => request<User>(`/admin/staff/${userId}/deactivate`, { method: 'POST' }),
  activateStaff: (userId: number) => request<User>(`/admin/staff/${userId}/activate`, { method: 'POST' }),
  deleteStaff: (userId: number) => request<{ deleted: true }>(`/admin/staff/${userId}`, { method: 'DELETE' }),

  // bitacora de auditoria (oculta, solo rol superadmin)
  auditLog: (params = '') => request<Paginated<AuditLog>>(`/admin/audit${params}`),

  // inventario (cajero/admin/superadmin): catalogo de insumos + bitacora
  // de movimientos (entradas, salidas, mermas, ajustes)
  inventoryItems: (params = '') => request<Paginated<InventoryItem>>(`/inventory/items${params}`),
  createInventoryItem: (payload: Partial<InventoryItem>) => request<InventoryItem>('/inventory/items', { method: 'POST', body: JSON.stringify(payload) }),
  updateInventoryItem: (id: number, payload: Partial<InventoryItem>) => request<InventoryItem>(`/inventory/items/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteInventoryItem: (id: number) => request<{ deleted: true }>(`/inventory/items/${id}`, { method: 'DELETE' }),
  inventoryMovements: (params = '') => request<Paginated<InventoryMovement>>(`/inventory/movements${params}`),
  createInventoryMovement: (payload: Record<string, unknown>) =>
    request<InventoryMovement & { item: InventoryItem }>('/inventory/movements', { method: 'POST', body: JSON.stringify(payload) }),
  inventorySummary: () => request<InventorySummary>('/inventory/summary'),

  // facturacion CFDI (cajero/admin/superadmin)
  invoiceCatalogs: () => request<Record<string, unknown>>('/invoices/catalogs'),
  company: () => request<Company>('/invoices/company'),
  updateCompany: (payload: Partial<Company>) => request<Company>('/invoices/company', { method: 'PUT', body: JSON.stringify(payload) }),
  pacConfig: () => request<PacConfig>('/invoices/pac-config'),
  updatePacConfig: (payload: Record<string, unknown>) => request<PacConfig>('/invoices/pac-config', { method: 'PUT', body: JSON.stringify(payload) }),
  testPacConfig: () => request<{ ok: boolean; message: string }>('/invoices/pac-config/test', { method: 'POST' }),
  previewInvoice: (payload: Record<string, unknown>) => request<{ ok: boolean; errors: string[]; [key: string]: unknown }>('/invoices/preview', { method: 'POST', body: JSON.stringify(payload) }),
  createInvoice: (payload: Record<string, unknown>) => request<Invoice>('/invoices', { method: 'POST', body: JSON.stringify(payload) }),
  invoices: (params = '') => request<{ items: Invoice[] }>(`/invoices${params}`),
  invoice: (id: number) => request<Invoice>(`/invoices/${id}`),
  cancelInvoice: (id: number, payload: Record<string, unknown>) => request<{ message: string; data: Invoice }>(`/invoices/${id}/cancel`, { method: 'POST', body: JSON.stringify(payload) }),
  createNotaCredito: (id: number) => request<Invoice>(`/invoices/${id}/nota-credito`, { method: 'POST' }),
  invoiceSalesSummary: (params = '') => request<InvoiceSalesSummary>(`/invoices/sales-summary${params}`),
  // El PDF/XML se sirven como archivo (no JSON), asi que no pasan por
  // request(): se piden con fetch directo (GET, sin CSRF) y se abren como
  // blob (igual que el recibo de venta ya hace con jsPDF, pero aqui el PDF
  // lo arma el backend). credentials:'include' manda la cookie de sesion.
  async invoiceFileBlob(id: number, kind: string): Promise<Blob> {
    const res = await fetch(`${API_URL}/invoices/${id}/${kind}`, { credentials: 'include' })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data?.error?.message || 'No se pudo descargar el archivo')
    }
    return res.blob()
  },
}
