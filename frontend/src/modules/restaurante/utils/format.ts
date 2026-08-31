// Helpers puros extraidos de main.jsx (sin JSX, sin hooks, sin dependencias
// de React) para que sean testeables de forma aislada -- ver
// frontend/tests/format.test.js.
import type { Translations } from '../i18n/translations'

export function money(n: number | string | null | undefined): string {
  return `$${Number(n || 0).toFixed(2)}`
}

// Nombre de la variable CSS (definida en styles/theme.css) para el color de
// cada estatus -- compartida por los tableros de mesero (TicketPanel,
// TablesView) y los paneles de admin (AdminOrdersPanel, PendingPayments).
export const STATUS_VAR: Record<string, string> = {
  borrador: '--status-borrador', pedido: '--status-pedido', en_preparacion: '--status-preparacion',
  listo_para_entrega: '--status-listo', entregado: '--status-entregado', pagado: '--status-pagado',
  cancelado: '--status-cancelado',
}

export function labelStatus(s: string, t: Translations): string {
  return (
    ({
      borrador: t.draft,
      pedido: t.ordered,
      en_preparacion: t.preparing,
      listo_para_entrega: t.ready,
      entregado: t.delivered,
      pagado: t.paid,
      cancelado: t.cancelled,
    } as Record<string, string>)[s] || s
  )
}

// Forma minima que necesita placeLabel/t_table: una Visit, una Order, o un
// platillo aplanado del tablero -- todos traen estos campos (algunos
// opcionales segun de donde vengan).
export interface PlaceLabelSource {
  is_takeout?: boolean
  table_number?: number | null
  visit_daily_number?: number | null
  daily_number?: number | null
  visit_id?: number | null
  id?: number
  customer_name?: string | null
  diner_index?: number
}

/** Etiqueta de lugar comun a mesas y pedidos "para llevar": una mesa
 * muestra "Mesa 5", un pedido para llevar muestra "Para llevar #12" (mas
 * el nombre/nota si se capturo alguno). Se usa en TODOS los lugares que
 * antes solo mostraban "Mesa {table_number}" (tableros de cocina/entregas,
 * cuentas por cobrar, recibos, panel de cancelaciones), para que un pedido
 * sin mesa fisica nunca se vea como "Mesa None"/vacio. `o` puede ser una
 * visita, una orden, o un platillo del tablero -- todos traen is_takeout,
 * table_number, y (si aplica) visit_id/customer_name. */
export function placeLabel(t: Translations, o: PlaceLabelSource, includeDiner?: boolean): string {
  if (o.is_takeout) {
    // Folio del dia (reinicia cada dia, ver Visit.daily_number en el
    // backend) en vez del id real de la visita, que nunca reinicia. `o`
    // puede ser la propia Visit (trae daily_number) o una Order/platillo
    // relacionado (trae visit_daily_number) -- se prueban ambos antes de
    // caer al id crudo, por si viene de un dato viejo sin folio asignado.
    const id = o.visit_daily_number ?? o.daily_number ?? o.visit_id ?? o.id ?? ''
    return `${t.takeoutLabel} #${id}${o.customer_name ? ' - ' + o.customer_name : ''}`
  }
  const base = `${t.table} ${o.table_number}`
  return includeDiner ? `${base} - ${t.diner} ${o.diner_index}` : base
}

export function elapsedMinutes(date: string | number | Date): number {
  return Math.max(0, Math.floor((new Date().getTime() - new Date(date).getTime()) / 60000))
}

export function fmtStamp(date: string | number | Date | null | undefined): string {
  return date ? new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--:--'
}

// Fecha en formato YYYY-MM-DD LOCAL (no UTC, a diferencia de
// toISOString()) -- usada por los presets de rango de fecha (hoy/ayer/esta
// semana/este mes) en ReportsPanel e InvoiceHistoryPanel, para que el
// rango coincida con el calendario real del dispositivo del usuario.
export function fmtLocalDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// Compartido por PayScreen (fondo/cambio) y RegisterPanel (apertura de
// caja) -- features/admin.
export const OPENING_AMOUNT_PRESETS: number[] = [0, 500, 1000, 2000]

export interface DateRangePreset {
  key: string
  label: string
}

// Compartido por los selectores de rango de fecha de ReportsPanel e
// InvoiceHistoryPanel (features/admin).
export const DATE_RANGE_PRESETS: DateRangePreset[] = [
  { key: 'today', label: 'rangeToday' },
  { key: 'yesterday', label: 'rangeYesterday' },
  { key: 'week', label: 'rangeThisWeek' },
  { key: 'month', label: 'rangeThisMonth' },
  { key: 'all', label: 'rangeAllTime' },
]

// Compartido por AuditLogPanel y UsersManager (features/admin).
export function staffRoleLabel(role: string, t: Translations): string {
  return (
    ({
      mesero: t.roleWaiter, cajero: t.roleCashier, cocina: t.roleKitchen, admin: t.roleAdmin, superadmin: t.roleSuperAdmin,
    } as Record<string, string>)[role] || role
  )
}

// Mismo criterio de reparto que _distribute() en visits.py (proporcional
// al subtotal de cada quien, sin perder centavos por redondeo -- el
// ultimo se ajusta con lo que sobre). Se usa en el frontend solo para
// PREVISUALIZAR en PayScreen cuanto le va a tocar a cada comensal del
// total que se esta por cobrar; el reparto real y definitivo lo sigue
// calculando el backend.
export function distributeProportionally(totalAmount: number, weights: number[]): number[] {
  const combined = weights.reduce((s, w) => s + w, 0)
  let assigned = 0
  return weights.map((w, idx) => {
    if (idx === weights.length - 1) return Math.round((totalAmount - assigned) * 100) / 100
    const share = combined > 0 ? w / combined : 1 / weights.length
    const amount = Math.round(totalAmount * share * 100) / 100
    assigned += amount
    return amount
  })
}
