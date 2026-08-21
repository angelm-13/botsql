import { Fragment, useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Eye, Link2, Plus, RefreshCw, Trash2, Upload } from "lucide-react";
import {
  createBankAccount,
  deleteBankStatement,
  getAllBank,
  getAllBankAccount,
  getAllInvoice,
  getAllProyect,
  getBankStatementMovements,
  getBankStatements,
  importBankStatement,
  matchBankStatementMovement,
  previewBankStatement,
} from "../api";

function money(value) {
  return Number(value || 0).toLocaleString("es-MX", { style: "currency", currency: "MXN" });
}

function dateLabel(value) {
  if (!value) return "—";
  const date = new Date(`${String(value).slice(0, 10)}T12:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("es-MX");
}

function messageFrom(error) {
  return error?.payload?.meta?.reason || error?.payload?.message || error?.message || "No fue posible completar la operación.";
}

export default function BankStatementsPanel({ canManage, canCreateAccount }) {
  const [accounts, setAccounts] = useState([]);
  const [banks, setBanks] = useState([]);
  const [projects, setProjects] = useState([]);
  const [statements, setStatements] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [accountId, setAccountId] = useState("");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [movements, setMovements] = useState([]);
  const [movementType, setMovementType] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [creatingAccount, setCreatingAccount] = useState(false);
  const [newAccount, setNewAccount] = useState({ id_bank: "", bank_account_description: "", id_proyect: "", branch: "", type: "checking" });

  const selectedStatement = statements.find((item) => item.id_bank_statement === selectedId) || null;
  const matchingInvoices = useMemo(() => {
    if (!selectedStatement) return invoices;
    return invoices.filter((invoice) => String(invoice.id_proyect || "") === String(selectedStatement.id_proyect || ""));
  }, [invoices, selectedStatement]);

  async function loadWorkspace() {
    setLoading(true);
    setError("");
    try {
      const [accountResponse, statementResponse, invoiceResponse, bankResponse, projectResponse] = await Promise.all([
        getAllBankAccount({ page: 1, per_page: 500 }),
        getBankStatements(),
        getAllInvoice({ page: 1, per_page: 500 }),
        getAllBank({ page: 1, per_page: 500 }),
        getAllProyect({ page: 1, per_page: 500 }),
      ]);
      const accountRows = accountResponse.items || accountResponse.data || accountResponse || [];
      setAccounts(accountRows);
      setStatements(statementResponse.items || []);
      setInvoices(invoiceResponse.items || invoiceResponse.data || invoiceResponse || []);
      setBanks(bankResponse.items || bankResponse.data || bankResponse || []);
      setProjects(projectResponse.items || projectResponse.data || projectResponse || []);
      if (!accountId && accountRows.length) setAccountId(String(accountRows[0].id_bank_account));
    } catch (requestError) {
      setError(messageFrom(requestError));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadWorkspace(); }, []);

  async function loadMovements(statementId, type = movementType) {
    setError("");
    try {
      const response = await getBankStatementMovements(statementId, { page: 1, per_page: 100, type });
      setMovements(response.items || []);
    } catch (requestError) {
      setError(messageFrom(requestError));
    }
  }

  async function toggleStatement(statementId) {
    if (selectedId === statementId) {
      setSelectedId(null);
      setMovements([]);
      return;
    }
    setSelectedId(statementId);
    await loadMovements(statementId);
  }

  function uploadBody() {
    const body = new FormData();
    body.append("id_bank_account", accountId);
    body.append("file", file);
    return body;
  }

  async function handlePreview() {
    if (!accountId || !file) return setError("Selecciona una cuenta y un archivo PDF o CSV.");
    setLoading(true); setError(""); setNotice("");
    try {
      setPreview(await previewBankStatement(uploadBody()));
    } catch (requestError) {
      setError(messageFrom(requestError));
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateAccount(event) {
    event.preventDefault();
    setError("");
    try {
      const created = await createBankAccount(newAccount);
      setCreatingAccount(false);
      setNewAccount({ id_bank: "", bank_account_description: "", id_proyect: "", branch: "", type: "checking" });
      await loadWorkspace();
      setAccountId(String(created.id_bank_account));
      setNotice("Cuenta bancaria creada.");
    } catch (requestError) {
      setError(messageFrom(requestError));
    }
  }

  async function handleImport() {
    if (!accountId || !file) return setError("Selecciona una cuenta y un archivo PDF o CSV.");
    setLoading(true); setError("");
    try {
      const response = await importBankStatement(uploadBody());
      setNotice(`Estado de cuenta importado con ${response.movement_count || 0} movimientos.`);
      setPreview(null); setFile(null);
      await loadWorkspace();
    } catch (requestError) {
      setError(messageFrom(requestError));
    } finally {
      setLoading(false);
    }
  }

  async function handleMatch(movement, invoiceId, force = false) {
    try {
      await matchBankStatementMovement(movement.id_bank_statement_movement, { id_invoice: invoiceId || null, force });
      await loadMovements(selectedId);
    } catch (requestError) {
      if (requestError.status === 409 && requestError.payload?.meta?.force_allowed && window.confirm("El importe no coincide con la factura. ¿Vincular de todas formas?")) {
        await handleMatch(movement, invoiceId, true);
        return;
      }
      setError(messageFrom(requestError));
    }
  }

  async function handleDelete(statementId) {
    if (!window.confirm("¿Eliminar este estado de cuenta y todos sus movimientos?")) return;
    try {
      await deleteBankStatement(statementId);
      if (selectedId === statementId) { setSelectedId(null); setMovements([]); }
      await loadWorkspace();
    } catch (requestError) {
      setError(messageFrom(requestError));
    }
  }

  function suggestedInvoice(movement) {
    const amount = Number(movement.debit || movement.credit || 0);
    return matchingInvoices.find((invoice) => Math.abs(Number(invoice.total || 0) - amount) <= 0.05);
  }

  return (
    <section className="bank-statements-workspace">
      <div className="bank-statements-heading">
        <div><p className="eyebrow">Conciliación bancaria</p><h3>Estados de cuenta</h3><p className="muted">Importa PDF de BBVA o CSV, valida saldos y vincula movimientos con facturas.</p></div>
        <button type="button" className="button ghost" onClick={loadWorkspace} disabled={loading}><RefreshCw size={16} />Actualizar</button>
      </div>

      {error && <div className="alert error">{error}</div>}
      {notice && <div className="alert success">{notice}</div>}

      {canManage && <div className="bank-statement-importer">
        <label className="field"><span>Cuenta bancaria</span><select required value={accountId} onChange={(event) => { setAccountId(event.target.value); setPreview(null); }}><option value="">Selecciona una cuenta</option>{accounts.map((account) => <option key={account.id_bank_account} value={account.id_bank_account}>{account.bank_account_description} · {account.branch || "Sin sucursal"}</option>)}</select>{canCreateAccount && <button type="button" className="text-button" onClick={() => setCreatingAccount((value) => !value)}><Plus size={14} />Nueva cuenta</button>}</label>
        <label className="field"><span>Estado de cuenta</span><input type="file" accept=".pdf,.csv,application/pdf,text/csv" onChange={(event) => { setFile(event.target.files?.[0] || null); setPreview(null); }} /></label>
        <div className="bank-import-actions"><button type="button" className="button" disabled={loading || !file || !accountId} onClick={handlePreview}><Eye size={16} />Previsualizar</button><button type="button" className="button primary" disabled={loading || !file || !accountId || preview?.already_imported} onClick={handleImport}><Upload size={16} />Importar</button></div>
      </div>}

      {canCreateAccount && creatingAccount && <form className="bank-account-inline" onSubmit={handleCreateAccount}>
        <label className="field"><span>Banco</span><select required value={newAccount.id_bank} onChange={(event) => setNewAccount((current) => ({ ...current, id_bank: event.target.value }))}><option value="">Selecciona</option>{banks.map((bank) => <option key={bank.id_bank} value={bank.id_bank}>{bank.bank_name}</option>)}</select></label>
        <label className="field"><span>Descripción</span><input required maxLength="200" value={newAccount.bank_account_description} onChange={(event) => setNewAccount((current) => ({ ...current, bank_account_description: event.target.value }))} /></label>
        <label className="field"><span>Proyecto</span><select required value={newAccount.id_proyect} onChange={(event) => setNewAccount((current) => ({ ...current, id_proyect: event.target.value }))}><option value="">Selecciona</option>{projects.map((project) => <option key={project.id_proyect} value={project.id_proyect}>{project.proyect_description || project.title || `Proyecto #${project.id_proyect}`}</option>)}</select></label>
        <label className="field"><span>Sucursal</span><input maxLength="30" value={newAccount.branch} onChange={(event) => setNewAccount((current) => ({ ...current, branch: event.target.value }))} /></label>
        <button type="submit" className="button primary">Guardar cuenta</button>
      </form>}

      {preview && <div className="bank-statement-preview">
        <div className="bank-statement-metrics"><span><small>Periodo</small><strong>{dateLabel(preview.statement.period_start)} – {dateLabel(preview.statement.period_end)}</strong></span><span><small>Cargos</small><strong>{money(preview.statement.total_debits)}</strong></span><span><small>Abonos</small><strong>{money(preview.statement.total_credits)}</strong></span><span><small>Movimientos</small><strong>{preview.movement_count}</strong></span><span><small>Validación</small><strong className={preview.reconciliation.ok ? "text-success" : "text-warning"}>{preview.reconciliation.ok ? "Conciliado" : "Revisar"}</strong></span></div>
        {preview.already_imported && <div className="alert error">Este archivo ya fue importado.</div>}
        {preview.reconciliation.warnings?.map((warning) => <p className="field-error" key={warning}>{warning}</p>)}
      </div>}

      <div className="bank-statements-list">
        <div className="bank-list-title"><strong>Historial importado</strong><span>{statements.length} estados</span></div>
        {!statements.length ? <div className="empty"><strong>Sin estados de cuenta</strong><p>Selecciona una cuenta y carga el primer archivo.</p></div> : <div className="table-wrap"><table><thead><tr><th></th><th>Archivo</th><th>Periodo</th><th>Cargos</th><th>Abonos</th><th>Saldo final</th><th>Estado</th><th>Movimientos</th><th></th></tr></thead><tbody>{statements.map((statement) => <Fragment key={statement.id_bank_statement}>
          <tr><td><button type="button" className="icon-button" title="Ver movimientos" onClick={() => toggleStatement(statement.id_bank_statement)}>{selectedId === statement.id_bank_statement ? <ChevronDown size={17} /> : <ChevronRight size={17} />}</button></td><td><strong>{statement.original_filename}</strong><small className="cell-value">{statement.parser_name || "—"}</small></td><td>{dateLabel(statement.period_start)} – {dateLabel(statement.period_end)}</td><td>{money(statement.total_debits)}</td><td>{money(statement.total_credits)}</td><td>{money(statement.ending_balance)}</td><td><span className={`bank-status ${statement.status}`}>{statement.status === "completed" ? "Conciliado" : "Revisar"}</span></td><td>{statement.movement_count}</td><td>{canManage && <button type="button" className="icon-button danger" title="Eliminar estado" onClick={() => handleDelete(statement.id_bank_statement)}><Trash2 size={16} /></button>}</td></tr>
          {selectedId === statement.id_bank_statement && <tr key={`${statement.id_bank_statement}-detail`} className="bank-movements-row"><td colSpan="9"><div className="bank-movements-toolbar"><strong>Movimientos</strong><select value={movementType} onChange={(event) => { setMovementType(event.target.value); loadMovements(statement.id_bank_statement, event.target.value); }}><option value="">Todos</option><option value="debit">Cargos</option><option value="credit">Abonos</option></select></div><div className="table-wrap"><table className="bank-movements-table"><thead><tr><th>Fecha</th><th>Descripción</th><th>Referencia</th><th>Cargo</th><th>Abono</th><th>Saldo</th><th>Conciliación</th></tr></thead><tbody>{movements.map((movement) => { const suggestion = suggestedInvoice(movement); return <tr key={movement.id_bank_statement_movement}><td>{dateLabel(movement.movement_date)}</td><td><strong>{movement.description}</strong><small className="cell-value">{movement.code || ""}</small></td><td>{movement.reference || "—"}</td><td>{movement.debit ? money(movement.debit) : "—"}</td><td>{movement.credit ? money(movement.credit) : "—"}</td><td>{movement.balance === null ? "—" : money(movement.balance)}</td><td><div className="bank-match-control"><select value={movement.id_invoice || ""} onChange={(event) => handleMatch(movement, event.target.value)} disabled={!canManage}><option value="">Sin vincular</option>{matchingInvoices.map((invoice) => <option key={invoice.id_invoice} value={invoice.id_invoice}>{invoice.folio || invoice.folio_fiscal || `Factura #${invoice.id_invoice}`} · {money(invoice.total)}{suggestion?.id_invoice === invoice.id_invoice ? " · Sugerida" : ""}</option>)}</select>{movement.id_invoice && <Link2 size={15} />}</div></td></tr>; })}</tbody></table></div></td></tr>}
        </Fragment>)}</tbody></table></div>}
      </div>
    </section>
  );
}
