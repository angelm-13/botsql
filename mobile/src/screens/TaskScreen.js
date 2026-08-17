import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function TaskScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="task" title="Task" pk="id_task" fields={["task_code", "start_date", "duration", "type", "owner", "analyst", "dependency", "leader", "validation", "task_description", "estimated_effort", "task_status", "fase", "priority", "title", "id_proyect"]} fieldTypes={{"task_code": "text", "start_date": "text", "duration": "number", "type": "text", "owner": "number", "analyst": "number", "dependency": "number", "leader": "number", "validation": "number", "task_description": "text", "estimated_effort": "text", "task_status": "text", "fase": "text", "priority": "text", "title": "text", "id_proyect": "number"}} validationRules={validationRules["task"] || {}} />;
}
