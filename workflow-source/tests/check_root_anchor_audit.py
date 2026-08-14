#!/usr/bin/env python3
"""기준 전수 조사가 **저장소에 남아 돌고 있는가** (v1.0.8, 11 case).

## 왜 필요한가

§2.47(린터) · §2.49(doctor) · §2.50(branch 해석기) · §2.51(dashboard) 은 같은 결함
네 번이었다. §2.50 에서 한 번은 AST 로 전수 조사했지만 **그 스크립트를 저장소에 남기지
않았다** — 그래서 §2.51 은 다시 손으로 찾았다. 조사를 남기지 않으면 다음 번에도 손으로
센다. `tools/audit_root_anchors.py` 가 그 조사이고, 이 검사가 그것을 돌린다.

## 이 검사가 고정하는 것

1. 조사가 **실제로 돌았다** — 파일 수 / 기준 수의 바닥선. 조사 0건은 결함 0건이 아니다.
2. 각 규칙이 **볼 자리가 있다** — R2/R3 후보 함수 수가 0이면 인자 이름 목록이 코드와
   갈라진 것이고, 규칙은 *깨지지 않고 무력화*된다 (§2.50 의 `GITHUB_REF_NAME` 과 같은 모양).
3. 이 저장소에 **미선언 결함이 없다**.
4. 원장에 **잔재가 없다** — 코드에 없는 예외가 선언돼 있으면 다음 사람은 사라진 예외를
   사실로 읽는다.
5. 되주입 3종(§2.49 / §2.51 / §2.50 의 실제 모양)이 **각각 다른 규칙으로** 잡힌다.
6. 깨끗한 코드는 잡지 않는다 — 위양성을 내는 검사는 무시당하고, 그러면 같은 검사가
   잡아 줄 진짜 결함도 함께 무시된다 (§2.48 의 교훈).
7. 조사 도구 자신이 **모듈 위치에서 기준을 유도하지 않는다** — 감사하는 함정에 감사자가
   빠지면 안 된다. 그리고 기준이 틀렸을 때 **조용히 통과하지 않는다**.
8. 저장소의 **모든** `.py` 가 조사되거나 제외 트리 안에 있다 (case 10). 여기서 독립적으로
   다시 세서 대조한다 — 도구의 개수를 되읽으면 자기 자신과 비교하는 것밖에 못 한다.
9. "생성물인가" 를 **이름이 아니라 `.gitignore`** 로 가른다 (case 11). `build` 라는 이름의
   진짜 소스가 조용히 빠지지 않고, fallback 으로 떨어졌으면 그 사실이 산출물에 있다.

Cross-ref: releases/Beta-v1.0.0.md §2.47 / §2.49 / §2.50 / §2.51 / §2.52 / §2.53 / §2.54.
"""

from __future__ import annotations

import json
import shutil

# 단독 43s 실측 (2026-08-14) — 기본 60s 상한과 여유가 없어 병렬 부하 편차만으로
# TIMEOUT flake 가 난다 (같은 날 slash 축 전량에서 실제로 났다). 행 검출은 150s 로 충분.
CHECK_TIMEOUT_S = 150
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "workflow-source" / "workflow_kit" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from audit_root_anchors import (  # noqa: E402
    ROOT_ANCHOR_LEDGER,
    SCAN_SOURCE_ARGUMENT,
    SCAN_SOURCE_CWD,
    SELECTION_GIT,
    SELECTION_NAME_FALLBACK,
    resolve_scan_root,
    run_audit,
)

AUDIT_TOOL = TOOLS_DIR / "audit_root_anchors.py"

# 바닥선. 실측(446 file / 322 기준 / R2 21 / R3 147)의 절반 근처로 잡아, 정상적인
# 증감은 통과시키되 **조사 범위가 무너지면** 걸리게 한다.
#
# **바닥선만으로는 부족하다.** `skills` 트리(19 file)를 조용히 빼는 되주입을 하면
# 446 → 427 로 줄어드는데 이 바닥선은 전부 통과한다. 범위가 *줄어든 사실* 은
# case_10 의 전수 대조가 잡는다 — 바닥선은 "붕괴" 를, 대조는 "누락" 을 본다.
MIN_SCANNED_FILES = 200
MIN_MODULE_ANCHORS = 120
MIN_R2_CANDIDATES = 5
MIN_R3_CANDIDATES = 30

