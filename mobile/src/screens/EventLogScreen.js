import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function EventLogScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="event_log" title="EventLog" pk="id_event_log" fields={["table_name", "field_name", "action", "before_value", "after_value"]} fieldTypes={{"table_name": "text", "field_name": "text", "action": "text", "before_value": "text", "after_value": "text"}} validationRules={validationRules["event_log"] || {}} />;
}
