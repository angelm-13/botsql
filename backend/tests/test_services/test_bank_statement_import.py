from __future__ import annotations

import unittest
from decimal import Decimal

from app.services.bank_statement_import import parse_statement_csv


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


if __name__ == "__main__": unittest.main()