# 되주입: 실제로 있었던 결함의 모양 그대로.
INJECTIONS: dict[str, tuple[str, str]] = {
    # §2.49 — doctor 의 기준이 저장소 루트의 두 단계 위였다.
    "anchor_outside_workspace": (
        "outside_anchor.py",
        "from pathlib import Path\n"
        "def _default_root() -> Path:\n"
        "    return Path(__file__).resolve().parents[6]\n",
    ),
    # §2.51 — dashboard 가 미지정 workspace 를 모듈 위치로 떨어뜨렸다.
    "module_anchor_as_default": (
        "default_anchor.py",
        "from pathlib import Path\n"
        "def collect(workspace_root=None):\n"
        "    if workspace_root is None:\n"
        "        return Path(__file__).resolve().parents[3]\n"
        "    return Path(workspace_root)\n",
    ),
    # §2.50 — workspace 를 받는데 branch 는 모듈 저장소에서 얻었다.
    "branch_from_module_repo": (
        "module_branch.py",
        "from pathlib import Path\n"
        "def get_current_branch() -> str:\n"
        "    return 'main'\n"
        "def workflow_branch_dir(project_profile_path):\n"
        "    return project_profile_path.parent / get_current_branch()\n",
    ),
}

# 위양성 방지: 세 규칙이 요구하는 올바른 모양.
CLEAN_SOURCE = (
    "from pathlib import Path\n"
    "def branch_for_workspace(ws) -> str:\n"
    "    return 'main'\n"
    "def collect(workspace_root=None):\n"
    "    root = Path(workspace_root) if workspace_root is not None else Path.cwd()\n"
    "    return root\n"
    "def branch_dir(project_profile_path):\n"
    "    return project_profile_path.parent / branch_for_workspace(project_profile_path)\n"
)


def _fixture(td: str, filename: str, source: str) -> Path:
    """조사 대상 배치를 흉내 낸 최소 트리."""
    root = Path(td) / "repo"
    pkg = root / "workflow-source" / "workflow_kit"
    pkg.mkdir(parents=True)
    (pkg / filename).write_text(source, encoding="utf-8")
    return root


def case_1_audit_actually_ran() -> bool:
    """1) 조사가 실제로 돌았다 — 바닥선 미만이면 범위가 무너진 것이다."""
    result = run_audit(REPO_ROOT)
    inv = result["inventory"]
    if not result["scan_ok"]:
        print(f"  FAIL: scan_ok=False — 필수 대상 부재 {result['missing_required_dirs']}")
        return False
    problems = []
    if inv["scanned_files"] < MIN_SCANNED_FILES:
        problems.append(f"scanned_files {inv['scanned_files']} < {MIN_SCANNED_FILES}")
    if inv["module_anchors"] < MIN_MODULE_ANCHORS:
        problems.append(f"module_anchors {inv['module_anchors']} < {MIN_MODULE_ANCHORS}")
    if inv["missing_dirs"]:
        problems.append(f"없는 조사 대상 {inv['missing_dirs']}")
    if inv["unparsable_files"]:
        problems.append(f"파싱 실패 {inv['unparsable_files']}")
    if problems:
        print(f"  FAIL: {problems}")
        return False
    print(f"  [info] {inv['scanned_files']} file / 모듈 유도 기준 {inv['module_anchors']} / "
          f"cwd {inv['cwd_anchors']} / 기타 연쇄 {inv['deep_parent_chains']}")
    return True


def case_2_rules_have_something_to_look_at() -> bool:
    """2) 각 규칙이 볼 자리가 있다 — 0이면 규칙이 조용히 무력화된 것이다."""
    inv = run_audit(REPO_ROOT)["inventory"]
    if inv["r2_candidate_functions"] < MIN_R2_CANDIDATES:
        print(f"  FAIL: R2 후보 {inv['r2_candidate_functions']} < {MIN_R2_CANDIDATES} — "
              "WORKSPACE_PARAM_NAMES 가 코드와 갈라졌을 수 있다")
        return False
    if inv["r3_candidate_functions"] < MIN_R3_CANDIDATES:
        print(f"  FAIL: R3 후보 {inv['r3_candidate_functions']} < {MIN_R3_CANDIDATES} — "
              "WORKSPACE_BEARING_PARAM_NAMES 가 코드와 갈라졌을 수 있다")
        return False
    print(f"  [info] R2 가 본 함수 {inv['r2_candidate_functions']}개 / "
          f"R3 가 본 함수 {inv['r3_candidate_functions']}개")
    return True


