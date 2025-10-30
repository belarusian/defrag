"""
Entry point for running defrag as a module.

Usage: python -m tools.defrag <command> [options]
"""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
