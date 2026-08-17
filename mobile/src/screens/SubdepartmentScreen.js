import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function SubdepartmentScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="subdepartment" title="Subdepartment" pk="id_subdepartment" fields={["subdepartment_description", "id_department"]} fieldTypes={{"subdepartment_description": "text", "id_department": "number"}} validationRules={validationRules["subdepartment"] || {}} />;
}
