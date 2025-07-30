from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.ingestion import ingest_document
from app.rag import EmbeddingModel, embed_chunks, retrieve_relevant_chunks, prepare_chunks_for_embedding
from app.qa import answer_query
from app.translator import translate_text
import os
import tempfile
import shutil
import langdetect
from dotenv import load_dotenv
from app.embeddings import summarize_text
import json
load_dotenv()


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "./uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Store last ingested document in memory for demo 
last_doc = {"meta": None, "embedding_model": None}

@app.post("/api/upload")
async def upload_api(file: UploadFile = File(...)):
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
        # Optionally, embed on upload
        embedding_model = EmbeddingModel(model_name='openai')
        embed_chunks(chunks, embedding_model, reembed=False)
        last_doc["meta"] = doc
        last_doc["embedding_model"] = embedding_model
        return {"filename": file.filename, "metadata": doc}
    except Exception as e:
        print("Exception in /api/upload:", e)
        traceback.print_exc()
        raise

@app.post("/api/translate")
def translate_api(text: str = Form(...), target_lang: str = Form(...), source_lang: str = Form(None)):
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
):
    """Answer a question about a document, with translation support and conversational memory."""
    import traceback
    try:
        # Retrieve last uploaded document and embedding model
        doc = last_doc.get("meta")
        embedding_model = EmbeddingModel(model_name='openai')
        if doc is None:
            raise HTTPException(status_code=400, detail="No document uploaded yet.")
        # Unify text extraction for all file types
        if 'text' in doc:
            text = doc['text']
        elif 'text_by_page' in doc:
            text = '\n'.join(doc['text_by_page'])
        else:
            raise HTTPException(status_code=500, detail="No text found in document.")
        # Retrieve relevant chunks from ChromaDB
        from app.rag import retrieve_relevant_chunks
        top_chunks = retrieve_relevant_chunks(
            query=question,
            embedding_model=embedding_model,
            top_k=5
        )
        # Parse chat history
        history = []
        if chat_history:
            try:
                history = json.loads(chat_history)
            except Exception:
                history = []
        # Generate answer using LLM with context and chat history
        from app.qa import answer_query
        original_answer = answer_query(question, top_chunks, chat_history=history)
        # Detect document language if available
        doc_language = doc.get('language', 'en')
        # Translate answer if needed
        translation_engine = None
        translated_answer = original_answer
        if user_lang.lower() != doc_language.lower():
            translated_answer = translate_text(original_answer, user_lang, doc_language)
            translation_engine = "deepl" if user_lang.upper() in {"EN", "FR", "NL", "ES", "DE", "IT", "PT", "RU", "JA", "ZH"} else "openai"
        return {
            "answer": translated_answer,
            "original_answer": original_answer,
            "doc_language": doc_language,
            "user_language": user_lang,
            "translation_engine": translation_engine,
            "translated": user_lang.lower() != doc_language.lower()
        }
    except Exception as e:
        print("Exception in /api/ask:", e)
        traceback.print_exc()
        raise 