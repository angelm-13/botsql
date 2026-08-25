import { useState } from 'react'
import { RefreshCw } from 'lucide-react'
import type { Translations } from '../../i18n/translations'

/**
 * Boton de "Actualizar" reutilizable para las pantallas que ya cargan sus
 * datos por polling (mesas, tablero de cocina/entregas, cobros
 * pendientes...): les da al usuario una forma de refrescar al instante en
 * vez de esperar al siguiente ciclo automatico. `onClick` debe ser la
 * misma funcion de carga que ya usa el polling de ese componente.
 */
export function RefreshButton({ onClick, t }: { onClick: () => unknown; t: Translations }) {
  const [spinning, setSpinning] = useState(false)
  function handleClick() {
    setSpinning(true)
    Promise.resolve(onClick()).finally(() => setTimeout(() => setSpinning(false), 500))
  }
  return <button className="icon-btn refresh-btn" onClick={handleClick} title={t.refresh}>
    <RefreshCw size={16} className={spinning ? 'spin' : ''} /> {t.refresh}
  </button>
}
