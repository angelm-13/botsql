import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { AuthApi } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null);
  const [tempToken, setTempToken] = useState(null);
  const [mfaRequired, setMfaRequired] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    AsyncStorage.getItem('tyakxa_token')
      .then((stored) => setToken(stored))
      .finally(() => setLoading(false));
  }, []);

  async function persistToken(nextToken) {
    await AsyncStorage.setItem('tyakxa_token', nextToken);
    setToken(nextToken);
    setTempToken(null);
    setMfaRequired(false);
  }

  async function login(username, password) {
    const result = await AuthApi.login(username, password);
    if (result?.mfa_required) {
      setTempToken(result.temp_token);
      setMfaRequired(true);
      return { mfaRequired: true };
    }
    if (result?.token) await persistToken(result.token);
    return { mfaRequired: false };
  }

  async function verifyMfa(code) {
    const result = await AuthApi.verifyMfaLogin(tempToken, code);
    if (result?.token) await persistToken(result.token);
    return result;
  }

  async function logout() {
    await AsyncStorage.removeItem('tyakxa_token');
    setToken(null);
    setTempToken(null);
    setMfaRequired(false);
  }

  const value = useMemo(() => ({ token, loading, login, verifyMfa, logout, mfaRequired }), [token, loading, mfaRequired]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth debe usarse dentro de AuthProvider');
  return value;
}
