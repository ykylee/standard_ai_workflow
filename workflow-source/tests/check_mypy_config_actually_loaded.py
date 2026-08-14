"""mypy strict 설정이 **실제로 로드되는가** (v1.0.2+).

## 왜 필요한가

`.github/workflows/mypy-strict.yml` 은 v0.11.11 부터 이렇게 돌고 있었다:

    mypy --no-incremental workflow-source/workflow_kit/     # cwd = REPO_ROOT

그리고 헤더 주석은 "workflow-source/ 의 pyproject [tool.mypy] strict=true read" 라고
적고 있었다. **사실이 아니었다.** mypy 의 config 탐색은 *cwd 기준* 으로

    ./mypy.ini → ./.mypy.ini → ./pyproject.toml ([tool.mypy] 가 있을 때만) → ./setup.cfg

순인데, REPO_ROOT 의 `pyproject.toml` 은 의도된 root-level placeholder scaffold
(`eb62f37`)라 `[tool.mypy]` 섹션이 없다. 그래서 전부 건너뛰고 `Config File: Default`
로 떨어졌다. 결과:

| 실행 | Config | 결과 |
|---|---|---|
| CI 가 하던 것 | **Default** | 0 errors / 117 files (green) |
| 선언된 strict 를 물렸을 때 | workflow-source/pyproject.toml | **4 errors** / 117 files |

같은 결함이 release-time gate (`tools/release_pipeline.py`) 에도 **사본으로** 있었다.
규약을 여러 곳에 복제하면 갈라지기만 하는 게 아니라 이렇게 **같이 틀린다**.

그리고 재발 방지용 test (`check_mypy_strict_ci_v0_11_11.py` case 8) 는 CI invocation 을
*충실히 재현* 하고 exit 0 을 확인했다. 깨진 실행을 정확히 복제했으니 green 이었다.
**재현은 검증이 아니다** — 무엇을 재현하는지도 함께 봐야 한다. 이 file 이 그 층이다.

## 이 file 이 보는 것

1. 선언 — mypy 를 부르는 **모든** 지점이 `--config-file` 을 명시하는가
   (AST 전수 조사 + workflow YAML, mypy 불필요)
2. 선언 내용 — 그 config 가 실제로 `strict = true` 인가
3. exclude anchor — 어떤 exclude 패턴도 `workflow_kit/` 내부를 잘라내지 않는가
4. 사실 — mypy 를 실제로 돌렸을 때 그 config 를 물었다고 보고하는가 (`mypy -v`)
5. 사실 — 잘려 나간 적 있는 `common/schemas/` 가 검사 대상에 들어 있는가
6. 음성 대조 — `--config-file` 을 빼면 정말로 `Default` 로 떨어지는가
   (위험이 실재함을 증명한다. 이게 없으면 4번이 무엇을 막는지 알 수 없다.)

4~6 은 mypy 가 있어야 한다. smoke CI 는 `pip install -e "./workflow-source[dev,...]"`
로 mypy 를 깔므로 CI 에서는 항상 돈다. 로컬에 mypy 가 없으면 4~6 만 SKIP 한다 —
1~3 은 mypy 없이도 항상 돈다.
"""
from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    ".github/workflows/mypy-strict.yml",
)
"""config 가 실제로 로드되는지를 재므로 config 파일과 그 대상이 관찰 범위다."""

# 병렬 전량(--jobs auto)에서 43s 실측 (2026-08-11) — 기본 60s 상한과 여유가
# 없어 부하 편차만으로 TIMEOUT flake 가 난다. 행(hang) 검출은 150s 로도 충분하다.
CHECK_TIMEOUT_S = 150


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_REL = "workflow-source/pyproject.toml"
CONFIG_PATH = REPO_ROOT / CONFIG_REL
TARGET_REL = "workflow-source/workflow_kit/"

# mypy 를 부르는 Python 코드를 찾을 범위. 하드코딩 목록 대신 **전수 조사** 한다 —
# 처음 이 file 을 쓸 때는 호출 지점이 3곳인 줄 알았으나 AST 로 훑으니 23곳이었고,
# 그 중 21곳이 config 없이 돌고 있었다. 목록을 손으로 유지하면 반드시 빠진다.
SCAN_DIRS = ["workflow-source/tests", "workflow-source/tools", "workflow-source/workflow_kit"]

# 이 file 자신은 제외 — `_run_mypy` 가 config 를 *인자로* 받고, 음성 대조 case 는
# 일부러 config 없이 부른다. AST 로는 그 구분이 안 된다.
SCAN_EXCLUDE = {"workflow-source/tests/check_mypy_config_actually_loaded.py"}

# YAML/스크립트라 AST 로 볼 수 없는 호출 지점.
TEXT_SITES = [(".github/workflows/mypy-strict.yml", "CI (mypy-strict workflow)")]


