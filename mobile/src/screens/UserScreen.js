import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function UserScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="user" title="User" pk="id_user" fields={["date_born", "date_start", "email", "first_name", "id_permission", "full_name", "id_proyect", "last_name_father", "last_name_mother", "national_id", "password", "principal_phone", "secundary_phone", "ssn", "supervisor", "base_salary"]} fieldTypes={{"date_born": "text", "date_start": "text", "email": "email", "first_name": "text", "id_permission": "number", "full_name": "text", "id_proyect": "number", "last_name_father": "text", "last_name_mother": "text", "national_id": "text", "password": "password", "principal_phone": "phone", "secundary_phone": "phone", "ssn": "text", "supervisor": "number", "base_salary": "number"}} validationRules={validationRules["user"] || {}} />;
}
