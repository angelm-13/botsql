"""Checadas de asistencia guardadas en la base.

Antes la pantalla de Asistencias solo le preguntaba al checador en vivo y no
guardaba nada. Aqui viven las dos piezas que faltaban:

* `importar_eventos_kronos`: guarda en `attendance_record` los eventos que
  contesta el checador. Es idempotente: cada checada se identifica por
  `<host del equipo>:<serialNo>`, y una que ya estaba no se vuelve a escribir,
  asi que importar dos veces el mismo rango no duplica nada.
* `checadas_en_rango` + `como_eventos_kronos`: leen lo guardado y lo devuelven
  con la forma de un evento del checador, para que el resumen por dia lo siga
  calculando `summarize_attendance` (kronos_service.py) -- una sola regla para
  lo vivo y lo guardado.

* `ligar_empleado` / `desligar_empleado`: dicen que usuario del sistema es cada
  numero del checador (`attendance_employee_link`). La regla es una sola: el
  `id_user` de una checada siempre es el del vinculo vivo de su numero. Por eso
  ligar rellena las checadas que ya estaban guardadas, desligar las deja sin
  empleado, y una importacion nueva ya entra ligada.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from urllib.parse import urlsplit

from sqlalchemy import select, update

from app.models import AttendanceEmployeeLink, AttendanceRecord, User
from app.models.session import transaction_context
from app.services.base_service import CrudService
from app.utils.errors import AppError
from app.utils.tiempo import a_hora_negocio, ahora_utc

FUENTE_KRONOS = "kronos"
LARGO_REFERENCIA = 64


class AttendanceRecordService(CrudService):
    model = AttendanceRecord
    primary_key = "id_attendance_record"
    entity_name = "attendance_record"


def _texto(valor, largo):
    texto = str(valor or "").strip()
    return texto[:largo] or None


def _host_del_equipo(device_url: str) -> str:
    return (urlsplit(str(device_url or "")).hostname or "kronos").lower()


def evento_kronos_a_registro(evento: dict, host: str) -> dict | None:
    """Un evento del checador como fila de `attendance_record`, o None si no sirve.

    Se descarta lo que no es una checada de una persona: sin numero de empleado
    (eventos de puerta, alarmas) o sin una hora que se pueda leer.
    """
    empleado = _texto(evento.get("employeeNoString") or evento.get("employeeNo"), 32)
    if not empleado:
        return None
    try:
        hora = datetime.fromisoformat(str(evento.get("time") or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    hora = a_hora_negocio(hora)

    serie = evento.get("serialNo")
    if serie not in (None, ""):
        referencia = f"{host}:{serie}"
    else:
        # Sin numero de serie, la checada se reconoce por quien y cuando.
        referencia = f"{host}:{empleado}:{hora.isoformat()}"
    return {
        "employee_no": empleado,
        "employee_name": _texto(evento.get("name"), 96),
        "check_time": hora,
        "source": FUENTE_KRONOS,
        "source_ref": referencia[:LARGO_REFERENCIA],
        "door_no": _texto(evento.get("doorNo"), 16),
        "verify_mode": _texto(evento.get("currentVerifyMode"), 40),
    }


def importar_eventos_kronos(eventos, device_url: str, user_id: int, personas=()) -> dict:
    """Guarda las checadas nuevas y cuenta que paso con cada evento.

    `personas` es el directorio del checador: da el nombre cuando el evento no
    lo trae.
    """
    host = _host_del_equipo(device_url)
    nombres = {str(p.get("employeeNo")): p.get("name") for p in personas or ()}
    recibidos = 0
    descartados = 0
    candidatos: dict[str, dict] = {}
    for evento in eventos or ():
        recibidos += 1
        fila = evento_kronos_a_registro(evento, host)
        if fila is None:
            descartados += 1
            continue
        if not fila["employee_name"]:
            fila["employee_name"] = _texto(nombres.get(fila["employee_no"]), 96)
        # El mismo evento repetido dentro de una sola respuesta cuenta una vez.
        candidatos.setdefault(fila["source_ref"], fila)

    guardados = 0
    with transaction_context() as db:
        empleados = _vinculos_vivos(db, FUENTE_KRONOS)
        existentes = set()
        referencias = list(candidatos)
        for inicio in range(0, len(referencias), 500):
            lote = referencias[inicio:inicio + 500]
            existentes.update(db.scalars(
                select(AttendanceRecord.source_ref)
                .where(AttendanceRecord.source == FUENTE_KRONOS)
                .where(AttendanceRecord.source_ref.in_(lote))
            ))
        for referencia, fila in candidatos.items():
            if referencia in existentes:
                continue
            db.add(AttendanceRecord(**fila, id_user=empleados.get(fila["employee_no"]), created_by=user_id))
            guardados += 1

    return {
        "received": recibidos,
        "saved": guardados,
        "already_saved": len(candidatos) - guardados,
        "skipped": descartados,
    }


def checadas_en_rango(desde: date, hasta: date) -> list[AttendanceRecord]:
    """Las checadas vivas del rango, ambos dias incluidos."""
    with transaction_context() as db:
        filas = list(db.scalars(
            select(AttendanceRecord)
            .where(AttendanceRecord.deletion_date.is_(None))
            .where(AttendanceRecord.check_time >= datetime.combine(desde, datetime.min.time()))
            .where(AttendanceRecord.check_time < datetime.combine(hasta + timedelta(days=1), datetime.min.time()))
            .order_by(AttendanceRecord.check_time.desc())
        ))
        for fila in filas:
            db.expunge(fila)
        return filas


def nombres_de_empleados(filas) -> dict[int, str]:
    """El nombre en el sistema de cada empleado ligado que aparece en `filas`."""
    ids = {fila.id_user for fila in filas if fila.id_user}
    if not ids:
        return {}
    with transaction_context() as db:
        return {
            id_user: nombre
            for id_user, nombre in db.execute(
                select(User.id_user, User.full_name).where(User.id_user.in_(ids)))
            if nombre
        }


def como_eventos_kronos(filas, nombres: dict[int, str] | None = None) -> list[dict]:
    """Lo guardado con la forma de un evento del checador.

    Cuando la checada ya esta ligada, el nombre es el del sistema y no el que
    tecleo alguien en el checador.
    """
    nombres = nombres or {}
    return [
        {
            "employeeNoString": fila.employee_no,
            "name": nombres.get(fila.id_user) or fila.employee_name or "",
            "time": fila.check_time.isoformat(),
            "doorNo": fila.door_no or "",
            "currentVerifyMode": fila.verify_mode or "",
        }
        for fila in filas
    ]


def _vinculos_vivos(db, fuente: str) -> dict[str, int]:
    return dict(db.execute(
        select(AttendanceEmployeeLink.employee_no, AttendanceEmployeeLink.id_user)
        .where(AttendanceEmployeeLink.source == fuente)
        .where(AttendanceEmployeeLink.deletion_date.is_(None))
    ).all())


def _numero_valido(employee_no) -> str:
    numero = _texto(employee_no, 32)
    if not numero:
        raise AppError("errors.invalid_field", 400, {"field": "employee_no"})
    return numero


def _asignar_checadas(db, fuente: str, numero: str, id_user: int | None) -> int:
    """Deja todas las checadas del numero con el empleado del vinculo."""
    resultado = db.execute(
        update(AttendanceRecord)
        .where(AttendanceRecord.source == fuente)
        .where(AttendanceRecord.employee_no == numero)
        .values(id_user=id_user)
    )
    return resultado.rowcount or 0


def empleados_para_ligar() -> list[dict]:
    """Los usuarios vivos marcados como empleados, para el selector de la pantalla."""
    with transaction_context() as db:
        filas = db.execute(
            select(User.id_user, User.full_name, User.username)
            .where(User.deletion_date.is_(None))
            .where(User.is_employee.is_(True))
            .order_by(User.full_name)
        ).all()
    return [{"id_user": id_user, "full_name": nombre or "", "username": usuario or ""}
            for id_user, nombre, usuario in filas]


def vinculos_de_empleados(fuente: str = FUENTE_KRONOS) -> list[dict]:
    """Los numeros ligados, con el nombre del empleado en el sistema."""
    with transaction_context() as db:
        filas = db.execute(
            select(AttendanceEmployeeLink.employee_no, AttendanceEmployeeLink.id_user, User.full_name)
            .join(User, User.id_user == AttendanceEmployeeLink.id_user)
            .where(AttendanceEmployeeLink.source == fuente)
            .where(AttendanceEmployeeLink.deletion_date.is_(None))
            .order_by(AttendanceEmployeeLink.employee_no)
        ).all()
    return [{"employee_no": numero, "id_user": id_user, "full_name": nombre or ""}
            for numero, id_user, nombre in filas]


def ligar_empleado(employee_no, id_user, user_id: int, fuente: str = FUENTE_KRONOS) -> dict:
    """Liga un numero del checador a un empleado y rellena sus checadas.

    Si el numero ya estaba ligado a otra persona, ese vinculo se cierra (borrado
    logico) y queda como rastro.
    """
    numero = _numero_valido(employee_no)
    try:
        id_user = int(id_user)
    except (TypeError, ValueError) as exc:
        raise AppError("errors.invalid_field", 400, {"field": "id_user"}) from exc

    with transaction_context() as db:
        empleado = db.get(User, id_user)
        if empleado is None or empleado.deletion_date is not None:
            raise AppError("errors.invalid_field", 400, {"field": "id_user"})
        # Solo checan los empleados: un usuario que no lo es (el administrador
        # del sistema, un cliente del portal) no puede quedar dueño de checadas
        # que luego contaria la nomina.
        if not empleado.is_employee:
            raise AppError("errors.invalid_field", 400, {"field": "id_user", "reason": "not_employee"})
        actual = db.scalars(
            select(AttendanceEmployeeLink)
            .where(AttendanceEmployeeLink.source == fuente)
            .where(AttendanceEmployeeLink.employee_no == numero)
            .where(AttendanceEmployeeLink.deletion_date.is_(None))
        ).first()
        if actual is None or actual.id_user != id_user:
            if actual is not None:
                actual.deletion_date = ahora_utc()
                # El indice unico parcial exige cerrar el anterior antes de abrir
                # el nuevo dentro de la misma transaccion.
                db.flush()
            db.add(AttendanceEmployeeLink(
                source=fuente, employee_no=numero, id_user=id_user, created_by=user_id))
        checadas = _asignar_checadas(db, fuente, numero, id_user)
        nombre = empleado.full_name or ""
    return {"employee_no": numero, "id_user": id_user, "full_name": nombre, "records_linked": checadas}


def desligar_empleado(employee_no, user_id: int, fuente: str = FUENTE_KRONOS) -> dict:
    """Quita el vinculo de un numero; sus checadas quedan sin empleado."""
    numero = _numero_valido(employee_no)
    with transaction_context() as db:
        actual = db.scalars(
            select(AttendanceEmployeeLink)
            .where(AttendanceEmployeeLink.source == fuente)
            .where(AttendanceEmployeeLink.employee_no == numero)
            .where(AttendanceEmployeeLink.deletion_date.is_(None))
        ).first()
        if actual is None:
            raise AppError("errors.resource_not_found", 404)
        actual.deletion_date = ahora_utc()
        checadas = _asignar_checadas(db, fuente, numero, None)
    return {"employee_no": numero, "id_user": None, "records_unlinked": checadas}


def asistencia_por_empleado(db, desde: date, hasta: date, ids=None) -> dict:
    """{id_user: [Dia, ...]} del rango, con las reglas de services/attendance_rules.py.

    `ids`: limita a esos empleados; si no se da, toma a quien tenga horario en
    el rango o checadas ligadas en el rango.
    """
    from app.models import EmployeeSchedule, PayrollHoliday, WorkSchedule, WorkScheduleDay
    from app.services import attendance_rules as reglas

    asignaciones = list(db.scalars(
        select(EmployeeSchedule)
        .where(EmployeeSchedule.deletion_date.is_(None))
        .where(EmployeeSchedule.valid_from <= hasta)
        .where((EmployeeSchedule.valid_to.is_(None)) | (EmployeeSchedule.valid_to >= desde))
    ))
    horarios = {h.id_work_schedule: h for h in db.scalars(select(WorkSchedule))}
    dias_de_horario: dict[int, dict[int, tuple]] = {}
    for d in db.scalars(select(WorkScheduleDay).where(WorkScheduleDay.deletion_date.is_(None))):
        dias_de_horario.setdefault(d.id_work_schedule, {})[d.weekday] = (d.start_time, d.end_time)
    festivos = set(db.scalars(
        select(PayrollHoliday.holiday_date)
        .where(PayrollHoliday.deletion_date.is_(None))
        .where(PayrollHoliday.holiday_date >= desde)
        .where(PayrollHoliday.holiday_date <= hasta)
    ))
    marcas: dict[int, dict[date, list]] = {}
    for id_user, hora in db.execute(
        select(AttendanceRecord.id_user, AttendanceRecord.check_time)
        .where(AttendanceRecord.id_user.isnot(None))
        .where(AttendanceRecord.deletion_date.is_(None))
        .where(AttendanceRecord.check_time >= datetime.combine(desde, datetime.min.time()))
        .where(AttendanceRecord.check_time < datetime.combine(hasta + timedelta(days=1), datetime.min.time()))
    ):
        marcas.setdefault(id_user, {}).setdefault(hora.date(), []).append(hora)

    if ids is None:
        ids = {a.id_user for a in asignaciones} | set(marcas)
    resultado = {}
    for id_user in ids:
        propias = [a for a in asignaciones if a.id_user == id_user]
        dias = []
        for fecha in reglas.dias_del_rango(desde, hasta):
            asignada = next((a for a in propias
                             if a.valid_from <= fecha and (a.valid_to is None or a.valid_to >= fecha)), None)
            horario = horarios.get(asignada.id_work_schedule) if asignada else None
            dias.append(reglas.clasificar_dia(
                fecha, marcas.get(id_user, {}).get(fecha, []),
                dias_de_horario.get(asignada.id_work_schedule, {}).get(fecha.weekday()) if asignada else None,
                fecha in festivos, horario.tolerance_minutes if horario else 0, asignada is not None))
        resultado[id_user] = dias
    return resultado


def incidencias(desde: date, hasta: date) -> list[dict]:
    """Reporte de retardos, faltas e incompletas por empleado (solo informativo)."""
    from app.services import attendance_rules as reglas
    with transaction_context() as db:
        por_empleado = asistencia_por_empleado(db, desde, hasta)
        nombres = dict(db.execute(select(User.id_user, User.full_name)
                                  .where(User.id_user.in_(list(por_empleado) or [0]))).all())
    filas = []
    for id_user, dias in por_empleado.items():
        filas.append({
            "id_user": id_user,
            "full_name": nombres.get(id_user) or f"#{id_user}",
            "has_schedule": any(d.con_horario for d in dias),
            **reglas.resumen(dias),
            "days": [d.como_dict() for d in dias],
        })
    return sorted(filas, key=lambda f: f["full_name"])
