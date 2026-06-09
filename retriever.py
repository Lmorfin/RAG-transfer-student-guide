"""
Milestone 4 — Embedding & Retrieval
====================================
RAG system: Community College -> CSU/UC Transfer Experiences

This module implements the third and fourth stages of the pipeline in
planning.md:

    Embedding + Vector Store  ->  Retrieval

It takes the cleaned chunks produced by the ingestion stage
(ingest_and_chunk.py), embeds them locally with all-MiniLM-L6-v2, stores them
in a persistent ChromaDB collection together with their metadata, and exposes a
`retrieve()` function for semantic search. A test block at the bottom runs the
evaluation questions from planning.md.

Runs fully locally. The only network use is the one-time download of the
embedding model weights from Hugging Face on first run.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sentence_transformers import SentenceTransformer
import chromadb

# Reuse the ingestion stage exactly — no re-implementation of chunking.
from ingest_and_chunk import build_documents, chunk_documents, DOCUMENTS_DIR


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"          # planning.md -> Retrieval Approach
CHROMA_PATH = Path(__file__).parent / "chroma_db"  # on-disk persistent store
COLLECTION_NAME = "transfer_chunks"
DEFAULT_TOP_K = 4                                  # task default (planning.md uses 5)

# Required metadata keys we expect on every stored chunk (for validation).
REQUIRED_METADATA_KEYS = {
    "source_file", "source_name", "chunk_index", "chunk_id", "char_count",
}


# ---------------------------------------------------------------------------
# Model + client setup
# ---------------------------------------------------------------------------

def load_embedding_model() -> SentenceTransformer:
    """Load all-MiniLM-L6-v2 once and reuse it for both indexing and queries.

    all-MiniLM-L6-v2 maps a sentence/short passage to a 384-dimensional vector.
    The same model MUST embed both the stored chunks and the query, otherwise
    the vectors live in different spaces and distances are meaningless.
    """
    print(f"Loading embedding model: {EMBEDDING_MODEL_NAME} ...")
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def get_collection() -> "chromadb.api.models.Collection.Collection":
    """Open (or create) the persistent ChromaDB collection.

    ChromaDB APIs used here:
      * PersistentClient(path=...)  -> a client that writes the database to disk
        so the index survives between runs (vs. the in-memory Client()).
      * get_or_create_collection(...) -> fetch the collection if it exists, else
        create it. We pin the distance metric with metadata={"hnsw:space": ...}.
        "cosine" measures the *angle* between vectors, which is the standard,
        length-robust choice for sentence embeddings. (Chroma's default is L2.)
    """
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


# ---------------------------------------------------------------------------
# Embedding pipeline (chunks -> vectors -> ChromaDB)
# ---------------------------------------------------------------------------

def load_chunks_from_ingestion():
    """Run the ingestion stage and return its list of Chunk objects.

    We call build_documents + chunk_documents directly (instead of the noisy
    main() report) so this stays quiet and importable.
    """
    documents = build_documents(DOCUMENTS_DIR)
    chunks = chunk_documents(documents)
    return chunks


def index_chunks(collection, model, chunks, batch_size: int = 64) -> int:
    """Embed every chunk and upsert it into ChromaDB with its metadata.

    Why `upsert` instead of `add`: upsert is keyed on the chunk's stable
    `chunk_id`. Re-running the script overwrites the same IDs rather than
    raising a duplicate-ID error or inserting duplicates — the operation is
    idempotent.

    Each Chroma record has four parallel parts, all addressed by the same id:
        ids        -> unique string per chunk  (chunk_id)
        documents  -> the raw chunk text
        embeddings -> the 384-dim vector we compute here
        metadatas  -> the source metadata dict (scalars only: str/int/float/bool)
    """
    if not chunks:
        print("  [warn] no chunks to index.")
        return 0

    total = len(chunks)
    print(f"Embedding and indexing {total} chunks (batch size {batch_size}) ...")

    for start in range(0, total, batch_size):
        batch = chunks[start:start + batch_size]

        ids = [c.metadata["chunk_id"] for c in batch]
        documents = [c.text for c in batch]
        metadatas = [c.metadata for c in batch]

        # normalize_embeddings=True returns unit-length vectors, which keeps
        # cosine distances clean and in a predictable range.
        embeddings = model.encode(
            documents,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        print(f"  indexed {min(start + batch_size, total)}/{total}")

    return total


def build_index(force_rebuild: bool = False):
    """Convenience: load model + collection, and index chunks if needed.

    Skips re-embedding when the collection already holds the expected number of
    chunks, unless force_rebuild=True.
    """
    model = load_embedding_model()
    collection = get_collection()

    chunks = load_chunks_from_ingestion()
    existing = collection.count()

    if force_rebuild or existing != len(chunks):
        if force_rebuild and existing:
            # Wipe the collection so a rebuild doesn't leave stale chunks behind.
            client = chromadb.PersistentClient(path=str(CHROMA_PATH))
            client.delete_collection(COLLECTION_NAME)
            collection = client.get_or_create_collection(
                name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
        index_chunks(collection, model, chunks)
    else:
        print(f"Collection already holds {existing} chunks — skipping indexing.")

    print(f"Collection '{COLLECTION_NAME}' ready: {collection.count()} chunks.\n")
    return model, collection


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve(query: str, model, collection, k: int = DEFAULT_TOP_K) -> list[dict]:
    """Embed a query and return the top-k most similar chunks.

    Steps:
      1. Embed the query with the SAME model used for the chunks.
      2. collection.query(...) runs an approximate-nearest-neighbour search over
         the stored vectors and returns the closest k records.
      3. Flatten Chroma's response into a simple list of dicts.

    Returns, per hit: text, distance (lower = closer), metadata, id, and a
    convenience `similarity` = 1 - distance (since the space is cosine).
    """
    query_embedding = model.encode(
        [query], normalize_embeddings=True, show_progress_bar=False
    ).tolist()

    # `include` controls which fields come back. IDs are always returned.
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    # Chroma returns each field as a list-of-lists (one inner list per query).
    # We sent a single query, so we read index [0] of each.
    hits: list[dict] = []
    for doc, meta, dist, _id in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
        results["ids"][0],
    ):
        hits.append({
            "id": _id,
            "text": doc,
            "metadata": meta,
            "distance": dist,
            "similarity": 1 - dist,   # cosine: 1.0 = identical, 0 = unrelated
        })
    return hits


# ---------------------------------------------------------------------------
# Debugging / validation helpers
# ---------------------------------------------------------------------------

def inspect_chunk(collection, chunk_id: str) -> None:
    """Print the full stored text + metadata for one chunk id."""
    record = collection.get(ids=[chunk_id], include=["documents", "metadatas"])
    if not record["ids"]:
        print(f"  [not found] {chunk_id}")
        return
    print(f"\n--- inspect {chunk_id} ---")
    print("Metadata:")
    for key, value in record["metadatas"][0].items():
        print(f"    {key:>13}: {value}")
    print("Text:")
    print(f"    {record['documents'][0]}")


def verify_metadata_stored(collection, sample_size: int = 5) -> None:
    """Spot-check that metadata round-tripped into ChromaDB correctly.

    Pulls a few records back out and confirms the required keys are present —
    useful because Chroma silently drops keys whose value is None.
    """
    record = collection.get(limit=sample_size, include=["metadatas"])
    print(f"\nVerifying metadata on {len(record['ids'])} sample chunks ...")
    for cid, meta in zip(record["ids"], record["metadatas"]):
        present = REQUIRED_METADATA_KEYS.issubset(meta.keys())
        status = "OK " if present else "MISSING KEYS"
        print(f"    [{status}] {cid}  keys={sorted(meta.keys())}")


def find_missing_metadata(collection) -> list[str]:
    """Scan the whole collection and return ids missing any required key."""
    record = collection.get(include=["metadatas"])
    bad: list[str] = []
    for cid, meta in zip(record["ids"], record["metadatas"]):
        missing = REQUIRED_METADATA_KEYS - set(meta.keys())
        # Treat blank required strings as missing too.
        blank = {k for k in REQUIRED_METADATA_KEYS
                 if isinstance(meta.get(k), str) and not meta.get(k).strip()}
        if missing or blank:
            bad.append(cid)
    print(f"\nChunks with missing/blank required metadata: {len(bad)}")
    for cid in bad:
        print(f"    {cid}")
    return bad


def display_scores(query: str, hits: list[dict]) -> None:
    """Compact one-line-per-hit score view for troubleshooting ranking."""
    print(f"\nScores for query: {query!r}")
    print(f"    {'rank':<5}{'distance':<11}{'similarity':<12}{'source':<22}chunk")
    for rank, hit in enumerate(hits, 1):
        meta = hit["metadata"]
        print(f"    {rank:<5}{hit['distance']:<11.4f}{hit['similarity']:<12.4f}"
              f"{meta.get('source_name', '?'):<22}"
              f"{meta.get('chunk_id', '?')}")


# ---------------------------------------------------------------------------
# Pretty-printing for the evaluation run
# ---------------------------------------------------------------------------

def print_results(query: str, hits: list[dict]) -> None:
    """Human-readable dump of a query's retrieved chunks + provenance."""
    print("\n" + "=" * 78)
    print(f"QUERY: {query}")
    print("=" * 78)
    if not hits:
        print("  (no results)")
        return
    for rank, hit in enumerate(hits, 1):
        meta = hit["metadata"]
        print(f"\n[{rank}] distance={hit['distance']:.4f}  "
              f"similarity={hit['similarity']:.4f}")
        print(f"    source : {meta.get('source_name')}  ({meta.get('source_file')})")
        print(f"    chunk  : index {meta.get('chunk_index')} "
              f"of {meta.get('total_chunks')}   id={meta.get('chunk_id')}")
        if meta.get("title"):
            print(f"    title  : {meta.get('title')}")
        if meta.get("url"):
            print(f"    url    : {meta.get('url')}")
        text = hit["text"].replace("\n", " ")
        print(f"    text   : {text}")


# ---------------------------------------------------------------------------
# Test / evaluation entry point
# ---------------------------------------------------------------------------

# The 5 evaluation questions from planning.md (>= 3 required).
EVALUATION_QUERIES = [
    "Should transfer students complete lower-division requirements before transferring?",
    "What are common reasons students choose community college before a CSU or UC?",
    "What barriers can make transferring from a community college difficult?",
    "Can students transfer into majors not offered at their community college?",
    "How can students improve their chances of a successful transfer?",
]


def main() -> None:
    # Make non-ASCII content print correctly on a Windows cp1252 console.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    # 1. Build (or reuse) the embedded index.
    model, collection = build_index()

    # 2. Validation / debugging checks before querying.
    verify_metadata_stored(collection)
    find_missing_metadata(collection)

    # 3. Run the evaluation queries with k defaulting to 4.
    for query in EVALUATION_QUERIES:
        hits = retrieve(query, model, collection, k=DEFAULT_TOP_K)
        print_results(query, hits)
        display_scores(query, hits)

    # 4. Example of inspecting one specific stored chunk for debugging.
    if collection.count():
        first_id = collection.get(limit=1)["ids"][0]
        inspect_chunk(collection, first_id)


if __name__ == "__main__":
    main()
