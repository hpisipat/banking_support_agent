# Banking Support Agent
### IITM Pravartak — Application Programming in Agentic AI
### Capstone Project

Project GitHub URL - https://github.com/hpisipat/banking_support_agent

A non-transactional AI-powered banking support agent built
using Python, LangChain, and OpenAI GPT-4o. Serves 3 user
personas across 6 feature areas with production-grade
guardrails, async logging, PII protection, and RAG-based
FAQ retrieval.

---

## Features
1. Document Checklist & Process Guide
2. Loan / Credit Card Eligibility Checker
3. FAQ / Policy Answers (RAG based)
4. Complaint Logging & Status Tracking
5. Branch / ATM Locator
6. Account Inquiry (Mock Data)

---

## Personas
| Persona | Who | Use Case |
|---|---|---|
| New Customer | No account yet | Account opening, products, eligibility |
| Existing Customer | Has an account | Support, complaints, account info |
| Banker / Staff | Bank employee | Customer lookup, policy answers |

---

## Tech Stack
- Python 3.10+
- LangChain + LangChain Community
- OpenAI GPT-4o (intent detection + response)
- OpenAI text-embedding-3-small (FAQ embeddings)
- FAISS (vector store)
- FastAPI + Streamlit (Phase 8)
- Docker + docker-compose (Packaging)
- httpx (corporate proxy bypass)

---

## Project Structure
banking_agent/
├── core/               # Agent brain — router, guardrails, LLM
├── data/               # Mock data + FAQ knowledge base
├── tools/              # Feature tools (FAQ RAG implemented)
├── observability/      # Async logging, PII scrubbing
├── tests/              # Prompt comparison, connection tests
├── docs/               # Project documentation
├── baseline_agent.py   # Phase 2 — rule-based agent
├── llm_agent_runner.py # Phase 3/4 — LLM powered agent
└── ingest.py           # Phase 4 — builds FAISS index

---

## Setup
```bash
# Install dependencies
pip install -r requirements.txt --no-cache-dir

# Add OpenAI API key to .env
cp .env.example .env

# Build FAQ index — run once
python ingest.py

# Run Phase 2 baseline agent
python baseline_agent.py

# Run Phase 3/4 LLM agent
python llm_agent_runner.py
```

---

## Phase-wise Development

| Phase | Description | Status |
|---|---|---|
| 1 | Problem Definition | ✅ Done |
| 2 | Basic Rule-Based Agent | ✅ Done |
| 3 | LLM Integration | ✅ Done |
| 4 | RAG / Knowledge Retrieval | ✅ Done |
| 5 | Tool Usage |  ✅ Done   |
| 6 | Memory & Planning | ⚠️ Partial (Planning deferred) |
| 7 | Adaptive Behaviour | ✅ Done |
| 8 | Deployment | ✅ Done |
| 9 | Evaluation | ⬜ Pending |

---

### Phase 1 — Problem Definition ✅
- Defined 3 user personas and 6 features
- Designed guardrails, logging strategy, success criteria
- Produced 12-section requirements document + 2-page summary

---

### Phase 2 — Basic Rule-Based Agent ✅

**What was built:**
- Keyword-based intent router — 6 intents
- Guardrails — blocks transactions, out-of-scope, abusive language
- Async JSON logging with PII scrubbing
- Mock data — 5 customers, 5 branches, 5 ATMs, 4 tickets

**Flow:**
User message
│
▼
Keyword matching
│
▼
Returns intent
│
▼
Stub response

**Documented Limitations:**
1. Exact keyword matching only — fails on synonyms
2. Order-dependent keyword conflicts — not scalable
3. No context understanding across turns
4. Stub responses only — no real answers
5. No natural language understanding
6. Binary responses — "I don't understand" with no follow-up

---

### Phase 3 — LLM Integration ✅

**What changed from Phase 2:**
- Replaced keyword router with GPT-4o intent detection
- Agent understands informal language ("txn", "passbook", "la bhai")
- Persona-aware system prompt — different behaviour per user type
- Multi-turn conversation memory across turns
- 3-retry limit on all tool calls with graceful fallback
- Keyword router kept as fallback if LLM intent fails

**Flow:**
User message
│
▼
System prompt + conversation
history sent to GPT-4o
│
▼
LLM understands intent
AND generates real answer
│
▼
Smart, contextual response

**Prompt Strategy Comparison:**

