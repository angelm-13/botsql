import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function InvoiceScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="invoice" title="Invoice" pk="id_invoice" fields={["date_emision", "date_expiration", "subtotal", "tax", "total", "invoice_status", "payment_method", "note", "id_customer_supplier", "fiscal_reference", "serie_csd", "internationalization", "currency", "type_exchange_rate", "tax_certification_supplier", "fiscal_certify_serie"]} fieldTypes={{"date_emision": "text", "date_expiration": "text", "subtotal": "number", "tax": "number", "total": "number", "invoice_status": "text", "payment_method": "text", "note": "text", "id_customer_supplier": "number", "fiscal_reference": "text", "serie_csd": "text", "internationalization": "text", "currency": "text", "type_exchange_rate": "number", "tax_certification_supplier": "number", "fiscal_certify_serie": "text"}} validationRules={validationRules["invoice"] || {}} />;
}
