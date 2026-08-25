import { createContext, useContext, useState, type ReactNode } from 'react'
import { AlertTriangle } from 'lucide-react'
import { Portal } from '../components/shared/Portal'
import type { Translations } from '../i18n/translations'

export type ConfirmAction = (message: string) => Promise<boolean>

interface ConfirmState {
  message: string
  resolve: (value: boolean) => void
}

// Reemplaza window.confirm() en toda la app con un dialogo con el mismo
// estilo que el resto de los modales (.modal/.ticket-panel). confirmAction()
// devuelve una promesa que resuelve true/false, para poder seguir usando
// "if (!(await confirmAction(...))) return;" en el mismo lugar donde antes
// habia un confirm() sincrono.
const ConfirmContext = createContext<ConfirmAction | null>(null)

// Mismo criterio que useToast(): siempre se llama dentro de <ConfirmProvider>.
export function useConfirmDialog(): ConfirmAction {
  return useContext(ConfirmContext) as ConfirmAction
}

export function ConfirmProvider({ t, children }: { t: Translations; children: ReactNode }) {
  const [state, setState] = useState<ConfirmState | null>(null)
  function confirmAction(message: string): Promise<boolean> {
    return new Promise(resolve => setState({ message, resolve }))
  }
  function resolve(value: boolean) { state?.resolve(value); setState(null) }
  return <ConfirmContext.Provider value={confirmAction}>
    {children}
    {state && <Portal><div className="modal">
      <div className="ticket-panel confirm-dialog" style={{ maxWidth: 400 }}>
        <div className="confirm-dialog-icon"><AlertTriangle size={22} /></div>
        <p className="confirm-dialog-message">{state.message}</p>
        <div className="receipt-modal-actions">
          <button className="primary" onClick={() => resolve(true)}>{t.continueAction}</button>
          <button className="ghost" onClick={() => resolve(false)}>{t.cancel}</button>
        </div>
      </div>
    </div></Portal>}
  </ConfirmContext.Provider>
}
