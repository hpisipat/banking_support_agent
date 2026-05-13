# ingest.py
# Run this ONCE to build the FAISS index from faq_banking.txt
# After running, faiss_index/ folder will be created
# Agent loads from this folder — no re-embedding needed

from dotenv import load_dotenv
import os
import httpx
from pathlib import Path

load_dotenv()

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters             import RecursiveCharacterTextSplitter
from langchain_community.vectorstores     import FAISS
from langchain_openai                     import OpenAIEmbeddings

# ── Configuration ─────────────────────────────────────────────────────────────
FAQ_FILE      = "data/faq_banking.txt"
INDEX_PATH    = "faiss_index"
CHUNK_SIZE    = 500
CHUNK_OVERLAP = 50

# ── Proxy bypass ──────────────────────────────────────────────────────────────
http_client       = httpx.Client(proxy=None, timeout=60.0)
http_async_client = httpx.AsyncClient(proxy=None, timeout=60.0)


def main():

    print("=" * 45)
    print("  Banking Agent — FAQ Ingestion")
    print("=" * 45)

    # Step 1 — Verify FAQ file exists
    if not Path(FAQ_FILE).exists():
        raise FileNotFoundError(
            f"FAQ file not found: {FAQ_FILE}\n"
            f"Please create data/faq_banking.txt first!"
        )

    # Step 2 — Load document
    print("\n1. Loading FAQ document...")
    loader    = TextLoader(FAQ_FILE, autodetect_encoding=True)
    documents = loader.load()
    print(f"   Loaded {len(documents)} document(s)")

    # Step 3 — Add metadata
    for doc in documents:
        doc.metadata["source"] = FAQ_FILE
        doc.metadata["type"]   = "banking_faq"

    # Step 4 — Split into chunks
    print("\n2. Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size    = CHUNK_SIZE,
        chunk_overlap = CHUNK_OVERLAP
    )
    chunks = splitter.split_documents(documents)

    # Add chunk level metadata
    for i, chunk in enumerate(chunks, start=1):
        chunk.metadata["chunk_id"] = i

    print(f"   Created {len(chunks)} chunks")

    # Step 5 — Create OpenAI embeddings with proxy bypass
    print("\n3. Creating OpenAI embeddings...")
    embeddings = OpenAIEmbeddings(
        model             = "text-embedding-3-small",
        api_key           = os.getenv("OPENAI_API_KEY"),
        http_client       = http_client,
        http_async_client = http_async_client
    )
    print("   Embeddings model ready")

    # Step 6 — Build FAISS index
    print("\n4. Building FAISS index...")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    print("   Index built")

    # Step 7 — Save index to disk
    print(f"\n5. Saving index to '{INDEX_PATH}/'...")
    os.makedirs(INDEX_PATH, exist_ok=True)
    vectorstore.save_local(INDEX_PATH)
    print(f"   Index saved")

    # Summary
    print("\n" + "=" * 45)
    print(f"  Ingestion Complete!")
    print(f"  Source   : {FAQ_FILE}")
    print(f"  Chunks   : {len(chunks)}")
    print(f"  Index at : {INDEX_PATH}/")
    print(f"  Next     : python tools/faq_tool.py")
    print("=" * 45)


if __name__ == "__main__":
    main()

