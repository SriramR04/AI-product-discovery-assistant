"""
ingest.py
---------
Loads products.csv, generates sentence-transformer embeddings,
and persists them to ChromaDB. Skips re-indexing if DB already exists.
"""

import os
import pandas as pd
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CSV_PATH    = os.path.join(BASE_DIR, "data", "products.csv")
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")

COLLECTION_NAME = "mumzworld_products"
EMBED_MODEL     = "all-MiniLM-L6-v2"


def get_chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=CHROMA_PATH)


def build_document(row: pd.Series) -> str:
    """Combine key fields into a rich text string for embedding."""
    return (
        f"{row['Product Name']} by {row['Brand']}. "
        f"Category: {row['Category']}. "
        f"Price: {row['Price_AED']} AED. "
        f"Age Group: {row['Age_Group']}. "
        f"{row['Description']}"
    )


def ingest(force: bool = False) -> chromadb.Collection:
    """
    Ingest CSV into ChromaDB.
    Returns the collection (existing or newly created).
    """
    client = get_chroma_client()

    # Check if collection already exists and has data
    existing = [c.name for c in client.list_collections()]
    if COLLECTION_NAME in existing and not force:
        collection = client.get_collection(COLLECTION_NAME)
        if collection.count() > 0:
            return collection  # Already indexed — skip

    # Fresh index
    if COLLECTION_NAME in existing:
        client.delete_collection(COLLECTION_NAME)

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    df = pd.read_csv(CSV_PATH)
    model = SentenceTransformer(EMBED_MODEL)

    documents = [build_document(row) for _, row in df.iterrows()]
    embeddings = model.encode(documents, show_progress_bar=False).tolist()

    metadatas = []
    for _, row in df.iterrows():
        metadatas.append({
            "product_name": str(row["Product Name"]),
            "brand":        str(row["Brand"]),
            "category":     str(row["Category"]),
            "price_aed":    float(row["Price_AED"]),
            "age_group":    str(row["Age_Group"]),
            "description":  str(row["Description"]),
        })

    ids = [f"product_{i}" for i in range(len(df))]

    collection.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )

    return collection


def get_collection() -> chromadb.Collection:
    """Return the existing collection (call ingest first)."""
    client = get_chroma_client()
    return client.get_collection(COLLECTION_NAME)
