from app.ingestion import ingest_document
from app.embeddings import summarize_document
from app.rag import EmbeddingModel, embed_chunks, retrieve_relevant_chunks, prepare_chunks_for_embedding
from pprint import pprint
import os

if __name__ == "__main__":
    # 1. Ingest a sample document
    file_path = "Samples/tncd.pdf"  # Change to your test file
    doc = ingest_document(file_path)
    print(f"Ingested: {doc['file_name']} ({doc['file_type']})")

    # 2. Summarize and chunk
    print("Summarizing and chunking...")
    summaries = summarize_document(
        doc,
        mode="document",
        model="gpt-3.5-turbo",  # Use a model you have access to
        domain="general",
        max_tokens=256,
        chunk_max_tokens=512,
        overlap=40,
        cache=True
    )
    print(f"Generated {len(summaries)} chunks.")

    # 3. Prepare chunks for embedding
    chunks = prepare_chunks_for_embedding(summaries, doc_name=doc['file_name'], language=doc.get('language'))

    # 4. Embed chunks into ChromaDB (OpenAI)
    print("Embedding chunks with OpenAI...")
    openai_model = EmbeddingModel(model_name='openai', openai_model='text-embedding-3-small')
    embed_chunks(chunks, openai_model, reembed=False)
    print("Embedding complete.")

    # 5. Run a sample query
    query = "What is the candidate's experience with machine learning and AI?"
    print(f"\nQuery: {query}")
    results = retrieve_relevant_chunks(query, openai_model, top_k=3, hybrid=True, return_scores=True, mmr=True)
    print("\nTop retrieved chunks (OpenAI):")
    for r in results:
        pprint({k: r[k] for k in ('score', 'text', 'metadata')})

    # 6. (Optional) Embed and retrieve with SentenceTransformers if available
    try:
        print("\nEmbedding chunks with SentenceTransformers...")
        st_model = EmbeddingModel(model_name='sentence-transformers', st_model='all-MiniLM-L6-v2')
        embed_chunks(chunks, st_model, collection_name='doc_chunks_st', reembed=False)
        print("Embedding complete (ST). Running query...")
        results_st = retrieve_relevant_chunks(query, st_model, collection_name='doc_chunks_st', top_k=3, hybrid=True, return_scores=True, mmr=True)
        print("\nTop retrieved chunks (SentenceTransformers):")
        for r in results_st:
            pprint({k: r[k] for k in ('score', 'text', 'metadata')})
    except Exception as e:
        print(f"SentenceTransformers embedding not available or failed: {e}") 