import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function NmTemplateTaskScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="nm_template_task" title="NmTemplateTask" pk="id_nm_template_task" fields={["id_task", "id_template"]} fieldTypes={{"id_task": "number", "id_template": "number"}} validationRules={validationRules["nm_template_task"] || {}} />;
}
