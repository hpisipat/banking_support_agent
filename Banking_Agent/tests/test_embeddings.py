# tests/test_embeddings.py

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
import openai
from dotenv import load_dotenv

load_dotenv()

print("Testing embeddings with proxy bypass...\n")

# Method 1 — Direct openai client
try:
    client = openai.OpenAI(
        api_key     = os.getenv("OPENAI_API_KEY"),
        http_client = httpx.Client(proxy=None, timeout=60.0)
    )

    response = client.embeddings.create(
        model = "text-embedding-3-small",
        input = "test sentence"
    )
    print("✅ Method 1 works!")
    print(f"   Embedding length: {len(response.data[0].embedding)}")

except Exception as e:
    print(f"❌ Method 1 failed: {e}")

# Method 2 — Via LangChain
try:
    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(
        model             = "text-embedding-3-small",
        api_key           = os.getenv("OPENAI_API_KEY"),
        http_client       = httpx.Client(proxy=None, timeout=60.0),
        http_async_client = httpx.AsyncClient(proxy=None, timeout=60.0)
    )

    result = embeddings.embed_query("test sentence")
    print("✅ Method 2 works!")
    print(f"   Embedding length: {len(result)}")

except Exception as e:
    print(f"❌ Method 2 failed: {e}")