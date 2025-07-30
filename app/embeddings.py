import os
import hashlib
import logging
import time
import csv
from typing import List, Dict, Any, Optional, Union, Callable

from dotenv import load_dotenv
import tiktoken
import nltk
from nltk.tokenize import sent_tokenize
from openai import RateLimitError
import backoff

load_dotenv()


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Download punkt for sentence tokenization if not already present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt_tab')

# Default summarization prompts by domain
SUMMARIZATION_PROMPTS = {
    "medical": "You are a medical document assistant. Summarize the following text concisely and clearly for a medical professional. Focus on key findings, diagnoses, treatments, and relevant details.\n\nText:\n{input}\n\nSummary:",
    "legal": "You are a legal document assistant. Summarize the following text for a legal professional, focusing on key facts, arguments, and outcomes.\n\nText:\n{input}\n\nSummary:",
    "general": "Summarize the following text comprehensively and clearly.\n\nText:\n{input}\n\nSummary:",
}

# Caching directory for summaries
CACHE_DIR = "./.summary_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# API usage log file
API_USAGE_LOG = "./api_usage_log.csv"

# Utility: Clear cache directory
def clear_cache():
    for f in os.listdir(CACHE_DIR):
        os.remove(os.path.join(CACHE_DIR, f))
    logging.info("Summary cache cleared.")

def get_openai_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set. Please set your OpenAI API key.")
    return api_key

def num_tokens_from_string(string: str, tokenizer: Optional[Callable[[str], List[int]]] = None, model: str = "gpt-4") -> int:
    if tokenizer:
        return len(tokenizer(string))
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(string))

def clean_text(text: str) -> str:
    # Remove excessive line breaks, fix OCR artifacts, etc.
    text = text.replace('\n', ' ').replace('  ', ' ')
    return text.strip()

def smart_chunk_text(
    text: str,
    model: str = "gpt-4",
    max_tokens: int = 768,
    overlap: int = 50,
    tokenizer: Optional[Callable[[str], List[int]]] = None
) -> List[str]:
    """
    Hybrid chunking: split by sentences, enforce token limits, allow overlap. Fallback to splitting on periods if sentence tokenization fails.
    """
    text = clean_text(text)
    try:
        sentences = sent_tokenize(text)
    except Exception:
        sentences = text.split('.')
    if tokenizer is None:
        enc = tiktoken.encoding_for_model(model)
        tokenizer = enc.encode
    chunks = []
    current_chunk = []
    current_tokens = 0
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        sent_tokens = len(tokenizer(sent))
        if current_tokens + sent_tokens > max_tokens:
            if current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)
                # Overlap: add last N tokens from previous chunk to next
                if overlap > 0 and chunk_text:
                    overlap_tokens = tokenizer(chunk_text)[-overlap:]
                    overlap_text = tiktoken.encoding_for_model(model).decode(overlap_tokens)
                    current_chunk = [overlap_text, sent]
                    current_tokens = len(tokenizer(overlap_text)) + sent_tokens
                else:
                    current_chunk = [sent]
                    current_tokens = sent_tokens
            else:
                # Sentence too long, force split
                chunks.append(sent)
                current_chunk = []
                current_tokens = 0
        else:
            current_chunk.append(sent)
            current_tokens += sent_tokens
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    return chunks

def get_prompt(domain: str = "general", custom_prompt: Optional[str] = None) -> str:
    if custom_prompt:
        return custom_prompt
    return SUMMARIZATION_PROMPTS.get(domain, SUMMARIZATION_PROMPTS["general"])

def cache_summary(chunk: str, summary: str, model: str, prompt_seed: str) -> None:
    h = hashlib.sha256((chunk + model + prompt_seed).encode()).hexdigest()
    with open(os.path.join(CACHE_DIR, f"{h}.txt"), "w", encoding="utf-8") as f:
        f.write(summary)

