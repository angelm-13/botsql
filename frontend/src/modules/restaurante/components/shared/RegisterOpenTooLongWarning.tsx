import { AlertTriangle } from 'lucide-react'
import type { Translations } from '../../i18n/translations'

/** Aviso cuando la caja lleva abierta mas de lo normal (ver
 * REGISTER_OPEN_ALERT_HOURS en backend/app/utils/cash.py) -- casi siempre
 * significa que alguien olvido cerrarla al terminar el turno. Reutiliza el
 * mismo estilo de aviso ambar que BoardTruncatedWarning en KitchenBoard.tsx
 * (misma idea: algo no bloqueante que igual conviene que alguien note). */
export function RegisterOpenTooLongWarning({ t }: { t: Translations }) {
  return <div className="board-truncated-warning"><AlertTriangle size={16} /> {t.registerOpenTooLong}</div>
}
