
from __future__ import annotations

from app.jobs.celery_app import celery
from app.jobs.task_helpers import result_ok


@celery.task(name="app.jobs.tasks_erp.close_accounting_period")
def close_accounting_period(period_id: int | str, requested_by: int | None = None) -> dict:
    return result_ok("jobs.erp.accounting_period_closed", period_id=period_id, requested_by=requested_by)


@celery.task(name="app.jobs.tasks_erp.recalculate_invoice_totals")
def recalculate_invoice_totals(invoice_id: int | str | None = None) -> dict:
    return result_ok("jobs.erp.invoice_totals_recalculated", invoice_id=invoice_id)


@celery.task(name="app.jobs.tasks_erp.generate_payroll_run")
def generate_payroll_run(payroll_period_id: int | str, requested_by: int | None = None) -> dict:
    return result_ok("jobs.erp.payroll_run_generated", payroll_period_id=payroll_period_id, requested_by=requested_by)


@celery.task(name="app.jobs.tasks_erp.reconcile_bank_accounts")
def reconcile_bank_accounts(bank_account_id: int | str | None = None) -> dict:
    return result_ok("jobs.erp.bank_accounts_reconciled", bank_account_id=bank_account_id)
