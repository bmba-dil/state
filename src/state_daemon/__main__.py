"""Entry point for ``python -m state_daemon`` — runs the daemon startup sequence.

Accepts optional ``--project-root`` and ``--socket`` CLI arguments so the
service installer (Phase 055) and the CLI start command (Phase 058) can
override defaults at launch time.
"""

from __future__ import annotations

import asyncio
import os
import sys


def main() -> None:
    """Parse minimal CLI args and run the orchestrator startup."""
    # Parse --project-root and --socket from sys.argv
    # Supports: python -m state_daemon --project-root /path --socket /path/to/sock
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        if argv[i] == "--project-root" and i + 1 < len(argv):
            os.environ["STATE_PROJECT_ROOT"] = argv[i + 1]
            i += 2
        elif argv[i] == "--socket" and i + 1 < len(argv):
            os.environ["STATE_DAEMON_SOCKET"] = argv[i + 1]
            i += 2
        elif argv[i] == "--pid" and i + 1 < len(argv):
            os.environ["STATE_DAEMON_PID"] = argv[i + 1]
            i += 2
        else:
            i += 1

    from src.state_daemon.orchestrator import startup

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(startup())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()
