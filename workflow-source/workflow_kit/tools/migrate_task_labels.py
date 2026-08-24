#!/usr/bin/env python3
"""task 본문 라벨을 **정본 표기로 통일**한다 (TASK-2026-08-24-main-004).

    wk migrate-task-labels                 # dry-run (기본)
    wk migrate-task-labels --apply
    wk migrate-task-labels --json

## 왜 필요한가

`TASK_FIELD_LABELS` 가 2026-08-20 에 영어로 뒤집혔다. 읽는 쪽은
`TASK_FIELD_ALIASES` 가 두 표기를 다 받으므로 **동작은 옳았지만**, 코퍼스는
섞인 채 남았다 (실측 2026-08-24: task 298개 중 한국어만 188 / 영어만 9 /
**한 파일 안 혼재 2**).

혼재는 정적이 아니다. `wk backlog-update --mode update` 는 **건드린 필드만**
정본 표기로 다시 쓰므로, 옛 파일을 갱신할 때마다 한 파일 안에 두 표기가
생긴다. 쓸수록 자란다.

## 왜 도구인가

손으로 고치면 파싱 계약이 조용히 깨진다 (정본 §11). 그리고 이 문제는 이
저장소만의 것이 아니다 — 같은 kit 을 쓰는 **소비자 저장소도 같은 레거시
코퍼스**를 갖는다. 일회성 스크립트로 처리하면 그들에게는 아무것도 남지 않는다.

## 안전 장치 — 파싱 동일성이 잠금장치다

**바꾼 뒤 파서가 다르게 읽으면 적용하지 않는다.** 라벨 표기는 사람이 읽는
면이고 상태의 근거는 frontmatter 이므로, 이 마이그레이션은 정의상 집계를
바꾸면 안 된다. 바뀐다면 그것은 마이그레이션이 아니라 사고다.

그래서 `--apply` 는 (1) 메모리 상에서 치환하고 (2) 치환 전후로
`_aggregate_from_appendonly_layout` 를 돌려 대조한 뒤 (3) 같을 때만 디스크에
쓴다. 다르면 **아무것도 쓰지 않고** 무엇이 달라졌는지 보고한다.

## 범위

`active/` 아래 **모든 브랜치**의 `backlog/tasks/*.md`. `archived/` 는 뺀다 —
어떤 집계도 그것을 읽지 않으므로(state 생성기·dashboard 모두 `active/` 만
훑는다) 고쳐도 얻는 것이 없고, 동결된 이력을 표기 때문에 다시 쓰는 것은
churn 이다.

## 멱등성

이미 정본 표기인 줄은 매칭되지 않는다. 두 번 돌려도 두 번째는 0건이다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workflow_kit.common.paths import memory_active_dir  # noqa: E402
from workflow_kit.common.project_docs import (  # noqa: E402
    TASK_FIELD_ALIASES,
    TASK_FIELD_LABELS,
)


def legacy_label_map() -> dict[str, str]:
    """옛 표기 → 정본 표기. **레지스트리에서 파생한다** (손 목록을 만들지 않는다)."""
    mapping: dict[str, str] = {}
    for key, aliases in TASK_FIELD_ALIASES.items():
        canonical = TASK_FIELD_LABELS[key]
        for alias in aliases:
            if alias != canonical:
                mapping[alias] = canonical
    return mapping


def migrate_text(text: str, mapping: dict[str, str]) -> tuple[str, int]:
    """한 파일의 본문 라벨을 정본으로. `(바뀐 내용, 바뀐 줄 수)`.

    **줄머리에 앵커한다** (`^- <라벨>:`). 앵커 없이 치환하면 같은 문자열을
    *본문에서 언급*하는 산문까지 바뀐다 — 이 저장소의 task 파일은 자기 라벨을
    산문으로 인용하는 일이 잦다.

    긴 라벨부터 적용한다. 짧은 라벨이 긴 라벨의 접두사인 경우(`호스트명` /
    `호스트 IP`)를 먼저 먹지 않게 한다.
    """
    changed = 0
    for alias in sorted(mapping, key=len, reverse=True):
        pattern = re.compile(rf"^- {re.escape(alias)}:", re.M)
        text, hits = pattern.subn(f"- {mapping[alias]}:", text)
        changed += hits
    return text, changed


def _aggregate(branch_dir: Path) -> dict[str, object]:
    from workflow_kit.common.state.builder import (  # noqa: PLC0415
        _aggregate_from_appendonly_layout,
    )

    return _aggregate_from_appendonly_layout(
        daily_backlog_dir=branch_dir / "backlog",
        tasks_dir=branch_dir / "backlog" / "tasks",
        sessions_dir=branch_dir / "sessions",
    )


def _branch_dirs(active_dir: Path) -> list[Path]:
    """`active/` 아래 `backlog/tasks/` 를 가진 브랜치 디렉터리들."""
    return sorted({p.parent.parent for p in active_dir.rglob("backlog/tasks")})


def run(*, active_dir: Path, apply: bool) -> dict[str, object]:
    mapping = legacy_label_map()
    branches: list[dict[str, object]] = []
    total_files = total_changed = total_lines = 0
    blocked: list[str] = []

    for branch_dir in _branch_dirs(active_dir):
        tasks_dir = branch_dir / "backlog" / "tasks"
        pending: dict[Path, str] = {}
        files = sorted(tasks_dir.glob("TASK-*.md"))
        lines_changed = 0
        for path in files:
            try:
                original = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            migrated, hits = migrate_text(original, mapping)
            if hits:
                pending[path] = migrated
                lines_changed += hits

        record: dict[str, object] = {
            "branch_dir": str(branch_dir),
            "files_scanned": len(files),
            "files_to_change": len(pending),
            "lines_to_change": lines_changed,
        }
        total_files += len(files)
        total_changed += len(pending)
        total_lines += lines_changed

        if pending and apply:
            # **파싱 동일성 잠금장치.** 쓰기 전에 재고, 달라지면 안 쓴다.
            before = _aggregate(branch_dir)
            backup = {p: p.read_text(encoding="utf-8") for p in pending}
            for path, content in pending.items():
                path.write_text(content, encoding="utf-8")
            after = _aggregate(branch_dir)
            if before != after:
                for path, content in backup.items():
                    path.write_text(content, encoding="utf-8")
                differing = [k for k in before if before[k] != after.get(k)]
                record["applied"] = False
                record["blocked_reason"] = (
                    f"파서 출력이 달라져 되돌렸다 — 다른 키: {differing}"
                )
                blocked.append(str(branch_dir))
            else:
                record["applied"] = True
        else:
            record["applied"] = False
        branches.append(record)

    return {
        "status": "blocked" if blocked else "ok",
        "mode": "apply" if apply else "dry-run",
        "active_dir": str(active_dir),
        "label_mappings": len(mapping),
        "files_scanned": total_files,
        "files_to_change": total_changed,
        "lines_to_change": total_lines,
        "branches": branches,
        "blocked": blocked,
        "note": (
            "archived/ 는 범위 밖이다 — 어떤 집계도 읽지 않으므로 고쳐도 얻는 것이 "
            "없고, 동결된 이력을 표기 때문에 다시 쓰는 것은 churn 이다."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="migrate-task-labels",
        description="task 본문 라벨을 정본 표기로 통일한다 (dry-run 기본).",
    )
    parser.add_argument("--active-dir", default=None)
    parser.add_argument("--apply", action="store_true", help="실제로 쓴다 (기본: dry-run)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    active_dir = (
        Path(args.active_dir) if args.active_dir else memory_active_dir(REPO_ROOT)
    )
    if not active_dir.is_dir():
        print(f"active 메모리 디렉터리가 없다: {active_dir}", file=sys.stderr)
        return 1

    result = run(active_dir=active_dir, apply=args.apply)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[{result['mode']}] {result['active_dir']}")
        print(f"  라벨 매핑    : {result['label_mappings']}")
        print(f"  훑은 파일    : {result['files_scanned']}")
        print(f"  바뀔 파일    : {result['files_to_change']}")
        print(f"  바뀔 줄      : {result['lines_to_change']}")
        for record in result["branches"]:
            if record["files_to_change"]:
                state = "적용" if record.get("applied") else "계획"
                print(
                    f"  - {state}: {record['branch_dir']} "
                    f"({record['files_to_change']}파일 / {record['lines_to_change']}줄)"
                )
                if record.get("blocked_reason"):
                    print(f"      ! {record['blocked_reason']}")
        print(f"  {result['note']}")
    return 1 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
