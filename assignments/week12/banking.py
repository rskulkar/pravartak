"""
Banking & Financial Services – Intelligent Customer Resolution
Multi-Agent Workflow using CrewAI

Usage:
    python banking_crew.py                        # Gemini (default)
    python banking_crew.py --llm gemini           # Gemini only
    python banking_crew.py --llm claude           # Claude only
    python banking_crew.py --llm compare          # Both side-by-side
    python banking_crew.py --llm gemini --query "My card was declined"

Required env vars (in .env file):
    GEMINI_API_KEY=your_gemini_key
    ANTHROPIC_API_KEY=your_anthropic_key   # only needed for claude/compare
"""

import json
import re
import os
import argparse
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# ── Load .env from the same directory as this script ──────────────────────
_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path)
# ──────────────────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════
# LLM FACTORY
# ══════════════════════════════════════════════

def get_llm(provider: str) -> LLM:
    """
    Return a CrewAI native LLM for the requested provider.
    Uses CrewAI's built-in LLM class (wraps LiteLLM under the hood).
    No langchain-google-genai or langchain-anthropic needed.

    Model string format:  "gemini/gemini-1.5-flash"
                          "anthropic/claude-3-5-haiku-20241022"
    """
    if provider == "gemini":
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise EnvironmentError(
                "GEMINI_API_KEY not set.\n"
                "Add to .env:  GEMINI_API_KEY=your_key"
            )
        return LLM(
            model="gemini/gemini-1.5-flash",
            api_key=key,
            temperature=0.1,
        )

    elif provider == "claude":
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY not set.\n"
                "Add to .env:  ANTHROPIC_API_KEY=your_key"
            )
        return LLM(
            model="anthropic/claude-3-5-haiku-20241022",
            api_key=key,
            temperature=0.1,
        )

    else:
        raise ValueError(f"Unknown provider '{provider}'. Choose: gemini | claude | compare")


# ══════════════════════════════════════════════
# TOOL 1 – Intent Classifier
# ══════════════════════════════════════════════

class IntentInput(BaseModel):
    message: str = Field(description="Raw customer message to classify")

class IntentClassifierTool(BaseTool):
    name: str = "intent_classifier"
    description: str = (
        "Classifies a customer banking message into one of 8 intent categories "
        "and extracts key entities (amounts, urgency signals). "
        "Returns structured JSON."
    )
    args_schema: type[BaseModel] = IntentInput

    def _run(self, message: str) -> str:
        msg = message.lower()

        intent = "general"
        if any(k in msg for k in [
            "fraud", "unauthorized", "didn't authorize", "did not authorize",
            "not done by me", "unknown transaction", "stolen card"
        ]):
            intent = "fraud"
        elif any(k in msg for k in [
            "suspicious login", "unknown device", "account hacked",
            "otp received", "not requested otp", "security breach", "trying to hack"
        ]):
            intent = "security"
        elif any(k in msg for k in [
            "wrong account", "wrong transfer", "wrong upi",
            "transferred to wrong", "accidentally transferred"
        ]):
            intent = "wrong_transfer"
        elif any(k in msg for k in [
            "payment failed", "transaction failed", "debited but not", "not credited",
            "salary not credited", "salary hasn't been credited",
            "money deducted", "double debit", "refund", "upi payment", "failed but money"
        ]):
            intent = "transaction"
        elif any(k in msg for k in [
            "loan", "emi", "loan application", "loan rejected",
            "personal loan", "home loan", "credit limit"
        ]):
            intent = "loan"
        elif any(k in msg for k in [
            "card blocked", "card declined", "card not working",
            "debit card", "credit card", "card issue", "atm", "pos terminal"
        ]):
            intent = "card"
        elif any(k in msg for k in [
            "balance", "statement", "account", "kyc", "ifsc", "branch"
        ]):
            intent = "account"

        urgency_keywords = [
            "urgent", "immediately", "emergency", "asap", "right now",
            "blocked", "stolen", "fraud", "unauthorized", "wrong transfer",
            "hacked", "suspicious", "unknown", "accidentally", "trying to hack", "please help"
        ]
        urgency_signal = any(k in msg for k in urgency_keywords)

        # Amount extraction — handles ₹, Rs, lakhs
        amount = None
        uni = re.search(r'₹\s*([\d,]+)', message)
        if uni:
            try:
                amount = float(uni.group(1).replace(',', ''))
            except ValueError:
                pass
        if amount is None:
            for pattern, mult in [
                (r'rs\.?\s*([\d,]+)',           1),
                (r'inr\s*([\d,]+)',             1),
                (r'([\d,]+)\s*(?:rupees?|rs)',  1),
                (r'([\d.]+)\s*lakhs?',     100000),
            ]:
                m = re.search(pattern, msg)
                if m:
                    try:
                        amount = float(m.group(1).replace(',', '')) * mult
                        break
                    except ValueError:
                        pass

        return json.dumps({
            "intent": intent,
            "urgency_signal": urgency_signal,
            "entities": {"amount": amount, "timestamp": datetime.now().isoformat()},
            "raw_message": message
        }, indent=2)


