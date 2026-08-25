import type { LucideIcon } from 'lucide-react'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  hint?: string
}

/** Estado vacio con icono, en vez de un texto suelto sin contexto. Se usa en
 * los lugares donde "no hay nada" pasa seguido durante el turno (columnas
 * de cocina/entregas, cuentas por cobrar, para llevar) para que se lea
 * como un estado normal y cuidado, no como si algo no hubiera cargado. */
export function EmptyState({ icon: Icon, title, hint }: EmptyStateProps) {
  return <div className="empty-state">
    <Icon size={28} />
    <p className="empty-state-title">{title}</p>
    {hint && <p className="empty-state-hint">{hint}</p>}
  </div>
}
