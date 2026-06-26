import ffmpeg
import os

def extract_audio(video_path, output_path):
    """Extracts audio from video file."""
    try:
        print(f"Extracting audio from {video_path} to {output_path}...")
        (
            ffmpeg
            .input(video_path)
            .output(output_path, acodec='pcm_s16le', ac=2, ar='44100')
            .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
        )
        print(f"Audio extracted successfully.")
    except ffmpeg.Error as e:
        print(f"Error extracting audio: {e.stderr.decode()}")
        raise

def combine_audio_video(video_path, audio_path, output_path):
    """Combines video (visuals only) with new audio."""
    try:
        print(f"Combining video {video_path} and audio {audio_path} into {output_path}...")
        video = ffmpeg.input(video_path)
        audio = ffmpeg.input(audio_path)
        # Use video['v'] to select video stream, or just video if we map explicitly
        # ffmpeg-python input object doesn't have .v attribute directly sometimes?
        # Let's use video['v'] which is safer.
        stream_v = video['v']
        (
            ffmpeg
            .output(stream_v, audio, output_path, vcodec='copy', acodec='aac')
            .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
        )
        print(f"Video created successfully.")
    except ffmpeg.Error as e:
        print(f"Error combining audio and video: {e.stderr.decode()}")
        raise
