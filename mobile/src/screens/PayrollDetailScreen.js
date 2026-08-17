import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function PayrollDetailScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="payroll_detail" title="PayrollDetail" pk="id_payroll_detail" fields={["id_payroll_period", "id_user", "gross_salary", "total_earnings", "total_deductions", "net_pay"]} fieldTypes={{"id_payroll_period": "number", "id_user": "number", "gross_salary": "number", "total_earnings": "number", "total_deductions": "number", "net_pay": "number"}} validationRules={validationRules["payroll_detail"] || {}} />;
}
