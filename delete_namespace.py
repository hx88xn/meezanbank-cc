#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv(override=True)

INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "jsbank-callcenter")
NAMESPACE = os.getenv("PINECONE_NAMESPACE", "meezanbank-data")

def main():
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        print("❌ PINECONE_API_KEY not set in .env")
        return 1
    pc = Pinecone(api_key=api_key)
    index = pc.Index(INDEX_NAME)
    print(f"🗑️ Deleting namespace '{NAMESPACE}' from index '{INDEX_NAME}'...")
    index.delete(delete_all=True, namespace=NAMESPACE)
    print(f"✅ Namespace '{NAMESPACE}' deleted.")
    return 0

if __name__ == "__main__":
    exit(main())
