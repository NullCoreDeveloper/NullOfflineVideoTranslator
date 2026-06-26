import torch
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
import os
import gc

try:
    import whisperx
except ImportError:
    whisperx = None
    print("Warning: whisperx is not installed. Please run: pip install git+https://github.com/m-bain/whisperx.git")

# Global variables to cache models across function calls to avoid reloading
_audio_cache = {}
_language_cache = "en"

def transcribe_audio(audio_path, model_size="base"):
    """Transcribes audio and aligns timestamps using WhisperX for perfect precision."""
    if whisperx is None:
        raise ImportError("whisperx is not installed. Run: pip install git+https://github.com/m-bain/whisperx.git")
        
    print(f"Loading WhisperX model ({model_size})...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    # Use float16 on GPU, int8 on CPU for speed
    compute_type = "float16" if device == "cuda" else "int8"
    print(f"Using device: {device}, Compute type: {compute_type}")
    
    # 1. Transcribe
    model = whisperx.load_model(model_size, device, compute_type=compute_type)
    audio = whisperx.load_audio(audio_path)
    _audio_cache[audio_path] = audio # Cache audio for diarization step
    
    print(f"Transcribing {audio_path} with batching...")
    batch_size = 16 if device == "cuda" else 4
    result = model.transcribe(audio, batch_size=batch_size)
    _language_cache = result["language"]
    
    # Free VRAM
    del model
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()
        
    # 2. Align timestamps precisely
    print(f"Aligning timestamps using Wav2Vec2...")
    model_a, metadata = whisperx.load_align_model(language_code=_language_cache, device=device)
    result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
    
    # Free VRAM
    del model_a
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()
        
    return result["segments"]

def diarize_audio(audio_path, hf_token):
    """Performs fast batched speaker diarization using WhisperX (Pyannote)."""
    if whisperx is None:
        raise ImportError("whisperx is not installed.")
        
    print(f"Loading WhisperX Diarization pipeline...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    try:
        from whisperx.diarize import DiarizationPipeline
        diarize_model = DiarizationPipeline(use_auth_token=hf_token, device=device)
        
        # Load audio from cache if possible
        audio = _audio_cache.get(audio_path)
        if audio is None:
            audio = whisperx.load_audio(audio_path)
            
        print(f"Diarizing {audio_path}...")
        diarize_segments = diarize_model(audio)
        
        # Free VRAM
        del diarize_model
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
            
        return diarize_segments
    except Exception as e:
        print(f"Diarization error: {e}")
        print("Ensure you have accepted the user agreement for pyannote/speaker-diarization-3.1 on HuggingFace and have a valid token.")
        return None

def mock_diarize_audio(audio_path):
    """Returns mock diarization segments for testing."""
    print("Running MOCK diarization...")
    segments = []
    # Simplified mock for 20 seconds
    segments.append({"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"})
    segments.append({"start": 5.0, "end": 10.0, "speaker": "SPEAKER_01"})
    segments.append({"start": 10.0, "end": 15.0, "speaker": "SPEAKER_00"})
    segments.append({"start": 15.0, "end": 20.0, "speaker": "SPEAKER_01"})
    return segments

def assign_speakers(whisper_segments, diarization_segments):
    """Assigns speakers to segments using WhisperX's built-in intelligent assignment."""
    if diarization_segments is None or len(diarization_segments) == 0:
        print("No diarization segments found. Assigning default speaker.")
        for seg in whisper_segments:
            seg["speaker"] = "SPEAKER_00"
        return whisper_segments

    print("Assigning speakers to segments using WhisperX intersection...")
    
    # We must reconstruct the result dict for whisperx
    result_dict = {"segments": whisper_segments}
    
    # Check if mock segments were passed instead of whisperx pandas dataframe
    if isinstance(diarization_segments, list):
        # Fallback to legacy assignment for mock segments
        for w_seg in whisper_segments:
            w_start, w_end = w_seg["start"], w_seg["end"]
            speaker_overlaps = {}
            for d_seg in diarization_segments:
                overlap = max(0, min(w_end, d_seg["end"]) - max(w_start, d_seg["start"]))
                if overlap > 0:
                    speaker_overlaps[d_seg["speaker"]] = speaker_overlaps.get(d_seg["speaker"], 0) + overlap
            if speaker_overlaps:
                w_seg["speaker"] = sorted(speaker_overlaps.items(), key=lambda x: x[1], reverse=True)[0][0]
            else:
                w_seg["speaker"] = "SPEAKER_00"
        return whisper_segments
        
    # Standard WhisperX intelligent assignment
    try:
        final_result = whisperx.assign_word_speakers(diarization_segments, result_dict)
        return final_result["segments"]
    except Exception as e:
        print(f"Error in assign_word_speakers: {e}. Ensure WhisperX is working properly.")
        # Fallback if assignment fails
        for seg in whisper_segments:
            seg["speaker"] = "SPEAKER_00"
        return whisper_segments
