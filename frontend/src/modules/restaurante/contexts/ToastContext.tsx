import { createContext, useContext, useMemo, useRef, useState, type ReactNode } from 'react'
import { CheckCircle2, XCircle, Info } from 'lucide-react'
import { Portal } from '../components/shared/Portal'

type ToastType = 'success' | 'error' | 'info'

interface Toast {
  id: number
  message: string
  type: ToastType
}

export interface ToastApi {
  success: (message: string) => void
  error: (message: string) => void
  info: (message: string) => void
}

// Reemplaza window.alert() en toda la app: un aviso no bloqueante, con el
// mismo lenguaje visual (tarjeta blanca, borde/icono de color) que el resto
// del rediseno, en vez de la ventana nativa del navegador. Cualquier
// componente puede usar useToast() porque el provider envuelve toda la app
// (ver App()).
const ToastContext = createContext<ToastApi | null>(null)

// useToast() siempre se llama dentro de <ToastProvider> (envuelve toda la
// app, ver App() en main.jsx) -- el "as ToastApi" evita que cada uno de los
// ~40 call sites (toast.error(...) etc.) tenga que checar null por un caso
// que en la practica nunca pasa.
export function useToast(): ToastApi {
  return useContext(ToastContext) as ToastApi
}

const TOAST_ICONS: Record<ToastType, typeof CheckCircle2> = { success: CheckCircle2, error: XCircle, info: Info }

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const idRef = useRef(0)
  function push(message: string, type: ToastType) {
    if (!message) return
    const id = ++idRef.current
    setToasts(list => [...list, { id, message, type }])
    setTimeout(() => setToasts(list => list.filter(x => x.id !== id)), 5000)
  }
  function dismiss(id: number) { setToasts(list => list.filter(x => x.id !== id)) }
  const api = useMemo<ToastApi>(() => ({
    success: (m) => push(m, 'success'),
    error: (m) => push(m, 'error'),
    info: (m) => push(m, 'info'),
  }), [])
  return <ToastContext.Provider value={api}>
    {children}
    <Portal><div className="toast-stack">
      {toasts.map(item => {
        const Icon = TOAST_ICONS[item.type] || Info
        return <div key={item.id} className={`toast toast-${item.type}`} onClick={() => dismiss(item.id)}>
          <Icon size={18} /><span>{item.message}</span>
        </div>
      })}
    </div></Portal>
  </ToastContext.Provider>
}
