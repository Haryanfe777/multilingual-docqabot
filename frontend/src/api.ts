import axios from 'axios';

// Configure base URL for backend API
const API_BASE_URL = 'http://localhost:8000';

export async function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  const response = await axios.post(`${API_BASE_URL}/api/upload`, formData, {
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
  const response = await axios.post(`${API_BASE_URL}/api/ask`, formData);
  return response.data;
}