import { useTranslation } from 'react-i18next';
import { useState } from 'react';

const languages = [
  { code: 'en', label: 'English' },
  { code: 'fr', label: 'Français' },
  { code: 'nl', label: 'Nederlands' },
  { code: 'es', label: 'Español' },
  { code: 'pcm', label: 'Pidgin' },
  { code: 'yo', label: 'Yorùbá' },
];

export default function LanguageSelector({ onAnswerLangChange }: { onAnswerLangChange?: (lang: string) => void }) {
  const { i18n, t } = useTranslation();
  const [answerLang, setAnswerLang] = useState(i18n.language);

  const handleUILangChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    i18n.changeLanguage(e.target.value);
  };
  const handleAnswerLangChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setAnswerLang(e.target.value);
    onAnswerLangChange && onAnswerLangChange(e.target.value);
  };

  return (
    <div style={{ marginBottom: 16, display: 'flex', gap: 16 }}>
      <div>
        <label htmlFor="ui-language-select">{t('select_language')} (UI): </label>
        <select id="ui-language-select" value={i18n.language} onChange={handleUILangChange}>
          {languages.map((lang) => (
            <option key={lang.code} value={lang.code}>{lang.label}</option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="answer-language-select">{t('select_language')} (Answer): </label>
        <select id="answer-language-select" value={answerLang} onChange={handleAnswerLangChange}>
          {languages.map((lang) => (
            <option key={lang.code} value={lang.code}>{lang.label}</option>
          ))}
        </select>
      </div>
    </div>
  );
} 