import type { jsPDF } from 'jspdf'
import type { Translations } from '../../i18n/translations'

/** Dibuja una version simplificada del FlameMark (el icono de la marca)
 * mas el wordmark, usando primitivas vectoriales de jsPDF (no hay ningun
 * archivo de imagen del logo: se recrea con figuras, igual que FlameMark
 * lo hace con SVG en el resto de la app). x,y en mm. Compartido por
 * buildCancellationsPdf (AdminOrdersPanel) y buildReportPdf (ReportsPanel). */
export function drawLogoPdf(doc: jsPDF, x: number, y: number, t?: Translations): void {
  const primary: [number, number, number] = [113, 113, 122]
  const dark: [number, number, number] = [43, 43, 43]
  doc.setFillColor(...dark)
  doc.ellipse(x + 4, y + 9, 5, 1.3, 'F')
  doc.setFillColor(...primary)
  doc.ellipse(x + 3.3, y + 5, 2.3, 3.6, 'F')
  doc.ellipse(x + 5.2, y + 4.6, 1.7, 2.9, 'F')
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(15)
  doc.setTextColor(...dark)
  doc.text((t ? t.welcome : 'MI RESTAURANTE').toUpperCase(), x + 12, y + 7.5)
  doc.setFont('helvetica', 'normal')
}
