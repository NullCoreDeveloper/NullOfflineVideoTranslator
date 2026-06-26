import os
import torch
import sys

# Add OpenVoice to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'OpenVoice'))

from openvoice import se_extractor
from openvoice.api import ToneColorConverter

class VoiceCloner:
    def __init__(self, device='cuda:0'):
        if not torch.cuda.is_available():
            device = 'cpu'
        self.device = device
        
        self.ckpt_converter = 'OpenVoice/checkpoints_v2/converter/checkpoint.pth'
        self.config_converter = 'OpenVoice/checkpoints_v2/converter/config.json'
        
        print(f"Loading OpenVoice model on {self.device}...")
        self.tone_color_converter = ToneColorConverter(self.config_converter, device=self.device)
        self.tone_color_converter.load_ckpt(self.ckpt_converter)
        print("OpenVoice model loaded.")
        
    def extract_speaker_embedding(self, audio_path):
        """Extracts speaker embedding from a reference audio file."""
        return self.tone_color_converter.extract_se(audio_path, se_save_path=None)
        
    def clone_voice(self, src_audio_path, output_path, target_se):
        """
        Converts the voice in src_audio_path to match the target_se.
        src_audio_path: Path to the TTS generated audio (base voice).
        output_path: Path to save the converted audio.
        target_se: Target speaker embedding (from original video).
        """
        # Extract source embedding from the input audio itself
        # This works because OpenVoice can convert from "any" voice
        
        # We need a temp dir for se_extractor to save intermediate files
        temp_dir = os.path.join(os.path.dirname(output_path), "temp_se")
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            source_se, _ = se_extractor.get_se(src_audio_path, self.tone_color_converter, target_dir=temp_dir)
            
            self.tone_color_converter.convert(
                audio_src_path=src_audio_path, 
                src_se=source_se, 
                tgt_se=target_se, 
                output_path=output_path,
                message="VideoTranslator" # Watermark
            )
        finally:
            # Cleanup temp dir if needed, or leave it for debug
            # shutil.rmtree(temp_dir, ignore_errors=True)
            pass
