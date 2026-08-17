import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function ProductSaleConfigScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="product_sale_config" title="ProductSaleConfig" pk="id_product_sale_config" fields={["id_product", "margin_percent", "manual_price", "id_inventory_status", "is_active"]} fieldTypes={{"id_product": "number", "margin_percent": "number", "manual_price": "number", "id_inventory_status": "number", "is_active": "text"}} validationRules={validationRules["product_sale_config"] || {}} />;
}
