/** Placeholder de carga con un pequeno "shimmer" (barra con brillo que se
 * desliza), en vez del texto suelto "..." que se usaba antes mientras
 * llegan los datos de un panel. */
export function LoadingPanel({ label }: { label?: string }) {
  return <div className="loading-panel">
    <div className="loading-bar" />
    <div className="loading-bar" style={{ width: '70%' }} />
    <div className="loading-bar" style={{ width: '45%' }} />
    {label && <p className="loading-label">{label}</p>}
  </div>
}
