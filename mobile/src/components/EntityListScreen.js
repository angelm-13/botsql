import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, RefreshControl, StyleSheet, Text, TextInput, View } from 'react-native';
import { EntityApi } from '../api/client';
import { t } from '../i18n';
import { theme } from '../theme';

export default function EntityListScreen({ navigation, entity, title, pk, fields, fieldTypes, validationRules }) {
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setError('');
    try {
      const result = await EntityApi.list(entity, { search, page: 1, perPage: 50 });
      setItems(Array.isArray(result) ? result : (result?.items || []));
    } catch (err) {
      setError(err.message || 'LOAD_ERROR');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [entity, search]);

  useEffect(() => { load(); }, [load]);

  const filtered = items.filter((item) => JSON.stringify(item).toLowerCase().includes(search.toLowerCase()));

  return (
    <View style={styles.page}>
      <View style={styles.toolbar}>
        <TextInput style={styles.search} placeholder={t('common.search')} value={search} onChangeText={setSearch} />
        <Pressable style={styles.newButton} onPress={() => navigation.navigate(`${title}Form`, { entity, pk, fields, fieldTypes, validationRules })}>
          <Text style={styles.newText}>＋</Text>
        </Pressable>
      </View>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {loading ? <ActivityIndicator /> : (
        <FlatList
          data={filtered}
          keyExtractor={(item, index) => String(item?.[pk] || index)}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />}
          ListEmptyComponent={<Text style={styles.empty}>{t('common.empty')}</Text>}
          renderItem={({ item }) => (
            <Pressable style={styles.card} onPress={() => navigation.navigate(`${title}Form`, { entity, pk, fields, fieldTypes, validationRules, item })}>
              <Text style={styles.cardTitle}>{String(item?.[fields[0]] || item?.[pk] || title)}</Text>
              {fields.slice(1, 4).map((field) => <Text key={field} style={styles.meta}>{t(`fields.${entity}.${field}`)}: {String(item?.[field] ?? '')}</Text>)}
            </Pressable>
          )}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, padding: 16, gap: 12 },
  toolbar: { flexDirection: 'row', gap: 10, alignItems: 'center' },
  search: { flex: 1, backgroundColor: '#fff', borderWidth: 1, borderColor: theme.colors.border, borderRadius: 16, padding: 12 },
  newButton: { backgroundColor: theme.colors.primary, width: 48, height: 48, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  newText: { color: '#fff', fontSize: 28, fontWeight: '900' },
  error: { color: theme.colors.danger, fontWeight: '800' },
  empty: { color: theme.colors.muted, textAlign: 'center', marginTop: 40 },
  card: { backgroundColor: '#fff', borderRadius: 18, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: theme.colors.border, ...theme.shadow },
  cardTitle: { color: theme.colors.ink, fontSize: 17, fontWeight: '900', marginBottom: 8 },
  meta: { color: theme.colors.muted, marginTop: 3 },
});
