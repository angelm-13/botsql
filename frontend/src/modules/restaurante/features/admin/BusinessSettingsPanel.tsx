import { useEffect, useState } from 'react';
import { Check, Loader2, PlugZap } from 'lucide-react';
import { api } from '../../services/api';
import { useToast } from '../../contexts/ToastContext';
import { LoadingPanel } from '../../components/shared/LoadingPanel';
import { DemoLockedNote } from '../../components/shared/DemoLockedNote';
import type { Translations } from '../../i18n/translations';
import type { Company, PacConfig, DemoStatus } from '../../types/api';

/** Configuracion fiscal del restaurante (Company, singleton) y del
 * proveedor de timbrado (PacConfig, singleton) -- solo isAdmin. 'mock' es
 * el unico proveedor con integracion real conectada en este servidor; los
 * modos de Facturama existen en el selector para dejar la configuracion
 * lista, pero /pac-config/test avisa claro que todavia no estan conectados
 * (ver PacNotImplementedError en el backend) en vez de fingir que si timbran. */
export function BusinessSettingsPanel({ t }: { t: Translations }) {
  const toast = useToast();
  const [catalogs, setCatalogs] = useState<{ regimen_fiscal: Record<string, string>; [key: string]: unknown } | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [pacConfig, setPacConfig] = useState<PacConfig | null>(null);
  const [pacPassword, setPacPassword] = useState('');
  const [savingCompany, setSavingCompany] = useState(false);
  const [savingPac, setSavingPac] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [demoStatus, setDemoStatus] = useState<DemoStatus | null>(null);
  const demoLocksPac = !!demoStatus?.enabled;

  async function load() {
    const [cat, comp, pac, status] = await Promise.all([api.invoiceCatalogs(), api.company(), api.pacConfig(), api.demoStatus()]);
    setCatalogs(cat as { regimen_fiscal: Record<string, string> }); setCompany(comp); setPacConfig(pac); setDemoStatus(status);
  }
  useEffect(() => { load().catch(e => toast.error(e.message)); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function saveCompany() {
    setSavingCompany(true);
    try {
      const saved = await api.updateCompany(company!);
      setCompany(saved);
      toast.success(t.businessSaved);
    } catch (e) { toast.error((e as Error).message); } finally { setSavingCompany(false); }
  }

  async function savePac() {
    setSavingPac(true);
    try {
      const payload: Record<string, unknown> = { provider: pacConfig!.provider, facturama_user: pacConfig!.facturama_user };
      if (pacPassword) payload.facturama_password = pacPassword;
      const saved = await api.updatePacConfig(payload);
      setPacConfig(saved);
      setPacPassword('');
      setTestResult(null);
      toast.success(t.pacSaved);
    } catch (e) { toast.error((e as Error).message); } finally { setSavingPac(false); }
  }

  async function testConnection() {
    setTesting(true); setTestResult(null);
    try { setTestResult(await api.testPacConfig()); }
    catch (e) { toast.error((e as Error).message); }
    finally { setTesting(false); }
  }

  if (!catalogs || !company || !pacConfig) return <LoadingPanel />;
  const isMock = pacConfig.provider === 'mock';

  return <section>
    <h3>{t.myBusiness}</h3>
    {!company.rfc && <p className="empty-hint">{t.businessIncompleteHint}</p>}
    <div className="dish-edit-card">
      <div className="dish-edit-row">
        <label className="dish-edit-field dish-edit-field-wide"><span>{t.businessRazonSocial}</span><input value={company.razon_social || ''} onChange={e => setCompany({ ...company, razon_social: e.target.value })} /></label>
        <label className="dish-edit-field dish-edit-field-sm"><span>{t.businessRfc}</span><input value={company.rfc || ''} onChange={e => setCompany({ ...company, rfc: e.target.value.toUpperCase() })} /></label>
      </div>
      <div className="dish-edit-row">
        <label className="dish-edit-field"><span>{t.businessRegimenFiscal}</span>
          <select value={company.regimen_fiscal || ''} onChange={e => setCompany({ ...company, regimen_fiscal: e.target.value })}>
            <option value="">-</option>
            {Object.entries(catalogs.regimen_fiscal).map(([k, v]) => <option key={k} value={k}>{k} - {v}</option>)}
          </select>
        </label>
        <label className="dish-edit-field dish-edit-field-sm"><span>{t.businessCp}</span><input value={company.cp || ''} onChange={e => setCompany({ ...company, cp: e.target.value })} /></label>
        <label className="dish-edit-field dish-edit-field-sm"><span>{t.businessSerie}</span><input value={company.serie || ''} onChange={e => setCompany({ ...company, serie: e.target.value.toUpperCase() })} /></label>
      </div>
      <label className="dish-edit-field dish-edit-field-wide"><span>{t.businessDireccion}</span><input value={company.direccion || ''} onChange={e => setCompany({ ...company, direccion: e.target.value })} /></label>
      <button className="primary" disabled={savingCompany} onClick={saveCompany}>{savingCompany ? <Loader2 size={16} className="spin" /> : <Check size={16} />} {t.pacSave}</button>
    </div>

    <h3 style={{ marginTop: 24 }}>{t.invoicingTab}</h3>
    <div className="dish-edit-card">
      <div className="dish-edit-row">
        <label className="dish-edit-field"><span>{t.pacProviderLabel}</span>
          <select value={pacConfig.provider} onChange={e => { setPacConfig({ ...pacConfig, provider: e.target.value }); setTestResult(null); }}>
            <option value="mock">{t.pacMock}</option>
            <option value="facturama_sandbox" disabled={demoLocksPac}>{t.pacSandbox}</option>
            <option value="facturama_production" disabled={demoLocksPac}>{t.pacProd}</option>
          </select>
        </label>
      </div>
      {demoLocksPac && <DemoLockedNote text={t.demoLockedPac} />}
      {!isMock && <div className="dish-edit-row">
        <label className="dish-edit-field"><span>{t.pacUser}</span><input value={pacConfig.facturama_user || ''} onChange={e => setPacConfig({ ...pacConfig, facturama_user: e.target.value })} /></label>
        <label className="dish-edit-field"><span>{t.pacPassword}</span><input type="password" placeholder={pacConfig.has_password ? t.pacPasswordSaved : ''} value={pacPassword} onChange={e => setPacPassword(e.target.value)} /></label>
      </div>}
      <div className="dish-edit-row" style={{ alignItems: 'center' }}>
        <button className="primary" disabled={savingPac} onClick={savePac}>{savingPac ? <Loader2 size={16} className="spin" /> : <Check size={16} />} {t.pacSave}</button>
        <button className="ghost" disabled={testing} onClick={testConnection}><PlugZap size={16} /> {testing ? t.pacTesting : t.pacTestConnection}</button>
      </div>
      {testResult && <p style={{ color: testResult.ok ? 'var(--green)' : 'var(--danger)', marginTop: 8 }}>{testResult.message}</p>}
    </div>
  </section>;
}
