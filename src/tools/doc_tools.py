from typing import List, Dict, Optional
from docling.document_converter import DocumentConverter

class DocAnalyst:
    """Forensic tools for analyzing PDF reports."""

    def __init__(self):
        self.converter = DocumentConverter()

    def ingest_pdf(self, pdf_path: str) -> str:
        """Converts PDF to Markdown/Text for analysis."""
        try:
            result = self.converter.convert(pdf_path)
            return result.document.export_to_markdown()
        except Exception as e:
            raise RuntimeError(f"Failed to ingest PDF {pdf_path}: {e}")

    @staticmethod
    def query_concepts(text: str, keywords: List[str]) -> Dict[str, str]:
        """Simple RAG-lite keyword search with context."""
        results = {}
        lines = text.split("\n")
        for keyword in keywords:
            found_contexts = []
            for i, line in enumerate(lines):
                if keyword.lower() in line.lower():
                    # Get surrounding context
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    context = "\n".join(lines[start:end])
                    found_contexts.append(context)
            
            if found_contexts:
                results[keyword] = "\n---\n".join(found_contexts[:3]) # Limit to 3 snippets
            else:
                results[keyword] = "Term not found."
        
        return results

    @staticmethod
    def extract_file_paths(text: str) -> List[str]:
        """Extracts potential file paths from the text for cross-referencing."""
        import re
        # Basic regex for paths like src/nodes/justice.py or reports/report.pdf
        path_pattern = r'[a-zA-Z0-9_\-\/]+\.[a-z]{2,4}'
        matches = re.findall(path_pattern, text)
        return list(set(matches))