# ══════════════════════════════════════════════
# TOOL 2 – RBI Policy Engine
# ══════════════════════════════════════════════

class PolicyInput(BaseModel):
    classification_json: str = Field(description="JSON string from intent classifier")

class RBIPolicyEngineTool(BaseTool):
    name: str = "rbi_policy_engine"
    description: str = (
        "Applies RBI guidelines to a classified customer intent. "
        "Returns resolution path, auto-resolvability, risk flags, and SLA."
    )
    args_schema: type[BaseModel] = PolicyInput

    def _run(self, classification_json: str) -> str:
        try:
            data = json.loads(classification_json)
        except json.JSONDecodeError:
            m = re.search(r'\{.*\}', classification_json, re.DOTALL)
            data = json.loads(m.group()) if m else {}

        intent = data.get("intent", "general")
        urgency = data.get("urgency_signal", False)
        amount  = data.get("entities", {}).get("amount")

        db = {
            "fraud": {
                "policy_name": "RBI Master Direction – Limiting Liability of Customers (2017)",
                "policy_summary": "Per RBI/2017-18/15: ZERO liability if reported in 3 days. Reversal within 10 working days.",
                "auto_resolvable": False,
                "resolution_path": "Block card → File fraud complaint → Initiate chargeback within 10 days",
                "risk_flags": ["high_financial_risk", "regulatory_liability", "mandatory_escalation"],
                "sla_hours": 24
            },
            "security": {
                "policy_name": "RBI Cybersecurity Framework (2016) + IT Act 2000",
                "policy_summary": "Account freeze within 2 hrs. CERT-In notification within 6 hrs.",
                "auto_resolvable": False,
                "resolution_path": "Freeze account → Force logout → Re-KYC → Notify CERT-In",
                "risk_flags": ["account_takeover_risk", "regulatory_reporting_required", "mandatory_escalation"],
                "sla_hours": 2
            },
            "wrong_transfer": {
                "policy_name": "RBI Payment & Settlement Systems Act 2007 + NPCI UPI Dispute Guidelines",
                "policy_summary": "Reversal initiated within 48 hrs. Completed in 7 working days via NPCI DMS.",
                "auto_resolvable": False,
                "resolution_path": "Log dispute → Contact beneficiary bank → NPCI DMS within 48 hrs",
                "risk_flags": ["time_critical_reversal", "inter_bank_coordination_required"],
                "sla_hours": 48
            },
            "transaction": {
                "policy_name": "RBI Circular on Failed Transactions (DPSS.CO.PD.No.629/02.01.014/2019-20)",
                "policy_summary": "Auto-reversal: UPI T+1, IMPS/NEFT T+2. Rs 100/day bank penalty for SLA breach.",
                "auto_resolvable": True,
                "resolution_path": "Check status → Verify auto-reversal → Manual credit if SLA breached",
                "risk_flags": [],
                "sla_hours": 48
            },
            "loan": {
                "policy_name": "RBI Fair Practices Code for Lenders + CIC Act 2005",
                "policy_summary": "Rejection reasons in writing. CIBIL >=700. EMI/income <=50%.",
                "auto_resolvable": True,
                "resolution_path": "Check eligibility → Explain rejection → Suggest alternatives",
                "risk_flags": [],
                "sla_hours": 168
            },
            "card": {
                "policy_name": "RBI Guidelines on Card Transactions (RBI/2021-22/74)",
                "policy_summary": "24/7 blocking. Replacement SLA: 7 days. POS decline in 12 hrs.",
                "auto_resolvable": True,
                "resolution_path": "Verify card status → Check decline code → Block/replace/re-enable",
                "risk_flags": [],
                "sla_hours": 12
            },
            "account": {
                "policy_name": "RBI KYC Master Direction 2016 + Banking Ombudsman Scheme 2006",
                "policy_summary": "Self-service balance. KYC in 30 days. Statements 10 years.",
                "auto_resolvable": True,
                "resolution_path": "Provide info / redirect to self-service channel",
                "risk_flags": [],
                "sla_hours": 72
            },
            "general": {
                "policy_name": "Banking Ombudsman Scheme 2006",
                "policy_summary": "General queries resolved within 5 working days.",
                "auto_resolvable": True,
                "resolution_path": "Provide information or redirect to appropriate channel",
                "risk_flags": [],
                "sla_hours": 120
            }
        }

        p = dict(db.get(intent, db["general"]))
        p["risk_flags"] = list(p["risk_flags"])

        if amount and amount >= 100000:
            if "high_value_transaction" not in p["risk_flags"]:
                p["risk_flags"].append("high_value_transaction")
            if intent not in ("fraud", "security", "wrong_transfer"):
                p["auto_resolvable"] = False

        return json.dumps({
            "intent": intent, "urgency_signal": urgency, "amount": amount,
            "policy_name": p["policy_name"], "policy_summary": p["policy_summary"],
            "auto_resolvable": p["auto_resolvable"], "resolution_path": p["resolution_path"],
            "risk_flags": p["risk_flags"], "sla_hours": p["sla_hours"],
            "raw_message": data.get("raw_message", "")
        }, indent=2)


