from __future__ import annotations

import csv
import io
import json
import math
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable


FIELD_ALIASES = {
    "dispute_id": ["dispute_id", "dispute", "case_id", "case", "chargeback_id", "claim_id", "id"],
    "processor": ["processor", "platform", "payment_processor", "gateway", "source"],
    "reason": ["reason", "dispute_reason", "reason_code", "claim_reason", "category"],
    "amount": ["amount", "dispute_amount", "chargeback_amount", "total", "transaction_amount"],
    "currency": ["currency", "ccy"],
    "due_date": ["due_date", "respond_by", "deadline", "evidence_due", "submit_by"],
    "transaction_date": ["transaction_date", "charge_date", "payment_date", "order_date", "date"],
    "order_id": ["order_id", "order", "order_number", "invoice", "invoice_id"],
    "customer_name": ["customer_name", "customer", "buyer", "buyer_name", "name"],
    "customer_email": ["customer_email", "email", "buyer_email", "client_email"],
    "product_type": ["product_type", "goods_type", "item_type", "fulfillment_type"],
    "delivery_status": ["delivery_status", "shipping_status", "fulfillment_status", "delivered"],
    "tracking_number": ["tracking_number", "tracking", "tracking_no", "shipment_tracking"],
    "shipping_address_match": ["shipping_address_match", "address_match", "ship_to_match"],
    "refund_status": ["refund_status", "refund", "refunded", "refund_state"],
    "customer_messages": ["customer_messages", "messages", "communication", "emails", "chat"],
    "policy_url": ["policy_url", "return_policy", "terms_url", "policy"],
    "notes": ["notes", "memo", "description", "comment"],
}

REQUIRED_FIELDS = ("dispute_id", "processor", "reason", "amount", "due_date")

REASON_REQUIREMENTS = {
    "fraud": ["customer_authorization", "avs_or_cvc", "ip_or_device", "customer_messages"],
    "product_not_received": ["tracking_number", "delivery_status", "shipping_address_match", "customer_messages"],
    "not_received": ["tracking_number", "delivery_status", "shipping_address_match", "customer_messages"],
    "not_as_described": ["product_description", "return_policy", "customer_messages", "photos_or_quality_notes"],
    "duplicate": ["receipt", "refund_status", "transaction_history"],
    "credit_not_processed": ["refund_status", "refund_receipt", "customer_messages"],
    "service_not_provided": ["service_log", "customer_messages", "contract_or_invoice"],
    "unknown": ["receipt", "customer_messages", "fulfillment_evidence"],
}


@dataclass
class NormalizedDispute:
    dispute_id: str
    processor: str
    reason: str
    amount: float
    currency: str = "USD"
    due_date: str = ""
    transaction_date: str = ""
    order_id: str = ""
    customer_name: str = ""
    customer_email: str = ""
    product_type: str = "physical"
    delivery_status: str = ""
    tracking_number: str = ""
    shipping_address_match: str = ""
    refund_status: str = ""
    customer_messages: str = ""
    policy_url: str = ""
    notes: str = ""
    extraction_source: str = "csv"
    confidence: float = 0.8
    needs_review: bool = False
    missing_fields: list[str] = field(default_factory=list)


@dataclass
class DisputeAnalysis:
    dispute: NormalizedDispute
    days_until_due: int | None
    urgency: str
    evidence_score: int
    win_readiness: str
    priority_score: float
    missing_evidence: list[str]
    available_evidence: list[str]
    recommended_action: str
    suggested_packet_sections: list[str]
    constraints: list[str]
    confidence: str
    false_positive_note: str


def _normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _parse_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    text = re.sub(r"[^0-9.\-]", "", text)
    try:
        return float(text)
    except ValueError:
        return default


def parse_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%b %d %Y", "%B %d %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in {"yes", "y", "true", "1", "delivered", "matched", "match"}


def detect_mapping(headers: Iterable[str]) -> dict[str, str]:
    normalized = {_normalize_header(header): header for header in headers}
    mapping: dict[str, str] = {}
    for internal, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            key = _normalize_header(alias)
            if key in normalized:
                mapping[internal] = normalized[key]
                break
    return mapping


