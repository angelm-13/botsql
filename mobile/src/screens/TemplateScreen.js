import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function TemplateScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="template" title="Template" pk="id_template" fields={["template_description"]} fieldTypes={{"template_description": "text"}} validationRules={validationRules["template"] || {}} />;
}