| Strategy | Banking Focus | Persona Aware | Structured |
|---|---|---|---|
| Zero Shot | ❌ Generic | ❌ No | ❌ No |
| System Prompt | ✅ Yes | ✅ Yes | ✅ Yes |
| Few Shot | ✅ Best | ✅ Yes | ✅ Best |

**Selected:** Few-shot + System Prompt

**Remaining limitation:** LLM answers from training data
— can hallucinate bank-specific details like branch addresses

---

### Phase 4 — RAG Knowledge Retrieval ✅

**What changed from Phase 3:**
- Built FAQ knowledge base (`data/faq_banking.txt`) — 6 sections, 30+ Q&As
- Ingestion pipeline (`ingest.py`) — chunks FAQ doc, creates OpenAI
  embeddings, saves FAISS index to disk
- FAQ RAG tool (`tools/faq_tool.py`) — retrieves top 3 chunks,
  GPT-4o answers ONLY from retrieved context
- FAISS index pre-built — fast load at runtime, multi-user safe
- Upgraded logger to async QueueHandler — thread-safe, non-blocking

**Phase 3 vs Phase 4 — FAQ answers:**

| Query | Phase 3 | Phase 4 |
|---|---|---|
| "What is minimum balance?" | Generic GPT-4o answer | Exact answer from faq_banking.txt |
| Question not in FAQ | LLM makes up an answer | "I don't have that information" |
| Branch locations | Hallucinates placeholder data | Hallucinates (fixed in Phase 5) |

**RAG Architecture:**
faq_banking.txt
│
▼ ingest.py (run once)
Split into chunks → OpenAI embeddings → FAISS index (saved to disk)
At query time:
User question → embed → search FAISS → top 3 chunks
│
▼
GPT-4o answers from chunks only — grounded, no hallucination

**Remaining limitation:** Branch, account, eligibility,
complaint tools still use generic LLM — fixed in Phase 5

---

## Guardrails & Safety

| Guardrail | Trigger | Action |
|---|---|---|
| Transaction block | transfer, pay, reset PIN | Blocked + WARNING logged |
| Out of scope | weather, cricket, movies | Redirected + INFO logged |
| Abusive language | offensive words | Empathetic redirect |
| Auth failure x3 | wrong customer ID | Session locked |
| Tool failure x3 | 3 consecutive errors | Graceful failure + ERROR |

---

## Logging

- **Pattern:** QueueHandler → Queue → QueueListener → FileHandler
- **File:** `logs/agent.log` — single unified file, append mode
- **PII scrubbed:** mobile, email, account number, Aadhaar, PAN
- **Thread-safe:** multiple users log simultaneously without corruption
- **Levels:** INFO (normal) / WARNING (guardrails) / ERROR (failures)

---

## Key Engineering Decisions

| Decision | Choice | Reason |
|---|---|---|
| LLM provider | OpenAI GPT-4o | Existing paid account |
| Embeddings | text-embedding-3-small | Cost efficient, good quality |
| Vector store | FAISS (local) | No extra API, fast, free |
| Proxy bypass | httpx.Client(proxy=None) | Corporate Oracle proxy blocks API |
| Log pattern | Async QueueHandler | Thread-safe, non-blocking |
| FAQ strategy | RAG not hardcoded | Scalable, updatable, no hallucination |

### Phase 5: Tools

In llm_agent_runner.py — the route_to_tool() function is where all 6 are connected

Distance Calculation:
─────────────────────────────────────────────
Algorithm  : OpenRouteService (ORS) Road Distance API
Fallback   : Haversine straight-line formula
API Key    : Set ORS_API_KEY in .env to enable

Behaviour:
- ORS_API_KEY set + internet access  → Real road distance ✅
- ORS_API_KEY set + VPN/blocked      → Auto fallback to Haversine ✅
- ORS_API_KEY not set                → Haversine directly ✅

Note: ORS API blocked on Oracle corporate VPN.
      Haversine fallback ensures agent always works
      regardless of network environment.
      Distances shown are approximate when using Haversine.

### Phase 6 — Memory & Planning ✅ (Partial)

**Planned scope:**
```
Part 1 — Long-term Memory     ✅ Done
Part 2 — Planning             ❌ Not done
Part 3 — Memory reset rules   ✅ Partially done (sensitive data cleared)
```

**Part 1 — Long-term Memory (Done):**
- Long-term memory persisted across sessions (`memory/user_memory.json`)
- Returning users greeted by name with their previous enquiry history
- Products enquired and preferred area extracted from chat history automatically
- Ticket IDs tracked per session and recalled in future sessions
- Ticket details persisted to disk (`data/session_tickets_store.json`) — survives restarts

