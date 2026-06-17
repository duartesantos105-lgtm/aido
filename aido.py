#!/usr/bin/env python3
"""
AIDO - Advanced Intelligence & Digital Operations
Entry point: Run this file to start the AIDO assistant.
"""
import sys
import os
from pathlib import Path

AIDO_DIR = Path(__file__).parent / "AIDO"
sys.path.insert(0, str(AIDO_DIR))
os.chdir(AIDO_DIR)

if __name__ == "__main__":
    from ui import AIDOApp
    app = AIDOApp()
    app.mainloop()
