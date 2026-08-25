from __future__ import annotations

import unittest
from decimal import Decimal

from app.services.bank_statement_import import parse_bbva_text, parse_statement_csv, reconcile_statement


class TestBankStatementImport(unittest.TestCase):
    def test_parses_totals_period_and_hash(self):
        result = parse_statement_csv(b"date,description,debit,credit\n2026-08-01,Compra,10.25,0\n2026-08-02,Deposito,0,20.50\n")
        self.assertEqual(result["total_debits"], Decimal("10.25"))
        self.assertEqual(result["total_credits"], Decimal("20.50"))
        self.assertEqual(len(result["file_hash"]), 64)

    def test_rejects_missing_columns_ambiguous_and_oversized_files(self):
        with self.assertRaises(ValueError): parse_statement_csv(b"date,value\n2026-01-01,1\n")
        with self.assertRaises(ValueError): parse_statement_csv(b"date,description,debit,credit\n2026-01-01,Bad,1,1\n")
        with self.assertRaises(ValueError): parse_statement_csv(b"x" * 20, max_bytes=10)

    def test_parses_bbva_statement_text_and_reconciles_balance(self):
        parsed = parse_bbva_text("""
        BBVA ESTADO DE CUENTA
        PERIODO DEL 01/08/2026 AL 31/08/2026
        SALDO INICIAL 1,000.00
        SALDO FINAL 1,150.00
        TOTAL CARGOS 50.00
        TOTAL ABONOS 200.00
        01/AGO 01/AGO N06 PAGO SERVICIO 50.00 0.00 950.00
        02/AGO 02/AGO N06 DEPOSITO RECIBIDO 0.00 200.00 1,150.00
        """, file_bytes=b"pdf-content")

        self.assertEqual(2, len(parsed["movements"]))
        self.assertEqual(Decimal("50.00"), parsed["total_debits"])
        self.assertEqual(Decimal("200.00"), parsed["total_credits"])
        self.assertEqual("N06", parsed["movements"][0]["code"])
        self.assertEqual(Decimal("1150.00"), parsed["ending_balance"])
        self.assertTrue(reconcile_statement(parsed)["ok"])

    def test_reconciliation_reports_document_total_difference(self):
        parsed = parse_statement_csv(b"date,description,debit,credit\n2026-08-01,Compra,10.00,0\n")
        parsed["document_total_debits"] = Decimal("15.00")

        reconciliation = reconcile_statement(parsed)

        self.assertFalse(reconciliation["ok"])
        self.assertTrue(reconciliation["warnings"])


if __name__ == "__main__": unittest.main()