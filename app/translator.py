import os
import logging
from functools import lru_cache
from typing import Optional, List

try:
    import deepl
except ImportError:
    deepl = None

try:
    from langdetect import detect as ld_detect
except ImportError:
    ld_detect = None


LANG_NORMALIZATION = {
    "en": "EN",
    "en-us": "EN-US",
    "en-gb": "EN-GB",
    "fr": "FR",
    "es": "ES",
    "de": "DE",
    "it": "IT",
    "pt": "PT-PT",
    "pt-br": "PT-BR",
    "nl": "NL",
    "sv": "SV",
    "fi": "FI",
    "da": "DA",
    "no": "NB",
    "pl": "PL",
    "ru": "RU",
    "tr": "TR",
    "zh": "ZH",
    "ja": "JA",
    "ko": "KO",
}


def _get_deepl_auth_key() -> Optional[str]:
    return os.getenv("DEEPL_API_KEY") or os.getenv("DEEPL_AUTH_KEY")


def has_deepl() -> bool:
    return deepl is not None and bool(_get_deepl_auth_key())


@lru_cache(maxsize=1)
def get_deepl_translator() -> Optional["deepl.Translator"]:
    if deepl is None:
        logging.warning("deepl package not installed. Translation disabled.")
        return None
    auth_key = _get_deepl_auth_key()
    if not auth_key:
        logging.warning("DEEPL_API_KEY not set. Translation disabled.")
        return None
    try:
        return deepl.Translator(auth_key)
    except Exception as e:
        logging.error(f"Failed to initialize DeepL translator: {e}")
        return None


def normalize_language_code(code: Optional[str], default: str = "EN") -> str:
    if not code:
        return default
    code = code.strip().lower()
    return LANG_NORMALIZATION.get(code, code.upper())


def detect_language(text: str, fallback: str = "en") -> str:
    if not text or len(text.strip()) == 0:
        return fallback
    if ld_detect is not None:
        try:
            return ld_detect(text)
        except Exception:
            return fallback
    return fallback


def _split_paragraphs(text: str, max_len: int = 4000) -> List[str]:
    if len(text) <= max_len:
        return [text]
    parts: List[str] = []
    current: List[str] = []
    length = 0
    for para in text.split("\n\n"):
        p = para.strip()
        if not p:
            continue
        if length + len(p) + 2 > max_len:
            if current:
                parts.append("\n\n".join(current))
            current = [p]
            length = len(p)
        else:
            current.append(p)
            length += len(p) + 2
    if current:
        parts.append("\n\n".join(current))
    return parts


@lru_cache(maxsize=512)
def translate_text(text: str, target_lang: str, source_lang: Optional[str] = None) -> str:
    """
    Translate text using DeepL if available; otherwise return text unchanged.
    Uses simple paragraph chunking and a small LRU cache to reduce cost.
    """
    translator = get_deepl_translator()
    if translator is None:
        return text
    try:
        tgt = normalize_language_code(target_lang)
        src = normalize_language_code(source_lang) if source_lang else None
        chunks = _split_paragraphs(text)
        outputs: List[str] = []
        for chunk in chunks:
            if not chunk:
                continue
            if src:
                result = translator.translate_text(chunk, target_lang=tgt, source_lang=src)
            else:
                result = translator.translate_text(chunk, target_lang=tgt)
            outputs.append(result.text)
        return "\n\n".join(outputs)
    except Exception as e:
        logging.error(f"DeepL translation failed, returning original text: {e}")
        return text


