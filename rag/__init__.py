"""
EmbedForge RAG Module (Optional) — document retrieval for enhanced context.

Install with: pip install embedforge[rag]
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Optional RAG pipeline for ingesting vendor documentation.

    Provides additional context to the LLM from PDF datasheets,
    reference manuals, and application notes.

    Requires: chromadb, sentence-transformers
    """

    def __init__(self, persist_dir: str = "./rag_data") -> None:
        self._persist_dir = Path(persist_dir)
        self._collection = None
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize the vector store. Returns False if dependencies missing."""
        try:
            import chromadb
            from chromadb.config import Settings

            client = chromadb.Client(
                Settings(
                    persist_directory=str(self._persist_dir),
                    anonymized_telemetry=False,
                )
            )
            self._collection = client.get_or_create_collection(
                name="embedforge_docs",
                metadata={"hnsw:space": "cosine"},
            )
            self._initialized = True
            logger.info(f"RAG initialized with {self._collection.count()} documents")
            return True
        except ImportError:
            logger.warning("RAG dependencies not installed. Run: pip install embedforge[rag]")
            return False

    def ingest_directory(self, docs_path: str, extensions: tuple = (".pdf", ".md", ".txt")) -> int:
        """Ingest documents from a directory into the vector store."""
        if not self._initialized:
            if not self.initialize():
                return 0

        path = Path(docs_path)
        if not path.exists():
            logger.warning(f"Docs path not found: {docs_path}")
            return 0

        count = 0
        for ext in extensions:
            for file in path.rglob(f"*{ext}"):
                try:
                    content = self._load_document(file)
                    if content:
                        chunks = self._chunk_text(content, chunk_size=1000, overlap=200)
                        for i, chunk in enumerate(chunks):
                            self._collection.add(
                                documents=[chunk],
                                ids=[f"{file.stem}_{i}"],
                                metadatas=[{"source": str(file), "chunk": i}],
                            )
                            count += 1
                except Exception as e:
                    logger.warning(f"Failed to ingest {file}: {e}")

        logger.info(f"Ingested {count} chunks from {docs_path}")
        return count

    def query(self, question: str, n_results: int = 5) -> List[str]:
        """Query the vector store for relevant context."""
        if not self._initialized:
            if not self.initialize():
                return []

        results = self._collection.query(
            query_texts=[question],
            n_results=n_results,
        )

        documents = results.get("documents", [[]])[0]
        return documents

    def _load_document(self, path: Path) -> Optional[str]:
        """Load a document file into text."""
        if path.suffix == ".pdf":
            try:
                import fitz  # pymupdf
                doc = fitz.open(str(path))
                return "\n".join(page.get_text() for page in doc)
            except ImportError:
                logger.warning("pymupdf not installed for PDF loading")
                return None
        else:
            return path.read_text(encoding="utf-8", errors="ignore")

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks
