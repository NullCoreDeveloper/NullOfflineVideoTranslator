import os
import json
import time
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import config

_current_key_idx = 0

def configure_gemini():
    global _current_key_idx
    if not config.GEMINI_API_KEYS:
        print("Error: No Gemini API keys found in config!")
        return False
    
    key = config.GEMINI_API_KEYS[_current_key_idx]
    genai.configure(api_key=key)
    print(f"Using Gemini API Key: {key[:8]}... (Key {_current_key_idx + 1} of {len(config.GEMINI_API_KEYS)})")
    
    # Simple Round-Robin for the next call
    _current_key_idx = (_current_key_idx + 1) % len(config.GEMINI_API_KEYS)
    return True

def get_language_name(code):
    langs = {
        "ru": "Russian", "en": "English", "es": "Spanish", "fr": "French",
        "de": "German", "it": "Italian", "pt": "Portuguese", "pl": "Polish",
        "tr": "Turkish", "nl": "Dutch", "cs": "Czech", "ar": "Arabic",
        "zh-cn": "Chinese", "ja": "Japanese", "hu": "Hungarian", "ko": "Korean",
        "hi": "Hindi"
    }
    return langs.get(code.lower(), "Russian")

def translate_segments(segments, target_lang="ru"):
    """Translates a list of Whisper segments using Gemini API."""
    lang_name = get_language_name(target_lang)
    print(f"Translating {len(segments)} segments to {lang_name} using Gemini...")
    
    if not segments:
        return []

    if not configure_gemini():
        print("Falling back to original text due to missing API keys.")
        return segments

    batch_size = config.GEMINI_BATCH_SIZE
    translated_segments = []

    generation_config = {
        "temperature": config.GEMINI_TEMPERATURE,
        "response_mime_type": "application/json",
    }
    
    # We turn off all safety settings because songs/gaming videos can be explicit
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    dynamic_prompt = config.GEMINI_SYSTEM_PROMPT.replace("{TARGET_LANGUAGE}", lang_name)

    model = genai.GenerativeModel(
        model_name=config.GEMINI_MODEL_NAME,
        generation_config=generation_config,
        system_instruction=dynamic_prompt,
        safety_settings=safety_settings
    )

    for i in range(0, len(segments), batch_size):
        batch = segments[i:i + batch_size]
        
        # Prepare payload minimizing token usage
        payload = []
        for j, seg in enumerate(batch):
            payload.append({
                "id": j,
                "speaker": seg.get("speaker", "SPEAKER_00"),
                "text": seg["text"]
            })
            
        json_payload = json.dumps(payload, ensure_ascii=False)
        print(f"Sending batch {i//batch_size + 1}/{(len(segments) + batch_size - 1)//batch_size} to Gemini...")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = model.generate_content(json_payload)
                result_json = json.loads(response.text)
                
                # Merge translation back into original segment structure
                for j, translated_item in enumerate(result_json):
                    if j < len(batch):
                        translated_text = translated_item.get("text", batch[j]["text"])
                        translated_segments.append({
                            "start": batch[j]["start"],
                            "end": batch[j]["end"],
                            "text": translated_text,
                            "original_text": batch[j]["text"],
                            "speaker": batch[j].get("speaker", "SPEAKER_00")
                        })
                break # Success
            except Exception as e:
                print(f"Gemini API Error (Attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print("Switching API key and retrying...")
                    configure_gemini()
                    time.sleep(2)
                else:
                    print("Translation failed for this batch. Using original text.")
                    for seg in batch:
                        translated_segments.append({
                            "start": seg["start"],
                            "end": seg["end"],
                            "text": seg["text"],
                            "original_text": seg["text"],
                            "speaker": seg.get("speaker", "SPEAKER_00")
                        })

    return translated_segments