def load_cached_summary(chunk: str, model: str, prompt_seed: str) -> Optional[str]:
    h = hashlib.sha256((chunk + model + prompt_seed).encode()).hexdigest()
    path = os.path.join(CACHE_DIR, f"{h}.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None

def log_api_usage(timestamp: float, model: str, prompt_tokens: int, completion_tokens: int, total_tokens: int, cost: Optional[float] = None):
    file_exists = os.path.isfile(API_USAGE_LOG)
    with open(API_USAGE_LOG, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["timestamp", "model", "prompt_tokens", "completion_tokens", "total_tokens", "cost"])
        writer.writerow([timestamp, model, prompt_tokens, completion_tokens, total_tokens, cost if cost is not None else ""])

def call_openai_with_retries(
    prompt: str,
    model: str = "gpt-4",
    max_tokens: int = 512,
    temperature: float = 0.3,
    max_retries: int = 5,
    backoff_base: float = 2.0,
    log_usage: bool = True
) -> str:

    from openai import OpenAI, RateLimitError
    api_key = get_openai_api_key()
    client = OpenAI(api_key=api_key)

    @backoff.on_exception(backoff.expo, RateLimitError, max_tries=max_retries)
    def _call():
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        summary = response.choices[0].message.content.strip()
        usage = getattr(response, 'usage', None)
        if log_usage and usage:
            logging.info(f"OpenAI API call successful. Prompt tokens: {usage.prompt_tokens}, Completion tokens: {usage.completion_tokens}")
        return summary
    try:
        return _call()
    except Exception as e:
        logging.error(f"OpenAI API call failed after retries: {e}")
        return f"[ERROR] OpenAI API call failed: {e}"

def summarize_text(
    text: str,
    model: str = "gpt-4",
    domain: str = "general",
    custom_prompt: Optional[str] = None,
    max_tokens: int = 512,
    chunk_max_tokens: int = 768,
    overlap: int = 50,
    cache: bool = True,
    tokenizer: Optional[Callable[[str], List[int]]] = None
) -> List[Dict[str, Any]]:
    """
    Summarize text using OpenAI GPT-4, with hybrid chunking, caching, and metadata.
    Returns a list of dicts: [{chunk, tokens, summary, text}]
    """
    prompt_seed = custom_prompt or get_prompt(domain)
    chunks = smart_chunk_text(text, model=model, max_tokens=chunk_max_tokens, overlap=overlap, tokenizer=tokenizer)
    results = []
    for i, chunk in enumerate(chunks):
        tokens = num_tokens_from_string(chunk, tokenizer=tokenizer, model=model)
        cached = load_cached_summary(chunk, model, prompt_seed) if cache else None
        if cached:
            summary = cached
            logging.info(f"Loaded cached summary for chunk {i}")
        else:
            prompt = prompt_seed.format(input=chunk)
            summary = call_openai_with_retries(prompt, model=model, max_tokens=max_tokens)
            if cache:
                cache_summary(chunk, summary, model, prompt_seed)
        results.append({
            "chunk": i,
            "tokens": tokens,
            "summary": summary,
            "text": chunk
        })
    return results

def summarize_document(
    doc: Dict[str, Any],
    mode: str = "document",  # "document", "page", or "section" (I didn't implement section)
    model: str = "gpt-4",
    domain: str = "general",
    custom_prompt: Optional[str] = None,
    max_tokens: int = 512,
    chunk_max_tokens: int = 768,
    overlap: int = 50,
    cache: bool = True,
    tokenizer: Optional[Callable[[str], List[int]]] = None
) -> List[Dict[str, Any]]:
    """
    Summarize a document (from ingestion). Mode can be 'document' (entire), 'page' (per page), or 'section' (future).
    Returns a list of dicts with chunk metadata and summaries.
    """
    if mode == "document":
        if doc.get("file_type") == "pdf":
            text = '\n'.join(doc["text_by_page"])
        else:
            text = doc["text"]
        return summarize_text(
            text,
            model=model,
            domain=domain,
            custom_prompt=custom_prompt,
            max_tokens=max_tokens,
            chunk_max_tokens=chunk_max_tokens,
            overlap=overlap,
            cache=cache,
            tokenizer=tokenizer
        )
    elif mode == "page":
        if doc.get("file_type") == "pdf":
            results = []
            for i, page in enumerate(doc["text_by_page"]):
                page_results = summarize_text(
                    page,
                    model=model,
                    domain=domain,
                    custom_prompt=custom_prompt,
                    max_tokens=max_tokens,
                    chunk_max_tokens=chunk_max_tokens,
                    overlap=overlap,
                    cache=cache,
                    tokenizer=tokenizer
                )
                for r in page_results:
                    r["page"] = i
                    r["source"] = f"{doc['file_name']} - Page {i+1}"
                results.extend(page_results)
            return results
        else:
            raise ValueError("Per-page summarization is only supported for PDFs.")
    else:
        raise ValueError(f"Unsupported summarization mode: {mode}")