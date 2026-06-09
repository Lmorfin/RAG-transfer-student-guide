"""
Milestone 5 (part 1) — Grounded Generation Layer
=================================================
RAG system: Community College -> CSU/UC Transfer Experiences

This module is the "Generation" box in planning.md's pipeline diagram. It:
  1. retrieves the top-k chunks from ChromaDB (via retriever.py),
  2. builds a strongly-grounded prompt from those chunks + their metadata,
  3. sends it to Groq's llama-3.3-70b-versatile model,
  4. returns a grounded answer plus a programmatically-built source list.

Public entry point:
    ask(question, k=5) -> {"answer": "...", "sources": ["doc1.txt", ...]}

The Gradio UI (app.py) and the test block at the bottom both call ask().
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from groq import Groq

# Reuse the already-built retrieval stage from Milestone 4.
from retriever import build_index, retrieve

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()  # read GROQ_API_KEY from .env

GROQ_MODEL = "llama-3.3-70b-versatile"   # planning.md -> Generation
DEFAULT_TOP_K = 5                        # planning.md -> Retrieval Approach (top-k = 5)
GENERATION_TEMPERATURE = 0.1             # low => stays close to the provided context

# The EXACT sentence the system must return when the context is insufficient.
FALLBACK_MESSAGE = (
    "I don't have enough information in the provided documents to answer that question."
)

# ---------------------------------------------------------------------------
# Lazy singletons
# ---------------------------------------------------------------------------
# The embedding model + ChromaDB collection are expensive to build, so we build
# them once on first use and reuse them for every subsequent question.

_model = None
_collection = None
_groq_client = None


def _get_pipeline():
    """Return (embedding_model, chroma_collection), building them once."""
    global _model, _collection
    if _model is None or _collection is None:
        _model, _collection = build_index()  # loads model, opens/loads ChromaDB
    return _model, _collection


def _get_groq_client() -> Groq:
    """Return a cached Groq client, validating the API key is present."""
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key.strip() in ("", "your_key_here"):
            raise RuntimeError(
                "GROQ_API_KEY is missing. Copy .env.example to .env and set a real "
                "key from https://console.groq.com"
            )
        _groq_client = Groq(api_key=api_key)
    return _groq_client


# ---------------------------------------------------------------------------
# Prompt construction (the grounding lives here)
# ---------------------------------------------------------------------------

# System prompt: hard rules. We *enforce* grounding rather than suggest it —
# the model is told to use ONLY the context, to never add outside knowledge,
# and to return the exact fallback sentence when the context falls short.
SYSTEM_PROMPT = f"""You are a careful assistant that answers questions about \
transferring from California community colleges to CSU/UC universities.

You must follow these rules without exception:
1. Answer using ONLY the information in the "CONTEXT" provided by the user.
2. Do NOT use any outside or prior knowledge. If a fact is not in the context, \
you do not know it.
3. If the context does not contain enough information to answer the question, \
respond with EXACTLY this sentence and nothing else:
"{FALLBACK_MESSAGE}"
4. Do not guess, speculate, or fill gaps. Do not invent statistics, names, or sources.
5. When sources in the context disagree or offer different perspectives, present \
the differing viewpoints rather than choosing one as universally correct.
6. Be concise and base every statement on the provided excerpts."""


def build_context(hits: list[dict]) -> str:
    """Format retrieved chunks into a numbered, source-labeled context block.

    Each excerpt is tagged with its source so the model can ground its answer
    and (optionally) reference excerpts. Attribution itself is computed
    programmatically in extract_sources() — we never trust the model to cite.
    """
    blocks = []
    for i, hit in enumerate(hits, 1):
        meta = hit["metadata"]
        label = f"{meta.get('source_name', 'Unknown')} ({meta.get('source_file', '?')})"
        blocks.append(f"[Excerpt {i} — {label}]\n{hit['text']}")
    return "\n\n".join(blocks)


def build_user_prompt(question: str, context: str) -> str:
    """Assemble the user message: the context first, then the question."""
    return (
        "CONTEXT (the only information you may use):\n"
        "----------------------------------------\n"
        f"{context}\n"
        "----------------------------------------\n\n"
        f"QUESTION: {question}\n\n"
        "Answer using only the context above. If the context does not contain "
        f'enough information, reply exactly: "{FALLBACK_MESSAGE}"'
    )


def extract_sources(hits: list[dict]) -> list[str]:
    """Build the source list PROGRAMMATICALLY from retrieval metadata.

    Deduplicates by source filename while preserving retrieval order (most
    relevant first). This is the authoritative citation — independent of
    whatever the LLM writes.
    """
    seen = set()
    sources: list[str] = []
    for hit in hits:
        src = hit["metadata"].get("source_file")
        if src and src not in seen:
            seen.add(src)
            sources.append(src)
    return sources


# ---------------------------------------------------------------------------
# Groq call
# ---------------------------------------------------------------------------

def generate_answer(question: str, context: str) -> str:
    """Send the grounded prompt to Groq and return the model's text answer."""
    client = _get_groq_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=GENERATION_TEMPERATURE,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(question, context)},
        ],
    )
    return response.choices[0].message.content.strip()


