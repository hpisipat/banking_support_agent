# Banking Support Agent
### IITM Pravartak — Application Programming in Agentic AI
### Capstone Project

A non-transactional AI-powered banking support agent built 
using Python, LangChain, and OpenAI GPT-4o.

## Features
1. Document Checklist & Process Guide
2. Loan / Credit Card Eligibility Checker
3. FAQ / Policy Answers (RAG based)
4. Complaint Logging & Status Tracking
5. Branch / ATM Locator
6. Account Inquiry (Mock Data)

## Personas
- New Customer
- Existing Customer
- Banker / Staff

## Tech Stack
- Python 3.10+
- LangChain
- OpenAI GPT-4o
- FAISS Vector Store
- FastAPI + Streamlit

## Phase-wise Development
| Phase | Description | Status |
|---|---|---|
| 1 | Problem Definition | ✅ Done |
| 2 | Basic Rule-Based Agent | ✅ Done |
| 3 | LLM Integration | 🔄 In Progress |
| 4 | RAG / Knowledge Retrieval | ⬜ Pending |
| 5 | Tool Usage | ⬜ Pending |
| 6 | Memory & Planning | ⬜ Pending |
| 7 | Adaptive Behaviour | ⬜ Pending |
| 8 | Deployment | ⬜ Pending |
| 9 | Evaluation | ⬜ Pending |

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env
# Add your OpenAI API key to .env
python baseline_agent.py
```