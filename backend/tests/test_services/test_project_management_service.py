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
            # Ya no hay salida directa a "in_progress": toda autorizacion
            # pasa primero por la espera de material (obligatoria, ver
            # test_project_workflow_service.py::test_an_authorized_project_cannot_skip_the_wait_for_material).
            "authorized": ("waiting_material",),
            "waiting_material": ("in_progress", "stopped"),
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
    def test_a_project_without_maquila_skips_the_workshop_states(self):
        self.assertEqual("completed", validate_project_transition(
            "authorized", "completed", requires_maquila=False))
        with self.assertRaises(AppError) as raised:
            validate_project_transition(
                "authorized", "waiting_material", requires_maquila=False)
        self.assertEqual("errors.project_invalid_transition", raised.exception.message_key)

    def test_a_stray_boolean_is_a_400_not_a_500(self):
        from app.services.project_management_service import _booleano_estricto

        valores = {"requires_maquila": "xyz"}
        with self.assertRaises(AppError) as raised:
            _booleano_estricto(valores, "requires_maquila")
        self.assertEqual(400, raised.exception.status_code)

        valores = {"requires_maquila": "False"}
        _booleano_estricto(valores, "requires_maquila")
        self.assertIs(False, valores["requires_maquila"])
