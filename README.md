<<<<<<< HEAD
A robust, production-ready, multilingual Document Question Answering (DocQA) bot. Upload documents (PDF, DOCX, TXT), ask questions in multiple languages, and get accurate, context-aware answers—powered by advanced retrieval, LLMs, and translation.


🚀 Features
Document Ingestion:
Supports PDF, DOCX, and TXT files.
Extracts text, images (for OCR), and rich metadata (filename, size, last modified, language).
Automatic language detection and OCR for scanned documents.

Chunking & Embeddings:
Hybrid chunking (semantic, token-aware, overlap) for optimal context.
Embeddings via OpenAI or SentenceTransformers.
Persistent vector store with ChromaDB.

Retrieval-Augmented Generation (RAG):
Hybrid semantic/keyword retrieval with MMR for diversity.
Top-k relevant chunks passed to LLM for contextual answers.

Multilingual Q&A & Translation:
Ask and receive answers in English, French, Dutch, Spanish, Pidgin, Yoruba, and more.
DeepL and OpenAI GPT-4 translation fallback.
Modern Frontend:
React + TypeScript, dark mode, responsive, chat-style UI.
File upload, language selectors, chat history, and answer display.
Robust Backend:
FastAPI, async endpoints, error handling, logging, and caching.
Rate limit handling and exponential backoff for API calls.
🏗️ Architecture
⚡ Quickstart
1. Clone the Repo
2. Backend Setup
Python 3.9+ recommended.
Install dependencies:
Set up environment variables in a .env file:
Start the backend:
3. Frontend Setup
Visit http://localhost:5173 in your browser.
📝 Usage
Upload a document (PDF, DOCX, or TXT).
Select your UI and answer language.
Ask questions in any supported language.
View answers with translation, supporting context, and chat history.
🌍 Supported Languages
English, French, Dutch, Spanish, Pidgin, Yoruba
(Easily extendable via translation module)
🛠️ Configuration
Chunking, embedding, and retrieval parameters can be tuned in app/embeddings.py and app/rag.py.
Translation: Uses DeepL by default, falls back to OpenAI for unsupported languages.
ChromaDB: Persistent vector store for fast retrieval.
🧩 Project Structure
🧪 Testing
Backend:
Add and run tests in tests/ (not included by default).
Frontend:
Use npm test for React component tests (if configured).
🤝 Contributing
Fork the repo and create your branch.
Make your changes and add tests.
Submit a pull request with a clear description.
🐛 Troubleshooting
ModuleNotFoundError: Ensure all dependencies are installed and your virtual environment is active.
API Errors: Check your API keys and rate limits.
Frontend not connecting: Ensure backend is running on the correct port.
📄 License
MIT License.
See LICENSE for details.
🙏 Acknowledgements
OpenAI
DeepL
ChromaDB
React
FastAPI
Built with ❤️ by Habeeb and contributors.
Let me know if you want to add badges, screenshots, or further customization!

