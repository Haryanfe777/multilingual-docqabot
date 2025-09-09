import argparse
import os
from typing import List, Dict, Any

from app.rag import EmbeddingModel, retrieve_relevant_chunks, get_chroma_client, get_or_create_collection
from app.eval import load_jsonl, save_jsonl, evaluate_single


def main():
    parser = argparse.ArgumentParser(description="Run RAG retrieval evaluation")
    parser.add_argument("eval_file", help="Path to eval JSONL (fields: query, relevant_refs, [cited_refs])")
    parser.add_argument("--top_k", type=int, default=5)
    parser.add_argument("--collection", type=str, default="doc_chunks")
    parser.add_argument("--out", type=str, default="eval_results.jsonl")
    args = parser.parse_args()

    eval_rows = load_jsonl(args.eval_file)
    client = get_chroma_client()
    _ = get_or_create_collection(client, args.collection)
    embedder = EmbeddingModel(model_name='openai')

    out_rows: List[Dict[str, Any]] = []
    for row in eval_rows:
        q = row.get("query", "")
        results = retrieve_relevant_chunks(q, embedder, top_k=args.top_k, hybrid=True, return_scores=True, mmr=True)
        metrics = evaluate_single(q, row, results, k=args.top_k)
        out = {"query": q, **metrics}
        out_rows.append(out)
        print(out)

    save_jsonl(args.out, out_rows)
    print(f"Saved results to {args.out}")


if __name__ == "__main__":
    main()


