"""
Plays a smooth sine tone whose pitch and volume can be changed at any time.
Later, the mouse (for testing) and then the Pico's sensors will control it.

Run:  python3 theremin.py
"""

import time
import numpy as np
import sounddevice as sd

# ---------------- Settings ----------------
SAMPLE_RATE = 44100   # samples per second
BLOCK_SIZE = 256      # samples per audio block (~6 ms), small = low delay
MIN_FREQ = 200.0      # lowest note in Hz (hand far away)
MAX_FREQ = 1000.0     # highest note in Hz (hand close)
MAX_VOLUME = 0.3      # keep below 1.0 to protect speakers and ears
GLIDE = 0.15          # 0-1, how fast pitch/volume catch up (lower = smoother)


class ThereminVoice:
    """Generates the tone. Other code just calls set_controls()."""

    def __init__(self):
        self.target_freq = MIN_FREQ
        self.target_vol = 0.0
        self._freq = MIN_FREQ   # current values, glide toward the targets
        self._vol = 0.0
        self._phase = 0.0       # where we are in the sine wave

    def set_controls(self, pitch, volume):
        """pitch and volume are both 0.0 to 1.0."""
        pitch = min(max(pitch, 0.0), 1.0)
        volume = min(max(volume, 0.0), 1.0)
        # Exponential mapping so equal hand movements sound like equal
        # musical steps (that's how our ears hear pitch).
        self.target_freq = MIN_FREQ * (MAX_FREQ / MIN_FREQ) ** pitch
        self.target_vol = volume * MAX_VOLUME

    def callback(self, outdata, frames, time_info, status):
        """Called automatically by sounddevice whenever it needs more audio."""
        # Move part of the way toward the targets (smooths out jumpy sensors)
        freq_end = self._freq + (self.target_freq - self._freq) * GLIDE
        vol_end = self._vol + (self.target_vol - self._vol) * GLIDE

        # Ramp across the block instead of jumping, so there are no clicks
        freqs = np.linspace(self._freq, freq_end, frames, endpoint=False)
        vols = np.linspace(self._vol, vol_end, frames, endpoint=False)

        # Add up the phase sample by sample so the wave stays continuous
        phases = self._phase + np.cumsum(2 * np.pi * freqs / SAMPLE_RATE)
        outdata[:, 0] = vols * np.sin(phases)

        self._phase = phases[-1] % (2 * np.pi)
        self._freq, self._vol = freq_end, vol_end


# ---------------- Test: sweep the pitch up and down ----------------
if __name__ == "__main__":
    voice = ThereminVoice()
    stream = sd.OutputStream(samplerate=SAMPLE_RATE, channels=1,
                             blocksize=BLOCK_SIZE, callback=voice.callback)
    with stream:
        print("Playing an 8-second test sweep... (Ctrl+C to stop early)")
        start = time.time()
        try:
            while time.time() - start < 8:
                t = time.time() - start
                pitch = (np.sin(t * 0.8) + 1) / 2   # slowly goes 0 -> 1 -> 0
                voice.set_controls(pitch, 0.8)
                time.sleep(0.05)   # ~20 updates/sec, like the real sensors
        except KeyboardInterrupt:
            pass
        voice.set_controls(0, 0)   # fade out instead of cutting off
        time.sleep(0.3)
    print("Done.")