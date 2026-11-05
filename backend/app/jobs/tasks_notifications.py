"""Avisos tambien por correo (respuestas de RH, 2026-11-05).

Cada aviso de la campana se manda ademas al correo de quien lo recibe, si tiene uno
capturado en su usuario y no apago "Recibir avisos por correo". El correo NO es
obligatorio: sin el, el aviso solo queda en la campana, como siempre. La cuenta que
envia es una sola por empresa (variables MAIL_* / SMTP_* del servidor, la misma que
usan citas y recuperacion de contrasena: services/email_service.py); sin ella no se
manda nada. Igual que el correo de citas: en segundo plano, con reintentos, y una
sola vez por aviso (`notification.email_sent_at`).
"""
from __future__ import annotations

import os
import smtplib

from app.jobs.celery_app import celery
from app.jobs.task_helpers import result_ok
from app.models import Notification, User
from app.models.session import transaction_context
from app.services.email_service import send_email
from app.utils.tiempo import ahora_utc


def correo_del_aviso(aviso: Notification, persona: User) -> tuple[str, str]:
    """(asunto, cuerpo) del correo de un aviso."""
    base = (os.getenv("PUBLIC_FRONTEND_BASE_URL") or "").rstrip("/")
    lineas = [f"Hola, {persona.full_name or persona.username or ''}".rstrip(", ") + ".", "", aviso.title]
    if aviso.message:
        lineas += ["", aviso.message]
    if base:
        lineas += ["", f"Ábrelo en el sistema: {base}"]
    lineas += ["", "Este aviso también está en la campana del sistema. Si no quieres recibirlo por correo,",
               "pide que desmarquen «Recibir avisos por correo» en tu usuario."]
    return f"TYAKXA · {aviso.title}"[:200], "\n".join(lineas)


@celery.task(
    bind=True,
    name="app.jobs.tasks_notifications.send_notification_email",
    autoretry_for=(OSError, smtplib.SMTPException),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_notification_email(self, id_notification: int) -> dict:
    del self
    with transaction_context() as db:
        aviso = db.query(Notification).filter(Notification.id_notification == id_notification).with_for_update().first()
        if aviso is None or aviso.deletion_date is not None:
            return result_ok("jobs.notifications.skipped", id_notification=id_notification)
        if aviso.email_sent_at is not None:
            return result_ok("jobs.notifications.already_sent", id_notification=id_notification)
        persona = db.get(User, aviso.id_user_recipient)
        correo = str(getattr(persona, "email", "") or "").strip()
        if persona is None or persona.deletion_date is not None or not correo or not persona.receive_email_notifications:
            return result_ok("jobs.notifications.no_email", id_notification=id_notification)
        asunto, cuerpo = correo_del_aviso(aviso, persona)
        if not send_email(correo, asunto, cuerpo):
            return result_ok("jobs.notifications.smtp_not_configured", id_notification=id_notification)
        aviso.email_sent_at = ahora_utc()
        return result_ok("jobs.notifications.email_sent", id_notification=id_notification)
