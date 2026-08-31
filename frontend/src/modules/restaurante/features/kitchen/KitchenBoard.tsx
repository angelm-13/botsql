import { useEffect, useRef, useState, type ReactNode } from 'react'
import { ChefHat, CheckCircle2, AlertTriangle } from 'lucide-react'
import { api } from '../../services/api'
import { useToast } from '../../contexts/ToastContext'
import { EmptyState } from '../../components/shared/EmptyState'
import { RefreshButton } from '../../components/shared/RefreshButton'
import { placeLabel, elapsedMinutes, fmtStamp } from '../../utils/format'
import type { Translations } from '../../i18n/translations'
import type { OrderItem, OrderStatus } from '../../types/api'

// AudioContext se crea una sola vez y se reutiliza en cada llamada (algunos
// navegadores lo suspenden hasta que hay un gesto del usuario; como esto se
// dispara despues de que el mesero ya inicio sesion con un clic, normalmente
// puede sonar). Modulo-level (no una propiedad pegada a la funcion) para que
// TypeScript no se queje de asignar props arbitrarias a una function.
let sharedAudioCtx: AudioContext | undefined

/** Genera un "ding" corto con la Web Audio API (sin archivos de audio) para
 * avisarle al mesero cuando un platillo nuevo llega a "listo para entrega".
 * Si el navegador bloquea el audio, se ignora en silencio en vez de romper
 * la app. */
export function playNotificationSound(): void {
  try {
    if (!sharedAudioCtx) {
      const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
      if (!Ctx) return
      sharedAudioCtx = new Ctx()
    }
    const ctx = sharedAudioCtx
    if (ctx.state === 'suspended') ctx.resume().catch(() => {})
    const now = ctx.currentTime
    ;[{ delay: 0, freq: 880 }, { delay: 0.16, freq: 1175 }].forEach(({ delay, freq }) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.value = freq
      gain.gain.setValueAtTime(0.0001, now + delay)
      gain.gain.exponentialRampToValueAtTime(0.3, now + delay + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, now + delay + 0.3)
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.start(now + delay)
      osc.stop(now + delay + 0.32)
    })
  } catch { /* audio bloqueado por el navegador: se ignora */ }
}

interface TableLabelSource {
  is_takeout?: boolean
  visit_daily_number?: number
  visit_id?: number
  customer_name?: string | null
  diner_index?: number
  table_number?: number | null
}

// Exportado: la pantalla de cobro (PayScreen, features/admin) tambien
// necesita la etiqueta "Mesa N - Comensal M"/"Para llevar #N - Comensal M"
// completa (a diferencia de placeLabel(), que no agrega el comensal para
// pedidos "para llevar").
export function t_table(t: Translations, o: TableLabelSource): string {
  if (o.is_takeout) {
    const id = o.visit_daily_number ?? o.visit_id ?? ''
    return `${t.takeoutLabel} #${id}${o.customer_name ? ' - ' + o.customer_name : ''} - ${t.diner} ${o.diner_index}`
  }
  return `${t.table} ${o.table_number} - ${t.diner} ${o.diner_index}`
}

interface KdsCardProps {
  title: string
  tableLabel: string
  note?: string | null
  guisadoText?: string | null
  sentAt?: string | null
  acceptedAt?: string | null
  preparedAt?: string | null
  deliveredAt?: string | null
  accentVar: string
  actionLabel?: string | null
  onAction?: () => void
  disabled?: boolean
  t: Translations
  isNew?: boolean
}

