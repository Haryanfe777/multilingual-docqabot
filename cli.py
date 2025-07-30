import argparse
import os
from dotenv import load_dotenv
load_dotenv()
# Ensure OPENAI_API_KEY is set in your .env file or environment variables
from app.ingestion import ingest_document
from app.embeddings import summarize_document
from app.rag import EmbeddingModel, embed_chunks, retrieve_relevant_chunks, prepare_chunks_for_embedding
from app.qa import answer_query
from pprint import pprint


def main():
    parser = argparse.ArgumentParser(description="Multilingual DocQA RAG CLI")
    parser.add_argument('--file', type=str, required=True, help='Path to document (PDF, DOCX, or TXT)')
    parser.add_argument('--query', type=str, required=True, help='Question to ask')
    parser.add_argument('--top_k', type=int, default=3, help='Number of chunks to retrieve')
    parser.add_argument('--embedding_model', type=str, default='openai', choices=['openai', 'sentence-transformers'], help='Embedding model to use')
    parser.add_argument('--reembed', action='store_true', help='Force re-embedding of all chunks')
    parser.add_argument('--dry_run', action='store_true', help='Dry run (no actual embedding)')
    args = parser.parse_args()

    print(f"Ingesting document: {args.file}")
    doc = ingest_document(args.file)
    print(f"File: {doc['file_name']} | Type: {doc['file_type']}")

    print("\nSummarizing and chunking...")
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

    print("\nPreparing chunks for embedding...")
    chunks = prepare_chunks_for_embedding(summaries, doc_name=doc['file_name'], language=doc.get('language'))

    if args.embedding_model == 'openai':
        print(f"\nEmbedding chunks with OpenAI...")
        embedding_model = EmbeddingModel(model_name='openai', openai_model='text-embedding-3-small')
    else:
        print(f"\nEmbedding chunks with SentenceTransformers...")
        embedding_model = EmbeddingModel(model_name='sentence-transformers', st_model='all-MiniLM-L6-v2')
    embed_chunks(chunks, embedding_model, reembed=args.reembed, dry_run=args.dry_run)
    print("Embedding complete.")

    print(f"\nRetrieving top {args.top_k} relevant chunks for your query...")
    results = retrieve_relevant_chunks(args.query, embedding_model, top_k=args.top_k, hybrid=True, return_scores=True, mmr=True)
    for i, r in enumerate(results):
        print(f"\n--- Chunk {i+1} ---")
        pprint({k: r[k] for k in ('score', 'text', 'metadata')})

    print("\nGetting answer from LLM...")
    answer = answer_query(args.query, results, model="gpt-3.5-turbo")
    print("\n=== FINAL ANSWER ===")
    print(answer)

if __name__ == "__main__":
    main() 