import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function PermissionScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="permission" title="Permission" pk="id_permission" fields={["authorized_by", "permission_description", "id_department", "id_subdepartment", "id_level"]} fieldTypes={{"authorized_by": "number", "permission_description": "text", "id_department": "number", "id_subdepartment": "number", "id_level": "number"}} validationRules={validationRules["permission"] || {}} />;
}