def case_3_no_undeclared_findings() -> bool:
    """3) 이 저장소에 미선언 결함이 없다."""
    result = run_audit(REPO_ROOT)
    if result["undeclared"]:
        print(f"  FAIL: 미선언 {len(result['undeclared'])}건")
        for f in result["undeclared"]:
            print(f"    [{f['rule']}] {f['path']}:{f['line']} ({f['symbol']}) — {f['detail']}")
        print("    → 고치거나, 이유와 함께 ROOT_ANCHOR_LEDGER 에 선언할 것")
        return False
    print(f"  [info] 미선언 0건 (선언된 예외 {len(result['declared'])}건)")
    return True


def case_4_ledger_has_no_stale_entries() -> bool:
    """4) 원장에 잔재가 없다 — 사라진 예외가 사실처럼 남아 있으면 안 된다."""
    result = run_audit(REPO_ROOT)
    if result["stale_ledger"]:
        print(f"  FAIL: 원장 잔재 {len(result['stale_ledger'])}건 (코드에 없다)")
        for e in result["stale_ledger"]:
            print(f"    [{e['rule']}] {e['path']} ({e['symbol']})")
        return False
    if not ROOT_ANCHOR_LEDGER:
        print("  [info] 원장이 비어 있다 (선언된 예외 없음)")
        return True
    missing_reason = [e.key for e in ROOT_ANCHOR_LEDGER if len(e.reason.strip()) < 20]
    if missing_reason:
        print(f"  FAIL: 이유가 없는 원장 항목 {missing_reason} — 선언은 이유와 함께여야 한다")
        return False
    print(f"  [info] 원장 {len(ROOT_ANCHOR_LEDGER)}건 전부 코드에 실재 + 이유 기재")
    return True


def case_5_injections_are_caught() -> bool:
    """5) 되주입 3종이 **각각 자기 규칙으로** 잡힌다 (섞여 잡히면 판정이 흐려진다)."""
    for expected_rule, (filename, source) in INJECTIONS.items():
        with tempfile.TemporaryDirectory() as td:
            root = _fixture(td, filename, source)
            result = run_audit(root)
            if not result["scan_ok"]:
                print(f"  FAIL: {expected_rule} — fixture 조사 실패 (scan_ok=False)")
                return False
            rules = sorted({f["rule"] for f in result["undeclared"]})
            if rules != [expected_rule]:
                print(f"  FAIL: {expected_rule} 되주입이 {rules} 로 잡혔다 (기대: [{expected_rule}])")
                return False
    print(f"  [info] 되주입 {len(INJECTIONS)}종 각각 다른 규칙으로 검출")
    return True


def case_6_clean_source_is_not_flagged() -> bool:
    """6) 올바른 모양은 잡지 않는다 — 위양성을 내는 검사는 무시당한다 (§2.48)."""
    with tempfile.TemporaryDirectory() as td:
        root = _fixture(td, "clean.py", CLEAN_SOURCE)
        result = run_audit(root)
        if not result["scan_ok"]:
            print("  FAIL: fixture 조사 실패 (scan_ok=False)")
            return False
        if result["undeclared"]:
            print(f"  FAIL: 깨끗한 코드에서 {len(result['undeclared'])}건 위양성")
            for f in result["undeclared"]:
                print(f"    [{f['rule']}] {f['symbol']} — {f['detail']}")
            return False
    print("  [info] 명시 인자 → cwd / branch_for_workspace 형태는 무징후")
    return True


