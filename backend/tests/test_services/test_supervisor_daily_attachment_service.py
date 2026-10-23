import pytest
from datetime import datetime
from io import BytesIO

from app.models import SupervisorActivityLog, SupervisorDailyAttachment
from app.services.supervisor_daily_attachment_service import SupervisorDailyAttachmentService
from app.models.session import transaction_context


@pytest.fixture
def sample_activity_log():
    """Crea un entry de bitácora para las pruebas."""
    with transaction_context() as session:
        activity_log = SupervisorActivityLog(
            id_user=1,
            activity_date="2026-09-25",
            content="Prueba de adjuntos",
            id_proyect=1,
            created_by=1,
        )
        session.add(activity_log)
        session.flush()
        log_id = activity_log.id_supervisor_activity_log
        session.commit()
    return log_id


def test_upload_attachment(sample_activity_log):
    """Prueba la subida de un archivo."""
    file_content = b"Este es contenido de prueba"
    file_obj = BytesIO(file_content)

    result = SupervisorDailyAttachmentService.upload_attachment(
        id_supervisor_activity_log=sample_activity_log,
        file_obj=file_obj,
        filename="test.txt",
        description="Archivo de prueba",
        user_id=1,
    )

    assert result is not None
    assert result["original_filename"] == "test.txt"
    assert result["extension"] == ".txt"
    assert result["file_size"] == len(file_content)
    assert result["description"] == "Archivo de prueba"
    assert "sha256" in result.get("file_path", "")


def test_upload_invalid_extension(sample_activity_log):
    """Prueba rechazo de extensión no permitida."""
    file_obj = BytesIO(b"contenido")

    with pytest.raises(Exception) as exc_info:
        SupervisorDailyAttachmentService.upload_attachment(
            id_supervisor_activity_log=sample_activity_log,
            file_obj=file_obj,
            filename="test.exe",
            user_id=1,
        )
    assert "extension" in str(exc_info.value).lower() or "permitida" in str(exc_info.value).lower()


def test_list_by_activity_log(sample_activity_log):
    """Prueba listado de adjuntos por bitácora."""
    # Subir dos archivos
    for i in range(2):
        file_obj = BytesIO(f"contenido {i}".encode())
        SupervisorDailyAttachmentService.upload_attachment(
            id_supervisor_activity_log=sample_activity_log,
            file_obj=file_obj,
            filename=f"test{i}.txt",
            user_id=1,
        )

    # Listar
    attachments = SupervisorDailyAttachmentService.list_by_activity_log(sample_activity_log)
    assert len(attachments) == 2
    assert all(a["id_supervisor_activity_log"] for a in attachments)


def test_delete_attachment(sample_activity_log):
    """Prueba eliminación lógica de adjunto."""
    # Subir un archivo
    result = SupervisorDailyAttachmentService.upload_attachment(
        id_supervisor_activity_log=sample_activity_log,
        file_obj=BytesIO(b"contenido"),
        filename="test.txt",
        user_id=1,
    )
    attachment_id = result["id_supervisor_daily_attachment"]

    # Verificar que existe
    attachments = SupervisorDailyAttachmentService.list_by_activity_log(sample_activity_log)
    assert len(attachments) == 1

    # Eliminar
    SupervisorDailyAttachmentService.delete_attachment(attachment_id)

    # Verificar que ya no está
    attachments = SupervisorDailyAttachmentService.list_by_activity_log(sample_activity_log)
    assert len(attachments) == 0
