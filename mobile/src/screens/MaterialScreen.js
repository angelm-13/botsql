import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function MaterialScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="material" title="Material" pk="id_material" fields={["material_description", "id_unit", "id_brand", "id_product_family"]} fieldTypes={{"material_description": "text", "id_unit": "number", "id_brand": "number", "id_product_family": "number"}} validationRules={validationRules["material"] || {}} />;
}