# ══════════════════════════════════════════════
# TOOL 3 – Response Drafter
# ══════════════════════════════════════════════

class DraftInput(BaseModel):
    policy_json: str = Field(description="JSON string from RBI policy engine")

class ResponseDraftingTool(BaseTool):
    name: str = "response_drafter"
    description: str = "Drafts customer-facing responses for auto-resolvable queries only."
    args_schema: type[BaseModel] = DraftInput

    def _run(self, policy_json: str) -> str:
        try:
            data = json.loads(policy_json)
        except json.JSONDecodeError:
            m = re.search(r'\{.*\}', policy_json, re.DOTALL)
            data = json.loads(m.group()) if m else {}

        if not data.get("auto_resolvable"):
            return json.dumps({"draft_complete": False, "note": "Skipped — not auto-resolvable"})

        intent = data.get("intent", "general")
        sla    = data.get("sla_hours", 120)
        amount = data.get("amount")
        rpath  = data.get("resolution_path", "")

        tpl = {
            "transaction": {
                "greeting": "Thank you for reaching out. We understand how concerning payment issues can be.",
                "body": (
                    f"We have logged your concern regarding the transaction"
                    f"{f' of Rs {amount:,.0f}' if amount else ''}. "
                    f"Per RBI guidelines, failed transactions are auto-reversed within 1-2 working days. "
                    f"Our team will investigate: {rpath}."
                ),
                "next_steps": [
                    "Check your account statement after 24 hours for auto-reversal.",
                    "If not resolved in 2 working days, share your transaction reference number.",
                    "Track complaint under 'My Complaints' in the app."
                ]
            },
            "loan": {
                "greeting": "Thank you for your inquiry about our loan products.",
                "body": (
                    f"Per RBI Fair Practices Code: {rpath}. "
                    f"Key criteria: CIBIL >=700, EMI/income <=50%, 6 months stable income."
                ),
                "next_steps": [
                    "Log in to the app to check pre-approved loan offers.",
                    "Rejection reasons communicated in writing within 7 days.",
                    "Improve eligibility: clear dues, maintain timely EMIs for 3-6 months."
                ]
            },
            "card": {
                "greeting": "We apologize for the inconvenience caused by your card issue.",
                "body": (
                    f"Your card concern has been noted. Action: {rpath}. "
                    f"POS decline investigated within 12 hours; replacements in 7 working days."
                ),
                "next_steps": [
                    "Block card: call 1800-XXX-XXXX or App -> Cards -> Block Card.",
                    "Visit nearest branch with photo ID for a replacement.",
                    "Card re-enabled or replaced within the SLA period."
                ]
            },
            "account": {
                "greeting": "Thank you for your query.",
                "body": f"For account queries: {rpath}. Statements available up to 10 years.",
                "next_steps": [
                    "Balance: mobile app, SMS 'BAL' to 567676, or ATM.",
                    "Statements: App -> Accounts -> Download Statement.",
                    "KYC: visit home branch with original + self-attested documents."
                ]
            },
            "general": {
                "greeting": "Thank you for contacting us.",
                "body": f"Your query will be addressed within {sla // 24} working days. {rpath}.",
                "next_steps": [
                    "SMS/email update within 2 working days.",
                    "Urgent assistance: 1800-XXX-XXXX (24/7).",
                    "Track: App -> My Complaints."
                ]
            }
        }

        t = tpl.get(intent, tpl["general"])
        return json.dumps({
            "greeting": t["greeting"], "body": t["body"], "next_steps": t["next_steps"],
            "policy_reference": data.get("policy_name", ""),
            "sla_commitment": f"Resolution within {sla} hours ({sla // 24} working days)",
            "escalation_required": False, "draft_complete": True
        }, indent=2)


