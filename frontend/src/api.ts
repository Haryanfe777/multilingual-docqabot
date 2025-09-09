import axios from 'axios';

const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';
const API_KEY = (import.meta as any).env?.VITE_API_KEY || '';
const DATASET = (import.meta as any).env?.VITE_DATASET || 'default';

const client = axios.create({ baseURL: API_BASE_URL });
client.interceptors.request.use((config) => {
  if (API_KEY) config.headers['X-API-Key'] = API_KEY;
  return config;
});

export async function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('dataset', DATASET);
  const response = await client.post(`/api/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function askQuestion(question: string, language: string, chatHistory: any[]) {
  const formData = new FormData();
  formData.append('question', question);
  formData.append('doc_id', 'default');
  formData.append('user_lang', language);
  formData.append('chat_history', JSON.stringify(chatHistory));
  formData.append('dataset', DATASET);
  const response = await client.post(`/api/ask`, formData);
  return response.data;
}

export async function summarize(mode: 'document'|'page' = 'document', targetLanguage?: string) {
  const body: any = { mode };
  if (targetLanguage) body.target_language = targetLanguage;
  const response = await client.post(`/api/summarize?dataset=${encodeURIComponent(DATASET)}`, body, {
    headers: { 'Content-Type': 'application/json' },
  });
  return response.data;
}