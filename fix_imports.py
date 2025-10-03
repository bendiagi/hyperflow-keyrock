"""
Fix import statements in all Python files
"""

import os
import re
from pathlib import Path

def fix_imports_in_file(file_path):
    """Fix import statements in a single file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix the malformed try/except blocks
    patterns = [
        (r'try:\s*try:\s*from \.\.config import Config\s*except ImportError:\s*from config import Config\s*except ImportError:\s*from config import Config', 
         'try:\n    from ..config import Config\nexcept ImportError:\n    from config import Config'),
        (r'try:\s*try:\s*from \.\.database import DatabaseConnection\s*except ImportError:\s*from database import DatabaseConnection\s*except ImportError:\s*from database import DatabaseConnection',
         'try:\n    from ..database import DatabaseConnection\nexcept ImportError:\n    from database import DatabaseConnection'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    with open(file_path, 'w') as f:
        f.write(content)

def main():
    """Fix all Python files in src directory"""
    src_dir = Path("src")
    
    for py_file in src_dir.rglob("*.py"):
        print(f"Fixing {py_file}")
        fix_imports_in_file(py_file)
    
    print("Import fixes completed!")

if __name__ == "__main__":
    main()
