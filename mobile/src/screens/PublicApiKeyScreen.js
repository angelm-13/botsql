import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function PublicApiKeyScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="public_api_key" title="PublicApiKey" pk="id_public_api_key" fields={["label", "key_hash", "key_prefix", "allowed_domains", "rate_limit_per_min", "is_active", "last_used_at"]} fieldTypes={{"label": "text", "key_hash": "text", "key_prefix": "text", "allowed_domains": "text", "rate_limit_per_min": "number", "is_active": "text", "last_used_at": "text"}} validationRules={validationRules["public_api_key"] || {}} />;
}
