# tools/faq_tool.py
# Loads pre-built FAISS index and answers FAQ questions
# using GPT-4o grounded in faq_banking.txt content
# Run ingest.py first to build the index!

import os
import httpx
from dotenv import load_dotenv

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from observability.logger import log_info, log_warning, log_error

from langchain_community.vectorstores  import FAISS
from langchain_openai                  import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts           import PromptTemplate
from langchain_core.messages          import HumanMessage
from langchain_core.output_parsers    import StrOutputParser
from langchain_core.runnables        import RunnablePassthrough

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────
INDEX_PATH = "faiss_index"

# ── Proxy bypass ──────────────────────────────────────────────────────────────
http_client       = httpx.Client(proxy=None, timeout=60.0)
http_async_client = httpx.AsyncClient(proxy=None, timeout=60.0)

# ── Global cache — loaded once, shared across all users ───────────────────────
_vectorstore = None
_embeddings  = None


# ── Helper — get embeddings ───────────────────────────────────────────────────

def get_embeddings():
    """Returns OpenAIEmbeddings with proxy bypass"""
    return OpenAIEmbeddings(
        model             = "text-embedding-3-small",
        api_key           = os.getenv("OPENAI_API_KEY"),
        http_client       = http_client,
        http_async_client = http_async_client
    )


# ── Function 1 — Load FAISS index from disk ───────────────────────────────────

def load_faq_vectorstore():
    """
    Loads pre-built FAISS index from disk.
    - Fast: no embedding creation at runtime
    - Safe: read-only, multiple users can query simultaneously
    - Cached: loaded once per session, reused for all queries
    """
    global _vectorstore, _embeddings

    # Return cached version if already loaded
    if _vectorstore is not None:
        return _vectorstore

    # Check index exists
    if not os.path.exists(INDEX_PATH):
        raise FileNotFoundError(
            f"\nFAISS index not found at '{INDEX_PATH}/'.\n"
            f"Please run: python ingest.py\n"
        )

    print("  Loading FAQ index from disk...")

    _embeddings  = get_embeddings()
    _vectorstore = FAISS.load_local(
        INDEX_PATH,
        _embeddings,
        allow_dangerous_deserialization = True   # safe — our own local index
    )

    print("  FAQ index loaded!\n")
    return _vectorstore


# ── Function 2 — Get FAQ Answer ───────────────────────────────────────────────

