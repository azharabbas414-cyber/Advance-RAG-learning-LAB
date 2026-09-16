"""
RAG-X — Phase 1
Advanced RAG Learning & Experimentation Platform

Single-file Streamlit application.

Features:
- Website URL ingestion (2+ URLs)
- PDF, DOCX, PPTX, XLSX/XLSM, TXT, MD, CSV, JSON, HTML/HTM upload
- Transparent recursive-style chunking baseline
- TF-IDF vector retrieval
- BM25 retrieval
- Hybrid retrieval using Reciprocal Rank Fusion
- Retrieval Inspector with scores and evidence
- Grounded generation using xAI Grok 4.6
- No external application modules required

Streamlit Secrets:
    XAI_API_KEY = "your-xai-api-key"
    XAI_MODEL = "grok-4.6"
    XAI_BASE_URL = "https://api.x.ai/v1"

Run:
    streamlit run source.py
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import requests
import streamlit as st
from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from openai import OpenAI
from openpyxl import load_workbook
from pptx import Presentation
from pypdf import PdfReader
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize


# ============================================================
# Configuration
# ============================================================

DEFAULT_GROK_MODEL = "grok-4.6"
DEFAULT_XAI_BASE_URL = "https://api.x.ai/v1"

SUPPORTED_UPLOAD_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".xlsm",
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".html",
    ".htm",
}


# ============================================================
# Data Models
# ============================================================

@dataclass
class SourceDocument:
    source_id: str
    source_name: str
    source_type: str
    source_uri: str
    text: str
    metadata: dict


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    source_name: str
    source_uri: str
    text: str
    metadata: dict


# ============================================================
# Configuration Helpers
# ============================================================

def get_secret_or_env(name: str, default: str | None = None) -> str | None:
    """
    Read configuration from Streamlit Secrets first, then environment.
    This allows the same code to work locally and on Streamlit Cloud.
    """
    try:
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass

    return os.getenv(name, default)


def get_grok_model() -> str:
    return get_secret_or_env(
        "XAI_MODEL",
        DEFAULT_GROK_MODEL,
    ) or DEFAULT_GROK_MODEL


def get_xai_base_url() -> str:
    return get_secret_or_env(
        "XAI_BASE_URL",
        DEFAULT_XAI_BASE_URL,
    ) or DEFAULT_XAI_BASE_URL


# ============================================================
# Text Utilities
# ============================================================

def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def make_id(name: str, text: str) -> str:
    return hashlib.sha1(
        f"{name}:{text[:500]}".encode(
            "utf-8",
            errors="ignore",
        )
    ).hexdigest()[:16]


# ============================================================
# Document Loaders
# ============================================================

def load_pdf(data: bytes, name: str) -> SourceDocument:
    reader = PdfReader(io.BytesIO(data))
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        if text.strip():
            pages.append(
                f"[Page {page_number}]\n{text}"
            )

    text = clean_text("\n\n".join(pages))

    return SourceDocument(
        source_id=make_id(name, text),
        source_name=name,
        source_type="pdf",
        source_uri=name,
        text=text,
        metadata={
            "pages": len(reader.pages),
        },
    )


def load_docx(data: bytes, name: str) -> SourceDocument:
    document = DocxDocument(io.BytesIO(data))
    parts = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            parts.append(paragraph.text)

    for table in document.tables:
        for row in table.rows:
            values = [
                cell.text.strip()
                for cell in row.cells
            ]

            if any(values):
                parts.append(" | ".join(values))

    text = clean_text("\n".join(parts))

    return SourceDocument(
        source_id=make_id(name, text),
        source_name=name,
        source_type="docx",
        source_uri=name,
        text=text,
        metadata={},
    )


def load_pptx(data: bytes, name: str) -> SourceDocument:
    presentation = Presentation(io.BytesIO(data))
    slides = []

    for slide_number, slide in enumerate(
        presentation.slides,
        start=1,
    ):
        texts = []

        for shape in slide.shapes:
            if hasattr(shape, "text"):
                if shape.text and shape.text.strip():
                    texts.append(shape.text)

        if texts:
            slides.append(
                f"[Slide {slide_number}]\n"
                + "\n".join(texts)
            )

    text = clean_text("\n\n".join(slides))

    return SourceDocument(
        source_id=make_id(name, text),
        source_name=name,
        source_type="pptx",
        source_uri=name,
        text=text,
        metadata={
            "slides": len(presentation.slides),
        },
    )


def load_xlsx(data: bytes, name: str) -> SourceDocument:
    workbook = load_workbook(
        io.BytesIO(data),
        read_only=True,
        data_only=True,
    )

    sheets = []

    for worksheet in workbook.worksheets:
        rows = []

        for row in worksheet.iter_rows(
            values_only=True,
        ):
            values = [
                "" if value is None else str(value)
                for value in row
            ]

            if any(value.strip() for value in values):
                rows.append(
                    " | ".join(values)
                )

        if rows:
            sheets.append(
                f"[Sheet: {worksheet.title}]\n"
                + "\n".join(rows)
            )

    text = clean_text("\n\n".join(sheets))

    return SourceDocument(
        source_id=make_id(name, text),
        source_name=name,
        source_type="xlsx",
        source_uri=name,
        text=text,
        metadata={
            "sheets": workbook.sheetnames,
        },
    )


def load_text(
    data: bytes,
    name: str,
    source_type: str,
) -> SourceDocument:
    text = data.decode(
        "utf-8",
        errors="replace",
    )

    text = clean_text(text)

    return SourceDocument(
        source_id=make_id(name, text),
        source_name=name,
        source_type=source_type,
        source_uri=name,
        text=text,
        metadata={},
    )


def load_csv(data: bytes, name: str) -> SourceDocument:
    decoded = data.decode(
        "utf-8",
        errors="replace",
    )

    reader = csv.reader(
        io.StringIO(decoded)
    )

    rows = [
        " | ".join(row)
        for row in reader
    ]

    text = clean_text(
        "\n".join(rows)
    )

    return SourceDocument(
        source_id=make_id(name, text),
        source_name=name,
        source_type="csv",
        source_uri=name,
        text=text,
        metadata={},
    )


def load_json(data: bytes, name: str) -> SourceDocument:
    obj = json.loads(
        data.decode(
            "utf-8",
            errors="replace",
        )
    )

    text = json.dumps(
        obj,
        ensure_ascii=False,
        indent=2,
    )

    return SourceDocument(
        source_id=make_id(name, text),
        source_name=name,
        source_type="json",
        source_uri=name,
        text=text,
        metadata={},
    )


def load_html(
    data: bytes,
    name: str,
) -> SourceDocument:
    soup = BeautifulSoup(
        data,
        "html.parser",
    )

    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
        ]
    ):
        tag.decompose()

    text = clean_text(
        soup.get_text("\n")
    )

    return SourceDocument(
        source_id=make_id(name, text),
        source_name=name,
        source_type="html",
        source_uri=name,
        text=text,
        metadata={},
    )


def load_uploaded_file(
    uploaded_file,
) -> SourceDocument:
    name = uploaded_file.name
    extension = Path(name).suffix.lower()
    data = uploaded_file.getvalue()

    if extension == ".pdf":
        return load_pdf(data, name)

    if extension == ".docx":
        return load_docx(data, name)

    if extension == ".pptx":
        return load_pptx(data, name)

    if extension in {".xlsx", ".xlsm"}:
        return load_xlsx(data, name)

    if extension == ".csv":
        return load_csv(data, name)

    if extension == ".json":
        return load_json(data, name)

    if extension in {".html", ".htm"}:
        return load_html(data, name)

    if extension in {".txt", ".md"}:
        return load_text(
            data,
            name,
            extension.lstrip("."),
        )

    raise ValueError(
        f"Unsupported file type: {extension}. "
        f"Supported formats: "
        f"{', '.join(sorted(SUPPORTED_UPLOAD_EXTENSIONS))}"
    )


# ============================================================
# Website Loader
# ============================================================

def load_url(
    url: str,
    timeout: int = 20,
) -> SourceDocument:
    parsed = urlparse(url)

    if parsed.scheme not in {
        "http",
        "https",
    }:
        raise ValueError(
            "URL must start with http:// or https://"
        )

    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(compatible; RAG-X/1.0)"
            )
        },
    )

    if response.status_code == 403:
        raise ValueError(
            "HTTP 403 Forbidden — the website is blocking automated "
            "requests. Try another accessible page or download the "
            "documentation and upload the PDF/document instead."
        )

    if response.status_code == 401:
        raise ValueError(
            "HTTP 401 Unauthorized — this page requires authentication."
        )

    if response.status_code == 429:
        raise ValueError(
            "HTTP 429 Too Many Requests — the website is rate limiting "
            "automated requests. Try again later."
        )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
        ]
    ):
        tag.decompose()

    title = (
        soup.title.get_text(
            " ",
            strip=True,
        )
        if soup.title
        else url
    )

    text = clean_text(
        soup.get_text("\n")
    )

    return SourceDocument(
        source_id=make_id(url, text),
        source_name=title[:200],
        source_type="url",
        source_uri=url,
        text=text,
        metadata={
            "status_code": response.status_code,
        },
    )


def load_urls(
    urls: list[str],
) -> list[SourceDocument]:
    documents = []

    for url in urls:
        url = url.strip()

        if not url:
            continue

        documents.append(
            load_url(url)
        )

    return documents


# ============================================================
# Chunking — Phase 1 Baseline
# ============================================================

def recursive_chunks(
    text: str,
    chunk_size: int = 900,
    overlap: int = 150,
) -> list[str]:
    """
    Lightweight recursive-style chunking baseline.

    Later RAG-X phases will implement and compare:
    - fixed chunking
    - recursive chunking
    - semantic chunking
    - parent-child chunking
    - contextual chunking
    """

    text = text.strip()

    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be greater than zero."
        )

    overlap = max(
        0,
        min(overlap, chunk_size - 1),
    )

    separators = [
        "\n\n",
        "\n",
        ". ",
        " ",
    ]

    blocks = [text]

    for separator in separators:
        if all(
            len(block) <= chunk_size
            for block in blocks
        ):
            break

        new_blocks = []

        for block in blocks:
            if len(block) <= chunk_size:
                new_blocks.append(block)
                continue

            parts = block.split(separator)
            current = ""

            for part in parts:
                candidate = (
                    f"{current}"
                    f"{separator if current else ''}"
                    f"{part}"
                )

                if len(candidate) <= chunk_size:
                    current = candidate
                else:
                    if current.strip():
                        new_blocks.append(
                            current.strip()
                        )

                    current = part

            if current.strip():
                new_blocks.append(
                    current.strip()
                )

        blocks = new_blocks

    final_chunks = []

    for block in blocks:
        if len(block) <= chunk_size:
            final_chunks.append(block)
            continue

        start = 0

        while start < len(block):
            end = min(
                start + chunk_size,
                len(block),
            )

            piece = block[start:end].strip()

            if piece:
                final_chunks.append(piece)

            if end >= len(block):
                break

            start = max(
                0,
                end - overlap,
            )

    return [
        chunk
        for chunk in final_chunks
        if chunk.strip()
    ]


def make_chunks(
    documents: list[SourceDocument],
    chunk_size: int = 900,
    overlap: int = 150,
) -> list[Chunk]:
    chunks = []

    for document in documents:
        pieces = recursive_chunks(
            document.text,
            chunk_size,
            overlap,
        )

        for index, piece in enumerate(pieces):
            chunks.append(
                Chunk(
                    chunk_id=(
                        f"{document.source_id}"
                        f"-{index:04d}"
                    ),
                    document_id=document.source_id,
                    source_name=document.source_name,
                    source_uri=document.source_uri,
                    text=piece,
                    metadata={
                        "source_type": document.source_type,
                        "chunk_index": index,
                        **document.metadata,
                    },
                )
            )

    return chunks


# ============================================================
# Retrieval Engine
# ============================================================

class RetrievalIndex:
    """
    Phase 1 transparent retrieval engine.

    Vector retrieval:
        TF-IDF + cosine similarity

    Keyword retrieval:
        BM25

    Hybrid:
        Reciprocal Rank Fusion (RRF)
    """

    def __init__(
        self,
        chunks: list[Chunk],
    ):
        if not chunks:
            raise ValueError(
                "Cannot build an index without chunks."
            )

        self.chunks = chunks

        texts = [
            chunk.text
            for chunk in chunks
        ]

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            max_features=50000,
            stop_words="english",
        )

        self.matrix = normalize(
            self.vectorizer.fit_transform(texts)
        )

        self.bm25 = BM25Okapi(
            [
                chunk.text.lower().split()
                for chunk in chunks
            ]
        )

    def vector_search(
        self,
        query: str,
        k: int = 5,
    ) -> list[dict]:
        query_vector = normalize(
            self.vectorizer.transform([query])
        )

        scores = (
            self.matrix
            @ query_vector.T
        ).toarray().ravel()

        order = np.argsort(
            -scores
        )[:k]

        return [
            {
                "rank": rank + 1,
                "score": float(scores[index]),
                "chunk": self.chunks[index],
            }
            for rank, index in enumerate(order)
        ]

    def bm25_search(
        self,
        query: str,
        k: int = 5,
    ) -> list[dict]:
        scores = self.bm25.get_scores(
            query.lower().split()
        )

        order = np.argsort(
            -scores
        )[:k]

        return [
            {
                "rank": rank + 1,
                "score": float(scores[index]),
                "chunk": self.chunks[index],
            }
            for rank, index in enumerate(order)
        ]

    def hybrid_search(
        self,
        query: str,
        k: int = 5,
    ) -> list[dict]:
        retrieval_k = max(
            k * 3,
            10,
        )

        vector_results = self.vector_search(
            query,
            retrieval_k,
        )

        bm25_results = self.bm25_search(
            query,
            retrieval_k,
        )

        fused = {}

        # Reciprocal Rank Fusion
        # RRF score = 1 / (60 + rank)

        for item in vector_results:
            chunk = item["chunk"]
            chunk_id = chunk.chunk_id

            if chunk_id not in fused:
                fused[chunk_id] = {
                    "chunk": chunk,
                    "score": 0.0,
                }

            fused[chunk_id]["score"] += (
                1 / (60 + item["rank"])
            )

        for item in bm25_results:
            chunk = item["chunk"]
            chunk_id = chunk.chunk_id

            if chunk_id not in fused:
                fused[chunk_id] = {
                    "chunk": chunk,
                    "score": 0.0,
                }

            fused[chunk_id]["score"] += (
                1 / (60 + item["rank"])
            )

        ranked = sorted(
            fused.values(),
            key=lambda item: item["score"],
            reverse=True,
        )[:k]

        return [
            {
                "rank": rank + 1,
                "score": float(item["score"]),
                "chunk": item["chunk"],
            }
            for rank, item in enumerate(ranked)
        ]


# ============================================================
# Grok 4.6
# ============================================================

def get_grok_client() -> OpenAI:
    api_key = get_secret_or_env(
        "XAI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "XAI_API_KEY is not configured. "
            "Add it in Streamlit Secrets."
        )

    return OpenAI(
        api_key=api_key,
        base_url=get_xai_base_url(),
    )


def generate_grounded_answer(
    query: str,
    results: list[dict],
) -> str:
    client = get_grok_client()
    model = get_grok_model()

    evidence_parts = []

    for source_number, item in enumerate(
        results,
        start=1,
    ):
        chunk = item["chunk"]

        evidence_parts.append(
            f"[Source {source_number}]\n"
            f"Name: {chunk.source_name}\n"
            f"URI: {chunk.source_uri}\n"
            f"Content:\n{chunk.text}"
        )

    evidence = "\n\n".join(
        evidence_parts
    )

    system_prompt = """