def case_7_auditor_root_is_not_module_derived() -> bool:
    """7) 조사 도구가 자기 기준을 **모듈 위치에서 유도하지 않는다**.

    감사하는 함정(§2.51)에 감사자가 빠지면, 어디서 부르든 늘 이 저장소를 재면서
    "쟀다" 고 보고하게 된다.
    """
    with tempfile.TemporaryDirectory() as td:
        elsewhere = Path(td).resolve()
        # cwd 를 바꿔 재는 것은 프로세스 전역 상태라, 별도 프로세스로 잰다.
        proc = subprocess.run(
            [sys.executable, str(AUDIT_TOOL), "--json"],
            cwd=str(elsewhere), capture_output=True, text=True, timeout=180,
            env={"PATH": "/usr/bin:/bin", "HOME": str(elsewhere)},
        )
        payload = json.loads(proc.stdout)
        if Path(payload["scan_root"]).resolve() != elsewhere:
            print(f"  FAIL: 다른 cwd 에서 불렀는데 기준이 {payload['scan_root']} "
                  f"(기대: {elsewhere}) — 모듈 위치로 떨어졌다")
            return False
        if payload["scan_root_source"] != SCAN_SOURCE_CWD:
            print(f"  FAIL: 출처가 {payload['scan_root_source']} (기대: {SCAN_SOURCE_CWD})")
            return False
        if Path(payload["scan_root"]).resolve() == REPO_ROOT:
            print("  FAIL: 다른 cwd 인데 이 저장소를 쟀다")
            return False
    root, source = resolve_scan_root(REPO_ROOT)
    if root != REPO_ROOT or source != SCAN_SOURCE_ARGUMENT:
        print(f"  FAIL: 명시 인자가 우선하지 않는다 — {root} / {source}")
        return False
    print(f"  [info] 미지정 → cwd, 명시 → argument. 모듈 위치는 쓰지 않는다")
    return True


def case_8_wrong_root_fails_loudly() -> bool:
    """8) 기준이 틀리면 **조용히 통과하지 않는다**.

    조사 대상이 하나도 없는데 "미선언 0건" 이라고 말하면, 그것은 실행 못 한 검사를
    통과로 보고하는 것이다.
    """
    with tempfile.TemporaryDirectory() as td:
        empty = Path(td)
        result = run_audit(empty)
        if result["scan_ok"]:
            print(f"  FAIL: 빈 디렉터리를 쟀는데 scan_ok=True (scanned={result['inventory']['scanned_files']})")
            return False
        if result["ok"]:
            print("  FAIL: 조사 0건인데 ok=True — 조사 0건은 결함 0건이 아니다")
            return False
        proc = subprocess.run(
            [sys.executable, str(AUDIT_TOOL), "--repo-root", str(empty)],
            capture_output=True, text=True, timeout=180,
        )
        if proc.returncode == 0:
            print(f"  FAIL: CLI 가 exit 0 (조사 0건인데 성공으로 보고)\n{proc.stdout}")
            return False
    print("  [info] 조사 0건 → scan_ok=False + exit 1")
    return True


