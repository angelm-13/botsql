# TYAKXA Mobile React Native

App móvil generada desde CSVs con login MFA.

## Probar

```bash
npm install
npm run start
```

## MFA

Flujo esperado del backend:

1. `POST /auth/login` devuelve `{ token }` o `{ mfa_required: true, temp_token }`.
2. Si requiere MFA, `POST /auth/mfa/verify-login` con `{ code, temp_token }` devuelve `{ token }`.
3. La app guarda el token final en AsyncStorage.
