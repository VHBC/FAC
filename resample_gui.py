import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
from pydub import AudioSegment
from scipy.signal import resample_poly
import soundfile as sf
import tempfile
import subprocess

# Set local ffmpeg and ffprobe path (same directory as script/exe)
script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
AudioSegment.converter = os.path.join(script_dir, "ffmpeg.exe")
AudioSegment.ffprobe = os.path.join(script_dir, "ffprobe.exe")

def resample_no_antialias(data, orig_sr, target_sr):
    gcd = np.gcd(orig_sr, target_sr)
    up = target_sr // gcd
    down = orig_sr // gcd
    return resample_poly(data, up, down, window=np.ones(up))

def convert_file(filepath, target_sr, output_format='wav', force_output_name=None):
    print(f"Processing: {filepath}")
    audio = AudioSegment.from_file(filepath)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    if audio.channels == 2:
        samples = samples.reshape((-1, 2))
    else:
        samples = samples.reshape((-1, 1))

    orig_sr = audio.frame_rate
    resampled = resample_no_antialias(samples, orig_sr, target_sr)

    # Enhanced normalization
    rms = np.sqrt(np.mean(resampled**2))
    if rms > 0:
        normalization_factor = 0.707 / rms
        resampled = resampled * normalization_factor
        peak = np.max(np.abs(resampled))
        if peak > 1:
            resampled = resampled / peak
    resampled = (resampled * 32767).clip(-32768, 32767).astype(np.int16)

    base, _ = os.path.splitext(filepath)
    temp_wav = tempfile.mktemp(suffix=".wav")
    if force_output_name:
        final_output = force_output_name
    else:
        final_output = f"{base}_{target_sr}Hz_ADPCM.wav"

    sf.write(temp_wav, resampled, target_sr)

    result = subprocess.run([
        AudioSegment.converter, "-y", "-i", temp_wav,
        "-acodec", "adpcm_ima_wav", final_output
    ])

    os.remove(temp_wav)

    if result.returncode == 0:
        print(f"Saved: {final_output}")
    else:
        print("FFmpeg failed.")

def select_files():
    try:
        target_sr = int(sr_entry.get())
        if target_sr < 1000:
            raise ValueError
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter a valid sample rate (e.g., 8192)")
        return

    files = filedialog.askopenfilenames(filetypes=[("Audio Files", "*.wav *.mp3 *.flac *.ogg *.aiff *.aif")])
    if not files:
        return

    for file in files:
        try:
            convert_file(file, target_sr, "wav")
        except Exception as e:
            print(f"Error with {file}: {e}")

    messagebox.showinfo("Done", "Conversion complete!")

# If files passed as arguments, run in batch CLI mode
if len(sys.argv) > 1:
    for file in sys.argv[1:]:
        try:
            out_path = os.path.splitext(file)[0] + "_8192Hz_ADPCM.wav"
            convert_file(file, 8192, 'wav', out_path)
        except Exception as e:
            print(f"Error converting {file}: {e}")
    sys.exit(0)

# GUI setup
root = tk.Tk()
root.title("Audio to ADPCM Converter")
root.geometry("420x260")

frame = tk.Frame(root)
frame.pack(expand=True)

tk.Label(frame, text="Batch Convert to ADPCM (No Antialiasing)", font=("Arial", 12)).pack(pady=10)

tk.Label(frame, text="Target Sample Rate (Hz):").pack()
sr_entry = tk.Entry(frame)
sr_entry.insert(0, "8192")
sr_entry.pack(pady=5)
tk.Label(frame, text="Examples: 8192, 12000, 16364", font=("Arial", 9)).pack()

tk.Button(frame, text="Select Audio Files", command=select_files, font=("Comic Sans MS", 14)).pack(pady=20)

root.mainloop()
