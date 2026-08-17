from __future__ import annotations

from tests.conftest import BackendTestCase


class TestCeleryJobs(BackendTestCase):
    def test_celery_app_imports(self):
        try:
            from celery_worker import celery_app
        except ModuleNotFoundError:
            self.skipTest("celery_worker.py has not been generated yet")
        self.assertIsNotNone(celery_app)

    def test_jobs_package_imports(self):
        try:
            import app.jobs
        except ModuleNotFoundError:
            self.skipTest("app.jobs has not been generated yet")
        self.assertTrue(True)
