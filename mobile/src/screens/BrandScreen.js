import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function BrandScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="brand" title="Brand" pk="id_brand" fields={["brand_description"]} fieldTypes={{"brand_description": "text"}} validationRules={validationRules["brand"] || {}} />;
}
