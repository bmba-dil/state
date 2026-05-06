# Phase 113: P0-12 Tool-Name Collision Regression Test

**Gathered:** 2026-05-05
**Status:** Complete
**Mode:** Infrastructure

<domain>
Spawn both servers → assert opencode refuses or mode-gate blocks; name prefix contract.

Created `tests/test_mcp_collision_regression.py` with 9 tests validating tool naming conventions, no overlap between build/teach namespaces, and mode-gate enforcement.
</domain>
