import os
import subprocess
from pydub import AudioSegment

import shutil
import math

def separate_vocals(audio_path, output_dir):
    """Separates vocals from audio using Demucs. Handles large files by chunking."""
    
    # Check for CUDA
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Demucs using device: {device}")

    # Load audio to check duration
    audio = AudioSegment.from_wav(audio_path)
    duration_sec = len(audio) / 1000.0
    
    # Chunk size in seconds (e.g., 10 minutes)
    CHUNK_SIZE = 600 
    
    if duration_sec <= CHUNK_SIZE:
        # Process normally
        return _run_demucs(audio_path, output_dir, device)
    
    print(f"Audio is too long ({duration_sec:.2f}s). Splitting into {CHUNK_SIZE}s chunks...")
    
    # Create temp dir for chunks
    chunks_dir = os.path.join(output_dir, "temp_chunks")
    os.makedirs(chunks_dir, exist_ok=True)
    
    num_chunks = math.ceil(duration_sec / CHUNK_SIZE)
    vocals_chunks = []
    no_vocals_chunks = []
    
    try:
        for i in range(num_chunks):
            start_ms = i * CHUNK_SIZE * 1000
            end_ms = min((i + 1) * CHUNK_SIZE * 1000, len(audio))
            
            chunk = audio[start_ms:end_ms]
            chunk_name = f"chunk_{i}"
            chunk_path = os.path.join(chunks_dir, f"{chunk_name}.wav")
            chunk.export(chunk_path, format="wav")
            
            print(f"Processing chunk {i+1}/{num_chunks}...")
            
            # Process chunk
            # Demucs creates a subfolder for each input file
            chunk_out_dir = os.path.join(chunks_dir, "out")
            v_path, nv_path = _run_demucs(chunk_path, chunk_out_dir, device)
            
            vocals_chunks.append(AudioSegment.from_wav(v_path))
            no_vocals_chunks.append(AudioSegment.from_wav(nv_path))
            
        # Concatenate results
        print("Concatenating chunks...")
        full_vocals = sum(vocals_chunks)
        full_no_vocals = sum(no_vocals_chunks)
        
        # Save final results
        final_out_dir = os.path.join(output_dir, "htdemucs", os.path.splitext(os.path.basename(audio_path))[0])
        os.makedirs(final_out_dir, exist_ok=True)
        
        final_vocals_path = os.path.join(final_out_dir, "vocals.wav")
        final_no_vocals_path = os.path.join(final_out_dir, "no_vocals.wav")
        
        full_vocals.export(final_vocals_path, format="wav")
        full_no_vocals.export(final_no_vocals_path, format="wav")
        
        return final_vocals_path, final_no_vocals_path
        
    finally:
        # Cleanup
        if os.path.exists(chunks_dir):
            shutil.rmtree(chunks_dir)

def _run_demucs(audio_path, output_dir, device):
    """Helper to run demucs on a single file."""
    os.makedirs(output_dir, exist_ok=True)
    
    cmd = [
        "demucs",
        "-n", "htdemucs",
        "--two-stems=vocals",
        "-d", device,
        "-o", output_dir,
        # "-j", "0", # Disable multiprocessing to save RAM?
        audio_path
    ]
    
    # print(f"Running Demucs: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Demucs failed: {e}")
        raise
        
    filename = os.path.splitext(os.path.basename(audio_path))[0]
    vocals_path = os.path.join(output_dir, "htdemucs", filename, "vocals.wav")
    no_vocals_path = os.path.join(output_dir, "htdemucs", filename, "no_vocals.wav")
    
    if not os.path.exists(vocals_path) or not os.path.exists(no_vocals_path):
        raise FileNotFoundError(f"Demucs output files not found for {audio_path}")
        
    return vocals_path, no_vocals_path
def merge_audio(vocals_path, background_path, output_path):
    """Merges vocals and background music using dynamic RMS normalization."""
    print(f"Merging {vocals_path} and {background_path} (with dynamic volume leveling)...")
    vocals = AudioSegment.from_wav(vocals_path)
    bg = AudioSegment.from_wav(background_path)
    
    # Динамическое выравнивание громкости (Нормализация по LUFS/dBFS)
    # 1. Приводим фоновую музыку к стандарту -14 dBFS (чтобы она не "орала" и не клипповала)
    target_bg_dbfs = -14.0
    bg_gain = target_bg_dbfs - bg.dBFS
    bg = bg.apply_gain(bg_gain)
    
    # 2. Приводим голос к стандарту -8 dBFS (на 6 децибел громче музыки)
    target_vocals_dbfs = -8.0
    vocals_gain = target_vocals_dbfs - vocals.dBFS
    vocals = vocals.apply_gain(vocals_gain)
    
    # Накладываем голос на музыку
    combined = bg.overlay(vocals)
    combined.export(output_path, format="wav")
    print(f"Merged audio saved to {output_path}")