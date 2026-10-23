import hashlib
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app.models.session import transaction_context
from app.models.supervisor_activity_log import SupervisorActivityLog
from app.models.supervisor_daily_attachment import SupervisorDailyAttachment
from app.utils.errors import AppError


class SupervisorDailyAttachmentService:
    UPLOAD_BASE_DIR = "/uploads/supervisor_daily"
    ALLOWED_EXTENSIONS = {".txt", ".docx", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp"}
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB

    @staticmethod
    def upload_attachment(
        id_supervisor_activity_log: int,
        file_obj,
        filename: str,
        description: str = None,
        user_id: int = None,
    ) -> dict:
        """
        Sube un adjunto a la bitácora del supervisor.

        Args:
            id_supervisor_activity_log: ID de la bitácora a la que pertenece
            file_obj: Archivo desde request.files
            filename: Nombre original del archivo
            description: Descripción opcional
            user_id: ID del usuario que sube (para auditoría)

        Returns:
            Dict con los datos del attachment creado
        """
        with transaction_context() as session:
            # Verificar que la bitácora existe
            activity_log = session.scalar(
                select(SupervisorActivityLog).where(
                    SupervisorActivityLog.id_supervisor_activity_log
                    == id_supervisor_activity_log
                )
            )
            if not activity_log:
                raise AppError("Bitacora no encontrada", 404)

            # Validar extensión
            file_ext = Path(filename).suffix.lower()
            if file_ext not in SupervisorDailyAttachmentService.ALLOWED_EXTENSIONS:
                raise AppError(
                    f"Extension no permitida. Permitidas: {', '.join(SupervisorDailyAttachmentService.ALLOWED_EXTENSIONS)}",
                    400,
                )

            # Leer archivo en memoria para validaciones
            file_data = file_obj.read()
            file_obj.seek(0)

            if len(file_data) > SupervisorDailyAttachmentService.MAX_FILE_SIZE:
                raise AppError(
                    f"Archivo demasiado grande. Máximo: {SupervisorDailyAttachmentService.MAX_FILE_SIZE / (1024*1024):.0f}MB",
                    413,
                )

            # Calcular SHA256
            sha256_hash = hashlib.sha256(file_data).hexdigest()

            # Crear ruta: /uploads/supervisor_daily/YYYY/MM/DD/sha256.ext
            date_str = activity_log.activity_date
            year, month, day = date_str.split("-") if "-" in date_str else ("2026", "09", "25")
            dir_path = f"{SupervisorDailyAttachmentService.UPLOAD_BASE_DIR}/{year}/{month}/{day}"
            os.makedirs(dir_path, exist_ok=True)

            file_path = f"{dir_path}/{sha256_hash}{file_ext}"

            # Guardar archivo en disco
            full_path = file_path  # En Docker/K8s, esto apunta a /uploads montado
            with open(full_path, "wb") as f:
                f.write(file_data)

            # Registrar en BD
            mime_type = SupervisorDailyAttachmentService._guess_mime_type(file_ext)
            attachment = SupervisorDailyAttachment(
                id_supervisor_activity_log=id_supervisor_activity_log,
                attachment_date=activity_log.activity_date,
                file_path=file_path,
                original_filename=filename,
                extension=file_ext,
                mime_type=mime_type,
                file_size=len(file_data),
                sha256=sha256_hash,
                description=description,
                created_by=user_id or 1,
            )
            session.add(attachment)
            session.flush()

            return {
                "id_supervisor_daily_attachment": attachment.id_supervisor_daily_attachment,
                "file_path": attachment.file_path,
                "original_filename": attachment.original_filename,
                "extension": attachment.extension,
                "file_size": attachment.file_size,
                "description": attachment.description,
                "creation_date": attachment.creation_date.isoformat(),
            }

    @staticmethod
    def list_by_activity_log(id_supervisor_activity_log: int) -> list:
        """Lista todos los adjuntos de una bitácora."""
        with transaction_context() as session:
            attachments = session.scalars(
                select(SupervisorDailyAttachment)
                .where(
                    SupervisorDailyAttachment.id_supervisor_activity_log
                    == id_supervisor_activity_log
                )
                .where(SupervisorDailyAttachment.deletion_date.is_(None))
            ).all()
            return [
                {
                    "id_supervisor_daily_attachment": a.id_supervisor_daily_attachment,
                    "file_path": a.file_path,
                    "original_filename": a.original_filename,
                    "extension": a.extension,
                    "file_size": a.file_size,
                    "mime_type": a.mime_type,
                    "description": a.description,
                    "creation_date": a.creation_date.isoformat(),
                }
                for a in attachments
            ]

    @staticmethod
    def list_by_project_and_date(id_proyect: int, date_from: str, date_to: str) -> list:
        """Lista adjuntos de un proyecto entre dos fechas."""
        with transaction_context() as session:
            attachments = session.scalars(
                select(SupervisorDailyAttachment)
                .join(SupervisorActivityLog)
                .where(SupervisorActivityLog.id_proyect == id_proyect)
                .where(SupervisorDailyAttachment.attachment_date >= date_from)
                .where(SupervisorDailyAttachment.attachment_date <= date_to)
                .where(SupervisorDailyAttachment.deletion_date.is_(None))
            ).all()
            return [
                {
                    "id_supervisor_daily_attachment": a.id_supervisor_daily_attachment,
                    "attachment_date": a.attachment_date,
                    "file_path": a.file_path,
                    "original_filename": a.original_filename,
                    "extension": a.extension,
                    "file_size": a.file_size,
                    "mime_type": a.mime_type,
                    "description": a.description,
                    "creation_date": a.creation_date.isoformat(),
                }
                for a in attachments
            ]

    @staticmethod
    def delete_attachment(id_supervisor_daily_attachment: int, user_id: int = None) -> None:
        """Elimina lógicamente un adjunto."""
        with transaction_context() as session:
            attachment = session.scalar(
                select(SupervisorDailyAttachment).where(
                    SupervisorDailyAttachment.id_supervisor_daily_attachment
                    == id_supervisor_daily_attachment
                )
            )
            if not attachment:
                raise AppError("Adjunto no encontrado", 404)

            attachment.deletion_date = datetime.utcnow()
            session.add(attachment)

    @staticmethod
    def _guess_mime_type(extension: str) -> str:
        """Adivina el MIME type por extensión."""
        mime_map = {
            ".txt": "text/plain",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
        }
        return mime_map.get(extension.lower(), "application/octet-stream")
