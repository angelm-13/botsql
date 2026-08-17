import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function BankScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="bank" title="Bank" pk="id_bank" fields={["bank_name"]} fieldTypes={{"bank_name": "text"}} validationRules={validationRules["bank"] || {}} />;
}
