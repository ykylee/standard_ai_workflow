"""중계 설정 자리 — ``~/.config/workflow-hub/`` (``WORKFLOW_HUB_RELAY_HOME`` 로 바꿈).

파일:
    ``relay.json``        hub · host_id · project_id · name (비밀 아님)
    ``relay.token``       중계 토큰 (600) — 다른 파일 · 로그 · 화면에 싣지 않는다
    ``relay-allow.json``  허용 목록 (§9.3) — 내용은 이 PC 에만, 허브에는 해시만
    ``relay-state.json``  일시정지 · 띄운 세션 기록
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

HOME_ENV = "WORKFLOW_HUB_RELAY_HOME"
#: 허용 목록이 받는 권한 모드 — bypass 계열은 적을 수 없다 (허브도 받지 않는다, 이중).
PERMISSION_MODES = ("default", "acceptEdits", "plan")
#: PC 동시 세션 상한 (요구 R21.6 · Q4).
MAX_SESSIONS = 3


def home() -> Path:
    raw = os.environ.get(HOME_ENV)
    return Path(raw) if raw else Path.home() / ".config" / "workflow-hub"


def _write(path: Path, text: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".")
    try:
        os.chmod(tmp, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def read_json(name: str, default: Any) -> Any:
    path = home() / name
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(name: str, value: Any) -> None:
    _write(home() / name, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def read_token() -> str | None:
    path = home() / "relay.token"
    return path.read_text(encoding="utf-8").strip() if path.is_file() else None


def write_token(token: str) -> None:
    _write(home() / "relay.token", token + "\n")


# --- 허용 목록 (§9.3, DO9) -------------------------------------------------------------

def load_allow() -> list[dict[str, Any]]:
    data = read_json("relay-allow.json", {"dir": []})
    return list(data.get("dir", []))


def save_allow(entries: list[dict[str, Any]]) -> None:
    write_json("relay-allow.json", {"dir": entries})


def allow_digest(entries: list[dict[str, Any]]) -> str:
    """허브에 보내는 것은 이 해시뿐이다 — 경로가 허브 기록 · 화면에 퍼지지 않게."""
    raw = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_entry(e: dict[str, Any]) -> str | None:
    if not isinstance(e.get("alias"), str) or not e["alias"].strip():
        return "alias 가 비었다"
    path = e.get("path")
    if not isinstance(path, str) or not Path(path).is_absolute():
        return "path 는 절대 경로"
    if not Path(path).is_dir():
        return f"디렉터리가 없다: {path}"
    if not isinstance(e.get("project"), str) or not e["project"]:
        return "project 가 비었다"
    if not isinstance(e.get("harnesses"), list) or not e["harnesses"]:
        return "harnesses 가 비었다"
    modes = e.get("permission_modes") or ["default"]
    bad = [m for m in modes if m not in PERMISSION_MODES]
    if bad:
        return f"받지 않는 권한 모드: {bad} — {' · '.join(PERMISSION_MODES)} 만 (bypass 계열 불가)"
    n = e.get("max_sessions", 1)
    if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= MAX_SESSIONS:
        return f"max_sessions 는 1~{MAX_SESSIONS}"
    return None


def check_request(entries: list[dict[str, Any]], project_id: str, target: dict[str, Any],
                  running_by_alias: dict[str, int]) -> tuple[dict[str, Any] | None, str]:
    """승인된 세션 요청을 이 PC 의 허용 목록에 대 본다 — 중앙이 승인했어도 목록 밖이면 거절 (요구 R21.4)."""
    alias = target.get("dir_alias")
    entry = next((e for e in entries if e.get("alias") == alias), None)
    if entry is None:
        return None, f"허용 목록에 없는 별칭: {alias}"
    if entry.get("project") != project_id:
        return None, f"{alias} 는 다른 프로젝트의 별칭이다"
    if target.get("harness") not in entry.get("harnesses", []):
        return None, f"{alias} 에 허용되지 않은 하네스: {target.get('harness')}"
    mode = target.get("permission_mode") or "default"
    if mode not in (entry.get("permission_modes") or ["default"]) or mode not in PERMISSION_MODES:
        return None, f"{alias} 에 허용되지 않은 권한 모드: {mode}"
    if running_by_alias.get(str(alias), 0) >= int(entry.get("max_sessions", 1)):
        return None, f"{alias} 의 동시 세션 상한 {entry.get('max_sessions', 1)}"
    return entry, ""
