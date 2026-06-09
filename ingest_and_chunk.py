"""
Milestone 3 — Document Ingestion & Chunking
============================================
RAG system: Community College -> CSU/UC Transfer Experiences

This script implements the first two stages of the pipeline described in
planning.md:

    Document Ingestion  ->  Chunking

It loads every .txt file in documents/, cleans boilerplate, extracts
per-document metadata, splits each document into 500-character chunks with a
50-character overlap (exactly as specified in the Chunking Strategy section),
attaches metadata to every chunk, prints a report, and runs validation checks.

Embedding / vector store / retrieval / generation are intentionally NOT here —
they belong to Milestones 4 and 5.

Stdlib only: no external dependencies are needed for ingestion + chunking.
"""

from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Configuration — values come straight from planning.md
# ---------------------------------------------------------------------------

DOCUMENTS_DIR = Path(__file__).parent / "documents"

CHUNK_SIZE = 500       # characters  (planning.md -> Chunking Strategy)
CHUNK_OVERLAP = 50     # characters  (planning.md -> Chunking Strategy)
STRIDE = CHUNK_SIZE - CHUNK_OVERLAP  # = 450; how far the window advances

# Map filename stems -> the human-readable source name from the planning.md
# Documents table. Used only as a FALLBACK when a file has no parseable header.
FILENAME_SOURCE_MAP = {
    "reddit_thread_1": "Reddit",
    "reddit_thread_2": "Reddit",
    "reddit_thread_3": "Reddit",
    "reddit_thread_4": "Reddit",
    "ppic_transfer_policy_brief": "PPIC",
    "ppic_college_affordability_in_ca": "PPIC",
    "edsource_transfer_roadblocks": "EdSource",
    "quora_uc_vs_csu_transfer": "Quora",
    "bestcolleges_uc_vs_csu": "BestColleges",
    "collegevine_csu_vs_uc": "CollegeVine",
    "magellan_transfer_guide": "Magellan Counseling",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Document:
    """A single loaded + cleaned source document with its metadata."""
    source_file: str          # e.g. "reddit_thread_1.txt"
    source_name: str          # e.g. "Reddit", "PPIC"
    url: str                  # original source URL (if found in the file)
    title: str                # Reddit/Quora title, else ""
    text: str                 # cleaned body text


@dataclass
class Chunk:
    """A retrievable chunk plus the metadata that travels with it."""
    text: str
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# STAGE 1a — Loading
# ---------------------------------------------------------------------------

def load_raw_documents(documents_dir: Path) -> list[tuple[Path, str]]:
    """Read every .txt file in the documents directory.

    Returns a list of (path, raw_text) tuples. Empty files are skipped with a
    warning so they never produce empty chunks downstream.
    """
    if not documents_dir.is_dir():
        raise FileNotFoundError(f"Documents directory not found: {documents_dir}")

    raw_docs: list[tuple[Path, str]] = []
    # Sorted for deterministic, reproducible chunk IDs across runs.
    for path in sorted(documents_dir.glob("*.txt")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            print(f"  [skip] empty file: {path.name}")
            continue
        raw_docs.append((path, text))
    return raw_docs


# ---------------------------------------------------------------------------
# STAGE 1b — Metadata extraction
# ---------------------------------------------------------------------------

def extract_metadata(path: Path, raw_text: str) -> tuple[str, str, str]:
    """Pull (source_name, url, title) from a document's header.

    Handles the two header layouts present in the corpus:
      * Reddit  : "REDDIT POST: r/<sub>" / "URL:" / "TITLE:"
      * Articles: "SOURCE: <name>" / "URL:"
    Falls back to FILENAME_SOURCE_MAP when a header field is absent.
    """
    stem = path.stem

    # --- source name -------------------------------------------------------
    source_name = ""
    src_match = re.search(r"^\s*SOURCE:\s*(.+)$", raw_text, re.MULTILINE)
    if src_match:
        source_name = src_match.group(1).strip()
    elif re.search(r"^\s*REDDIT POST:", raw_text, re.MULTILINE):
        source_name = "Reddit"
    if not source_name:                       # final fallback
        source_name = FILENAME_SOURCE_MAP.get(stem, "Unknown")

    # --- url ---------------------------------------------------------------
    url = ""
    url_match = re.search(r"^\s*URL:\s*(\S+)", raw_text, re.MULTILINE)
    if url_match:
        url = url_match.group(1).strip()

    # --- title (Reddit / Quora style only) ---------------------------------
    title = ""
    title_match = re.search(r"^\s*TITLE:\s*(.+)$", raw_text, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()

    return source_name, url, title


# ---------------------------------------------------------------------------
# STAGE 1c — Cleaning
# ---------------------------------------------------------------------------

# Defensive boilerplate patterns. The corpus is already hand-cleaned plain
# text, so these are mostly no-ops today, but they keep the pipeline robust if
# a raw HTML scrape is ever dropped into documents/.
_HTML_TAG = re.compile(r"<[^>]+>")
_BOILERPLATE_LINE = re.compile(
    r"^\s*("
    r"accept (all )?cookies|cookie (policy|settings|preferences)|"   # cookie banners
    r"we use cookies|"
    r"skip to (main )?content|"                                      # nav
    r"(home|menu|navigation|sign in|log in|subscribe|newsletter)\s*$|"
    r"share (this|on)|tweet|follow us|"                              # share buttons
    r"advertisement|sponsored|"                                      # ads
    r"all rights reserved|©.*|copyright.*|privacy policy|terms of (use|service)"  # footers
    r")",
    re.IGNORECASE,
)
# Structural separators used in OUR files: "------------" and "=== ... ===".
_SEPARATOR_LINE = re.compile(r"^\s*(-{3,}|={3,}.*={3,}|={3,})\s*$")
# Header lines whose content is already captured as metadata -> drop from body
# so they don't pollute the embedded chunk text.
_HEADER_META_LINE = re.compile(r"^\s*(SOURCE|URL):\s*", re.IGNORECASE)


def clean_text(raw_text: str) -> str:
    """Remove boilerplate while preserving review text, ratings, names, and
    contextual info needed for retrieval.

    Steps:
      1. Strip any HTML tags (defensive).
      2. Drop structural separator lines (------------ and === ... ===).
      3. Drop known boilerplate lines (cookie/nav/ads/footer/share).
      4. Remove duplicate Reddit upvote-count lines (e.g. a stray "42" right
         after "UPVOTES: 42") — these are scrape artifacts, not content.
      5. Collapse excessive blank lines and trailing whitespace.
    NOTE: AUTHOR / TITLE / BODY / UPVOTES / ratings lines are deliberately KEPT.
    """
    text = _HTML_TAG.sub(" ", raw_text)

    cleaned_lines: list[str] = []
    prev_upvotes: str | None = None  # tracks the number from the last "UPVOTES:" line

    for line in text.splitlines():
        stripped = line.strip()

        # 2 + 3: skip separators, boilerplate, and metadata header lines
        if (_SEPARATOR_LINE.match(stripped)
                or _BOILERPLATE_LINE.match(stripped)
                or _HEADER_META_LINE.match(stripped)):
            continue

        # 4: detect "UPVOTES: N" so we can drop a following duplicate "N" line
        up_match = re.match(r"^UPVOTES:\s*(\d+)\s*$", stripped)
        if up_match:
            prev_upvotes = up_match.group(1)
            cleaned_lines.append(stripped)
            continue
        if stripped == "":
            # Keep blank lines but don't let them reset the upvote tracker, so
            # a duplicate count separated by a blank line is still caught.
            cleaned_lines.append("")
            continue
        if prev_upvotes is not None and stripped == prev_upvotes:
            prev_upvotes = None      # swallow the duplicate count line
            continue
        prev_upvotes = None

        cleaned_lines.append(line.rstrip())

    text = "\n".join(cleaned_lines)
    # 5: collapse 3+ newlines into a clean paragraph break, trim ends.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_documents(documents_dir: Path) -> list[Document]:
    """Load -> extract metadata -> clean, producing ready-to-chunk Documents."""
    documents: list[Document] = []
    for path, raw_text in load_raw_documents(documents_dir):
        source_name, url, title = extract_metadata(path, raw_text)
        cleaned = clean_text(raw_text)
        if not cleaned:
            print(f"  [skip] nothing left after cleaning: {path.name}")
            continue
        documents.append(
            Document(
                source_file=path.name,
                source_name=source_name,
                url=url,
                title=title,
                text=cleaned,
            )
        )
    return documents


# ---------------------------------------------------------------------------
# STAGE 2 — Chunking (exact 500-char window, 50-char overlap)
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into fixed-size character chunks with a sliding-window overlap.

    This is the splitting method specified in planning.md:
      * window width  = chunk_size      (500 chars)
      * step / stride = chunk_size - overlap (450 chars)
    Consecutive chunks therefore share `overlap` (50) characters so a thought
    that straddles a boundary is not lost.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    stride = chunk_size - overlap
    chunks: list[str] = []
    start = 0
    while start < len(text):
        chunk = text[start:start + chunk_size].strip()
        if chunk:                      # guard against whitespace-only chunks
            chunks.append(chunk)
        if start + chunk_size >= len(text):
            break                      # last window reached the end
        start += stride
    return chunks


def chunk_documents(documents: Iterable[Document]) -> list[Chunk]:
    """Chunk every document and attach full metadata to each chunk.

    Metadata per chunk:
      source_file, source_name, url, title,
      chunk_index (within its document), total_chunks (in that document),
      chunk_id (stable, unique), char_count.
    """
    all_chunks: list[Chunk] = []
    for doc in documents:
        pieces = chunk_text(doc.text)
        total = len(pieces)
        stem = Path(doc.source_file).stem
        for i, piece in enumerate(pieces):
            metadata = {
                "source_file": doc.source_file,
                "source_name": doc.source_name,
                "url": doc.url,
                "title": doc.title,
                "chunk_index": i,
                "total_chunks": total,
                "chunk_id": f"{stem}::chunk_{i:03d}",  # e.g. reddit_thread_1::chunk_000
                "char_count": len(piece),
            }
            all_chunks.append(Chunk(text=piece, metadata=metadata))
    return all_chunks


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

REQUIRED_METADATA_KEYS = {
    "source_file", "source_name", "chunk_index", "chunk_id", "char_count",
}


def validate_chunks(chunks: list[Chunk]) -> dict:
    """Run quality checks and return a report dict.

    Checks for:
      * empty chunks            (no usable text)
      * duplicate chunks        (identical normalized text)
      * missing metadata        (required keys absent or blank)
    """
    empty: list[str] = []
    missing_metadata: list[str] = []
    seen: dict[str, str] = {}        # normalized-text-hash -> first chunk_id
    duplicates: list[tuple[str, str]] = []

    for chunk in chunks:
        cid = chunk.metadata.get("chunk_id", "<no-id>")

        # empty
        if not chunk.text or not chunk.text.strip():
            empty.append(cid)

        # missing / blank required metadata (url & title may legitimately be "")
        for key in REQUIRED_METADATA_KEYS:
            value = chunk.metadata.get(key, None)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                missing_metadata.append(f"{cid} (missing '{key}')")

        # duplicate (whitespace/case-normalized)
        norm = re.sub(r"\s+", " ", chunk.text.strip().lower())
        digest = hashlib.sha1(norm.encode("utf-8")).hexdigest()
        if digest in seen:
            duplicates.append((cid, seen[digest]))
        else:
            seen[digest] = cid

    return {
        "empty": empty,
        "duplicates": duplicates,
        "missing_metadata": missing_metadata,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def representative_indices(total: int, k: int = 5) -> list[int]:
    """Pick k indices spread evenly across the corpus (not just the first k)."""
    if total <= k:
        return list(range(total))
    step = total / k
    return [int(i * step) for i in range(k)]


def print_report(documents: list[Document], chunks: list[Chunk],
                 validation: dict) -> None:
    """Print the summary required by the spec."""
    print("\n" + "=" * 70)
    print("INGESTION & CHUNKING REPORT")
    print("=" * 70)
    print(f"Total documents loaded : {len(documents)}")
    print(f"Total chunks created   : {len(chunks)}")

    sizes = [c.metadata["char_count"] for c in chunks]
    if sizes:
        print(f"Chunk size (chars)     : min={min(sizes)}  "
              f"avg={sum(sizes) // len(sizes)}  max={max(sizes)}  "
              f"(target={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")

    # --- 5 representative chunks + their metadata --------------------------
    print("\n" + "-" * 70)
    print("5 REPRESENTATIVE CHUNKS")
    print("-" * 70)
    for idx in representative_indices(len(chunks), 5):
        chunk = chunks[idx]
        print(f"\n[Global chunk #{idx}]  id={chunk.metadata['chunk_id']}")
        print("  Metadata:")
        for key, value in chunk.metadata.items():
            print(f"    {key:>13}: {value}")
        preview = chunk.text.replace("\n", " ")
        print(f"  Text ({len(chunk.text)} chars):")
        print(f"    {preview}")

    # --- validation results ------------------------------------------------
    print("\n" + "-" * 70)
    print("VALIDATION")
    print("-" * 70)
    print(f"Empty chunks         : {len(validation['empty'])}")
    if validation["empty"]:
        print(f"    {validation['empty']}")
    print(f"Duplicate chunks     : {len(validation['duplicates'])}")
    for dup_id, first_id in validation["duplicates"]:
        print(f"    {dup_id} duplicates {first_id}")
    print(f"Missing metadata     : {len(validation['missing_metadata'])}")
    for item in validation["missing_metadata"]:
        print(f"    {item}")

    status = "PASS" if not (validation["empty"]
                            or validation["missing_metadata"]) else "REVIEW"
    print(f"\nOverall: {status}")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> list[Chunk]:
    """Run the full ingestion + chunking pipeline and return the chunks.

    Returning the chunks lets Milestone 4 import and embed them directly:
        from ingest_and_chunk import main
        chunks = main()
    """
    # Ensure non-ASCII content (curly quotes, em-dashes, emoji) prints
    # correctly even on a Windows cp1252 console.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    print("Loading documents from:", DOCUMENTS_DIR)
    documents = build_documents(DOCUMENTS_DIR)
    chunks = chunk_documents(documents)
    validation = validate_chunks(chunks)
    print_report(documents, chunks, validation)
    return chunks


if __name__ == "__main__":
    main()
