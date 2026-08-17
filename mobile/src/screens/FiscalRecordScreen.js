import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function FiscalRecordScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="fiscal_record" title="FiscalRecord" pk="id_fiscal_record" fields={["fiscal_record_name", "id_fiscal_account", "amount", "type", "id_fiscal_stamp"]} fieldTypes={{"fiscal_record_name": "text", "id_fiscal_account": "number", "amount": "number", "type": "text", "id_fiscal_stamp": "number"}} validationRules={validationRules["fiscal_record"] || {}} />;
}
