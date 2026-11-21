#!/usr/bin/env python3
"""2.0 사전 판 번호 · GitHub 'latest' 판정 (TASK-2026-11-21-main-026 · 요구 R16.7 · 소유자 2026-11-21).

소유자 결정: 2.0 첫 판은 PEP 440 ``2.0.0b1`` (pyproject · ``__version__`` · wheel · 태그가 같은 문자열), 베타도
가장 높은 판이면 latest, 2.x 가 나온 뒤의 1.x 판은 ``--latest=false``.

1. 정렬 — 사전 판 < 정식 판, 옛 ``-beta`` 태그 · 읽을 수 없는 태그(``beta-v1``) 처리, 태그 정렬과 CHANGELOG 정렬이 같은 순서
2. 사전 판 판정 — ``2.0.0b1`` · ``v1.0.0-beta`` 는 사전 판, ``1.30.0`` · ``2.0.0`` 은 아님
3. latest 판정 — 2.0.0b1(원격 최고 1.29.1) latest · 그 뒤 1.30.0 · 1.30.1 은 아님 · 2.0.0 은 latest
4. 발행 명령 — ``gh release create`` 인자에 latest 판정이 들어가고 ``--target`` 이 main 고정이 아니다
5. 산출물 이름 — ``2.0.0b1`` 의 wheel · sdist 파일명이 판 문자열 그대로 (PEP 440 정규화가 바꾸지 않는다)
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 120

WATCHES = (
    "workflow-source/workflow_kit/*",  # release_pipeline 이 kit 전체를 import 한다
    "workflow-source/pyproject.toml",
)

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.tools import release_pipeline as rp  # noqa: E402
from workflow_kit.tools.release_pipeline_changelog import _changelog_version_sort_key  # noqa: E402
from workflow_kit.tools.release_pipeline_dist import _expected_dist_pattern  # noqa: E402

_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail and not ok else ''}")


def main() -> int:
    print("check_release_prerelease_latest")
    want = ["v0.7.17-beta", "v0.7.17", "v1.0.0-beta", "v1.0.0", "v1.29.1", "v1.30.0", "v2.0.0b1", "v2.0.0b2",
            "v2.0.0rc1", "v2.0.0", "v2.0.1", "v2.1.0"]
    shuffled = list(reversed(want[::2])) + list(want[1::2])
    got = sorted(shuffled, key=rp._version_sort_key)
    cl = sorted([w.lstrip("v") for w in shuffled], key=_changelog_version_sort_key)
    bad_tag_first = sorted(["v1.0.0", "beta-v1"], key=rp._version_sort_key)[0] == "beta-v1"
    _record("case 1 (정렬 — 사전 판 < 정식 판 · 옛 -beta · 태그 = CHANGELOG 순서 · 못 읽는 태그는 맨 앞)",
            got == want and cl == [w.lstrip("v") for w in want] and bad_tag_first, f"tag={got} changelog={cl}")

    pre = {v: rp.is_prerelease(v) for v in ("2.0.0b1", "v1.0.0-beta", "2.0.0rc1", "1.30.0", "2.0.0", "v1.29.1")}
    _record("case 2 (사전 판 판정)", pre == {"2.0.0b1": True, "v1.0.0-beta": True, "2.0.0rc1": True, "1.30.0": False,
                                       "2.0.0": False, "v1.29.1": False}, str(pre))

    d = rp.release_latest_decision
    table = {
        "2.0.0b1 첫 발행": (d("v2.0.0b1", ["v1.29.0", "v1.29.1", "beta-v1"])["latest"], True),
        "같이 내는 1.30.0": (d("v1.30.0", ["v1.29.1", "v2.0.0b1"])["latest"], False),
        "뒤의 1.x patch": (d("v1.30.1", ["v1.30.0", "v2.0.0b1"])["latest"], False),
        "2.0.0 정식": (d("v2.0.0", ["v2.0.0b1", "v1.30.0"])["latest"], True),
        "2.x 없을 때 1.x": (d("v1.29.2", ["v1.29.1"])["latest"], True),
    }
    wrong = {k: v for k, v in table.items() if v[0] != v[1]}
    _record("case 3 (latest 판정 — 원격 최고일 때만)", not wrong, str(wrong))

    src = (SOURCE_ROOT / "workflow_kit" / "tools" / "release_pipeline.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    gh_lists = [n for n in ast.walk(tree) if isinstance(n, ast.List) and n.elts
                and isinstance(n.elts[0], ast.Constant) and n.elts[0].value == "gh"
                and len(n.elts) > 2 and getattr(n.elts[2], "value", None) == "create"]
    seg = ast.get_source_segment(src, gh_lists[0]) if gh_lists else ""
    problems4 = []
    if len(gh_lists) != 1:
        problems4.append(f"gh release create 목록 {len(gh_lists)}개")
    if '"--latest" if latest["latest"] else "--latest=false"' not in seg:
        problems4.append("latest 판정 인자 없음")
    if '"--target", "main"' in seg:
        problems4.append("--target main 고정")
    if "release_latest_decision(" not in src:
        problems4.append("latest 판정을 부르지 않는다")
    _record("case 4 (발행 명령 — latest 인자 · target 고정 아님)", not problems4, "; ".join(problems4))

    _record("case 5 (산출물 이름 — 2.0.0b1 은 그대로)", _expected_dist_pattern("2.0.0b1") == "2.0.0b1",
            _expected_dist_pattern("2.0.0b1"))

    print(f"PASS {len(_passes)} · FAIL {len(_failures)}")
    for f in _failures:
        print(f"  FAIL {f}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
