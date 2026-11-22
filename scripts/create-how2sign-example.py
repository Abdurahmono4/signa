"""Synthetic English speech fixture, paired to an existing source phrase for testing."""
import subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.app.core import binary
subprocess.run([binary('ffmpeg'),'-y','-v','error','-f','lavfi','-i','color=c=0x193453:s=1280x720:r=24',
 '-i',str(ROOT/'examples/how2sign-speech.wav'),'-vf',
 "drawtext=text='How2Sign - English speech test':fontcolor=white:fontsize=42:x=(w-tw)/2:y=250,drawtext=text='At least in a physical way.':fontcolor=white:fontsize=36:x=(w-tw)/2:y=340",
 '-c:v','libx264','-c:a','aac','-shortest',str(ROOT/'examples/how2sign-speech.mp4')],check=True)
