# Banking Support Agent
### IITM Pravartak — Application Programming in Agentic AI
### Capstone Project

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
| 6 | Memory & Planning | ✅ Done  |
| 7 | Adaptive Behaviour | ⬜ Pending |
| 8 | Deployment | ⬜ Pending |
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

### Phase 6: Chat History stored across sessions

Whenever a user logs in the session history is stored and is greeted with during next login. Also ticket info is also stored across sessions 