def _is_fallback(answer: str) -> bool:
    """True if the model declined to answer (matches the fallback sentence)."""
    norm = answer.lower().strip().strip('"').rstrip(".")
    return norm == FALLBACK_MESSAGE.lower().rstrip(".")


# ---------------------------------------------------------------------------
# End-to-end entry point  (User question -> answer + sources)
# ---------------------------------------------------------------------------

def ask(question: str, k: int = DEFAULT_TOP_K, with_context: bool = False) -> dict:
    """Run the full RAG flow and return {"answer", "sources"}.

    Flow (matches planning.md "Application Flow"):
      1. user question -> 2. retrieve top-k chunks -> 3. build grounded prompt
      -> 4. send to Groq -> 5. generate answer -> 6. return answer + sources.

    Args:
        question: the user's question.
        k: number of chunks to retrieve (defaults to planning.md's top-k = 5).
        with_context: if True, also return the retrieved hits under "contexts"
            (used by the UI/tests to display the retrieved chunks).
    """
    question = (question or "").strip()
    if not question:
        return {"answer": "Please enter a question.", "sources": []}

    model, collection = _get_pipeline()

    # Step 2: retrieve.
    hits = retrieve(question, model, collection, k=k)

    # No chunks at all -> nothing to ground on -> fallback, no sources.
    if not hits:
        result = {"answer": FALLBACK_MESSAGE, "sources": []}
        if with_context:
            result["contexts"] = []
        return result

    # Step 3 + 4 + 5: build grounded prompt, call Groq, get answer.
    context = build_context(hits)
    answer = generate_answer(question, context)

    # Step 6: programmatic source attribution. If the model declined, return no
    # sources (nothing was actually used to answer).
    sources = [] if _is_fallback(answer) else extract_sources(hits)

    result = {"answer": answer, "sources": sources}
    if with_context:
        result["contexts"] = hits
    return result


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def _print_test(title: str, question: str, k: int = DEFAULT_TOP_K) -> None:
    """Run one test question and print chunks, metadata, answer, grounding note."""
    print("\n" + "#" * 80)
    print(f"# TEST: {title}")
    print(f"# Question: {question}")
    print("#" * 80)

    result = ask(question, k=k, with_context=True)

    # Retrieved chunks + source metadata.
    print("\n-- Retrieved chunks & metadata --")
    for i, hit in enumerate(result["contexts"], 1):
        meta = hit["metadata"]
        print(f"\n  [{i}] {meta.get('source_name')} / {meta.get('source_file')} "
              f"(chunk {meta.get('chunk_index')}, distance {hit['distance']:.4f})")
        print(f"      {hit['text'][:220].replace(chr(10), ' ')}...")

    # Generated answer.
    print("\n-- Generated answer --")
    print(f"  {result['answer']}")

    # Programmatic sources.
    print("\n-- Sources (programmatic) --")
    print(f"  {result['sources'] if result['sources'] else '(none)'}")

    # Grounding assessment.
    print("\n-- Grounded? --")
    if _is_fallback(result["answer"]):
        print("  Correctly declined: context lacked the answer (fallback triggered).")
    else:
        print("  Answer drawn from the retrieved excerpts above; sources cite the "
              "documents actually retrieved.")


def main() -> None:
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    # 1. Clearly answerable from the documents.
    _print_test(
        "Single-document answerable",
        "What barriers can make transferring from a community college difficult?",
    )

    # 2. Requires combining information from multiple retrieved chunks/sources.
    _print_test(
        "Multi-chunk synthesis",
        "What are the differences between UC and CSU, and why might a student "
        "choose community college first?",
    )

    # 3. Not covered by the documents -> should trigger the fallback.
    _print_test(
        "Out-of-scope (fallback expected)",
        "What is the average dorm Wi-Fi speed at MIT, and what's the best pizza "
        "place near campus?",
    )


if __name__ == "__main__":
    main()
