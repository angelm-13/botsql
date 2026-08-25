import { createPortal } from 'react-dom'
import type { ReactNode } from 'react'

/**
 * Renderiza sus hijos directamente en document.body en vez de en el punto
 * del arbol de React donde se usa. Los modales (.modal, position:fixed)
 * dependen de posicionarse contra el viewport completo; si un ancestro
 * (por ejemplo .app-shell, que tiene overflow:hidden) los recorta o los
 * confina a una caja mas chica, el modal se ve pequeno/cortado en vez de
 * cubrir toda la pantalla. Un portal evita ese problema por completo,
 * sin importar que contenedor tenga overflow/transform en el camino.
 */
export function Portal({ children }: { children: ReactNode }) {
  return createPortal(children, document.body)
}
