import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function BankAccountScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="bank_account" title="BankAccount" pk="id_bank_account" fields={["id_bank", "bank_account_description", "branch", "type", "ordinary_interest", "moratorium_interest", "anuality", "reimbursement"]} fieldTypes={{"id_bank": "number", "bank_account_description": "text", "branch": "text", "type": "text", "ordinary_interest": "number", "moratorium_interest": "number", "anuality": "number", "reimbursement": "number"}} validationRules={validationRules["bank_account"] || {}} />;
}