# ══════════════════════════════════════════════
# TOOL 4 – Escalation Engine
# ══════════════════════════════════════════════

class EscalationInput(BaseModel):
    all_context_json: str = Field(description="Combined JSON from all prior agents")

class EscalationEngineTool(BaseTool):
    name: str = "escalation_engine"
    description: str = (
        "Final gatekeeper. Applies hard and soft escalation rules. "
        "Returns tier, reasons, internal actions, and final customer response."
    )
    args_schema: type[BaseModel] = EscalationInput

    def _run(self, all_context_json: str) -> str:
        try:
            data = json.loads(all_context_json)
        except json.JSONDecodeError:
            m = re.search(r'\{.*\}', all_context_json, re.DOTALL)
            data = json.loads(m.group()) if m else {}

        intent   = data.get("intent", "general")
        urgency  = data.get("urgency_signal", False)
        flags    = data.get("risk_flags", [])
        auto_res = data.get("auto_resolvable", True)
        amount   = data.get("amount")
        draft    = data.get("draft_response", {})

        escalate = False; tier = None; reasons = []; actions = []

        if intent == "fraud":
            escalate = True; tier = "fraud_team"
            reasons.append("Unauthorized transaction — mandatory escalation (RBI 2017-18/15)")
            actions += ["Block card immediately", "Initiate chargeback", "File SAR"]
        elif intent == "security":
            escalate = True; tier = "fraud_team"
            reasons.append("Security breach / account takeover (RBI Cybersecurity Framework)")
            actions += ["Freeze account", "Force logout all sessions", "Notify CERT-In within 6 hrs"]
        elif intent == "wrong_transfer":
            escalate = True; tier = "l2_operations"
            reasons.append("Wrong beneficiary — 48-hr NPCI reversal SLA is time-critical")
            actions += ["Contact beneficiary bank", "Log NPCI DMS dispute"]
            if amount and amount >= 100000:
                tier = "l2_operations_legal"
                reasons.append(f"High-value Rs {amount:,.0f} — RBI Ombudsman notification may apply")
        elif amount and amount >= 100000 and not auto_res:
            escalate = True; tier = "l2_operations"
            reasons.append(f"High-value dispute Rs {amount:,.0f} — exceeds auto-resolution threshold")
            actions.append("Assign senior relationship manager")
        elif not auto_res and urgency:
            escalate = True; tier = "l1_support"
            reasons.append("Policy gap + urgency — requires human agent judgment")
            actions.append("Assign L1 agent within 30 minutes")
        elif not auto_res:
            escalate = True; tier = "l1_support_low_priority"
            reasons.append("Could not auto-resolve — requires human policy review")
            actions.append("Queue for L1 review within 4 hours")

        if escalate:
            if tier in ("fraud_team", "l2_operations_legal"):
                msg = (
                    "We have received your report and immediately flagged it for our specialist team. "
                    "A senior banking specialist will contact you within 2 hours. "
                    "Reminders: (1) Never share OTP/password, "
                    "(2) Monitor your account closely, (3) Fraud helpline: 1800-XXX-XXXX (24/7)."
                )
            elif tier == "l2_operations":
                msg = (
                    "Your case requires our operations team and has been escalated as priority. "
                    "You will be contacted within 4 hours. "
                    "Please do not initiate another transfer until this is resolved."
                )
            else:
                msg = (
                    "Your query requires a banking specialist. You will be connected shortly. "
                    "Estimated wait: 15-30 minutes. "
                    "Or visit your nearest branch with photo ID for faster resolution."
                )
        else:
            if draft.get("draft_complete"):
                msg = (f"{draft['greeting']} {draft['body']} "
                       f"Next steps: {' | '.join(draft['next_steps'])}")
            else:
                msg = "Your query has been received and will be addressed within the stipulated timeline."

        return json.dumps({
            "escalate": escalate, "escalation_tier": tier,
            "escalation_reason": reasons, "internal_actions": actions,
            "sla_hours": data.get("sla_hours", 120), "risk_flags": flags,
            "policy_reference": data.get("policy_name", ""),
            "customer_facing_response": msg,
            "resolution_status": "ESCALATED" if escalate else "AUTO_RESOLVED"
        }, indent=2)