def _mypy_call_sites() -> list[tuple[str, int, bool]]:
    """(파일, 줄번호, --config-file 명시 여부) — `--version` 탐침은 제외."""
    sites: list[tuple[str, int, bool]] = []
    for d in SCAN_DIRS:
        for p in sorted((REPO_ROOT / d).rglob("*.py")):
            rel = p.relative_to(REPO_ROOT).as_posix()
            if rel in SCAN_EXCLUDE:
                continue
            try:
                tree = ast.parse(p.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "run"
                        and node.args
                        and isinstance(node.args[0], ast.List)):
                    continue
                lits = [e.value for e in node.args[0].elts
                        if isinstance(e, ast.Constant) and isinstance(e.value, str)]
                if "mypy" not in lits or "--version" in lits:
                    continue
                sites.append((rel, node.lineno, "--config-file" in lits))
    return sites


def _mypy_available() -> bool:
    try:
        subprocess.run(
            [sys.executable, "-m", "mypy", "--version"],
            capture_output=True, timeout=60, check=True,
        )
        return True
    except Exception:
        return False


def _run_mypy(extra_args: list[str]) -> subprocess.CompletedProcess[str]:
    """REPO_ROOT 를 cwd 로 mypy 실행 (CI 와 동일 조건)."""
    return subprocess.run(
        [sys.executable, "-m", "mypy", "-v", "--no-incremental", *extra_args, TARGET_REL],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300,
    )


def _config_line(proc: subprocess.CompletedProcess[str]) -> str:
    for line in (proc.stdout + proc.stderr).splitlines():
        if line.startswith("LOG:  Config File:"):
            return line.split(":", 2)[2].strip()
    return ""


def test_sites_declare_config_file() -> bool:
    """1) mypy 를 부르는 **모든** 지점이 --config-file 을 명시하는가 (전수 조사)."""
    ok = True

    sites = _mypy_call_sites()
    missing = [(f, ln) for f, ln, has in sites if not has]
    if missing:
        ok = False
        print(f"  FAIL: config 미명시 호출 {len(missing)}/{len(sites)}건 — "
              "cwd 에 [tool.mypy] 가 없으면 Config File: Default 로 떨어진다")
        for f, ln in missing[:10]:
            print(f"    {f}:{ln}")
        if len(missing) > 10:
            print(f"    ... 외 {len(missing) - 10}건")
    else:
        print(f"  ok: Python 호출 {len(sites)}건 모두 config 명시")

    for rel, label in TEXT_SITES:
        path = REPO_ROOT / rel
        if not path.is_file():
            print(f"  FAIL: {label} — 파일 부재 ({rel})")
            ok = False
            continue
        # 주석에 적힌 설명이 아니라 **실제 invocation** 이어야 한다.
        code = "\n".join(
            ln for ln in path.read_text(encoding="utf-8").splitlines()
            if not ln.lstrip().startswith("#")
        )
        if "--config-file" not in code or "pyproject.toml" not in code:
            print(f"  FAIL: {label} — invocation 에 --config-file 부재 ({rel})")
            ok = False
        else:
            print(f"  ok: {label}")

    if ok:
        print(f"  PASS: 호출 지점 {len(sites) + len(TEXT_SITES)}곳 모두 config 명시")
    return ok


def test_config_declares_strict() -> bool:
    """2) 로드 대상 config 가 실제로 strict = true 인가."""
    if not CONFIG_PATH.is_file():
        print(f"  FAIL: {CONFIG_REL} 부재")
        return False
    text = CONFIG_PATH.read_text(encoding="utf-8")
    if "[tool.mypy]" not in text:
        print(f"  FAIL: {CONFIG_REL} 에 [tool.mypy] 섹션 부재")
        return False
    section = text.split("[tool.mypy]", 1)[1]
    # 다음 섹션 헤더 전까지
    section = re.split(r"^\[", section, maxsplit=1, flags=re.MULTILINE)[0]
    if not re.search(r"^\s*strict\s*=\s*true\s*$", section, re.MULTILINE):
        print(f"  FAIL: [tool.mypy] 에 strict = true 부재")
        return False
    print("  PASS: [tool.mypy] strict = true")
    return True


def _exclude_patterns() -> list[str]:
    text = CONFIG_PATH.read_text(encoding="utf-8")
    m = re.search(r"^exclude\s*=\s*(\[.*?\])", text, re.MULTILINE | re.DOTALL)
    if not m:
        return []
    return re.findall(r'"([^"]+)"', m.group(1))


