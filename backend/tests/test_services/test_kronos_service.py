import unittest
from unittest.mock import Mock, patch

from app.services.kronos_service import (
    KronosService,
    attendance_endpoint,
    attendance_statistics,
    people_endpoint,
    summarize_attendance,
)


class TestKronosService(unittest.TestCase):
    def test_endpoints_are_normalized(self):
        source = "https://clock.local/ISAPI/AccessControl/AcsEvent?format=json&security=1&iv=abc"
        self.assertEqual(
            attendance_endpoint(source),
            "https://clock.local/ISAPI/AccessControl/AcsEvent?format=json",
        )
        self.assertEqual(
            people_endpoint(source, "Search"),
            "https://clock.local/ISAPI/AccessControl/UserInfo/Search?format=json",
        )

    def test_summary_and_statistics_match_kronos_contract(self):
        events = [
            {"employeeNoString": "A-01", "time": "2026-08-20T17:10:00-06:00", "doorNo": 1},
            {"employeeNoString": "A-01", "time": "2026-08-20T08:02:00-06:00", "doorNo": 1},
        ]
        report = summarize_attendance(events, [{"employeeNo": "A-01", "name": "Ana"}])
        self.assertEqual(report[0]["firstEntry"], "2026-08-20T08:02:00-06:00")
        self.assertEqual(report[0]["lastExit"], "2026-08-20T17:10:00-06:00")
        self.assertEqual(report[0]["marks"], 2)
        self.assertEqual(attendance_statistics(report)[0]["estimatedHours"], 9.1)

    @patch("app.services.kronos_service.requests.Session")
    def test_people_pagination_uses_digest_session(self, session_factory):
        first = Mock()
        first.raise_for_status.return_value = None
        first.json.return_value = {
            "UserInfoSearch": {
                "responseStatusStrg": "MORE",
                "UserInfo": [{"employeeNo": "1", "name": "Ana"}],
            }
        }
        second = Mock()
        second.raise_for_status.return_value = None
        second.json.return_value = {
            "UserInfoSearch": {
                "responseStatusStrg": "OK",
                "UserInfo": [{"employeeNo": "2", "name": "Luis"}],
            }
        }
        session_factory.return_value.request.side_effect = [first, second]

        people = KronosService(
            {
                "deviceUrl": "https://clock.local",
                "username": "admin",
                "password": "secret",
            }
        ).fetch_people()

        self.assertEqual([person["employeeNo"] for person in people], ["1", "2"])
        self.assertEqual(session_factory.return_value.request.call_count, 2)


if __name__ == "__main__":
    unittest.main()
