import wave
import math
import struct
import random

def generate_music(filename, duration=10.0, sample_rate=44100, volume=0.5):
    print(f"Generating musical track to {filename}...")
    num_samples = int(duration * sample_rate)
    
    # Define a simple C Major Arpeggio sequence
    # Notes: C4, E4, G4, C5
    notes = [261.63, 329.63, 392.00, 523.25]
    tempo = 0.25 # seconds per note
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setparams((1, 2, sample_rate, num_samples, 'NONE', 'not compressed'))
        
        for i in range(num_samples):
            t = float(i) / sample_rate
            
            # Which note are we on?
            note_idx = int(t / tempo) % len(notes)
            freq = notes[note_idx]
            
            # Simple Synthesis: Mix of Sine and Sawtooth for "8-bit" like music
            # Vibrato
            vibrato = 1.0 + 0.005 * math.sin(2 * math.pi * 6.0 * t)
            eff_freq = freq * vibrato
            
            # Sine wave
            val_sin = math.sin(2.0 * math.pi * eff_freq * t)
            
            # Harmonics (Sawtooth-ish approximation)
            val_saw = 0.0
            for h in range(1, 6):
                val_saw += (math.sin(2.0 * math.pi * eff_freq * h * t) / h)
            val_saw *= 0.6
            
            # Envelope (pluck effect for each note)
            local_t = (t % tempo) / tempo
            envelope = math.exp(-3.0 * local_t) # Decay
            
            # Combine
            value = (val_sin * 0.5 + val_saw * 0.5) * envelope * volume
            
            # Soft Clipping to prevent distortion
            if value > 1.0: value = 1.0
            if value < -1.0: value = -1.0
            
            sample = int(value * 32767.0)
            wav_file.writeframes(struct.pack('<h', sample))
            
    print(f"Done! Created musical loop: {filename}")

if __name__ == "__main__":
    generate_music("sound.wav")