# ══════════════════════════════════════════════
# AGENT + TASK BUILDERS
# ══════════════════════════════════════════════

def build_agents(llm):
    """Instantiate all 4 agents bound to the given LLM."""
    shared = dict(verbose=True, allow_delegation=False, max_iter=3, llm=llm)

    intent_agent = Agent(
        role="Banking Intent Classification Specialist",
        goal="Classify the customer message into 1 of 8 intents and extract amount + urgency.",
        backstory=(
            "Expert in Indian banking complaints — UPI failures, card declines, loan queries, fraud. "
            "Your classification drives every downstream decision."
        ),
        tools=[IntentClassifierTool()], **shared
    )
    policy_agent = Agent(
        role="RBI Policy & Compliance Reasoning Specialist",
        goal="Apply the correct RBI guideline; determine auto-resolvability, risk flags, and SLA.",
        backstory=(
            "Compliance expert with mastery of RBI Master Directions, NPCI guidelines, "
            "and the Banking Ombudsman Scheme."
        ),
        tools=[RBIPolicyEngineTool()], **shared
    )
    response_agent = Agent(
        role="Customer Response Drafting Specialist",
        goal="Draft empathetic, policy-compliant responses with next steps and SLA. Only when auto_resolvable=True.",
        backstory=(
            "Senior CX specialist at a leading Indian private bank. "
            "Balances regulatory accuracy with human empathy."
        ),
        tools=[ResponseDraftingTool()], **shared
    )
    escalation_agent = Agent(
        role="Risk Assessment & Escalation Decision Specialist",
        goal="Final gatekeeper: apply hard + soft escalation rules; route to correct tier.",
        backstory=(
            "Final checkpoint in the bank's resolution workflow. "
            "Never under-escalates fraud; never wastes specialist time on routine queries."
        ),
        tools=[EscalationEngineTool()], **shared
    )
    return intent_agent, policy_agent, response_agent, escalation_agent


