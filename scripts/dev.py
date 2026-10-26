"""Dev loop: `zensical serve` plus re-rendering .qmd files on change.

Usage: python scripts/dev.py <project-dir>

Zensical watches docs/ and reloads the browser; this script watches src/
and re-runs `quarto render` for each changed source file.
"""

import subprocess
import sys
from pathlib import Path

from watchfiles import watch

project = Path(sys.argv[1] if len(sys.argv) > 1 else "example").resolve()
src = project / "src"

server = subprocess.Popen(["zensical", "serve"], cwd=project)
try:
    for changes in watch(src):
        changed = {Path(path) for _, path in changes}
        for path in sorted(changed):
            if path.suffix in {".qmd", ".md"} and path.exists():
                print(f"[dev] rendering {path.relative_to(project)}", flush=True)
                subprocess.run(["quarto", "render", str(path.relative_to(project))], cwd=project)
            elif path.suffix in {".bib", ".yml", ".js", ".css"}:
                print(f"[dev] {path.name} changed, re-rendering project", flush=True)
                subprocess.run(["quarto", "render"], cwd=project)
                break
except KeyboardInterrupt:
    pass
finally:
    server.terminate()
