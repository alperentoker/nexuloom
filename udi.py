#!/usr/bin/env python3
"""Backward-compatibility wrapper for udi -> nexuloom CLI."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nexuloom import cli

if __name__ == "__main__":
    cli()
