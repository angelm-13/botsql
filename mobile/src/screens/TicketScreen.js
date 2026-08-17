import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function TicketScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="ticket" title="Ticket" pk="id_ticket" fields={["ticket_description", "ticket_status", "note"]} fieldTypes={{"ticket_description": "text", "ticket_status": "text", "note": "text"}} validationRules={validationRules["ticket"] || {}} />;
}
