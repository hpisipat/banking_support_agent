# tests/test_connection.py

import os
import httpx
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

print("=== Testing OpenAI with proxy bypass ===")

# Create client with no proxy
http_client = httpx.Client(proxy=None, timeout=60.0)
client      = OpenAI(http_client=http_client)

try:
    response = client.chat.completions.create(
        model      = "gpt-4o",
        messages   = [{"role": "user", "content": "say hello"}],
        max_tokens = 10
    )
    print("✅ Connection works!")
    print(f"Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")