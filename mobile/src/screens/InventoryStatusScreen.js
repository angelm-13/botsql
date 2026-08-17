import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function InventoryStatusScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="inventory_status" title="InventoryStatus" pk="id_inventory_status" fields={["inventory_status_code", "inventory_status_description", "color", "entity_scope", "flow_scope", "id_department", "id_subdepartment", "id_minimum_level", "is_active", "is_terminal", "visible_to_other_departments", "sort_order"]} fieldTypes={{"inventory_status_code": "text", "inventory_status_description": "text", "color": "text", "entity_scope": "text", "flow_scope": "text", "id_department": "number", "id_subdepartment": "number", "id_minimum_level": "number", "is_active": "text", "is_terminal": "text", "visible_to_other_departments": "text", "sort_order": "number"}} validationRules={validationRules["inventory_status"] || {}} />;
}
