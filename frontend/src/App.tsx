import { useState } from 'react';
import './App.css';
import DocumentUpload from './components/DocumentUpload';
import QuestionInput from './components/QuestionInput';
import AnswerDisplay from './components/AnswerDisplay';
import LanguageSelector from './components/LanguageSelector';
import { uploadDocument, askQuestion } from './api';

function App() {
  const [uploading, setUploading] = useState(false);
  const [docMeta, setDocMeta] = useState<any>(null);
  const [answer, setAnswer] = useState('');
  const [originalAnswer, setOriginalAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chunks, setChunks] = useState<any[]>([]);
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [answerLang, setAnswerLang] = useState('en');

  const handleUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      const meta = await uploadDocument(file);
      setDocMeta(meta);
      setChatHistory([]);
      setAnswer('');
      setOriginalAnswer('');
      setChunks([]);
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleAsk = async (q: string, lang: string) => {
    setLoading(true);
    setError(null);
    setAnswer('');
    setOriginalAnswer('');
    setChunks([]);
    try {
      const res = await askQuestion(q, lang, chatHistory);
      setAnswer(res.answer || '');
      setOriginalAnswer(res.original_answer || res.answer || '');
      setChunks(res.chunks || []);
      setChatHistory((prev) => [
        ...prev,
        {
          q,
          a: res.answer || '',
          original: res.original_answer || res.answer || '',
          doc_language: res.doc_language,
          user_language: res.user_language,
          translation_engine: res.translation_engine,
          translated: res.translated,
          timestamp: new Date().toISOString(),
        },
      ]);
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
          {docMeta && <div className="doc-meta">Document: {docMeta.metadata?.file_name || docMeta.file_name}</div>}
          <section className="qa-section">
            {/* Chat bubbles for Q&A history */}
            {chatHistory.map((item, i) => (
              <div key={i} className={`chat-bubble ${i % 2 === 0 ? 'user-bubble' : 'answer-bubble'}` }>
                <div className={`bubble-avatar ${i % 2 === 0 ? 'user' : 'bot'}`}>{i % 2 === 0 ? '🧑' : '🤖'}</div>
                <div>
                  <div style={{ fontWeight: 500 }}>{i % 2 === 0 ? `Q: ${item.q}` : `A: ${item.a}`}</div>
                  <div className="chat-history-meta">{new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                </div>
              </div>
            ))}
            {/* Current answer bubble */}
            {answer && (
              <div className="chat-bubble answer-bubble">
                <div className="bubble-avatar bot">🤖</div>
                <div>
                  <div style={{ fontWeight: 500 }}>A: {answer}</div>
                  <div className="chat-history-meta">{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                </div>
              </div>
            )}
            <AnswerDisplay
              answer={answer}
              original_answer={originalAnswer}
              loading={loading}
              error={error || undefined}
              chunks={chunks}
              doc_language={docMeta?.metadata?.language}
              user_language={answerLang}
              translation_engine={chatHistory.length > 0 ? chatHistory[chatHistory.length-1].translation_engine : undefined}
              translated={chatHistory.length > 0 ? chatHistory[chatHistory.length-1].translated : false}
            />
            <QuestionInput onAsk={handleAsk} disabled={!docMeta || uploading || loading} />
          </section>
        </div>
      </main>
    </div>
  );
}

export default App;
