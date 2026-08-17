import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function MovementScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="movement" title="Movement" pk="id_movement" fields={["id_fiscal_account", "date", "type", "amount", "currency", "type_exchange_rate"]} fieldTypes={{"id_fiscal_account": "number", "date": "text", "type": "text", "amount": "number", "currency": "text", "type_exchange_rate": "number"}} validationRules={validationRules["movement"] || {}} />;
}
