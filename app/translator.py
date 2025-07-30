import os
import deepl
from openai import OpenAI
from app.embeddings import get_openai_api_key

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
DEEPL_LANGS = {"EN", "FR", "NL", "ES", "DE", "IT", "PT", "RU", "JA", "ZH"}  # Add more as needed

if not DEEPL_API_KEY:
    raise RuntimeError("DEEPL_API_KEY environment variable not set.")

translator = deepl.Translator(DEEPL_API_KEY)

def translate_text(text: str, target_lang: str, source_lang: str = None) -> str:
    """
    Translate text to target_lang using DeepL if supported, else fallback to OpenAI GPT-4.
    target_lang: e.g., 'EN', 'FR', 'ES', 'NL', 'PCM', 'YO', etc.
    source_lang: e.g., 'EN', 'FR', etc. (optional)
    """
    target_lang_up = target_lang.upper()
    if target_lang_up in DEEPL_LANGS:
        try:
            result = translator.translate_text(text, target_lang=target_lang_up, source_lang=source_lang.upper() if source_lang else None)
            return result.text
        except Exception as e:
            raise RuntimeError(f"DeepL translation failed: {e}")
    else:
        # Fallback to OpenAI GPT-4 for unsupported languages (e.g., Pidgin, Yoruba)
        api_key = get_openai_api_key()
        client = OpenAI(api_key=api_key)
        prompt = f"Translate the following text to {target_lang} (or as close as possible):\n\n{text}"
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"OpenAI translation failed: {e}")
