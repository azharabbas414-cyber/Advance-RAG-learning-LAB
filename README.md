# 🧠 RAG-X — Phase 1

## Advanced RAG Learning & Experimentation Laboratory

Phase 1 establishes a transparent RAG baseline:

```text
Websites / Documents
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
   Grok 4.6 LLM
        ↓
 Grounded Answer
```

The project is intentionally modular. Future phases will add advanced RAG techniques one by one and show the user the actual before/after results.

---

# 1. Phase 1 capabilities

## Website RAG

Enter at least two public URLs.

Recommended initial test:

```text
https://docs.streamlit.io/
https://docs.python.org/3/
```

The application downloads the HTML, removes scripts/styles, extracts readable text and turns the pages into RAG sources.

## Document RAG

Supported Phase 1 formats:

- PDF
- DOCX
- PPTX
- XLSX / XLSM
- TXT
- Markdown
- CSV
- JSON
- HTML / HTM

The uploader accepts any extension, but the parser intentionally supports a defined set. Unsupported formats are reported rather than silently creating bad text.

---

# 2. Grok LLM

RAG-X Phase 1 uses **xAI Grok** for generation.

Current default:

```text
grok-4.6
```

xAI currently documents `grok-4.6` as its flagship model for coding, agentic tasks and knowledge work. The model supports a 500k-token context window and both Responses API and Chat Completions. 

RAG-X uses the OpenAI-compatible xAI endpoint:

```text
https://api.x.ai/v1
```

The model is configurable through:

```text
XAI_MODEL
```

Default:

```text
grok-4.6
```

This means we can update the model later without changing the RAG architecture.

---

# 3. Configure Grok locally

Create:

```text
.streamlit/secrets.toml
```

Add:

```toml
XAI_API_KEY = "your-xai-api-key"
XAI_MODEL = "grok-4.6"
XAI_BASE_URL = "https://api.x.ai/v1"
```

Do NOT commit this file.

The repository contains:

```text
.streamlit/secrets.toml.example
```

as a safe template.

For local execution, Streamlit exposes secrets through its secrets/environment mechanism. The application expects `XAI_API_KEY` to be available.

---

# 4. Install

Python 3.12 is recommended.

```bash
git clone <YOUR_REPOSITORY_URL>
cd rag-x
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
streamlit run streamlit_app.py
```

---

# 5. First experiment

## Step 1 — Add websites

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

## Step 2 — Build index

Open:

```text
🔧 Build Index
```

Click:

```text
Build / Rebuild Index
```

## Step 3 — Compare retrieval

Open:

```text
🔎 Retrieval Inspector
```

Ask:

```text
What is Streamlit Community Cloud?
```

Run:

```text
Vector
BM25
Hybrid
```

Inspect the actual retrieved chunks.

## Step 4 — Ask Grok

Open:

```text
💬 Grok RAG Chat
```

Ask:

```text
What is Streamlit Community Cloud and how is it deployed?
```

The flow is:

```text
Question
   ↓
Hybrid retrieval
   ↓
Top-K evidence
   ↓
Grok 4.6
   ↓
Grounded answer
```

Grok is instructed to answer only from the supplied evidence and cite it as `[Source N]`.

---

# 6. Important Phase 1 architecture decision

Grok is deliberately isolated:

```text
app/
├── retrieval.py
├── chunking.py
├── loaders/
│
└── llm/
    └── grok.py
```

This is important because future modules can call Grok without putting model-specific code inside every module.

For example:

```text
Query Rewriting
       ↓
     Grok
       ↓
Rewritten query
```

```text
Query Decomposition
       ↓
     Grok
       ↓
Q1 / Q2 / Q3
```

```text
Agentic RAG
       ↓
     Grok
       ↓
Plan → Retrieve → Evaluate → Retrieve
```

---

# 7. Future RAG-X architecture

```text
                    ┌─────────────┐
                    │    Grok     │
                    │   4.6       │
                    └──────┬──────┘
                           │
             ┌─────────────┼──────────────┐
             ↓             ↓              ↓
       Query Rewrite   Decomposition   Agent
             │             │              │
             └─────────────┼──────────────┘
                           ↓
                    Retrieval Layer
                           │
                ┌──────────┼──────────┐
                ↓          ↓          ↓
             Vector       BM25      Graph
                └──────────┼──────────┘
                           ↓
                       Reranker
                           ↓
                  Context Management
                           ↓
                         Grok
                           ↓
                  Grounded Answer
                           ↓
                      Evaluation
```

---

# 8. Streamlit Cloud deployment

Push the project to GitHub.

Then create a Streamlit Community Cloud application using:

```text
Repository:
YOUR_USERNAME/rag-x

Main file:
streamlit_app.py
```

The repository already contains:

```text
requirements.txt
```

For deployment, configure the secret:

```toml
XAI_API_KEY = "your-xai-api-key"
XAI_MODEL = "grok-4.6"
XAI_BASE_URL = "https://api.x.ai/v1"
```

Do this through the Streamlit Cloud Secrets interface rather than committing the key.

The application should use public/sanitized RAG data.

---

# 9. Security

Never put this in GitHub:

```text
XAI_API_KEY = "real-key"
```

Never commit:

```text
.streamlit/secrets.toml
```

Never use real confidential NOC data in the public Streamlit deployment.

For your telecom learning dataset, use:

- public vendor documentation
- RFCs
- sanitized incident reports
- synthetic network data
- publicly available technical documentation

---

# 10. What we learn in Phase 1

By completing Phase 1, you should understand:

1. Document ingestion
2. Website ingestion
3. Text extraction
4. Chunking
5. Vector retrieval
6. BM25
7. Hybrid retrieval
8. Top-K
9. Retrieval scores
10. Evidence inspection
11. Grounded generation
12. Citation handling
13. Separation between retrieval and LLM generation

After this baseline is verified, Phase 2 will introduce the next RAG technique while keeping the Phase 1 baseline available for comparison.
