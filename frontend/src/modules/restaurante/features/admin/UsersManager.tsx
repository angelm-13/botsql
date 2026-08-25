import { useEffect, useState } from 'react';
import { Check, Settings, Trash2, UserMinus, UserPlus } from 'lucide-react';
import { api } from '../../services/api';
import { useToast } from '../../contexts/ToastContext';
import { useConfirmDialog } from '../../contexts/ConfirmContext';
import { DemoLockedNote } from '../../components/shared/DemoLockedNote';
import { staffRoleLabel } from '../../utils/format';
import type { Translations } from '../../i18n/translations';
import type { Role, StaffMember, DemoStatus } from '../../types/api';

const STAFF_ROLES: Role[] = ['mesero', 'cajero', 'cocina', 'admin'];

interface EditStaffForm {
  username: string
  password: string
  role: Role
  name: string
  nickname: string
}

function EditStaffRow({ t, user, onSaved, onCancel }: { t: Translations; user: StaffMember; onSaved: () => void; onCancel: () => void }) {
  const [form, setForm] = useState<EditStaffForm>({
    username: user.username, password: '', role: user.role,
    name: user.waiter ? user.waiter.name : '', nickname: user.waiter ? user.waiter.nickname : '',
  });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  async function save() {
    setError('');
    setSaving(true);
    try {
      const payload: Record<string, unknown> = { username: form.username, role: form.role };
      if (form.password) payload.password = form.password;
      if (form.role === 'mesero') { payload.name = form.name; payload.nickname = form.nickname; }
      await api.updateStaff(user.id, payload);
      onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return <tr>
    <td><input value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} /></td>
    <td>
      <select value={form.role} onChange={e => setForm({ ...form, role: e.target.value as Role })}>
        {STAFF_ROLES.map(r => <option key={r} value={r}>{staffRoleLabel(r, t)}</option>)}
      </select>
    </td>
    <td>
      {form.role === 'mesero' ? <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <input placeholder={t.fullName} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
        <input placeholder={t.nickname} value={form.nickname} onChange={e => setForm({ ...form, nickname: e.target.value })} />
      </div> : '-'}
    </td>
    <td>
      <input type="password" placeholder={t.newPasswordOptional} value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} />
      {error && <div className="error" style={{ fontSize: 11 }}>{error}</div>}
    </td>
    <td style={{ display: 'flex', gap: 6 }}>
      <button className="primary" disabled={saving} onClick={save}><Check size={14} /></button>
      <button onClick={onCancel}>&times;</button>
    </td>
  </tr>;
}

export function UsersManager({ t }: { t: Translations }) {
  const toast = useToast();
  const confirmDialog = useConfirmDialog();
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [demoStatus, setDemoStatus] = useState<DemoStatus | null>(null);
  const [form, setForm] = useState<EditStaffForm>({ username: '', password: '', role: 'mesero', name: '', nickname: '' });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  async function load() {
    const [d, status] = await Promise.all([api.staff(), api.demoStatus()]);
    setStaff(d.items || []);
    setDemoStatus(status);
  }
  useEffect(() => { load().catch(console.error); }, []);
  const atStaffCap = !!(demoStatus?.enabled && demoStatus.staff_count >= demoStatus.max_staff);

  async function addStaff() {
    setError('');
    setSaving(true);
    try {
      await api.createStaff(form as unknown as Record<string, unknown>);
      setForm({ username: '', password: '', role: 'mesero', name: '', nickname: '' });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(u: StaffMember) {
    if (u.is_active && !await confirmDialog(t.confirmDeactivateUser)) return;
    try {
      if (u.is_active) await api.deactivateStaff(u.id); else await api.activateStaff(u.id);
      load().catch(console.error);
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  async function deleteStaff(u: StaffMember) {
    if (!await confirmDialog(t.confirmDeleteStaff)) return;
    try {
      await api.deleteStaff(u.id);
      load().catch(console.error);
    } catch (e) {
      // Si tiene historial (has_history), el backend ya manda un mensaje
      // claro sugiriendo desactivar en su lugar -- se muestra tal cual.
      toast.error((e as Error).message);
    }
  }

  return <section>
    <h3>{t.staffList}</h3>
    <table className="report-table">
      <thead><tr><th>{t.username}</th><th>{t.role}</th><th>{t.fullName}</th><th>{t.status}</th><th></th></tr></thead>
      <tbody>{staff.map(u => editingId === u.id
        ? <EditStaffRow key={u.id} t={t} user={u} onCancel={() => setEditingId(null)} onSaved={() => { setEditingId(null); load().catch(console.error); }} />
        : <tr key={u.id} style={{ opacity: u.is_active ? 1 : .5 }}>
          <td>{u.username}</td>
          <td>{staffRoleLabel(u.role, t)}</td>
          <td>{u.waiter ? `${u.waiter.name} (${u.waiter.nickname})` : '-'}</td>
          <td>{u.is_active ? t.active : t.inactive}</td>
          <td style={{ display: 'flex', gap: 6 }}>
            <button onClick={() => setEditingId(u.id)}><Settings size={14} /> {t.editUser}</button>
            <button onClick={() => toggleActive(u)}>{u.is_active ? <><UserMinus size={14} /> {t.deactivateUser}</> : <><UserPlus size={14} /> {t.activateUser}</>}</button>
            <button className="ghost dish-edit-delete" onClick={() => deleteStaff(u)}><Trash2 size={14} /> {t.deleteStaff}</button>
          </td>
        </tr>)}</tbody>
    </table>

    <h3 style={{ marginTop: 30 }}>{t.addStaff}</h3>
    {atStaffCap && <DemoLockedNote text={t.demoStaffLimitReached} />}
    {!atStaffCap && <>
      <div className="form-row">
        <div className="field"><label>{t.username}</label><input value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} /></div>
        <div className="field"><label>{t.password}</label><input type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} /></div>
        <div className="field"><label>{t.role}</label>
          <select value={form.role} onChange={e => setForm({ ...form, role: e.target.value as Role })}>
            {STAFF_ROLES.map(r => <option key={r} value={r}>{staffRoleLabel(r, t)}</option>)}
          </select>
        </div>
        {form.role === 'mesero' && <>
          <div className="field"><label>{t.fullName}</label><input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
          <div className="field"><label>{t.nickname}</label><input value={form.nickname} onChange={e => setForm({ ...form, nickname: e.target.value })} /></div>
        </>}
      </div>
      {form.role === 'mesero' && <p className="empty-hint">{t.staffWaiterHint}</p>}
      {error && <div className="error">{error}</div>}
      <button className="primary" disabled={saving} onClick={addStaff}><UserPlus size={16} /> {t.addStaff}</button>
    </>}
  </section>;
}