function KdsCard({ title, tableLabel, note, guisadoText, sentAt, acceptedAt, preparedAt, deliveredAt, accentVar, actionLabel, onAction, disabled, t, isNew }: KdsCardProps) {
  const activeSince = deliveredAt || preparedAt || acceptedAt || sentAt
  return <div className={`kds-card${isNew ? ' kds-card-new' : ''}`}>
    <div className="kds-main">
      <h3>{title}</h3>
      <p className="kds-table">{tableLabel}</p>
      {guisadoText && <p className="kds-note">{guisadoText}</p>}
      {note && <p className="kds-note">&quot;{note}&quot;</p>}
      <div className="kds-timeline">
        <span className={sentAt ? 'kds-stamp done' : 'kds-stamp'}>{t.emitted}: {fmtStamp(sentAt)}</span>
        <span className={acceptedAt ? 'kds-stamp done' : 'kds-stamp'}>{t.accepted}: {fmtStamp(acceptedAt)}</span>
        <span className={preparedAt ? 'kds-stamp done' : 'kds-stamp'}>{t.prepared}: {fmtStamp(preparedAt)}</span>
        <span className={deliveredAt ? 'kds-stamp done' : 'kds-stamp'}>{t.delivered}: {fmtStamp(deliveredAt)}</span>
      </div>
    </div>
    <div className="kds-side">
      <span className="kds-elapsed-label">{t.elapsedLabel}</span>
      <span className="kds-elapsed-value" style={{ color: `var(${accentVar})` }}>{activeSince ? `${elapsedMinutes(activeSince)} min` : '-'}</span>
      {actionLabel && <button className="kds-action" style={{ background: `var(${accentVar})` }} disabled={disabled} onClick={onAction}>{actionLabel}</button>}
    </div>
  </div>
}

/** Dibuja una tarjeta KDS por cada PLATILLO de la lista (ya vienen aplanados
 * desde /kitchen/board, un renglon por platillo con su propio estatus y
 * tiempos) -- por eso cada accion (aceptar/marcar listo/entregar) solo
 * afecta a ESE platillo (onAction recibe order_id e item_id), nunca al
 * resto de platillos de la misma orden. */
function renderKdsItems(
  list: OrderItem[],
  t: Translations,
  accentVar: string,
  actionLabel: string | null | undefined,
  onAction: ((orderId: number, itemId: number) => void) | null | undefined,
  includeDiner: boolean,
  newIds?: Set<number>,
  busyIds?: Set<number>,
): ReactNode {
  if (list.length === 0) return <EmptyState icon={CheckCircle2} title={t.noOrders} />
  return list.map(item => {
    const guisadoText = item.guisado_1 ? `${item.guisado_1.name}${item.guisado_2 ? ' + ' + item.guisado_2.name : ''}${item.combinado ? ` (${t.guisadoCombined})` : ''}` : null
    const tableLabel = placeLabel(t, item, includeDiner)
    return <KdsCard key={item.id}
      title={`${item.quantity > 1 ? item.quantity + ' x ' : ''}${item.dish ? item.dish.title : ''}`}
      tableLabel={tableLabel}
      note={item.note}
      guisadoText={guisadoText}
      sentAt={item.sent_at}
      acceptedAt={item.cooked_at}
      preparedAt={item.ready_at}
      deliveredAt={item.delivered_at}
      accentVar={accentVar}
      actionLabel={actionLabel}
      onAction={actionLabel && onAction ? () => onAction(item.order_id, item.id) : undefined}
      disabled={busyIds ? busyIds.has(item.id) : false}
      t={t}
      isNew={newIds ? newIds.has(item.id) : false}
    />
  })
}

/** Evita que dos clics rapidos en la misma tarjeta del tablero de cocina o
 * de entregas (facil con dedos en una tablet) disparen la misma peticion
 * dos veces: mientras el id sigue "ocupado" el boton de esa tarjeta se
 * deshabilita (ver KdsCard/renderKdsItems), y cualquier error del backend
 * ahora se avisa con un toast en vez de perderse como una promesa
 * rechazada sin manejar. */
function useBusyIds() {
  const [busyIds, setBusyIds] = useState<Set<number>>(() => new Set())
  const toast = useToast()
  async function run(id: number, fn: () => Promise<void>) {
    if (busyIds.has(id)) return
    setBusyIds(prev => new Set(prev).add(id))
    try {
      await fn()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e))
    } finally {
      setBusyIds(prev => { const next = new Set(prev); next.delete(id); return next })
    }
  }
  return { busyIds, run }
}

