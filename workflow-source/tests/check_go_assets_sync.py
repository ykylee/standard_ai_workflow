#!/usr/bin/env python3
"""Go 내장 자산 · SQL 이관 판 1~12 단일 출처 동기화 검사 (M-055 WBS-55.1, hub_go_spec §2.1 · §5.4 · DG5).

3 cases:
  1. 이관 SQL(판 1~12) — Go ``internal/db/migrations.go`` 의 ``V1..V12`` 와 Python ``hub.db.MIGRATIONS`` 바이트 일치
  2. 내장 자산(§2.1) — ``hub-go/internal/assets/`` 사본(``hub_client.py`` · ``standard_block.md`` · ``static/*``)과
     Python 정본 바이트 일치 (실제 파일 집합 포함)
  3. 되주입 — SQL 이관 문자열 1글자 변조 · 내장 자산 1바이트 변조 모두 red 로 잡힌다
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 60

WATCHES = (
    "hub-go/*",
    "workflow-source/core/hub_workflow_standard.md",
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
HUB_GO = REPO_ROOT / "hub-go"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.hub import db as hubdb  # noqa: E402
from workflow_kit.hub import render as hubrender  # noqa: E402
from workflow_kit.hub._standard_snapshot import STANDARD_BLOCK  # noqa: E402

_MIGRATION_RE = re.compile(r"(?m)^const (V\d+) = `([^`]*)`")

_passes: list[str] = []
_failures: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    suffix = f" — {detail}" if detail else ""
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{suffix}")


def parse_go_migrations(go_src: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in _MIGRATION_RE.finditer(go_src)}


def check_migrations_match(go_src: str, py_migrations: list[str]) -> list[str]:
    problems: list[str] = []
    parsed = parse_go_migrations(go_src)
    expected_keys = [f"V{i}" for i in range(1, len(py_migrations) + 1)]
    if sorted(parsed) != sorted(expected_keys):
        problems.append(f"키 불일치: got={sorted(parsed)} want={sorted(expected_keys)}")
        return problems
    for idx, py_sql in enumerate(py_migrations, 1):
        key = f"V{idx}"
        go_sql = parsed[key]
        if go_sql != py_sql:
            problems.append(f"{key} SQL 바이트 불일치 (go_len={len(go_sql)} py_len={len(py_sql)})")
    return problems


def asset_pairs() -> list[tuple[str, bytes, bytes]]:
    py_hub = SOURCE_ROOT / "workflow_kit" / "hub"
    go_assets = HUB_GO / "internal" / "assets"
    pairs: list[tuple[str, bytes, bytes]] = []

    py_client = py_hub / "client" / "hub_client.py"
    go_client = go_assets / "hub_client.py"
    pairs.append(("hub_client.py", go_client.read_bytes() if go_client.is_file() else b"", py_client.read_bytes()))

    go_std = go_assets / "standard_block.md"
    pairs.append((
        "standard_block.md",
        go_std.read_bytes() if go_std.is_file() else b"",
        STANDARD_BLOCK.encode("utf-8"),
    ))
    core_block = hubrender.standard_block_from_core()
    pairs.append((
        "standard_block.md == core/hub_workflow_standard.md",
        go_std.read_bytes() if go_std.is_file() else b"",
        core_block.encode("utf-8"),
    ))

    py_static = py_hub / "static"
    go_static = go_assets / "static"
    all_names = sorted(
        {p.name for p in py_static.iterdir() if p.is_file()}
        | ({p.name for p in go_static.iterdir() if p.is_file()} if go_static.is_dir() else set())
    )
    for name in all_names:
        gp = go_static / name
        pp = py_static / name
        pairs.append((
            f"static/{name}",
            gp.read_bytes() if gp.is_file() else b"<MISSING>",
            pp.read_bytes() if pp.is_file() else b"<MISSING_SRC>",
        ))
    return pairs


def check_assets_match(pairs: list[tuple[str, bytes, bytes]]) -> list[str]:
    problems: list[str] = []
    for label, got, want in pairs:
        if got != want:
            problems.append(f"{label} 불일치 (go={len(got)}B vs py={len(want)}B)")
    return problems


def case_1_migrations_sql_sync() -> str:
    mig_file = HUB_GO / "internal" / "db" / "migrations.go"
    if not mig_file.is_file():
        _record("case 1 (이관 SQL 판 1~12 Go=Python 바이트 일치)", False, "migrations.go 없음")
        return ""
    go_src = mig_file.read_text(encoding="utf-8")
    problems = check_migrations_match(go_src, hubdb.MIGRATIONS)
    _record(
        "case 1 (이관 SQL 판 1~12 Go=Python 바이트 일치)",
        not problems,
        "; ".join(problems) or f"V1~V{len(hubdb.MIGRATIONS)} 바이트 100% 일치",
    )
    return go_src


def case_2_embedded_assets_sync() -> list[tuple[str, bytes, bytes]]:
    pairs = asset_pairs()
    problems = check_assets_match(pairs)
    _record(
        "case 2 (내장 자산 hub_client · standard_block · static/* 바이트 일치)",
        not problems,
        "; ".join(problems) or f"{len(pairs)}/{len(pairs)} 자산 일치",
    )
    return pairs


def case_3_reinjection(go_src: str, pairs: list[tuple[str, bytes, bytes]]) -> None:
    problems: list[str] = []
    if not go_src or not pairs:
        _record("case 3 (되주입 — SQL 변조 · 자산 변조 모두 검출)", False, "선행 case 자료 없음")
        return

    bad_sql_src = go_src.replace("CREATE TABLE meta", "CREATE TABLE meta_tampered", 1)
    if bad_sql_src == go_src or not check_migrations_match(bad_sql_src, hubdb.MIGRATIONS):
        problems.append("SQL 이관 문자열 변조를 검출하지 못했다")

    bad_pairs = list(pairs)
    label0, got0, want0 = bad_pairs[0]
    bad_pairs[0] = (label0, got0 + b" ", want0)
    if not check_assets_match(bad_pairs):
        problems.append("내장 자산 변조를 검출하지 못했다")

    _record(
        "case 3 (되주입 — SQL 변조 · 자산 변조 모두 검출)",
        not problems,
        "; ".join(problems) or "SQL · 자산 양쪽 변조 red 검출 확인",
    )


def main() -> int:
    print("=== Go 내장 자산 · SQL 이관 동기화 (M-055 WBS-55.1) ===")
    go_src = case_1_migrations_sql_sync()
    pairs = case_2_embedded_assets_sync()
    case_3_reinjection(go_src, pairs)
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
