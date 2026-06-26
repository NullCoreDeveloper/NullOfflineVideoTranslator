import edge_tts
import asyncio
import os
import ffmpeg
from pydub import AudioSegment

async def create_speech(text, voice, output_file):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def create_multi_speaker_sample(output_path):
    print("Creating multi-speaker sample video...")
    
    # 1. Generate Speech segments
    # Speaker 1: Male
    # Speaker 2: Female
    
    segments = [
        ("Hello, how are you doing today?", "en-US-ChristopherNeural"),
        ("I am doing very well, thank you. And yourself?", "en-US-AriaNeural"),
        ("I am great. We are testing the new video translator.", "en-US-ChristopherNeural"),
        ("That sounds exciting. Does it support multiple voices?", "en-US-AriaNeural"),
        ("Yes, it should detect us as different speakers.", "en-US-ChristopherNeural")
    ]
    
    combined_audio = AudioSegment.empty()
    
    # Generate and concatenate
    for i, (text, voice) in enumerate(segments):
        temp_file = f"temp_seg_{i}.mp3"
        asyncio.run(create_speech(text, voice, temp_file))
        
        seg_audio = AudioSegment.from_mp3(temp_file)
        combined_audio += seg_audio
        # Add a small pause
        combined_audio += AudioSegment.silent(duration=500)
        
        os.remove(temp_file)
        
    combined_audio.export("sample_conversation.mp3", format="mp3")
    
    # 2. Create Video
    try:
        speech = ffmpeg.input("sample_conversation.mp3")
        
        # Background music
        bg_music = ffmpeg.input('sine=f=440:d=10', f='lavfi').filter('volume', 0.05)
        
        # We need to know duration of speech to set video duration
        duration = len(combined_audio) / 1000.0
        print(f"Total duration: {duration}s")
        
        # Loop background music to match duration? Or just generate enough.
        # Let's generate silence with duration
        
        # Video stream (blue color)
        video = ffmpeg.input(f'color=c=blue:s=1280x720:d={duration}', f='lavfi')
        
        (
            ffmpeg
            .output(video, speech, output_path, vcodec='libx264', acodec='aac', shortest=None)
            .run(overwrite_output=True)
        )
        print(f"Sample video created at {output_path}")
        
    except Exception as e:
        print(f"Error creating sample: {e}")
    finally:
        if os.path.exists("sample_conversation.mp3"):
            os.remove("sample_conversation.mp3")

if __name__ == "__main__":
    create_multi_speaker_sample("multi_speaker_sample.mp4")
