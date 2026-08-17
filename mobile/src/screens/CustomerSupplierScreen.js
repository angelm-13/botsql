import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function CustomerSupplierScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="customer_supplier" title="CustomerSupplier" pk="id_customer_supplier" fields={["postal_code", "name", "title", "contact_name", "phone", "email", "web_site", "street", "number_ext", "number_int", "neighborhood", "city", "geographic_state", "fiscal_type", "last_fiscal_certification_date", "tax_id"]} fieldTypes={{"postal_code": "text", "name": "text", "title": "text", "contact_name": "text", "phone": "phone", "email": "email", "web_site": "text", "street": "text", "number_ext": "text", "number_int": "text", "neighborhood": "text", "city": "text", "geographic_state": "text", "fiscal_type": "text", "last_fiscal_certification_date": "text", "tax_id": "text"}} validationRules={validationRules["customer_supplier"] || {}} />;
}
