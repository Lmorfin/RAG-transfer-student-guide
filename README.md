# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->
This domain focuses on the experiences and challenges faced by students who transfer from California community colleges to CSU and UC universities. This information is valuable because it includes real student perspectives on transfer preparation, academic expectations, social adjustment, and access to campus resources.

This knowledge is difficult to find through official channels because universities primarily provide information about transfer pathways, admissions requirements, and academic programs. However, they rarely capture the personal experiences, challenges, and advice shared by transfer students themselves.

Much of this information is scattered across online communities such as Reddit, Quora, and other discussion forums. Because the information is spread across many different sources, it can be difficult for prospective transfer students to find, compare, and learn from the experiences of others.

---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | Reddit | Experiences/perspectives about transferring. | documents/reddit_thread_1.txt |
| 2 | Reddit| Should students transfer before completing lower-divison courses? | documents/reddit_thread_2.txt |
| 3 | Reddit| Transferring with a major that is offered at the CSU/UC but not in the current community college. | documents/reddit_thread_3.txt |
| 4 | Reddit | Deciding between enrolling to a CSU/UC or community college right after highschool. | documents/reddit_thread_4.txt |
| 5 | PPIC | This article examines the challenges and opportunities in the California community college–to–CSU transfer pathway, highlighting low transfer rates despite high acceptance rates and proposing strategies to improve student success and bachelor's degree attainment. | documents/ppic_transfer_policy_brief.txt |
| 6 | EdSource| This article discusses the persistent barriers facing California community college students seeking to transfer to UC and CSU campuses, highlighting systemic challenges such as complex transfer requirements, limited course availability, inconsistent admissions policies, and the need for greater collaboration among higher education institutions. | documents/edsource_transfer_roadblocks.txt  |
| 7 | Quora | This Quora thread shares experiences and advice about choosing whether to enroll at a CSU, UC, or CC first. | documents/quora_uc_vs_csu_transfer.txt |
| 8 | BestColleges | This article explains how UC and CSU schools compare. | documents/bestcolleges_uc_vs_csu.txt |
| 9 | CollegeVine |FAQ post of a student asking the differences between CSU and UC schools. | documents/collegevine_csu_vs_uc.txt |
| 10 | PPIC | This article talks about College Affordability in California | documents/ppic_college_affordability_in_ca.txt |
| 11 | Magellan Counseling | This article provides an overview of the college transfer process in California, explaining the requirements for transferring from community colleges or four-year universities to UC, CSU, and other institutions while emphasizing the importance of early planning, completing transferable coursework, meeting major-specific prerequisites, and seeking academic guidance. |documents/magellan_transfer_guide.txt |

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:** 500 Characters

**Overlap:** 50 Characters

**Why these choices fit your documents:** My document collection contains a mixture of Reddit dicussions, Quora threads, and informational articles. Some documents consist of short student experiences while others contain longer explanations of transfer requirements and transfer pathways. A chunk size of 500 characters is large enough to capture complete thoughts and student experiences while remaining small enough for efficient retrieval. A 50-character overlap helps prevent important information from being lost when a sentence spans multiple chunks.


**Final chunk count:** 212 chunks.

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:** all-MiniLM-L6-v2 via sentence-transformers

**Production tradeoff reflection:** If cost were not a constraint, I would consider a larger embedding model such as text-embedding-3-large. A larger model may better capture nuanced questions about transfer preparation, transfer shock, academic planning, and student experiences. However, larger models introduce additional API costs, storage requirements, and latency. Since my corpus consists entirely of English-language documents, multilingual support is not a major consideration.

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:** Answer the user's question using only the information contained in the provided context. Do not use outside knowledge or make assumptions. If the context does not contain enough information to answer the question, respond with: 'I don't have enough information in the provided documents to answer that question

