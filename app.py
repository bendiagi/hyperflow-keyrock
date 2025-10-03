"""
Streamlit app entry point for HyperFlow
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from visualization.dashboard import main

if __name__ == "__main__":
    main()
