from __future__ import annotations

import hashlib
from datetime import date
from io import BytesIO

from app.models import SupervisorActivityLog
from app.models.session import transaction_context
from app.services.supervisor_daily_attachment_service import SupervisorDailyAttachmentService
from tests.conftest import BackendTestCase


class TestSupervisorDailyAttachmentService(BackendTestCase):
    def _create_activity_log(self):
        with transaction_context() as session:
            activity_log = SupervisorActivityLog(
                id_user=1,
                activity_date=date(2026, 9, 25),
                content="Prueba de adjuntos",
                id_proyect=1,
                created_by=1,
            )
            session.add(activity_log)
            session.flush()
            return activity_log.id_supervisor_activity_log

    def _upload(self, id_log, filename="test.txt", content=b"contenido", **extra):
        return SupervisorDailyAttachmentService.upload_attachment(
            id_supervisor_activity_log=id_log,
            file_obj=BytesIO(content),
            filename=filename,
            user_id=1,
            **extra,
        )

    def test_upload_attachment(self):
        id_log = self._create_activity_log()
        content = b"Este es contenido de prueba"

        result = self._upload(id_log, content=content, description="Archivo de prueba")

        self.assertEqual("test.txt", result["original_filename"])
        self.assertEqual(".txt", result["extension"])
        self.assertEqual(len(content), result["file_size"])
        self.assertEqual("Archivo de prueba", result["description"])
        self.assertIn(hashlib.sha256(content).hexdigest(), result["file_path"])

    def test_upload_invalid_extension(self):
        id_log = self._create_activity_log()

        with self.assertRaises(Exception) as ctx:
            self._upload(id_log, filename="test.exe")

        message = str(ctx.exception).lower()
        self.assertTrue("extension" in message or "permitida" in message)

    def test_list_by_activity_log(self):
        id_log = self._create_activity_log()
        for i in range(2):
            self._upload(id_log, filename=f"test{i}.txt", content=f"contenido {i}".encode())

        attachments = SupervisorDailyAttachmentService.list_by_activity_log(id_log)

        self.assertEqual(2, len(attachments))
        self.assertEqual({"test0.txt", "test1.txt"}, {a["original_filename"] for a in attachments})

    def test_delete_attachment(self):
        id_log = self._create_activity_log()
        attachment_id = self._upload(id_log)["id_supervisor_daily_attachment"]
        self.assertEqual(1, len(SupervisorDailyAttachmentService.list_by_activity_log(id_log)))

        SupervisorDailyAttachmentService.delete_attachment(attachment_id)

        self.assertEqual(0, len(SupervisorDailyAttachmentService.list_by_activity_log(id_log)))
