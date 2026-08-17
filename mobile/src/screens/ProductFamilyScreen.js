import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function ProductFamilyScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="product_family" title="ProductFamily" pk="id_product_family" fields={["product_family_description", "type"]} fieldTypes={{"product_family_description": "text", "type": "text"}} validationRules={validationRules["product_family"] || {}} />;
}
