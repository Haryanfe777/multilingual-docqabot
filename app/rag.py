import os
import time
import uuid
from typing import List, Dict, Any, Optional, Union
import logging
from datetime import datetime

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from chromadb.api.types import Documents, Embeddings, Metadatas

from sentence_transformers import SentenceTransformer
from openai import OpenAI, RateLimitError
import nltk
from nltk.tokenize import word_tokenize

import re

# Ensure NLTK 'punkt' is available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

CHROMA_DB_DIR = './db'
CHROMA_COLLECTION = 'doc_chunks'

# --- Embedding Model Setup ---
class EmbeddingModel:
    def __init__(self, model_name: str = 'openai', openai_model: str = 'text-embedding-3-small', st_model: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.openai_model = openai_model
        self.st_model = st_model
        self.st_embedder = None
        self.name = f"{model_name}:{openai_model if model_name == 'openai' else st_model}"
        if model_name == 'sentence-transformers':
            self.st_embedder = SentenceTransformer(st_model)

    def embed(self, texts: List[str], log_tokens: bool = True, max_retries: int = 5) -> List[List[float]]:
        if self.model_name == 'openai':
            api_key = os.getenv('OPENAI_API_KEY')
            client = OpenAI(api_key=api_key)
            for attempt in range(max_retries):
                try:
                    response = client.embeddings.create(
                        input=texts,
                        model=self.openai_model
                    )
                    if log_tokens:
                        usage = getattr(response, 'usage', None)
                        if usage:
                            logging.info(f"[OpenAI] Embedding token usage: prompt={usage.prompt_tokens}, total={usage.total_tokens}")
                    return [d.embedding for d in response.data]
                except RateLimitError as e:
                    logging.warning("[OpenAI] Embedding rate limit hit. Sleeping for 60s.")
                    time.sleep(60)
                except Exception as e:
                    logging.error(f"[OpenAI] Embedding error: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                    else:
                        raise
        elif self.model_name == 'sentence-transformers':
            return self.st_embedder.encode(texts, show_progress_bar=False, convert_to_numpy=False).tolist()
        else:
            raise ValueError(f"Unknown embedding model: {self.model_name}")

class MockEmbeddingModel:
    name = "mock"
    def embed(self, texts, **kwargs):
        # Return a fixed vector for each text (e.g., 384-dim)
        return [[0.1] * 384 for _ in texts]

# --- ChromaDB Setup ---
def get_chroma_client(persist_dir: str = CHROMA_DB_DIR, namespace: Optional[str] = None) -> chromadb.Client:
    db_dir = os.path.join(persist_dir, namespace) if namespace else persist_dir
    os.makedirs(db_dir, exist_ok=True)
    return chromadb.Client(Settings(
        persist_directory=db_dir,
        anonymized_telemetry=False
    ))

def get_or_create_collection(client: chromadb.Client, name: str = CHROMA_COLLECTION) -> chromadb.Collection:
    if name in [c.name for c in client.list_collections()]:
        logging.info(f"Retrieved ChromaDB collection: {name}")
        return client.get_collection(name)
    logging.info(f"Created new ChromaDB collection: {name}")
    return client.create_collection(name)

# --- Embedding and Indexing ---
def embed_chunks(
    chunks: List[Dict[str, Any]],
    embedding_model: EmbeddingModel,
    client: Optional[chromadb.Client] = None,
    collection_name: str = CHROMA_COLLECTION,
    batch_size: int = 32,
    reembed: bool = False,
    dry_run: bool = False
) -> None:
    """
    Embed and index chunks in ChromaDB. Each chunk should have 'text' and metadata.
    """
    if client is None:
        client = get_chroma_client()
    collection = get_or_create_collection(client, collection_name)
    ids = []
    docs = []
    metas = []
    all_ids = []
    for chunk in chunks:
        # Deterministic chunk id to avoid duplicate re-indexing across runs
        chunk_id = chunk.get('chunk_id') or f"{chunk.get('doc_name','doc')}-{int(chunk.get('page',0))}-{int(chunk.get('chunk',0))}"
        all_ids.append(chunk_id)
        ids.append(chunk_id)
        docs.append(chunk['text'])
        meta = {k: v for k, v in chunk.items() if k != 'text'}
        meta['chunk_id'] = chunk_id
        if 'source' not in meta:
            meta['source'] = chunk.get('source', f"{chunk.get('doc_name','doc')} - Page {chunk.get('page',0)}")
        if 'timestamp' not in meta:
            meta['timestamp'] = chunk.get('timestamp', datetime.utcnow().isoformat())
        if 'uuid' not in meta:
            meta['uuid'] = str(uuid.uuid4())
        metas.append(meta)
    # Optionally skip already embedded chunks
    if not reembed:
        existing = set(collection.get(ids=ids).get('ids', []))
        new_ids, new_docs, new_metas = [], [], []
        for i, cid in enumerate(ids):
            if cid not in existing:
                new_ids.append(cid)
                new_docs.append(docs[i])
                new_metas.append(metas[i])
        logging.info(f"Skipped {len(all_ids) - len(new_ids)} existing chunks. Embedding {len(new_ids)} new ones.")
        ids, docs, metas = new_ids, new_docs, new_metas
    if dry_run:
        logging.info(f"[DRY RUN] Would embed {len(ids)} chunks.")
        return
    # Batch embedding
    for i in range(0, len(docs), batch_size):
        batch_docs = docs[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        batch_metas = metas[i:i+batch_size]
        if not batch_docs:
            continue
        embeddings = embedding_model.embed(batch_docs)
        collection.add(
            documents=batch_docs,
            embeddings=embeddings,
            metadatas=batch_metas,
            ids=batch_ids
        )
        logging.info(f"Embedded and stored {len(batch_docs)} chunks in ChromaDB.")
    # client.persist()  # Removed: not needed in latest ChromaDB

# --- Retrieval ---
def normalize_text(text: str) -> List[str]:
    # Lowercase, remove punctuation, tokenize
    text = re.sub(r'[^\w\s]', '', text.lower())
    return word_tokenize(text)

def retrieve_relevant_chunks(
    query: str,
    embedding_model: EmbeddingModel,
    client: Optional[chromadb.Client] = None,
    collection_name: str = CHROMA_COLLECTION,
    top_k: int = 5,
    hybrid: bool = True,
    keyword_weight: float = 0.2,
    return_scores: bool = False,
    mmr: bool = False,
    mmr_lambda: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Retrieve top-k relevant chunks for a query using semantic and (optionally) keyword search.
    Returns: List of dicts with text, metadata, and similarity score.
    """
    if client is None:
        client = get_chroma_client()
    collection = get_or_create_collection(client, collection_name)
    # Semantic search
    query_emb = embedding_model.embed([query])[0]
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k*8 if mmr else top_k*2,  # get more for MMR/hybrid
        include=["documents", "metadatas", "distances"]
    )
    hits = []
    query_words = set(normalize_text(query))
    for i in range(len(results['ids'][0])):
        hit = {
            'id': results['ids'][0][i],
            'text': results['documents'][0][i],
            'metadata': results['metadatas'][0][i],
            'distance': results['distances'][0][i]
        }
        chunk_words = set(normalize_text(hit['text']))
        overlap = len(query_words & chunk_words)
        if hybrid:
            hit['hybrid_score'] = hit['distance'] - keyword_weight * overlap
            hit['score'] = hit['hybrid_score']
        else:
            hit['score'] = hit['distance']
        if return_scores:
            hit['raw_distance'] = hit['distance']
            if hybrid:
                hit['raw_hybrid_score'] = hit['hybrid_score']
        hits.append(hit)
    # Hybrid: sort by hybrid score
    if hybrid:
        hits.sort(key=lambda x: x['hybrid_score'])
    else:
        hits.sort(key=lambda x: x['distance'])
    # MMR (Maximal Marginal Relevance) for diversity
    if mmr and hits:
        selected = []
        candidates = hits.copy()
        selected.append(candidates.pop(0))
        while len(selected) < top_k and candidates:
            mmr_scores = []
            for cand in candidates:
                sim_to_query = 1 - cand['distance']
                sim_to_selected = max([1 - abs(cand['distance'] - sel['distance']) for sel in selected])
                mmr_score = mmr_lambda * sim_to_query - (1 - mmr_lambda) * sim_to_selected
                mmr_scores.append(mmr_score)
            idx = mmr_scores.index(max(mmr_scores))
            selected.append(candidates.pop(idx))
        hits = selected
    # Fallback: if all distances are high, do keyword search
    if hits and hits[0]['distance'] > 0.7:
        logging.info("Semantic search weak, using keyword fallback.")
        keyword_hits = [h for h in hits if any(w in normalize_text(h['text']) for w in query_words)]
        if keyword_hits:
            return keyword_hits[:top_k]
    return hits[:top_k]

# --- Utility: Prepare Chunks for Embedding ---
def prepare_chunks_for_embedding(
    summaries: List[Dict[str, Any]],
    doc_name: str,
    language: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Add metadata to each chunk summary for embedding/indexing.
    """
    for chunk in summaries:
        chunk['doc_name'] = doc_name
        if language:
            chunk['language'] = language
        if 'source' not in chunk:
            chunk['source'] = f"{doc_name} - Page {chunk.get('page', 0)}"
        if 'timestamp' not in chunk:
            chunk['timestamp'] = datetime.utcnow().isoformat()
        if 'uuid' not in chunk:
            chunk['uuid'] = str(uuid.uuid4())
    return summaries

# --- Security: Mask sensitive keys in logs ---
def mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return "***"
    return key[:4] + "..." + key[-4:]

logging.info(f"OpenAI API key loaded: {mask_key(os.getenv('OPENAI_API_KEY'))}")
