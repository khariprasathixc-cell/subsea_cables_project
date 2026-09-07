"""
SubseaGuard Sentinel-X — Unified Pipeline Orchestrator
Launches and manages all three bimodal fusion sub-services:
  1. HTTP Web Server (Port 8000) -> Serves Leaflet GIS frontend
  2. DAS Hardware Listener       -> Captures acoustic / piezo sensor signals
  3. Anomaly Detection Engine   -> Sequential AIS corridor + ML + DAS fusion
Handles graceful shutdown (SIGINT / Ctrl+C) across all child processes.
"""

import os
import sys
import time
import signal
import subprocess
import webbrowser

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
HTTP_PORT = 8000
FRONTEND_URL = f"http://localhost:{HTTP_PORT}/frontend/"

processes = []


def cleanup(signum=None, frame=None):
    """Gracefully terminate all running subprocesses."""
    print("\n" + "=" * 65)
    print("   Shutting down SubseaGuard Sentinel-X services...")
    print("=" * 65)

    for name, proc in reversed(processes):
        if proc.poll() is None:
            print(f"Stopping {name} (PID {proc.pid})...")
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception as e:
                print(f"Error terminating {name}: {e}")

    print("All services stopped cleanly.\n")
    sys.exit(0)


def start_process(name, cmd, cwd=ROOT_DIR):
    """Launch a subprocess and register it for cleanup."""
    print(f"Starting {name}...")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=None,   # Inherit stdout so live logs stream to console
            stderr=None,   # Inherit stderr for debugging
            bufsize=1,
            universal_newlines=True
        )
        processes.append((name, proc))
        return proc
    except Exception as e:
        print(f"Failed to start {name}: {e}")
        cleanup()


def main():
    print("=" * 65)
    print("   SubseaGuard Sentinel-X — Bimodal Sensor Fusion Engine")
    print("=" * 65)
    print(f"Root Directory : {ROOT_DIR}")
    print(f"Python Executable: {sys.executable}")
    print(f"Dashboard URL   : {FRONTEND_URL}")
    print("=" * 65 + "\n")

    # Register signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # 1. Start HTTP Server
    http_cmd = [sys.executable, "-m", "http.server", str(HTTP_PORT)]
    start_process("HTTP Web Server (port 8000)", http_cmd, cwd=ROOT_DIR)
    time.sleep(0.5)

    # 2. Start DAS Hardware Listener
    listener_script = os.path.join(ROOT_DIR, "hardware_fusion", "listener.py")
    listener_cmd = [sys.executable, listener_script]
    start_process("DAS Acoustic/Piezo Listener", listener_cmd, cwd=ROOT_DIR)
    time.sleep(0.5)

    # 3. Start Anomaly Detection Engine
    detection_script = os.path.join(ROOT_DIR, "backend", "anomaly_detection.py")
    detection_cmd = [sys.executable, detection_script]
    start_process("Anomaly Detection & Sensor Fusion", detection_cmd, cwd=ROOT_DIR)

    print("\n" + "=" * 65)
    print("   ✅ ALL SUBSEAGUARD SERVICES OPERATIONAL")
    print("=" * 65)
    print(f"Access Digital Twin Dashboard at: {FRONTEND_URL}")
    print("Tap your piezo sensor / mic to test live DAS confirmation.")
    print("Press Ctrl+C at any time to shut down all processes cleanly.\n")

    # Monitor loop
    try:
        while True:
            for name, proc in processes:
                ret = proc.poll()
                if ret is not None:
                    print(f"\n[Warning] {name} exited unexpectedly with code {ret}")
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