**Part 2 — Planning (Not done — deferred to Phase 7):**

Currently the agent detects a single intent per message. If a user asks two things in one message, only the first intent is answered.

Example of what planning would enable:
```
User: "I want to open an account and also check loan eligibility"
        │
        ▼
Agent plans two steps:
  Step 1 → document_tool    (account opening docs)
  Step 2 → eligibility_tool (loan eligibility)
        │
        ▼
Executes both and presents a combined response
```

Deferred to future enhancement:
- Multi-step planning (detect multiple intents per message)
- Current implementation handles one intent per turn
- LLM naturally handles follow-up questions via `chat_history`
- Full planning implementation would use LangChain `AgentExecutor`
  with registered tools — planned for production version

**Part 3 — Memory reset rules (Partially done):**
- Sensitive data (customer ID, mobile, email, account number) never persisted — cleared after every session
- Non-sensitive data (products enquired, preferred area, ticket IDs) retained across sessions
- Full reset rules (e.g. expiry, user-triggered clear) not yet implemented

**Ticket Management (implemented in Phase 6):**
- Agent asks for problem description before logging a ticket — does not log on vague requests
- Full ticket details shown: Ticket ID, description, category, priority, status, logged date, ETA
- Auto-priority assignment based on complaint keywords:

| Category | Keywords | Priority | SLA |
|---|---|---|---|
| Unauthorized Transaction | unauthorized, fraud | Urgent | 4 hours |
| Card Cloned / Fraud | cloned, skimmed, stolen card | Urgent | 4 hours |
| Failed Transaction | failed, deducted, reversed | High | 24 hours |
| Card Swallowed | swallowed, card stuck | High | 24 hours |
| Wrong Charges | wrong charge, extra charge | Medium | 48 hours |
| Net Banking Issue | net banking, upi, login | Medium | 48 hours |
| Staff Misbehaviour | staff, rude, misbehave | Medium | 72 hours |
| Account Opening Delay | account opening, delay | Low | 5 days |
| General | (all other) | Low | 5 days |

- Only bankers can update ticket priority — customers shown branch visit message

**Memory Architecture:**
```
Session ends
│
▼
save_session_memory()
│
├── products_enquired, preferred_area, ticket_ids → persisted
└── customer_id, mobile, email → cleared (never saved)

Next session starts
│
▼
load_memory() → build_memory_context() → injected into system prompt
│
▼
LLM greets returning user naturally with their history
```

**Files changed:**
- `memory/memory_manager.py` — NEW: load, save, build context, PII guard
- `memory/__init__.py` — NEW
- `llm_agent_runner.py` — MODIFIED: memory load/save, returning-user greeting, ticket/product tracking
- `tools/complaint_tool.py` — MODIFIED: ticket persistence, banker-only priority, full details display

---

### Phase 7 — Adaptive Behaviour ✅

**What was built:**
- Session-level feedback collected once per session — just before goodbye
- Follow-up question on negative feedback — captures what specifically wasn't helpful
- Feedback persisted to disk (`data/feedback.json`) — survives restarts and spans sessions
- Style computed from feedback history — activates only after 3+ sessions
- All 6 tools adapted — style guidance injected into every tool's system prompt
- Recent user comments injected into prompts — LLM has specific context, not just generic hints
- Additive-only principle — base response always intact, feedback only adds context on top

**Feedback Flow:**
```
Session ends
│
▼
"How was your experience today? 👍 yes / 👎 no"
│
├── 👍 yes → saves "positive" to feedback.json
│
└── 👎 no  → "What could we have done better?"
             saves "negative" + free-text comment to feedback.json
```

**Style Adaptation (kicks in after 3+ sessions):**

| Negative Rate | Style | What changes |
|---|---|---|
| < 20% | concise | LLM notes users prefer direct answers — leads with key point |
| 20–60% | balanced | LLM structures response clearly with bullet points |
| ≥ 60% | detailed | LLM adds example, plain language, clarification offer at end |
| < 3 sessions | default | No change — not enough data yet |

**How style is injected (additive only):**
```
feedback.json → get_feedback_style(persona, "session")
      │
      ▼
get_style_guidance(style, persona)
      │
      ├── Pulls recent negative comments from feedback.json
      ├── Builds additive prompt block
      └── Injected into system prompt of every tool
             faq_tool / document_tool / eligibility_tool /
             locator_tool / complaint_tool / account_tool
```

