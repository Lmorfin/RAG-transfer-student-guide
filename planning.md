# Project 1 Planning: The Unofficial Guide

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->
**Community College -> CSU/UC Transfer Experiences**

This domain focuses on the experiences and challenges faced by students who transfer from California community colleges to CSU and UC universities. This information is valuable because it includes real student perspectives on transfer preparation, academic expectations, social adjustment, and access to campus resources.

This knowledge is difficult to find through official channels because universities primarily provide information about transfer pathways, admissions requirements, and academic programs. However, they rarely capture the personal experiences, challenges, and advice shared by transfer students themselves.

Much of this information is scattered across online communities such as Reddit, Quora, and other discussion forums. Because the information is spread across many different sources, it can be difficult for prospective transfer students to find, compare, and learn from the experiences of others.


---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

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

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:** 500 Characters

**Overlap:** 50 Characters

**Reasoning:** My document collection contains a mixture of Reddit dicussions, Quora threads, and informational articles. Some documents consist of short student experiences while others contain longer explanations of transfer requirements and transfer pathways. A chunk size of 500 characters is large enough to capture complete thoughts and student experiences while remaining small enough for efficient retrieval. A 50-character overlap helps prevent important information from being lost when a sentence spans multiple chunks.

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:** all-MiniLM-L6-v2 via sentence-transformers (tentative).

**Top-k:** 5

**Production tradeoff reflection:** If cost were not a constraint, I would consider a larger embedding model such as text-embedding-3-large. A larger model may better capture nuanced questions about transfer preparation, transfer shock, academic planning, and student experiences. However, larger models introduce additional API costs, storage requirements, and latency. Since my corpus consists entirely of English-language documents, multilingual support is not a major consideration.

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | Should transfer students complete lower-division requirements before transferring?|Most sources recommend completing lower-division and major prerequisites before transferring. This can save on costs. |
| 2 | What are common reasons students choose community college before a CSU or UC? |Lower cost, flexibility, smaller class sizes, and guaranteed (TAG) transfer opportunities. |
| 3 | What barriers can make transferring from a community college difficult? |Complex transfer requirements, limited course availability, and navigating prerequisite completion. |
| 4 | Can students transfer into majors not offered at their community college? |Yes, students can transfer into majors that are not offered at their community college, but careful prerequisite planning is important. Students should complete the required transferable coursework and major preparation requirements before transferring. |
| 5 | How can students improve their chances of a successful transfer? |Early planning, completing transferable coursework, meeting major prerequisites, and seeking academic guidance. | 

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. Reddit and Quora discussions often contain different opinions and personal experiences. For example some students may strongly recommend completing all lower-vision requirements before transferring, while others may have transferred successfully without doing so. The retrieval system must present these perspectives accurately rather than one opinion as universally correct.

2. Some questions may be better answered by informational articles, while others are best answered by student experiences. The retrieval system may return a Reddit dicussion when a user is looking for factual transfer guidance, this could lead to incomplete or less useful answers.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->
   

```text
┌─────────────────────────┐
│   Document Ingestion    │
│  (Python / plain .txt)  │
│  documents/*.txt        │
│  • Load raw text files  │
│  • Extract metadata     │
│  • Validate documents   │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│       Chunking          │
│  • Chunk size: 500 char │
│  • Overlap: 50 char     │
│  • Generate chunk IDs   │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Embedding + Vector     │
│        Store            │
│  • all-MiniLM-L6-v2     │
│    (sentence-transformers)
│  • ChromaDB             │
│    persistent vector    │
│    database             │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│       Retrieval         │
│  • Embed user query     │
│  • ChromaDB similarity  │
│    search               │
│  • Top-k = 5 chunks     │
│  • Return chunk text +  │
│    source metadata      │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│       Generation        │
│  • Groq API             │
│  • Llama 3.3 70B        │
│    Versatile            │
│  • User question +      │
│    retrieved chunks     │
│  • Grounded response    │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│    Query Interface      │
│  • Gradio Web UI        │
│  • Question input       │
│  • Generated answer     │
│  • Source references    │
└─────────────────────────┘
```
   
---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:** I created a script to scrape forum posts, and articles, I did do some manual work by formatting documents and made sure they are consistent to ensure chunks stay accurate. I will use Claude to help implement document loading and chunking. I will provide my Chunking Strategy section and ask it to create a chunking function using a chunk size of 500 characters and an overlap of 50 characters. I will verify the output by checking chunk sizes and ensuring information is not unnecessarily split. 

**Milestone 4 — Embedding and retrieval:**

**Milestone 5 — Generation and interface:**
