"""
SubseaGuard Sentinel-X — DAS Acoustic / Piezo Hydrophone Listener
Captures high-frequency acoustic and piezo sensor signals via line-in / microphone at 44.1 kHz.
Streams live real-time RMS VU-meter telemetry and computes FFT dominant peak frequency on transients.
Outputs detections directly to terminal stdout and atomically to hardware_fusion/vibration_signal.json.
"""

import os
import sys
import time
import json
import argparse
import numpy as np
import sounddevice as sd

# Ensure UTF-8 output on all consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Default Acquisition & Signal Parameters
DEFAULT_SAMPLE_RATE = 44100     # 44.1 kHz standard audio acquisition rate
DEFAULT_BLOCK_SIZE = 2048       # 2048 samples per window (~46.4 ms)
DEFAULT_CHANNELS = 1            # Mono hydrophone / piezo stream
DEFAULT_RMS_THRESHOLD = 0.020   # RMS sensitivity threshold for piezo / mic strike
DEFAULT_COOLDOWN = 0.25         # Seconds between repeated hit notifications

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VIBRATION_SIGNAL_FILE = os.path.join(CURRENT_DIR, "vibration_signal.json")

# Module runtime state
last_hit_time = 0.0
last_meter_time = 0.0
active_threshold = DEFAULT_RMS_THRESHOLD


def write_signal(payload, retries=5, delay=0.005):
    """Atomically update vibration_signal.json with Windows lock resilience."""
    tmp_file = VIBRATION_SIGNAL_FILE + f".tmp.{os.getpid()}"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        for attempt in range(retries):
            try:
                os.replace(tmp_file, VIBRATION_SIGNAL_FILE)
                break
            except PermissionError:
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    try:
                        with open(VIBRATION_SIGNAL_FILE, "w", encoding="utf-8") as f:
                            json.dump(payload, f, indent=2)
                    except Exception:
                        pass
    except Exception:
        pass
    finally:
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except Exception:
                pass


def audio_callback(indata, frames, time_info, status):
    """Process incoming audio block, stream live VU meter, and detect acoustic transient spikes."""
    global last_hit_time, last_meter_time, active_threshold

    if status:
        pass

    audio_samples = indata[:, 0].astype(np.float64)
    rms = float(np.sqrt(np.mean(audio_samples ** 2)))
    energy = float(np.sum(audio_samples ** 2))
    now = time.time()

    # Detect transient strike
    if rms >= active_threshold:
        # Compute FFT and find peak dominant frequency (ignoring DC bin at 0 Hz)
        fft_vals = np.abs(np.fft.rfft(audio_samples))
        if len(fft_vals) > 1:
            fft_vals[0] = 0.0  # Filter out 0 Hz DC offset

        freqs = np.fft.rfftfreq(len(audio_samples), d=1.0 / DEFAULT_SAMPLE_RATE)
        peak_idx = int(np.argmax(fft_vals))
        peak_freq = float(freqs[peak_idx])

        if now - last_hit_time >= DEFAULT_COOLDOWN:
            timestamp_str = time.strftime("%H:%M:%S", time.localtime(now)) + f".{int((now % 1) * 1000):03d}"
            # Print newline then formatted transient alert
            sys.stdout.write(
                f"\r\n[💥 DAS TRANSIENT DETECTED] Peak Freq: {peak_freq:>7.1f} Hz | Energy: {energy:>8.4f} | RMS: {rms:>6.4f} | Time: {timestamp_str}\n"
            )
            sys.stdout.flush()
            last_hit_time = now

        payload = {
            "vibration_detected": True,
            "frequency_hz": round(peak_freq, 2),
            "energy": round(energy, 4),
            "timestamp": now
        }
        write_signal(payload)

    # Live RMS VU-meter bar (~10-15 Hz throttle for smooth terminal rendering)
    if now - last_meter_time >= 0.08:
        bar_len = 20
        # Scale RMS: 0.0 to 0.05 covers ambient -> threshold
        fill_count = int(min(rms / max(active_threshold, 0.001) * bar_len, bar_len))
        bar = "=" * fill_count + " " * (bar_len - fill_count)
        status_text = "TRIGGER" if rms >= active_threshold else "IDLE   "
        
        sys.stdout.write(f"\r[AUDIO IN] RMS: {rms:0.4f} | Level: [{bar}] | Status: {status_text}")
        sys.stdout.flush()
        last_meter_time = now


