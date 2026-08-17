import React, { useMemo, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { EntityApi } from '../api/client';
import { t } from '../i18n';
import { theme } from '../theme';
import { inputPropsForField, validateForm } from '../utils/validation';

export default function EntityFormScreen({ navigation, route }) {
  const { entity, pk, fields, fieldTypes = {}, validationRules = {}, item } = route.params;
  const isEditing = Boolean(item?.[pk]);
  const initial = useMemo(() => {
    const base = {};
    fields.forEach((field) => { base[field] = item?.[field] == null ? '' : String(item[field]); });
    return base;
  }, [fields, item]);
  const [form, setForm] = useState(initial);
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  async function save() {
    setError('');
    const validation = validateForm(form, validationRules);
    if (!validation.valid) {
      setFieldErrors(validation.errors);
      setError(t('common.validationFailed'));
      return;
    }
    setFieldErrors({});
    setSaving(true);
    try {
      if (isEditing) await EntityApi.update(entity, item[pk], form);
      else await EntityApi.create(entity, form);
      navigation.goBack();
    } catch (err) {
      const meta = err.payload?.meta;
      if (meta?.field) setFieldErrors((prev) => ({ ...prev, [meta.field]: err.message || 'errors.invalid_field' }));
      setError(err.message || 'SAVE_ERROR');
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    Alert.alert(t('common.delete'), entity, [
      { text: t('common.cancel'), style: 'cancel' },
      { text: t('common.delete'), style: 'destructive', onPress: async () => {
        await EntityApi.remove(entity, item[pk]);
        navigation.goBack();
      }},
    ]);
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      {fields.map((field) => (
        <View key={field} style={styles.group}>
          <Text style={styles.label}>{t(`fields.${entity}.${field}`)}</Text>
          <TextInput
            style={[styles.input, fieldErrors[field] ? styles.inputError : null]}
            value={form[field]}
            onChangeText={(value) => {
              setForm((prev) => ({ ...prev, [field]: value }));
              setFieldErrors((prev) => {
                if (!prev[field]) return prev;
                const next = { ...prev };
                delete next[field];
                return next;
              });
            }}
            {...inputPropsForField(field, validationRules[field], fieldTypes[field])}
          />
          {fieldErrors[field] ? <Text style={styles.fieldError}>{t(fieldErrors[field], fieldErrors[field])}</Text> : null}
        </View>
      ))}
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Pressable style={styles.save} onPress={save} disabled={saving}><Text style={styles.saveText}>{t('common.save')}</Text></Pressable>
      {isEditing ? <Pressable style={styles.delete} onPress={remove}><Text style={styles.deleteText}>{t('common.delete')}</Text></Pressable> : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { padding: 18, gap: 14 },
  group: { gap: 6 },
  label: { color: theme.colors.ink, fontWeight: '800' },
  input: { backgroundColor: '#fff', borderWidth: 1, borderColor: theme.colors.border, borderRadius: 16, padding: 14, fontSize: 16 },
  inputError: { borderColor: theme.colors.danger, backgroundColor: '#fff7f7' },
  fieldError: { color: theme.colors.danger, fontWeight: '800', fontSize: 12 },
  error: { color: theme.colors.danger, fontWeight: '800' },
  save: { backgroundColor: theme.colors.primary, borderRadius: 16, padding: 16, alignItems: 'center', marginTop: 8 },
  saveText: { color: '#fff', fontWeight: '900', fontSize: 16 },
  delete: { borderWidth: 1, borderColor: theme.colors.danger, borderRadius: 16, padding: 16, alignItems: 'center' },
  deleteText: { color: theme.colors.danger, fontWeight: '900' },
});
