import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function UnitScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="unit" title="Unit" pk="id_unit" fields={["unit_code", "unit_name", "unit_category", "is_active", "symbol", "measurement_system"]} fieldTypes={{"unit_code": "text", "unit_name": "text", "unit_category": "text", "is_active": "text", "symbol": "text", "measurement_system": "text"}} validationRules={validationRules["unit"] || {}} />;
}
