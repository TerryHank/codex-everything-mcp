from pathlib import Path
import sys

src_dir = Path(__file__).resolve().parent / "src"
if src_dir.exists():
    sys.path.insert(0, str(src_dir))

from codex_everything_mcp.server import main


if __name__ == "__main__":
    main()
