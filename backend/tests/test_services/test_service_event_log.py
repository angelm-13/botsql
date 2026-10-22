from __future__ import annotations

from datetime import datetime, timedelta

from tests.conftest import BackendTestCase
from tests.model_factory import build_payload
from app.services.event_log_service import EventLogService


class TestEventLogService(BackendTestCase):
    def test_crud_service_event_log(self):
        created = EventLogService.create(build_payload(EventLogService, {'table_name': 'user', 'field_name': 'user_id', 'action': 'create', 'before_value': 'test_before_value', 'after_value': 'test_after_value', 'created_by': 1}))
        self.assertIsNotNone(created)
        page = EventLogService.list(page=1, per_page=10, filters={}, sort=None)
        self.assertIn("items", page)
        self.assertIn("total", page)

    def _asiento(self, **extra):
        payload = {'table_name': 'user', 'field_name': '*', 'action': 'create',
                   'before_value': '', 'after_value': 'x', 'created_by': 1}
        payload.update(extra)
        return EventLogService.create(build_payload(EventLogService, payload))

    def test_deleting_an_entry_hides_it_but_leaves_its_own_entry(self):
        victima = self._asiento(table_name='entity_permission')
        EventLogService.delete(victima['id_event_log'], user_id=1)

        items = EventLogService.list(page=1, per_page=100, filters={})['items']
        self.assertNotIn(victima['id_event_log'], [i['id_event_log'] for i in items])
        rastro = [i for i in items if i['table_name'] == 'event_log' and i['action'] == 'delete']
        self.assertEqual(len(rastro), 1)
        self.assertIn(str(victima['id_event_log']), str(rastro[0]['before_value']))
        self.assertIn('entity_permission', str(rastro[0]['before_value']))

    def test_editing_an_entry_leaves_its_own_entry(self):
        victima = self._asiento()
        EventLogService.update(victima['id_event_log'], {'after_value': 'alterado'}, user_id=1)

        items = EventLogService.list(page=1, per_page=100, filters={})['items']
        rastro = [i for i in items if i['table_name'] == 'event_log' and i['action'] == 'update']
        self.assertEqual([i['field_name'] for i in rastro], ['after_value'])

    def test_creating_an_entry_does_not_log_itself(self):
        self._asiento()
        items = EventLogService.list(page=1, per_page=100, filters={})['items']
        self.assertEqual([i for i in items if i['table_name'] == 'event_log'], [])

    def test_the_list_shows_the_most_recent_first_by_default(self):
        ahora = datetime.utcnow()
        viejo = self._asiento(creation_date=ahora - timedelta(days=2))
        nuevo = self._asiento(creation_date=ahora)
        medio = self._asiento(creation_date=ahora - timedelta(days=1))

        ids = [i['id_event_log'] for i in EventLogService.list(page=1, per_page=100, filters={})['items']]
        self.assertEqual([i for i in ids if i in {viejo['id_event_log'], nuevo['id_event_log'], medio['id_event_log']}],
                         [nuevo['id_event_log'], medio['id_event_log'], viejo['id_event_log']])

        ids_asc = [i['id_event_log'] for i in EventLogService.list(page=1, per_page=100, filters={}, sort='creation_date')['items']]
        self.assertEqual([i for i in ids_asc if i in {viejo['id_event_log'], nuevo['id_event_log'], medio['id_event_log']}],
                         [viejo['id_event_log'], medio['id_event_log'], nuevo['id_event_log']])
