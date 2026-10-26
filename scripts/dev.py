"""Dev loop: `zensical serve` plus re-rendering .qmd files on change.

Usage: python scripts/dev.py <project-dir>

Zensical watches docs/ and reloads the browser; this script watches the
project's .qmd sources and re-runs `quarto render` for each changed file.
"""

import subprocess
import sys
from pathlib import Path

from watchfiles import watch

project = Path(sys.argv[1] if len(sys.argv) > 1 else "example").resolve()
generated = {project / "docs", project / "site", project / "_freeze", project / ".quarto"}


def is_source(path):
    return not any(parent in generated for parent in path.parents)


server = subprocess.Popen(["zensical", "serve"], cwd=project)
try:
    for changes in watch(project, watch_filter=lambda _, path: is_source(Path(path))):
        changed = {Path(path) for _, path in changes}
        for path in sorted(changed):
            if path.suffix == ".qmd" and path.exists():
                print(f"[dev] rendering {path.name}", flush=True)
                subprocess.run(["quarto", "render", path.name], cwd=project)
            elif path.suffix in {".bib", ".yml", ".js"}:
                print(f"[dev] {path.name} changed, re-rendering project", flush=True)
                subprocess.run(["quarto", "render"], cwd=project)
                break
except KeyboardInterrupt:
    pass
finally:
    server.terminate()
