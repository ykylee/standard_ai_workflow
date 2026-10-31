"""workflow_kit.common.atomic_write helper smoke test (v0.7.15+).

POSIX 의 os.replace atomic guarantee 기반 JSON / text atomic write.

Test list:
1. test_atomic_write_json_creates_file: 부재 path → file 생성 + 내용 정합
2. test_atomic_write_json_replaces_existing: 기존 file → 새 내용으로 replace
3. test_atomic_write_json_atomicity: tmp file 패턴 + os.replace 사용 검증 (POSIX)
4. test_atomic_write_preserves_existing_newline: **개행 관례 보존** — 기존 CRLF 는
   CRLF, 기존 LF 는 LF, 신규는 LF (2026-10-31 실측 — 재발 방지)
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/workflow_kit/common/*",
)

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
ATOMIC_WRITE = SOURCE_ROOT / "workflow_kit" / "common" / "atomic_write.py"


def _import_atomic():
    """atomic_write 모듈 importlib 로 load."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("atomic_write", str(ATOMIC_WRITE))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- Test 1: 부재 path → file 생성 + 내용 정합 ---


def test_atomic_write_json_creates_file() -> None:
    """부재 dir + 부재 file → atomic_write_json 으로 file 생성 + 내용 검증."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "subdir" / "state.json"
        data = {"session": {"in_progress": [], "recent_done": ["v0.7.14"]}, "memory": {"last_freeze": "2026-06-15"}}
        mod = _import_atomic()
        mod.atomic_write_json(target, data)

        assert target.exists(), "file not created"
        assert target.parent.exists(), "parent dir not created"
        body = target.read_text(encoding="utf-8")
        loaded = json.loads(body)
        assert loaded == data, f"content mismatch: {loaded} != {data}"


# --- Test 2: 기존 file → 새 내용으로 replace ---


def test_atomic_write_json_replaces_existing() -> None:
    """기존 file 의 내용을 새 dict 로 replace. 이전 내용 부재 확인."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "state.json"
        # initial content
        target.write_text(json.dumps({"v": 1}), encoding="utf-8")
        pre = target.read_text(encoding="utf-8")
        assert "v\": 1" in pre

        # replace
        mod = _import_atomic()
        new_data = {"session": {"in_progress": [], "recent_done": []}, "memory": {"version": "0.7.15"}}
        mod.atomic_write_json(target, new_data)

        post = target.read_text(encoding="utf-8")
        loaded = json.loads(post)
        assert loaded == new_data
        # old content absent
        assert '"v": 1' not in post, "old content not removed"


# --- Test 3: atomicity (tmp file + os.replace 패턴 검증) ---


def test_atomic_write_json_atomicity() -> None:
    """atomic_write_json 가 tempfile + os.replace 패턴 사용. (POSIX atomic guarantee)

    source code level 검증: 'tempfile' + 'os.replace' + 'mkstemp' 의 import / 사용 존재.
    """
    text = ATOMIC_WRITE.read_text()
    # import 검증
    assert "import tempfile" in text, "tempfile import missing"
    assert "import os" in text, "os import missing"
    # 핵심 atomic 패턴
    assert "os.replace" in text, "os.replace call missing (POSIX atomic rename)"
    assert "mkstemp" in text, "mkstemp call missing (unique tmp file)"
    assert "os.fsync" in text, "os.fsync call missing (durability before rename)"
    # tmp file prefix (target dir)
    assert "tmp" in text, "tmp file marker missing"


# --- Test 4: 개행 관례 보존 (EOL 뒤집힘 재발 방지) ---


def test_atomic_write_preserves_existing_newline() -> None:
    """정본 writer 가 **대상 파일의 개행 관례를 지킨다**.

    2026-10-31 실측 — writer 가 `newline="\\n"` 을 고정했더니, Windows 에서
    CRLF 로 쓰여 있던 task 파일이 **LF 로 뒤집혔다**. 내용은 같은데 바이트가
    달라졌고, git 은 정규화해 그 차이를 감췄다 — 그래서 "오른 것 같고 실제로는
    다른 파일"이 됐다.

    그래서 규칙은 하나다:
      - **기존 파일이면 그 파일의 관례를 지킨다** (CRLF → CRLF, LF → LF).
      - **신규 파일이면 LF** (저장소 표준).

    이 검사가 red 면 writer 가 개행을 덮어쓴다 — 재발 방지 게이트다.
    """
    mod = _import_atomic()
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # 1) 신규 파일 → LF
        fresh = root / "fresh.txt"
        mod.atomic_write_text(fresh, "a\nb\n")
        assert b"\r\n" not in fresh.read_bytes(), "신규 파일은 LF 여야 한다"

        # 2) 기존 CRLF 파일 → CRLF 유지
        crlf = root / "crlf.txt"
        crlf.write_bytes(b"old\r\n")
        mod.atomic_write_text(crlf, "new\r\n")
        body = crlf.read_bytes()
        assert b"\r\n" in body, "기존 CRLF 파일의 CRLF 가 뒤집혔다"
        assert b"\n\n" not in body.replace(b"\r\n", b""), "CRLF 파일에 혼합 개행이 생겼다"

        # 3) 기존 LF 파일 → LF 유지
        lf = root / "lf.txt"
        lf.write_bytes(b"old\n")
        mod.atomic_write_text(lf, "new\n")
        assert b"\r\n" not in lf.read_bytes(), "기존 LF 파일이 CRLF 로 뒤집혔다"

        # 4) JSON 도 같은 규칙 — CRLF JSON 이 CRLF 로 유지되고 여전히 유효 JSON
        crlf_json = root / "crlf.json"
        crlf_json.write_bytes(b'{\r\n  "a": 1\r\n}\r\n')
        mod.atomic_write_json(crlf_json, {"a": 2})
        raw = crlf_json.read_bytes()
        assert b"\r\n" in raw, "기존 CRLF JSON 의 CRLF 가 뒤집혔다"
        assert json.loads(raw.decode("utf-8")) == {"a": 2}, "CRLF JSON 이 유효하지 않다"


# --- 메인 실행 ---


def main() -> int:
    test_funcs = [
        test_atomic_write_json_creates_file,
        test_atomic_write_json_replaces_existing,
        test_atomic_write_json_atomicity,
        test_atomic_write_preserves_existing_newline,
    ]

    failed: list[str] = []
    for fn in test_funcs:
        name = fn.__name__
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as e:
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
            failed.append(name)

    total = len(test_funcs)
    passed = total - len(failed)
    print(f"\n{passed}/{total} tests passed.")
    if failed:
        print(f"\n{len(failed)} tests failed:")
        for name in failed:
            print(f"  - {name}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