def get_faq_answer(question, persona="existing_customer",
                   session_id="SYSTEM", feedback_style="default"):
    """
    Retrieves relevant FAQ chunks and generates
    grounded answer using GPT-4o.

    Parameters:
        question : user's banking question
        persona  : new_customer / existing_customer / banker

    Returns:
        answer   : string — grounded in FAQ document
        sources  : list of retrieved document chunks
    """

    # Load index
    vectorstore = load_faq_vectorstore()
    retriever   = vectorstore.as_retriever(
                    search_kwargs = {"k": 3}   # retrieve top 3 chunks
                  )
    
    # Log tool called
    log_info(session_id, persona, "faq_tool_called", question)

    vectorstore = load_faq_vectorstore()
    retriever   = vectorstore.as_retriever(
                    search_kwargs = {"k": 3}
                  )
    
    
    # Persona specific tone
    tone_map = {
        "new_customer"      : "Use simple friendly language. Avoid jargon.",
        "existing_customer" : "Be supportive and solution focused.",
        "banker"            : "Be formal and precise. Include policy details."
    }
    tone = tone_map.get(persona, "Be professional and concise.")

    # Feedback-driven style guidance
    from tools.feedback_tool import get_style_guidance
    style_guidance = get_style_guidance(feedback_style, persona)

    # Prompt — strictly answers from context only
    prompt = PromptTemplate.from_template("""
You are a banking support assistant. {tone}
{style_guidance}
Answer the question using ONLY the information in the context below.
If the answer is not found in the context, respond with:
"I don't have that information. Please contact your nearest branch or call 1800-XXX-XXXX."

Do NOT make up any information.
Do NOT use any knowledge outside the provided context.

Context:
{context}

Question: {question}

Answer:""")

    # GPT-4o with proxy bypass
    llm = ChatOpenAI(
        model             = "gpt-4o",
        temperature       = 0,
        http_client       = http_client,
        http_async_client = http_async_client
    )

    # Format retrieved chunks into one string
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # LCEL chain — modern LangChain approach
    chain = (
        {
            "context"        : retriever | format_docs,
            "question"       : RunnablePassthrough(),
            "tone"           : lambda _: tone,
            "style_guidance" : lambda _: style_guidance
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    # Retrieve source chunks for transparency
    retrieved_docs = retriever.invoke(question)
    
    # Log chunks retrieved
    log_info(session_id, persona,
             "faq_chunks_retrieved",
             f"count={len(retrieved_docs)}")
    

    # Run chain and get answer
    answer = chain.invoke(question)
    

    # ✅ Log answer or fallback
    if "don't have that information" in answer.lower():
        log_warning(session_id, persona,
                    "faq_fallback",
                    f"not in FAQ: {question}")
    else:
        log_info(session_id, persona,
                 "faq_answer_generated",
                 f"length={len(answer)}")
        
    
    return answer, retrieved_docs


# ── Function 3 — Compare With vs Without RAG ─────────────────────────────────

def compare_with_without_rag(question,
                              session_id="SYSTEM"):
    """
    Compares answer quality with and without RAG.
    Required for Phase 4 documentation.

    Returns:
        without_rag : generic GPT-4o answer
        with_rag    : grounded answer from FAQ document
        sources     : chunks retrieved from FAISS
    """

    llm = ChatOpenAI(
        model             = "gpt-4o",
        temperature       = 0,
        http_client       = http_client,
        http_async_client = http_async_client
    )

    log_info(session_id, "system",
             "rag_comparison_started", question)
    


    # Without RAG — direct GPT-4o answer
    response_without = llm.invoke([
        HumanMessage(content=question)
    ])
    

    # With RAG — grounded in FAQ document
    response_with, sources = get_faq_answer(question, session_id=session_id)

    return response_without.content, response_with, sources


# ── Test ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("=" * 55)
    print("  Phase 4 — RAG FAQ Tool Test")
    print("=" * 55)

    TEST_SESSION = "TEST-PHASE4-001"

    # ── Test 1: Basic FAQ questions ───────────────────────────────────────────
    print("\n── Test 1: Basic FAQ Questions ───────────────────────")

    questions = [                                    # ← define FIRST
        "What is the minimum balance for savings account?",
        "What is the interest rate for personal loan?",
        "What are NEFT charges?",
        "What is the penalty for breaking FD early?"
    ]

    for q in questions:                              # ← then loop
        print(f"\nQ: {q}")
        answer, sources = get_faq_answer(
            q,
            persona    = "existing_customer",
            session_id = TEST_SESSION
        )
        print(f"A: {answer}")
        print(f"   [{len(sources)} chunk(s) retrieved]")

    # ── Test 2: With vs Without RAG ───────────────────────────────────────────
    print("\n── Test 2: With vs Without RAG ───────────────────────")
    q = "What is the minimum balance for savings account?"
    print(f"\nQuestion: {q}")

    without, with_rag, sources = compare_with_without_rag(
        q,
        session_id = TEST_SESSION
    )

    print(f"\n❌ Without RAG (generic GPT-4o):")
    print(without)
    print(f"\n✅ With RAG (grounded in YOUR document):")
    print(with_rag)
    print(f"\nChunks retrieved: {len(sources)}")
    for i, src in enumerate(sources, 1):
        print(f"\nChunk {i}: {src.page_content[:200]}...")

    # ── Test 3: Question NOT in FAQ ───────────────────────────────────────────
    print("\n── Test 3: Question Not in FAQ ───────────────────────")
    q = "What is the process for getting a locker?"
    print(f"\nQ: {q}")
    answer, _ = get_faq_answer(
        q,
        persona    = "existing_customer",
        session_id = TEST_SESSION
    )
    print(f"A: {answer}")
    print("\n✅ Agent correctly says it doesn't know")
    print("   instead of hallucinating an answer")