import React, { useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { useAuth } from '../auth/AuthContext';
import { t } from '../i18n';
import { theme } from '../theme';

export default function LoginScreen() {
  const { login, verifyMfa, mfaRequired } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit() {
    setError('');
    setLoading(true);
    try {
      if (mfaRequired) await verifyMfa(code.trim());
      else await login(username.trim(), password);
    } catch (err) {
      setError(err.message || 'AUTH_ERROR');
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.page}>
      <View style={styles.hero}>
        <Text style={styles.brand}>TYAKXA</Text>
        <Text style={styles.subtitle}>{t('common.secureAccess')}</Text>
      </View>
      <View style={styles.card}>
        <Text style={styles.title}>{mfaRequired ? t('common.verify') : t('common.login')}</Text>
        {!mfaRequired ? (
          <>
            <TextInput style={styles.input} placeholder={t('common.username')} autoCapitalize="none" value={username} onChangeText={setUsername} />
            <TextInput style={styles.input} placeholder={t('common.password')} secureTextEntry value={password} onChangeText={setPassword} />
          </>
        ) : (
          <>
            <Text style={styles.help}>{t('common.mfaHelp')}</Text>
            <TextInput style={styles.input} placeholder={t('common.mfaCode')} keyboardType="number-pad" maxLength={6} value={code} onChangeText={setCode} />
          </>
        )}
        {error ? <Text style={styles.error}>{error}</Text> : null}
        <Pressable style={styles.button} onPress={submit} disabled={loading}>
          {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>{mfaRequired ? t('common.verify') : t('common.login')}</Text>}
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: theme.colors.ink, justifyContent: 'center', padding: 24 },
  hero: { marginBottom: 28 },
  brand: { color: '#fff', fontSize: 42, fontWeight: '900', letterSpacing: 2 },
  subtitle: { color: '#cbd5e1', fontSize: 16, marginTop: 8 },
  card: { backgroundColor: theme.colors.card, borderRadius: 28, padding: 24, ...theme.shadow },
  title: { fontSize: 24, fontWeight: '800', color: theme.colors.ink, marginBottom: 18 },
  input: { borderWidth: 1, borderColor: theme.colors.border, borderRadius: 16, padding: 14, marginBottom: 12, fontSize: 16, backgroundColor: '#fff' },
  help: { color: theme.colors.muted, marginBottom: 12, lineHeight: 20 },
  error: { color: theme.colors.danger, marginBottom: 12, fontWeight: '700' },
  button: { backgroundColor: theme.colors.primary, borderRadius: 16, padding: 16, alignItems: 'center', marginTop: 4 },
  buttonText: { color: '#fff', fontWeight: '800', fontSize: 16 },
});
