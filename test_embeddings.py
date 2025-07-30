from app.ingestion import ingest_document
from app.embeddings import summarize_document, clear_cache
from pprint import pprint

if __name__ == "__main__":
    # Clear cache for a fresh test (optional)
    clear_cache()

    # Ingest a sample document (PDF, DOCX, or TXT)
    file_path = "Samples/tncd.pdf"  # Change to your test file
    doc = ingest_document(file_path)

    # Summarize the document (document mode)
    print("=== Document Mode Summary ===")
    summaries = summarize_document(
        doc,
        mode="document",
        model="gpt-3.5-turbo",
        domain="medical",  # Try "legal" or "general" as well
        max_tokens=256,
        chunk_max_tokens=512,
        overlap=40,
        cache=True
    )
    pprint(summaries)

    # Summarize per page (if PDF)
    if doc.get("file_type") == "pdf":
        print("\n=== Page Mode Summary ===")
        page_summaries = summarize_document(
            doc,
            mode="page",
            model="gpt-4",
            domain="medical",
            max_tokens=256,
            chunk_max_tokens=512,
            overlap=40,
            cache=True
        )
        pprint(page_summaries)