import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function FiscalStampScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="fiscal_stamp" title="FiscalStamp" pk="id_fiscal_stamp" fields={["concept", "reviewed_by", "authorized_by", "auxiliar", "num_policy"]} fieldTypes={{"concept": "text", "reviewed_by": "number", "authorized_by": "number", "auxiliar": "text", "num_policy": "text"}} validationRules={validationRules["fiscal_stamp"] || {}} />;
}
