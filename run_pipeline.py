"""
Run the HyperFlow data pipeline
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from main import main

if __name__ == "__main__":
    main()
