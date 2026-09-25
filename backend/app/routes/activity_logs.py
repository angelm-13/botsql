from __future__ import annotations

from datetime import datetime, date
from flask import Blueprint, jsonify, request

from app.services.activity_log_service import (
    create_activity,
    get_activity_by_id,
    get_activities_by_range,
    get_supervisor_pending_activities,
    get_activities_by_project,
    update_activity,
    delete_activity,
)
from app.services.notification_service import create_notification
from app.utils.auth import token_required, require_entity_permission
from app.utils.errors import AppError


bp_activity_logs = Blueprint("activity_logs", __name__, url_prefix="/activity-logs")


def parse_date(date_str):
    """Convierte un string a date. Retorna None si es inválido."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None


@bp_activity_logs.route("", methods=["POST"])
@token_required
def create_activity_log(user_data):
    """
    POST /activity-logs
    Body: {
        "id_proyect": int,
        "activity_date": "2026-09-25",
        "description": "Qué se hizo hoy",
        "status": "pending|in_progress|completed",
        "hours_spent": 8.5,
        "notes": "Notas adicionales"
    }

    Crea un nuevo registro de actividad diaria.
    Solo supervisores pueden crear sus propias actividades.
    """
    id_user = user_data.get('id_user')
    if not id_user:
        raise AppError("Usuario no autenticado", 401)

    data = request.get_json() or {}

    # Validaciones
    id_proyect = data.get('id_proyect')
    activity_date_str = data.get('activity_date')
    description = data.get('description', '').strip()

    if not id_proyect:
        raise AppError("id_proyect es requerido", 400)
    if not activity_date_str:
        raise AppError("activity_date es requerido", 400)
    if not description:
        raise AppError("description no puede estar vacía", 400)

    activity_date = parse_date(activity_date_str)
    if not activity_date:
        raise AppError("activity_date debe estar en formato YYYY-MM-DD", 400)

    status = data.get('status', 'pending')
    if status not in ['pending', 'in_progress', 'completed']:
        status = 'pending'

    hours_spent = data.get('hours_spent')
    if hours_spent:
        try:
            from decimal import Decimal
            hours_spent = Decimal(str(hours_spent))
        except:
            hours_spent = None

    notes = data.get('notes', '').strip() or None

    # Crear la actividad
    activity = create_activity(
        id_proyect=id_proyect,
        id_supervisor=id_user,
        activity_date=activity_date,
        description=description,
        status=status,
        hours_spent=hours_spent,
        notes=notes,
        created_by=id_user,
    )

    # Crear notificación (opcional - si el gerente lo configuró así)
    # Por ahora, solo registramos silenciosamente
    # create_notification(
    #     id_user_recipient=gerente_id,
    #     notification_type='activity_log_created',
    #     title=f"Bitácora creada",
    #     ...
    # )

    return jsonify(activity.serialize()), 201


@bp_activity_logs.route("", methods=["GET"])
@token_required
def list_activities(user_data):
    """
    GET /activity-logs?id_proyect=1&id_supervisor=5&start_date=2026-09-01&end_date=2026-09-30&limit=50&offset=0

    Lista actividades con filtros opcionales.
    Los supervisores solo ven sus propias actividades.
    Los gerentes/admin ven todas.
    """
    id_user = user_data.get('id_user')
    if not id_user:
        raise AppError("Usuario no autenticado", 401)

    # Filtros
    id_proyect = request.args.get('id_proyect', type=int)
    id_supervisor = request.args.get('id_supervisor', type=int)
    start_date = parse_date(request.args.get('start_date'))
    end_date = parse_date(request.args.get('end_date'))
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))

    # Validación: supervisores solo ven sus propias actividades
    user_type = user_data.get('user_type', '').lower()
    is_admin = user_data.get('is_superuser') or user_data.get('is_bootstrap_admin')

    if not is_admin and user_type not in ['admin', 'gerente']:
        # Es supervisor, solo ve sus propias actividades
        id_supervisor = id_user

    activities = get_activities_by_range(
        id_proyect=id_proyect,
        id_supervisor=id_supervisor,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )

    return jsonify([a.serialize() for a in activities])


@bp_activity_logs.route("/<int:id_activity>", methods=["GET"])
@token_required
def get_activity(user_data, id_activity):
    """
    GET /activity-logs/{id}

    Obtiene una actividad específica.
    """
    activity = get_activity_by_id(id_activity)

    if not activity:
        raise AppError("Actividad no encontrada", 404)

    id_user = user_data.get('id_user')
    is_admin = user_data.get('is_superuser') or user_data.get('is_bootstrap_admin')
    user_type = user_data.get('user_type', '').lower()

    # Validación: supervisores solo ven sus propias actividades
    if not is_admin and user_type not in ['admin', 'gerente']:
        if activity.id_supervisor != id_user:
            raise AppError("No tienes permiso para ver esta actividad", 403)

    return jsonify(activity.serialize())


@bp_activity_logs.route("/<int:id_activity>", methods=["PUT"])
@token_required
def update_activity_log(user_data, id_activity):
    """
    PUT /activity-logs/{id}
    Body: {
        "description": "Nueva descripción",
        "status": "completed",
        "hours_spent": 8.5,
        "notes": "Nuevas notas"
    }

    Actualiza una actividad.
    Solo el supervisor propietario puede actualizar.
    """
    id_user = user_data.get('id_user')
    if not id_user:
        raise AppError("Usuario no autenticado", 401)

    activity = get_activity_by_id(id_activity)
    if not activity:
        raise AppError("Actividad no encontrada", 404)

    # Solo el supervisor propietario puede editar
    if activity.id_supervisor != id_user:
        raise AppError("No tienes permiso para editar esta actividad", 403)

    data = request.get_json() or {}

    # Actualizar campos permitidos
    update_fields = {}
    if 'description' in data:
        update_fields['description'] = str(data['description']).strip()
    if 'status' in data:
        status = data['status']
        if status in ['pending', 'in_progress', 'completed']:
            update_fields['status'] = status
    if 'hours_spent' in data:
        try:
            from decimal import Decimal
            update_fields['hours_spent'] = Decimal(str(data['hours_spent']))
        except:
            pass
    if 'notes' in data:
        update_fields['notes'] = str(data['notes']).strip() or None

    updated_activity = update_activity(id_activity, id_supervisor=id_user, **update_fields)

    if not updated_activity:
        raise AppError("No se pudo actualizar la actividad", 400)

    return jsonify(updated_activity.serialize())


@bp_activity_logs.route("/<int:id_activity>", methods=["DELETE"])
@token_required
def delete_activity_log(user_data, id_activity):
    """
    DELETE /activity-logs/{id}

    Elimina una actividad (soft delete).
    Solo el supervisor propietario puede eliminar.
    """
    id_user = user_data.get('id_user')
    if not id_user:
        raise AppError("Usuario no autenticado", 401)

    activity = get_activity_by_id(id_activity)
    if not activity:
        raise AppError("Actividad no encontrada", 404)

    # Solo el supervisor propietario puede eliminar
    if activity.id_supervisor != id_user:
        raise AppError("No tienes permiso para eliminar esta actividad", 403)

    success = delete_activity(id_activity, id_supervisor=id_user)

    if not success:
        raise AppError("No se pudo eliminar la actividad", 400)

    return jsonify({'message': 'Actividad eliminada'}), 200


@bp_activity_logs.route("/pending", methods=["GET"])
@token_required
def get_pending_activities(user_data):
    """
    GET /activity-logs/pending?days=7

    Obtiene las actividades pendientes o en progreso del supervisor actual.
    Útil para un recordatorio de bitácoras sin completar.
    """
    id_user = user_data.get('id_user')
    if not id_user:
        raise AppError("Usuario no autenticado", 401)

    days = int(request.args.get('days', 7))

    activities = get_supervisor_pending_activities(id_user, days=days)

    return jsonify([a.serialize() for a in activities])


@bp_activity_logs.route("/project/<int:id_proyect>/report", methods=["GET"])
@token_required
def get_project_activity_report(user_data, id_proyect):
    """
    GET /activity-logs/project/{id_proyect}/report?start_date=2026-09-01&end_date=2026-09-30

    Obtiene un reporte de todas las actividades de un proyecto en un rango de fechas.
    Útil para generar reportes o descargar bitácoras en CSV/PDF.
    """
    id_user = user_data.get('id_user')
    if not id_user:
        raise AppError("Usuario no autenticado", 401)

    start_date = parse_date(request.args.get('start_date'))
    end_date = parse_date(request.args.get('end_date'))

    activities = get_activities_by_project(
        id_proyect=id_proyect,
        start_date=start_date,
        end_date=end_date,
    )

    return jsonify([a.serialize() for a in activities])
