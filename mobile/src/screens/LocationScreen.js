import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function LocationScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="location" title="Location" pk="id_location" fields={["id_location_type", "location_description", "id_location_reference"]} fieldTypes={{"id_location_type": "number", "location_description": "text", "id_location_reference": "number"}} validationRules={validationRules["location"] || {}} />;
}