/**
 * Hook compartido por los tableros de cocina/entregas: recuerda que
 * platillos ya se habian visto en el chequeo anterior, y devuelve el
 * conjunto de ids "recien llegados" (para resaltarlos brevemente con
 * kds-card-new). Nunca resalta nada en la primera carga de la pantalla,
 * solo platillos que aparecen DESPUES de que la pantalla ya estaba abierta.
 */
function useNewArrivals(items: OrderItem[], playSound = false): Set<number> {
  const [newIds, setNewIds] = useState<Set<number>>(() => new Set())
  const seenIds = useRef<Set<number> | null>(null)
  // Acumula los timeout ids de esta instancia del hook (no de este efecto:
  // un timeout programado en un chequeo puede seguir vivo cuando llega el
  // siguiente). Sin este ref+cleanup, navegar a otra pestana dentro de los
  // 3s posteriores a que llegara un platillo nuevo dejaba el setTimeout
  // corriendo sobre un componente ya desmontado.
  const timeoutIds = useRef<ReturnType<typeof setTimeout>[]>([])
  useEffect(() => {
    const currentIds = new Set(items.map(it => it.id))
    if (seenIds.current) {
      const fresh: number[] = []
      currentIds.forEach(id => { if (!seenIds.current!.has(id)) fresh.push(id) })
      if (fresh.length) {
        setNewIds(prev => new Set([...prev, ...fresh]))
        fresh.forEach(id => {
          const timeoutId = setTimeout(() => setNewIds(prev => { const next = new Set(prev); next.delete(id); return next }), 3000)
          timeoutIds.current.push(timeoutId)
        })
        // Un solo sonido por tanda (aunque lleguen varios platillos a la vez
        // en el mismo chequeo), para no saturar de "dings" seguidos.
        if (playSound) playNotificationSound()
      }
    }
    seenIds.current = currentIds
  }, [items, playSound])
  useEffect(() => () => { timeoutIds.current.forEach(clearTimeout) }, [])
  return newIds
}

/** Aviso discreto para cuando el tablero llego al limite de platillos activos
 * que puede mostrar a la vez (ver KITCHEN_BOARD_LIMIT en el backend): sin
 * esto, si un dia hay mas platillos activos que el limite, el personal veria
 * una lista incompleta sin ninguna senal de que faltan platillos. */
function BoardTruncatedWarning({ t }: { t: Translations }) {
  return <div className="board-truncated-warning"><AlertTriangle size={16} /> {t.boardTruncatedWarning}</div>
}

export function DeliveryBoard({ t }: { t: Translations }) {
  const [items, setItems] = useState<OrderItem[]>([])
  const [truncated, setTruncated] = useState(false)
  // Usa el mismo endpoint que el tablero de cocina (platillos individuales,
  // no ordenes completas): asi cada platillo se recoge/entrega por su cuenta,
  // sin importar en que etapa vaya el resto de la orden a la que pertenece.
  async function load() {
    try {
      const data = await api.kitchenBoard()
      setItems((data.items || []).filter(it => (['en_preparacion', 'listo_para_entrega'] as OrderStatus[]).includes(it.status as OrderStatus)))
      setTruncated(!!data.truncated)
    } catch (e) { console.error(e) }
  }
  useEffect(() => { load(); const id = setInterval(load, 4000); return () => clearInterval(id) }, [])
  const { busyIds, run } = useBusyIds()
  async function markDelivered(orderId: number, itemId: number) {
    await run(itemId, async () => { await api.updateItemStatus(orderId, itemId, 'entregado'); await load() })
  }
  const newIds = useNewArrivals(items)
  const preparing = items.filter(it => it.status === 'en_preparacion')
  const ready = items.filter(it => it.status === 'listo_para_entrega')
  return <><div className="board-refresh-row"><RefreshButton t={t} onClick={load} /></div>
  {truncated && <BoardTruncatedWarning t={t} />}
  <div className="waiter-board">
    <div className="board-column">
      <div className="column-header" style={{ background: 'var(--status-preparacion)' }}><h2>{t.preparing}</h2><span className="count">{preparing.length}</span></div>
      <div className="column-items">{renderKdsItems(preparing, t, '--status-preparacion', null, null, true, newIds)}</div>
    </div>
    <div className="board-column">
      <div className="column-header" style={{ background: 'var(--status-listo)' }}><h2>{t.ready}</h2><span className="count">{ready.length}</span></div>
      <div className="column-items">{renderKdsItems(ready, t, '--status-listo', t.pickup, markDelivered, true, newIds, busyIds)}</div>
    </div>
  </div></>
}

