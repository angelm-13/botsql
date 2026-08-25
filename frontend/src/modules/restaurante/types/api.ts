// Tipos que reflejan el to_dict() de cada modelo del backend (ver
// backend/app/models/entities.py y openapi.yaml, que es la fuente de
// verdad -- estos tipos deben mantenerse en sincronia con ese archivo).
// Los campos opcionales (`?`) son los que el backend puede omitir o mandar
// null segun el caso (ej. table_number en un pedido "para llevar").

export type Role = 'mesero' | 'cocina' | 'cajero' | 'admin' | 'superadmin'

export interface User {
  id: number
  username: string
  role: Role
  is_active: boolean
  waiter_id: number | null
  created_at: string
}

export interface Waiter {
  id: number
  name: string
  nickname: string
  status: string
  max_tables: number
}

export interface Table {
  id: number
  number: number
  capacity: number
  location_description: string | null
  // Solo presentes en la respuesta de GET /tables (calculados, no columnas reales).
  occupied?: boolean
  visit_id?: number | null
  diners_count?: number
}

export interface Category {
  id: number
  slug: string
  name: string
  icon: string
  color: string
  sort_order: number
  is_active: boolean
}

export interface Guisado {
  id: number
  name: string
  is_active: boolean
}

export type DishSchedule = 'all' | 'weekday' | 'weekend' | 'mon' | 'tue' | 'wed' | 'thu' | 'fri' | 'sat' | 'sun'

export interface Dish {
  id: number
  title: string
  description: string | null
  image_url: string | null
  size_label: string | null
  icon: string
  category: string
  price: number
  production_cost: number
  requires_guisado: boolean
  schedule: DishSchedule
  is_active: boolean
}

export type OrderStatus = 'borrador' | 'pedido' | 'en_preparacion' | 'listo_para_entrega' | 'entregado' | 'pagado' | 'cancelado'
export type PaymentMethod = 'efectivo' | 'tarjeta' | 'transferencia' | 'mixto'

export interface OrderItem {
  id: number
  order_id: number
  dish_id: number
  dish?: Dish
  quantity: number
  unit_price: number
  note: string | null
  guisado_1_id: number | null
  guisado_2_id: number | null
  guisado_1?: Guisado | null
  guisado_2?: Guisado | null
  combinado: boolean
  status: OrderStatus | null
  cancel_reason: string | null
  cancelled_by_id: number | null
  cancelled_at: string | null
  // Presente solo en /orders/cancelled (join armado a mano en la ruta).
  cancelled_by_username?: string | null
  sent_at: string | null
  cooked_at: string | null
  ready_at: string | null
  delivered_at: string | null
  // Presentes solo en /kitchen/board y /orders/cancelled (aplanados desde su Order/Visit).
  order_id_daily_number?: number
  table_number?: number | null
  is_takeout?: boolean
  visit_id?: number
  visit_daily_number?: number
  customer_name?: string | null
  diner_index?: number
}

export interface Order {
  id: number
  visit_id: number
  diner_index: number
  waiter_id: number | null
  status: OrderStatus
  daily_number: number
  items: OrderItem[]
  subtotal?: number
  total?: number
  tip_type: 'manual' | 'porcentaje' | null
  tip_percent: number | null
  tip_amount: number
  discount_amount: number
  tax_amount: number
  payment_method: PaymentMethod | null
  received_amount: number | null
  cash_amount: number | null
  paid_at: string | null
  register_session_id: number | null
  started_at: string
  sent_at: string | null
  cooked_at: string | null
  ready_at: string | null
  delivered_at: string | null
  // Presentes cuando el pedido viene aplanado junto con datos de su visita
  // (cuentas por cobrar, tableros) -- no columnas reales de Order.
  table_number?: number | null
  is_takeout?: boolean
  customer_name?: string | null
  visit_daily_number?: number
}

export interface Visit {
  id: number
  table_number: number | null
  is_takeout: boolean
  customer_name: string | null
  daily_number: number | null
  waiter_id: number | null
  diners_count: number
  status: 'active' | 'closed'
  opened_at: string
  closed_at: string | null
  orders: Order[]
  total: number
}

export interface CashSession {
  id: number
  opened_by_id: number
  opening_amount: number
  closed_by_id: number | null
  closing_amount: number | null
  expected_amount: number | null
  difference: number | null
  status: 'open' | 'closed'
  opened_at: string
  closed_at: string | null
  notes: string | null
  sales_breakdown_json?: string | null
  live_summary?: {
    orders_count: number
    total_sales: number
    total_tips: number
    payment_breakdown: Record<string, number>
    cash_collected: number
    cash_expected: number
  }
  open_hours?: number
  open_too_long?: boolean
}

export interface Reservation {
  id: number
  table_number: number | null
  name: string
  date: string
  time: string
  guests: number
  event_type: string | null
  status: 'pending' | 'cancelled'
}

export type InventoryMovementType = 'entrada' | 'salida' | 'merma' | 'ajuste'

export interface InventoryItem {
  id: number
  description: string
  unit: string
  quantity: number
  cost_per_unit: number
  min_stock: number
  is_active: boolean
  // Calculados, no columnas reales.
  total_value?: number
  // Solo en /inventory/summary (calculado, no columna real).
  is_low_stock?: boolean
}

