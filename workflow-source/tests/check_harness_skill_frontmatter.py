"""bootstrap 이 내보내는 harness skill/agent 의 YAML frontmatter 검사 (v1.0.3+).

## 왜 필요한가

`scripts/bootstrap_lib/harnesses/renderers.py` 는 harness 별 skill/agent 파일을
**Python 문자열 리터럴** 로 생성한다. 그 안에 YAML frontmatter 가 들어 있는데,
파일로 나가기 전까지 파서를 한 번도 통과하지 않는다. 예를 들어
`render_grok_build_skill` 의 `description` 은 따옴표 없는 plain scalar 인데 백틱과
슬래시를 포함한다 — 지금은 유효하지만, 누가 거기에 `: `(콜론+공백) 하나만 넣으면
조용히 깨지고 **그걸 잡을 것이 아무것도 없다.**

조사해 보니 `skill-lint`(npm) 가 정확히 이 규칙들을 검사한다. 다만 이 저장소는
Node 툴체인이 없고, 그 도구는 **디스크의 `SKILL.md` 디렉터리** 를 대상으로 한다.
여기서 검사해야 할 것은 *생성기 안의 리터럴* 이므로, 같은 규칙을 Python 으로 둔다.
(서버를 띄워야만 알 수 있는 층은 별도 워크플로우가 담당한다 — C안.)

> 주의: `workflow-source/skills/*/SKILL.md` 14개는 이 검사 대상이 **아니다.**
> 그것들은 frontmatter 없이 마크다운 불릿 헤더 규약을 쓰는 내부 명세 문서다.
> skill-lint 를 그대로 돌리면 14개 전부 "Invalid frontmatter" 로 잡힌다 — 도구가
> 틀린 게 아니라 대상이 다르다.

## 검사 규칙 (skill-lint 정합)

1. frontmatter 가 `---` 로 열고 닫히며 **유효한 YAML 매핑** 인가
2. `name` — 1–64자, 소문자 `[a-z0-9-]`, 하이픈이 양끝/연속으로 오지 않음
3. `description` — 필수, 1–1024자
4. harness 스키마 — opencode agent 는 `mode ∈ {primary, subagent}`,
   `permission.<key> ∈ {allow, deny, ask}`
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RENDERERS = REPO_ROOT / "workflow-source" / "scripts" / "bootstrap_lib" / "harnesses" / "renderers.py"

NAME_RE = re.compile(r"^(?!-)(?!.*--)[a-z0-9-]{1,64}(?<!-)$")
MODE_VALUES = {"primary", "subagent"}
PERMISSION_VALUES = {"allow", "deny", "ask"}


def _frontmatter_blocks() -> list[tuple[str, str]]:
    """(렌더 함수명, frontmatter 본문) 목록.

    렌더 함수는 args/context 를 요구하므로 호출하지 않고, 반환 문자열 리터럴에서
    맨 앞 `---` 블록만 뽑는다. frontmatter 자체는 전부 정적이라 보간이 없다
    (그 사실도 case 0 에서 함께 확인한다).
    """
    src = RENDERERS.read_text(encoding="utf-8")
    tree = ast.parse(src)
    out: list[tuple[str, str]] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        seg = ast.get_source_segment(src, node) or ""
        m = re.search(r'"""---\n(.*?)\n---\n', seg, re.DOTALL)
        if m:
            out.append((node.name, m.group(1)))
    return out


def _yaml():
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        print("  FAIL: PyYAML 부재 — dev extra 에 선언돼 있어야 한다")
        return None
    return yaml


