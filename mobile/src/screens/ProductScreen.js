import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function ProductScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="product" title="Product" pk="id_product" fields={["id_invoice", "id_location", "id_material", "gross_price", "color", "is_directly_related_to_product_service", "product_status", "path_imagen", "product_code", "note", "descripcion", "cantidad", "id_marca", "id_familia"]} fieldTypes={{"id_invoice": "number", "id_location": "number", "id_material": "number", "gross_price": "number", "color": "text", "is_directly_related_to_product_service": "text", "product_status": "text", "path_imagen": "text", "product_code": "text", "note": "text", "descripcion": "text", "cantidad": "number", "id_marca": "number", "id_familia": "number"}} validationRules={validationRules["product"] || {}} />;
}
