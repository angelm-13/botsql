from __future__ import annotations

import unittest

from app.services.project_management_service import validate_project_transition
from app.utils.errors import AppError


class TestProjectStateMachine(unittest.TestCase):
    def test_accepts_complete_project_lifecycle(self):
        allowed = {
            # Gerente mueve el proyecto directo desde Borrador, sin pasar
            # por "submitted" -- ver test_project_workflow_service.py para
            # quien tiene permiso de pedir cada una.
            "draft": ("submitted", "authorized", "denied", "blocked"),
            "submitted": ("authorized", "denied", "blocked"),
            "blocked": ("submitted", "authorized", "denied"),
            "authorized": ("in_progress",),
            "in_progress": ("stopped", "completed"),
            "stopped": ("in_progress",),
        }
        for current, targets in allowed.items():
            for target in targets:
                reason = "Motivo requerido" if target in {"denied", "blocked", "stopped"} else None
                self.assertEqual(target, validate_project_transition(current, target, reason))

    def test_maps_legacy_active_status_to_draft(self):
        self.assertEqual("submitted", validate_project_transition("active", "submitted"))

    def test_requires_reason_for_negative_or_paused_states(self):
        for target in ("denied", "blocked"):
            with self.assertRaises(AppError) as raised:
                validate_project_transition("submitted", target)
            self.assertEqual("errors.project_transition_reason_required", raised.exception.message_key)
        with self.assertRaises(AppError):
            validate_project_transition("in_progress", "stopped")

    def test_rejects_unlisted_transitions(self):
        for current, target in (("draft", "in_progress"), ("authorized", "completed"), ("denied", "draft"), ("completed", "in_progress")):
            with self.assertRaises(AppError) as raised:
                validate_project_transition(current, target)
            self.assertEqual("errors.project_invalid_transition", raised.exception.message_key)


if __name__ == "__main__":
    unittest.main()