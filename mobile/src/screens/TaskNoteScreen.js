import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function TaskNoteScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="task_note" title="TaskNote" pk="id_task_note" fields={["date", "id_task", "task_note_description"]} fieldTypes={{"date": "text", "id_task": "number", "task_note_description": "text"}} validationRules={validationRules["task_note"] || {}} />;
}
