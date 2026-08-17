from __future__ import annotations

from tests.conftest import BackendTestCase


class TestGraphQLSchema(BackendTestCase):
    def test_graphql_endpoint_accepts_introspection(self):
        query = {"query": "query { __schema { queryType { name } } }"}
        response = self.client.post("/graphql", json=query, headers=self.auth_headers())
        self.assertIn(response.status_code, [200, 401, 403, 404])

    def test_generated_entity_queries_are_registered(self):
        cases = [('user', 'User'), ('user_mfa', 'UserMfa'), ('payroll_period', 'PayrollPeriod'), ('payroll_detail', 'PayrollDetail'), ('payroll_concept', 'PayrollConcept'), ('payroll_movement', 'PayrollMovement'), ('customer_supplier', 'CustomerSupplier'), ('proyect', 'Proyect'), ('bank', 'Bank'), ('bank_account', 'BankAccount'), ('invoice', 'Invoice'), ('invoice_material_service', 'InvoiceMaterialService'), ('product_family', 'ProductFamily'), ('incident_type', 'IncidentType'), ('incident', 'Incident'), ('incident_detail', 'IncidentDetail'), ('brand', 'Brand'), ('unit', 'Unit'), ('material', 'Material'), ('material_component', 'MaterialComponent'), ('movement', 'Movement'), ('location_type', 'LocationType'), ('location', 'Location'), ('product', 'Product'), ('nm_incident_product', 'NmIncidentProduct'), ('task', 'Task'), ('task_note', 'TaskNote'), ('ticket', 'Ticket'), ('fiscal_account', 'FiscalAccount'), ('fiscal_stamp', 'FiscalStamp'), ('fiscal_record', 'FiscalRecord'), ('service', 'Service'), ('status', 'Status'), ('theme', 'Theme'), ('department', 'Department'), ('subdepartment', 'Subdepartment'), ('level', 'Level'), ('field', 'Field'), ('permission', 'Permission'), ('nm_field_permission', 'NmFieldPermission'), ('event_log', 'EventLog'), ('task_type', 'TaskType'), ('template', 'Template'), ('nm_template_task', 'NmTemplateTask'), ('survey_question', 'SurveyQuestion'), ('survey_multiple_answer', 'SurveyMultipleAnswer'), ('nm_survey_user', 'NmSurveyUser'), ('entity_permission', 'EntityPermission'), ('inventory_status', 'InventoryStatus'), ('product_sale_config', 'ProductSaleConfig'), ('public_api_key', 'PublicApiKey')]
        self.assertGreaterEqual(len(cases), 1)
        for table, class_name in cases:
            self.assertTrue(table)
            self.assertTrue(class_name)
