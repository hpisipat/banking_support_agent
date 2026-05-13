import json
import os
import sys
from datetime import datetime

from langchain_core.messages import AIMessage, HumanMessage

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from core.guardrails import check_guardrails
from core.router import detect_intent
from llm_agent_runner import route_to_tool
from observability.logger import generate_session_id, scrub_pii

try:
    from core.llm_agent import detect_intent_llm
except Exception:
    detect_intent_llm = None


CASES_FILE = os.path.join(PROJECT_ROOT, "tests", "phase9_eval_cases.json")
REPORT_DIR = os.path.join(PROJECT_ROOT, "tests", "reports")


def load_cases():
    with open(CASES_FILE, "r", encoding="utf-8") as handle:
        return json.load(handle)


def contains_any(text, keywords):
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def evaluate_case(case):
    session_id = generate_session_id()
    persona = case["persona"]
    user_message = case["user_message"]
    chat_history = []

    blocked, block_message = check_guardrails(user_message)
    expected_blocked = case["expected_blocked"]

    actual_intent = "blocked" if blocked else "unknown"
    intent_source = "guardrail"

    if not blocked:
        if detect_intent_llm is not None:
            try:
                actual_intent = detect_intent_llm(user_message)
                intent_source = "llm"
            except Exception:
                actual_intent = detect_intent(user_message)
                intent_source = "fallback"
        else:
            actual_intent = detect_intent(user_message)
            intent_source = "fallback"

    if blocked:
        response = block_message or ""
    else:
        response = route_to_tool(
            intent=actual_intent,
            user_message=user_message,
            persona=persona,
            session_id=session_id,
            chat_history=chat_history,
            memory_context="",
            session_data={"products_enquired": [], "last_intent": "unknown", "ticket_ids": []},
            memory={},
            feedback_style="default",
            user_id=f"phase9-{case['id'].lower()}"
        )
        chat_history.append(HumanMessage(content=user_message))
        chat_history.append(AIMessage(content=response))

    checks = {
        "blocked_match": blocked == expected_blocked,
        "intent_match": actual_intent == case["expected_intent"],
        "keyword_match": contains_any(response, case["keywords_any"])
    }

    passed = all(checks.values())

    return {
        "id": case["id"],
        "description": case["description"],
        "persona": persona,
        "user_message": user_message,
        "expected_intent": case["expected_intent"],
        "actual_intent": actual_intent,
        "intent_source": intent_source,
        "expected_blocked": expected_blocked,
        "actual_blocked": blocked,
        "checks": checks,
        "passed": passed,
        "response_preview": response[:500]
    }


def run_pii_audit():
    sample = (
        "Customer CUST-10234 mobile 9876543210 email ravi@gmail.com "
        "account 123456789012 Aadhaar 1234 5678 9012 PAN ABCDE1234F"
    )
    scrubbed = scrub_pii(sample)
    checks = {
        "mobile_redacted": "[MOBILE_REDACTED]" in scrubbed,
        "email_redacted": "[EMAIL_REDACTED]" in scrubbed,
        "account_redacted": "[ACCOUNT_REDACTED]" in scrubbed,
        "aadhaar_redacted": "[AADHAAR_REDACTED]" in scrubbed,
        "pan_redacted": "[PAN_REDACTED]" in scrubbed,
        "customer_id_redacted": "[CUSTOMER_ID_REDACTED]" in scrubbed
    }
    return {
        "sample": sample,
        "scrubbed": scrubbed,
        "checks": checks,
        "passed": all(checks.values())
    }


def build_summary(results, pii_audit):
    total = len(results)
    passed = sum(1 for result in results if result["passed"])
    blocked_accuracy = sum(1 for result in results if result["checks"]["blocked_match"]) / total
    intent_accuracy = sum(1 for result in results if result["checks"]["intent_match"]) / total
    keyword_accuracy = sum(1 for result in results if result["checks"]["keyword_match"]) / total

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_cases": total,
        "cases_passed": passed,
        "overall_pass_rate": round(passed / total, 3),
        "blocked_accuracy": round(blocked_accuracy, 3),
        "intent_accuracy": round(intent_accuracy, 3),
        "response_keyword_accuracy": round(keyword_accuracy, 3),
        "pii_audit_passed": pii_audit["passed"]
    }


def write_report(summary, results, pii_audit):
    os.makedirs(REPORT_DIR, exist_ok=True)

    json_path = os.path.join(REPORT_DIR, "phase9_report.json")
    md_path = os.path.join(REPORT_DIR, "phase9_report.md")

    payload = {
        "summary": summary,
        "results": results,
        "pii_audit": pii_audit
    }

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    lines = [
        "# Phase 9 Evaluation Report",
        "",
        f"Generated at: {summary['generated_at']}",
        "",
        "## Summary",
        f"- Total cases: {summary['total_cases']}",
        f"- Cases passed: {summary['cases_passed']}",
        f"- Overall pass rate: {summary['overall_pass_rate']}",
        f"- Guardrail accuracy: {summary['blocked_accuracy']}",
        f"- Intent accuracy: {summary['intent_accuracy']}",
        f"- Response keyword accuracy: {summary['response_keyword_accuracy']}",
        f"- PII audit passed: {summary['pii_audit_passed']}",
        "",
        "## Case Results"
    ]

    for result in results:
        lines.extend([
            f"### {result['id']} - {'PASS' if result['passed'] else 'FAIL'}",
            f"- Description: {result['description']}",
            f"- Persona: {result['persona']}",
            f"- Expected intent: {result['expected_intent']}",
            f"- Actual intent: {result['actual_intent']} ({result['intent_source']})",
            f"- Expected blocked: {result['expected_blocked']}",
            f"- Actual blocked: {result['actual_blocked']}",
            f"- Checks: {result['checks']}",
            f"- Response preview: {result['response_preview']}",
            ""
        ])

    lines.extend([
        "## PII Audit",
        f"- Checks: {pii_audit['checks']}",
        f"- Scrubbed sample: {pii_audit['scrubbed']}",
        ""
    ])

    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    return json_path, md_path


def main():
    cases = load_cases()
    results = [evaluate_case(case) for case in cases]
    pii_audit = run_pii_audit()
    summary = build_summary(results, pii_audit)
    json_path, md_path = write_report(summary, results, pii_audit)

    print("=" * 60)
    print("Phase 9 - Evaluation & Review")
    print("=" * 60)
    print(f"Cases passed           : {summary['cases_passed']} / {summary['total_cases']}")
    print(f"Overall pass rate      : {summary['overall_pass_rate']}")
    print(f"Guardrail accuracy     : {summary['blocked_accuracy']}")
    print(f"Intent accuracy        : {summary['intent_accuracy']}")
    print(f"Response keyword match : {summary['response_keyword_accuracy']}")
    print(f"PII audit passed       : {summary['pii_audit_passed']}")
    print(f"JSON report            : {json_path}")
    print(f"Markdown report        : {md_path}")


if __name__ == "__main__":
    main()