export interface InventoryMovement {
  id: number
  inventory_item_id: number
  type: InventoryMovementType
  quantity_delta: number
  unit_cost: number
  reason: string | null
  resulting_quantity: number
  created_by_id: number
  created_by_username?: string | null
  created_at: string
  // Calculados/aplanados desde el insumo relacionado, no columnas reales.
  total_cost?: number
  inventory_item_description?: string | null
  inventory_item_unit?: string | null
}

export type CfdiType = 'I' | 'E'
export type CancelStatus = 'en_proceso' | 'cancelado' | null

export interface Invoice {
  id: number
  visit_id: number | null
  order_ids_json?: string
  uuid: string | null
  serie: string
  folio: string
  cfdi_type: CfdiType
  status: 'stamped'
  cancel_status: CancelStatus
  cancelled_reason?: string | null
  cancelled_at?: string | null
  relacion_uuid?: string | null
  receptor_rfc: string
  receptor_nombre: string
  receptor_regimen_fiscal?: string
  receptor_cp_fiscal?: string
  receptor_email?: string | null
  uso_cfdi?: string
  forma_pago?: string
  metodo_pago?: string
  moneda?: string
  subtotal: number
  iva_amount: number
  total: number
  xml_content?: string | null
  pac_provider?: string
  stamped_at: string | null
  created_by?: string | null
}

export interface Company {
  id: number
  razon_social: string | null
  rfc: string | null
  regimen_fiscal: string | null
  cp: string | null
  direccion: string | null
  serie: string
}

export interface PacConfig {
  id: number
  provider: string
  facturama_user: string | null
  has_password: boolean
}

// Estado de la version freemium/de prueba (ver backend/app/demo.py y
// GET /api/demo/status). 'enabled' en false significa que este despliegue
// es la version completa (demo_restaurante) -- ningun otro campo aplica en
// ese caso, y el frontend no debe mostrar ningun banner ni bloqueo.
export type DemoStatus =
  | { enabled: false }
  | {
      enabled: true
      expired: boolean
      expires_at: string
      days_remaining: number
      max_staff: number
      staff_count: number
      max_invoices_per_month: number
      invoices_used_this_month: number
    }

export interface AuditLog {
  id: number
  actor_user_id: number | null
  actor_username: string
  actor_role: string
  action: string
  entity_type: string
  entity_id: number | null
  description: string
  created_at: string
}

export interface Pagination {
  page: number
  per_page: number
  total: number
}

export interface Paginated<T> {
  items: T[]
  pagination: Pagination
}

export interface ApiErrorBody {
  error: { message: string; code: string; status: number }
}

// ---- Formas de los endpoints de reportes/KPIs (cashier.py) ----
// No son modelos de SQLAlchemy con to_dict() propio, sino respuestas
// armadas a mano en la ruta -- se documentan aqui igual, en base a
// openapi.yaml y al codigo real de backend/app/routes/cashier.py.

export interface RecentOrderSummary {
  id: number
  daily_number: number | null
  visit_daily_number?: number
  table_number: number | null
  is_takeout: boolean
  customer_name: string | null
  diner_index: number
  time: string | null
  items_summary: string
  status: OrderStatus
}

export interface DayMetrics {
  orders: number
  items_requested: number
  tables_served: number
  items_ready: number
  items_cancelled: number
  avg_prep_minutes: number
}

export interface DashboardData extends DayMetrics {
  date: string
  orders_today: number
  items_requested_today: number
  tables_served_today: number
  items_ready_today: number
  items_cancelled_today: number
  avg_prep_minutes_today: number
  orders_by_hour: { hour: number; count: number }[]
  status_distribution: Record<string, number>
  recent_orders: RecentOrderSummary[]
  category_breakdown: { category: string; quantity: number; percent: number }[]
  previous_day: DayMetrics & { date: string }
}

export interface KpisData {
  total_sales: number
  tips: number
  top_dishes: { dish: string; quantity: number }[]
  dish_frequency: { dish: string; frequency: number }[]
  top_tables: { table: number; services: number }[]
  services_by_waiter: { waiter: string; services: number }[]
  avg_minutes_from_ready_to_delivered: number
  avg_ticket: number
  active_tables: number
  active_takeout_orders: number
  register_open: boolean
  register_opened_at: string | null
  register_open_too_long: boolean
  payment_breakdown: Record<string, number>
}

export interface SalesReportDay {
  date: string
  orders: number
  sales: number
  tips: number
}

export interface SalesReport {
  days: SalesReportDay[]
  total_orders: number
  total_sales: number
  total_tips: number
}

export interface InventorySummary {
  total_value: number
  active_items_count: number
  low_stock_items: InventoryItem[]
  mermas_this_month: { count: number; quantity: number; cost: number }
  entradas_this_month: { count: number; quantity: number; cost: number }
  salidas_this_month: { count: number; quantity: number; cost: number }
}

export interface InvoiceSalesSummary {
  total_sales: number
  invoice_count: number
  days: { date: string; sales: number; count: number }[]
}

export interface StaffMember extends User {
  waiter: Waiter | null
}

export interface PayVisitResult {
  visit: Visit
  subtotal: number
  tax_amount: number
  discount_amount: number
  tip_amount: number
  total: number
  change_amount: number | null
  orders_paid: number[]
  orders_daily_numbers: number[]
  orders_breakdown: {
    order_id: number
    diner_index: number
    daily_number: number
    subtotal: number
    tax_amount: number
    discount_amount: number
    tip_amount: number
    total: number
  }[]
}
