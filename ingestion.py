import os
import glob
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
import uuid

load_dotenv(override=True)

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "jsbank-callcenter")
NAMESPACE = os.getenv("PINECONE_NAMESPACE", "meezanbank-data")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=1024)


def get_source_category(filename: str) -> dict:
    name = os.path.basename(filename).replace(".txt", "")

    if "digital" in name.lower():
        category = "Digital Banking"
        subcategory = "Digital Accounts & Services"
    elif "banking" in name.lower():
        category = "Banking Products"
        subcategory = "Accounts & Services"
    elif "ameen" in name.lower() or "islamic" in name.lower():
        category = "Islamic Banking"
        subcategory = "Meezan Bank Islamic Products"
    elif "signature" in name.lower() or "premium" in name.lower():
        category = "Premium Banking"
        subcategory = "Priority Banking"
    elif "deposit" in name.lower():
        category = "Deposits"
        subcategory = "Term Deposits & Savings"
    elif "consumer" in name.lower():
        category = "Consumer Banking"
        subcategory = "Loans & Financing"
    else:
        category = "General"
        subcategory = name.replace("_", " ").replace("-", " ").title()

    return {
        "category": category,
        "subcategory": subcategory,
        "source_file": name
    }


def ingest_text_file(file_path: str):
    print(f"📄 Ingesting {file_path}...")

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    if not text.strip():
        print(f"⚠️ Skipping empty file: {file_path}")
        return

    source_info = get_source_category(file_path)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        length_function=len,
        is_separator_regex=False,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = text_splitter.split_text(text)

    vectors = []
    for i, chunk in enumerate(chunks):
        doc_id = str(uuid.uuid4())
        vector = embeddings.embed_query(chunk)

        metadata = {
            "text": chunk,
            "category": source_info["category"],
            "subcategory": source_info["subcategory"],
            "source_file": source_info["source_file"],
            "chunk_index": i,
            "total_chunks": len(chunks)
        }

        vectors.append({
            "id": doc_id,
            "values": vector,
            "metadata": metadata
        })

        if len(vectors) >= 50:
            index.upsert(vectors=vectors, namespace=NAMESPACE)
            print(f"  ✓ Upserted batch of {len(vectors)} vectors")
            vectors = []

    if vectors:
        index.upsert(vectors=vectors, namespace=NAMESPACE)
        print(f"  ✓ Upserted final batch of {len(vectors)} vectors")

    print(f"✅ Completed: {file_path} ({len(chunks)} chunks)")


def ingest_all_pages(pages_dir: str = "pages"):
    txt_files = glob.glob(os.path.join(pages_dir, "*.txt"))

    if not txt_files:
        print(f"❌ No .txt files found in {pages_dir}")
        return

    print(f"\n🚀 Starting ingestion of {len(txt_files)} files into namespace '{NAMESPACE}'...\n")

    for file_path in sorted(txt_files):
        try:
            ingest_text_file(file_path)
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")

    print(f"\n✅ Ingestion complete! All files indexed in namespace '{NAMESPACE}'")

    stats = index.describe_index_stats()
    if NAMESPACE in stats.get("namespaces", {}):
        count = stats["namespaces"][NAMESPACE]["vector_count"]
        print(f"📊 Total vectors in namespace: {count}")


def clear_namespace():
    print(f"🗑️ Clearing namespace '{NAMESPACE}'...")
    index.delete(delete_all=True, namespace=NAMESPACE)
    print(f"✅ Namespace '{NAMESPACE}' cleared")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        clear_namespace()

    ingest_all_pages("pages")
