import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function FieldScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="field" title="Field" pk="id_field" fields={["table_name", "field_name"]} fieldTypes={{"table_name": "text", "field_name": "text"}} validationRules={validationRules["field"] || {}} />;
}
