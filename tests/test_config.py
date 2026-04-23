from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from pytest import MonkeyPatch

from src.state_core.config import (
    DEFAULT_OPENCODE_HOST,
    DEFAULT_OPENCODE_PORT,
    find_opencode_config,
    resolve_opencode_url,
)


class TestFindOpencodeConfig:
    def test_returns_none_when_no_config(self, tmp_path: Path) -> None:
        result = find_opencode_config(start_dir=tmp_path)
        assert result is None

    def test_finds_opencode_json(self, tmp_path: Path) -> None:
        cfg = tmp_path / "opencode.json"
        cfg.write_text("{}")
        result = find_opencode_config(start_dir=tmp_path)
        assert result == cfg

    def test_finds_dot_opencode_opencode_json(self, tmp_path: Path) -> None:
        dot_dir = tmp_path / ".opencode"
        dot_dir.mkdir()
        cfg = dot_dir / "opencode.json"
        cfg.write_text("{}")
        result = find_opencode_config(start_dir=tmp_path)
        assert result == cfg

    def test_prefers_opencode_json_over_dot_opencode(self, tmp_path: Path) -> None:
        top = tmp_path / "opencode.json"
        top.write_text("{}")
        dot_dir = tmp_path / ".opencode"
        dot_dir.mkdir()
        dot_cfg = dot_dir / "opencode.json"
        dot_cfg.write_text("{}")
        result = find_opencode_config(start_dir=tmp_path)
        assert result == top

    def test_walks_up_to_parent(self, tmp_path: Path) -> None:
        child = tmp_path / "sub" / "deep"
        child.mkdir(parents=True)
        cfg = tmp_path / "opencode.json"
        cfg.write_text("{}")
        result = find_opencode_config(start_dir=child)
        assert result == cfg

    def test_stops_at_filesystem_root(self) -> None:
        result = find_opencode_config(start_dir=Path("/"))
        assert result is None

    def test_ignores_directories_named_opencode_json(self, tmp_path: Path) -> None:
        d = tmp_path / "opencode.json"
        d.mkdir()
        result = find_opencode_config(start_dir=tmp_path)
        assert result is None

    def test_defaults_to_cwd(self) -> None:
        with patch("src.state_core.config.Path.cwd", return_value=Path("/tmp")):
            result = find_opencode_config()
        assert result is None or result.parent == Path("/tmp")


class TestResolveOpencodeUrl:
    def test_default_fallback(self) -> None:
        url = resolve_opencode_url(start_dir=Path("/nonexistent"))
        assert url == f"http://{DEFAULT_OPENCODE_HOST}:{DEFAULT_OPENCODE_PORT}"

    def test_reads_port_from_opencode_json(self, tmp_path: Path) -> None:
        cfg = tmp_path / "opencode.json"
        cfg.write_text(json.dumps({"server": {"port": 18999, "hostname": "0.0.0.0"}}))
        url = resolve_opencode_url(start_dir=tmp_path)
        assert url == "http://0.0.0.0:18999"

    def test_reads_hostname_only(self, tmp_path: Path) -> None:
        cfg = tmp_path / "opencode.json"
        cfg.write_text(json.dumps({"server": {"hostname": "192.168.1.50"}}))
        url = resolve_opencode_url(start_dir=tmp_path)
        assert url == f"http://192.168.1.50:{DEFAULT_OPENCODE_PORT}"

    def test_port_zero_falls_back_to_default(self, tmp_path: Path) -> None:
        cfg = tmp_path / "opencode.json"
        cfg.write_text(json.dumps({"server": {"port": 0}}))
        url = resolve_opencode_url(start_dir=tmp_path)
        assert url == f"http://{DEFAULT_OPENCODE_HOST}:{DEFAULT_OPENCODE_PORT}"

    def test_port_out_of_range_falls_back(self, tmp_path: Path) -> None:
        cfg = tmp_path / "opencode.json"
        cfg.write_text(json.dumps({"server": {"port": 99999}}))
        url = resolve_opencode_url(start_dir=tmp_path)
        assert url == f"http://{DEFAULT_OPENCODE_HOST}:{DEFAULT_OPENCODE_PORT}"

    def test_malformed_json_falls_back(self, tmp_path: Path) -> None:
        cfg = tmp_path / "opencode.json"
        cfg.write_text("not valid json")
        url = resolve_opencode_url(start_dir=tmp_path)
        assert url == f"http://{DEFAULT_OPENCODE_HOST}:{DEFAULT_OPENCODE_PORT}"

    def test_empty_config_file_falls_back(self, tmp_path: Path) -> None:
        cfg = tmp_path / "opencode.json"
        cfg.write_text("")
        url = resolve_opencode_url(start_dir=tmp_path)
        assert url == f"http://{DEFAULT_OPENCODE_HOST}:{DEFAULT_OPENCODE_PORT}"

    def test_env_var_override(self, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setenv("STATE_OPENCODE_URL", "http://custom:9999")
        url = resolve_opencode_url(start_dir=Path("/nonexistent"))
        assert url == "http://custom:9999"

    def test_env_var_ignores_config_file(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setenv("STATE_OPENCODE_URL", "http://from-env:7777")
        cfg = tmp_path / "opencode.json"
        cfg.write_text(json.dumps({"server": {"port": 18999, "hostname": "0.0.0.0"}}))
        url = resolve_opencode_url(start_dir=tmp_path)
        assert url == "http://from-env:7777"

    def test_env_var_trailing_slash_stripped(self, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setenv("STATE_OPENCODE_URL", "http://test:1234/")
        url = resolve_opencode_url()
        assert url == "http://test:1234"

    def test_server_null_does_not_crash(self, tmp_path: Path) -> None:
        cfg = tmp_path / "opencode.json"
        cfg.write_text(json.dumps({"server": None}))
        url = resolve_opencode_url(start_dir=tmp_path)
        assert url == f"http://{DEFAULT_OPENCODE_HOST}:{DEFAULT_OPENCODE_PORT}"

    def test_missing_server_uses_defaults(self, tmp_path: Path) -> None:
        cfg = tmp_path / "opencode.json"
        cfg.write_text(json.dumps({"other": "data"}))
        url = resolve_opencode_url(start_dir=tmp_path)
        assert url == f"http://{DEFAULT_OPENCODE_HOST}:{DEFAULT_OPENCODE_PORT}"
