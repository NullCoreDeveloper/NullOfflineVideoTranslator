import argparse
import os
import asyncio
import shutil
from pydub import AudioSegment

# Import our modules
import utils
import audio_processor
import transcriber
import translator
import tts_engine
import config

def main():
    parser = argparse.ArgumentParser(description="Video Translator (EN -> RU)")
    parser.add_argument("video_path", help="Path to the input video file")
    parser.add_argument("--hf_token", help="HuggingFace Token for Diarization (pyannote.audio)", default=getattr(config, "HF_TOKEN", os.environ.get("HF_TOKEN")))
    parser.add_argument("--mock_diarization", action="store_true", help="Use mock diarization for testing")
    parser.add_argument("--keep_temp", action="store_true", help="Keep temporary files")
    
    args = parser.parse_args()
    
    video_path = os.path.abspath(args.video_path)
    if not os.path.exists(video_path):
        print(f"Error: File {video_path} not found.")
        return

    if not args.hf_token:
        print("Warning: No HuggingFace Token provided. Diarization will be skipped (Single speaker mode).")
        print("To enable multi-speaker support, provide --hf_token or set HF_TOKEN env var.")

    # Setup paths
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    output_dir = os.path.join(os.path.dirname(video_path), f"{base_name}_translated_ru")
    os.makedirs(output_dir, exist_ok=True)
    
    temp_audio_path = os.path.join(output_dir, "original_audio.wav")
    demucs_output_dir = os.path.join(output_dir, "demucs_out")
    tts_audio_path = os.path.join(output_dir, "tts_vocals.wav")
    final_audio_path = os.path.join(output_dir, "final_audio.wav")
    final_video_path = os.path.join(output_dir, f"{base_name}_ru.mp4")
    
    try:
        # 1. Extract Audio
        if not os.path.exists(temp_audio_path):
            print("Step 1: Extracting audio...")
            utils.extract_audio(video_path, temp_audio_path)
        else:
            print("Step 1: Audio already extracted. Skipping.")
        
        # Get duration
        original_audio = AudioSegment.from_wav(temp_audio_path)
        duration_sec = len(original_audio) / 1000.0
        print(f"Video duration: {duration_sec:.2f} seconds")

        # 2. Separate Vocals
        # 2. Separate Vocals
        # Demucs output folder name is based on input filename (original_audio.wav)
        vocals_path = os.path.join(demucs_output_dir, "htdemucs", "original_audio", "vocals.wav")
        no_vocals_path = os.path.join(demucs_output_dir, "htdemucs", "original_audio", "no_vocals.wav")
        
        if not os.path.exists(vocals_path) or not os.path.exists(no_vocals_path):
            print("Step 2: Separating vocals...")
            vocals_path, no_vocals_path = audio_processor.separate_vocals(temp_audio_path, demucs_output_dir)
        else:
            print("Step 2: Vocals already separated. Skipping.")
        
        # 3. Transcribe & Diarize
        import json
        segments_path = os.path.join(output_dir, "segments.json")
        raw_segments_path = os.path.join(output_dir, "raw_segments.json")
        
        if os.path.exists(segments_path):
            print("Step 3 & 4: Loading fully translated existing segments...")
            with open(segments_path, "r", encoding="utf-8") as f:
                translated_segments = json.load(f)
            segments = translated_segments
        else:
            # Check if we at least have raw transcribed segments
            if os.path.exists(raw_segments_path):
                print("Step 3: Loading existing raw transcribed segments (skipping Whisper)...")
                with open(raw_segments_path, "r", encoding="utf-8") as f:
                    segments = json.load(f)
            else:
                print("Step 3: Transcribing...")
                whisper_segments = transcriber.transcribe_audio(vocals_path)
                
                if args.mock_diarization:
                    diarization_segments = transcriber.mock_diarize_audio(vocals_path)
                    segments = transcriber.assign_speakers(whisper_segments, diarization_segments)
                elif args.hf_token:
                    diarization_segments = transcriber.diarize_audio(vocals_path, args.hf_token)
                    segments = transcriber.assign_speakers(whisper_segments, diarization_segments)
                else:
                    segments = whisper_segments
                    for seg in segments:
                        seg["speaker"] = "SPEAKER_00"
                
                # Save raw segments so we never have to run Whisper again if it crashes later
                with open(raw_segments_path, "w", encoding="utf-8") as f:
                    json.dump(segments, f, ensure_ascii=False, indent=2)
            
            # 4. Translate Text (EN -> RU)
            print("Step 4: Translating...")
            translated_segments = translator.translate_segments(segments, target_lang="ru")
            
            # Save final translated segments
            with open(segments_path, "w", encoding="utf-8") as f:
                json.dump(translated_segments, f, ensure_ascii=False, indent=2)
            
            # Update segments to translated for the next steps
            segments = translated_segments
        
        # Step 4.5: Extract speaker samples for XTTS
        print("Step 4.5: Extracting speaker samples for XTTS...")
        import voice_analyzer
        
        unique_speakers = set(s.get("speaker", "SPEAKER_00") for s in segments)
        speaker_profiles = {}
        
        # OpenVoice is now removed in favor of XTTSv2 ONNX
        voice_cloner = None 

        for speaker in unique_speakers:
            sample_path = None
            try:
                # We need a sample audio for this speaker for XTTSv2 Voice Cloning
                sample_path = voice_analyzer.get_speaker_sample(vocals_path, segments, speaker, output_dir)
                if sample_path:
                    print(f"Extracted voice sample for {speaker}: {sample_path}")
            except Exception as e:
                print(f"Error extracting sample for {speaker}: {e}")

            speaker_profiles[speaker] = {
                "ref_audio": sample_path
            }

        # 5. Generate TTS Audio (Multi-speaker)
        print("Step 5: Generating TTS...")
        if os.path.exists(tts_audio_path):
            try:
                # Check if file is valid and not empty
                if os.path.getsize(tts_audio_path) > 1000:
                    AudioSegment.from_wav(tts_audio_path)
                    print("TTS audio already exists and is valid. Skipping.")
                else:
                    print("TTS audio exists but is too small. Regenerating...")
                    os.remove(tts_audio_path)
                    asyncio.run(tts_engine.generate_audio_from_segments(
                        translated_segments,
                        tts_audio_path,
                        duration_sec,
                        speaker_profiles=speaker_profiles,
                        voice_cloner=voice_cloner
                    ))
            except Exception as e:
                print(f"TTS audio exists but seems corrupted ({e}). Regenerating...")
                if os.path.exists(tts_audio_path):
                    os.remove(tts_audio_path)
                asyncio.run(tts_engine.generate_audio_from_segments(
                    translated_segments,
                    tts_audio_path,
                    duration_sec,
                    speaker_profiles=speaker_profiles,
                    voice_cloner=voice_cloner
                ))
        else:
            asyncio.run(tts_engine.generate_audio_from_segments(
                translated_segments,
                tts_audio_path,
                duration_sec,
                speaker_profiles=speaker_profiles,
                voice_cloner=voice_cloner
            ))
        
        # 6. Merge New Vocals with Background
        if not os.path.exists(final_audio_path):
            print("Step 6: Merging audio...")
            audio_processor.merge_audio(tts_audio_path, no_vocals_path, final_audio_path)
        else:
            print("Step 6: Audio already merged. Skipping.")
        
        # 7. Combine with Video
        print("Step 7: Combining video...")
        utils.combine_audio_video(video_path, final_audio_path, final_video_path)
        
        print(f"\nDone! Translated video saved to: {final_video_path}")
        
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if not args.keep_temp:
            # Cleanup logic
            pass

if __name__ == "__main__":
    main()