You are RAG-X, a grounded retrieval assistant.

Rules:
1. Answer only from the supplied retrieved evidence.
2. Do not invent facts.
3. If the evidence does not contain enough information,
   explicitly say that the available evidence is insufficient.
4. Cite supporting evidence using [Source N].
5. Do not create citations for sources that were not supplied.
6. Prefer a clear, concise technical answer.
""".strip()

    user_prompt = (
        f"Question:\n{query}\n\n"
        f"Retrieved evidence:\n{evidence}"
    )

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    )

    return response.output_text


# ============================================================
# Streamlit State
# ============================================================

def initialize_state() -> None:
    defaults = {
        "documents": [],
        "chunks": [],
        "index": None,
        "last_results": [],
        "last_query": "",
        "last_method": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ============================================================
# UI Helpers
# ============================================================

def show_source_summary() -> None:
    documents = st.session_state.documents

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Sources",
        len(documents),
    )

    col2.metric(
        "Chunks",
        len(st.session_state.chunks),
    )

    col3.metric(
        "Grok Model",
        get_grok_model(),
    )

    if documents:
        counts = {}

        for document in documents:
            counts[document.source_type] = (
                counts.get(
                    document.source_type,
                    0,
                )
                + 1
            )

        st.caption(
            " | ".join(
                f"{source_type}: {count}"
                for source_type, count
                in counts.items()
            )
        )


# ============================================================
# Main Streamlit Application
# ============================================================

def main() -> None:
    st.set_page_config(
        page_title="RAG-X | Phase 1",
        page_icon="🧠",
        layout="wide",
    )

    initialize_state()

    st.title("🧠 RAG-X")
    st.caption(
        "Phase 1 — Source Ingestion + Baseline Retrieval + "
        "Grok 4.6 Grounded Generation"
    )

    # --------------------------------------------------------
    # Sidebar
    # --------------------------------------------------------

    with st.sidebar:
        st.header("Phase 1 Pipeline")

        st.write("1. Ingest websites/documents")
        st.write("2. Chunk documents")
        st.write("3. Build retrieval index")
        st.write("4. Compare Vector / BM25 / Hybrid")
        st.write("5. Inspect retrieved evidence")
        st.write("6. Generate answer with Grok")

        st.divider()

        st.subheader("Chunk Settings")

        chunk_size = st.slider(
            "Chunk size",
            min_value=300,
            max_value=1800,
            value=900,
            step=50,
        )

        overlap = st.slider(
            "Chunk overlap",
            min_value=0,
            max_value=400,
            value=150,
            step=25,
        )

        top_k = st.slider(
            "Top K",
            min_value=1,
            max_value=10,
            value=5,
        )

        st.divider()

        st.subheader("Grok")

        st.code(
            f"Model: {get_grok_model()}\n"
            f"API: {get_xai_base_url()}"
        )

        if get_secret_or_env("XAI_API_KEY"):
            st.success(
                "XAI_API_KEY detected"
            )
        else:
            st.warning(
                "XAI_API_KEY not detected"
            )

    # --------------------------------------------------------
    # Tabs
    # --------------------------------------------------------

    sources_tab, index_tab, retrieval_tab, chat_tab = st.tabs(
        [
            "📚 Sources",
            "🔧 Build Index",
            "🔎 Retrieval Inspector",
            "💬 Grok RAG Chat",
        ]
    )

    # ========================================================
    # SOURCES
    # ========================================================

    with sources_tab:
        st.subheader("Website RAG")

        st.info(
            "Add one or more public website URLs. "
            "You can start with a single URL or add multiple URLs "
            "for a larger RAG knowledge base."
        )

        urls_text = st.text_area(
            "Website URLs — one or more, one per line",
            value=(
                "https://docs.streamlit.io/\n"
                "https://docs.python.org/3/"
            ),
            height=120,
        )

        if st.button(
            "🌐 Load Website Sources",
            use_container_width=True,
        ):
            urls = [
                url.strip()
                for url in urls_text.splitlines()
                if url.strip()
            ]

            if not urls:
                st.error(
                    "Please enter at least one URL."
                )
            else:
                successful_documents = []
                failed_urls = []

                progress = st.progress(
                    0,
                    text="Starting website ingestion..."
                )

                for number, url in enumerate(urls, start=1):
                    try:
                        document = load_url(url)
                        successful_documents.append(document)

                    except Exception as exc:
                        failed_urls.append(
                            {
                                "url": url,
                                "error": str(exc),
                            }
                        )

                    progress.progress(
                        number / len(urls),
                        text=f"Processed {number}/{len(urls)} URL(s)"
                    )

                progress.empty()

                if successful_documents:
                    st.session_state.documents.extend(
                        successful_documents
                    )

                    st.success(
                        f"Loaded {len(successful_documents)} "
                        f"website source(s)."
                    )

                if failed_urls:
                    st.warning(
                        f"{len(failed_urls)} URL(s) could not be loaded."
                    )

                    for failure in failed_urls:
                        st.error(
                            f"{failure['url']} — {failure['error']}"
                        )

        st.divider()

        st.subheader("Document RAG")

        st.caption(
            "Phase 1 supports: PDF, DOCX, PPTX, XLSX/XLSM, "
            "TXT, MD, CSV, JSON and HTML/HTM."
        )

        uploaded_files = st.file_uploader(
            "Upload one or more documents",
            type=None,
            accept_multiple_files=True,
        )

        if st.button(
            "📥 Ingest Uploaded Documents",
            use_container_width=True,
        ):
            if not uploaded_files:
                st.warning(
                    "Please select at least one file."
                )
            else:
                successful = 0

                for uploaded_file in uploaded_files:
                    try:
                        document = load_uploaded_file(
                            uploaded_file
                        )

                        st.session_state.documents.append(
                            document
                        )

                        successful += 1

                    except Exception as exc:
                        st.error(
                            f"{uploaded_file.name}: {exc}"
                        )

                if successful:
                    st.success(
                        f"Ingested {successful} document(s)."
                    )

        st.divider()

        st.subheader("Current Sources")
        show_source_summary()

        if not st.session_state.documents:
            st.info(
                "No sources loaded yet."
            )

        for document in st.session_state.documents:
            with st.expander(
                f"{document.source_type.upper()} — "
                f"{document.source_name}"
            ):
                st.write(
                    f"**Source:** {document.source_uri}"
                )

                st.write(
                    f"**Characters:** "
                    f"{len(document.text):,}"
                )

                preview = document.text[:1500]

                if len(document.text) > 1500:
                    preview += "..."

                st.text(preview)

    # ========================================================
    # BUILD INDEX
    # ========================================================

    with index_tab:
        st.subheader(
            "Build / Rebuild Phase 1 Index"
        )

        if not st.session_state.documents:
            st.warning(
                "Add at least one source first."
            )
        else:
            st.write(
                f"Documents: "
                f"**{len(st.session_state.documents)}**"
            )

            st.write(
                f"Chunk size: **{chunk_size}** | "
                f"Overlap: **{overlap}**"
            )

            if st.button(
                "🚀 Build / Rebuild Index",
                type="primary",
                use_container_width=True,
            ):
                try:
                    with st.spinner(
                        "Chunking documents and building indexes..."
                    ):
                        chunks = make_chunks(
                            st.session_state.documents,
                            chunk_size=chunk_size,
                            overlap=overlap,
                        )

                        index = RetrievalIndex(
                            chunks
                        )

                        st.session_state.chunks = chunks
                        st.session_state.index = index
                        st.session_state.last_results = []

                    st.success(
                        f"Index ready: "
                        f"{len(chunks)} chunks."
                    )

                except Exception as exc:
                    st.error(
                        f"Index build failed: {exc}"
                    )

            if st.session_state.chunks:
                st.subheader(
                    "Chunk Preview"
                )

                for chunk in st.session_state.chunks[:8]:
                    with st.expander(
                        f"{chunk.source_name} | "
                        f"chunk {chunk.metadata['chunk_index']}"
                    ):
                        st.write(chunk.text)

    # ========================================================
    # RETRIEVAL INSPECTOR
    # ========================================================

    with retrieval_tab:
        st.subheader(
            "Retrieval Inspector"
        )

        if st.session_state.index is None:
            st.warning(
                "Build the index first."
            )
        else:
            query = st.text_input(
                "Test query",
                value=(
                    "What is Streamlit Community Cloud?"
                ),
            )

            method = st.selectbox(
                "Retrieval method",
                [
                    "Vector",
                    "BM25",
                    "Hybrid",
                ],
            )

            if st.button(
                "🔎 Run Retrieval",
                use_container_width=True,
            ):
                if method == "Vector":
                    results = (
                        st.session_state.index
                        .vector_search(
                            query,
                            top_k,
                        )
                    )

                elif method == "BM25":
                    results = (
                        st.session_state.index
                        .bm25_search(
                            query,
                            top_k,
                        )
                    )

                else:
                    results = (
                        st.session_state.index
                        .hybrid_search(
                            query,
                            top_k,
                        )
                    )

                st.session_state.last_results = results
                st.session_state.last_query = query
                st.session_state.last_method = method

            if st.session_state.last_results:
                st.success(
                    f"Method: "
                    f"{st.session_state.last_method} | "
                    f"Query: "
                    f"{st.session_state.last_query}"
                )

                for item in st.session_state.last_results:
                    chunk = item["chunk"]

                    st.markdown(
                        f"### #{item['rank']} — "
                        f"score {item['score']:.4f}"
                    )

                    st.caption(
                        f"{chunk.source_name} | "
                        f"{chunk.source_uri}"
                    )

                    st.write(
                        chunk.text
                    )

                    st.divider()

    # ========================================================
    # GROK RAG CHAT
    # ========================================================

    with chat_tab:
        st.subheader(
            "Grok 4.6 Grounded RAG"
        )

        st.info(
            f"Generation model: "
            f"`{get_grok_model()}`"
        )

        if st.session_state.index is None:
            st.warning(
                "Build the index first."
            )
        else:
            query = st.chat_input(
                "Ask a question about your sources..."
            )

            if query:
                with st.spinner(
                    "Retrieving evidence..."
                ):
                    results = (
                        st.session_state.index
                        .hybrid_search(
                            query,
                            top_k,
                        )
                    )

                st.session_state.last_results = results
                st.session_state.last_query = query
                st.session_state.last_method = "Hybrid"

                if not get_secret_or_env(
                    "XAI_API_KEY"
                ):
                    st.error(
                        "XAI_API_KEY is not configured. "
                        "Add it in Streamlit Secrets."
                    )
                else:
                    try:
                        with st.spinner(
                            f"Grok {get_grok_model()} "
                            "is generating..."
                        ):
                            answer = (
                                generate_grounded_answer(
                                    query,
                                    results,
                                )
                            )

                        st.markdown(
                            "### Answer"
                        )

                        st.write(answer)

                    except Exception as exc:
                        st.error(
                            f"Grok API request failed: {exc}"
                        )

                st.markdown(
                    "### Retrieved Evidence"
                )

                for item in results:
                    chunk = item["chunk"]

                    with st.expander(
                        f"[Source {item['rank']}] "
                        f"{chunk.source_name} — "
                        f"score {item['score']:.4f}"
                    ):
                        st.caption(
                            chunk.source_uri
                        )

                        st.write(
                            chunk.text
                        )

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    st.divider()

    st.caption(
        "RAG-X Phase 1 is a transparent baseline. "
        "Advanced RAG techniques will be added one by one "
        "and compared against this baseline."
    )


if __name__ == "__main__":
    main()