def test_blocks_found() -> bool:
    """0) 검사 대상을 실제로 찾았는가 + frontmatter 에 보간이 없는가.

    이 case 가 없으면 렌더러 구조가 바뀌었을 때 "대상 0건 → 전부 통과"로
    조용히 무력화된다.
    """
    if not RENDERERS.is_file():
        print(f"  FAIL: {RENDERERS.relative_to(REPO_ROOT)} 부재")
        return False
    blocks = _frontmatter_blocks()
    if len(blocks) < 5:
        print(f"  FAIL: frontmatter 블록 {len(blocks)}개 — 렌더러 구조 변경 의심 "
              "(추출 정규식이 더 이상 맞지 않을 수 있다)")
        return False
    ok = True
    for name, fm in blocks:
        holes = re.findall(r"\{[^{}]+\}", fm)
        if holes:
            print(f"  FAIL: {name} — frontmatter 에 값 보간 {holes} "
                  "(보간값이 `: `/줄바꿈을 담으면 YAML 이 조용히 깨진다; "
                  "따옴표로 감싸거나 본문으로 옮길 것)")
            ok = False
    if ok:
        print(f"  PASS: frontmatter {len(blocks)}개 추출, 보간 0건")
    return ok


def test_frontmatter_parses() -> bool:
    """1) 유효한 YAML 매핑인가."""
    yaml = _yaml()
    if yaml is None:
        return False
    ok = True
    for name, fm in _frontmatter_blocks():
        try:
            d = yaml.safe_load(fm)
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL: {name} — {type(e).__name__}: {str(e)[:100]}")
            ok = False
            continue
        if not isinstance(d, dict):
            print(f"  FAIL: {name} — frontmatter 가 매핑이 아니다 ({type(d).__name__})")
            ok = False
    if ok:
        print("  PASS: frontmatter 전부 유효한 YAML 매핑")
    return ok


def _parsed() -> list[tuple[str, dict]]:
    yaml = _yaml()
    if yaml is None:
        return []
    out = []
    for name, fm in _frontmatter_blocks():
        try:
            d = yaml.safe_load(fm)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(d, dict):
            out.append((name, d))
    return out


def test_name_and_description() -> bool:
    """2·3) `name` 형식과 `description` 길이 (skill-lint 규칙)."""
    ok = True
    for fn, d in _parsed():
        if "name" in d:
            name = d["name"]
            if not isinstance(name, str) or not NAME_RE.match(name):
                print(f"  FAIL: {fn} — `name` 형식 위반 {name!r} "
                      "(1–64자 소문자 [a-z0-9-], 하이픈 양끝/연속 불가)")
                ok = False
        desc = d.get("description")
        if desc is None:
            print(f"  FAIL: {fn} — `description` 부재")
            ok = False
        elif not isinstance(desc, str) or not (1 <= len(desc) <= 1024):
            n = len(desc) if isinstance(desc, str) else "N/A"
            print(f"  FAIL: {fn} — `description` 길이 위반 ({n}자, 1–1024 이어야 한다)")
            ok = False
    if ok:
        print("  PASS: name 형식 + description 길이 정합")
    return ok


def test_harness_schema() -> bool:
    """4) harness 별 enum — opencode agent 의 `mode` / `permission`."""
    ok = True
    for fn, d in _parsed():
        if "mode" in d and d["mode"] not in MODE_VALUES:
            print(f"  FAIL: {fn} — `mode` = {d['mode']!r} (허용: {sorted(MODE_VALUES)})")
            ok = False
        perm = d.get("permission")
        if perm is not None:
            if not isinstance(perm, dict):
                print(f"  FAIL: {fn} — `permission` 이 매핑이 아니다")
                ok = False
                continue
            for k, v in perm.items():
                if v not in PERMISSION_VALUES:
                    print(f"  FAIL: {fn} — `permission.{k}` = {v!r} "
                          f"(허용: {sorted(PERMISSION_VALUES)})")
                    ok = False
    if ok:
        print("  PASS: harness 스키마(mode / permission) 정합")
    return ok


def main() -> int:
    cases = [
        ("test_blocks_found", test_blocks_found),
        ("test_frontmatter_parses", test_frontmatter_parses),
        ("test_name_and_description", test_name_and_description),
        ("test_harness_schema", test_harness_schema),
    ]
    results = []
    for name, fn in cases:
        print(f"\n[{name}]")
        results.append((name, fn()))
    passed = sum(1 for _, ok in results if ok)
    print()
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== {passed}/{len(cases)} PASS ===")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
