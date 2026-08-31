import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import type { Translations } from '../../i18n/translations'

interface ErrorBoundaryProps {
  children: ReactNode
  /** Etiqueta de la seccion que envuelve (ej. "mesero", "cocina") -- solo
   * para el log, ayuda a saber DONDE revento sin depender del stack. */
  section?: string
  /** Opcional a proposito: si el error ocurrio en un punto donde `t` no
   * llego (o el propio idioma es parte del problema), esta pantalla debe
   * seguir mostrandose igual con los textos de respaldo en espanol. */
  t?: Translations
}

interface ErrorBoundaryState {
  hasError: boolean
}

/**
 * Ultima red de seguridad de la interfaz. Sin esto, cualquier excepcion no
 * atrapada durante el render (un campo que el backend dejo de mandar, un
 * `.map()` sobre algo que llego null) desmonta TODO el arbol de React y
 * deja la pantalla completamente en blanco -- sin mensaje, sin forma de
 * recuperarse salvo que el usuario adivine que hay que recargar. En una
 * tablet en medio del servicio, eso parece "se murio el sistema".
 *
 * Tiene que ser una clase: los hooks no pueden atrapar errores de render,
 * React solo expone componentDidCatch/getDerivedStateFromError en clases.
 *
 * Se monta por seccion (ver main.tsx), no una sola vez en la raiz, para que
 * un error en el panel de administracion no tumbe tambien la barra
 * superior ni el boton de salir -- el usuario sigue pudiendo navegar a otra
 * pantalla en vez de quedarse atorado.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // console.error a proposito: es lo que Sentry (si esta configurado en el
    // backend/frontend a futuro) y las herramientas del navegador recogen.
    console.error(`[ErrorBoundary${this.props.section ? ' ' + this.props.section : ''}]`, error, info.componentStack)
  }

  render() {
    if (!this.state.hasError) return this.props.children
    const t = this.props.t
    return <div className="error-boundary">
      <AlertTriangle size={32} />
      <h2>{t ? t.errorBoundaryTitle : 'Algo salio mal en esta pantalla'}</h2>
      <p>{t ? t.errorBoundaryBody : 'El resto de la aplicacion sigue funcionando: puedes cambiar de pestana, o recargar para volver a intentar.'}</p>
      <button className="primary" onClick={() => window.location.reload()}>
        <RefreshCw size={16} /> {t ? t.errorBoundaryReload : 'Recargar'}
      </button>
    </div>
  }
}
