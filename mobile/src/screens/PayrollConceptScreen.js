import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function PayrollConceptScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="payroll_concept" title="PayrollConcept" pk="id_payroll_concept" fields={["payroll_code", "payroll_concept_description", "type", "is_taxable", "is_imss"]} fieldTypes={{"payroll_code": "text", "payroll_concept_description": "text", "type": "text", "is_taxable": "text", "is_imss": "text"}} validationRules={validationRules["payroll_concept"] || {}} />;
}
