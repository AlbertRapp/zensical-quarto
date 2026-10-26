"""Quarto post-render hook: move docs/src/* up to docs/.

Quarto keeps each input's path relative to the project root, so
src/page.qmd renders to docs/src/page.md. Zensical should see docs/page.md.
"""

import os
import shutil
from pathlib import Path

output_dir = Path(os.environ.get("QUARTO_PROJECT_OUTPUT_DIR", "docs"))
nested = output_dir / "src"

if nested.is_dir():
    for item in nested.rglob("*"):
        if item.is_dir():
            continue
        target = output_dir / item.relative_to(nested)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(item, target)
    shutil.rmtree(nested)
