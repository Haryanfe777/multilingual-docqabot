import { useState } from 'react';
import { useTranslation } from 'react-i18next';

interface Chunk {
  text: string;
  metadata?: { source?: string };
}

interface AnswerDisplayProps {
  answer: string;
  original_answer?: string;
  loading: boolean;
  error?: string;
  chunks?: Chunk[];
  doc_language?: string;
  user_language?: string;
  translation_engine?: string;
  translated?: boolean;
}

export default function AnswerDisplay({ answer, original_answer, loading, error, chunks, doc_language, user_language, translation_engine, translated }: AnswerDisplayProps) {
  const { t } = useTranslation();
  const [showOriginal, setShowOriginal] = useState(false);
  if (loading) return <div>{t('answer')}: ...</div>;
  if (error) return <div style={{ color: 'red' }}>{error}</div>;
  if (!answer) return null;
  return (
    <div style={{ marginTop: 16 }}>
      <div className={`chat-bubble answer-bubble`}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <strong>{t('answer')}:</strong>
          {translated && (
            <span className="translation-badge">{t('Translated from X', { lang: doc_language })} {translation_engine && `(${translation_engine})`}</span>
          )}
          {translated && (
            <button className="toggle-btn" onClick={() => setShowOriginal((v) => !v)}>
              {showOriginal ? t('Show Translated') : t('Show Original')}
            </button>
          )}
        </div>
        <div style={{ marginTop: 8 }}>
          {translated && showOriginal ? original_answer : answer}
        </div>
        <div className="lang-info" style={{ fontSize: 12, color: '#888', marginTop: 8 }}>
          {t('Document Language')}: {doc_language || '-'} | {t('Your Language')}: {user_language || '-'}
        </div>
      </div>
      {chunks && chunks.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <strong>Supporting Chunks:</strong>
          <ul>
            {chunks.map((chunk, i) => (
              <li key={i} style={{ marginBottom: 8 }}>
                <div style={{ fontStyle: 'italic', color: '#444' }}>{chunk.text}</div>
                {chunk.metadata?.source && <div style={{ fontSize: 12, color: '#888' }}>Source: {chunk.metadata.source}</div>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
} 