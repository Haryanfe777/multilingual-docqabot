import { useState } from 'react';
import { useTranslation } from 'react-i18next';

export default function QuestionInput({ onAsk, disabled }: { onAsk: (question: string, lang: string) => void, disabled?: boolean }) {
  const { t, i18n } = useTranslation();
  const [question, setQuestion] = useState('');
  const answerLang = i18n.language;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim()) {
      onAsk(question, answerLang);
      setQuestion('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="input-area">
      <input
        type="text"
        value={question}
        onChange={e => setQuestion(e.target.value)}
        placeholder={t('Ask a question...')}
        disabled={disabled}
      />
      <button type="submit" disabled={disabled || !question.trim()} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span>{t('Send')}</span>
        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" viewBox="0 0 24 24"><path fill="currentColor" d="M2 21l21-9-21-9v7l15 2-15 2v7z"/></svg>
      </button>
    </form>
  );
} 