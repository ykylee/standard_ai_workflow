#!/usr/bin/env python3
"""검사가 *무엇을 강제하는지* 선언하게 하고, 그 선언이 사실인지 대조한다.

TASK-2026-09-21-main-003 (OpenSpec concept 흡수 — 도구는 채택하지 않았다).

**왜 필요한가** (2026-09-21 실측). 검사들은 이미 정본 스펙의 절을 인용하고 있었다 —
`§ 인용 671건 / 127개 파일` (`WATCHES` 상용구 204건 제외). 그런데 그중 기계가 *어느
문서* 인지 특정할 수 있는 형태(`` `경로` §N ``)는 **10건** 뿐이었다. 나머지 661건은
링크가 아니라 **산문**이다 — 절 번호가 바뀌어도, 절이 통째로 사라져도 조용하다.

그래서 산문 인용을 파싱해 고치는 방향은 기각했다. *파싱이 안 되는 것* 이 문제의
본체이므로, 파서를 더 똑똑하게 만드는 것은 추측을 늘릴 뿐이다. 대신 **선언 축을
새로 세우고 선언만 대조한다** — goal coverage 를 어휘 겹침에서 선언 사슬로 옮긴 것과
같은 수법이다 (TASK-2026-09-21-main-001).

**두 선언의 축이 다르다**:

- `WATCHES` — "무엇이 바뀌면 나를 돌려라" (입력 표면, ADR-028)
- `ENFORCES` — "내가 어떤 정본 요구를 지킨다" (강제 대상, 이 검사)

**전수 이행을 게이트로 강제하지 않는다.** 127개 파일을 한 세션에 옮기면 선언의
품질이 아니라 선언의 개수만 는다. 미선언 수는 meta-watch 의 `미분류 68` 과 같은
**관찰 지표**로 보고만 한다.
"""
from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/core/*.md",
    "workflow-source/tests/*.py",
)

#: 이 검사가 강제하는 정본 요구 — 자기 자신에게도 규약을 적용한다.
ENFORCES = ("check-enforces-declaration-must-resolve",)

import ast
import re
import sys
import warnings
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
CORE_DIR = SOURCE_ROOT / "core"
TESTS_DIR = SOURCE_ROOT / "tests"

#: 정본 스펙의 요구 헤딩. 절 번호가 아니라 **이름**이다 — 절은 재배치되지만
#: 요구는 이름을 유지한다.
#:
#: id 를 **느슨하게** 잡는 것이 의도다. kebab-case 만 인식하게 좁히면 형식 위반이
#: red 가 아니라 *침묵* 이 된다 — 요구가 그냥 없는 것이 되고, 그것을 ENFORCES 한
#: 검사를 case 1 이 대신 탓한다. 원인을 엉뚱한 층에 돌리는 판정이다
#: (되주입 4에서 실측: 형식 위반 주입이 4/4 PASS 로 통과했다). 형식은 case 3 이 잰다.
REQUIREMENT_HEADING = re.compile(r"^#{2,4}\s*Requirement:\s*(?P<id>\S+)\s*$", re.MULTILINE)

#: id 형식 — kebab-case. 대문자/밑줄/공백을 섞으면 같은 요구가 두 이름을 갖는다.
REQUIREMENT_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    if ok:
        _passes.append(case)
        print(f"  {case}: PASS{(' — ' + detail) if detail else ''}")
    else:
        _failures.append(f"{case}: {detail}")
        print(f"  {case}: FAIL — {detail}")


def _strip_code_fences(text: str) -> str:
    """``` 펜스 안을 지운다.

    펜스 안의 `### Requirement: <id>` 는 **형식 예시**지 선언이 아니다. 구분하지
    않으면 스펙이 자기 형식을 설명하는 것만으로 중복 선언이 된다 — 규약을 설명하는
    메타 문서에 위양성을 내는, 이 저장소가 이미 이름 붙인 결함 유형이다.
    """
    out, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        out.append("" if fenced else line)
    return "\n".join(out)


def declared_requirements() -> dict[str, list[Path]]:
    """core 스펙이 선언한 요구 id → 선언한 파일들 (중복 검출을 위해 목록)."""
    found: dict[str, list[Path]] = {}
    for path in sorted(CORE_DIR.glob("*.md")):
        body = _strip_code_fences(path.read_text(encoding="utf-8"))
        for m in REQUIREMENT_HEADING.finditer(body):
            found.setdefault(m.group("id"), []).append(path)
    return found


def enforces_by_check() -> dict[Path, tuple[str, ...]]:
    """검사 파일 → 그 파일이 선언한 ENFORCES 튜플.

    **import 하지 않고 AST 로 읽는다.** 검사를 import 하면 그 검사의 부작용이
    이 검사 안에서 돌아간다 — 저장소를 건드리는 검사가 실제로 있었다
    (smoke 저장소 오염 postmortem).
    """
    out: dict[Path, tuple[str, ...]] = {}
    for path in sorted(TESTS_DIR.glob("check_*.py")):
        try:
            with warnings.catch_warnings():
                # 다른 검사 파일이 이미 가진 SyntaxWarning(예: `\\``)은 이 판정의
                # 대상이 아니다. 여기서 재방출하면 남의 경고가 내 출력으로 보인다.
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:  # 문법이 깨진 검사는 이 판정의 대상이 아니다
            _record("parse", False, f"{path.name}: {exc}")
            continue
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "ENFORCES" not in names:
                continue
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                _record("literal", False, f"{path.name}: ENFORCES 가 리터럴이 아니다")
                continue
            if isinstance(value, str):
                value = (value,)
            out[path] = tuple(str(v) for v in value)
    return out


def test_enforces_declarations_resolve() -> None:
    """case 1: 모든 ENFORCES id 가 core 스펙에 **실재**한다.

    끊긴 선언은 조용한 0 이 아니라 red 다 — goal coverage 의 `goal_dangling_link`
    와 같은 규율. 선언이 허공을 가리키면 "이 검사가 무엇을 지키는가" 의 답이
    거짓이 되고, 거짓인 선언은 없는 선언보다 나쁘다.
    """
    declared = declared_requirements()
    dangling: list[str] = []
    total = 0
    for path, ids in enforces_by_check().items():
        for rid in ids:
            total += 1
            if rid not in declared:
                dangling.append(f"{path.name} → {rid!r}")
    _record(
        "case 1 (ENFORCES 가 실재 요구를 가리킨다)",
        not dangling,
        "; ".join(dangling) if dangling else f"{total}건 전부 해결",
    )


def test_requirement_ids_are_unique() -> None:
    """case 2: 요구 id 가 스펙 전체에서 유일하다.

    두 스펙이 같은 id 를 쓰면 정본이 둘이 된다 — 이 저장소가 가장 자주 만난
    결함 유형이고(`규약은 단일 출처로`), 복제는 반드시 갈라진다.
    """
    dupes = {rid: [p.name for p in paths] for rid, paths in declared_requirements().items() if len(paths) > 1}
    _record(
        "case 2 (요구 id 유일)",
        not dupes,
        "; ".join(f"{rid}: {files}" for rid, files in dupes.items()) if dupes else "중복 0",
    )


def test_requirement_ids_are_kebab_case() -> None:
    """case 3: id 형식이 kebab-case 다.

    형식을 안 고정하면 같은 요구가 `goalCoverage` / `goal_coverage` /
    `goal-coverage` 세 이름을 갖고, 대조는 셋 다 놓친다.
    """
    bad = [rid for rid in declared_requirements() if not REQUIREMENT_ID_RE.match(rid)]
    _record("case 3 (id 형식 kebab-case)", not bad, f"위반: {bad}" if bad else "형식 위반 0")


def test_adoption_is_reported_not_gated() -> None:
    """case 4: 이행 현황을 **보고**한다 (게이트 아님).

    전수 이행을 게이트로 강제하면 선언의 품질이 아니라 개수만 는다. 미선언 수는
    관찰 지표로 남긴다 — meta-watch 의 `미분류 68` 과 같은 자리다.

    판정하는 것은 하나뿐이다: **시범 대상이 0 이 되면 안 된다.** 0 이면 위 세
    case 가 빈 집합을 검사하며 통과한다 — 검사는 깨지지 않고 무력화된다.
    """
    enforcing = enforces_by_check()
    all_checks = list(TESTS_DIR.glob("check_*.py"))
    declared = declared_requirements()
    print(
        f"  [report] 요구 선언 {len(declared)}건 · ENFORCES 선언 검사 "
        f"{len(enforcing)}/{len(all_checks)}개 (미선언 {len(all_checks) - len(enforcing)} — 관찰 지표)"
    )
    _record(
        "case 4 (시범 대상 비어 있지 않음)",
        bool(enforcing) and bool(declared),
        f"ENFORCES {len(enforcing)}개 / 요구 {len(declared)}건"
        if enforcing and declared
        else "선언이 0 이면 case 1~3 이 빈 집합을 검사하며 통과한다",
    )


def main() -> int:
    print("=== requirement 선언 대조 (TASK-2026-09-21-main-003) ===")
    for fn in (
        test_enforces_declarations_resolve,
        test_requirement_ids_are_unique,
        test_requirement_ids_are_kebab_case,
        test_adoption_is_reported_not_gated,
    ):
        fn()
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
