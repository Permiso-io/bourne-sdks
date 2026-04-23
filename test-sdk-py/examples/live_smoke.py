"""
Optional: send a single run to the real Permiso API (dashboard verification).

  cd test-sdk-py
  # pip install -e .   (includes permiso-custom-hooks-sdk)
  # export PERMISO_API_KEY=...  or use .env at repo root / cwd

  python examples/live_smoke.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from permiso_custom_hooks import (
    PermisoCustomHooksClient,
    PermisoCustomHooksConfig,
)


def _load_dotenv() -> None:
    here = Path(__file__).resolve().parent
    for path in (here / ".env", here.parent / ".env", here.parent.parent / ".env", Path.cwd() / ".env"):
        if not path.is_file():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))
        break


def main() -> None:
    _load_dotenv()
    key = (os.environ.get("PERMISO_API_KEY") or "").strip()
    if not key:
        print("Set PERMISO_API_KEY in the environment or a .env file.", file=sys.stderr)
        sys.exit(2)
    base_url = (os.environ.get("PERMISO_BASE_URL") or "").strip() or None
    kwargs: dict = {"api_key": key}
    if base_url:
        kwargs["base_url"] = base_url
    client = PermisoCustomHooksClient(PermisoCustomHooksConfig(**kwargs))
    print("runId:", client.get_run_id())
    client.send_event(
        "live_smoke",
        {
            "source": "user",
            "type": "text",
            "text": "test-sdk-py live smoke",
        },
    )
    client.end_run()
    print("done; run ended, new runId (unused):", client.get_run_id())


if __name__ == "__main__":
    main()
