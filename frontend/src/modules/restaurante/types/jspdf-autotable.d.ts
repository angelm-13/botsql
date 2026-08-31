// jspdf-autotable 3.x aumenta jsPDF.prototype en tiempo de ejecucion (ver
// `import 'jspdf-autotable'` en AdminOrdersPanel/ReportsPanel), pero sus
// .d.ts no declaran ese metodo sobre el tipo jsPDF -- se agrega aqui a mano.
import 'jspdf'
import type { UserOptions } from 'jspdf-autotable'

declare module 'jspdf' {
  interface jsPDF {
    autoTable(options: UserOptions): jsPDF
    lastAutoTable: { finalY: number }
  }
}
