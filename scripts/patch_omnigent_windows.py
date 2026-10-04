"""Work around an Omnigent 0.16 Windows bug: local Python @tool functions fail with
`AssertionError: pass_fds not supported on Windows` (omnigent/tools/local.py uses a POSIX
fd-3 pipe). Omnigent already ships a stdout response protocol (used for Docker/srt);
this patch selects it on Windows. Idempotent; run `--revert` to undo.

    python scripts/patch_omnigent_windows.py [--revert]
"""
import sys
from pathlib import Path

import omnigent.tools.local as local

OLD = "use_stdout = self._sandbox_config.container_image is not None or srt_active"
NEW = OLD + ' or os.name == "nt"  # patched: no pass_fds on Windows'

path = Path(local.__file__)
src = path.read_text(encoding="utf-8")
if "--revert" in sys.argv:
    path.write_text(src.replace(NEW, OLD), encoding="utf-8")
    print("reverted", path)
elif NEW in src:
    print("already patched", path)
elif OLD in src:
    if "\nimport os" not in src:
        raise SystemExit("unexpected omnigent version: no `import os` in tools/local.py")
    path.write_text(src.replace(OLD, NEW), encoding="utf-8")
    print("patched", path)
else:
    raise SystemExit("unexpected omnigent version: patch target not found; check tools/local.py manually")
