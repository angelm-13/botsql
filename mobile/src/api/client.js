import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';

const fallbackUrl = Constants.expoConfig?.extra?.apiUrl || `http://localhost:${process.env.EXPO_PUBLIC_BACKEND_PORT || 5001}`;
export const API_URL = process.env.EXPO_PUBLIC_API_URL || fallbackUrl;

async function authHeaders() {
  const token = await AsyncStorage.getItem('tyakxa_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiRequest(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(await authHeaders()),
    ...(options.headers || {}),
  };

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const error = new Error(data?.error_key || data?.message || `HTTP_${response.status}`);
    error.status = response.status;
    error.payload = data;
    throw error;
  }
  return data;
}

export const AuthApi = {
  login: (username, password) => apiRequest('/auth/login', {
    method: 'POST', body: JSON.stringify({ username, password }),
  }),
  verifyMfaLogin: (tempToken, code) => apiRequest('/auth/mfa/verify-login', {
    method: 'POST', body: JSON.stringify({ temp_token: tempToken, code }),
  }),
  setupMfa: () => apiRequest('/auth/mfa/setup', { method: 'POST' }),
  enableMfa: (code) => apiRequest('/auth/mfa/enable', { method: 'POST', body: JSON.stringify({ code }) }),
  disableMfa: (code) => apiRequest('/auth/mfa/disable', { method: 'POST', body: JSON.stringify({ code }) }),
};

export const EntityApi = {
  list: (entity, params = {}) => {
    const qs = new URLSearchParams({ page: String(params.page || 1), per_page: String(params.perPage || 20) });
    if (params.search) qs.set('q', params.search);
    return apiRequest(`/${entity}/?${qs.toString()}`);
  },
  create: (entity, payload) => apiRequest(`/${entity}/`, { method: 'POST', body: JSON.stringify(payload) }),
  update: (entity, id, payload) => apiRequest(`/${entity}/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  remove: (entity, id) => apiRequest(`/${entity}/${id}`, { method: 'DELETE' }),
};
