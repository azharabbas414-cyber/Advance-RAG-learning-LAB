# 🧠 RAG-X — Phase 1

## Advanced RAG Learning & Experimentation Platform

This version is intentionally reduced to **only three files** so it can be pasted directly into a GitHub repository and deployed on Streamlit.

```text
rag-x/
├── source.py
├── requirements.txt
└── README.md
```

No additional Python modules are required.

---

# 1. What Phase 1 does

RAG-X Phase 1 builds a transparent baseline RAG pipeline:

```text
Website / Documents
        ↓
   Text Extraction
        ↓
      Chunking
        ↓
 ┌──────┼────────┐
 ↓      ↓        ↓
Vector BM25   Hybrid
 └──────┼────────┘
        ↓
 Retrieved Evidence
        ↓
      Grok 4.6
        ↓
 Grounded Answer
        ↓
    [Source N]
```

The purpose is to understand **how RAG works**, not just build a chatbot.

---

# 2. Three files

## source.py

Contains the complete application:

- Streamlit UI
- Website ingestion
- Document ingestion
- PDF parser
- DOCX parser
- PPTX parser
- XLSX/XLSM parser
- TXT/Markdown parser
- CSV parser
- JSON parser
- HTML parser
- Chunking
- TF-IDF vector retrieval
- BM25 retrieval
- Hybrid retrieval
- Retrieval Inspector
- Grok 4.6 generation
- Grounded-answer prompt
- Source/evidence display

## requirements.txt

Contains all Python dependencies.

## README.md

Contains installation, configuration, deployment and learning instructions.

---

# 3. Supported document formats

Phase 1 supports:

```text
PDF
DOCX
PPTX
XLSX
XLSM
TXT
MD
CSV
JSON
HTML
HTM
```

The uploader accepts files, but unsupported formats are explicitly rejected because a reliable parser is required for each format.

More document loaders can be added in later phases.

---

# 4. Website RAG

The application can ingest public web pages.

The default examples are (you may use one, both, or replace them):

```text
https://docs.streamlit.io/
https://docs.python.org/3/
```

Use one URL or multiple URLs for the initial experiment.

The application:

```text
URL
 ↓
HTTP GET
 ↓
HTML
 ↓
Remove scripts/styles
 ↓
Extract text
 ↓
Chunk
 ↓
Index
```

---

# 5. Grok 4.6

RAG-X uses xAI Grok for the generation layer.

Default model:

```text
grok-4.6
```

xAI's current documentation identifies Grok 4.6 as its flagship model for general knowledge work, coding and agentic tasks.

The xAI OpenAI-compatible API endpoint used by this application is:

```text
https://api.x.ai/v1
```

The code keeps the Grok integration centralized inside `source.py`, so a future model change does not require changing the RAG architecture.

---

# 6. Streamlit Secrets

For Streamlit Cloud, open the application's **Secrets** settings and add:

```toml
XAI_API_KEY = "your-xai-api-key"
XAI_MODEL = "grok-4.6"
XAI_BASE_URL = "https://api.x.ai/v1"
```

Do not put the real API key into GitHub.

Do not commit a secrets file containing the real key.

---

# 7. Local installation

Clone your repository:

```bash
git clone YOUR_GITHUB_REPOSITORY
cd rag-x
```

Create a virtual environment:

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install:

```bash
pip install -r requirements.txt
```

Run:

```bash
streamlit run source.py
```

---

# 8. First experiment

## Step 1 — Load websites

Open:

```text
📚 Sources
```

Use:

```text
https://docs.streamlit.io/
https://docs.python.org/3/
```

Click:

```text
Load Website Sources
```

You should see both sources.

---

## Step 2 — Build the index

Open:

```text
🔧 Build Index
```

Click:

```text
Build / Rebuild Index
```

The application will:

```text
Documents
   ↓
Chunks
   ↓
TF-IDF index
   +
BM25 index
```

---

# 9. Test retrieval

Open:

```text
🔎 Retrieval Inspector
```

Try:

```text
What is Streamlit Community Cloud?
```

Run the same query using:

```text
Vector
BM25
Hybrid
```

