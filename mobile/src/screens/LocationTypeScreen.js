import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function LocationTypeScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="location_type" title="LocationType" pk="id_location_type" fields={["location_type_description"]} fieldTypes={{"location_type_description": "text"}} validationRules={validationRules["location_type"] || {}} />;
}
