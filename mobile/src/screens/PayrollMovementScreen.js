import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function PayrollMovementScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="payroll_movement" title="PayrollMovement" pk="id_payroll_movement" fields={["id_payroll_detail", "id_payroll_concept", "amount"]} fieldTypes={{"id_payroll_detail": "number", "id_payroll_concept": "number", "amount": "number"}} validationRules={validationRules["payroll_movement"] || {}} />;
}
