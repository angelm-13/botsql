import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function IncidentScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="incident" title="Incident" pk="id_incident" fields={["incident_date", "id_incident_type", "note", "id_user", "incident_status", "close_date", "id_lider"]} fieldTypes={{"incident_date": "text", "id_incident_type": "number", "note": "text", "id_user": "number", "incident_status": "text", "close_date": "text", "id_lider": "number"}} validationRules={validationRules["incident"] || {}} />;
}
