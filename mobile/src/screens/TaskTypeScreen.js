import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function TaskTypeScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="task_type" title="TaskType" pk="id_task_type" fields={["task_type_description", "task_type_scope", "task_type_limit"]} fieldTypes={{"task_type_description": "text", "task_type_scope": "text", "task_type_limit": "text"}} validationRules={validationRules["task_type"] || {}} />;
}
