"""저장소의 YAML 표면을 **진짜 파서**로 검사한다 (v1.0.3+).

## 왜 필요한가

이 저장소에서 YAML 을 읽는 유일한 코드는 `check_mypy_strict_ci_v0_11_11.py` 의
`_read_yaml_simple` / `_read_yaml_text_based` 라는 **자체 정규식 파서**였다.
PyYAML 이 있으면 그것을 쓰고, 없으면 정규식 fallback 으로 내려간다 — 그런데 그
fallback 안에 결함이 있었다:

    fallback_pattern = re.compile(r"mypy[^\\n]*--no-incremental[^\\n]*workflow_kit/")

raw string 이라 문자 클래스가 `[^\n]`(줄바꿈 제외)이 아니라 **`[^\\n]`(역슬래시와
문자 `n` 제외)** 로 해석된다. 여러 줄 invocation 을 허용하려던 의도가 전혀 동작하지
않았고, 아무도 몰랐다. **파서를 직접 쓰면 갈라진다.**

게다가 fallback 은 PyYAML 이 없을 때만 도는데, 그 조건이 곧 CI 였다 — `pyyaml` 은
dev extra 에 선언돼 있지 않았다. 즉 *CI 에서는 항상 결함 있는 경로*로 돌았다.

## 이 file 이 보는 것

1. 구문 — 모든 `.yml`/`.yaml` 이 PyYAML 로 파싱되는가
2. 스키마 — GitHub Actions 워크플로우가 `name`/`on`/`jobs` 를 갖추고, 각 job 이
   `runs-on` 과 `steps` 를 갖는가
3. 파서 단일 출처 — **자체 YAML 파서를 새로 만들지 않았는가** (원래 결함의 재발 방지)
4. 셸 안전 — `run:` 블록이 errexit 이 켜진 채 `$?` 를 직접 읽지 않는가
   (§2.27 사고: 러너가 non-zero 로 끝나는 순간 다음 줄 `rc=$?` 에 닿기도 전에
   스텝이 중단돼, 실패 요약 블록이 한 번도 실행되지 않았다.)

   > **이 case 가 그 부류의 유일한 방어선이다.** 도입 검토 중 actionlint 로 같은
   > 모양을 재현해 돌려 봤는데 **exit 0** 이었다 — shellcheck 에는 "errexit 때문에
   > 이 줄에 닿지 못한다"는 규칙이 없다. actionlint 는 다른 층(SC2086 미인용 변수 등)을
   > 보므로 함께 두지만, 이 규칙을 대신하지는 못한다.

PyYAML 은 dev extra 에 선언돼 있으므로 CI 에서는 항상 있다. 없으면 hard fail 한다 —
"항상 skip" 은 red 보다 나쁘다.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# 검사 대상에서 제외할 경로 조각 (가상환경/캐시/외부 산출물)
SKIP_PARTS = {".venv", ".venv-build", "node_modules", "__pycache__", "site", "build", "dist"}

# 자체 YAML 파서 금지 대상. 이 file 자신과, 파서를 *언급만* 하는 문서는 제외.
PARSER_SCAN_DIRS = ["workflow-source/tests", "workflow-source/tools", "workflow-source/workflow_kit"]
PARSER_SCAN_EXCLUDE = {"workflow-source/tests/check_yaml_surfaces.py"}


def _yaml():
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        print("  FAIL: PyYAML 부재 — dev extra 에 선언돼 있어야 한다 "
              '(`pip install -e "./workflow-source[dev]"`)')
        return None
    return yaml


def _yaml_files() -> list[Path]:
    out: list[Path] = []
    for pattern in ("*.yml", "*.yaml"):
        for p in REPO_ROOT.rglob(pattern):
            if SKIP_PARTS & set(p.parts):
                continue
            out.append(p)
    return sorted(out)


def test_all_yaml_parses() -> bool:
    """1) 모든 YAML 이 진짜 파서로 읽히는가."""
    yaml = _yaml()
    if yaml is None:
        return False
    files = _yaml_files()
    if not files:
        print("  FAIL: 검사 대상 YAML 이 0개 — 탐색 경로가 잘못됐다")
        return False
    ok = True
    for p in files:
        try:
            yaml.safe_load(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001 — 파싱 실패 사유를 그대로 보고한다
            print(f"  FAIL: {p.relative_to(REPO_ROOT)} — {type(e).__name__}: {str(e)[:120]}")
            ok = False
    if ok:
        print(f"  PASS: YAML {len(files)}개 모두 파싱")
    return ok


def _workflows() -> list[Path]:
    d = REPO_ROOT / ".github" / "workflows"
    return sorted(d.glob("*.yml")) + sorted(d.glob("*.yaml")) if d.is_dir() else []


def test_workflow_schema() -> bool:
    """2) GitHub Actions 워크플로우의 최소 스키마."""
    yaml = _yaml()
    if yaml is None:
        return False
    wfs = _workflows()
    if not wfs:
        print("  FAIL: .github/workflows 에 워크플로우가 없다")
        return False
    ok = True
    for p in wfs:
        rel = p.relative_to(REPO_ROOT)
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
        if not isinstance(d, dict):
            print(f"  FAIL: {rel} — 최상위가 매핑이 아니다")
            ok = False
            continue
        if not d.get("name"):
            print(f"  FAIL: {rel} — `name` 부재")
            ok = False
        # YAML 1.1 quirk: 키 `on` 은 boolean True 로 파싱된다.
        if "on" not in d and True not in d:
            print(f"  FAIL: {rel} — 트리거(`on`) 부재")
            ok = False
        jobs = d.get("jobs")
        if not isinstance(jobs, dict) or not jobs:
            print(f"  FAIL: {rel} — `jobs` 부재/빈 값")
            ok = False
            continue
        for jname, job in jobs.items():
            if not isinstance(job, dict):
                print(f"  FAIL: {rel}:{jname} — job 이 매핑이 아니다")
                ok = False
                continue
            if "runs-on" not in job and "uses" not in job:
                print(f"  FAIL: {rel}:{jname} — `runs-on` 도 `uses` 도 없다")
                ok = False
            if "uses" not in job and not job.get("steps"):
                print(f"  FAIL: {rel}:{jname} — `steps` 부재")
                ok = False
    if ok:
        print(f"  PASS: 워크플로우 {len(wfs)}개 스키마 정합")
    return ok


def _reads_yaml_without_parser(src: str) -> list[tuple[int, str]]:
    """YAML 을 파서 없이 읽는 함수를 찾는다 — (줄번호, 함수명).

    판정은 **이름이 아니라 동작**으로 한다. 처음에는 `def _read_yaml*` 같은 이름으로
    잡았는데, 내부를 `yaml.safe_load` 로 이미 바꾼 함수까지 걸려 위양성이 났다.
    이름은 규약이고 규약은 어긋난다 — 함수가 실제로 파서를 부르는지를 본다.

    걸리는 조건 (둘 중 하나):
      (a) 이름이 YAML 파서를 자처하는데 본문에서 `yaml.safe_load`/`yaml.load` 를 부르지 않음
      (b) 이름과 무관하게, YAML 최상위 키 모양(`^name:` / `^on:` / `^jobs:`)을 정규식으로 뜯음
    """
    import ast

    hits: list[tuple[int, str]] = []
    tree = ast.parse(src)
    structural_re = re.compile(r"\^(name|on|jobs|plugins|hooks):")

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body_src = ast.unparse(node)
        calls_parser = "yaml.safe_load" in body_src or "yaml.load" in body_src
        name_claims_yaml = re.match(r"_?(read|parse|load)_yaml", node.name) is not None
        if name_claims_yaml and not calls_parser:
            hits.append((node.lineno, f"{node.name} (파서를 부르지 않는다)"))
            continue
        # (b) 본문의 문자열 리터럴이 YAML 구조를 정규식으로 뜯는가
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                if structural_re.search(sub.value):
                    hits.append((sub.lineno, f"{node.name} (YAML 구조를 정규식으로 매치: "
                                             f"{sub.value[:40]!r})"))
                    break
    return hits


def test_no_handrolled_yaml_parser() -> bool:
    """3) 자체 YAML 파서를 만들지 않았는가 — 원래 결함의 재발 방지."""
    hits: list[str] = []
    for d in PARSER_SCAN_DIRS:
        for p in sorted((REPO_ROOT / d).rglob("*.py")):
            rel = p.relative_to(REPO_ROOT).as_posix()
            if rel in PARSER_SCAN_EXCLUDE:
                continue
            try:
                found = _reads_yaml_without_parser(p.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            hits += [f"{rel}:{line}  {what}" for line, what in found]
    if hits:
        print(f"  FAIL: 파서 없이 YAML 을 읽는 코드 {len(hits)}건 — "
              "`yaml.safe_load` 를 쓸 것 (정규식 파서는 반드시 갈라진다)")
        for h in hits[:8]:
            print(f"    {h}")
        return False
    print("  PASS: 파서 없이 YAML 을 읽는 코드 없음")
    return True


def test_run_blocks_do_not_lose_exit_code() -> bool:
    """4) `run:` 블록이 러너 종료코드를 잃지 않는가 (§2.27 사고 재발 방지).

    **errexit 은 기본으로 켜져 있다.** GitHub 는 `run:` 을 `bash -e {0}` 로 (셸을
    `bash` 로 명시하면 `bash --noprofile --norc -eo pipefail {0}` 로) 실행한다.
    즉 블록 안에 `set -e` 라고 적혀 있지 않아도 켜져 있으며, `set -uo pipefail` 은
    그것을 끄지 않는다. 실제 사고가 정확히 이 모양이었다 — 러너가 non-zero 로 끝나는
    순간 **다음 줄 `rc=$?` 에 닿기도 전에** 스텝이 중단돼, 실패 요약 블록이 한 번도
    실행된 적이 없었다.

    그래서 판정은 "`set -e` 가 적혀 있는가"가 아니라 **"errexit 을 명시적으로 껐는가"**
    로 한다. `$?` 를 읽으려면 `|| rc=$?` 로 받거나, `set +e` 로 꺼야 한다.
    (`continue-on-error` 는 스텝 실패를 job 실패로 만들지 않을 뿐, 스텝 중단은 막지 않는다.)
    """
    yaml = _yaml()
    if yaml is None:
        return False
    ok = True
    for p in _workflows():
        rel = p.relative_to(REPO_ROOT)
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
        for jname, job in (d.get("jobs") or {}).items():
            if not isinstance(job, dict):
                continue
            for i, step in enumerate(job.get("steps") or []):
                run = step.get("run") if isinstance(step, dict) else None
                if not isinstance(run, str):
                    continue
                errexit_off = False
                for line in run.splitlines():
                    stripped = line.strip()
                    # 주석 줄은 코드가 아니다. (이 규칙을 설명하는 주석 자체가
                    # `rc=$?` 를 인용하고 있어 실제로 위양성이 났다.)
                    if stripped.startswith("#"):
                        continue
                    if re.match(r"^set\s+\+[a-z]*e", stripped):
                        errexit_off = True
                    elif re.match(r"^set\s+-[a-z]*e", stripped):
                        errexit_off = False
                    if errexit_off:
                        continue
                    if re.search(r"=\s*\$\?", line) and "||" not in line:
                        print(f"  FAIL: {rel}:{jname} step[{i}] — errexit 이 켜진 채 "
                              f"`$?` 를 직접 읽는다 (그 줄에 닿지 못한다). "
                              f"`|| rc=$?` 로 받거나 `set +e` 로 끌 것: {stripped[:60]}")
                        ok = False
    if ok:
        print("  PASS: `run:` 블록이 종료코드를 잃지 않는다")
    return ok


def test_run_blocks_do_not_pin_canonical_versions() -> bool:
    """5) `run:` 블록이 **정본이 있는 버전**을 리터럴로 박지 않는가.

    실측 (TASK-2026-08-20-main-016): `okf-validate.yml` 이

        if ! grep -q 'okf_version: "0.1"' "$out/index.md"; then

    로 단언하고 있었다. `okf_export.OKF_SPEC_VERSION` 이 0.2 로 오르자 이 스텝이
    red 가 됐다 — **export 는 내내 옳았고 틀린 것은 검사였다.** 저장소가 이미
    이름 붙인 결함이다: *검사가 리터럴로 든 기대값은 계약이 아니라 그 시점 상수다.*

    같은 이행(main-003)이 **Python 검사의 리터럴은 정본 참조로 바꿨는데** YAML 은
    손대지 않았다. 그물이 파일 형식 경계에서 갈린 것이다. 게다가 이 워크플로는
    경로 필터가 걸려 있어 그 뒤 푸시에서 트리거되지 않았고, red 가 6회 쌓이도록
    아무도 못 봤다.

    판정은 **정본 상수 이름을 알고 있는 키**에 한정한다 — 아무 숫자나 잡으면
    python-version 같은 정당한 핀까지 걸린다.
    """
    yaml = _yaml()
    if yaml is None:
        return False
    #: `<번들/산출물 키>` → 그 값의 정본. 정본이 있는 것만 여기 적는다.
    pinned: dict[str, tuple[str, str]] = {
        "okf_version": ("workflow_kit.okf_export", "OKF_SPEC_VERSION"),
    }
    ok = True
    for p_ in _workflows():
        rel = p_.relative_to(REPO_ROOT)
        d = yaml.safe_load(p_.read_text(encoding="utf-8"))
        for jname, job in (d.get("jobs") or {}).items():
            if not isinstance(job, dict):
                continue
            for i, step in enumerate(job.get("steps") or []):
                run = step.get("run") if isinstance(step, dict) else None
                if not isinstance(run, str):
                    continue
                for line in run.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    for key, (module, const) in pinned.items():
                        if re.search(rf"{re.escape(key)}\s*:\s*.?\d+\.\d+", stripped):
                            print(
                                f"  FAIL: {rel}:{jname} step[{i}] — `{key}` 를 리터럴로 "
                                f"박았다. `{module}.{const}` 가 정본이니 거기서 파생할 것: "
                                f"{stripped[:70]}"
                            )
                            ok = False
    if ok:
        print("  PASS: `run:` 블록이 정본 있는 버전을 리터럴로 박지 않는다")
    return ok


def test_run_blocks_reference_existing_scripts() -> bool:
    """6) `run:` 블록이 **실재하는 스크립트**를 부르는가.

    실측 (TASK-2026-08-20-main-017): `consumer-metrics-digest.yml` 이
    `workflow-source/tools/consumer_metrics.py` 를 불렀는데, 그 파일은
    `workflow-source/workflow_kit/tools/` 로 옮겨진 뒤였다 (`7fed4158`,
    2nd deprecation cycle 의 구경로 shim drop). **파일은 따라 옮겨졌는데
    워크플로의 참조가 안 따라왔다.**

    주간 cron 으로만 도는 워크플로라 3일간 아무도 못 봤다 — 이것이
    main-016 이 남긴 규칙("돌지 않은 워크플로는 통과한 워크플로가 아니다")의
    두 번째 사례다. **자주 안 도는 워크플로일수록 정적으로 잡아야 한다.**

    저장소 상대 경로로 적힌 `.py` 만 본다. `${{ }}` 치환이나 변수가 섞인
    경로는 정적으로 판정할 수 없으므로 건너뛴다 — **모르는 것을 실패로
    만들지 않되, 아는 것은 반드시 본다.**
    """
    yaml = _yaml()
    if yaml is None:
        return False
    # 저장소 최상위 디렉터리로 시작하는 상대 경로만 판정 대상이다.
    roots = tuple(
        d.name for d in REPO_ROOT.iterdir() if d.is_dir() and not d.name.startswith(".")
    )
    if not roots:
        print("  FAIL: 저장소 최상위 디렉터리를 못 읽었다")
        return False
    pattern = re.compile(rf"(?:{'|'.join(re.escape(r) for r in roots)})/[A-Za-z0-9_./-]+\.py")
    ok = True
    seen = 0
    for p_ in _workflows():
        rel = p_.relative_to(REPO_ROOT)
        d = yaml.safe_load(p_.read_text(encoding="utf-8"))
        for jname, job in (d.get("jobs") or {}).items():
            if not isinstance(job, dict):
                continue
            for i, step in enumerate(job.get("steps") or []):
                run = step.get("run") if isinstance(step, dict) else None
                if not isinstance(run, str):
                    continue
                for line in run.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("#") or "${{" in stripped:
                        continue
                    for match in pattern.findall(stripped):
                        seen += 1
                        if not (REPO_ROOT / match).is_file():
                            print(
                                f"  FAIL: {rel}:{jname} step[{i}] — 없는 스크립트를 "
                                f"부른다: {match}"
                            )
                            ok = False
    if ok:
        print(f"  PASS: `run:` 블록의 스크립트 참조 {seen}건이 전부 실재한다")
    return ok


def main() -> int:
    cases = [
        ("test_all_yaml_parses", test_all_yaml_parses),
        ("test_workflow_schema", test_workflow_schema),
        ("test_no_handrolled_yaml_parser", test_no_handrolled_yaml_parser),
        ("test_run_blocks_do_not_lose_exit_code", test_run_blocks_do_not_lose_exit_code),
        ("test_run_blocks_do_not_pin_canonical_versions",
         test_run_blocks_do_not_pin_canonical_versions),
        ("test_run_blocks_reference_existing_scripts",
         test_run_blocks_reference_existing_scripts),
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