Look at:

- returned chunks
- ranking
- retrieval score
- source
- source URL
- actual evidence

This is an important part of learning RAG.

---

# 10. Ask Grok

Open:

```text
💬 Grok RAG Chat
```

Ask:

```text
What is Streamlit Community Cloud?
```

The application performs:

```text
User Question
      ↓
Hybrid Retrieval
      ↓
Top-K Chunks
      ↓
Evidence
      ↓
Grok 4.6
      ↓
Grounded Answer
```

Grok is instructed:

- answer only from retrieved evidence
- do not invent facts
- state when evidence is insufficient
- cite evidence using `[Source N]`

---

# 11. Why Phase 1 uses TF-IDF instead of embeddings

This is intentional.

We want the first RAG experiment to make retrieval behavior easy to understand.

Phase 1:

```text
TF-IDF
+
BM25
+
Hybrid
```

Later:

```text
Phase 3
    ↓
Real Embeddings
    ↓
Semantic Vector Search
```

This lets us compare:

```text
Keyword Search
       vs
Semantic Search
       vs
Hybrid Search
```

and actually see the difference.

---

# 12. Advanced RAG roadmap

RAG-X will evolve from the Phase 1 baseline.

```text
Phase 1  Foundation + Baseline RAG
Phase 2  Advanced Chunking
Phase 3  Embedding Experiments
Phase 4  Hybrid Retrieval
Phase 5  Query Rewriting
Phase 6  Multi-Query
Phase 7  Query Decomposition
Phase 8  HyDE
Phase 9  Reranking
Phase 10 Parent-Child Retrieval
Phase 11 Contextual Retrieval
Phase 12 Metadata Filtering
Phase 13 Context Compression
Phase 14 Query Routing
Phase 15 Graph RAG
Phase 16 Agentic RAG
Phase 17 Self-RAG
Phase 18 Corrective RAG
Phase 19 RAG Evaluation
Phase 20 Experiment Dashboard
```

---

# 13. Learning method

For every new technique we should follow:

```text
1. Understand the concept
        ↓
2. Run Phase 1 baseline
        ↓
3. Implement the new technique
        ↓
4. Run the same query/test
        ↓
5. Compare results
        ↓
6. Measure metrics
        ↓
7. Understand why it improved
        ↓
8. Understand trade-offs
```

Example:

```text
Baseline Chunking
       ↓
Question
       ↓
Retrieved Evidence
       ↓
Result

        VS

Semantic Chunking
       ↓
Same Question
       ↓
Retrieved Evidence
       ↓
Result
```

The objective is to see **what the advanced technique actually changes**.

---

# 14. Important security note

For a public GitHub/Streamlit Cloud project:

Use:

- public documentation
- RFCs
- synthetic network data
- sanitized incident reports
- public technical documents

Do not upload confidential:

- NOC configurations
- customer information
- passwords
- API keys
- private IP/network information
- internal incident reports

For your real telecom/NOC environment, a later version can be designed as an **offline/on-premises RAG + local LLM** system.

---

# 15. GitHub structure

Your repository should contain exactly:

```text
rag-x/
│
├── source.py
├── requirements.txt
└── README.md
```

Then Streamlit uses:

```text
source.py
```

as the main application file.

---

# 16. Streamlit deployment

When creating the Streamlit application:

```text
Repository:
YOUR_USERNAME/rag-x

Branch:
main

Main file:
source.py
```

Then configure the Streamlit Secrets:

```toml
XAI_API_KEY = "your-xai-api-key"
XAI_MODEL = "grok-4.6"
XAI_BASE_URL = "https://api.x.ai/v1"
```

No other application files are required.

---

# 17. Phase 1 success criteria

Phase 1 is considered complete when you can:

- load two websites
- upload supported documents
- build chunks
- build the index
- run Vector retrieval
- run BM25 retrieval
- run Hybrid retrieval
- inspect retrieved evidence
- send retrieved evidence to Grok 4.6
- receive a grounded answer
- see `[Source N]` citations

After that, we can start **Phase 2 — Advanced Chunking** and keep this Phase 1 implementation as the baseline.
