import { Fragment, useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
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
import { useI18n } from "../i18n";
import { useDialogo } from "../dialogo/useDialogo.js";

function money(value, locale) {
  return Number(value || 0).toLocaleString(locale, { style: "currency", currency: "MXN" });
}

function dateLabel(value, locale) {
  if (!value) return "—";
  const date = new Date(`${String(value).slice(0, 10)}T12:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(locale);
}

function messageFrom(error, t) {
  return error?.payload?.meta?.reason || error?.payload?.message || error?.message || t("bank_statements.error_operation");
}

export default function BankStatementsPanel({ canManage, canCreateAccount }) {
  const { lang, t } = useI18n();
  const dialogo = useDialogo();
  const formatMoney = (value) => money(value, lang);
  const formatDate = (value) => dateLabel(value, lang);
  const errorMessage = (error) => messageFrom(error, t);
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
      setError(errorMessage(requestError));
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
      setError(errorMessage(requestError));
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
    if (!accountId || !file) return setError(t("bank_statements.select_account_file"));
    setLoading(true); setError(""); setNotice("");
    try {
      setPreview(await previewBankStatement(uploadBody()));
    } catch (requestError) {
      setError(errorMessage(requestError));
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
      setNotice(t("bank_statements.account_created"));
    } catch (requestError) {
      setError(errorMessage(requestError));
    }
  }

  async function handleImport() {
    if (!accountId || !file) return setError(t("bank_statements.select_account_file"));
    setLoading(true); setError("");
    try {
      const response = await importBankStatement(uploadBody());
      setNotice(`${t("bank_statements.imported_with")} ${response.movement_count || 0} ${t("bank_statements.movements_lower")}.`);
      setPreview(null); setFile(null);
      await loadWorkspace();
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  async function handleMatch(movement, invoiceId, force = false) {
    try {
      await matchBankStatementMovement(movement.id_bank_statement_movement, { id_invoice: invoiceId || null, force });
      await loadMovements(selectedId);
    } catch (requestError) {
      if (requestError.status === 409 && requestError.payload?.meta?.force_allowed && await dialogo.confirmar(t("bank_statements.confirm_force_match"))) {
        await handleMatch(movement, invoiceId, true);
        return;
      }
      setError(errorMessage(requestError));
    }
  }

  async function handleDelete(statementId) {
    if (!(await dialogo.confirmar(t("bank_statements.confirm_delete")))) return;
    try {
      await deleteBankStatement(statementId);
      if (selectedId === statementId) { setSelectedId(null); setMovements([]); }
      await loadWorkspace();
    } catch (requestError) {
      setError(errorMessage(requestError));
    }
  }

  function suggestedInvoice(movement) {
    const amount = Number(movement.debit || movement.credit || 0);
    return matchingInvoices.find((invoice) => Math.abs(Number(invoice.total || 0) - amount) <= 0.05);
  }

  return (
    <section className="bank-statements-workspace">
      <div className="bank-statements-heading">
        <div><p className="eyebrow">{t("bank_statements.eyebrow")}</p><h3>{t("bank_statements.title")}</h3><p className="muted">{t("bank_statements.subtitle")}</p></div>
        <button type="button" className="button ghost" onClick={loadWorkspace} disabled={loading}><RefreshCw size={16} />{t("bank_statements.refresh")}</button>
      </div>

      {error && <div className="alert error">{error}</div>}
      {notice && <div className="alert success">{notice}</div>}

      {canManage && <div className="bank-statement-importer">
        <label className="field"><span>{t("bank_statements.bank_account")}</span><select required value={accountId} onChange={(event) => { setAccountId(event.target.value); setPreview(null); }}><option value="">{t("bank_statements.select_account")}</option>{accounts.map((account) => <option key={account.id_bank_account} value={account.id_bank_account}>{account.bank_account_description} · {account.branch || t("bank_statements.no_branch")}</option>)}</select>{canCreateAccount && <button type="button" className="text-button" onClick={() => setCreatingAccount((value) => !value)}><Plus size={14} />{t("bank_statements.new_account")}</button>}</label>
        <label className="field"><span>{t("bank_statements.statement")}</span><input type="file" accept=".pdf,.csv,application/pdf,text/csv" onChange={(event) => { setFile(event.target.files?.[0] || null); setPreview(null); }} /></label>
        <div className="bank-import-actions"><button type="button" className="button" disabled={loading || !file || !accountId} onClick={handlePreview}><Eye size={16} />{t("bank_statements.preview")}</button><button type="button" className="button primary" disabled={loading || !file || !accountId || preview?.already_imported} onClick={handleImport}><Upload size={16} />{t("bank_statements.import")}</button></div>
      </div>}

      {canCreateAccount && creatingAccount && <form className="bank-account-inline" onSubmit={handleCreateAccount}>
        <label className="field"><span>{t("bank_statements.bank")}</span><select required value={newAccount.id_bank} onChange={(event) => setNewAccount((current) => ({ ...current, id_bank: event.target.value }))}><option value="">{t("bank_statements.select")}</option>{banks.map((bank) => <option key={bank.id_bank} value={bank.id_bank}>{bank.bank_name}</option>)}</select></label>
        <label className="field"><span>{t("bank_statements.description")}</span><input required maxLength="200" value={newAccount.bank_account_description} onChange={(event) => setNewAccount((current) => ({ ...current, bank_account_description: event.target.value }))} /></label>
        <label className="field"><span>{t("bank_statements.project")}</span><select required value={newAccount.id_proyect} onChange={(event) => setNewAccount((current) => ({ ...current, id_proyect: event.target.value }))}><option value="">{t("bank_statements.select")}</option>{projects.map((project) => <option key={project.id_proyect} value={project.id_proyect}>{project.proyect_description || project.title || `${t("bank_statements.project")} #${project.id_proyect}`}</option>)}</select></label>
        <label className="field"><span>{t("bank_statements.branch")}</span><input maxLength="30" value={newAccount.branch} onChange={(event) => setNewAccount((current) => ({ ...current, branch: event.target.value }))} /></label>
        <button type="submit" className="button primary">{t("bank_statements.save_account")}</button>
      </form>}

      {preview && <div className="bank-statement-preview">
        <div className="bank-statement-metrics"><span><small>{t("bank_statements.period")}</small><strong>{formatDate(preview.statement.period_start)} – {formatDate(preview.statement.period_end)}</strong></span><span><small>{t("bank_statements.debits")}</small><strong>{formatMoney(preview.statement.total_debits)}</strong></span><span><small>{t("bank_statements.credits")}</small><strong>{formatMoney(preview.statement.total_credits)}</strong></span><span><small>{t("bank_statements.movements")}</small><strong>{preview.movement_count}</strong></span><span><small>{t("bank_statements.validation")}</small><strong className={preview.reconciliation.ok ? "text-success" : "text-warning"}>{preview.reconciliation.ok ? t("bank_statements.reconciled") : t("bank_statements.review")}</strong></span></div>
        {preview.already_imported && <div className="alert error">{t("bank_statements.already_imported")}</div>}
        {preview.reconciliation.warnings?.map((warning) => <p className="field-error" key={warning}>{warning}</p>)}
      </div>}

      <div className="bank-statements-list">
        <div className="bank-list-title"><strong>{t("bank_statements.import_history")}</strong><span>{statements.length} {t("bank_statements.statements_lower")}</span></div>
        {!statements.length ? <div className="empty"><strong>{t("bank_statements.empty_title")}</strong><p>{t("bank_statements.empty_body")}</p></div> : <div className="table-wrap"><table><thead><tr><th></th><th>{t("bank_statements.file")}</th><th>{t("bank_statements.period")}</th><th>{t("bank_statements.debits")}</th><th>{t("bank_statements.credits")}</th><th>{t("bank_statements.ending_balance")}</th><th>{t("bank_statements.status")}</th><th>{t("bank_statements.movements")}</th><th></th></tr></thead><tbody>{statements.map((statement) => <Fragment key={statement.id_bank_statement}>
          <tr><td><button type="button" className="icon-button" title={t("bank_statements.view_movements")} onClick={() => toggleStatement(statement.id_bank_statement)}>{selectedId === statement.id_bank_statement ? <ChevronDown size={17} /> : <ChevronRight size={17} />}</button></td><td><strong>{statement.original_filename}</strong><small className="cell-value">{statement.parser_name || "—"}</small></td><td>{formatDate(statement.period_start)} – {formatDate(statement.period_end)}</td><td>{formatMoney(statement.total_debits)}</td><td>{formatMoney(statement.total_credits)}</td><td>{formatMoney(statement.ending_balance)}</td><td><span className={`bank-status ${statement.status}`}>{statement.status === "completed" ? t("bank_statements.reconciled") : t("bank_statements.review")}</span></td><td>{statement.movement_count}</td><td>{canManage && <button type="button" className="icon-button danger" title={t("bank_statements.delete_statement")} onClick={() => handleDelete(statement.id_bank_statement)}><Trash2 size={16} /></button>}</td></tr>
          {selectedId === statement.id_bank_statement && <tr key={`${statement.id_bank_statement}-detail`} className="bank-movements-row"><td colSpan="9"><div className="bank-movements-toolbar"><strong>{t("bank_statements.movements")}</strong><select value={movementType} onChange={(event) => { setMovementType(event.target.value); loadMovements(statement.id_bank_statement, event.target.value); }}><option value="">{t("bank_statements.all")}</option><option value="debit">{t("bank_statements.debits")}</option><option value="credit">{t("bank_statements.credits")}</option></select></div><div className="table-wrap"><table className="bank-movements-table"><thead><tr><th>{t("bank_statements.date")}</th><th>{t("bank_statements.description")}</th><th>{t("bank_statements.reference")}</th><th>{t("bank_statements.debit")}</th><th>{t("bank_statements.credit")}</th><th>{t("bank_statements.balance")}</th><th>{t("bank_statements.reconciliation")}</th></tr></thead><tbody>{movements.map((movement) => { const suggestion = suggestedInvoice(movement); return <tr key={movement.id_bank_statement_movement}><td>{formatDate(movement.movement_date)}</td><td><strong>{movement.description}</strong><small className="cell-value">{movement.code || ""}</small></td><td>{movement.reference || "—"}</td><td>{movement.debit ? formatMoney(movement.debit) : "—"}</td><td>{movement.credit ? formatMoney(movement.credit) : "—"}</td><td>{movement.balance === null ? "—" : formatMoney(movement.balance)}</td><td><div className="bank-match-control"><select value={movement.id_invoice || ""} onChange={(event) => handleMatch(movement, event.target.value)} disabled={!canManage}><option value="">{t("bank_statements.unlinked")}</option>{matchingInvoices.map((invoice) => <option key={invoice.id_invoice} value={invoice.id_invoice}>{invoice.folio || invoice.folio_fiscal || `${t("bank_statements.invoice")} #${invoice.id_invoice}`} · {formatMoney(invoice.total)}{suggestion?.id_invoice === invoice.id_invoice ? ` · ${t("bank_statements.suggested")}` : ""}</option>)}</select>{movement.id_invoice && <Link2 size={15} />}</div></td></tr>; })}</tbody></table></div></td></tr>}
        </Fragment>)}</tbody></table></div>}
      </div>
    </section>
  );
}

BankStatementsPanel.propTypes = {
  canManage: PropTypes.bool,
  canCreateAccount: PropTypes.bool,
};
