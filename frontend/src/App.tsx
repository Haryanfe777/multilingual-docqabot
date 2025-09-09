import { useState } from 'react';
import './App.css';
import DocumentUpload from './components/DocumentUpload';
import QuestionInput from './components/QuestionInput';
import AnswerDisplay from './components/AnswerDisplay';
import LanguageSelector from './components/LanguageSelector';
import { uploadDocument, askQuestion, summarize } from './api';
import MetadataDisplay from './components/MetadataDisplay';

function App() {
  const [uploading, setUploading] = useState(false);
  const [docMeta, setDocMeta] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [answerLang, setAnswerLang] = useState('en');

  const handleUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      const meta = await uploadDocument(file);
      setDocMeta(meta);
      setChatHistory([]);
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleAsk = async (q: string, lang: string) => {
    setLoading(true);
    setError(null);
    // Do not clear history; push user question immediately
    setChatHistory((prev) => [
      ...prev,
      { q, a: '', original: '', chunks: [], timestamp: new Date().toISOString() },
    ]);
    try {
      const res = await askQuestion(q, lang, chatHistory);
      // Update last entry with assistant answer
      setChatHistory((prev) => {
        const copy = [...prev];
        const last = copy[copy.length - 1];
        if (last && !last.a) {
          last.a = res.answer || '';
          last.original = res.original_answer || res.answer || '';
          last.chunks = res.chunks || [];
          last.doc_language = res.doc_language;
          last.user_language = res.user_language;
          last.translation_engine = res.translation_engine;
          last.translated = res.translated;
        }
        return copy;
      });
    } catch (err: any) {
      setError(err.message || 'Failed to get answer');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="web-app-bg">
      <header className="web-header">
        <h1>Habeeb's Multilingual DocQA</h1>
        <div className="lang-selectors">
          <LanguageSelector onAnswerLangChange={setAnswerLang} />
        </div>
      </header>
      <main className="web-main">
        <div className="card-panel">
          <section className="upload-section">
            <DocumentUpload onUpload={handleUpload} />
            {uploading && <span>Uploading...</span>}
          </section>
          {docMeta && (
            <>
              <MetadataDisplay metadata={docMeta.metadata || docMeta} />
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={async () => {
                  setLoading(true);
                  setError(null);
                  try {
                    // Create a synthetic turn in history and then fill in the summary
                    setChatHistory((prev) => ([...prev, { q: 'Document summary', a: '', original: '', chunks: [], timestamp: new Date().toISOString(), user_language: answerLang }]));
                    const res = await summarize('document', answerLang);
                    const summaryText = res.items?.map((i: any) => i.summary).join('\n\n') || '';
                    setChatHistory((prev) => {
                      const copy = [...prev];
                      const last = copy[copy.length - 1];
                      if (last && !last.a) {
                        last.a = summaryText;
                        last.original = summaryText;
                        last.translated = false;
                      }
                      return copy;
                    });
                  } catch (e: any) {
                    setError(e.message || 'Failed to summarize');
                  } finally {
                    setLoading(false);
                  }
                }}>Summarize Document</button>
                <button onClick={async () => {
                  setLoading(true);
                  setError(null);
                  try {
                    setChatHistory((prev) => ([...prev, { q: 'Page summaries', a: '', original: '', chunks: [], timestamp: new Date().toISOString(), user_language: answerLang }]));
                    const res = await summarize('page', answerLang);
                    const summaryText = res.items?.map((i: any) => `Page ${i.page ?? '?'}: ${i.summary}`).join('\n\n') || '';
                    setChatHistory((prev) => {
                      const copy = [...prev];
                      const last = copy[copy.length - 1];
                      if (last && !last.a) {
                        last.a = summaryText;
                        last.original = summaryText;
                        last.translated = false;
                      }
                      return copy;
                    });
                  } catch (e: any) {
                    setError(e.message || 'Failed to summarize pages');
                  } finally {
                    setLoading(false);
                  }
                }}>Summarize Per Page</button>
              </div>
            </>
          )}
          <section className="qa-section">
            {error && <div style={{ color: 'red', marginBottom: 8 }}>{error}</div>}
            {/* Render each turn: user question bubble + assistant answer (with references) */}
            {chatHistory.map((item, i) => (
              <div key={i}>
                <div className={`chat-bubble user-bubble`}>
                  <div className={`bubble-avatar user`}>🧑</div>
                  <div>
                    <div style={{ fontWeight: 500 }}>{`Q: ${item.q}`}</div>
                    <div className="chat-history-meta">{new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                  </div>
                </div>
                {item.a && (
                  <AnswerDisplay
                    answer={item.a}
                    original_answer={item.original}
                    loading={false}
                    error={undefined}
                    chunks={item.chunks}
                    doc_language={item.doc_language}
                    user_language={item.user_language || answerLang}
                    translation_engine={item.translation_engine}
                    translated={item.translated}
                  />
                )}
              </div>
            ))}
            <QuestionInput onAsk={handleAsk} disabled={!docMeta || uploading || loading} answerLang={answerLang} />
          </section>
        </div>
      </main>
    </div>
  );
}

export default App;
