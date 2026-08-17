import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function InvoiceMaterialServiceScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="invoice_material_service" title="InvoiceMaterialService" pk="id_invoice_material_service" fields={["id_invoice", "id_material", "id_service", "invoice_material_service_description", "max_requirement_date", "is_directly_related_to_product_service_creation", "id_authorized", "id_status", "id_buyer", "id_customer_supplier", "gross_price", "quantity", "id_product", "line_type", "tax_applicable", "line_tax"]} fieldTypes={{"id_invoice": "number", "id_material": "number", "id_service": "number", "invoice_material_service_description": "text", "max_requirement_date": "text", "is_directly_related_to_product_service_creation": "text", "id_authorized": "number", "id_status": "number", "id_buyer": "number", "id_customer_supplier": "number", "gross_price": "number", "quantity": "number", "id_product": "number", "line_type": "text", "tax_applicable": "text", "line_tax": "number"}} validationRules={validationRules["invoice_material_service"] || {}} />;
}