def normalize_row(row: dict[str, Any], mapping: dict[str, str], source: str = "csv") -> NormalizedDispute:
    values: dict[str, Any] = {}
    for field_name in FIELD_ALIASES:
        source_col = mapping.get(field_name)
        values[field_name] = row.get(source_col, "") if source_col else ""
    missing = [field_name for field_name in REQUIRED_FIELDS if not str(values.get(field_name, "")).strip()]
    dispute = NormalizedDispute(
        dispute_id=str(values.get("dispute_id") or f"UNMAPPED-{abs(hash(str(row))) % 100000}").strip(),
        processor=str(values.get("processor") or "unknown").strip().lower(),
        reason=normalize_reason(str(values.get("reason") or "unknown")),
        amount=_parse_float(values.get("amount")),
        currency=str(values.get("currency") or "USD").strip().upper() or "USD",
        due_date=str(values.get("due_date") or "").strip(),
        transaction_date=str(values.get("transaction_date") or "").strip(),
        order_id=str(values.get("order_id") or "").strip(),
        customer_name=str(values.get("customer_name") or "").strip(),
        customer_email=str(values.get("customer_email") or "").strip(),
        product_type=str(values.get("product_type") or "physical").strip().lower(),
        delivery_status=str(values.get("delivery_status") or "").strip().lower(),
        tracking_number=str(values.get("tracking_number") or "").strip(),
        shipping_address_match=str(values.get("shipping_address_match") or "").strip().lower(),
        refund_status=str(values.get("refund_status") or "").strip().lower(),
        customer_messages=str(values.get("customer_messages") or "").strip(),
        policy_url=str(values.get("policy_url") or "").strip(),
        notes=str(values.get("notes") or "").strip(),
        extraction_source=source,
        confidence=0.85 if not missing else 0.55,
        needs_review=bool(missing),
        missing_fields=missing,
    )
    return dispute


def normalize_reason(reason: str) -> str:
    text = _normalize_header(reason)
    if "fraud" in text or "unauthorized" in text or "recogn" in text:
        return "fraud"
    if "not_received" in text or ("not" in text and "received" in text) or "product_not_received" in text:
        return "product_not_received"
    if "not_as" in text or "described" in text or "quality" in text:
        return "not_as_described"
    if "duplicate" in text:
        return "duplicate"
    if "credit" in text or "refund" in text:
        return "credit_not_processed"
    if "service" in text:
        return "service_not_provided"
    return text or "unknown"


def parse_csv(text: str) -> tuple[list[NormalizedDispute], dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text.strip()))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row. Include columns such as dispute_id, processor, reason, amount, and due_date.")
    mapping = detect_mapping(reader.fieldnames)
    missing_required = [field for field in REQUIRED_FIELDS if field not in mapping]
    rows = list(reader)
    disputes = [normalize_row(row, mapping) for row in rows]
    metadata = {
        "mapping": mapping,
        "missing_required_columns": missing_required,
        "row_count": len(disputes),
        "source_system_hint": infer_source_system(reader.fieldnames),
    }
    if missing_required:
        metadata["warning"] = "Some required fields were not mapped. A review step is required before trusting the analysis."
    return disputes, metadata


def infer_source_system(headers: Iterable[str]) -> str:
    header_text = " ".join(_normalize_header(h) for h in headers)
    if "charge_id" in header_text or "payment_intent" in header_text:
        return "Stripe-like export"
    if "order_number" in header_text and "fulfillment" in header_text:
        return "Shopify-like export"
    if "case_id" in header_text or "claim_id" in header_text:
        return "PayPal-like export"
    if "square" in header_text or "tender" in header_text:
        return "Square-like export"
    return "generic CSV/Excel export"


