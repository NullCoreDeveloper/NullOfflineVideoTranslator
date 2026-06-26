import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN", "")

# Парсим список ключей из переменной окружения (по умолчанию пусто, ключи должны быть в .env)
gemini_keys_str = os.getenv("GEMINI_API_KEYS", "")
GEMINI_API_KEYS = [k.strip() for k in gemini_keys_str.split(",") if k.strip()]

PROXY_URL = os.getenv("PROXY_URL", "")

# Применяем прокси глобально, чтобы edge-tts (озвучка от Microsoft) и скачивание моделей работали через него
if PROXY_URL:
    os.environ["HTTP_PROXY"] = PROXY_URL
    os.environ["HTTPS_PROXY"] = PROXY_URL
    os.environ["ALL_PROXY"] = PROXY_URL

# Настройки перевода через Gemini
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-3.1-flash-lite")
GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.2"))
GEMINI_BATCH_SIZE = int(os.getenv("GEMINI_BATCH_SIZE", "100"))

GEMINI_SYSTEM_PROMPT = os.getenv("GEMINI_SYSTEM_PROMPT", """You are a professional video translator. Translate the 'text' field in the following JSON list of subtitle segments into {TARGET_LANGUAGE}.
Pay attention to the global context of the segments. This is likely a gaming or internet culture video. 
Crucial Rules:
1. Translate gamer tags, usernames, and slang correctly based on context. Do NOT translate names literally (e.g. "Dream" should be "Дрим", not "Мечта". "Notch" is "Нотч", not "Зарубка").
2. Keep the conversational and natural tone. Notice who is speaking based on the "speaker" field to understand dialogue flow.
3. ADD EXCLAMATION MARKS (!!!) and use ALL CAPS for emphasis if the context implies screaming, shouting, or high excitement. The text-to-speech engine relies entirely on punctuation to generate emotion. Do not hesitate to use multiple exclamation marks.
4. Keep the exact same number of items. Return an array of JSON objects with the exact same 'id' and 'speaker', but with the 'text' translated.
5. Return ONLY a valid JSON array of objects, nothing else. No markdown code blocks, just the raw JSON array.

Here is the JSON list of objects to translate:
""")
