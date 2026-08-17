import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function IncidentDetailScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="incident_detail" title="IncidentDetail" pk="id_incident_detail" fields={["id_incident_type", "incident_detail_name", "incident_detail_description"]} fieldTypes={{"id_incident_type": "number", "incident_detail_name": "text", "incident_detail_description": "text"}} validationRules={validationRules["incident_detail"] || {}} />;
}
