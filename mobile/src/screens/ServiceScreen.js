import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function ServiceScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="service" title="Service" pk="id_service" fields={["service_description", "average_time_cost", "id_brand"]} fieldTypes={{"service_description": "text", "average_time_cost": "number", "id_brand": "number"}} validationRules={validationRules["service"] || {}} />;
}