def case_10_scan_covers_every_source_file() -> bool:
    """10) 저장소의 **모든** `.py` 가 조사되거나 제외 트리 안에 있다 — 빠진 것이 없다.

    첫 버전은 `SCAN_DIRS` 라는 *포함* 목록으로 조사 대상을 정했다. 그러면 새 소스 트리가
    생겼을 때 조사에서 빠지는데 **그 사실이 어디에도 안 보인다** — "선언했는데 없는 것"
    은 셀 수 있어도 "있는데 선언 안 한 것" 은 셀 수 없기 때문이다. 실제로 27 file 이
    조용히 빠져 있었다(`skills` 19 / `ai-workflow/mcp_servers` 6 / `examples` 2).

    그래서 포함 목록을 없앴다. 이 case 는 그 사실을 **독립적으로** 다시 센다 — 도구의
    산출물을 되읽지 않고 여기서 직접 훑는다. 자기 자신과 비교하면 둘이 같이 틀려도
    통과한다(§2.50 의 교훈).
    """
    # 기대값은 **git 에게 직접** 묻는다. 도구와 같은 정본을 쓰되 호출은 여기서 따로 한다
    # — 이름 목록으로 세면 추적되는 `build/` 소스가 생겼을 때 위양성이 된다(§2.54).
    expected: set[Path] = set()
    for args in (["ls-files", "-z", "--", "*.py"],
                 ["ls-files", "--others", "--exclude-standard", "-z", "--", "*.py"]):
        proc = subprocess.run(["git", "-C", str(REPO_ROOT), *args],
                              capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            print(f"  FAIL: git 조회 실패 ({args}): {proc.stderr.strip()[:200]}")
            return False
        expected |= {Path(r) for r in proc.stdout.split("\0")
                     if r and (REPO_ROOT / r).is_file()}
    if not expected:
        print("  FAIL: git 이 .py 를 한 건도 안 냈다 — 대조의 전제가 무너졌다")
        return False

    result = run_audit(REPO_ROOT)
    scanned = {Path(f) for f in _scanned_relpaths(result)}
    missed = sorted(expected - scanned)
    extra = sorted(scanned - expected)
    if missed:
        print(f"  FAIL: 조사에서 빠진 소스 {len(missed)}건: {[str(p) for p in missed[:8]]}")
        print("        → 제외 트리도 아닌데 안 봤다. 포함 목록이 되살아났나?")
        return False
    if extra:
        print(f"  FAIL: 제외 대상인데 조사됨 {len(extra)}건: {[str(p) for p in extra[:8]]}")
        return False
    print(f"  [info] git 기준 .py {len(expected)}건 전부 조사됨 "
          f"(선정: {result['inventory']['source_selection']})")
    return True


def case_11_generated_is_decided_by_git_not_by_name() -> bool:
    """11) "생성물인가" 를 **이름이 아니라 저장소 선언**(`.gitignore`)으로 가른다.

    이름 기반 제외는 추측이다. `build` 라는 이름의 *진짜 소스* 디렉터리가 생기면
    조용히 빠지고, 그 안의 결함은 "미선언 0건" 으로 보고된다 — 실행 못 한 검사가
    통과로 보이는 바로 그 모양이다.

    셋을 고정한다:
      (a) 이 저장소는 `git` 으로 대상을 고른다 — 조용히 추측으로 떨어지지 않는다.
      (b) git 이 추적하는 `build/` 안의 소스는 **조사되고 결함이 잡힌다**.
      (c) git 루트가 아니면 fallback 이되, **그 사실을 산출물이 밝힌다**.
    """
    real = run_audit(REPO_ROOT)
    if real["inventory"]["source_selection"] != SELECTION_GIT:
        print(f"  FAIL: 이 저장소의 대상 선정이 {real['inventory']['source_selection']} "
              f"(기대: {SELECTION_GIT}) — 이름 추측으로 조용히 떨어졌다")
        return False

    src = ("from pathlib import Path\n"
           "def _root():\n"
           "    return Path(__file__).resolve().parents[6]\n")
    with tempfile.TemporaryDirectory() as td:
        root = _fixture(td, "ok.py", "x = 1\n")
        build = root / "build"          # 이름은 생성물, 실체는 소스
        build.mkdir()
        (build / "real_source.py").write_text(src, encoding="utf-8")

        env = {"PATH": "/usr/bin:/bin", "HOME": str(root), "GIT_CONFIG_GLOBAL": "/dev/null"}
        for args in (("init", "-q", "."), ("add", "-A"),
                     ("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")):
            proc = subprocess.run(["git", *args], cwd=str(root), capture_output=True,
                                  text=True, timeout=60, env=env)
            if proc.returncode != 0:
                print(f"  FAIL: fixture git 준비 실패 ({args}): {proc.stderr.strip()[:200]}")
                return False

        got = run_audit(root)
        if got["inventory"]["source_selection"] != SELECTION_GIT:
            print(f"  FAIL: fixture 가 git 모드가 아니다 ({got['inventory']['source_selection']})")
            return False
        hit = [f for f in got["undeclared"] if f["path"] == "build/real_source.py"]
        if not hit:
            print("  FAIL: git 이 추적하는 build/ 안의 결함을 못 봤다 — 이름으로 잘라낸 것이다")
            print(f"        조사 {got['inventory']['scanned_files']} file, "
                  f"미선언 {len(got['undeclared'])}건")
            return False

        # (c) git 을 지우면 fallback 이고, 그 사실이 보여야 한다.
        shutil.rmtree(root / ".git")
        fb = run_audit(root)
        if fb["inventory"]["source_selection"] != SELECTION_NAME_FALLBACK:
            print(f"  FAIL: git 없는데 선정이 {fb['inventory']['source_selection']}")
            return False
        if [f for f in fb["undeclared"] if f["path"] == "build/real_source.py"]:
            print("  FAIL: fallback 이 build/ 를 봤다 — 이 case 의 전제가 무너졌다")
            return False

    print("  [info] 저장소는 git 선정 / 추적되는 build/ 의 결함 검출 / "
          "fallback 은 자기가 fallback 임을 밝힌다")
    return True


def _scanned_relpaths(result: dict[str, Any]) -> list[str]:
    """도구가 실제로 연 file 목록. 없으면 이 case 는 성립하지 않는다."""
    paths = result.get("scanned_paths")
    assert paths is not None, "run_audit 이 scanned_paths 를 내지 않는다 — 커버리지 판정 불가"
    return list(paths)


def case_9_cli_runs_green_on_this_repo() -> bool:
    """9) CLI 를 저장소 루트에서 돌리면 exit 0 (실제 invocation 형태)."""
    proc = subprocess.run(
        [sys.executable, str(AUDIT_TOOL), "--repo-root", str(REPO_ROOT)],
        capture_output=True, text=True, timeout=180,
    )
    if proc.returncode != 0:
        print(f"  FAIL: exit {proc.returncode}\n{proc.stdout}\n{proc.stderr[-600:]}")
        return False
    if "결과: OK" not in proc.stdout:
        print(f"  FAIL: 요약 줄 부재 — 출력 형식이 바뀌었나?\n{proc.stdout[-400:]}")
        return False
    print("  [info] CLI exit 0 + '결과: OK'")
    return True


CASES = [
    ("case_1_audit_actually_ran", case_1_audit_actually_ran),
    ("case_2_rules_have_something_to_look_at", case_2_rules_have_something_to_look_at),
    ("case_3_no_undeclared_findings", case_3_no_undeclared_findings),
    ("case_4_ledger_has_no_stale_entries", case_4_ledger_has_no_stale_entries),
    ("case_5_injections_are_caught", case_5_injections_are_caught),
    ("case_6_clean_source_is_not_flagged", case_6_clean_source_is_not_flagged),
    ("case_7_auditor_root_is_not_module_derived", case_7_auditor_root_is_not_module_derived),
    ("case_8_wrong_root_fails_loudly", case_8_wrong_root_fails_loudly),
    ("case_9_cli_runs_green_on_this_repo", case_9_cli_runs_green_on_this_repo),
    ("case_10_scan_covers_every_source_file", case_10_scan_covers_every_source_file),
    ("case_11_generated_is_decided_by_git_not_by_name", case_11_generated_is_decided_by_git_not_by_name),
]


def main() -> int:
    print(f"=== check_root_anchor_audit (v1.0.8, {len(CASES)} case) ===")
    passed = 0
    for name, fn in CASES:
        print(f"\n[{name}]")
        try:
            ok = fn()
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL: 예외 {type(exc).__name__}: {exc}")
            ok = False
        if ok:
            passed += 1
    print(f"\n결과: {passed}/{len(CASES)} PASS")
    return 0 if passed == len(CASES) else 1


# pytest wrapper (TST-WF-01)
def test_case_1_audit_actually_ran() -> None:
    assert case_1_audit_actually_ran()


def test_case_2_rules_have_something_to_look_at() -> None:
    assert case_2_rules_have_something_to_look_at()


def test_case_3_no_undeclared_findings() -> None:
    assert case_3_no_undeclared_findings()


def test_case_4_ledger_has_no_stale_entries() -> None:
    assert case_4_ledger_has_no_stale_entries()


def test_case_5_injections_are_caught() -> None:
    assert case_5_injections_are_caught()


def test_case_6_clean_source_is_not_flagged() -> None:
    assert case_6_clean_source_is_not_flagged()


def test_case_7_auditor_root_is_not_module_derived() -> None:
    assert case_7_auditor_root_is_not_module_derived()


def test_case_8_wrong_root_fails_loudly() -> None:
    assert case_8_wrong_root_fails_loudly()


def test_case_9_cli_runs_green_on_this_repo() -> None:
    assert case_9_cli_runs_green_on_this_repo()


def test_case_10_scan_covers_every_source_file() -> None:
    assert case_10_scan_covers_every_source_file()


def test_case_11_generated_is_decided_by_git_not_by_name() -> None:
    assert case_11_generated_is_decided_by_git_not_by_name()


if __name__ == "__main__":
    sys.exit(main())
