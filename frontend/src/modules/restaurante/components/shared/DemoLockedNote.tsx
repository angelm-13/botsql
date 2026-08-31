import { Lock } from 'lucide-react'

/** Nota reutilizable para marcar una funcion bloqueada en la version
 * freemium/de prueba (ver backend/app/demo.py) -- usada en KPIs historicos,
 * reportes con rango de fechas, el selector de PAC real, y los formularios
 * que ya llegaron a su tope (personal, facturas del mes). */
export function DemoLockedNote({ text }: { text: string }) {
  return <div className="demo-locked-note"><Lock size={14} /><span>{text}</span></div>
}
