import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function NmFieldPermissionScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="nm_field_permission" title="NmFieldPermission" pk="id_nm_field_permission" fields={["id_field", "id_permission", "control_type"]} fieldTypes={{"id_field": "number", "id_permission": "number", "control_type": "text"}} validationRules={validationRules["nm_field_permission"] || {}} />;
}