**Design Principles:**
- Feedback is **additive only** — base information never removed or shortened
- Each persona's feedback is stored separately — one user's preference does not affect others
- Comments stored with timestamp — most recent 3 shown to LLM
- Style never overrides guardrails or tool logic

**Files changed:**
- `tools/feedback_tool.py` — NEW: `save_feedback()`, `get_feedback_style()`, `get_style_guidance()`, `get_recent_comments()`
- `llm_agent_runner.py` — MODIFIED: session-level feedback collection, follow-up on negative, style lookup per session
- `core/llm_agent.py` — MODIFIED: `build_system_prompt()` injects style guidance
- `tools/faq_tool.py` — MODIFIED: accepts and applies `feedback_style`
- `tools/document_tool.py` — MODIFIED: accepts and applies `feedback_style`
- `tools/eligibility_tool.py` — MODIFIED: accepts and applies `feedback_style`
- `tools/locator_tool.py` — MODIFIED: accepts and applies `feedback_style`
- `tools/complaint_tool.py` — MODIFIED: accepts and applies `feedback_style`
- `tools/account_tool.py` — MODIFIED: accepts and applies `feedback_style`

---

### Phase 8 - Deployment & Packaging

**Deployment surface added:**
- `api_app.py` - FastAPI backend exposing health, session, chat, end-session, and feedback endpoints
- `streamlit_app.py` - Streamlit web UI for persona selection, chat, and feedback submission
- `core/session_service.py` - reusable session manager that wraps the existing agent logic for web usage
- `Dockerfile.api` - packaging for the FastAPI backend
- `Dockerfile.ui` - packaging for the Streamlit frontend
- `docker-compose.yml` - packaged startup for both services together
- `.dockerignore` - excludes runtime artifacts from Docker builds

**Run locally:**
```bash
# Terminal 1 - FastAPI backend
uvicorn api_app:app --reload

# Terminal 2 - Streamlit frontend
streamlit run streamlit_app.py
```

**Default URLs:**
- FastAPI docs: `http://127.0.0.1:8000/docs`
- Streamlit UI: `http://127.0.0.1:8501`

**API endpoints:**
- `GET /health`
- `POST /sessions`
- `POST /sessions/{session_id}/messages`
- `POST /sessions/{session_id}/end`
- `POST /sessions/{session_id}/feedback`

**Multi-user support:**
- Session state is persisted in SQLite (`data/banking_agent.db`) instead of in-memory Python only
- Long-term memory and feedback are scoped by `user_id + persona`
- Streamlit now asks for a `User ID` before starting a session
- Multiple users can use the same deployed app without sharing conversation memory or feedback preferences

---

## Packaging

**Packaging files added:**
- `Dockerfile.api` - container image for the FastAPI backend
- `Dockerfile.ui` - container image for the Streamlit frontend
- `docker-compose.yml` - launches API and UI together
- `.dockerignore` - keeps runtime artifacts out of Docker build context

**Run with Docker Compose:**
```bash
# Build and start both services
docker compose up --build
```

**Packaged URLs:**
- FastAPI docs: `http://127.0.0.1:8000/docs`
- Streamlit UI: `http://127.0.0.1:8501`

**How it works:**
- `api` service runs `uvicorn api_app:app`
- `ui` service runs `streamlit run streamlit_app.py`
- Streamlit talks to the API using `BANKING_AGENT_API_URL=http://api:8000`
- `data/` and `logs/` are mounted so SQLite and logs persist outside the containers

**Packaging notes:**
- Keep `faiss_index/` in the repo so the FAQ service works immediately inside the containers
- Add your `OPENAI_API_KEY` to `.env` before running `docker compose up --build`

---

### Phase 9 - Evaluation & Review

**Evaluation artifacts added:**
- `tests/phase9_eval_cases.json` - 10-query evaluation suite across personas, tools, and guardrails
- `tests/evaluate_phase9.py` - runnable evaluation harness that scores outcomes and writes reports

**What Phase 9 measures:**
- Guardrail accuracy (transactional, out-of-scope, abusive queries)
- Intent accuracy
- Response quality via keyword-based expected-output checks
- PII redaction audit using the logger scrubber

**Run Phase 9 evaluation:**
```bash
python tests/evaluate_phase9.py
```

**Generated reports:**
- `tests/reports/phase9_report.json`
- `tests/reports/phase9_report.md`
