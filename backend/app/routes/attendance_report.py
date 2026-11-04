from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from app.services import reporte_de_asistencia as reporte
from app.utils.auth import require_entity_permission, token_required
from app.utils.xlsx_simple import MIME

# Reporte de asistencia para RH: lo controla la capacidad `attendance_report` del Gestor.
bp_attendance_report = Blueprint('attendance_report', __name__, url_prefix='/attendance_report')

TITULOS = {
    "employee": "Empleado", "late": "Retardos", "late_minutes": "Minutos de retardo", "absences": "Faltas",
    "absences_next_to_rest": "Faltas junto a descanso", "pending_justification": "Sin justificar",
    "leave_days": "Dias de permiso o vacaciones", "manual_checks": "Checadas a mano",
    "overtime_minutes": "Horas extra confirmadas (min)", "overtime_pending_minutes": "Horas extra pendientes de RH (min)",
    "alerts": "Alertas", "supervisor": "Supervisor",
    "alert_late": "Retardos repetidos", "alert_absences": "Faltas repetidas",
    "alert_absence_next_to_rest": "Falta junto a descanso o festivo", "alert_manual": "Muchas checadas a mano",
    "alert_pending": "Dias sin justificar",
}


@bp_attendance_report.route('/', methods=['GET'])
@token_required
@require_entity_permission('attendance_report', 'read')
def attendance_report(user_data):
    """Reporte del rango (?start=AAAA-MM-DD&end=AAAA-MM-DD, hasta 31 dias)."""
    return jsonify(reporte.reporte(request.args.get('start'), request.args.get('end')))


@bp_attendance_report.route('/xlsx', methods=['GET'])
@token_required
@require_entity_permission('attendance_report', 'read')
def attendance_report_xlsx(user_data):
    contenido, nombre = reporte.xlsx(request.args.get('start'), request.args.get('end'), TITULOS)
    return Response(contenido, mimetype=MIME, headers={'Content-Disposition': f'attachment; filename="{nombre}"'})
