"""Reporte de asistencia para RH (punto 8 de RH, diseño aprobado el 2026-11-04).

Semana o quincena, una fila por empleado: retardos, faltas, dias sin justificar,
permisos y vacaciones, checadas capturadas o corregidas a mano (las de
attendance_correction, que ya llevan el motivo del supervisor) y horas extra
(confirmadas por RH y pendientes). Marca patrones que RH quiere ver:

* retardos en el periodo >= `report_alert_late`
* faltas en el periodo >= `report_alert_absences`
* falta pegada a un descanso o festivo (alarga el fin de semana o el puente)
* checadas a mano >= `report_alert_manual`
* dias pendientes de justificar (una sola checada)
* supervisores que capturan a mano >= `report_alert_supervisor_manual`

Los limites se ajustan en Ajustes de nomina (0 = sin esa alerta). Las reglas
de cada dia son las de attendance_rules.py; aqui solo se cuentan. Solo lectura.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select

from app.models import AttendanceCorrection, Overtime, User
from app.models.session import transaction_context
from app.utils.errors import AppError
from app.utils.xlsx_simple import libro

RETARDOS, FALTAS = "report_alert_late", "report_alert_absences"
A_MANO, SUPERVISOR_A_MANO = "report_alert_manual", "report_alert_supervisor_manual"
# clave -> (valor por omision, valores permitidos), como las demas politicas.
POLITICA_DEL_REPORTE = {RETARDOS: (3, range(0, 32)), FALTAS: (2, range(0, 32)),
                        A_MANO: (2, range(0, 32)), SUPERVISOR_A_MANO: (5, range(0, 101))}
MAX_DIAS = 31
ALTA, MEDIA = "high", "medium"


def _fecha(valor, campo) -> date:
    try:
        return date.fromisoformat(str(valor))
    except (TypeError, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": campo}) from exc


def limites(db, al_dia: date) -> dict:
    from app.services.payroll_calculation_service import _vigentes
    capturados = _vigentes(db, tuple(POLITICA_DEL_REPORTE), al_dia)
    return {clave: int(capturados.get(clave, defecto)) for clave, (defecto, _) in POLITICA_DEL_REPORTE.items()}


def _faltas_junto_a_descanso(dias) -> int:
    """Faltas cuyo dia anterior o siguiente (dentro del rango) es descanso o festivo."""
    descanso = [not d.laboral or d.festivo for d in dias]
    return sum(1 for i, d in enumerate(dias) if d.falta and (
        (i > 0 and descanso[i - 1]) or (i + 1 < len(dias) and descanso[i + 1])))


def _alertas(fila: dict, lim: dict) -> list[dict]:
    alertas = []
    if lim[RETARDOS] and fila["late"] >= lim[RETARDOS]:
        alertas.append({"code": "late", "level": MEDIA, "value": fila["late"]})
    if lim[FALTAS] and fila["absences"] >= lim[FALTAS]:
        alertas.append({"code": "absences", "level": ALTA, "value": fila["absences"]})
    if fila["absences_next_to_rest"]:
        alertas.append({"code": "absence_next_to_rest", "level": ALTA, "value": fila["absences_next_to_rest"]})
    if lim[A_MANO] and fila["manual_checks"] >= lim[A_MANO]:
        alertas.append({"code": "manual", "level": MEDIA, "value": fila["manual_checks"]})
    if fila["pending_justification"]:
        alertas.append({"code": "pending", "level": MEDIA, "value": fila["pending_justification"]})
    return alertas


def reporte(desde, hasta) -> dict:
    from app.services.attendance_record_service import asistencia_por_empleado
    from app.services.attendance_rules import resumen
    from app.services.overtime_service import CONFIRMADA, PENDIENTE_RH
    desde, hasta = _fecha(desde, "start"), _fecha(hasta, "end")
    if hasta < desde or (hasta - desde).days + 1 > MAX_DIAS:
        raise AppError("errors.invalid_field", 400, {"field": "end", "reason": "range"})
    with transaction_context() as db:
        lim = limites(db, hasta)
        por_empleado = asistencia_por_empleado(db, desde, hasta)
        a_mano: dict[int, list] = {}
        por_supervisor: dict[int, int] = {}
        for c in db.scalars(select(AttendanceCorrection)
                            .where(AttendanceCorrection.check_date.between(desde, hasta))
                            .where(AttendanceCorrection.deletion_date.is_(None))):
            a_mano.setdefault(c.id_user, []).append(c)
            por_supervisor[c.created_by] = por_supervisor.get(c.created_by, 0) + 1
        extra = {(u, e): int(m or 0) for u, e, m in db.execute(
            select(Overtime.id_user, Overtime.approval_status, func.sum(Overtime.minutes))
            .where(Overtime.work_date.between(desde, hasta)).where(Overtime.deletion_date.is_(None))
            .group_by(Overtime.id_user, Overtime.approval_status))}
        ids = set(por_empleado) | set(a_mano) | {u for u, _ in extra}
        nombres = dict(db.execute(select(User.id_user, User.full_name)
                                  .where(User.id_user.in_(list(ids | set(por_supervisor)) or [0]))).all())
        filas = []
        for id_user in ids:
            dias = por_empleado.get(id_user, [])
            r = resumen(dias)
            correcciones = a_mano.get(id_user, [])
            fila = {
                "id_user": id_user, "full_name": nombres.get(id_user) or f"#{id_user}",
                "late": r["late"], "late_minutes": r["late_minutes"], "absences": r["absences"],
                "absences_next_to_rest": _faltas_junto_a_descanso(dias),
                "pending_justification": r["pending_justification"],
                "leave_days": r["vacation_days"] + r["paid_leave_days"] + r["unpaid_leave_days"] + r["disability_days"],
                "manual_checks": len(correcciones),
                "manual_added": sum(1 for c in correcciones if c.previous_time is None),
                "manual_exceptions": sum(1 for c in correcciones if c.is_exception),
                "manual_reasons": [{"date": c.check_date.isoformat(), "reason": c.reason,
                                    "by": nombres.get(c.created_by) or f"#{c.created_by}"}
                                   for c in sorted(correcciones, key=lambda c: c.check_date)],
                "overtime_minutes": extra.get((id_user, CONFIRMADA), 0),
                "overtime_pending_minutes": extra.get((id_user, PENDIENTE_RH), 0),
            }
            fila["alerts"] = _alertas(fila, lim)
            filas.append(fila)
        supervisores = sorted(
            ({"id_user": u, "full_name": nombres.get(u) or f"#{u}", "manual_checks": n,
              "alert": bool(lim[SUPERVISOR_A_MANO]) and n >= lim[SUPERVISOR_A_MANO]}
             for u, n in por_supervisor.items()), key=lambda s: -s["manual_checks"])
    # Primero quien tiene alertas altas, luego medias, luego el resto; dentro, por nombre.
    peso = lambda f: (-sum(2 if a["level"] == ALTA else 1 for a in f["alerts"]), f["full_name"])  # noqa: E731
    return {"start": desde.isoformat(), "end": hasta.isoformat(), "limits": lim,
            "employees": sorted(filas, key=peso), "supervisors": supervisores,
            "with_alerts": sum(1 for f in filas if f["alerts"])}


def xlsx(desde, hasta, titulos: dict) -> tuple[bytes, str]:
    datos = reporte(desde, hasta)
    columnas = ("late", "late_minutes", "absences", "absences_next_to_rest", "pending_justification", "leave_days",
                "manual_checks", "overtime_minutes", "overtime_pending_minutes")
    tabla = [[titulos["employee"]] + [titulos[c] for c in columnas] + [titulos["alerts"]]]
    for f in datos["employees"]:
        tabla.append([f["full_name"]] + [f[c] for c in columnas]
                     + [", ".join(titulos[f"alert_{a['code']}"] for a in f["alerts"])])
    if datos["supervisors"]:
        tabla += [[], [titulos["supervisor"], titulos["manual_checks"]]]
        tabla += [[s["full_name"], s["manual_checks"]] for s in datos["supervisors"]]
    nombre = f"asistencia_{datos['start']}_{datos['end']}.xlsx"
    return libro(f"Asistencia {datos['start']}", tabla), nombre



MAX_DIAS_BITACORA = 366


def bitacora(desde, hasta, id_supervisor=None) -> dict:
    """Bitacora de correcciones de checadas para RH (decision del 2026-11-04: el
    supervisor corrige sin limite y RH ve quien movio que, para detectar malas
    practicas). Cada correccion con la hora de antes y la nueva, el motivo, quien
    la hizo y cuando; filtrable por quien la capturo."""
    desde, hasta = _fecha(desde, "start"), _fecha(hasta, "end")
    if hasta < desde or (hasta - desde).days + 1 > MAX_DIAS_BITACORA:
        raise AppError("errors.invalid_field", 400, {"field": "end", "reason": "range"})
    consulta = (select(AttendanceCorrection).where(AttendanceCorrection.check_date.between(desde, hasta))
                .where(AttendanceCorrection.deletion_date.is_(None)))
    if id_supervisor not in (None, ""):
        try:
            consulta = consulta.where(AttendanceCorrection.created_by == int(id_supervisor))
        except (TypeError, ValueError) as exc:
            raise AppError("errors.invalid_field", 400, {"field": "id_supervisor"}) from exc
    with transaction_context() as db:
        filas = db.scalars(consulta.order_by(AttendanceCorrection.creation_date.desc(),
                                             AttendanceCorrection.id_attendance_correction.desc())).all()
        quienes = {f.created_by for f in filas} | {f.id_user for f in filas}
        # Para el filtro: todos los que han corregido algo en el rango, aunque el filtro deje a uno.
        capturistas = set(db.scalars(select(AttendanceCorrection.created_by).distinct()
                                     .where(AttendanceCorrection.check_date.between(desde, hasta))
                                     .where(AttendanceCorrection.deletion_date.is_(None))))
        nombres = dict(db.execute(select(User.id_user, User.full_name)
                                  .where(User.id_user.in_(list(quienes | capturistas) or [0]))).all())
        hora = lambda v: v.strftime("%H:%M") if v else None  # noqa: E731
        return {
            "start": desde.isoformat(), "end": hasta.isoformat(),
            "supervisors": sorted(({"id_user": u, "full_name": nombres.get(u) or f"#{u}"} for u in capturistas),
                                  key=lambda s: s["full_name"]),
            "corrections": [{
                "id_attendance_correction": f.id_attendance_correction, "date": f.check_date.isoformat(),
                "id_user": f.id_user, "employee": nombres.get(f.id_user) or f"#{f.id_user}",
                "previous_time": hora(f.previous_time), "new_time": hora(f.new_time), "added": f.previous_time is None,
                "reason": f.reason, "is_exception": bool(f.is_exception),
                "by": nombres.get(f.created_by) or f"#{f.created_by}", "id_by": f.created_by,
                "created_at": f.creation_date.isoformat(timespec="minutes") if f.creation_date else None,
            } for f in filas],
        }
