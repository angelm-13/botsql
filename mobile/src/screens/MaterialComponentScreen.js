import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function MaterialComponentScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="material_component" title="MaterialComponent" pk="id_material_component" fields={["id_material", "id_component", "relation", "id_unit"]} fieldTypes={{"id_material": "number", "id_component": "number", "relation": "number", "id_unit": "number"}} validationRules={validationRules["material_component"] || {}} />;
}
