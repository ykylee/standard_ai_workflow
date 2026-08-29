#!/usr/bin/env python3
"""Smoke — registry endpoint 기반 mavis alias command/url 합성 (v0.15.22+).

## 왜 이 검사가 필요한가

TASK-2026-08-08-main-011. sync_mavis 가 *지금* mavis alias block 에 `command=None`
만 emit — 그게 곧 mavis 가 *실행할 명령* 이 없으니 *instance 가 못 뜬다*.
registry entry 의 `endpoint` 가 *이미 합성 가능한 단서* 이다. endpoint 가
`cmd:/abs/tool` 형식이면 mavis alias block 에 `command` 와 `args` 를 합성.
`url:http://...` 형식이면 `url` + `type="streamable-http"`. None 이면 둘 다
생략 (alias 는 mavis:<branch> 메타만, 실제 instance 안 뜸 — registry 가
*알림* 역할). 그 외 형식은 그대로 alias 의 endpoint 필드에 (mavis 가 이해
못 함 — caller 책임).

6 cases:
  1) endpoint="cmd:/abs/tool" → alias.command=tool, args=[].
  2) endpoint="url:http://..." → alias.url, type=streamable-http.
  3) endpoint=None → command/url 둘 다 없음.
  4) endpoint="custom:..." → alias.endpoint 보존 (advisory).
  5) endpoint="cmd:" (빈 path) → empty dict (skip).
  6) endpoint_to_mavis_fields direct — 4가지 패턴 단위 검증.

Refs:
  - workflow-source/workflow_kit/common/workspace_registry.py
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import json
import os
import sys
import atexit
import shutil
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
SCRIPTS_DIR = REPO_ROOT / "workflow-source" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from workflow_kit.common import workspace_registry as R  # noqa: E402


#: mkdtemp + 프로세스 종료 시 정리 (v1.1.2, `check_tempdir_leak_guard` case 7).
#:
#: `mkdtemp` 은 `TemporaryDirectory` 와 달리 자동 정리가 **전혀** 없어서 성공한
#: 실행마다 temp dir 이 하나씩 쌓인다. 컨텍스트 매니저가 정석이지만 이 파일의
#: 테스트들은 함수 전체가 한 덩어리라 감싸려면 전부 재들여쓰기해야 한다. 정리
#: 보장은 `atexit` 으로 같게 두고 변경면을 줄인다 — assert 가 중간에 터져도 정리된다.
def _tmpdir(prefix: str) -> Path:
    path = Path(tempfile.mkdtemp(prefix=prefix))
    atexit.register(shutil.rmtree, path, ignore_errors=True)
    return path


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _isolated() -> tuple[Path, Path]:
    reg_dir = _tmpdir("reg-ep-")
    reg_path = reg_dir / "registry.json"
    mavis_dir = _tmpdir("mavis-ep-")
    mavis_path = mavis_dir / "mcp.json"
    os.environ["WORKFLOW_REGISTRY_PATH"] = str(reg_path)
    os.environ["WORKFLOW_MAVIS_GLOBAL_PATH"] = str(mavis_path)
    os.environ["WORKFLOW_HOST_ID"] = "test-host"
    return reg_path, mavis_path


def test_endpoint_cmd_synthesizes_command() -> None:
    """case 1: cmd: → command + args."""
    _, mavis_path = _isolated()
    try:
        R.register("/abs/ws1", branch="cmd-branch", endpoint="cmd:/abs/tool/serve")
        R.sync_mavis(apply_export=True)
        data = json.loads(mavis_path.read_text(encoding="utf-8"))
        alias = data["mcpServers"].get("mavis:cmd-branch")
        _assert(alias is not None, f"mavis:cmd-branch missing: {list(data['mcpServers'])}")
        _assert(
            alias.get("command") == "/abs/tool/serve",
            f"command mismatch: {alias.get('command')}",
        )
        _assert(alias.get("args") == [], f"args mismatch: {alias.get('args')}")
    finally:
        R.unregister(all=True)


def test_endpoint_url_synthesizes_url_and_type() -> None:
    """case 2: url: → url + type."""
    _, mavis_path = _isolated()
    try:
        R.register("/abs/ws2", branch="url-branch", endpoint="url:http://example.com/mcp")
        R.sync_mavis(apply_export=True)
        data = json.loads(mavis_path.read_text(encoding="utf-8"))
        alias = data["mcpServers"].get("mavis:url-branch")
        _assert(alias is not None, f"mavis:url-branch missing")
        _assert(
            alias.get("url") == "http://example.com/mcp",
            f"url mismatch: {alias.get('url')}",
        )
        _assert(
            alias.get("type") == "streamable-http",
            f"type mismatch: {alias.get('type')}",
        )
    finally:
        R.unregister(all=True)


def test_endpoint_none_omits_command_and_url() -> None:
    """case 3: None → 둘 다 생략 (alias 는 메타만)."""
    _, mavis_path = _isolated()
    try:
        R.register("/abs/ws3", branch="none-branch")
        R.sync_mavis(apply_export=True)
        data = json.loads(mavis_path.read_text(encoding="utf-8"))
        alias = data["mcpServers"].get("mavis:none-branch")
        _assert(alias is not None, f"mavis:none-branch missing")
        _assert("command" not in alias, f"command 키가 박혔다: {alias}")
        _assert("url" not in alias, f"url 키가 박혔다: {alias}")
        _assert("args" not in alias, f"args 키가 박혔다: {alias}")
    finally:
        R.unregister(all=True)


def test_endpoint_unknown_preserved_as_field() -> None:
    """case 4: 그 외 형식 → alias.endpoint 보존 (advisory)."""
    _, mavis_path = _isolated()
    try:
        R.register("/abs/ws4", branch="other-branch", endpoint="custom:some-token")
        R.sync_mavis(apply_export=True)
        data = json.loads(mavis_path.read_text(encoding="utf-8"))
        alias = data["mcpServers"].get("mavis:other-branch")
        _assert(alias is not None, f"mavis:other-branch missing")
        _assert(
            alias.get("endpoint") == "custom:some-token",
            f"endpoint 보존 실패: {alias}",
        )
    finally:
        R.unregister(all=True)


def test_endpoint_empty_path_returns_empty() -> None:
    """case 5: cmd: 또는 url: prefix 뒤에 빈 path → empty dict."""
    _, _ = _isolated()
    try:
        # direct 함수 검증
        _assert(R.endpoint_to_mavis_fields("cmd:") == {}, f"cmd: empty not handled")
        _assert(R.endpoint_to_mavis_fields("url:") == {}, f"url: empty not handled")
    finally:
        R.unregister(all=True)


def test_endpoint_to_mavis_fields_direct() -> None:
    """case 6: 4가지 패턴 단위."""
    _, _ = _isolated()
    try:
        # cmd
        out1 = R.endpoint_to_mavis_fields("cmd:/abs/tool")
        _assert(out1 == {"command": "/abs/tool", "args": []}, f"cmd synth: {out1}")
        # url
        out2 = R.endpoint_to_mavis_fields("url:http://x")
        _assert(out2 == {"url": "http://x", "type": "streamable-http"}, f"url synth: {out2}")
        # None
        out3 = R.endpoint_to_mavis_fields(None)
        _assert(out3 == {}, f"None: {out3}")
        # unknown
        out4 = R.endpoint_to_mavis_fields("weird:value")
        _assert(out4 == {"endpoint": "weird:value"}, f"unknown: {out4}")
        # 빈 문자열
        out5 = R.endpoint_to_mavis_fields("")
        _assert(out5 == {}, f"empty: {out5}")
    finally:
        R.unregister(all=True)


def main() -> int:
    tests = [
        test_endpoint_cmd_synthesizes_command,
        test_endpoint_url_synthesizes_url_and_type,
        test_endpoint_none_omits_command_and_url,
        test_endpoint_unknown_preserved_as_field,
        test_endpoint_empty_path_returns_empty,
        test_endpoint_to_mavis_fields_direct,
    ]
    passed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"FAIL  {t.__name__}: {e}")
            return 1
        except Exception as e:  # pragma: no cover
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
            return 2
        print(f"PASS  {t.__name__}")
        passed += 1
    print(f"\n{passed}/{len(tests)} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
