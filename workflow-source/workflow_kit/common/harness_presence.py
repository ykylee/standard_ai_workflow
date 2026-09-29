"""프로젝트에 **어느 하네스가 적용됐는가** — 판정 정본 (TASK-2026-09-29-main-004).

`wk ensure-entrypoints`(세션 시작의 자기 복구)와 `wk doctor` 의 `project_scope` 가
같은 질문을 따로 답하고 있었다. 둘 다 "선언 파일 중 하나라도 kit 버전 마커가
있으면 적용" 이었는데, 선언 파일에는 **여러 하네스가 함께 선언한 공유 파일**
(`AGENTS.md` — codex · opencode · pi-dev)이 있다. codex 가 쓴 `AGENTS.md` 의 마커
하나가 opencode 까지 적용됨으로 만들었고, 세션 시작은 요청하지 않은 opencode
오버레이 7개를 "부재 진입점" 으로 생성했다 (v1.14.1 발행 wheel 격리 실측).

## 규칙

- **고유 파일**(다른 하네스가 선언하지 않은 파일)에 마커가 있으면 적용이다. 확장자상
  마커를 **달 수 없는** 고유 파일(`.codex/config.toml.example`, `opencode.json` 등)은
  존재가 유일한 증거라 존재로 센다 — codex 는 고유 파일이 이것 하나뿐이다.
- **공유 파일**의 마커는 고유 파일로 적용이 확인된 하네스의 몫이다. 그 파일을
  선언한 하네스 중 아무도 고유 파일로 확인되지 않았을 때만, 고유 파일이 **없는**
  하네스(pi-dev)를 적용으로 본다 — 그 하네스는 공유 파일 말고는 증거를 낼 수 없다.
- 파일은 있는데 적용이 아닌 하네스는 `candidates` 로 따로 낸다 — 숨기지 않는다.

한계: codex 와 pi-dev 를 함께 적용한 프로젝트에서 pi-dev 는 파일로 구별되지 않아
후보로 남는다. pi-dev 의 선언은 `AGENTS.md` 하나라 복구할 것도 없다.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from workflow_kit.bootstrap_lib.harnesses import HARNESS_SPECS
from workflow_kit.upgrade_diff import parse_version_marker, suffix_marker_supported


def declared_relpaths() -> dict[str, tuple[str, ...]]:
    """하네스별 선언 파일 (registry 에서 파생 — 손 목록을 두지 않는다)."""
    return {
        name: (*spec.entry_files, *spec.extra_files)
        for name, spec in HARNESS_SPECS.items()
    }


def shared_relpaths() -> frozenset[str]:
    """두 개 이상의 하네스가 선언한 파일."""
    counts = Counter(rel for rels in declared_relpaths().values() for rel in rels)
    return frozenset(rel for rel, n in counts.items() if n > 1)


def _has_marker(path: Path) -> bool:
    try:
        return parse_version_marker(path.read_text(encoding="utf-8")) is not None
    except (OSError, UnicodeDecodeError):
        return False


def _is_evidence(path: Path) -> bool:
    """고유 파일이 적용의 증거인가 — 마커가 있거나, 마커를 달 수 없는 파일이 있다."""
    if not path.is_file():
        return False
    if not suffix_marker_supported(path.suffix):
        return True
    return _has_marker(path)


def detect_harnesses(project_root: Path) -> tuple[list[str], list[str]]:
    """``(적용된 하네스, 후보 하네스)`` — 둘 다 이름순."""
    declared = declared_relpaths()
    shared = shared_relpaths()

    present: dict[str, list[str]] = {}
    marked: set[str] = set()
    for rels in declared.values():
        for rel in rels:
            path = project_root / rel
            if path.is_file():
                if _has_marker(path):
                    marked.add(rel)
    for name, rels in declared.items():
        found = [rel for rel in rels if (project_root / rel).is_file()]
        if found:
            present[name] = found

    applied = {
        name for name, rels in declared.items()
        if any(rel not in shared and _is_evidence(project_root / rel) for rel in rels)
    }
    for rel in shared & marked:
        claimants = [name for name, rels in declared.items() if rel in rels]
        if any(name in applied for name in claimants):
            continue
        applied.update(
            name for name in claimants
            if all(r in shared for r in declared[name])
        )

    candidates = sorted(name for name in present if name not in applied)
    return sorted(applied), candidates
