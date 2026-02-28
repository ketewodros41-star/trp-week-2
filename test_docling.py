from docling.document_converter import DocumentConverter
import sys

print("Initializing DocumentConverter...")
try:
    converter = DocumentConverter()
    print("Converter initialized.")
    
    pdf_path = r"c:\Users\Davea\.gemini\antigravity\scratch\trp-audit-challenge\peer_repo_eyor\reports\Automaton-Auditor_Interim Architecture Report.pdf"
    print(f"Converting {pdf_path}...")
    result = converter.convert(pdf_path)
    print("Conversion complete.")
    print(result.document.export_to_markdown()[:100])
except Exception as e:
    print(f"Error during docling test: {e}")
    sys.exit(1)
finally:
    print("Test script finishing.")
