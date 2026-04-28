# Chargeback Evidence Desk

English | [中文](README.zh-CN.md)

Local-first evidence triage for small merchants fighting Stripe, Shopify, PayPal, and Square chargebacks.

- Normalizes messy dispute exports and pasted dispute text into reviewable cases.
- Ranks cases by deadline, amount at risk, evidence gaps, and reason-code requirements.
- Produces a Markdown/JSON evidence packet outline with concrete next actions.

Screenshot/GIF to be added before launch.

Quick demo:

```bash
python server.py
# open http://127.0.0.1:8784
```

## Hero Section

Chargeback Evidence Desk is a local browser app for small e-commerce sellers, studios, agencies, and service businesses that need to respond to payment disputes before evidence deadlines expire. It turns dispute rows, dashboard text, and manual case notes into an evidence queue, deadline board, processor summary, and copy-ready packet outline.

## Problem

Small merchants often learn about a chargeback after the money has already been pulled from their balance. The hard part is not only knowing that a dispute exists. The real work is finding the order, checking the response deadline, matching the dispute reason, collecting tracking or delivery proof, pulling customer messages, deciding which cases deserve attention first, and writing a concise evidence packet before the platform deadline.

## Why Existing Approaches Are Not Enough

Processor dashboards tell merchants where to upload evidence, but they do not always help a small team triage many disputes across Stripe, Shopify, PayPal, and Square. Spreadsheets can track cases, but they usually do not translate reason codes into missing evidence, deadline risk, or a packet structure. Generic chargeback guides explain what evidence might help, but the merchant still has to map that advice back to each case.

## What This Project Does

CSV export, pasted dispute text, or manual case entry -> flexible field mapping -> human review table -> evidence requirement scoring -> deadline and amount prioritization -> Markdown/JSON packet report.

## Why this is useful

This is not a generic upload-and-report screen. Chargeback Evidence Desk focuses on the operational moment before submission: which dispute should be handled first, which evidence is missing, which processor/reason category is involved, what packet sections to assemble, and how uncertainty should be labeled before the merchant submits anything.

## Key Features

- Flexible CSV mapping for Stripe-like, Shopify-like, PayPal-like, Square-like, and generic spreadsheet exports.
- Pasted dispute text parser for dashboard emails, copied PDF text, or OCR text.
- Manual dispute entry for one-off cases.
- Mandatory normalized review table before analysis.
- Deadline, amount-at-risk, evidence-readiness, and missing-field scoring.
- Reason-specific evidence checklist for fraud, product-not-received, not-as-described, duplicate, refund, and service disputes.
- Processor board for Stripe, Shopify, PayPal, Square, and generic cases.
- What-if notes for internal deadline buffers and missing tracking evidence.
- Markdown and JSON exports saved locally.
- No accounts, no API keys, no external data upload.

## Demo / Screenshots

Screenshot/GIF to be added before launch.

The included sample has 24 disputes across Stripe, Shopify, PayPal, and Square. It includes expired deadlines, critical deadlines, missing tracking, missing due dates, digital goods, services, high-value cases, low-value cases, refunds, duplicate disputes, fraud disputes, and product-not-received disputes.

## Quick Start

```bash
python server.py
```

Open `http://127.0.0.1:8784`, click `Load 24-case sample`, then `Analyze evidence queue`.

Run tests:

```bash
python -m unittest discover -s tests
python scripts/smoke_test.py
```

## Example Input / Output

Input examples:

- `samples/chargebacks_24_cases.csv`
- `samples/stripe_like_disputes.csv`
- `samples/pasted_dispute_examples.txt`

Output files:

- `outputs/chargeback-evidence-report.md`
- `outputs/chargeback-evidence-report.json`
- committed examples in `examples/`

The report includes an executive summary, processor summary, deadline-prioritized queue, missing evidence list, confidence label, recommended next action, and packet sections for each dispute.

## Use Cases

- A Shopify merchant has several chargebacks and needs to decide which evidence packet to prepare first.
- A Stripe seller has fraud and product-not-received disputes and wants to see missing AVS, device, tracking, or message evidence.
- A PayPal seller wants a local checklist before uploading seller-protection documentation.
- A Square merchant wants a concise case packet before submitting documents in the dashboard.
- A small agency wants to triage disputed service invoices without sending private client data to a SaaS tool.

## How It Works

The app maps common column names into a normalized dispute model. It then applies reason-specific evidence requirements, checks due dates against an internal review buffer, scores evidence readiness, ranks cases by deadline, amount at risk, missing evidence, and review needs, and generates a local Markdown/JSON packet. The pasted-text parser uses conservative deterministic patterns and marks low-confidence extraction for review.

## Project Structure

```text
chargeback_evidence_desk/analyzer.py   import, parsing, scoring, report generation
server.py                              local web server and API
web/                                   browser desk UI
samples/                               realistic CSV and pasted-text fixtures
tests/                                 unit tests
scripts/smoke_test.py                  user-perspective smoke test
examples/                              generated sample report
```

## Roadmap

- Source-specific export presets for Stripe, Shopify, PayPal, and Square.
- PDF/image OCR import.
- Evidence attachment checklist with local file references.
- Processor-specific packet formatting.
- Optional CLI/CI mode for agencies handling many disputes.
- Screenshot/GIF for GitHub launch.

## Limitations

Chargeback Evidence Desk is an operational preparation tool, not legal advice and not a guarantee of dispute outcome. It does not submit evidence to processors, does not connect to Stripe/Shopify/PayPal/Square APIs, and does not perform PDF/image OCR. Pasted text parsing is conservative and must be reviewed before use. Processor rules change, so merchants should verify final evidence requirements in the relevant dashboard or official documentation.

## License

MIT

## Language

- English: `README.md`
- Chinese: `README.zh-CN.md`
