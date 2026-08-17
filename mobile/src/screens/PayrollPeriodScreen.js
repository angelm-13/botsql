import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function PayrollPeriodScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="payroll_period" title="PayrollPeriod" pk="id_payroll_period" fields={["period_start", "period_end", "payment_date", "id_status"]} fieldTypes={{"period_start": "text", "period_end": "text", "payment_date": "text", "id_status": "number"}} validationRules={validationRules["payroll_period"] || {}} />;
}
