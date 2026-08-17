import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function DepartmentScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="department" title="Department" pk="id_department" fields={["department_description"]} fieldTypes={{"department_description": "text"}} validationRules={validationRules["department"] || {}} />;
}
