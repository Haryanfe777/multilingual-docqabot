from typing import List, Dict, Any
from openai import OpenAI
import logging
from app.embeddings import get_openai_api_key


def answer_query(query: str, retrieved_chunks: List[Dict[str, Any]], model: str = "gpt-3.5-turbo", max_tokens: int = 512, chat_history: list = None) -> str:
    """
    Answer a user query using retrieved context chunks and an LLM (OpenAI chat completion).
    Only the provided context is used for answering. Optionally, include chat history for conversational memory.
    """
    context = "\n\n".join([chunk['text'] for chunk in retrieved_chunks])
    history_str = ""
    if chat_history:
        for turn in chat_history[-5:]:
            q = turn.get('q') or turn.get('question')
            a = turn.get('a') or turn.get('answer') or turn.get('original')
            if q and a:
                history_str += f"Q: {q}\nA: {a}\n"
    prompt = f"""You are a helpful assistant. Using the context below, review the uploaded documents and answer the question as explicitly and comprehensively as possible. No fluff or verbose or filler language. If available, use valid examples or scenarios to illustrate the answer.'
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