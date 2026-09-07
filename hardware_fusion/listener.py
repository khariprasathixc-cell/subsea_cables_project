"""
Root entrypoint for DAS Hardware Listener.
Calls hardware_fusion/listener.py
"""
import os
import sys

# Add hardware_fusion to sys.path and execute
hardware_fusion_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hardware_fusion')
sys.path.insert(0, hardware_fusion_dir)

from listener import main

if __name__ == "__main__":
    main()
