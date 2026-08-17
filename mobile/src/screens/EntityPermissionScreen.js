import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function EntityPermissionScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="entity_permission" title="EntityPermission" pk="id_entity_permission" fields={["id_permission", "entity_name", "control_type"]} fieldTypes={{"id_permission": "number", "entity_name": "text", "control_type": "text"}} validationRules={validationRules["entity_permission"] || {}} />;
}
