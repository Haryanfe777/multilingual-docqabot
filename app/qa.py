from typing import List, Dict, Any, Tuple
from openai import OpenAI
import logging
from app.embeddings import get_openai_api_key


def answer_query(query: str, retrieved_chunks: List[Dict[str, Any]], model: str = "gpt-3.5-turbo", max_tokens: int = 512, chat_history: list = None) -> str:
    """
    Answer a user query using retrieved context chunks and an LLM (OpenAI chat completion).
    Only the provided context is used for answering. Optionally, include chat history for conversational memory.
    """
    # Use full retrieved chunks as context (more variation, fewer repeats)
    context = "\n\n".join([chunk['text'] for chunk in retrieved_chunks])
    history_str = ""
    if chat_history:
        for turn in chat_history[-5:]:
            q = turn.get('q') or turn.get('question')
            a = turn.get('a') or turn.get('answer') or turn.get('original')
            if q and a:
                history_str += f"Q: {q}\nA: {a}\n"
    prompt = f"""You are a helpful assistant. Using ONLY the context, give a clear, concise, well-structured answer.

Format strictly as:
- A brief paragraph or direct answer.
- A short bullet list of key points (max 6 bullets).
- If steps are relevant, a numbered list of steps.

Avoid filler text. Do NOT include citations here.

Conversation so far:
{history_str}
Context:
{context}

Question:
{query}

Answer:"""
    try:
        api_key = get_openai_api_key()
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"OpenAI QA call failed: {e}")
        return f"[Error] {e}" 


def _short_snippet(text: str, max_len: int = 160) -> str:
    if not text:
        return ""
    s = " ".join(text.split())
    return (s[:max_len] + "…") if len(s) > max_len else s


def build_sources(retrieved_chunks: List[Dict[str, Any]], max_refs: int = 5) -> List[Dict[str, Any]]:
    """
    Deterministically group retrieved chunks into compact source references.
    Groups by (doc_name, page). Returns up to max_refs sources with fields:
    {index, doc_name, page, chunk_ids, source, snippet}
    """
    groups: Dict[Tuple[str, int], Dict[str, Any]] = {}
    for hit in retrieved_chunks:
        meta = hit.get("metadata", {})
        doc_name = meta.get("doc_name") or meta.get("file_name") or "document"
        page = int(meta.get("page", 0))
        key = (doc_name, page)
        if key not in groups:
            groups[key] = {
                "doc_name": doc_name,
                "page": page,
                "chunk_ids": [],
                "source": meta.get("source", f"{doc_name} - Page {page}"),
                "snippet": _short_snippet(hit.get("text", ""))
            }
        cid = meta.get("chunk_id") or meta.get("uuid")
        if cid:
            groups[key]["chunk_ids"].append(cid)
    # Order by earliest page then by group size desc
    ordered = sorted(groups.values(), key=lambda g: (g.get("page", 0), -len(g.get("chunk_ids", []))))
    sources: List[Dict[str, Any]] = []
    for i, g in enumerate(ordered[:max_refs], start=1):
        g["index"] = i
        sources.append(g)
    return sources


def format_references(sources: List[Dict[str, Any]]) -> str:
    if not sources:
        return ""
    lines = ["References:"]
    for s in sources:
        page_part = f" p. {s['page']}" if s.get("page", 0) else ""
        lines.append(f"[{s['index']}] {s['doc_name']}{page_part} — \"{s['snippet']}\"")
    return "\n".join(lines)