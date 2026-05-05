"""OS service definition generation — launchd plist (macOS) and systemd user unit (Linux).

Task 055.1: Service Template Generator
Task 055.2: Install/Uninstall Commands

Produces valid service definitions that can be installed/removed via ``state daemon
install`` and ``state daemon uninstall``.  The daemon survives user logout (macOS
``RunAtLoad`` / Linux ``WantedBy=default.target``) and system reboot.
"""

from __future__ import annotations

import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Final

import structlog

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Task 055.1 — Service template constants
# ---------------------------------------------------------------------------

PLIST_LABEL: Final[str] = "com.state.daemon"

_PLIST_DIR: Final[str] = str(Path.home() / "Library" / "LaunchAgents")
_PLIST_PATH: Final[str] = str(Path(_PLIST_DIR) / f"{PLIST_LABEL}.plist")

_UNIT_DIR: Final[str] = str(Path.home() / ".config" / "systemd" / "user")
_UNIT_PATH: Final[str] = str(Path(_UNIT_DIR) / "state-daemon.service")

_LOG_DIR: Final[str] = ".state"
_STDOUT_LOG: Final[str] = f"{_LOG_DIR}/daemon.stdout.log"
_STDERR_LOG: Final[str] = f"{_LOG_DIR}/daemon.stderr.log"


def _plist_xml(daemon_path: str, socket_path: str, project_root: str) -> str:
    """Build a valid macOS launchd .plist as a pretty-printed XML string.

    Uses the plist DTD ``-//Apple//DTD PLIST 1.0//EN`` and returns a decoded
    ``str`` (not bytes) for symmetry with ``generate_service_unit``.
    """
    plist_el = ET.Element("plist", version="1.0")
    dict_el = ET.SubElement(plist_el, "dict")

    def _kv(key: str, value: str) -> None:
        k = ET.SubElement(dict_el, "key")
        k.text = key
        v = ET.SubElement(dict_el, "string")
        v.text = value

    def _kb(key: str, value: bool) -> None:
        k = ET.SubElement(dict_el, "key")
        k.text = key
        tag = "true" if value else "false"
        ET.SubElement(dict_el, tag)

    def _ka(key: str, values: list[str]) -> None:
        k = ET.SubElement(dict_el, "key")
        k.text = key
        arr = ET.SubElement(dict_el, "array")
        for item in values:
            el = ET.SubElement(arr, "string")
            el.text = item

    _kv("Label", PLIST_LABEL)
    _ka("ProgramArguments", [
        daemon_path,
        "-m", "state_daemon",
        "--project-root", project_root,
        "--socket", socket_path,
    ])
    _kb("RunAtLoad", True)
    _kb("KeepAlive", True)
    _kv("WorkingDirectory", project_root)
    _kv("StandardOutPath", os.path.join(project_root, _STDOUT_LOG))
    _kv("StandardErrorPath", os.path.join(project_root, _STDERR_LOG))

    raw = ET.tostring(plist_el, encoding="unicode")

    doctype = '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
    doctype += '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'

    from xml.dom import minidom  # noqa: E402

    reparsed = minidom.parseString(raw)
    pretty = reparsed.toprettyxml(indent="\t", encoding="UTF-8")
    decoded = pretty.decode("utf-8")

    # minidom already includes the XML declaration; insert the DOCTYPE after it
    lines = decoded.split("\n")
    out: list[str] = []
    for i, line in enumerate(lines):
        out.append(line)
        if i == 0:  # right after <?xml ...?>
            out.append(doctype.rstrip("\n"))
    return "\n".join(out)


