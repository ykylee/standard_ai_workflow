#!/usr/bin/env python3
"""상대 경로 문자열은 호스트와 무관하게 POSIX 형태다 (TASK-2026-09-29-main-018).

주장:
1. **`wk doctor` 사본 대조는 Windows 에서도 하위 디렉터리 파일을 '미등록' 으로 부르지 않는다** —
   정본 키(`skills/a/SKILL.md`)와 비교하는 쪽이 `str(relative_to)` 면 역슬래시라 전부 extra 가 된다.
2. **커밋되거나 호스트를 건너는 산출물의 경로는 슬래시다** — wiki L2 stub 의 L1 SSOT 줄,
   OKF 번들의 page 상대 경로.
3. **정적 가드**: 위 사이트를 둔 모듈에 `str(x.relative_to(...))` 가 다시 들어오지 않는다.

Windows 는 `relative_to` 가 `PureWindowsPath` 를 돌려주게 바꿔 흉내 낸다 —
`str()` 은 역슬래시를, `as_posix()` 만 슬래시를 낸다.
"""
from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import re
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path, PureWindowsPath
from typing import Iterator
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

FAILURES: list[str] = []

#: `str(relative_to)` 를 걷어 낸 모듈 — 결과가 비교·커밋·교환되는 곳.
GUARDED_MODULES = (
    "workflow_kit/common/state/roadmap.py",
    "workflow_kit/deploy_doctor.py",
    "workflow_kit/plugin_payload.py",
    "workflow_kit/okf_export.py",
    "workflow_kit/okf_import.py",
    "workflow_kit/tools/refresh_wiki_memory.py",
)
STR_RELATIVE_TO = re.compile(r"str\([\w.]+\.relative_to\(")


def _record(case: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS: {case}")
    else:
        print(f"FAIL: {case} — {detail}")
        FAILURES.append(case)


@contextmanager
def _windows_relative_to() -> Iterator[None]:
    host_path = type(Path())
    original = host_path.relative_to

    def fake(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        return PureWindowsPath(*original(self, *args, **kwargs).parts)

    with mock.patch.object(host_path, "relative_to", fake):
        yield


def test_doctor_cache_compare_nested_file_is_known() -> None:
    from workflow_kit.deploy_doctor import _compare_cache

    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        canonical = {"skills/session-start/SKILL.md": "body\n"}
        target = root / "skills" / "session-start" / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text("body\n", encoding="utf-8")
        with _windows_relative_to():
            report = _compare_cache(root, canonical, ())
        if report.get("extra"):
            problems.append(f"정본에 있는 파일이 extra 로 잡혔다: {report['extra']}")
        if report.get("differs") or report.get("missing"):
            problems.append(f"differs/missing 이 비어야 한다: {report.get('differs')} {report.get('missing')}")
    _record("test_doctor_cache_compare_nested_file_is_known", not problems, "; ".join(problems))


def test_wiki_l1_ssot_path_is_posix() -> None:
    from workflow_kit.tools import refresh_wiki_memory as rwm

    with _windows_relative_to():
        rel = rwm._rel_to_repo(rwm.REPO_ROOT / "ai-workflow" / "memory" / "state.json")
    ok = rel == "ai-workflow/memory/state.json"
    _record("test_wiki_l1_ssot_path_is_posix", ok, f"got {rel!r}")


def test_okf_import_relative_path_is_posix() -> None:
    from workflow_kit.okf_import import _parse_bundle_pages

    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        bundle = Path(tmp)
        page = bundle / "concepts" / "foo.md"
        page.parent.mkdir()
        page.write_text("---\ntype: concept\ntitle: Foo\n---\n\n# Foo\n", encoding="utf-8")
        with _windows_relative_to():
            pages = _parse_bundle_pages(bundle)
        if not pages:
            problems.append("fixture page 가 파싱되지 않았다 — 측정 불가")
        problems.extend(f"역슬래시 경로: {p.relative_path}" for p in pages if p.relative_path != "concepts/foo.md")
    _record("test_okf_import_relative_path_is_posix", not problems, "; ".join(problems))


def test_guarded_modules_have_no_str_relative_to() -> None:
    hits: list[str] = []
    for rel in GUARDED_MODULES:
        text = (SOURCE_ROOT / rel).read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            if STR_RELATIVE_TO.search(line):
                hits.append(f"{rel}:{lineno}")
    _record("test_guarded_modules_have_no_str_relative_to", not hits, ", ".join(hits))


def main() -> int:
    cases = [
        test_doctor_cache_compare_nested_file_is_known,
        test_wiki_l1_ssot_path_is_posix,
        test_okf_import_relative_path_is_posix,
        test_guarded_modules_have_no_str_relative_to,
    ]
    for case in cases:
        case()
    total = len(cases)
    print(f"\n{total - len(FAILURES)}/{total} passed")
    if FAILURES:
        raise AssertionError(f"{len(FAILURES)} case(s) failed: {FAILURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