def print_device_audit():
    """List all detected audio input devices and host APIs."""
    print("\n--- Audio Input Devices Detected ---", flush=True)
    devices = sd.query_devices()
    host_apis = sd.query_hostapis()
    default_input_idx = sd.default.device[0]

    for idx, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            is_default = (idx == default_input_idx)
            marker = " -> [ACTIVE DEFAULT]" if is_default else ""
            api_name = host_apis[dev['hostapi']]['name']
            print(f"  [{idx:2d}] {dev['name']} ({api_name}, In: {dev['max_input_channels']}ch){marker}", flush=True)
    print("------------------------------------\n", flush=True)


def main():
    global active_threshold

    parser = argparse.ArgumentParser(description="SubseaGuard DAS Audio / Piezo Listener")
    parser.add_argument("--device", type=int, default=None, help="Input audio device index")
    parser.add_argument("--threshold", type=float, default=DEFAULT_RMS_THRESHOLD, help="RMS trigger threshold (default: 0.020)")
    parser.add_argument("--list-devices", action="store_true", help="List audio devices and exit")
    args = parser.parse_args()

    if args.list_devices:
        print_device_audit()
        sys.exit(0)

    active_threshold = args.threshold

    # Device resolution
    try:
        if args.device is not None:
            device_info = sd.query_devices(args.device)
            selected_device = args.device
            device_name = f"[{selected_device}] {device_info['name']}"
        else:
            default_idx = sd.default.device[0]
            device_info = sd.query_devices(default_idx) if default_idx is not None and default_idx >= 0 else sd.query_devices(kind='input')
            selected_device = default_idx
            device_name = f"[{selected_device}] {device_info['name']}"
    except Exception as e:
        selected_device = None
        device_name = f"Default Microphone ({e})"

    print("=" * 75, flush=True)
    print("   SubseaGuard Sentinel-X — Audio-Rate Hydrophone Listener (44.1 kHz)", flush=True)
    print("=" * 75, flush=True)
    print(f"Active Audio Device : {device_name}", flush=True)
    print(f"Sampling Rate       : {DEFAULT_SAMPLE_RATE} Hz (44.1 kHz)", flush=True)
    print(f"Block Size          : {DEFAULT_BLOCK_SIZE} samples ({DEFAULT_BLOCK_SIZE / DEFAULT_SAMPLE_RATE * 1000:.1f} ms window)", flush=True)
    print(f"RMS Trigger Level   : {active_threshold:.4f}", flush=True)
    print(f"Signal Target File  : {VIBRATION_SIGNAL_FILE}", flush=True)
    print("=" * 75, flush=True)

    print_device_audit()

    # Initialize vibration signal file with clean idle state
    write_signal({
        "vibration_detected": False,
        "frequency_hz": 0.0,
        "energy": 0.0,
        "timestamp": time.time()
    })

    print("🟢 Live Audio Stream Initialized. Tap your piezo sensor or microphone...\n", flush=True)

    try:
        with sd.InputStream(
            device=selected_device,
            samplerate=DEFAULT_SAMPLE_RATE,
            channels=DEFAULT_CHANNELS,
            blocksize=DEFAULT_BLOCK_SIZE,
            dtype='float32',
            callback=audio_callback
        ):
            while True:
                time.sleep(0.05)
    except KeyboardInterrupt:
        sys.stdout.write("\n\nListener terminated cleanly.\n")
        sys.stdout.flush()
        sys.exit(0)
    except Exception as e:
        sys.stdout.write(f"\n\n[Audio Stream Error] {e}\nListener terminated cleanly.\n")
        sys.stdout.flush()
        sys.exit(0)


if __name__ == "__main__":
    main()