def build_tasks(message: str, agents: tuple) -> list:
    ia, pa, ra, ea = agents
    t1 = Task(
        description=f'Classify this message:\n\n"{message}"\n\nUse intent_classifier. Return full JSON.',
        expected_output="JSON: intent, urgency_signal, entities.amount, raw_message.",
        agent=ia
    )
    t2 = Task(
        description="Pass the Task 1 JSON to rbi_policy_engine. Do not modify it.",
        expected_output="JSON: policy_name, auto_resolvable, risk_flags, sla_hours, resolution_path.",
        agent=pa, context=[t1]
    )
    t3 = Task(
        description=(
            "If auto_resolvable=True, call response_drafter with the Task 2 JSON. "
            "If False, return JSON with draft_complete: false."
        ),
        expected_output="JSON: greeting, body, next_steps, sla_commitment, draft_complete.",
        agent=ra, context=[t2]
    )
    t4 = Task(
        description=(
            "Combine all prior outputs into one JSON and call escalation_engine. "
            "Include: intent, urgency_signal, risk_flags, auto_resolvable, amount, "
            "sla_hours, policy_name, draft_response (Task 3 output)."
        ),
        expected_output="JSON: escalate, escalation_tier, escalation_reason, internal_actions, customer_facing_response, resolution_status.",
        agent=ea, context=[t1, t2, t3]
    )
    return [t1, t2, t3, t4]


# ══════════════════════════════════════════════
# CREW RUNNER
# ══════════════════════════════════════════════

def run_crew(message: str, provider: str) -> str:
    llm    = get_llm(provider)
    agents = build_agents(llm)
    tasks  = build_tasks(message, agents)
    crew   = Crew(agents=list(agents), tasks=tasks, process=Process.sequential, verbose=True)
    return str(crew.kickoff())


def run_comparison(message: str) -> dict:
    print(f"\n{'='*70}\nCOMPARISON MODE\nQuery: {message}\n{'='*70}\n")
    print("── Running Gemini ──────────────────────────────────────────────────")
    g = run_crew(message, "gemini")
    print("\n── Running Claude ──────────────────────────────────────────────────")
    c = run_crew(message, "claude")
    return {"gemini": g, "claude": c}


# ══════════════════════════════════════════════
# SAMPLE QUERIES
# ══════════════════════════════════════════════

SAMPLE_QUERIES = [
    "What is my current account balance?",
    "I want to apply for a personal loan of Rs 5 lakhs.",
    "My debit card was declined at the POS terminal today.",
    "Why was my loan application rejected last week?",
    "My UPI payment of Rs 500 failed but money was debited from my account.",
    "Someone made 3 unauthorized transactions from my credit card totalling Rs 45000 which I did not authorize.",
    "I accidentally transferred Rs 2 lakhs to the wrong account. Please help urgently!",
    "There are 5 suspicious logins to my net banking from unknown devices in the last hour.",
    "My salary of Rs 85000 hasn't been credited this month and it is already the 5th.",
    "I received an OTP I did not request — I think someone is trying to hack my account.",
]


# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Banking Multi-Agent Crew — LLM provider selector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python banking_crew.py                              # Gemini, all 10 queries
  python banking_crew.py --llm claude                # Claude, all 10 queries
  python banking_crew.py --llm compare               # Both side-by-side, all 10 queries
  python banking_crew.py --llm gemini --query "My card was declined"
        """
    )
    parser.add_argument(
        "--llm",
        choices=["gemini", "claude", "compare"],
        default="gemini",
        help="LLM backend to use (default: gemini)"
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Single query string (default: run all 10 sample queries)"
    )
    args = parser.parse_args()
    queries = [args.query] if args.query else SAMPLE_QUERIES

    for i, q in enumerate(queries, 1):
        print(f"\n{'#'*70}\nTEST CASE {i:02d}\n{'#'*70}")
        if args.llm == "compare":
            results = run_comparison(q)
            print(f"\n{'═'*70}")
            print(f"GEMINI [{q[:60]}...]:\n{results['gemini']}")
            print(f"\nCLAUDE [{q[:60]}...]:\n{results['claude']}")
            print("═"*70)
        else:
            result = run_crew(q, args.llm)
            print(f"\nFINAL OUTPUT [{args.llm.upper()}]:\n{result}\n")