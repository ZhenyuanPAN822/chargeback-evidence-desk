from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path

from chargeback_evidence_desk.analyzer import analyze_disputes, parse_csv, parse_invoice_text


ROOT = Path(__file__).resolve().parents[1]


class AnalyzerTests(unittest.TestCase):
    def test_realistic_sample_has_24_cases(self) -> None:
        text = (ROOT / "samples" / "chargebacks_24_cases.csv").read_text(encoding="utf-8")
        disputes, metadata = parse_csv(text)
        self.assertEqual(len(disputes), 24)
        self.assertEqual(metadata["source_system_hint"], "PayPal-like export")

    def test_flexible_stripe_mapping_works(self) -> None:
        text = (ROOT / "samples" / "stripe_like_disputes.csv").read_text(encoding="utf-8")
        disputes, metadata = parse_csv(text)
        self.assertEqual(len(disputes), 2)
        self.assertEqual(disputes[0].dispute_id, "dp_1")
        self.assertEqual(disputes[0].reason, "product_not_received")
        self.assertIn("dispute_id", metadata["mapping"])

    def test_missing_required_fields_are_reported(self) -> None:
        disputes, metadata = parse_csv("name,total\nAlice,10\n")
        self.assertIn("dispute_id", metadata["missing_required_columns"])
        self.assertTrue(disputes[0].needs_review)

    def test_pasted_text_parser_extracts_fields(self) -> None:
        text = """Stripe dispute id: DP-7781
        Reason: product not received
        Disputed amount: $188.00
        Respond by: 2026-05-01
        Order # ORD-7781
        Customer: nina@example.com
        Tracking number: 1ZPASTE123456
        Delivered. Shipping address matches."""
        dispute = parse_invoice_text(text)
        self.assertEqual(dispute.dispute_id, "DP-7781")
        self.assertEqual(dispute.amount, 188.0)
        self.assertEqual(dispute.reason, "product_not_received")
        self.assertEqual(dispute.tracking_number, "1ZPASTE123456")

    def test_analysis_prioritizes_deadline_and_evidence_gap(self) -> None:
        text = (ROOT / "samples" / "chargebacks_24_cases.csv").read_text(encoding="utf-8")
        disputes, _ = parse_csv(text)
        report = analyze_disputes(disputes, today=date(2026, 4, 28))
        self.assertEqual(report["summary"]["dispute_count"], 24)
        self.assertGreaterEqual(report["summary"]["critical_count"], 2)
        self.assertIn("markdown_report", report)
        top = report["queue"][0]
        self.assertIn(top["urgency"], {"critical", "expired", "due_soon"})

    def test_product_not_received_missing_tracking_is_actionable(self) -> None:
        text = "case_id,platform,reason_code,dispute_amount,respond_by\nCB-X,Stripe,product_not_received,100,2026-05-01\n"
        disputes, _ = parse_csv(text)
        report = analyze_disputes(disputes, today=date(2026, 4, 28))
        finding = report["queue"][0]
        self.assertIn("tracking_number", finding["missing_evidence"])
        self.assertIn("Collect missing evidence", finding["recommended_action"])

    def test_malformed_csv_does_not_crash(self) -> None:
        disputes, metadata = parse_csv("not,a,normal\n1,2\n")
        self.assertEqual(len(disputes), 1)
        self.assertTrue(metadata["missing_required_columns"])


if __name__ == "__main__":
    unittest.main()

