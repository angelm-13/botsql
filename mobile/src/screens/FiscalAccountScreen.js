import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function FiscalAccountScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="fiscal_account" title="FiscalAccount" pk="id_fiscal_account" fields={["fiscal_account_description", "balance", "id_fiscal_account_reference"]} fieldTypes={{"fiscal_account_description": "text", "balance": "number", "id_fiscal_account_reference": "number"}} validationRules={validationRules["fiscal_account"] || {}} />;
}
