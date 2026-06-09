"""
Milestone 5 (part 2) — Gradio Query Interface
==============================================
RAG system: Community College -> CSU/UC Transfer Experiences

This is the final "Query Interface" box in planning.md's pipeline diagram.
It provides a local web UI that connects to the grounded generation layer
(query.ask) which in turn drives retrieval (retriever.py) + Groq generation.

Run locally:
    .venv/Scripts/python.exe app.py
Then open the printed http://127.0.0.1:7860 URL in your browser.
"""

import gradio as gr

# End-to-end RAG function: question -> {"answer", "sources", "contexts"}.
from query import ask, DEFAULT_TOP_K


def format_sources(result: dict) -> str:
    """Build a readable source list from the retrieval metadata.

    `result["sources"]` is the authoritative deduped filename list. We enrich
    each with its friendly source name + URL (pulled from the retrieved chunks)
    for display, without changing the underlying citation contract.
    """
    if not result["sources"]:
        return "(No sources — the answer was not grounded in the documents.)"

    # Map filename -> (source_name, url) from the retrieved chunk metadata.
    info = {}
    for hit in result.get("contexts", []):
        meta = hit["metadata"]
        info.setdefault(
            meta.get("source_file"),
            (meta.get("source_name", ""), meta.get("url", "")),
        )

    lines = []
    for src in result["sources"]:
        name, url = info.get(src, ("", ""))
        label = f"• {name} — {src}" if name else f"• {src}"
        if url:
            label += f"\n    {url}"
        lines.append(label)
    return "\n".join(lines)


def handle_query(question: str):
    """Gradio callback: run the RAG pipeline and return (answer, sources)."""
    result = ask(question, k=DEFAULT_TOP_K, with_context=True)
    return result["answer"], format_sources(result)


# ---------------------------------------------------------------------------
# UI layout
# ---------------------------------------------------------------------------

with gr.Blocks(title="The Unofficial Transfer Guide") as demo:
    gr.Markdown(
        "# The Unofficial Transfer Guide\n"
        "Ask about transferring from a California community college to a CSU/UC. "
        "Answers are grounded **only** in the collected documents; if the answer "
        "isn't in them, the system will say so."
    )

    # Question input + Ask button.
    question_box = gr.Textbox(
        label="Your question",
        placeholder="e.g. What barriers make transferring from a community college difficult?",
        lines=2,
    )
    ask_button = gr.Button("Ask", variant="primary")

    # Answer + sources outputs.
    answer_box = gr.Textbox(label="Answer", lines=8)
    sources_box = gr.Textbox(label="Retrieved from (sources)", lines=6)

    # A few example questions from the evaluation plan.
    gr.Examples(
        examples=[
            "Should transfer students complete lower-division requirements before transferring?",
            "What are common reasons students choose community college before a CSU or UC?",
            "Can students transfer into majors not offered at their community college?",
        ],
        inputs=question_box,
    )

    # Wire the button and the Enter key to the same handler.
    ask_button.click(handle_query, inputs=question_box, outputs=[answer_box, sources_box])
    question_box.submit(handle_query, inputs=question_box, outputs=[answer_box, sources_box])


if __name__ == "__main__":
    # share=False keeps it local (no external dependency), per the spec.
    demo.launch()
