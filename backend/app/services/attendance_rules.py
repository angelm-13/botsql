"""Reglas de asistencia: retardos, faltas, checadas incompletas y dias pagados.

Una sola fuente para el reporte de Incidencias y para la nomina. Nada de esto
se guarda: se calcula cada vez a partir de las checadas (`attendance_record`),
el horario vigente del empleado (`employee_schedule` + `work_schedule_day`) y
los festivos (`payroll_holiday`).

Por cada empleado y dia:

* Dia laboral = su horario trabaja ese dia de la semana y no es festivo.
* Falta: dia laboral sin ninguna checada.
* Retardo: la primera checada llega despues de la hora de entrada mas la
  tolerancia del horario. Se reportan los minutos tarde contados desde la hora
  de entrada. Es SOLO informativo: no afecta la nomina (decision de RH,
  2026-10-20).
* Checada incompleta: una sola checada en un dia laboral (falta la entrada o la
  salida).
* Trabajo en descanso o festivo: checadas en un dia que no le tocaba.
* Ausencia justificada (employee_leave): vacaciones, permiso con o sin goce o
  incapacidad. Ese dia nunca es falta ni retardo; si de todos modos checo, se
  marca como aviso (`checo_en_ausencia`).

Dias pagados (nomina):
* Dia cubierto por un horario asignado: se paga siempre (laboral, descanso o
  festivo), salvo que sea falta.
* Dia sin horario asignado: se paga solo si tiene checada (como antes de que
  existieran los horarios).
* Ausencias (decisiones de RH, 2026-10-21):
  - vacaciones y permiso con goce: se pagan.
  - permiso sin goce: sus dias laborables no se pagan; un descanso o festivo de
    su horario dentro del permiso se sigue pagando.
  - incapacidad: no se paga ningun dia del rango, ni descansos ni festivos,
    porque el IMSS cubre el subsidio por dias naturales.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta


@dataclass
class Dia:
    fecha: date
    laboral: bool
    festivo: bool
    con_horario: bool
    entrada: time | None = None
    salida: time | None = None
    marcas: list = field(default_factory=list)
    falta: bool = False
    retardo: bool = False
    minutos_retardo: int = 0
    incompleta: bool = False
    trabajo_en_descanso: bool = False
    ausencia: str | None = None
    checo_en_ausencia: bool = False

    @property
    def pagado(self) -> bool:
        if self.ausencia in ("vacation", "paid_leave"):
            return True
        if self.ausencia == "disability":
            return False
        if self.ausencia == "unpaid_leave":
            return self.con_horario and not self.laboral
        return (not self.falta) if self.con_horario else bool(self.marcas)

    @property
    def cuenta_como_ausencia(self) -> bool:
        """Si el dia gasta un dia de su ausencia: la incapacidad cuenta los dias
        naturales; las demas, los laborables de su horario (o todos sin horario)."""
        if self.ausencia is None:
            return False
        return self.ausencia == "disability" or self.laboral or not self.con_horario

    def como_dict(self) -> dict:
        return {
            "date": self.fecha.isoformat(),
            "workday": self.laboral, "holiday": self.festivo, "has_schedule": self.con_horario,
            "start": self.entrada.strftime("%H:%M") if self.entrada else None,
            "end": self.salida.strftime("%H:%M") if self.salida else None,
            "first": self.marcas[0].strftime("%H:%M") if self.marcas else None,
            "last": self.marcas[-1].strftime("%H:%M") if self.marcas else None,
            "marks": len(self.marcas),
            "absence": self.falta, "late": self.retardo, "late_minutes": self.minutos_retardo,
            "incomplete": self.incompleta, "worked_on_rest_day": self.trabajo_en_descanso,
            "leave": self.ausencia, "checked_during_leave": self.checo_en_ausencia,
            "paid": self.pagado,
        }


def clasificar_dia(fecha: date, marcas, horario_del_dia, festivo: bool, tolerancia: int, con_horario: bool,
                   ausencia: str | None = None) -> Dia:
    """Clasifica un dia de un empleado.

    `marcas`: horas (time o datetime) de sus checadas ese dia, en cualquier orden.
    `horario_del_dia`: (entrada, salida) si su horario trabaja ese dia, o None.
    `ausencia`: tipo de ausencia justificada que cubre el dia, o None.
    """
    horas = sorted(m.time() if isinstance(m, datetime) else m for m in (marcas or ()))
    laboral = con_horario and horario_del_dia is not None and not festivo
    dia = Dia(fecha=fecha, laboral=laboral, festivo=festivo, con_horario=con_horario, marcas=horas)
    if horario_del_dia is not None:
        dia.entrada, dia.salida = horario_del_dia
    if ausencia:
        dia.ausencia = ausencia
        dia.checo_en_ausencia = bool(horas)
        return dia
    if laboral:
        if not horas:
            dia.falta = True
            return dia
        llegada = datetime.combine(fecha, horas[0])
        tarde = int((llegada - datetime.combine(fecha, dia.entrada)).total_seconds() // 60)
        if tarde > int(tolerancia):
            dia.retardo = True
            dia.minutos_retardo = tarde
        dia.incompleta = len(horas) == 1
    elif con_horario and horas:
        dia.trabajo_en_descanso = True
    return dia


def dias_del_rango(desde: date, hasta: date):
    actual = desde
    while actual <= hasta:
        yield actual
        actual += timedelta(days=1)


def resumen(dias) -> dict:
    """Totales de un empleado en un rango."""
    dias = list(dias)
    return {
        "workdays": sum(d.laboral for d in dias),
        "attended": sum(d.laboral and not d.falta and not d.ausencia for d in dias),
        "absences": sum(d.falta for d in dias),
        "late": sum(d.retardo for d in dias),
        "late_minutes": sum(d.minutos_retardo for d in dias),
        "incomplete": sum(d.incompleta for d in dias),
        "worked_on_rest_days": sum(d.trabajo_en_descanso for d in dias),
        "paid_days": sum(d.pagado for d in dias),
        "vacation_days": sum(d.ausencia == "vacation" and d.cuenta_como_ausencia for d in dias),
        "paid_leave_days": sum(d.ausencia == "paid_leave" and d.cuenta_como_ausencia for d in dias),
        "unpaid_leave_days": sum(d.ausencia == "unpaid_leave" and d.cuenta_como_ausencia for d in dias),
        "disability_days": sum(d.ausencia == "disability" and d.cuenta_como_ausencia for d in dias),
        "checked_during_leave": sum(d.checo_en_ausencia for d in dias),
    }