TEXT_PATTERNS = {
    "dispute_id": [r"(?:dispute|case|claim|chargeback)\s*(?:id|#|number)?\s*[:#]?\s*([A-Z0-9\-]{4,})"],
    "order_id": [r"(?:order|invoice)\s*(?:id|#|number)?\s*[:#]?\s*([A-Z0-9\-]{3,})"],
    "customer_email": [r"([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})"],
    "amount": [r"(?:amount|total|disputed amount|chargeback amount)\s*[:#]?\s*([$€£]?\s*[0-9][0-9,]*(?:\.[0-9]{2})?)"],
    "due_date": [r"(?:due|respond by|deadline|submit by|evidence due)\s*[:#]?\s*([A-Z][a-z]+ \d{1,2} \d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})"],
    "reason": [r"(?:reason|category)\s*[:#]?\s*([A-Za-z _\-]+)"],
    "tracking_number": [r"(?:tracking number|tracking)\s*[:#]?\s*([A-Z0-9\-]{6,})"],
}


def parse_invoice_text(text: str) -> NormalizedDispute:
    fields: dict[str, str] = {}
    for field_name, patterns in TEXT_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields[field_name] = match.group(1).strip()
                break
    processor = "stripe" if "stripe" in text.lower() else "shopify" if "shopify" in text.lower() else "paypal" if "paypal" in text.lower() else "unknown"
    amount_text = fields.get("amount", "")
    currency = "USD"
    if "€" in amount_text:
        currency = "EUR"
    elif "£" in amount_text:
        currency = "GBP"
    dispute = NormalizedDispute(
        dispute_id=fields.get("dispute_id", f"TEXT-{abs(hash(text)) % 100000}"),
        processor=processor,
        reason=normalize_reason(fields.get("reason", "unknown")),
        amount=_parse_float(amount_text),
        currency=currency,
        due_date=fields.get("due_date", ""),
        order_id=fields.get("order_id", ""),
        customer_email=fields.get("customer_email", ""),
        tracking_number=fields.get("tracking_number", ""),
        delivery_status="delivered" if re.search(r"\bdelivered\b", text, re.IGNORECASE) else "",
        shipping_address_match="yes" if re.search(r"address (?:match|matches|matched)", text, re.IGNORECASE) else "",
        customer_messages="present" if re.search(r"email|message|chat|whatsapp", text, re.IGNORECASE) else "",
        notes=text.strip()[:800],
        extraction_source="pasted_text",
    )
    present = sum(1 for value in (fields.get("dispute_id"), fields.get("amount"), fields.get("due_date"), fields.get("reason")) if value)
    dispute.confidence = min(0.9, 0.35 + present * 0.14)
    dispute.needs_review = dispute.confidence < 0.75
    dispute.missing_fields = [field_name for field_name in REQUIRED_FIELDS if not getattr(dispute, field_name)]
    return dispute


def analyze_disputes(disputes: list[NormalizedDispute], today: date | None = None, scenario: dict[str, Any] | None = None) -> dict[str, Any]:
    today = today or date.today()
    scenario = scenario or {}
    deadline_buffer = int(scenario.get("deadline_buffer_days", 1))
    include_low_value = bool(scenario.get("include_low_value", True))
    analyses = [analyze_one(dispute, today, deadline_buffer) for dispute in disputes]
    if not include_low_value:
        analyses = [item for item in analyses if item.dispute.amount >= 50 or item.urgency in {"critical", "due_soon"}]
    analyses.sort(key=lambda item: item.priority_score, reverse=True)
    processor_summary: dict[str, dict[str, Any]] = {}
    for item in analyses:
        key = item.dispute.processor or "unknown"
        bucket = processor_summary.setdefault(key, {"count": 0, "amount": 0.0, "critical": 0})
        bucket["count"] += 1
        bucket["amount"] += item.dispute.amount
        if item.urgency == "critical":
            bucket["critical"] += 1
    return {
        "summary": {
            "dispute_count": len(disputes),
            "analyzed_count": len(analyses),
            "total_amount": round(sum(item.dispute.amount for item in analyses), 2),
            "critical_count": sum(1 for item in analyses if item.urgency == "critical"),
            "needs_review_count": sum(1 for item in analyses if item.dispute.needs_review),
        },
        "processor_summary": processor_summary,
        "queue": [analysis_to_dict(item) for item in analyses],
        "what_if": build_what_if(analyses),
        "markdown_report": render_markdown(analyses, processor_summary),
    }


