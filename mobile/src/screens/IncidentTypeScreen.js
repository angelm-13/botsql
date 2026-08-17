import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function IncidentTypeScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="incident_type" title="IncidentType" pk="id_incident_type" fields={["incident_type_description"]} fieldTypes={{"incident_type_description": "text"}} validationRules={validationRules["incident_type"] || {}} />;
}
