import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function ThemeScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="theme" title="Theme" pk="id_theme" fields={["tenant_id", "primary_color", "secondary_color", "background_color", "text_color", "highlight_color", "success_color", "error_color"]} fieldTypes={{"tenant_id": "number", "primary_color": "text", "secondary_color": "text", "background_color": "text", "text_color": "text", "highlight_color": "text", "success_color": "text", "error_color": "text"}} validationRules={validationRules["theme"] || {}} />;
}