def analyze_one(dispute: NormalizedDispute, today: date, deadline_buffer: int = 1) -> DisputeAnalysis:
    due = parse_date(dispute.due_date)
    days_until_due = (due - today).days if due else None
    urgency = classify_urgency(days_until_due, deadline_buffer)
    required = REASON_REQUIREMENTS.get(dispute.reason, REASON_REQUIREMENTS["unknown"])
    available: list[str] = []
    missing: list[str] = []
    evidence_flags = {
        "tracking_number": bool(dispute.tracking_number),
        "delivery_status": "delivered" in dispute.delivery_status,
        "shipping_address_match": _truthy(dispute.shipping_address_match),
        "customer_messages": bool(dispute.customer_messages),
        "refund_status": bool(dispute.refund_status),
        "receipt": bool(dispute.order_id or dispute.transaction_date),
        "transaction_history": bool(dispute.order_id),
        "customer_authorization": bool(dispute.customer_messages or dispute.notes),
        "avs_or_cvc": "avs" in dispute.notes.lower() or "cvc" in dispute.notes.lower(),
        "ip_or_device": "ip" in dispute.notes.lower() or "device" in dispute.notes.lower(),
        "product_description": bool(dispute.notes or dispute.policy_url),
        "return_policy": bool(dispute.policy_url),
        "photos_or_quality_notes": "photo" in dispute.notes.lower() or "quality" in dispute.notes.lower(),
        "refund_receipt": "refunded" in dispute.refund_status,
        "service_log": "service" in dispute.product_type or "usage" in dispute.notes.lower(),
        "contract_or_invoice": bool(dispute.order_id),
        "fulfillment_evidence": bool(dispute.tracking_number or dispute.customer_messages),
    }
    for evidence in required:
        if evidence_flags.get(evidence):
            available.append(evidence)
        else:
            missing.append(evidence)
    evidence_score = int(round(100 * len(available) / max(len(required), 1)))
    amount_weight = min(35, math.log10(max(dispute.amount, 1)) * 12)
    urgency_weight = {"critical": 45, "due_soon": 30, "normal": 14, "unknown": 20, "expired": 50}[urgency]
    gap_weight = (100 - evidence_score) * 0.35
    priority_score = round(amount_weight + urgency_weight + gap_weight + (15 if dispute.needs_review else 0), 1)
    readiness = "ready_to_compile" if evidence_score >= 75 and urgency != "expired" else "needs_evidence" if urgency != "expired" else "deadline_risk"
    confidence = "HIGH" if evidence_score >= 75 and not dispute.needs_review else "MEDIUM" if evidence_score >= 50 else "LOW"
    constraints = []
    if urgency in {"critical", "expired"}:
        constraints.append("deadline")
    if dispute.amount >= 500:
        constraints.append("cash_at_risk")
    if missing:
        constraints.append("evidence_gap")
    if dispute.reason in {"fraud", "product_not_received"}:
        constraints.append("reason_code_evidence")
    return DisputeAnalysis(
        dispute=dispute,
        days_until_due=days_until_due,
        urgency=urgency,
        evidence_score=evidence_score,
        win_readiness=readiness,
        priority_score=priority_score,
        missing_evidence=missing,
        available_evidence=available,
        recommended_action=recommend_action(dispute, urgency, missing, evidence_score),
        suggested_packet_sections=packet_sections(dispute.reason),
        constraints=constraints,
        confidence=confidence,
        false_positive_note="This is an evidence-readiness checklist, not a guarantee of dispute outcome. Processors and issuing banks decide outcomes.",
    )


def classify_urgency(days_until_due: int | None, deadline_buffer: int) -> str:
    if days_until_due is None:
        return "unknown"
    if days_until_due < 0:
        return "expired"
    if days_until_due <= deadline_buffer:
        return "critical"
    if days_until_due <= 5:
        return "due_soon"
    return "normal"


