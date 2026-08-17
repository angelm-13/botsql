import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function StatusScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="status" title="Status" pk="id_status" fields={["status_description", "category", "is_terminal", "sort_order"]} fieldTypes={{"status_description": "text", "category": "text", "is_terminal": "text", "sort_order": "text"}} validationRules={validationRules["status"] || {}} />;
}
