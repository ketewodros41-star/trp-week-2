import re
import logging
from typing import List, Dict

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class DocAnalyst:
    """Forensic tools for analyzing PDF reports with chunked ingestion (RAG-lite)."""

    def __init__(self):
        self._chunks: List[Dict[str, str]] = []

    def ingest_pdf(self, pdf_path: str) -> str:
        """
        Converts PDF to text using PyMuPDF with page-level chunking.
        Stores chunks internally for targeted retrieval via query_chunks().
        Returns the full text for backward compatibility.
        """
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            self._chunks = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                full_text += page_text

                # Split each page further by heading-like sections
                sections = self._split_by_headings(page_text, page_num + 1)
                self._chunks.extend(sections)

            doc.close()
            logger.info(
                f"DocAnalyst ingested {len(doc)} pages into {len(self._chunks)} chunks "
                f"from {pdf_path}"
            )
            return full_text
        except Exception as e:
            raise RuntimeError(f"Failed to ingest PDF {pdf_path}: {e}")

    @staticmethod
    def _split_by_headings(page_text: str, page_num: int) -> List[Dict[str, str]]:
        """
        Splits a page's text into chunks by heading patterns.
        A heading is detected as a short line (< 80 chars) followed by
        longer content, or lines that look like Markdown/section headers.
        Falls back to the full page as a single chunk.
        """
        # Try splitting on lines that look like headings
        heading_pattern = re.compile(
            r'^(?:#{1,4}\s+.+|[A-Z][A-Za-z\s:–\-]{3,60})$', re.MULTILINE
        )
        matches = list(heading_pattern.finditer(page_text))

        if len(matches) < 2:
            # Not enough headings found — treat entire page as one chunk
            return [{
                "page": page_num,
                "heading": f"Page {page_num}",
                "content": page_text.strip(),
            }]

        chunks = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(page_text)
            section_text = page_text[start:end].strip()
            if section_text:
                chunks.append({
                    "page": page_num,
                    "heading": match.group().strip(),
                    "content": section_text,
                })

        return chunks if chunks else [{
            "page": page_num,
            "heading": f"Page {page_num}",
            "content": page_text.strip(),
        }]

    def query_chunks(self, keywords: List[str], top_k: int = 3) -> Dict[str, List[Dict]]:
        """
        RAG-lite targeted retrieval: searches stored chunks for keywords
        and returns the most relevant chunks per keyword.
        """
        results: Dict[str, List[Dict]] = {}

        for keyword in keywords:
            scored_chunks = []
            kw_lower = keyword.lower()

            for chunk in self._chunks:
                content_lower = chunk["content"].lower()
                if kw_lower in content_lower:
                    # Score by frequency of keyword in chunk
                    frequency = content_lower.count(kw_lower)
                    scored_chunks.append({
                        "page": chunk["page"],
                        "heading": chunk["heading"],
                        "content": chunk["content"],
                        "relevance_hits": frequency,
                    })

            # Sort by relevance (frequency), return top_k
            scored_chunks.sort(key=lambda c: c["relevance_hits"], reverse=True)
            results[keyword] = scored_chunks[:top_k]

        return results

    def query_concepts(self, text: str, keywords: List[str]) -> Dict[str, str]:
        """
        Chunk-aware concept search. If chunks are available, searches within
        chunks for targeted context. Falls back to line-level search.
        """
        # If we have chunks from ingestion, use chunk-based retrieval
        if self._chunks:
            chunk_results = self.query_chunks(keywords)
            results = {}
            for keyword, chunks in chunk_results.items():
                if chunks:
                    # Return the most relevant chunk's content with page reference
                    best = chunks[0]
                    context = (
                        f"[Page {best['page']}, Section: {best['heading']}]\n"
                        f"{best['content'][:500]}"
                    )
                    if len(chunks) > 1:
                        context += f"\n\n(+{len(chunks) - 1} more matching chunk(s))"
                    results[keyword] = context
                else:
                    results[keyword] = "Term not found."
            return results

        # Fallback: line-level keyword search with context window
        results = {}
        lines = text.split("\n")
        for keyword in keywords:
            found_contexts = []
            for i, line in enumerate(lines):
                if keyword.lower() in line.lower():
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    context = "\n".join(lines[start:end])
                    found_contexts.append(context)

            if found_contexts:
                results[keyword] = "\n---\n".join(found_contexts[:3])
            else:
                results[keyword] = "Term not found."

        return results

    @staticmethod
    def extract_file_paths(text: str) -> List[str]:
        """Extracts potential file paths from the text for cross-referencing."""
        path_pattern = r'[a-zA-Z0-9_\-\/]+\.[a-z]{2,4}'
        matches = re.findall(path_pattern, text)
        return list(set(matches))