def recommend_action(dispute: NormalizedDispute, urgency: str, missing: list[str], evidence_score: int) -> str:
    if urgency == "expired":
        return "Record as deadline risk, save all documents, and review prevention controls for future disputes."
    if missing:
        first = ", ".join(missing[:3])
        return f"Collect missing evidence first: {first}. Then compile a concise packet for {dispute.processor.title()}."
    if evidence_score >= 75:
        return "Compile the evidence packet now, review for concise factual language, and submit before the deadline."
    return "Review extracted fields and add stronger transaction, fulfillment, and customer communication evidence."


def packet_sections(reason: str) -> list[str]:
    base = ["Case summary", "Transaction receipt", "Customer/order identity", "Timeline", "Merchant statement"]
    if reason in {"product_not_received", "not_received"}:
        return base + ["Tracking and delivery proof", "Shipping address match", "Customer communication"]
    if reason == "fraud":
        return base + ["Authorization signals", "Device/IP/AVS notes", "Fulfillment or usage proof"]
    if reason == "not_as_described":
        return base + ["Product description at purchase", "Return/refund policy", "Resolution attempts"]
    if reason == "credit_not_processed":
        return base + ["Refund status", "Refund receipt or explanation", "Customer communication"]
    return base + ["Relevant fulfillment evidence", "Customer communication", "Policy notes"]


def build_what_if(analyses: list[DisputeAnalysis]) -> dict[str, Any]:
    if not analyses:
        return {}
    critical_now = sum(1 for item in analyses if item.urgency == "critical")
    ready_now = sum(1 for item in analyses if item.win_readiness == "ready_to_compile")
    missing_tracking = sum(1 for item in analyses if "tracking_number" in item.missing_evidence)
    return {
        "deadline_buffer_plus_2_days": "More disputes become critical if the team wants a 2-day internal review buffer.",
        "add_tracking_evidence": f"Adding tracking evidence would directly improve {missing_tracking} dispute(s).",
        "ready_packet_count": ready_now,
        "critical_deadline_count": critical_now,
        "decision_impact": "Prioritize critical deadline cases first, then high-amount cases with small evidence gaps.",
    }


def analysis_to_dict(item: DisputeAnalysis) -> dict[str, Any]:
    data = asdict(item)
    data["dispute"] = asdict(item.dispute)
    return data


def render_markdown(analyses: list[DisputeAnalysis], processor_summary: dict[str, dict[str, Any]]) -> str:
    lines = [
        "# Chargeback Evidence Desk Report",
        "",
        "This report is an operational evidence checklist, not legal advice and not a guarantee of dispute outcome.",
        "",
        "## Executive Summary",
        f"- Disputes analyzed: {len(analyses)}",
        f"- Critical deadline cases: {sum(1 for item in analyses if item.urgency == 'critical')}",
        f"- Total amount at issue: {sum(item.dispute.amount for item in analyses):.2f}",
        "",
        "## Processor Summary",
    ]
    for processor, summary in processor_summary.items():
        lines.append(f"- {processor.title()}: {summary['count']} disputes, {summary['amount']:.2f} at issue, {summary['critical']} critical")
    lines.extend(["", "## Priority Queue"])
    for idx, item in enumerate(analyses, 1):
        dispute = item.dispute
        lines.extend(
            [
                f"### {idx}. {dispute.dispute_id} - {dispute.processor.title()} - {dispute.amount:.2f} {dispute.currency}",
                f"- Reason: {dispute.reason}",
                f"- Due: {dispute.due_date or 'unknown'} ({item.urgency})",
                f"- Evidence readiness: {item.evidence_score}/100 ({item.win_readiness})",
                f"- Confidence: {item.confidence}",
                f"- Missing evidence: {', '.join(item.missing_evidence) if item.missing_evidence else 'none'}",
                f"- Next action: {item.recommended_action}",
                f"- Packet sections: {', '.join(item.suggested_packet_sections)}",
                "",
            ]
        )
    return "\n".join(lines)


def load_sample(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    disputes, metadata = parse_csv(text)
    return {"disputes": [asdict(item) for item in disputes], "metadata": metadata}


def save_outputs(report: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "chargeback-evidence-report.json"
    md_path = output_dir / "chargeback-evidence-report.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(report.get("markdown_report", ""), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
