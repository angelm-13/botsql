import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function ProyectScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="proyect" title="Proyect" pk="id_proyect" fields={["id_customer_supplier", "leader", "proyect_description", "title", "proyect_status"]} fieldTypes={{"id_customer_supplier": "number", "leader": "number", "proyect_description": "text", "title": "text", "proyect_status": "text"}} validationRules={validationRules["proyect"] || {}} />;
}
