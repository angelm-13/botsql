import { useState, type FormEvent } from 'react'
import { KeyRound } from 'lucide-react'
import { api } from '../../services/api'
import { Portal } from './Portal'
import type { Translations } from '../../i18n/translations'

/**
 * Cambio de la PROPIA contrasena, disponible para cualquier rol desde la
 * barra superior. Antes esto no existia: la unica forma de cambiar una
 * contrasena era pedirle al administrador que editara la cuenta, lo que
 * obliga a dictarle la contrasena nueva a otra persona.
 *
 * Pide la contrasena actual porque el backend la exige (ver
 * /auth/change-password): en un restaurante las tablets quedan con la
 * sesion abierta y desatendidas, y sin eso cualquiera podria dejar al
 * mesero fuera de su cuenta al pasar junto a una.
 */
export function ChangePasswordModal({ t, onClose }: { t: Translations; onClose: () => void }) {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError('')
    // La confirmacion se valida aqui y no en el backend a proposito: es un
    // error de dedo del usuario, no una regla de negocio -- avisarle sin
    // gastar una llamada (y sin gastar uno de los 5 intentos que permite el
    // freno anti fuerza-bruta del endpoint) es mejor experiencia.
    if (next !== confirm) { setError(t.passwordsDoNotMatch); return }
    setBusy(true)
    try {
      await api.changePassword(current, next)
      setDone(true)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return <Portal><div className="modal"><div className="ticket-panel" style={{ width: 'min(380px,95vw)' }}>
    <button className="close" onClick={onClose}>&times;</button>
    <h2><KeyRound size={18} style={{ marginRight: 6, verticalAlign: '-3px' }} />{t.changePassword}</h2>
    {done ? <>
      <p style={{ color: 'var(--green)' }}>{t.passwordChanged}</p>
      <p className="empty-hint">{t.passwordChangedHint}</p>
      <button className="primary big" onClick={onClose}>{t.close}</button>
    </> : <form onSubmit={submit}>
      <label>{t.currentPassword}
        <input type="password" value={current} onChange={e => setCurrent(e.target.value)} autoComplete="current-password" />
      </label>
      <label>{t.newPassword}
        <input type="password" value={next} onChange={e => setNext(e.target.value)} autoComplete="new-password" />
      </label>
      <label>{t.confirmNewPassword}
        <input type="password" value={confirm} onChange={e => setConfirm(e.target.value)} autoComplete="new-password" />
      </label>
      {error && <div className="error">{error}</div>}
      <button className="primary big" disabled={busy}>{busy ? t.processing : t.changePassword}</button>
    </form>}
  </div></div></Portal>
}
