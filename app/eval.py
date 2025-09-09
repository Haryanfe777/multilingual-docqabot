import json
import math
from typing import List, Dict, Any, Tuple


def normalize_ref(meta: Dict[str, Any]) -> Tuple[str, int]:
    doc = meta.get("doc_name") or meta.get("file_name") or "document"
    page = int(meta.get("page", 0))
    return (doc, page)


def precision_recall_at_k(retrieved: List[Tuple[str, int]], relevant: List[Tuple[str, int]], k: int = 5) -> Dict[str, float]:
    retrieved_k = retrieved[:k]
    rel_set = set(relevant)
    hit = sum(1 for r in retrieved_k if r in rel_set)
    precision = hit / max(1, len(retrieved_k))
    recall = hit / max(1, len(rel_set))
    return {"precision@k": precision, "recall@k": recall}


def citation_accuracy(retrieved: List[Tuple[str, int]], cited: List[Tuple[str, int]]) -> float:
    if not cited:
        return 0.0
    ret_set = set(retrieved)
    correct = sum(1 for c in cited if c in ret_set)
    return correct / len(cited)


def evaluate_single(query: str, ground_truth: Dict[str, Any], system_results: List[Dict[str, Any]], k: int = 5) -> Dict[str, Any]:
    """
    ground_truth expects keys: "relevant_refs": [{doc_name, page}], optional "cited_refs" for expected citations.
    system_results are retrieved chunks: each has text and metadata.
    """
    retrieved_refs = [normalize_ref(r.get("metadata", {})) for r in system_results]
    relevant_refs = [(g.get("doc_name"), int(g.get("page", 0))) for g in ground_truth.get("relevant_refs", [])]
    metrics = precision_recall_at_k(retrieved_refs, relevant_refs, k=k)
    expected_cites = [(c.get("doc_name"), int(c.get("page", 0))) for c in ground_truth.get("cited_refs", [])]
    if expected_cites:
        metrics["citation_accuracy"] = citation_accuracy(retrieved_refs, expected_cites)
    return metrics


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def save_jsonl(path: str, rows: List[Dict[str, Any]]):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


