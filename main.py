import os
from dotenv import load_dotenv
load_dotenv()
# Ensure OPENAI_API_KEY is set in your .env file or environment variables
from app.ingestion import ingest_document
from app.rag import EmbeddingModel, embed_chunks, retrieve_relevant_chunks, prepare_chunks_for_embedding
from pprint import pprint
import nltk
from app.embeddings import summarize_document

#from app.embeddings import clear_cache
#clear_cache()

import os
print("Environment proxies:", os.environ.get("HTTPS_PROXY"), os.environ.get("HTTP_PROXY"))

# Set this to your sample file path (PDF, DOCX, or TXT)
SAMPLE_FILE = os.path.join('Samples', 'tncd.pdf')  # Change to your test file

SAMPLE_QUERY = "What treatment options are available for the patient wwith colerectal cancer?"


def main():
    print(f"Ingesting document: {SAMPLE_FILE}")
    try:
        doc = ingest_document(SAMPLE_FILE)
    except Exception as e:
        print(f"Error during ingestion: {e}")
        return

    print("\n--- Document Metadata ---")
    for k, v in doc.items():
        if k != 'text_by_page' and k != 'text':
            print(f"{k}: {v}")

    # Summarize entire document
    print("\n--- Full Document Summary ---")
    try:
        summaries = summarize_document(
            doc,
            mode="document",
            model="gpt-3.5-turbo",
            domain="general",
            max_tokens=256,
            chunk_max_tokens=512,
            overlap=40,
            cache=True
        )
        print(f"Generated {len(summaries)} chunks.")
    except Exception as e:
        print(f"Error during summarization: {e}")
        return

    # Prepare chunks for embedding
    print("\n--- Preparing Chunks for Embedding ---")
    chunks = prepare_chunks_for_embedding(summaries, doc_name=doc['file_name'], language=doc.get('language'))

    # Embed chunks into ChromaDB (OpenAI)
    print("\n--- Embedding Chunks into ChromaDB (OpenAI) ---")
    openai_model = EmbeddingModel(model_name='openai', openai_model='text-embedding-3-small')
    embed_chunks(chunks, openai_model, reembed=False)
    print("Embedding complete.")

    # Run a sample query
    print(f"\n--- Retrieval Demo ---\nQuery: {SAMPLE_QUERY}")
    results = retrieve_relevant_chunks(SAMPLE_QUERY, openai_model, top_k=3, hybrid=True, return_scores=True, mmr=True)
    print("\nTop retrieved chunks:")
    for r in results:
        pprint({k: r[k] for k in ('score', 'text', 'metadata')})

    # Per-page summary (if PDF)
    if doc.get('file_type') == 'pdf':
        print("\n--- Per-Page Summaries ---")
        try:
            page_summaries = summarize_document(doc, mode="page", model="gpt-3.5-turbo", domain="general", max_tokens=256, chunk_max_tokens=512, overlap=40, cache=True)
            for i, page_sum in enumerate(page_summaries):
                print(f"\nPage {i+1} Summary:\n{page_sum['summary'] if isinstance(page_sum, dict) else page_sum}")
        except Exception as e:
            print(f"Error during per-page summarization: {e}")

if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI server on http://localhost:8000 ...")
    print("Make sure you have set your OPENAI_API_KEY in your environment or .env file.")
    uvicorn.run("app.api:app", host="0.0.0.0", port=8000, reload=True)
else:
    print("Make sure you have set your OPENAI_API_KEY in your environment or .env file.")

