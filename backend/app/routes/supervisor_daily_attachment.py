from flask import Blueprint, jsonify, request

from app.services.supervisor_daily_attachment_service import SupervisorDailyAttachmentService
from app.utils.auth import require_login

bp = Blueprint("supervisor_daily_attachment", __name__, url_prefix="/supervisor_daily_attachment")


@bp.route("/upload", methods=["POST"])
@require_login
def upload_attachment():
    """Sube un adjunto a la bitácora del supervisor."""
    user_id = request.jwt.get("id_user")

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file_obj = request.files["file"]
    id_supervisor_activity_log = request.form.get("id_supervisor_activity_log", type=int)
    description = request.form.get("description")

    if not id_supervisor_activity_log:
        return jsonify({"error": "id_supervisor_activity_log is required"}), 400

    if file_obj.filename == "":
        return jsonify({"error": "No selected file"}), 400

    result = SupervisorDailyAttachmentService.upload_attachment(
        id_supervisor_activity_log=id_supervisor_activity_log,
        file_obj=file_obj,
        filename=file_obj.filename,
        description=description,
        user_id=user_id,
    )

    return jsonify(result), 201


@bp.route("/by_activity_log/<int:id_supervisor_activity_log>", methods=["GET"])
@require_login
def list_by_activity_log(id_supervisor_activity_log):
    """Lista adjuntos de una bitácora específica."""
    attachments = SupervisorDailyAttachmentService.list_by_activity_log(
        id_supervisor_activity_log
    )
    return jsonify({"items": attachments}), 200


@bp.route("/by_project/<int:id_proyect>", methods=["GET"])
@require_login
def list_by_project():
    """Lista adjuntos de un proyecto entre dos fechas."""
    id_proyect = request.args.get("id_proyect", type=int)
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    if not all([id_proyect, date_from, date_to]):
        return (
            jsonify({"error": "id_proyect, date_from, and date_to are required"}),
            400,
        )

    attachments = SupervisorDailyAttachmentService.list_by_project_and_date(
        id_proyect, date_from, date_to
    )
    return jsonify({"items": attachments}), 200


@bp.route("/<int:id_supervisor_daily_attachment>", methods=["DELETE"])
@require_login
def delete_attachment(id_supervisor_daily_attachment):
    """Elimina lógicamente un adjunto."""
    user_id = request.jwt.get("id_user")
    SupervisorDailyAttachmentService.delete_attachment(id_supervisor_daily_attachment, user_id)
    return jsonify({"message": "Attachment deleted"}), 200
