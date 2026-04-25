"""Shared test configuration — suppresses structlog logging during CLI tests.

The structlog configure MUST run before any module that uses
structlog.get_logger() is imported. This conftest is loaded by pytest
before any test modules, ensuring log suppression is in place.
"""

from __future__ import annotations

import logging

import structlog

# Suppress structlog info/debug messages during tests — repair and other
# operational logs are emitted to stdout via ConsoleRenderer and would
# pollute CliRunner-captured output, breaking CLI output assertions.
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL),
)