def _service_unit_text(daemon_path: str, socket_path: str, project_root: str) -> str:
    """Build a valid systemd user unit file as a string."""
    unit = (
        "[Unit]\n"
        "Description=State Daemon\n"
        "After=network.target\n"
        "\n"
        "[Service]\n"
        "Type=simple\n"
        f"ExecStart={daemon_path} -m state_daemon --project-root {project_root} --socket {socket_path}\n"
        "Restart=on-failure\n"
        "RestartSec=5\n"
        f"WorkingDirectory={project_root}\n"
        f"StandardOutput=append:{os.path.join(project_root, _STDOUT_LOG)}\n"
        f"StandardError=append:{os.path.join(project_root, _STDERR_LOG)}\n"
        "\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )
    return unit


# Public API
# ---------------------------------------------------------------------------


def generate_plist(daemon_path: str, socket_path: str, project_root: str) -> str:
    """Return a valid macOS launchd .plist XML string for ``com.state.daemon``.

    Args:
        daemon_path: Path to the Python interpreter (``sys.executable``).
        socket_path: Absolute path to the daemon's Unix socket.
        project_root: Project directory for ``WorkingDirectory`` and log outputs.
    """
    return _plist_xml(daemon_path, socket_path, project_root)


def generate_service_unit(daemon_path: str, socket_path: str, project_root: str) -> str:
    """Return a valid systemd ``--user`` unit file for ``state-daemon.service``.

    Args:
        daemon_path: Path to the Python interpreter (``sys.executable``).
        socket_path: Absolute path to the daemon's Unix socket.
        project_root: Project directory for ``WorkingDirectory`` and log outputs.
    """
    return _service_unit_text(daemon_path, socket_path, project_root)


# ---------------------------------------------------------------------------
# Task 055.2 — Install / Uninstall Commands
# ---------------------------------------------------------------------------


def _service_file_path() -> str:
    """Return the OS-appropriate service definition path."""
    if sys.platform == "darwin":
        return _PLIST_PATH
    return _UNIT_PATH


def _service_file_dir() -> str:
    """Return the directory that must exist before writing the service file."""
    if sys.platform == "darwin":
        return _PLIST_DIR
    return _UNIT_DIR


def _install_cmd(path: str) -> tuple[str, ...]:
    """Return the platform command tuple to load/enable the service."""
    if sys.platform == "darwin":
        return ("launchctl", "load", path)
    return ("systemctl", "--user", "enable", "state-daemon.service")


def _start_cmd() -> tuple[str, ...]:
    """Return the platform command tuple to start the service after enabling it."""
    if sys.platform == "darwin":
        # launchctl load already starts the service; no separate command needed.
        return ()
    return ("systemctl", "--user", "start", "state-daemon.service")


def _unload_cmd(path: str) -> tuple[str, ...]:
    """Return the platform command tuple to unload/disable the service."""
    if sys.platform == "darwin":
        return ("launchctl", "unload", path)
    return (
        "systemctl", "--user", "stop", "state-daemon.service",
    )


def _disable_cmd() -> tuple[str, ...]:
    """Return the platform command to disable the user unit (Linux only)."""
    if sys.platform == "darwin":
        return ()
    return ("systemctl", "--user", "disable", "state-daemon.service")


def install_service(
    daemon_path: str | None = None,
    socket_path: str | None = None,
    project_root: str | None = None,
) -> None:
    """Install the OS service definition so the daemon starts at login.

    On macOS this writes ``~/Library/LaunchAgents/com.state.daemon.plist`` and
    calls ``launchctl load``.  On Linux it writes
    ``~/.config/systemd/user/state-daemon.service``, then runs
    ``systemctl --user enable && systemctl --user start``.

    Args:
        daemon_path: Path to ``sys.executable``.  Defaults to ``sys.executable``.
        socket_path: Daemon Unix socket path.  Defaults to
            ``.state/daemon.sock`` resolved from *project_root*.
        project_root: Project directory.  Defaults to ``os.getcwd()``.
    """
    if daemon_path is None:
        daemon_path = sys.executable
    if project_root is None:
        project_root = os.getcwd()
    if socket_path is None:
        socket_path = os.path.join(project_root, ".state", "daemon.sock")

    # --- 1. Generate the service definition ---
    if sys.platform == "darwin":
        content = generate_plist(daemon_path, socket_path, project_root)
    else:
        content = generate_service_unit(daemon_path, socket_path, project_root)

    # --- 2. Write file ---
    dest_dir = _service_file_dir()
    dest_path = _service_file_path()

    os.makedirs(dest_dir, exist_ok=True)
    with open(dest_path, "w") as fh:
        fh.write(content)
    log.info("service_file_written", path=dest_path)

    # --- 3. Load/enable ---
    cmd = _install_cmd(dest_path)
    subprocess.run(cmd, check=True, capture_output=False)
    log.info("service_loaded", cmd=list(cmd))

    # --- 4. Start (Linux only; launchctl load starts automatically) ---
    start = _start_cmd()
    if start:
        subprocess.run(start, check=True, capture_output=False)
        log.info("service_started", cmd=list(start))


def uninstall_service() -> None:
    """Remove and unload the OS service definition.

    On macOS this calls ``launchctl unload`` then removes the plist.
    On Linux it stops, disables, and then removes the unit file.
    """
    dest_path = _service_file_path()

    # --- 1. Unload / stop + disable ---
    unload = _unload_cmd(dest_path)
    if unload:
        # launchctl unload is best-effort if plist already gone
        subprocess.run(unload, capture_output=False)
        log.info("service_unloaded", cmd=list(unload))

    disable = _disable_cmd()
    if disable:
        subprocess.run(disable, capture_output=False)
        log.info("service_disabled", cmd=list(disable))

    # --- 2. Remove file ---
    try:
        os.remove(dest_path)
        log.info("service_file_removed", path=dest_path)
    except FileNotFoundError:
        log.warning("service_file_not_found", path=dest_path)


# ---------------------------------------------------------------------------
# Helpers for CLI
# ---------------------------------------------------------------------------

def current_platform_name() -> str:
    """Return a human-readable platform name."""
    if sys.platform == "darwin":
        return "macOS (launchd)"
    return "Linux (systemd --user)"