**How source attribution is surfaced in the response:** The system stores source filenames as metadata in ChromaDB during the embedding stage. After retrieval, the filenames associated with the top-k retrieved chunks are collected and appended to the final response programmatically. This ensures source attribution is based on the actual retrieved documents rather than relying on the LLM to generate citations on its own.

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 |Should transfer students complete lower-division requirements before transferring? | Most sources recommend completing lower-division and major prerequisites before transferring. This can save on costs.|According to Excerpt 1, it is recommended to plan early and complete required courses before transferring. Excerpt 5 suggests that completing general education requirements at a community college can save time and money, allowing students to transfer in as juniors. However, Excerpt 4 notes that even when transferring with completed courses, the accepting college can still choose not to accept some classes as credit. Excerpt 5 also presents a personal consideration, where finishing general education requirements before transferring would mean the student's GPA at the new institution would depend entirely on their performance in STEM courses. |Relevant |Accurate |
| 2 |What are common reasons students choose community college before a CSU or UC? | Lower cost, flexibility, smaller class sizes, and guaranteed (TAG) transfer opportunities.| According to the context, common reasons students choose community college before a CSU or UC include: Financial aid, as one student mentions "Money isn't a problem since I got A LOT of aid from fasfa" (Excerpt 5), Priority in transferring, as a CC transfer student comments "they get so much more priority over other types" (Excerpt 5), Knowing what major and classes to take, as one student states "I already know what major and classes I want to take at csulb and ucr" (Excerpt 5). |Partially relevant |Partially accurate |
| 3 |What barriers can make transferring from a community college difficult? |Complex transfer requirements, limited course availability, and navigating prerequisite completion. |According to the context, some barriers that can make transferring from a community college difficult include: Few counselors due to financial constraints, which delays how early students receive information on their academic paths. The lack of required courses being available when students need them. Financial aid limits, and Structural problems that exist in the transfer process. | Relevant | Accurate  |
| 4 |Can students transfer into majors not offered at their community college? |Yes, students can transfer into majors that are not offered at their community college, but careful prerequisite planning is important. Students should complete the required transferable coursework and major preparation requirements before transferring. |I don't have enough information in the provided documents to answer that question. | Off-target | Inaccurate|
| 5 |How can students improve their chances of a successful transfer?  |Early planning, completing transferable coursework, meeting major prerequisites, and seeking academic guidance. |According to the context, students can improve their chances of a successful transfer by: Completing transfer-level English and math in the first year to accelerate transfer-readiness. Receiving better and more proactive advising. Having flexible scheduling, and Increasing on-campus work opportunities to help students enroll full time. Additionally, supporting early momentum and helping students navigate and succeed during their first year, whether in the community college or after transferring to the CSU, should be prioritized. | Relevant | Accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:** Can students transfer into majors not offered at their community college?

**What the system returned:** "I don't have enough information in the provided documents to answer that question."

**Root cause (tied to a specific pipeline stage):** The failure occurred during the retrieval stage. Although information related to this topic existed within the document collection, the retrieval system did not return the relevant chunk among the top-k results. The wording of the query differed from the wording used in the source document, making it difficult for the embedding model to identify the correct chunk as semantically relevant.

**What you would change to fix it:** I would experiment with increasing the chunk size and retrieval value (k) so that more relevant context is available during retrieval. I would also consider using a larger embedding model with stronger semantic understanding to improve retrieval performance on questions that use different wording than the source documents

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:** The planning document provided a clear roadmap for building the RAG pipeline incrementally. By defining the document sources, chunking strategy, retrieval approach, and evaluation questions ahead of time, I was able to implement and test each milestone independently rather than attempting to build the entire system at once. This made debugging much easier when retrieval or generation issues occurred.

**One way your implementation diverged from the spec, and why:** One area where the implementation diverged from the original plan was retrieval performance. While the planned architecture was able to answer most evaluation questions correctly, one question failed because the relevant chunk was not retrieved. This highlighted that retrieval quality depends not only on architecture but also on embedding quality, chunking decisions, and document coverage, which required additional tuning beyond the original specification

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:* My planning.md Documents section, Chunking Strategy section, and pipeline diagram.
- *What it produced:* A Python ingestion pipeline that loaded text files, cleaned document content, split documents into chunks, and attached metadata to each chunk.
- *What I changed or overrode:* I adjusted the chunk size to 500 characters with a 50-character overlap to better fit my collection of Reddit discussions, Quora threads, and transfer-related articles. I also added additional validation output to inspect representative chunks before embedding.

**Instance 2**

- *What I gave the AI:* My Retrieval Approach section from planning.md, ChromaDB requirements, embedding model selection, and pipeline diagram.
- *What it produced:* Code for generating embeddings using all-MiniLM-L6-v2, storing vectors in ChromaDB with metadata, creating a retrieval function, and integrating retrieval with Groq's llama-3.3-70b-versatile model through a Gradio interface.
- *What I changed or overrode:* I modified the system prompt to enforce stricter grounding behavior and implemented source attribution programmatically using retrieved metadata instead of relying on the LLM to generate citations. I also tested multiple retrieval settings before settling on the final top-k configuration.
