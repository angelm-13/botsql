"""Avisos cuando alguien no checa (revision contable, 2026-10-28, punto 3).

RH es quien sabe a quien le toca checar y a que hora: su horario, sus
vacaciones, permisos e incapacidades, festivos y descansos. Un job corre esto
cada 5 minutos (app/jobs/tasks_rh.py) y avisa (campana):

* Entrada: si ya pasaron `attendance_warning_entry_minutes` (15 por omision)
  desde su hora de entrada y no tiene ninguna checada ese dia, al empleado.
* Supervisor: si a los `attendance_warning_supervisor_minutes` (30) sigue sin
  checar entrada, a su supervisor (`user.supervisor`).
* Salida: si ya pasaron `attendance_warning_exit_minutes` (30) desde su hora de
  salida y solo tiene una checada (entro y no salio), al empleado: sin la
  salida el dia queda pendiente de justificar y no se paga.

No se avisa en descanso, festivo ni ausencia aprobada. Cada aviso sale una sola
vez por dia (se busca el mismo aviso en las ultimas 20 horas). Cada empresa
cambia los minutos en Ajustes de nomina; 0 = sin ese aviso.

El aviso por WhatsApp lo mandaria el flujo del checador (n8n): queda pendiente
de platicarlo con ese equipo y con Alan. Aqui solo la campana del sistema.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select

from app.models import Notification, User
from app.models.session import transaction_context
from app.utils.tiempo import ahora_negocio, ahora_utc

ENTRADA = "attendance_warning_entry_minutes"
SALIDA = "attendance_warning_exit_minutes"
SUPERVISOR = "attendance_warning_supervisor_minutes"
# clave -> (valor por omision, valores permitidos), igual que las demas politicas.
POLITICA_DE_AVISOS = {ENTRADA: (15, range(0, 241)), SUPERVISOR: (30, range(0, 241)), SALIDA: (30, range(0, 241))}

SIN_ENTRADA = "attendance_missing_check_in"
SIN_ENTRADA_EQUIPO = "attendance_missing_check_in_team"
SIN_SALIDA = "attendance_missing_check_out"


def _minutos(db, al_dia) -> dict:
    from app.services.payroll_calculation_service import _vigentes
    capturados = _vigentes(db, tuple(POLITICA_DE_AVISOS), al_dia)
    return {clave: int(capturados.get(clave, por_omision)) for clave, (por_omision, _) in POLITICA_DE_AVISOS.items()}


def _ya_avisado(db, tipo: str, destinatario: int, id_empleado: int) -> bool:
    desde = ahora_utc() - timedelta(hours=20)
    return db.scalars(select(Notification.id_notification)
                      .where(Notification.notification_type == tipo)
                      .where(Notification.id_user_recipient == destinatario)
                      .where(Notification.target_entity == "attendance")
                      .where(Notification.target_id == id_empleado)
                      .where(Notification.creation_date >= desde)).first() is not None


def avisar_checadas_faltantes(ahora: datetime | None = None) -> int:
    """Manda los avisos que tocan `ahora` (hora del negocio). Devuelve cuantos mando."""
    from app.services.attendance_record_service import asistencia_por_empleado
    from app.services.notification_service import create_notification
    ahora = ahora or ahora_negocio()
    hoy = ahora.date()
    pendientes = []
    with transaction_context() as db:
        minutos = _minutos(db, hoy)
        dias = asistencia_por_empleado(db, hoy, hoy)
        empleados = {u.id_user: u for u in db.scalars(
            select(User).where(User.id_user.in_(list(dias) or [0]))
            .where(User.deletion_date.is_(None)).where(User.is_employee.is_(True)))}
        for id_user, lista in dias.items():
            dia = lista[0] if lista else None
            empleado = empleados.get(id_user)
            if empleado is None or dia is None or not dia.laboral or dia.ausencia:
                continue
            entrada = datetime.combine(hoy, dia.entrada)
            salida = datetime.combine(hoy, dia.salida)
            nombre = empleado.full_name or f"#{id_user}"
            if not dia.marcas:
                if minutos[ENTRADA] and ahora >= entrada + timedelta(minutes=minutos[ENTRADA]):
                    pendientes.append((id_user, SIN_ENTRADA, id_user, "No has checado tu entrada",
                                       f"Tu entrada era a las {dia.entrada:%H:%M}. Si ya llegaste, checa ahora."))
                jefe = empleado.supervisor
                if (minutos[SUPERVISOR] and jefe and jefe != id_user
                        and ahora >= entrada + timedelta(minutes=minutos[SUPERVISOR])):
                    pendientes.append((jefe, SIN_ENTRADA_EQUIPO, id_user, f"{nombre} no ha checado su entrada",
                                       f"{nombre} entraba a las {dia.entrada:%H:%M} y no ha checado."))
            elif len(dia.marcas) == 1 and minutos[SALIDA] and ahora >= salida + timedelta(minutes=minutos[SALIDA]):
                pendientes.append((id_user, SIN_SALIDA, id_user, "No has checado tu salida",
                                   f"Tu salida era a las {dia.salida:%H:%M}. Sin la salida, el día queda "
                                   "pendiente de justificar y no se paga."))
        from app.services.employee_leave_service import ve_rh
        destinos = {u.id_user: u for u in db.scalars(select(User).where(User.id_user.in_([p[0] for p in pendientes] or [0])))}
        # Solo a quien su rol deja ver RH en el Gestor (pedido de Alan, 2026-11-05).
        pendientes = [p for p in pendientes if ve_rh(destinos.get(p[0])) and not _ya_avisado(db, p[1], p[0], p[2])]
    enviados = 0
    for destinatario, tipo, id_empleado, titulo, mensaje in pendientes:
        try:
            # created_by es llave a user: lo escribe el sistema a nombre de quien lo recibe.
            create_notification(id_user_recipient=destinatario, notification_type=tipo, title=titulo,
                                message=mensaje, created_by=destinatario,
                                target_entity="attendance", target_id=id_empleado)
            enviados += 1
        except Exception:
            pass
    return enviados
