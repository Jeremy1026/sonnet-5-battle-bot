import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORM_ROOT = "/Users/jcurcio/Development/llm-battle"
FIXTURES_DIR = os.path.join(PLATFORM_ROOT, "tests", "fixtures")

for path in (REPO_ROOT, PLATFORM_ROOT, FIXTURES_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)
