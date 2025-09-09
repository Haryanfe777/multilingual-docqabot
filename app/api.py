from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.ingestion import ingest_document
from app.rag import EmbeddingModel, embed_chunks, retrieve_relevant_chunks, prepare_chunks_for_embedding, get_chroma_client, get_or_create_collection, CHROMA_DB_DIR
from app.qa import answer_query, build_sources, format_references
from app.translator import translate_text, detect_language as tr_detect
import os
import tempfile
import shutil
import langdetect
from dotenv import load_dotenv
from app.embeddings import summarize_text, summarize_document
import json
from pydantic import BaseModel
from typing import List, Optional
load_dotenv()


app = FastAPI()

# Security & CORS configuration
API_KEY = os.getenv("API_KEY") or os.getenv("DOCQABOT_API_KEY")
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))
ALLOWED_ORIGINS = [o.strip() for o in (os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")) if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "./uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Store last ingested document in memory per dataset (demo scope)
last_docs: dict = {}


def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


_rate_state: dict = {}
def rate_limiter(request: Request):
    import time
    now = time.time()
    ip = request.client.host if request.client else "unknown"
    window_start = now - 60
    hist = _rate_state.get(ip, [])
    hist = [t for t in hist if t >= window_start]
    if len(hist) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    hist.append(now)
    _rate_state[ip] = hist

@app.post("/api/upload")
async def upload_api(file: UploadFile = File(...), dataset: str = Form("default"), _: None = Depends(require_api_key), __: None = Depends(rate_limiter)):
    import traceback
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        doc = ingest_document(file_path)
        # Unify text extraction for all file types
        if 'text' in doc:
            text = doc['text']
        elif 'text_by_page' in doc:
            text = '\n'.join(doc['text_by_page'])
        else:
            raise HTTPException(status_code=500, detail="No text found in document.")
        # Summarize and chunk the document text (returns list of dicts)
        chunks = summarize_text(text)
        # Add metadata to each chunk
        chunks = prepare_chunks_for_embedding(
            chunks,
            doc_name=doc.get('file_name', 'document'),
            language=doc.get('language', 'unknown')
        )
        # Optionally, embed on upload within a dataset namespace
        embedding_model = EmbeddingModel(model_name='openai')
        client = get_chroma_client(namespace=dataset)
        _ = get_or_create_collection(client, "doc_chunks")
        embed_chunks(chunks, embedding_model, client=client, collection_name="doc_chunks", reembed=False)
        last_docs[dataset] = {"meta": doc, "embedding_model": embedding_model}
        return {"filename": file.filename, "metadata": doc}
    except Exception as e:
        print("Exception in /api/upload:", e)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/translate")
def translate_api(text: str = Form(...), target_lang: str = Form(...), source_lang: str = Form(None), _: None = Depends(require_api_key), __: None = Depends(rate_limiter)):
    """Translate arbitrary text to a target language."""
    try:
        translated = translate_text(text, target_lang, source_lang)
        detected_lang = langdetect.detect(text)
        engine = "deepl" if target_lang.upper() in {"EN", "FR", "NL", "ES", "DE", "IT", "PT", "RU", "JA", "ZH"} else "openai"
        return {"translated": translated, "detected_source_lang": detected_lang, "engine": engine}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/ask")
def ask_api(
    question: str = Form(...),
    doc_id: str = Form(...),
    user_lang: str = Form(...),
    chat_history: str = Form(None),
    dataset: str = Form("default"),
    _: None = Depends(require_api_key),
    __: None = Depends(rate_limiter),
):
    """Answer a question about a document, with translation support and conversational memory."""
    import traceback
    try:
        # Retrieve last uploaded document and embedding model
        ds = last_docs.get(dataset)
        doc = ds.get("meta") if ds else None
        embedding_model = ds.get("embedding_model") if ds else EmbeddingModel(model_name='openai')
        if doc is None:
            raise HTTPException(status_code=400, detail="No document uploaded yet.")
        # Unify text extraction for all file types
        if 'text' in doc:
            text = doc['text']
        elif 'text_by_page' in doc:
            text = '\n'.join(doc['text_by_page'])
        else:
            raise HTTPException(status_code=500, detail="No text found in document.")
        # Translate the question to English for retrieval if needed
        question_lang = tr_detect(question) if question else "en"
        question_en = question
        # Translate question to EN for retrieval
        doc_language = (doc.get('language') if isinstance(doc.get('language'), str) else None) or 'en'
        if question_lang and question_lang.lower() != "en":
            question_en = translate_text(question, target_lang="EN", source_lang=question_lang)

        # Retrieve relevant chunks from ChromaDB
        from app.rag import retrieve_relevant_chunks
        client = get_chroma_client(namespace=dataset)
        _ = get_or_create_collection(client, "doc_chunks")
        top_chunks = retrieve_relevant_chunks(
            query=question_en,
            embedding_model=embedding_model,
            client=client,
            collection_name="doc_chunks",
            top_k=5
        )
        # Parse chat history (preserved across questions by frontend)
        history = []
        if chat_history:
            try:
                history = json.loads(chat_history)
            except Exception:
                history = []
        # Generate answer using LLM with context and chat history
        from app.qa import answer_query
        original_answer = answer_query(question_en, top_chunks, chat_history=history)
        # Build deterministic citations only; do not append to answer
        sources = build_sources(top_chunks)
        # Back-translate answer to user's language if different from English
        translation_engine = None
        translated_answer = original_answer
        if user_lang and user_lang.lower()[:2] != "en":
            translated_answer = translate_text(original_answer, target_lang=user_lang, source_lang="EN")
            translation_engine = "deepl"
        return {
            "answer": translated_answer,
            "original_answer": original_answer,
            "question": question,
            "question_en": question_en,
            "user_language": user_lang,
            "translation_engine": translation_engine,
            "translated": user_lang and user_lang.lower()[:2] != "en",
            "sources": sources,
            "dataset": dataset
        }
    except Exception as e:
        print("Exception in /api/ask:", e)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


# --- Pydantic Schemas for Summarization ---
class SummarizeRequest(BaseModel):
    mode: str = "document"  # "document" or "page"
    model: str = "gpt-4"
    domain: str = "medical"
    custom_prompt: Optional[str] = None
    max_tokens: int = 512
    chunk_max_tokens: int = 768
    overlap: int = 50
    cache: bool = True
    target_language: Optional[str] = None


class SummaryItem(BaseModel):
    page: Optional[int] = None
    chunk: int
    summary: str
    tokens: int
    source: Optional[str] = None


class SummarizeResponse(BaseModel):
    mode: str
    language: str
    num_items: int
    items: List[SummaryItem]


@app.post("/api/summarize", response_model=SummarizeResponse)
async def summarize_api(req: SummarizeRequest, dataset: str = "default", _: None = Depends(require_api_key), __: None = Depends(rate_limiter)):
    import traceback
    try:
        ds = last_docs.get(dataset)
        doc = ds.get("meta") if ds else None
        if doc is None:
            raise HTTPException(status_code=400, detail="No document uploaded yet.")
        # Run summarization
        results = summarize_document(
            doc,
            mode=req.mode,
            model=req.model,
            domain=req.domain,
            custom_prompt=req.custom_prompt,
            max_tokens=req.max_tokens,
            chunk_max_tokens=req.chunk_max_tokens,
            overlap=req.overlap,
            cache=req.cache,
        )
        # Build items and translate summaries if requested
        items: List[SummaryItem] = []
        for r in results:
            summ = r.get("summary", "")
            if req.target_language and req.target_language.lower()[:2] != "en" and summ:
                summ = translate_text(summ, target_lang=req.target_language)
            items.append(SummaryItem(
                page=r.get("page"),
                chunk=int(r.get("chunk", 0)),
                summary=summ,
                tokens=int(r.get("tokens", 0)),
                source=r.get("source")
            ))
        # Determine language for response (detected)
        language = req.target_language or (doc.get('language') if isinstance(doc.get('language'), str) else 'en')
        return SummarizeResponse(
            mode=req.mode,
            language=language or 'en',
            num_items=len(items),
            items=items
        )
    except HTTPException:
        raise
    except Exception as e:
        print("Exception in /api/summarize:", e)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


# Dataset management endpoints
@app.get("/api/datasets")
def list_datasets(_: None = Depends(require_api_key), __: None = Depends(rate_limiter)):
    try:
        if not os.path.isdir(CHROMA_DB_DIR):
            return {"datasets": []}
        names = [name for name in os.listdir(CHROMA_DB_DIR) if os.path.isdir(os.path.join(CHROMA_DB_DIR, name))]
        return {"datasets": names}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


class DatasetRequest(BaseModel):
    name: str


@app.post("/api/datasets/reset")
def reset_dataset(req: DatasetRequest, _: None = Depends(require_api_key), __: None = Depends(rate_limiter)):
    try:
        target = os.path.join(CHROMA_DB_DIR, req.name)
        if os.path.isdir(target):
            shutil.rmtree(target)
        if req.name in last_docs:
            last_docs.pop(req.name, None)
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})