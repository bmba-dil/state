"""Entry point for ``python -m state_worker``."""

from __future__ import annotations

import asyncio

from state_worker.main import main

if __name__ == "__main__":
    asyncio.run(main())
