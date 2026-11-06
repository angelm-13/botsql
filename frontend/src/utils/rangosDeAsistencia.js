// Semana (lunes a domingo) y quincena (1-15 o 16-fin de mes) para el reporte de
// asistencia para RH (pages/AttendanceReportPage.jsx).

const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

// El rango de `tipo` ("week" o "biweekly") que contiene `dia`.
export function rangoDe(tipo, dia = new Date()) {
  const d = new Date(dia.getFullYear(), dia.getMonth(), dia.getDate());
  if (tipo === "week") {
    const lunes = new Date(d.getFullYear(), d.getMonth(), d.getDate() - ((d.getDay() + 6) % 7));
    return { start: iso(lunes), end: iso(new Date(lunes.getFullYear(), lunes.getMonth(), lunes.getDate() + 6)) };
  }
  const primera = d.getDate() <= 15;
  return {
    start: iso(new Date(d.getFullYear(), d.getMonth(), primera ? 1 : 16)),
    end: iso(primera ? new Date(d.getFullYear(), d.getMonth(), 15) : new Date(d.getFullYear(), d.getMonth() + 1, 0)),
  };
}

// El rango anterior al que contiene `dia`.
export function rangoAnterior(tipo, dia = new Date()) {
  const [a, m, d] = rangoDe(tipo, dia).start.split("-").map(Number);
  return rangoDe(tipo, new Date(a, m - 1, d - 1));
}
