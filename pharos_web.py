"""Run the Pharos local interface directly from a source checkout."""
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from pharos.server import main  # noqa: E402


if __name__ == "__main__":
    main()