def test_exclude_does_not_hit_workflow_kit() -> bool:
    """3) exclude 패턴이 workflow_kit/ 내부를 잘라내지 않는가.

    원래 결함: `"schemas/.*"` 는 anchor 가 없어 경로 어디서든 매치했고,
    의도한 `workflow-source/schemas/` (실은 .py 가 0개다) 대신
    `workflow_kit/common/schemas/` 의 **실소스 20 file** 을 조용히 제외했다.
    """
    patterns = _exclude_patterns()
    if not patterns:
        print("  FAIL: exclude 패턴을 읽지 못했다")
        return False

    # workflow_kit/ 내부의 실제 경로를 두 cwd 기준으로 만들어 본다.
    kit = REPO_ROOT / "workflow-source" / "workflow_kit"
    samples: list[str] = []
    for p in sorted(kit.rglob("*.py"))[:400]:
        rel_root = p.relative_to(REPO_ROOT).as_posix()          # cwd = REPO_ROOT
        rel_ws = p.relative_to(REPO_ROOT / "workflow-source").as_posix()  # cwd = workflow-source
        samples += [rel_root, rel_ws]

    ok = True
    for pat in patterns:
        try:
            rx = re.compile(pat)
        except re.error as e:
            print(f"  FAIL: exclude 패턴이 유효한 정규식이 아니다 {pat!r}: {e}")
            ok = False
            continue
        hits = [s for s in samples if rx.search(s)]
        if hits:
            print(f"  FAIL: exclude {pat!r} 가 workflow_kit/ 내부 {len(hits)}건을 매치 "
                  f"(예: {hits[0]})")
            ok = False
    if ok:
        print(f"  PASS: exclude {len(patterns)}개 모두 workflow_kit/ 와 무관")
    return ok


def test_mypy_actually_loads_config() -> bool:
    """4) 실제로 돌렸을 때 그 config 를 물었다고 보고하는가."""
    proc = _run_mypy(["--config-file", CONFIG_REL])
    loaded = _config_line(proc)
    if not loaded:
        print("  FAIL: `mypy -v` 출력에 'Config File:' 줄이 없다 (출력 형식 변경?)")
        return False
    if Path(loaded).resolve() != CONFIG_PATH.resolve():
        print(f"  FAIL: 로드된 config 가 다르다 — 기대 {CONFIG_PATH}, 실제 {loaded!r}")
        return False
    print(f"  PASS: Config File = {loaded}")
    return True


def test_schemas_files_are_checked() -> bool:
    """5) 한때 조용히 잘려 나갔던 common/schemas/ 가 검사 대상인가.

    exclude anchor 결함으로 117 → 97 file 로 줄어 있었다. 개수만 보면 알아채기
    어려우므로 **특정 파일이 대상에 들어 있는지** 를 본다.
    """
    proc = _run_mypy(["--config-file", CONFIG_REL])
    out = proc.stdout + proc.stderr
    found = re.findall(r"path='([^']*workflow_kit/common/schemas/[^']*)'", out)
    if not found:
        print("  FAIL: workflow_kit/common/schemas/ 가 검사 대상에 없다 "
              "(exclude anchor 회귀 가능성)")
        return False
    print(f"  PASS: common/schemas/ {len(found)} file 검사 대상")
    return True


def test_negative_control_default_config() -> bool:
    """6) 음성 대조 — --config-file 을 빼면 정말로 Default 로 떨어지는가.

    이게 실패하면 4번이 무엇을 막고 있는지 알 수 없다. 원래 결함을 그대로
    재현해 두는 자리다.
    """
    proc = _run_mypy([])
    loaded = _config_line(proc)
    if loaded and Path(loaded).resolve() == CONFIG_PATH.resolve():
        print("  PASS: (환경이 바뀌어) config 없이도 올바른 config 를 문다 — 위험 해소됨")
        return True
    if loaded and loaded != "Default":
        print(f"  FAIL: 예상 밖의 config 를 문다: {loaded!r}")
        return False
    print("  PASS: config 미지정 시 Default — 명시가 필요하다는 전제 성립")
    return True


def main() -> int:
    text_cases = [
        ("test_sites_declare_config_file", test_sites_declare_config_file),
        ("test_config_declares_strict", test_config_declares_strict),
        ("test_exclude_does_not_hit_workflow_kit", test_exclude_does_not_hit_workflow_kit),
    ]
    behavior_cases = [
        ("test_mypy_actually_loads_config", test_mypy_actually_loads_config),
        ("test_schemas_files_are_checked", test_schemas_files_are_checked),
        ("test_negative_control_default_config", test_negative_control_default_config),
    ]

    results: list[tuple[str, bool]] = []
    for name, fn in text_cases:
        print(f"\n[{name}]")
        results.append((name, fn()))

    if _mypy_available():
        for name, fn in behavior_cases:
            print(f"\n[{name}]")
            try:
                results.append((name, fn()))
            except subprocess.TimeoutExpired:
                print("  FAIL: mypy timeout (>300s)")
                results.append((name, False))
    elif os.environ.get("GITHUB_ACTIONS") == "true":
        # CI 는 dev extra 로 mypy 를 깐다. 없으면 설치 단계가 깨진 것이므로 hard fail —
        # "항상 skip" 은 red 보다 나쁘다 (초록으로 보인다).
        print("\n  FAIL: CI 인데 mypy 가 없다 — [dev] extra 설치 누락")
        results += [(name, False) for name, _ in behavior_cases]
    else:
        print("\n  SKIP: mypy 미설치 — 동작 검증 3건 건너뜀 "
              '(`pip install -e "./workflow-source[dev]"`)')

    passed = sum(1 for _, ok in results if ok)
    print()
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== {passed}/{len(results)} PASS ===")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
