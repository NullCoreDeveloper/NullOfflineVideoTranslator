import librosa
import numpy as np
import os
from pydub import AudioSegment

def analyze_speaker_pitch(audio_path, segments, speaker_id):
    """
    Analyzes the pitch of a specific speaker in the audio file.
    Returns the average pitch (F0) in Hz.
    """
    print(f"Analyzing pitch for {speaker_id}...")
    
    try:
        # Load the full audio file
        y, sr = librosa.load(audio_path, sr=None)
        
        speaker_pitches = []
        
        for seg in segments:
            if seg.get("speaker") != speaker_id:
                continue
                
            # Extract segment
            start_sample = int(seg["start"] * sr)
            end_sample = int(seg["end"] * sr)
            
            if end_sample - start_sample < 512: # Skip very short segments
                continue
                
            y_seg = y[start_sample:end_sample]
            
            # Extract pitch (F0) using piptrack
            # fmin=50, fmax=400 covers most human speech range
            f0, voiced_flag, voiced_probs = librosa.pyin(
                y_seg, 
                fmin=librosa.note_to_hz('C2'), 
                fmax=librosa.note_to_hz('C6')
            )
            
            # Filter out unvoiced parts (NaNs)
            valid_f0 = f0[~np.isnan(f0)]
            
            if len(valid_f0) > 0:
                speaker_pitches.extend(valid_f0)
                
        if not speaker_pitches:
            print(f"Warning: No valid pitch data found for {speaker_id}")
            return None
            
        avg_pitch = np.mean(speaker_pitches)
        print(f"Average pitch for {speaker_id}: {avg_pitch:.2f} Hz")
        return avg_pitch
        
    except Exception as e:
        print(f"Error analyzing pitch: {e}")
        return None

def detect_gender(pitch_hz):
    """
    Detects gender based on average pitch.
    Threshold is typically around 165-175 Hz.
    """
    if pitch_hz is None:
        return "MALE" # Default
        
    # Simple threshold
    if pitch_hz < 170:
        return "MALE"
    else:
        return "FEMALE"

def get_pitch_adjustment(target_pitch, gender):
    """
    Calculates the pitch shift (in Hz or semitones) needed for TTS.
    Edge-TTS accepts pitch in Hz (e.g. +50Hz) or relative semitones (not supported directly by all voices, but we can try).
    Actually, edge-tts supports +XHz or +Xst (semitones).
    
    We will try to map the speaker's pitch relative to the average for their gender.
    Avg Male: ~120 Hz
    Avg Female: ~210 Hz
    """
    if target_pitch is None:
        return "+0Hz"
        
    base_pitch = 120 if gender == "MALE" else 210
    
    # Calculate difference
    diff = target_pitch - base_pitch
    
    # Dampen the effect so it's not too extreme
    # e.g. if diff is +50Hz, we might only apply +25Hz shift to keep it natural
    adjustment = int(diff * 0.5)
    
    # Format for edge-tts
    sign = "+" if adjustment >= 0 else ""
    return f"{sign}{adjustment}Hz"
def get_speaker_sample(audio_path, segments, speaker, output_dir, target_duration_sec=10):
    """
    Extracts a sample audio clip for the specified speaker by combining multiple segments
    until a target duration (e.g., 10 seconds) is reached.
    Returns the path to the sample file.
    """
    speaker_segments = [s for s in segments if s.get("speaker") == speaker]
    if not speaker_segments:
        return None
        
    # Sort segments by length (longest first) to get the best continuous speech chunks
    speaker_segments.sort(key=lambda s: s["end"] - s["start"], reverse=True)
    
    audio = AudioSegment.from_wav(audio_path)
    combined_sample = AudioSegment.empty()
    
    current_duration_ms = 0
    target_duration_ms = target_duration_sec * 1000
    
    for seg in speaker_segments:
        start_time = seg["start"] * 1000
        end_time = seg["end"] * 1000
        
        chunk = audio[start_time:end_time]
        # Add a tiny bit of silence between chunks to keep it natural
        combined_sample += chunk + AudioSegment.silent(duration=100) 
        current_duration_ms += len(chunk)
        
        if current_duration_ms >= target_duration_ms:
            break
            
    # Cap the audio length to prevent OOM in XTTS (max ~12 seconds)
    max_duration = target_duration_ms + 2000
    if len(combined_sample) > max_duration:
        combined_sample = combined_sample[:max_duration]
    
    sample_dir = os.path.join(output_dir, "speaker_samples")
    os.makedirs(sample_dir, exist_ok=True)
    
    sample_path = os.path.join(sample_dir, f"{speaker}_sample.wav")
    combined_sample.export(sample_path, format="wav")
    
    # Apply DeepFilterNet to clean the sample and remove demucs artifacts
    try:
        print(f"✨ Enhancing voice sample for {speaker} using DeepFilterNet...")
        import subprocess
        import sys
        
        # Опциональная проверка на установленную библиотеку
        try:
            import df.enhance
        except ImportError:
            print("⚠️ ВНИМАНИЕ: DeepFilterNet не установлен! Очистка голоса пропущена.")
            print("💡 Для идеального клонирования установите: pip install deepfilternet (Внимание: скачает ~3 ГБ PyTorch)")
            return sample_path

        clean_sample_path = os.path.join(sample_dir, f"{speaker}_sample_DeepFilterNet3.wav")
        # Run deepFilter directly via Python to bypass PATH issues
        cmd = [
            sys.executable, "-c",
            "import sys; from df.enhance import run; sys.argv=['deepFilter', sys.argv[1], '-o', sys.argv[2]]; sys.exit(run())",
            sample_path, sample_dir
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"DeepFilterNet stderr: {result.stderr}")
            raise Exception(f"Command failed with exit status {result.returncode}")
        if os.path.exists(clean_sample_path):
            print("✨ Voice sample successfully cleaned!")
            return clean_sample_path
        else:
            print("⚠️ DeepFilterNet output file not found. Using original sample.")
    except Exception as e:
        print(f"⚠️ DeepFilterNet enhancement failed: {e}. Using original uncleaned sample.")
    
    return sample_path
