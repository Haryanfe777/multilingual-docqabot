# test_ingestion.py
from app.ingestion import ingest_document

if __name__ == "__main__":
    file_path = "Samples/N1.docx"  # relative to your project root
    result = ingest_document(file_path)
    from pprint import pprint
    pprint(result)