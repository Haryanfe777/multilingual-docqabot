# DocQA Multilingual Question-Answering Bot

DocQA is an advanced multilingual document question-answering system. It allows users to upload documents in various formats, ask natural language questions in their preferred language, and receive accurate, translated answers in real-time.

## Features 

-- **Multilingual Support**: Ask questions in multiple languages and receive translated responses.

-- **Chat Interface**: Interactive, chat-style UI with dark mode, timestamps, and bubble design.

-- **Language Detection & Translation**: Automatic detection of document language and user language preferences.

-- **Live Language Selector**: Choose UI and answer language anytime.

-- **Backend Intelligence**: Integrated RAG pipeline with translation, summarization, and hybrid chunking.
 
## Project Structure

```bash
.
├── backend/
│   ├── app/
│   │   ├── ingestion.py      # Load and split document into chunks
│   │   ├── embeddings.py     # Hybrid chunking, embedding logic, summarization
│   │   ├── rag.py            # Chunk retrieval pipeline
│   │   ├── qa.py             # LLM-based Q&A over document
│   │   ├── translation.py    # Translation using DeepL/OpenAI APIs
│   │   ├── config.py         # Config variables
│   │   ├── utils.py          # Helper functions
│   └── main.py               # FastAPI entrypoint
│
├── frontend/
│   ├── components/           # Reusable React components (Chat, Selectors, etc.)
│   ├── pages/                # Main UI pages
│   ├── locales/              # i18n translation files
│   ├── utils/                # Frontend helpers
│   └── App.jsx               # Entry point
│
├── public/                   # Static assets
├── README.md                 # You're here.
├── requirements.txt          # Python dependencies
├── package.json              # Frontend dependencies
└── .env                      # Environment variables

```

## How it Works 
**Document Ingestion:**\
  -- Supports PDF, DOCX, and TXT files.\
  -- Extracts text, images (for OCR), and rich metadata (filename, size, last modified, language).\
  -- Automatic language detection and OCR for scanned documents.

**Chunking & Embeddings:**\
  -- Hybrid chunking (semantic, token-aware, overlap) for optimal context.\
  -- Embeddings via OpenAI or SentenceTransformers.\
  -- Persistent vector store with ChromaDB.

**Retrieval-Augmented Generation (RAG):**\
  -- Hybrid semantic/keyword retrieval with MMR for diversity.\
  -- Top-k relevant chunks passed to LLM for contextual answers.

**Multilingual Q&A & Translation:**\
   -- Ask and receive answers in English, French, Dutch, Spanish, Pidgin, Yoruba, and more.\
   -- DeepL and OpenAI GPT-4 translation fallback.
 
 **Modern Frontend:**\
   -- React + TypeScript, dark mode, responsive, chat-style UI.\
   -- File upload, language selectors, chat history, and answer display.
   
**Robust Backend:**\
  -- FastAPI, async endpoints, error handling, logging, and caching.\
  --Rate limit handling and exponential backoff for API calls.

## Installation
1. Clone the Repo
  ```bash
git clone https://github.com/Haryanfe777/multilingual-docqabot
cd docqabot
```

2. Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```
3. Setup Frontend
```bash
cd frontend
npm install
npm run dev
```
4. Environment: Add .env in the backend with API keys:
```bash
OPENAI_API_KEY=...
DEEPL_API_KEY=...
```
### Contributing
Fork the repo and create your branch.\
Make your changes and add tests.\
Submit a pull request with a clear description.

### Troubleshooting
ModuleNotFoundError: Ensure all dependencies are installed and your virtual environment is active.
API Errors: Check your API keys and rate limits.
Frontend not connecting: Ensure backend is running on the correct port.

### Tech Stack
**Backend:** FastAPI, Python, OpenAI, DeepL\

**Frontend:** React, Tailwind, i18n\

**Language Detection:** langdetect\

**Embeddings:** OpenAI/Custom

## License
MIT License. Do what you want — just don’t sell it and claim it’s yours.