export function KitchenBoard({ t }: { t: Translations }) {
  const [items, setItems] = useState<OrderItem[]>([])
  const [truncated, setTruncated] = useState(false)
  // /kitchen/board ya devuelve un renglon por platillo (no por orden), cada
  // uno con su propio estatus: por eso aceptar/marcar listo un platillo aqui
  // nunca mueve de columna a otros platillos de la misma orden.
  async function load() {
    try {
      const data = await api.kitchenBoard()
      setItems(data.items || [])
      setTruncated(!!data.truncated)
    } catch (e) { console.error(e) }
  }
  useEffect(() => { load(); const id = setInterval(load, 3000); return () => clearInterval(id) }, [])
  const { busyIds, run } = useBusyIds()
  async function updateStatus(orderId: number, itemId: number, s: string) {
    await run(itemId, async () => { await api.updateItemStatus(orderId, itemId, s); await load() })
  }
  // A diferencia del tablero de entregas (que ya tiene su propio aviso desde
  // WaiterApp), aqui SI se reproduce el sonido: es la primera senal que
  // recibe cocina de que llego un pedido nuevo, y esta pantalla suele quedar
  // en una tablet fija sin que nadie la este viendo todo el tiempo.
  const newIds = useNewArrivals(items, true)
  const groupByStatus = (status: string) => items.filter(it => it.status === status)
  const newItems = groupByStatus('pedido')
  const preparingItems = groupByStatus('en_preparacion')
  const readyItems = groupByStatus('listo_para_entrega')
  // Cancelar un platillo es exclusivo del administrador (AdminOrdersPanel);
  // cocina ya no ve la accion de cancelar aqui.
  return <main className="kitchen-page">
    <div className="section-title" style={{ padding: '24px 24px 0', justifyContent: 'space-between' }}><div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><ChefHat /><h1>{t.kitchenBoard}</h1></div><RefreshButton t={t} onClick={load} /></div>
    {truncated && <div style={{ padding: '0 24px' }}><BoardTruncatedWarning t={t} /></div>}
    <div className="kitchen-board">
      <div className="board-column">
        <div className="column-header" style={{ background: 'var(--status-nuevo)' }}><h2>{t.newOrders}</h2><span className="count">{newItems.length}</span></div>
        <div className="column-items">{renderKdsItems(newItems, t, '--status-nuevo', t.started, (orderId, itemId) => updateStatus(orderId, itemId, 'en_preparacion'), false, newIds, busyIds)}</div>
      </div>
      <div className="board-column">
        <div className="column-header" style={{ background: 'var(--status-preparacion)' }}><h2>{t.preparing}</h2><span className="count">{preparingItems.length}</span></div>
        <div className="column-items">{renderKdsItems(preparingItems, t, '--status-preparacion', t.markReady, (orderId, itemId) => updateStatus(orderId, itemId, 'listo_para_entrega'), false, newIds, busyIds)}</div>
      </div>
      <div className="board-column">
        <div className="column-header" style={{ background: 'var(--status-listo)' }}><h2>{t.ready}</h2><span className="count">{readyItems.length}</span></div>
        <div className="column-items">{renderKdsItems(readyItems, t, '--status-listo', null, null, false, newIds, busyIds)}</div>
      </div>
    </div>
  </main>
}
