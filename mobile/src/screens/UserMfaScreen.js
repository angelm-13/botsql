import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function UserMfaScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="user_mfa" title="UserMfa" pk="id_user_mfa" fields={["id_user", "secret", "secret_iv", "enabled", "failed_attempts", "locked_until", "last_used_at", "backup_codes", "created_at", "updated_at"]} fieldTypes={{"id_user": "number", "secret": "text", "secret_iv": "text", "enabled": "text", "failed_attempts": "number", "locked_until": "text", "last_used_at": "text", "backup_codes": "text", "created_at": "text", "updated_at": "text"}} validationRules={validationRules["user_mfa"] || {}} />;
}
