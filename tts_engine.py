import os
import asyncio
import numpy as np
import soundfile as sf
import sys
from pydub import AudioSegment
import shutil
import ffmpeg
import pyrubberband as pyrb

# Assuming the ONNX inference scripts are in xtts_models/
sys.path.append(os.path.join(os.path.dirname(__file__), 'xtts_models'))

_xtts_import_error = None
try:
    from xtts_streaming_pipeline import StreamingTTSPipeline
    import logging
    # Mute both the specific pipeline logger and the root logger that spam token info
    logging.getLogger("data_processing_pipeline").setLevel(logging.ERROR)
    logging.getLogger().setLevel(logging.ERROR)
except ImportError as e:
    _xtts_import_error = str(e)
    StreamingTTSPipeline = None

# Global pipeline instance to avoid reloading models for every segment
_xtts_pipeline = None

def get_xtts_pipeline():
    global _xtts_pipeline
    if _xtts_pipeline is None:
        if StreamingTTSPipeline is None:
            raise RuntimeError(f"XTTS ONNX scripts not found or failed to import. Error: {_xtts_import_error}")
            
        import config
        base_dir = os.path.join(os.path.dirname(__file__), 'xtts_models', 'xtts_onnx')
        mode_str = "INT8" if config.USE_INT8_QUANTIZATION else "FP32"
        print(f"Loading XTTSv2 {mode_str} ONNX models from {base_dir}...")
        _xtts_pipeline = StreamingTTSPipeline(
            model_dir=base_dir,
            vocab_path=os.path.join(base_dir, 'vocab.json'),
            mel_norms_path=os.path.join(base_dir, 'mel_stats.npy'),
            use_int8_gpt=config.USE_INT8_QUANTIZATION
        )
    return _xtts_pipeline

async def generate_audio_from_segments(segments, output_path, total_duration_sec, speaker_profiles=None, voice_cloner=None, target_lang="ru"):
    """Generates full audio track from translated segments using XTTSv2."""
    import config
    mode_str = "INT8" if config.USE_INT8_QUANTIZATION else "FP32"
    print(f"Generating TTS audio using XTTSv2 ({mode_str}) for {len(segments)} segments...")
    
    combined_audio = AudioSegment.silent(duration=int(total_duration_sec * 1000))
    
    temp_dir = "temp_tts"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    
    pipeline = get_xtts_pipeline()
    
    # Pre-compute speaker latents so we don't recalculate them for every segment
    speaker_latents = {}
    if speaker_profiles:
        for speaker, profile in speaker_profiles.items():
            ref_audio = profile.get("ref_audio")
            if ref_audio and os.path.exists(ref_audio):
                print(f"Computing speaker conditioning for {speaker}...")
                speaker_latents[speaker] = pipeline.get_conditioning_latents(ref_audio)
    
    for i, segment in enumerate(segments):
        text = segment.get("text")
        if not text or not text.strip():
            print(f"Warning: Skipping segment {i} due to empty text")
            continue
            
        speaker = segment.get("speaker", "SPEAKER_00")
        
        if speaker not in speaker_latents:
            print(f"Warning: No valid reference audio found for {speaker}. Skipping segment {i}.")
            continue
            
        gpt_cond_latent, speaker_embedding = speaker_latents[speaker]
        temp_file = os.path.join(temp_dir, f"seg_{i}.wav")
        
        print(f"Synthesizing segment {i}/{len(segments)} ({speaker}): {text[:30]}...")
        
        try:
            # We run this synchronously since it's fully CPU bound
            # But asyncio.to_thread prevents blocking the event loop
            def _synthesize():
                import textwrap
                all_audio = []
                
                # XTTS has a hard limit of ~182 chars for Russian. We split safely at 150.
                text_chunks = textwrap.wrap(text, width=150, break_long_words=False)
                
                for chunk in text_chunks:
                    for audio_chunk in pipeline.inference_stream(chunk, target_lang, gpt_cond_latent, speaker_embedding, stream_chunk_size=0):
                        all_audio.append(audio_chunk)
                        
                full_wav = np.concatenate(all_audio, axis=0)
                sf.write(temp_file, full_wav, 24000)
                
            await asyncio.to_thread(_synthesize)
            
            segment_audio = AudioSegment.from_wav(temp_file)
            
            # Speedup if it exceeds time budget
            segment_duration_ms = len(segment_audio)
            target_duration_ms = (segment["end"] - segment["start"]) * 1000
            
            if segment_duration_ms > target_duration_ms * 1.1:
                speed_factor = segment_duration_ms / target_duration_ms
                speed_factor = min(speed_factor, 1.5)
                
                print(f"Speeding up segment {i} by {speed_factor:.2f}x using Rubberband")
                speed_temp_out = os.path.join(temp_dir, f"seg_{i}_fast.wav")
                
                # Smart time stretch using Rubberband
                y, sr = sf.read(temp_file)
                y_stretched = pyrb.time_stretch(y, sr, speed_factor)
                sf.write(speed_temp_out, y_stretched, sr)
                
                segment_audio = AudioSegment.from_file(speed_temp_out)
                
            start_time = segment["start"] * 1000
            combined_audio = combined_audio.overlay(segment_audio, position=int(start_time))
            
        except Exception as e:
            print(f"Error synthesizing segment {i}: {e}")
            
    combined_audio.export(output_path, format="wav")
    print(f"TTS audio saved to {output_path}")
    shutil.rmtree(temp_dir)
