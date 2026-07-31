"""
Convenience entry point. All real orchestration logic lives in
scheduler/main.py — this just lets you run `python main.py` from the
project root without typing `python -m scheduler.main`.
"""

from scheduler.main import main

if __name__ == "__main__":
    main()
