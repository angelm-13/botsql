import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function NmIncidentProductScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="nm_incident_product" title="NmIncidentProduct" pk="id_nm_incident_product" fields={["id_incident", "id_product", "note", "quantity", "close_date"]} fieldTypes={{"id_incident": "number", "id_product": "number", "note": "text", "quantity": "number", "close_date": "text"}} validationRules={validationRules["nm_incident_product"] || {}} />;
}
