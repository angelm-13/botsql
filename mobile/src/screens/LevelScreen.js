import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function LevelScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="level" title="Level" pk="id_level" fields={["level_description"]} fieldTypes={{"level_description": "text"}} validationRules={validationRules["level"] || {}} />;
}
