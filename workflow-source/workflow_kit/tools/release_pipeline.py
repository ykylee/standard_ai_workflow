#!/usr/bin/env python3
"""v0.7.9+: standard-ai-workflow release pipeline 정식화 (7 subcommand).

release 절차 (validate → dist → version-bump → note-draft → release → verify → rollback) 의
*기계화 layer*. manual 절차 (docs/RELEASE.md — 채널 정책 정본은 §1) 의 *부족 부분* 자동화.

Phase 1 (v0.7.9): validate / version-bump / note-draft — 사전 점검 + version + note.
Phase 2 (v0.7.10): release / verify / rollback — gh CLI 통합 + read-only verify + destructive rollback.
Phase 3 (v0.7.11): dist — `python3 -m build` wheel + sdist 자동 빌드 (PEP 517/518).
Phase 5 (v0.7.18): release coordination observability — cmd_release 의 --auto-bump
  + remote tag pre-check (`git ls-remote origin`). v0.7.16 의 race lesson 반영.
Phase 6 (v0.13.1+): dashboard post-release emit — gh release create 성공 후
  workflow_kit.workflow_kit_cli --command=dashboard --format=markdown 자동 호출.
  --skip-dashboard-emit 으로 skip, --dashboard-output=PATH 로 경로 override.

본 도구는 어떤 인덱스에도 **업로드하지 않는다** (명령만 출력한다).
업로드 가부는 **docs/RELEASE.md §1 채널 정책** 이 정본이다 — 여기서 규칙을
*재진술하지 않는다*. 사본은 갈라진다: §1 의 TestPyPI 행은 2026-08-13 에 1회 한정
허용으로 열렸다가 2026-08-14 에 다시 닫혔다 (소유자 최종 결정 = PyPI 발행 안 함,
§1 각주 0). 하루 만에 두 번 움직인 값을 주석에 적었다면 바로 거짓이 됐을 것이다.
(v1.2.1: 그 이전 주석은 저장소 밖 agent memory 를 근거로 인용해, 소비자도 새
기여자도 확인할 수 없는 자리에 정책이 있었다.)

Usage:
    # dry-run: 모든 subcommand plan 만 출력
    wk release-pipeline validate --dry-run
    wk release-pipeline version-bump --patch --dry-run
    wk release-pipeline note-draft --from=v0.7.8 --to=v0.7.9 --dry-run

    # apply
    wk release-pipeline version-bump --patch --apply
    wk release-pipeline note-draft --from=v0.7.8 --to=v0.7.9 --apply

    # JSON 출력 (CI integration)
    wk release-pipeline validate --json

Reference:
- workflow_kit/tools/check_packaging.py (packaging 정합성 검증)
- workflow_kit/tools/refresh_wiki_memory.py (v0.7.5, git log → memory emit 패턴)
- workflow_kit.cli.doctor (v0.7.8 state-aware baseline 검증)
- docs/RELEASE.md §1 (release 채널 정책 **정본**: GitHub Releases 만)
- docs/RELEASE.md (수동 release 절차)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
import sys
from datetime import datetime, timezone
from pathlib import Path

# v0.7.15+ atomic_write (POSIX os.replace guarantee)
# workflow-source 를 sys.path 에 추가 (script 가 standalone 으로 실행될 때도
# workflow_kit 모듈이 import 가능하도록). v0.13.2+ 추가.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    from workflow_kit.common.atomic_write import atomic_write_json, atomic_write_text
    from workflow_kit.common.dashboard_data import DRIFT_LEDGER_RELPATH  # v1.0.1+ north-star 원장
    from workflow_kit.common.paths import state_path_for_workspace
    from workflow_kit.common.state.cache import refresh_maturity_last_updated  # v0.14.6+ Task 3 follow-up
except ImportError:
    # standalone script (no workflow_kit on sys.path) — fall back to direct write.
    atomic_write_json = None  # type: ignore[assignment]
    atomic_write_text = None  # type: ignore[assignment]
    refresh_maturity_last_updated = None  # type: ignore[assignment]
    # 원장 경로는 dashboard 와 **같은 문자열이어야** 한다 (writer ↔ reader 정합).
    DRIFT_LEDGER_RELPATH = "ai-workflow/memory/release/drift_ledger.jsonl"
    state_path_for_workspace = None  # type: ignore[assignment]
# 1차 출처
#
# ⚠️ 이름과 달리 **git 저장소 루트가 아니라 `workflow-source/`** 다 (`parents[2]`).
# `pyproject.toml` / `releases/` / `workflow_kit/` 를 여는 데는 이게 맞지만, **git
# 경로 인자와 섞으면 안 된다** — `git status --porcelain` 은 *저장소 루트* 기준
# 경로를 내놓으므로 그걸 `cwd=REPO_ROOT` 에서 `git add` 에 넘기면
# `workflow-source/workflow-source/...` 가 된다 (v1.1.2 release 에서 실제로 터졌다).
# git 경로를 다루는 자리는 `_git_toplevel()` 을 쓴다.
REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"
RELEASES_DIR = REPO_ROOT / "releases"
WORKFLOW_KIT_INIT = REPO_ROOT / "workflow_kit" / "__init__.py"
#: pi.dev 패키지 매니페스트. **저장소 루트**에 산다 (payload 는 `plugin/`).
#: 렌더 대상이 아니라 손으로 유지되는 npm 메타지만(plugin_payload `_PI_STATIC_*`),
#: `version` 만은 kit 을 따라야 한다 — 안 따라가면 갤러리가 낡은 버전을 광고한다
#: (2026-08-30 실측: kit 1.7.0 인데 1.2.0 으로 5개 minor 동안 고착).
PI_PACKAGE_JSON = REPO_ROOT.parent / "plugin" / "package.json"

# (v1.2.0) EXPECTED_SUBPACKAGES 사본은 삭제 — 소비자가 없었고 pyproject
# `packages` 와 이미 갈라져 있었다. packaging 정합은 check_packaging 이 wheel
# 실측으로 판정한다 (REQUIRED_IMPORTS / FORBIDDEN_IMPORTS).

# tomllib (3.11+) / tomli (3.10) 분기
if sys.version_info >= (3, 11):
    import tomllib  # type: ignore[import-not-found]
else:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef, import-not-found]

# ---------------------------------------------------------------------------
# 추출 helper 모듈 재-export (TASK-2026-08-11-main-007)
# ---------------------------------------------------------------------------
# 본 파일은 spec_from_file_location("release_pipeline", path) 로 *package-less*
# 로드되는 경우가 많아 relative import 가 실패한다 → tools/ 를 sys.path 에 올리고
# top-level `import *` 로 재-export 한다. 각 helper 모듈은 underscore 이름까지
# `__all__` 에 명시하므로, 기존 check / caller 는 계속 release_pipeline 의
# attribute (`rp._twine_check`, `rp._parse_git_log` 등) 로 접근할 수 있다.
# helper 모듈은 release_pipeline 을 import 하지 않는다 (순환 금지).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_pipeline_changelog import *  # noqa: E402,F401,F403
from release_pipeline_dist import *  # noqa: E402,F401,F403
from release_pipeline_emit import *  # noqa: E402,F401,F403
from release_pipeline_frontmatter import *  # noqa: E402,F401,F403


# ---------------------------------------------------------------------------
# 1. validate
# ---------------------------------------------------------------------------


#: mypy 의 INTERNAL ERROR 는 **정형 보일러플레이트로 시작**한다 — 안내 문구와
#: 문서 URL 이 먼저 나오고, 정작 쓸모 있는 것(버전, 크래시 지점, traceback)은
#: 그 뒤다. 사유를 앞으로 끌어올리지 않으면 상위 요약이 자를 때 **보일러플레이트만
#: 남는다**. 2026-08-18 사건(run 32094513107)이 정확히 그랬다: stderr 는 잡혔는데
#: CI 요약이 120자에서 잘라 "Please try using mypy master on GitHub" 까지만 남았고,
#: 원인은 아티팩트를 내려받아서야 보였다 (TASK-2026-08-13-main-004 관찰 3차).
_MYPY_BOILERPLATE_MARKERS: tuple[str, ...] = (
    "Please try using mypy master on GitHub",
    "https://mypy.readthedocs.io/en/stable/common_issues.html",
    "report a bug at https://github.com/python/mypy/issues",
    "version: ",
)



def _isolated_mypy_cache_dir() -> str:
    """이 프로세스 전용 mypy 캐시 경로 (TASK-2026-08-24-main-007).

    `--no-incremental` 은 캐시 **읽기**만 끄고 디렉터리는 그대로 만든다. 그래서
    병렬 구간의 mypy 호출들이 같은 cwd 의 `.mypy_cache` 를 두고 경합했고, 관찰
    4차의 트레이스백이 `mypy/build.py:create_metastore` 를 지목했다.

    **빈 문자열(`--cache-dir=`)로는 못 끈다** — 캐시를 *끄는* 것이 아니라 cwd 로
    *옮긴다* (실측: `3.13/cache.*.db` 가 작업 디렉터리에 쏟아진다). 처음에
    `.mypy_cache` 부재만 확인하고 "아무것도 안 만든다" 로 읽어 저장소에 캐시
    db 를 커밋했다 — 기대한 산출물의 부재를 산출물 전체의 부재로 읽은 것이다.

    그래서 **전용 경로**를 준다. 프로세스별로 갈라지므로 병렬에서 부딪히지 않고,
    `TMPDIR` 아래라 러너가 정리한다 (전량 runner 는 `--tmp-dir` 로 실디스크를 준다).
    """
    return str(Path(tempfile.gettempdir()) / f"mypy-cache-{os.getpid()}")

def _mypy_stderr_signal(stderr: str, *, keep: int = 20) -> str:
    """mypy stderr 에서 **신호를 앞으로** 오게 정리한다.

    보일러플레이트를 걷어 낸 줄을 먼저 싣고, 그러고도 남는 자리에 원문 꼬리를
    붙인다. 잘려도 사유가 남는 것이 목적이다.
    """
    lines = [ln for ln in stderr.strip().splitlines() if ln.strip()]
    if not lines:
        return ""
    signal = [
        ln for ln in lines
        if not any(m.lower() in ln.lower() for m in _MYPY_BOILERPLATE_MARKERS)
    ]
    # 보일러플레이트를 다 걷어 내면 아무것도 안 남는 경우가 있다 — 그러면 원문을 쓴다.
    ordered = (signal or lines)[-keep:]
    return "\n".join(ordered)


def _traceback_conclusion_first(text: str, *, keep: int = 20) -> str:
    """트레이스백의 **결론을 맨 앞으로** 올린 꼬리.

    `--show-traceback` 을 준 뒤(관찰 4차) 트레이스백이 드디어 로그에 왔는데,
    step summary 의 `error_excerpt[:800]` 이 그 **꼬리를 잘랐다** — 남은 것은
    `File "mypy/` 까지였고 정작 어느 예외였는지는 사라졌다.

    절단은 언제나 머리를 남긴다. 그런데 트레이스백의 신호는 **꼬리**에 있다
    (마지막 프레임과 예외 줄). 상한을 또 올리는 것은 다음 트레이스백이 더 길어지면
    같은 자리로 돌아온다 — 그래서 **결론을 머리로 옮긴다.** 절단 상한과 무관하게
    "무엇이 터졌나" 가 먼저 보인다.
    """
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return ""
    if not any(ln.startswith("Traceback (most recent call last)") for ln in lines):
        return "\n".join(lines[-keep:])
    # 예외 줄 = 들여쓰기 없는 마지막 줄 (프레임은 두 칸 이상 들여쓴다)
    exception = next(
        (ln for ln in reversed(lines) if ln and not ln.startswith(" ")
         and not ln.startswith("Traceback")),
        lines[-1],
    )
    body = lines[-keep:]
    return "\n".join([f"[exception] {exception}", *body])


def cmd_validate(args) -> dict:
    """4 source 의 release-readiness 검증.

    1. check_packaging.py: pyproject 의 [tool.setuptools.packages] ↔ 디스크 정합
    2. workflow_kit.cli.doctor: 7 baseline 모두 evaluate (state-aware variant)
    3. state.json freshness: v0.7.5+ refresh_wiki_memory 의 last_freeze / last_ingest
    4. git status: working tree clean (release commit 의 clean state 보장)
    5. mypy strict: v0.11.12+ — workflow_kit/ mypy 2.1.0 strict 0 errors 강제
       (CI mypy-strict workflow 와 동일 invocation, release-time gate)
    """
    results: dict = {}

    # 1. check_packaging
    if not args.skip_packaging:
        # v0.11.17 in-scope fix: 부모 process 의 PYTHONPATH (예: `workflow-source`)
        # 가 상속되면, wheel install 의 site-packages/bootstrap_lib 가 shadowing
        # 되어 `No module named 'bootstrap_lib'` 실패. packaging check 는 venv
        # site-packages 만 사용해야 함. doctor/state/git check 는 venv site-packages
        # 만 사용하므로 동일 처리.
        clean_env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "workflow_kit/tools/check_packaging.py")],
            capture_output=True, text=True, timeout=120,
            env=clean_env,
        )
        results["packaging"] = {
            "exit_code": proc.returncode,
            "ok": proc.returncode == 0,
            "last_line": proc.stdout.strip().split("\n")[-1] if proc.stdout else "",
        }
    else:
        results["packaging"] = {"ok": True, "skipped": True}

    # 2. workflow_kit.cli.doctor (v0.7.8)
    if not args.skip_doctor:
        # v1.1.4: baselines 는 project_root 아래에서 `workflow-source/` 를 조립하므로
        # project_root 는 **저장소 루트**(REPO_ROOT.parent)여야 한다. 이전에는
        # REPO_ROOT(= workflow-source/)를 넘겨 tests 탐색이 workflow-source/workflow-source/
        # 로 어긋났고, doctor 는 "0 tests across 0 files" 로 — 아무것도 재지 않은 채 —
        # non_compliant 를 냈다. config 는 저장소 루트가 아니라 workflow-source/pyproject.toml
        # 에 있으므로 --config-path 를 명시한다 (silent default fallback 방지, §2.49).
        # PYTHONPATH 를 명시한다 — 이전에는 caller 환경 상속에 암묵 의존해,
        # PYTHONPATH 없이 부른 caller 에서는 doctor 가 import 단계에서 죽고
        # 게이트는 "실행 못 함" 을 fail 로 보고했다 (fail-closed 는 맞지만 만성).
        # release_pipeline 은 source tree 의 도구이므로 같은 tree 를 재는 것이 맞다.
        doctor_env = {**os.environ}
        doctor_env["PYTHONPATH"] = str(REPO_ROOT) + (
            os.pathsep + doctor_env["PYTHONPATH"] if doctor_env.get("PYTHONPATH") else ""
        )
        proc = subprocess.run(
            [sys.executable, "-m", "workflow_kit.cli.doctor", "--json",
             "--project-root", str(REPO_ROOT.parent),
             "--config-path", str(REPO_ROOT)],
            capture_output=True, text=True, timeout=60,
            env=doctor_env,
        )
        if proc.returncode == 0:
            try:
                doctor_out = json.loads(proc.stdout)
                cs_status = {
                    bl: doctor_out["results"][bl]["status"]
                    for bl in doctor_out["results"]
                }
                non_compliant = [
                    bl for bl, st in cs_status.items() if st == "non_compliant"
                ]
                results["doctor"] = {
                    "ok": len(non_compliant) == 0,
                    "baselines": cs_status,
                    "non_compliant": non_compliant,
                }
            except (json.JSONDecodeError, KeyError) as e:
                results["doctor"] = {"ok": False, "error": str(e)}
        else:
            results["doctor"] = {"ok": False, "exit_code": proc.returncode}
    else:
        results["doctor"] = {"ok": True, "skipped": True}

    # 3. state.json freshness
    if not args.skip_state:
        # 정본 helper 로만 경로를 얻는다 — legacy 문자열 조립은 §2.20 의 재발 경로다.
        state_path = state_path_for_workspace(REPO_ROOT.parent)
        if state_path.exists():
            # v1.1.4: 판정 필드를 현재 writer 의 계약으로 교체. 이전 판정
            # (`memory.last_freeze` 존재) 은 v0.7.x raw-mirror 전용 도구
            # (refresh_wiki_memory.update_state_json) 만 쓰는 필드였고, 현재 정본
            # writer (scripts/generate_workflow_state.py, branch-scoped) 는 그 섹션을
            # 아예 안 쓴다 — reader 만 legacy 에 남아 만성 fail 이던 자리다
            # (state-json silent-failing 과 같은 모양: reader/writer 를 같이 옮겼는지
            # 확인). 현 계약 = top-level `generated_at` stamp. legacy 스키마
            # (`memory.last_freeze` 보유) 도 계속 인정한다.
            try:
                data = json.loads(state_path.read_text())
            except json.JSONDecodeError as e:
                results["state"] = {"ok": False, "error": f"state.json parse: {e}"}
            else:
                generated_at = data.get("generated_at", "")
                last_freeze = data.get("memory", {}).get("last_freeze", "")
                results["state"] = {
                    "ok": bool(generated_at) or bool(last_freeze),
                    "generated_at": generated_at,
                    "last_freeze": last_freeze,
                    "state_path": str(state_path),
                }
        else:
            # state.json 부재도 OK (default empty state 시 v0.7.8 정합).
            # v1.1.7: 어떤 경로를 보고 부재라 판정했는지 함께 보고한다 — 경로는
            # 브랜치 컨텍스트(`CODEX_WORKFLOW_BRANCH`)에 따라 달라지므로, 이것이
            # 없으면 "왜 absent 인지" 를 호출자가 알 수 없다 (실제로 CI slash job
            # 진단을 어렵게 만든 자리다).
            results["state"] = {"ok": True, "absent": True, "state_path": str(state_path)}
    else:
        results["state"] = {"ok": True, "skipped": True}

    # 4. git status
    if not args.skip_git:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10,
        )
        clean = proc.stdout.strip() == ""
        results["git"] = {
            "ok": clean,
            "untracked_or_modified": proc.stdout.strip().split("\n") if not clean else [],
        }
    else:
        results["git"] = {"ok": True, "skipped": True}

    # 5. mypy strict (v0.11.12+ — release-time gate, CI mypy-strict workflow 의 local mirror)
    # v0.11.10 의 FULL mypy strict 도달 (35 file strict clean) 을 release-time 강제.
    # CI (.github/workflows/mypy-strict.yml) 가 PR-time 방어선이라면, 본 check 는
    # release-time 방어선. invocation 은 CI 와 동일:
    #   `mypy --no-incremental --config-file <workflow-source/pyproject.toml> workflow_kit/`
    #   (cwd = parent_of_REPO_ROOT, 절대경로)
    #
    # v1.0.2 — **이 gate 도 strict 로 돈 적이 없다.** cwd 가 project root 인데 그곳의
    # pyproject.toml 은 의도된 root-level placeholder scaffold (eb62f37) 라
    # [tool.mypy] 가 없어, mypy 가 config 탐색을
    # 모두 건너뛰고 `Config File: Default` 로 떨어졌다. CI 와 **똑같은 결함을 복제**하고
    # 있었다 — 규약을 세 곳에 사본으로 두면 갈라지는 게 아니라 같이 틀린다.
    # (이전 주석의 "sub-package config 와의 merge 회피" 는 사실이 아니다. mypy 는 config 를
    #  merge 하지 않고 정확히 하나만 고른다.)
    #
    # REPO_ROOT = workflow-source/ (release_pipeline.py 의 Path.__file__.parents[1] 정의)
    # 이므로, *project root* (REPO_ROOT.parent) 를 cwd 로 사용하고, target 을 절대경로.
    if not getattr(args, "skip_mypy", False):
        try:
            mypy_target = str(REPO_ROOT / "workflow_kit/")
            mypy_config = str(REPO_ROOT / "pyproject.toml")
            # `--cache-dir=`(빈 값): 캐시 디렉터리를 **아예 만들지 않는다**.
            # `--no-incremental` 은 캐시 **읽기**만 끄고 `.mypy_cache` 는 그대로
            # 만든다 (실측 2026-08-24) — 그래서 병렬 구간의 mypy 호출 6곳이 같은
            # cwd 의 같은 디렉터리를 두고 경합했고, 관찰 4차의 트레이스백이
            # `mypy/build.py:create_metastore` 를 지목했다. 읽지 않는 캐시를 만들
            # 이유가 없으므로 만들지 않는 편이 엄격히 낫다 (판정 동일 실측:
            # 양쪽 모두 `199 source files`).
            #
            # `--show-traceback`: mypy 는 **내부 오류일 때만** 트레이스백을 찍으므로
            # 정상 경로 비용이 0 이다. 없을 때 무슨 일이 났는지 4차까지 몰랐다 —
            # 게이트가 `exit 2 / error_count 0` 을 내고 stderr 에는 mypy 가
            # *"please use --show-traceback"* 이라고 **요청하는 문구만** 남았다.
            # 그 요청을 로그로 옮겨 놓고 정작 플래그를 준 적이 없어서, 완료 기준
            # ("다음 재발이 트레이스백을 남긴다")이 원리적으로 충족될 수 없었다
            # (TASK-2026-08-13-main-004 관찰 4차, 2026-08-24).
            mypy_proc = subprocess.run(
                [sys.executable, "-m", "mypy", "--no-incremental", "--cache-dir", _isolated_mypy_cache_dir(), "--show-traceback",
                 "--config-file", mypy_config, mypy_target],
                cwd=str(REPO_ROOT.parent), capture_output=True, text=True, timeout=120,
            )
            # error count: lines like "file.py:LINE: error: ... [rule]"
            error_lines = [
                line for line in mypy_proc.stdout.splitlines()
                if ".py:" in line and "error:" in line
            ]
            first_error = error_lines[0] if error_lines else None
            # v1.0.2: 판정과 함께 **어떤 config 로 쟀는지**를 낸다 (d5be282 와 같은 원칙).
            # 이 값이 없어서 "strict 0 errors" 라는 판정이 무엇을 근거로 한 것인지
            # 아무도 확인할 수 없었다.
            results["mypy"] = {
                "ok": mypy_proc.returncode == 0,
                "exit_code": mypy_proc.returncode,
                "error_count": len(error_lines),
                "first_error": first_error,
                "config_file": mypy_config,
            }
            if mypy_proc.returncode != 0 and not error_lines:
                # **exit != 0 인데 셀 오류가 0건** — mypy 의 blocking error 다 (exit 2).
                # 그 사유는 stderr 로 나오고 위 필터(`.py:` + `error:`)에 안 걸리므로,
                # 담지 않으면 판정 결과가 `0 errors 인데 실패` 한 줄로 남아 **진단이
                # 불가능**해진다. 실제로 그 모양의 flake 가 4번 터지는 동안(2026-08-11~13)
                # 원인을 좁히지 못했다 (TASK-2026-08-13-main-004). CI 로그는 만료되고
                # annotation 에는 검사 이름도 안 실린다 — 증거를 여기서 들고 있어야 한다.
                results["mypy"]["stderr_tail"] = _mypy_stderr_signal(mypy_proc.stderr)
                # `--show-traceback` 은 트레이스백을 **stdout** 으로 낸다 (관찰 4차 실측).
                results["mypy"]["stdout_tail"] = _traceback_conclusion_first(
                    mypy_proc.stdout
                )
            # v1.1.4: `-m mypy` 는 모듈 부재 시 FileNotFoundError 가 아니라
            # rc 1 + stderr 로 죽는다 — 아래 except 분기는 이 호출 형태에서는
            # 절대 타지 않았고, "mypy 가 오류를 찾음" 과 "mypy 실행 불가" 가
            # 같은 모양(ok False, error_count 0)이 됐다. 판정은 그대로 fail
            # (실행 못 한 검사는 통과가 아니다) — 출처만 구분해 보고한다.
            if mypy_proc.returncode != 0 and "No module named mypy" in mypy_proc.stderr:
                results["mypy"]["error"] = (
                    "mypy unavailable in this interpreter (No module named mypy) — "
                    "venv 에서 실행하거나 `pip install -e ./workflow-source[dev]`"
                )
        except FileNotFoundError:
            # mypy module 부재 — dev extra install 누락. v0.11.11 pin 정합 이지만
            # 환경 문제 가능. hard fail (gate 가 무효 = release 정지).
            results["mypy"] = {
                "ok": False,
                # v1.0.2: sub-package pyproject 제거에 따라 정본 배포판으로 교정.
                "error": "mypy module not installed (run `pip install -e ./workflow-source[dev]`)",
            }
        except subprocess.TimeoutExpired:
            results["mypy"] = {"ok": False, "error": "mypy timeout (>120s)"}
    else:
        results["mypy"] = {"ok": True, "skipped": True}

    # 6. 플러그인 산출물 정합 (P4, TASK-2026-08-12-main-017)
    # manifest 3장이 pyproject version 을 **복사해 담는다** — 어긋난 채 릴리스하면
    # marketplace 가 낡은 버전을 광고한다 (v1.1.7 stamp 누락 동형).
    #
    # 여기가 강제 지점인 이유: bump 가 부수효과로 재생성하게 짰더니, 원본 저장소에서
    # bump 를 apply 했다 되돌리는 릴리스 검사들이 pyproject 만 복원하고 manifest 는
    # 낡은 채 남겼다 (실측). 그래서 `state.json` 과 같은 규율로 바꿨다 — **생성물은
    # 사람이 명령으로 재생성하고, 게이트가 정합을 강제한다.** 실패 시 `fix` 에 그
    # 명령이 담긴다.
    if not getattr(args, "skip_plugin_payload", False):
        status = plugin_payload_status(read_workflow_kit_version())
        results["plugin_payload"] = {
            "ok": bool(status.get("ok")) and bool(status.get("in_sync")),
            **{k: v for k, v in status.items() if k != "ok"},
        }
    else:
        results["plugin_payload"] = {"ok": True, "skipped": True}

    return results


# ---------------------------------------------------------------------------
# 1.4 mypy CI cross-verify (v0.11.13+ — Layer 1 CI ↔ Layer 2 local mypy gate 정합)
# ---------------------------------------------------------------------------


#: 발행을 막을 수 있는 **필수 CI 워크플로**. 이 목록에 있는 것이 HEAD sha 에서
#: green 이 아니면 `release --apply` 가 멈춘다 (v1.8.1, TASK-2026-09-01-main-005).
#:
#: ## 왜 목록이 필요한가
#:
#: 이전에는 발행 게이트가 `mypy-strict.yml` **하나만** 조회했고 그마저 advisory 였다.
#: 그래서 `smoke` 가 2026-08-30 `6d9ad763` 부터 **10 커밋 연속 red** 인 동안
#: 게이트는 내내 green 을 봤고, **v1.8.0 이 그 위에서 발행됐다** (발행 커밋
#: `6c495e61` 실측: smoke=failure, mypy-strict=success).
#:
#: 뿌리는 설계의 분업이었다 — 릴리스 노트의 `누적 smoke N/N PASS` 는 **사람의 주장**
#: 이고(`verify_release_note_smoke_count` 주석이 그렇게 적는다), 그 주장을 CI 와
#: 대조하는 자리가 없었다. 이제 여기가 그 자리다.
#:
#: ## 목록에 넣는 기준
#:
#: **소비자에게 나가는 산출물의 정확성을 재는 축**만 넣는다. 문서 사이트(`mkdocs`)나
#: 워크플로 문법(`actionlint`) 이 red 라고 발행을 막으면, 막을 이유가 없는 것이
#: 막혀 사람이 escape hatch 를 습관적으로 쓰게 된다 — 그러면 게이트가 다시 없어진다.
REQUIRED_CI_WORKFLOWS: tuple[str, ...] = (
    "smoke",           # 전량 검사 2축 (native / slash)
    "mypy-strict",     # 타입 게이트
    "os-matrix",       # 크로스 OS
    "mcp-sdk-matrix",  # MCP SDK 버전 매트릭스
)


def _fetch_ci_runs_for_sha(sha: str, *, repo: str, timeout: int = 20) -> tuple[list[dict], str | None]:
    """HEAD sha 의 워크플로 run 목록. ``(runs, error)``.

    `--commit` 으로 **sha 를 직접 지정**한다. 이전 구현은 `--limit 1` 로 최신 run 을
    집었는데, HEAD 의 run 이 아직 없으면 **이전 커밋의 run** 을 보게 되고 브랜치
    필터도 없었다.
    """
    try:
        proc = subprocess.run(
            ["gh", "run", "list", "--repo", repo, "--commit", sha, "--limit", "50",
             "--json", "name,conclusion,status,databaseId,url"],
            cwd=str(REPO_ROOT.parent), capture_output=True, text=True, timeout=timeout,
        )
    except FileNotFoundError:
        return [], "gh CLI not found"
    except subprocess.TimeoutExpired:
        return [], f"gh run list timeout (>{timeout}s)"
    if proc.returncode != 0:
        return [], f"gh run list failed (exit={proc.returncode}): {proc.stderr.strip()[:200]}"
    try:
        return json.loads(proc.stdout), None
    except json.JSONDecodeError as exc:
        return [], f"gh run list JSON parse error: {exc}"


def verify_required_ci(
    *, head_sha: str | None = None, repo: str | None = None,
    runs: list[dict] | None = None, fetch_error: str | None = None,
) -> dict:
    """필수 워크플로가 **이 커밋에서** 전부 green 인가. 발행 차단 판정.

    `runs` / `fetch_error` 를 주입하면 네트워크 없이 판정만 잰다 (검사용).

    워크플로별 상태:
      - ``success``  : green
      - ``missing``  : 이 sha 에 run 이 없다 (아직 안 돌았거나 트리거 안 됨)
      - ``pending``  : 아직 도는 중
      - ``failure``  : red (conclusion 이 success 가 아닌 모든 완료 상태)

    `success` 가 아닌 것이 하나라도 있으면 ``ok=False`` 다. **모름은 통과가 아니다** —
    run 이 없거나 gh 를 못 부른 것도 막는다. 못 잰 것을 green 으로 세면 이 게이트는
    있으나 마나다 (그것이 정확히 v1.8.0 에서 일어난 일이다).
    """
    if runs is None and fetch_error is None:
        if head_sha is None:
            proc = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(REPO_ROOT.parent), capture_output=True, text=True, timeout=5,
            )
            head_sha = proc.stdout.strip() if proc.returncode == 0 else None
        if not head_sha:
            return {
                "ok": False, "head_sha": None, "workflows": {},
                "blocking": list(REQUIRED_CI_WORKFLOWS),
                "error": "HEAD sha 를 읽지 못했다",
                "required": list(REQUIRED_CI_WORKFLOWS),
            }
        runs, fetch_error = _fetch_ci_runs_for_sha(head_sha, repo=repo or _get_repo())

    if fetch_error:
        return {
            "ok": False, "head_sha": head_sha, "workflows": {},
            "blocking": list(REQUIRED_CI_WORKFLOWS),
            "error": f"CI 결과를 못 읽었다 — {fetch_error}",
            "required": list(REQUIRED_CI_WORKFLOWS),
        }

    by_name: dict[str, dict] = {}
    for run in runs or []:
        name = run.get("name")
        if name in REQUIRED_CI_WORKFLOWS and name not in by_name:
            by_name[name] = run  # gh 는 최신순이므로 첫 항목이 최신이다

    workflows: dict[str, str] = {}
    blocking: list[str] = []
    for name in REQUIRED_CI_WORKFLOWS:
        run = by_name.get(name)
        if run is None:
            state = "missing"
        elif run.get("status") != "completed":
            state = "pending"
        elif run.get("conclusion") == "success":
            state = "success"
        else:
            state = "failure"
        workflows[name] = state
        if state != "success":
            blocking.append(name)

    return {
        "ok": not blocking,
        "head_sha": head_sha,
        "required": list(REQUIRED_CI_WORKFLOWS),
        "workflows": workflows,
        "blocking": blocking,
        "error": None if not blocking else (
            "필수 CI 워크플로가 green 이 아니다: "
            + ", ".join(f"{n}={workflows[n]}" for n in blocking)
        ),
    }


def _cross_verify_ci_mypy(*, timeout: int = 15) -> dict:
    """GH Actions mypy-strict workflow 의 last run 결과 와 local HEAD sha 비교.

    Layer 1 (CI, v0.11.11+) 와 Layer 2 (release-time gate, v0.11.12+) 의 정합 verify.
    verdict:
      - "sanity": CI success + local mypy 정합 (default, release 진행)
      - "drift_warning": CI success 인데 local fail (local drift, advisory)
      - "ci_stale": CI success 인데 headSha != HEAD (re-run 권고, advisory)
      - "ci_fail": CI failure (advisory)
      - "absent": gh CLI 성공 / no run found (advisory)
      - "skipped": gh CLI 부재 / error (advisory)

    Returns:
        {
            "verdict": str,
            "ci_run": dict | None,  # {databaseId, conclusion, headSha, event, status, createdAt, url}
            "head_sha": str | None,
            "head_sha_match": bool | None,
            "message": str,
        }
    """
    head_sha_proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(REPO_ROOT.parent), capture_output=True, text=True, timeout=5,
    )
    head_sha = head_sha_proc.stdout.strip() if head_sha_proc.returncode == 0 else None

    try:
        gh_proc = subprocess.run(
            ["gh", "run", "list", "--repo", "ykylee/standard_ai_workflow",
             "--workflow", "mypy-strict.yml", "--limit", "1",
             "--json", "databaseId,conclusion,headSha,event,status,createdAt,url"],
            cwd=str(REPO_ROOT.parent), capture_output=True, text=True, timeout=timeout,
        )
    except FileNotFoundError:
        return {
            "verdict": "skipped",
            "ci_run": None,
            "head_sha": head_sha,
            "head_sha_match": None,
            "message": "gh CLI not found (skip cross-verify)",
        }
    except subprocess.TimeoutExpired:
        return {
            "verdict": "skipped",
            "ci_run": None,
            "head_sha": head_sha,
            "head_sha_match": None,
            "message": f"gh run list timeout (>{timeout}s)",
        }

    if gh_proc.returncode != 0:
        return {
            "verdict": "skipped",
            "ci_run": None,
            "head_sha": head_sha,
            "head_sha_match": None,
            "message": f"gh run list failed (exit={gh_proc.returncode}): {gh_proc.stderr.strip()[:200]}",
        }

    try:
        runs = json.loads(gh_proc.stdout)
    except json.JSONDecodeError as e:
        return {
            "verdict": "skipped",
            "ci_run": None,
            "head_sha": head_sha,
            "head_sha_match": None,
            "message": f"gh run list JSON parse error: {e}",
        }

    if not runs:
        return {
            "verdict": "absent",
            "ci_run": None,
            "head_sha": head_sha,
            "head_sha_match": None,
            "message": "no mypy-strict CI run found",
        }

    last_run = runs[0]
    ci_conclusion = last_run.get("conclusion")
    ci_head_sha = last_run.get("headSha")
    head_sha_match = (ci_head_sha == head_sha) if (ci_head_sha and head_sha) else None

    # verdict 결정 (Layer 1 CI ↔ Layer 2 local mypy 정합)
    # caller 가 별도로 local_mypy_ok / local_mypy_status 를 inject 해서
    # drift_warning / no_local_verify verdict 결정. 여기서는 CI-only verdict 반환.
    if ci_conclusion == "success":
        if head_sha_match is False:
            verdict = "ci_stale"
            message = (
                f"CI success for headSha={ci_head_sha[:7]}, "
                f"but local HEAD={head_sha[:7]} — re-run recommended"
            )
        else:
            verdict = "ci_sanity"
            message = (
                f"CI success for headSha={ci_head_sha[:7]} (matches local HEAD) — "
                f"local mypy 정합 verify 는 caller 가 verdict 결정"
            )
    elif ci_conclusion == "failure":
        verdict = "ci_fail"
        message = (
            f"CI failure for headSha={ci_head_sha[:7] if ci_head_sha else '?'}, "
            f"databaseId={last_run.get('databaseId')}"
        )
    else:
        verdict = "absent"
        message = (
            f"CI status {ci_conclusion!r} (not success/failure) for headSha={ci_head_sha[:7] if ci_head_sha else '?'}"
        )

    return {
        "verdict": verdict,
        "ci_run": last_run,
        "head_sha": head_sha,
        "head_sha_match": head_sha_match,
        "message": message,
    }


def _resolve_cross_verify_verdict(ci_mypy: dict, local_mypy: dict) -> str:
    """_cross_verify_ci_mypy 의 ci-only verdict 를 *local mypy* 와 결합하여 final verdict 결정.

    Verdict matrix:
      | CI verdict   | local mypy ok | local status | final verdict      |
      |--------------|---------------|--------------|--------------------|
      | ci_sanity    | True          | checked      | sanity             |
      | ci_sanity    | False         | checked      | drift_warning      |
      | ci_sanity    | N/A           | skipped      | no_local_verify    |
      | ci_stale     | (any)         | (any)        | ci_stale           |
      | ci_fail      | (any)         | (any)        | ci_fail            |
      | absent       | (any)         | (any)        | absent             |
      | skipped      | (any)         | (any)        | skipped            |
    """
    ci_verdict = ci_mypy.get("verdict")
    if ci_verdict != "ci_sanity":
        return ci_verdict or "absent"
    # ci_sanity 인 경우에만 local mypy 와 cross-verify
    # local_mypy 가 비어있거나 (--skip-validate) skipped 면 no_local_verify
    if not local_mypy or local_mypy.get("skipped"):
        return "no_local_verify"
    if local_mypy.get("ok"):
        return "sanity"
    return "drift_warning"


def _attach_release_summary(results: dict) -> dict:
    """results dict 에 v0.11.15+ 1-line summary 추가. 모든 return point 에서 호출.

    summary format: `ci_mypy=<verdict>, local_mypy=<ok|FAIL|skipped>,
    ready=<true|false>, next=<X.Y.Z|->, error=<error message or ok>`

    `cmd_release --json | jq -r '.summary'` 로 *1-line grep / pipe 가능*.
    """
    ci_verdict = results.get("ci_mypy", {}).get("verdict", "skipped")
    # local mypy 조회: pre_check.mypy (validate 활성 시) 또는 ci_mypy.local_mypy (cross-verify)
    local_mypy = results.get("pre_check", {}).get("mypy", {})
    if not local_mypy:
        # pre_check 가 비어있거나 mypy source 부재 (--skip-validate or --skip-mypy)
        local_mypy = results.get("ci_mypy", {}).get("local_mypy", {})
    if not local_mypy:
        # 둘 다 부재 → skipped (--skip-validate or mypy source 부재)
        local_str = "skipped"
    elif local_mypy.get("skipped"):
        local_str = "skipped"
    elif local_mypy.get("ok"):
        local_str = "ok"
    else:
        local_str = "FAIL"
    # ready_to_release (Layer 1 sanity + Layer 2 ok + tag mismatch X)
    if not results.get("error"):
        # success path: error 부재 + ci sanity
        if ci_verdict in ("sanity", "ci_sanity", "no_local_verify", "absent", "skipped") and local_str == "ok":
            ready = "true"
        else:
            ready = "false"
    else:
        ready = "false"
    # next version (version_source 또는 cli flag) — version_source 는 source label (cli-flag,
    # auto-bump, pyproject.toml) 이고 실제 version 은 다른 field. pyproject.toml 의 경우
    # read_version() 으로 읽은 값이지만, results 에는 source label 만 남는다.
    next_v = results.get("version") or results.get("version_source", "-")
    if next_v == "auto-bump" or next_v == "full-auto-bump":
        next_v = results.get("auto_bump", {}).get("next", "-")
    # version_source 가 label 이면 raw version 으로 fallback (없으면 label 유지)
    if next_v in ("cli-flag", "pyproject.toml", "auto-bump", "full-auto-bump"):
        # next_v 가 label 이면 results["error"] 부재 시엔 tag/version 표시, 있으면 "-"
        next_v = "-"
    err = results.get("error", "ok")
    summary = (
        f"ci_mypy={ci_verdict}, "
        f"local_mypy={local_str}, "
        f"ready={ready}, "
        f"next={next_v}, "
        f"error={err if isinstance(err, str) else 'ok'}"
    )
    results["summary"] = summary
    return results


# ---------------------------------------------------------------------------
# 1.5 release coordination observability (v0.7.18+)
# ---------------------------------------------------------------------------


def _check_remote_tag(tag: str, *, timeout: int = 15) -> dict:
    """원격 (origin) 에 주어진 tag 가 존재하는지 확인.

    Returns:
        {"exists": bool, "remote_url": str | None, "tag": str}
    """
    result: dict = {"exists": False, "remote_url": None, "tag": tag}
    # 1. remote URL 추출
    remote_proc = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=timeout,
    )
    if remote_proc.returncode != 0:
        return result
    result["remote_url"] = remote_proc.stdout.strip()
    # 2. ls-remote 로 tag 조회
    ls_proc = subprocess.run(
        ["git", "ls-remote", "origin", f"refs/tags/{tag}"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=timeout,
    )
    if ls_proc.returncode == 0 and ls_proc.stdout.strip():
        result["exists"] = True
    return result


def _list_remote_tags(pattern: str = "v*", *, timeout: int = 15) -> list[str]:
    """원격의 tag list (정규식 filter, sort -V)."""
    ls_proc = subprocess.run(
        ["git", "ls-remote", "--tags", "origin", pattern],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=timeout,
    )
    if ls_proc.returncode != 0:
        return []
    tags = []
    for line in ls_proc.stdout.strip().splitlines():
        # line: "<sha>\trefs/tags/<tagname>"
        parts = line.split("\t", 1)
        if len(parts) == 2:
            tag = parts[1].removeprefix("refs/tags/")
            # peel 된 ^{} tag 제외
            if not tag.endswith("^{}"):
                tags.append(tag)
    return sorted(tags, key=_version_sort_key)


def _version_sort_key(tag: str) -> tuple:
    """PEP 440 + suffix sort key. v0.7.17-beta → (0, 7, 17, 'beta'), v0.7.18 → (0, 7, 18, '').

    SemVer-ish + PEP 440 suffix 순서 (release < alpha < beta < rc). 정수 tuple 이므로
    `sorted(tags, key=_version_sort_key)` 가 *자동으로* numeric + suffix 순서.
    """
    # 'v' prefix 제거
    s = tag.lstrip("v")
    # '-suffix' 분리
    if "-" in s:
        base, suffix = s.split("-", 1)
    else:
        base, suffix = s, ""
    # base = 'X.Y.Z' → int tuple
    parts = base.split(".")
    nums = tuple(int(p) for p in parts if p.isdigit())
    # suffix sort: '' (release) < 'alpha' < 'beta' < 'rc'
    suffix_order = {"": 0, "alpha": 1, "beta": 2, "rc": 3}
    suffix_rank = suffix_order.get(suffix.split(".")[0], 99)
    return nums + (suffix_rank, suffix)


def next_available_version(local_version: str, *, remote_tags: list[str] | None = None) -> dict:
    """local_version 보다 큰, remote 에 없는 다음 version 결정.

    1차 출처: remote `git ls-remote --tags origin "vX.Y.*"` 의 latest + 0.0.1 bump.
    local_version 이 이미 remote 의 latest 보다 크면 그대로 (충돌 없음).
    같은 major.minor prefix 의 모든 tag → max + 0.0.1.

    Args:
        local_version: 현재 local pyproject 의 version (e.g. "0.7.17").
        remote_tags: pre-fetched list. None 이면 _list_remote_tags() 호출.

    Returns:
        {"next": "0.7.18", "current_local": "0.7.17", "remote_max": "0.7.17-beta", "bumped": True}
    """
    if remote_tags is None:
        remote_tags = _list_remote_tags()
    # local_version 의 major.minor prefix
    parts = local_version.split(".")
    if len(parts) < 2:
        major_minor_prefix = local_version
    else:
        major_minor_prefix = ".".join(parts[:2])
    # remote 의 같은 major.minor 의 tag 만 filter
    prefix = f"v{major_minor_prefix}."
    same_prefix = [t for t in remote_tags if t.startswith(prefix)]
    # numeric base 비교 (PEP 440 suffix 무시)
    def base_tuple(t: str) -> tuple:
        b = t.lstrip("v").split("-", 1)[0]
        try:
            return tuple(int(p) for p in b.split("."))
        except ValueError:
            return (0,)
    if same_prefix:
        remote_max = max(same_prefix, key=base_tuple)
    else:
        remote_max = None
    local_tuple = base_tuple(f"v{local_version}")
    if remote_max is None:
        # remote 에 같은 major.minor 부재 → local 그대로 (다음 patch 가 local 의 +1)
        next_v = local_version
        bumped = False
    else:
        remote_tuple = base_tuple(remote_max)
        if local_tuple > remote_tuple:
            # local 이 remote max 보다 큼 → 그대로
            next_v = local_version
            bumped = False
        elif local_tuple < remote_tuple:
            # local 이 remote max 보다 작음 → remote max + 0.0.1
            next_tuple = list(remote_tuple)
            next_tuple[-1] += 1
            next_v = ".".join(str(n) for n in next_tuple)
            bumped = True
        else:
            # local == remote max → patch bump
            next_tuple = list(remote_tuple)
            next_tuple[-1] += 1
            next_v = ".".join(str(n) for n in next_tuple)
            bumped = True
    return {
        "next": next_v,
        "current_local": local_version,
        "remote_max": remote_max,
        "bumped": bumped,
    }


# ---------------------------------------------------------------------------
# 2. version-bump
# ---------------------------------------------------------------------------


def read_version() -> str:
    """pyproject.toml 의 [project] version 읽기."""
    with PYPROJECT.open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def write_version(new_version: str) -> None:
    """pyproject.toml 의 [project] version 갱신."""
    text = PYPROJECT.read_text()
    text = re.sub(
        r'(version\s*=\s*)"[\d.]+([^"]*)"',
        rf'\1"{new_version}\2"',
        text,
        count=1,
    )
    PYPROJECT.write_text(text)


def read_workflow_kit_version() -> str:
    """workflow_kit.__version__ 읽기. e.g. 'v0.7.13-beta'.

    v0.8.0+: SSOT = pyproject.toml [project] version (spec §4.3).
    workflow_kit/__init__.py 의 __version__ 은 runtime 에서 pyproject.toml 을 parse 해서
    compute 하므로, 본 함수도 동일한 SSOT 에서 직접 compute.

    v1.2.1 (TASK-2026-08-13-main-007): stable 정리로 포맷이 PEP 440 그대로가 됐다
    (`1.2.1`). git tag 만 관례대로 `v` 접두사를 붙인다.
    """
    return read_version()


def write_workflow_kit_version(new_version: str, *, suffix: str = "-beta") -> str:
    """workflow_kit.__version__ 갱신.

    v0.8.0+: SSOT = pyproject.toml [project] version. workflow_kit/__init__.py 는 runtime
    compute 이므로 pyproject.toml 만 갱신하면 됨. __init__.py 의 literal fallback 도
    정합성 위해 함께 갱신 (spec §4.3 loud fallback chain).

    e.g. new_version='0.8.1' → pyproject.toml version 0.8.1, __init__.py fallback
    "v0.8.1-beta". __init__.py 의 SSOT compute (f"v{version}-beta") 가 pyproject 을
    parse 해서 같은 값을 return.
    """
    write_version(new_version)
    # __init__.py 의 literal fallback (loud fallback chain 의 3번째) 도 정합성 유지.
    # suffix 가 "" 이면 그냥 "v{version}", 그 외는 "v{version}{suffix}" (suffix 가 이미 -beta 같은 suffix 포함).
    # v0.11.22 → 0.11.23 사이에서 suffix 이중 처리 (v0.11.23-beta-beta) bug fix.
    text = WORKFLOW_KIT_INIT.read_text()
    replacement = f'{new_version}{suffix or ""}'
    # v1.2.1: literal 이 `return "1.2.1"` 형태다. `v?` 로 구 포맷도 받아 마이그레이션.
    new_text, n = re.subn(
        r'(return\s+")v?\d+\.\d+(?:\.\d+)?(?:[-+][a-zA-Z0-9.]+)?(")',
        rf'\g<1>{replacement}\g<2>',
        text,
    )
    if n == 0:
        # v1.2.1 (TASK-2026-08-13-main-007): 이전에는 여기서 **조용히 넘어갔다**.
        # 포맷이 바뀌어 regex 가 빗나가면 loud fallback 이 낡은 채 남는데도
        # 호출자는 "갱신했다" 는 값을 돌려받았다 — 실행 못 한 갱신은 성공이 아니다.
        raise RuntimeError(
            f"loud fallback literal 을 {WORKFLOW_KIT_INIT} 에서 찾지 못했다 "
            f"(포맷이 바뀌었는가?). 갱신하지 못한 채 성공을 보고할 수 없다."
        )
    WORKFLOW_KIT_INIT.write_text(new_text)
    write_pi_package_version(new_version)
    return f"{new_version}{suffix or ''}"


def write_pi_package_version(new_version: str) -> None:
    """pi.dev 패키지 매니페스트의 ``version`` 을 kit 버전으로 맞춘다.

    이 파일은 byte 대조 대상이 아니다 (npm 메타라 손으로 유지한다). 그래서
    **버전만** 여기서 따라가게 한다. 파일이 없으면 조용히 넘어가지 않는다 —
    갱신하지 못한 것을 성공으로 보고하면 다음 발행이 낡은 버전을 광고한다.
    """
    if not PI_PACKAGE_JSON.is_file():
        raise RuntimeError(
            f"pi 패키지 매니페스트를 찾지 못했다: {PI_PACKAGE_JSON}. "
            "갱신하지 못한 채 성공을 보고할 수 없다."
        )
    text = PI_PACKAGE_JSON.read_text(encoding="utf-8")
    new_text, n = re.subn(
        r'("version"\s*:\s*")[^"]+(")', rf'\g<1>{new_version}\g<2>', text, count=1)
    if n == 0:
        raise RuntimeError(
            f'{PI_PACKAGE_JSON} 에서 "version" 필드를 찾지 못했다 (포맷이 바뀌었는가?). '
            "갱신하지 못한 채 성공을 보고할 수 없다."
        )
    PI_PACKAGE_JSON.write_text(new_text, encoding="utf-8")

def plugin_payload_status(version_label: str, *, repo_root: Path | None = None) -> dict:
    """플러그인 산출물이 주어진 버전과 정합인지 **판정만** 한다. 쓰지 않는다.

    bump 는 pyproject 만 고치는데 플러그인 manifest 3장은 그 버전을 **복사해
    담는다** — 어긋난 채 릴리스하면 marketplace 가 낡은 버전을 광고한다. v1.1.7 의
    RELEASE.md stamp 누락과 같은 계열이다.

    **왜 자동으로 쓰지 않는가** (소유자 판정, 2026-08-12): 처음에는 bump 가 곧바로
    재생성하게 짰는데, 그 설계가 이 저장소와 충돌한다. 릴리스 검사 여럿이 *원본
    저장소*에서 bump 를 apply 한 뒤 되돌리는데 (실측: `pyproject.toml` 이 1.1.8 →
    1.1.9 → 1.1.8 로 86ms 만에 왕복), 그 복원 로직은 플러그인 산출물을 모른다.
    그래서 pyproject 는 제자리로 오는데 **manifest 3장만 낡은 채 남는다** — 전량
    검사가 매번 FAIL 했다. 부수효과로 파일을 쓰는 대신, `state.json` 과 같은 규율을
    쓴다: **생성물은 사람이 명령으로 재생성하고, 게이트가 정합을 강제한다.**

    판정 대상 트리는 **이 파이프라인이 실제로 다루는 트리**다 (``REPO_ROOT.parent``).
    ``plugin_payload.default_repo_root()`` 를 쓰면 안 된다 — 그건 *모듈이 로드된
    위치*라 사본과 원본을 못 가른다 (sandbox 실행이 원본을 가리키는 사고를 실제로
    냈다).

    Args:
        version_label: 정합 기준 버전 문자열 (``v`` 접두 포함, 예 ``v1.1.9-beta``).
        repo_root: 판정할 저장소 루트. 기본값은 이 파이프라인의 작업 대상 트리.

    Returns:
        ``{"ok": bool, "in_sync": bool, "version": str, "repo_root": str,
          "drifted": [상대경로], "drifted_count": int, "fix": "<재생성 명령>"}``
    """
    fix_cmd = "python3 -m workflow_kit.plugin_payload --apply"
    try:
        from workflow_kit.plugin_payload import (
            diff_repo_plugin_files,
            render_repo_plugin_files,
        )
    except Exception as e:  # noqa: BLE001 - 플러그인 모듈 부재는 릴리스를 막지 않는다
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "version": version_label}

    try:
        root = Path(repo_root) if repo_root is not None else REPO_ROOT.parent
        drifted = diff_repo_plugin_files(root, render_repo_plugin_files(version=version_label))
        return {
            "ok": True,
            "in_sync": not drifted,
            "version": version_label,
            "repo_root": str(root),
            "drifted": drifted,
            "drifted_count": len(drifted),
            "fix": fix_cmd,
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "version": version_label}


def bump_version(version: str, *, patch: bool = False, minor: bool = False, major: bool = False, to: str | None = None) -> str:
    """version bump.

    --to=... 명시 시 그대로 사용. 아니면 --major/--minor/--patch 중 1개 (default: --patch).
    """
    if to is not None:
        return to
    major_n, minor_n, patch_n = parse_version(version)
    if major:
        return f"{major_n + 1}.0.0"
    if minor:
        return f"{major_n}.{minor_n + 1}.0"
    # default: patch
    return f"{major_n}.{minor_n}.{patch_n + 1}"


def parse_version(version: str) -> tuple[int, int, int]:
    """'0.7.8' → (0, 7, 8). pre-release 식별자 (e.g. '-beta') 는 무시."""
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
    if not m:
        raise ValueError(f"invalid version: {version}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def cmd_refresh_maturity(args) -> dict:
    """maturity_matrix.json 의 `last_updated` field 자동 갱신 (v0.14.6+ Task 3 follow-up).

    v0.14.0+ dashboard Panel 1 freshness 보강을 위한 dispatcher subcommand.
    helper `refresh_maturity_last_updated` (cache.py) 를 호출하여 `last_updated` 를
    오늘 날짜로 갱신. idempotent (이미 today 면 no-op).

    v0.15.2+ (out-of-scope 1 해소): `--no-legacy-memory` strict opt-out caller 정합.
    legacy_memory=False 면 silent fallback 비활성 caller 로 간주, maturity refresh
    skip + warning emit (release note 가 legacy caller 의 silent fallback 자체가
    disable 된 caller 정합).

    Args (CLI namespace):
        apply (bool): default True. dry-run 모드 (--dry-run) 시 False.
        today (str | None): 명시적 override (default: date.today().isoformat()).
        maturity_path (str | None): 명시적 path (default: workflow-source/core/maturity_matrix.json).
        json (bool): JSON 출력.
        legacy_memory (bool | None): v0.15.2+ strict opt-out flag. False 면 skip.

    Returns:
        dict { refreshed: bool, before: str, after: str, today: str,
               maturity_path: str, mode: 'apply' | 'dry-run',
               legacy_memory_strict_opt_out: bool (v0.15.2+) }
    """
    from datetime import date as _date

    # v0.15.2+: legacy_memory strict opt-out (--no-legacy-memory) caller 정합.
    # silent fallback 비활성 caller 는 maturity refresh 자체를 skip.
    legacy_memory_strict_opt_out = getattr(args, "legacy_memory", None) is False
    if legacy_memory_strict_opt_out:
        return {
            "refreshed": False,
            "before": "",
            "after": "",
            "today": getattr(args, "today", None) or _date.today().isoformat(),
            "maturity_path": "<skipped — --no-legacy-memory strict opt-out>",
            "mode": "apply" if getattr(args, "apply", True) else "dry-run",
            "legacy_memory_strict_opt_out": True,
            "skip_reason": "v0.15.0+ ⚠️ BREAKING caller strict opt-out — silent fallback 비활성 정합. "
                           "maturity refresh skip.",
        }

    mode = "apply" if getattr(args, "apply", True) else "dry-run"
    today = getattr(args, "today", None) or _date.today().isoformat()
    maturity_path_arg = getattr(args, "maturity_path", None)
    if maturity_path_arg:
        maturity_path = Path(maturity_path_arg)
        if not maturity_path.is_absolute():
            maturity_path = (REPO_ROOT / maturity_path_arg).resolve()
    else:
        # release_pipeline.py 의 REPO_ROOT 는 workflow-source/ (tools/ 의 parent). 본
        # helper 는 root 기준이므로 REPO_ROOT.parent 사용 (doubled path 방지).
        maturity_path = (REPO_ROOT.parent / "workflow-source" / "core" / "maturity_matrix.json").resolve()

    result: dict[str, Any] = {
        "mode": mode,
        "today": today,
        "maturity_path": str(maturity_path),
        "refreshed": False,
        "before": "",
        "after": today,
    }
    if mode == "dry-run":
        # dry-run: 실제 갱신 없이 plan 만 emit
        if maturity_path.is_file():
            try:
                with maturity_path.open("r", encoding="utf-8") as fp:
                    mm = json.load(fp)
                result["before"] = str(mm.get("last_updated", ""))
            except (OSError, json.JSONDecodeError):
                pass
        result["dry_run_note"] = (
            "실제 last_updated 갱신 안 함. --apply 또는 --dry-run 미지정 시 자동 호출."
        )
        return result

    # apply mode — refresh_maturity_last_updated helper 호출
    if refresh_maturity_last_updated is None:
        result["error"] = (
            "refresh_maturity_last_updated helper unavailable (workflow_kit import 실패). "
            "workflow-source 가 sys.path 에 있는지 확인."
        )
        return result

    refreshed = refresh_maturity_last_updated(maturity_path, today=today)
    result["refreshed"] = refreshed["updated"]
    result["before"] = refreshed["before"]
    result["after"] = refreshed["after"]
    return result


def cmd_version_bump(args) -> dict:
    """pyproject.toml version patch + workflow_kit/__init__.py __version__ 자동 sync (v0.7.14+).

    --no-init flag 시 __init__.py sync skip (CI / override 시나리오).

    v0.7.27+: --apply 시 sync_release_hash.py 자동 호출 (TASK-V0726-003). 본 release 의
    state.json + backlog 의 hash = latest commit (apply 후의 chore commit) 으로 1 commit
    으로 정합. infinite fix(state) loop 회피.
    """
    current = read_version()
    current_wk = read_workflow_kit_version()
    if args.dry_run:
        new = bump_version(
            current,
            patch=args.patch, minor=args.minor, major=args.major, to=args.to,
        )
        result = {
            "mode": "dry-run",
            "current_pyproject": current,
            "current_workflow_kit": current_wk,
            "next_pyproject": new,
            "next_workflow_kit": new if not getattr(args, "no_init", False) else "(skipped)",
        }
        return result
    if args.to is None and not (args.patch or args.minor or args.major):
        args.patch = True

    # v1.0.0 guard: post-step 이 `git commit --amend` 로 working tree 를 HEAD 에 흡수하므로,
    # bump 이전에 *미커밋 작업이 있으면* 그것까지 release commit 에 빨려 들어간다.
    # → amend 가 실제로 돌 때 (skip_sync_hash=False) 만 clean tree 를 강제. --allow-dirty override.
    will_amend = not getattr(args, "skip_sync_hash", False)
    if will_amend and not getattr(args, "allow_dirty", False):
        dirty = _git_dirty_paths()
        if dirty:
            return {
                "mode": "aborted",
                "current_pyproject": current,
                "current_workflow_kit": current_wk,
                "dirty_paths": dirty[:50],
                "dirty_count": len(dirty),
                "error": (
                    f"working tree is not clean ({len(dirty)} path) — post-step `git commit --amend` "
                    f"가 미커밋 작업을 release commit 에 흡수합니다. commit/stash 후 재실행하거나 "
                    f"--skip-sync-hash / --allow-dirty 를 사용하세요."
                ),
            }

    new = bump_version(
        current,
        patch=args.patch, minor=args.minor, major=args.major, to=args.to,
    )
    write_version(new)
    result = {
        "mode": "applied",
        "previous_pyproject": current,
        "current_pyproject": new,
    }
    if not getattr(args, "no_init", False):
        written = write_workflow_kit_version(new, suffix="")
        result["previous_workflow_kit"] = current_wk
        result["current_workflow_kit"] = written
    else:
        result["workflow_kit_skipped"] = True

    # 플러그인 산출물 정합을 **보고만** 한다 (P4). 여기서 쓰지 않는 이유는
    # `plugin_payload_status` docstring 참조 — 강제는 릴리스 게이트가 한다.
    result["plugin_payload_status"] = plugin_payload_status(new)

    # TASK-V0726-003 (v0.7.27): post-step 자동 sync — state.json + backlog 의 hash = latest
    # commit. --skip-sync-hash flag 시 skip (manual override).
    if not getattr(args, "skip_sync_hash", False):
        sync_result = _run_post_step_sync_hash(
            new, allow_pushed_amend=getattr(args, "allow_pushed_amend", False),
        )
        result["sync_hash_result"] = sync_result
    return result


def _git_toplevel(*, timeout: int = 15) -> Path:
    """git 저장소 루트. 실패하면 `REPO_ROOT.parent` 로 떨어진다.

    `REPO_ROOT` 는 이름과 달리 `workflow-source/` 라, `git status --porcelain` 이
    내놓는 *저장소 루트 기준* 경로를 그대로 쓰려면 이 함수의 결과를 cwd 로 써야
    한다. 둘을 섞으면 경로가 중복된다 (v1.1.2 release 에서 `git add` 가
    `workflow-source/workflow-source/pyproject.toml` 을 찾다 실패했다).
    """
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=timeout, cwd=str(REPO_ROOT),
        )
    except (OSError, subprocess.TimeoutExpired):
        return REPO_ROOT.parent
    top = proc.stdout.strip()
    if proc.returncode != 0 or not top:
        return REPO_ROOT.parent
    return Path(top)


def _git_dirty_paths(*, timeout: int = 15, needs_add_only: bool = False) -> list[str]:
    """`git status --porcelain` 의 변경 path 목록 (untracked 포함).

    rename (`R  old -> new`) 은 new path 만 반환. git 호출 실패 시 빈 list.

    needs_add_only=True 는 worktree 열(Y)이 index 와 다른 entry 만 남긴다 —
    `git add` 대상 선별용. index 에만 있는 변경 (`M `/`D `/`A ` 등, Y=' ') 은
    이미 staged 라 add 가 불필요하고, 특히 **staged 삭제 (`D `) 는 worktree 에도
    index 에도 없어 `git add -- <path>` 가 pathspec fatal** 을 낸다.
    """
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, timeout=timeout, cwd=str(_git_toplevel()),
    )
    if proc.returncode != 0:
        return []
    paths = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        if needs_add_only and line[1] == " ":
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path.strip().strip('"'))
    return paths


def _head_is_pushed(*, timeout: int = 15) -> dict:
    """HEAD 가 upstream 에 이미 push 됐는지 판정.

    Returns:
        dict(checked, upstream, pushed). upstream 이 없으면 checked=False (판정 불가 →
        호출측에서 amend 를 막지 않음).
    """
    proc_up = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        capture_output=True, text=True, timeout=timeout, cwd=str(REPO_ROOT),
    )
    if proc_up.returncode != 0 or not proc_up.stdout.strip():
        return {"checked": False, "upstream": None, "pushed": False}
    upstream = proc_up.stdout.strip()
    proc_anc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", "HEAD", upstream],
        capture_output=True, text=True, timeout=timeout, cwd=str(REPO_ROOT),
    )
    return {"checked": True, "upstream": upstream, "pushed": proc_anc.returncode == 0}


def _run_post_step_sync_hash(version: str, *, allow_pushed_amend: bool = False) -> dict:
    """sync_release_hash.py 자동 호출 (TASK-V0726-003 post-step) + amend 통합 (TASK-V0727-001).

    2-phase:
    1. sync_release_hash.py 자동 호출 — state.json + backlog 의 TBD → *current HEAD* hash
    2. `git add` (sync 의 변경) + `git commit --amend --no-edit` — 1 commit 통합 (별도 fix(state) commit 불필요)

    v1.0.0 guard: Phase 2 의 amend 는 **이미 push 된 commit 을 재작성**할 수 있으므로,
    amend 직전에 HEAD 가 upstream 의 ancestor 인지 검사한다 (`allow_pushed_amend=True` 로
    override 가능). staging 도 `git add -A` 대신 **현재 dirty path 를 명시적으로 나열**해
    무엇이 amend 에 흡수됐는지 result 에 기록한다. dirty tree 자체의 차단은 호출측
    (`cmd_version_bump`) 의 pre-flight 책임.

    sync_release_hash.py 는 release_pipeline.py 와 같은 dir (workflow-source/workflow_kit/tools/) 에
    위치. REPO_ROOT 와 무관하게 __file__ 의 parents[1] (workflow-source/workflow_kit/tools/) 기준.

    Args:
        version: new version (e.g. "0.7.29").

    Returns:
        dict with keys: ok (bool), sync_result (subprocess result), amend_result (subprocess result),
        final_hash (amend 후의 HEAD short SHA, 또는 None).
        sync_release_hash.py 또는 git amend 의 returncode != 0 면 ok = False.
    """
    sync_tool = Path(__file__).resolve().parent / "sync_release_hash.py"
    if not sync_tool.exists():
        return {
            "ok": False, "sync_result": None, "amend_result": None, "final_hash": None,
            "error": f"sync_release_hash.py not found: {sync_tool}",
        }
    version_arg = f"v{version}" if not version.startswith("v") else version

    # Phase 1: sync_release_hash 호출
    proc_sync = subprocess.run(
        [sys.executable, str(sync_tool), f"--version={version_arg}", "--apply"],
        capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT),
    )
    sync_result = {
        "stdout": proc_sync.stdout,
        "stderr": proc_sync.stderr,
        "returncode": proc_sync.returncode,
    }
    if proc_sync.returncode != 0:
        return {
            "ok": False, "sync_result": sync_result, "amend_result": None, "final_hash": None,
            "error": f"sync_release_hash.py failed (returncode={proc_sync.returncode}): {proc_sync.stderr}",
        }

    # Phase 2: git add (sync 의 변경) + git commit --amend --no-edit (1 commit 통합)
    # amend 시 *HEAD* 의 *직전* commit (feat or chore) 이 amend 됨
    # sync_release_hash 의 변경 = state.json + backlog 의 TBD → HEAD hash
    # *이미* amend 후 의 *HEAD* 의 본 release 의 chore commit hash 와 정합
    # Guard 1 (v1.0.0): 이미 push 된 commit 은 amend 금지 — 원격 history 재작성 방지
    pushed_info = _head_is_pushed()
    if pushed_info["pushed"] and not allow_pushed_amend:
        return {
            "ok": False, "sync_result": sync_result, "amend_result": None, "final_hash": None,
            "head_pushed": pushed_info,
            "error": (
                f"HEAD is already pushed to {pushed_info['upstream']} — refusing to amend "
                f"(원격 history 재작성 위험). 새 commit 으로 처리하거나 --allow-pushed-amend 로 override."
            ),
        }

    # Guard 2 (v1.0.0): `git add -A` 대신 dirty path 명시 — 무엇이 흡수됐는지 기록
    staged_paths = _git_dirty_paths()
    if not staged_paths:
        return {
            "ok": True, "sync_result": sync_result, "amend_result": None, "final_hash": None,
            "head_pushed": pushed_info, "staged_paths": [],
            "skipped": "no changes to amend",
            "error": None,
        }
    # `staged_paths` 는 저장소 루트 기준이다 — cwd 도 루트여야 한다.
    # add 는 worktree 측 변경만 — 이미 staged 된 삭제 (`D `) 를 pathspec 으로 주면
    # fatal 이고, staged-only 변경은 add 없이도 amend 에 흡수된다.
    toplevel = _git_toplevel()
    add_targets = _git_dirty_paths(needs_add_only=True)
    if add_targets:
        proc_add = subprocess.run(
            ["git", "add", "--", *add_targets],
            capture_output=True, text=True, timeout=30, cwd=str(toplevel),
        )
        add_result = {
            "stdout": proc_add.stdout,
            "stderr": proc_add.stderr,
            "returncode": proc_add.returncode,
        }
        if proc_add.returncode != 0:
            return {
                "ok": False, "sync_result": sync_result, "amend_result": add_result, "final_hash": None,
                "head_pushed": pushed_info, "staged_paths": staged_paths,
                "error": f"git add failed (returncode={proc_add.returncode}): {proc_add.stderr}",
            }

    proc_amend = subprocess.run(
        ["git", "commit", "--amend", "--no-edit"],
        capture_output=True, text=True, timeout=30, cwd=str(toplevel),
    )
    amend_result = {
        "stdout": proc_amend.stdout,
        "stderr": proc_amend.stderr,
        "returncode": proc_amend.returncode,
    }
    if proc_amend.returncode != 0:
        return {
            "ok": False, "sync_result": sync_result, "amend_result": amend_result, "final_hash": None,
            "head_pushed": pushed_info, "staged_paths": staged_paths,
            "error": f"git commit --amend failed (returncode={proc_amend.returncode}): {proc_amend.stderr}",
        }

    # final hash (amend 후의 HEAD)
    # 2-step: full SHA → short=7 (F-7+ 의 정공법, v0.7.26)
    proc_full = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=5, cwd=str(REPO_ROOT),
    )
    if proc_full.returncode == 0 and proc_full.stdout.strip():
        head_full = proc_full.stdout.strip()
        proc_short = subprocess.run(
            ["git", "rev-parse", "--short=7", head_full],
            capture_output=True, text=True, timeout=5, cwd=str(REPO_ROOT),
        )
        if proc_short.returncode == 0 and proc_short.stdout.strip():
            final_hash = proc_short.stdout.strip()[:7]
        else:
            final_hash = None
    else:
        final_hash = None

    return {
        "ok": True, "sync_result": sync_result, "amend_result": amend_result, "final_hash": final_hash,
        "head_pushed": pushed_info, "staged_paths": staged_paths,
        "error": None,
    }


# ---------------------------------------------------------------------------
# 3. note-draft
# ---------------------------------------------------------------------------


def collect_commits_since(from_tag: str) -> list[dict]:
    """git log <from_tag>..HEAD 의 commit 목록."""
    proc = subprocess.run(
        ["git", "log", f"{from_tag}..HEAD", "--pretty=format:%h|%s|%an|%ai"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30,
    )
    if proc.returncode != 0:
        return []
    rows = []
    for line in proc.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|", 3)
        if len(parts) == 4:
            rows.append({
                "short": parts[0], "subject": parts[1],
                "author": parts[2], "date": parts[3][:10],
            })
    return rows


def draft_release_note(to_version: str, commits: list[dict], from_tag: str) -> str:
    """release note skeleton 자동 생성.

    기존 Beta-v<X>.<Y>.<Z>.md 의 패턴 따름:
    - TL;DR + 핵심 추가
    - Commit
    - Reference
    """
    today = datetime.now().strftime("%Y-%m-%d")
    feat_commits = [c for c in commits if c["subject"].startswith("feat")]
    chore_commits = [c for c in commits if c["subject"].startswith("chore")]
    docs_commits = [c for c in commits if c["subject"].startswith("docs")]

    lines = [
        f"# Beta v{to_version} — (자동 생성, 편집 필요) ({today})",
        "",
        "> 본 release note 는 `tools/release_pipeline.py note-draft` 의 *skeleton*.",
        "> commit hash / 본문 / Reference 등을 *수동 편집* 후 `docs/v<X>.<Y>.<Z>-release.md` 로 commit.",
        f"> 범위: `{from_tag}..HEAD` ({len(commits)} commit)",
        "",
        "## TL;DR",
        "",
        f"- {len(feat_commits)} feat / {len(chore_commits)} chore / {len(docs_commits)} docs commit",
        f"- 범위: `{from_tag}..HEAD`",
        "",
        "## 핵심 추가",
        "",
        "### feat",
        "",
    ]
    for c in feat_commits:
        lines.append(f"- `{c['short']}` {c['subject']}")
    if chore_commits:
        lines += ["", "### chore", ""]
        for c in chore_commits:
            lines.append(f"- `{c['short']}` {c['subject']}")
    if docs_commits:
        lines += ["", "### docs", ""]
        for c in docs_commits:
            lines.append(f"- `{c['short']}` {c['subject']}")

    lines += [
        "",
        "## Commit",
        "",
        "| Hash | Subject |",
        "|---|---|",
    ]
    for c in commits[:30]:  # max 30
        lines.append(f"| `{c['short']}` | {c['subject']} |")
    if len(commits) > 30:
        lines.append(f"| ... | ({len(commits) - 30} more) |")

    lines += [
        "",
        "## Reference",
        "",
        f"- 이전 release note: `Beta-v{from_tag.replace('v', '')}.md`",
        f"- memory entry: 추후 추가",
        "",
        "---",
        "",
        f"<!-- Auto-generated by workflow_kit/tools/release_pipeline.py note-draft --from={from_tag} --to={to_version} -->",
        "",
    ]
    return "\n".join(lines)


def cmd_note_draft(args) -> dict:
    """git log --since=<from_tag> → release note skeleton."""
    commits = collect_commits_since(args.from_tag)
    if not commits:
        return {"mode": "error", "error": f"no commits since {args.from_tag}"}
    note = draft_release_note(args.to, commits, args.from_tag)
    output_path = RELEASES_DIR / f"Beta-v{args.to}.md"
    if args.dry_run:
        return {
            "mode": "dry-run",
            "output_path": str(output_path.relative_to(REPO_ROOT)),
            "commits": len(commits),
            "preview_first_500": note[:500],
        }
    output_path.write_text(note)
    return {
        "mode": "applied",
        "output_path": str(output_path.relative_to(REPO_ROOT)),
        "commits": len(commits),
    }


# ---------------------------------------------------------------------------
# 3.5 changelog-gen (Phase 4 — v0.7.14+)
# ---------------------------------------------------------------------------


def cmd_changelog_gen(args) -> dict:
    """multi-release git log → CHANGELOG.md 본문 생성 (Keep-a-Changelog 형식)."""
    from_tag = getattr(args, "from_tag", None)
    to_tag = getattr(args, "to_tag", "HEAD")
    commits = collect_commits_in_range(from_tag, to_tag)
    if not commits:
        if from_tag is not None:
            return {
                "error": f"no commits in range {from_tag}..{to_tag} (from_tag 또는 to_tag invalid 할 수 있음)",
            }
        return {"mode": "error", "error": "no commits in git log"}
    body = draft_changelog(commits, unreleased_label=getattr(args, "unreleased_label", "Unreleased"))
    output_path = Path(args.output) if args.output else (REPO_ROOT / "CHANGELOG.md")
    if args.dry_run:
        return {
            "mode": "dry-run",
            "output_path": str(output_path),
            "commits": len(commits),
            "versions": len(set(c["version"] for c in commits)),
            "from_tag": from_tag,
            "to_tag": to_tag,
            "preview_first_500": body[:500],
        }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if atomic_write_text is not None:
        atomic_write_text(output_path, body)
    else:
        output_path.write_text(body, encoding="utf-8")
    return {
        "mode": "applied",
        "output_path": str(output_path),
        "commits": len(commits),
        "versions": len(set(c["version"] for c in commits)),
        "from_tag": from_tag,
        "to_tag": to_tag,
    }


# ---------------------------------------------------------------------------
# Drift prevention helpers (v0.11.23+, P1 — doc-headers-update)
# ---------------------------------------------------------------------------

README_PATH = REPO_ROOT.parent / "README.md"
CORE_DOCS_DIR = REPO_ROOT / "core"
DOCS_DIR = REPO_ROOT.parent / "docs"

DOC_HEADER_DATE_RE = re.compile(
    r"^(-\s*최종\s*수정일:\s*)(\d{4}-\d{2}-\d{2})(\s*)$", re.MULTILINE
)


def _iter_doc_markdown_files(scope: str) -> list[Path]:
    """drift-prevention 대상 .md 파일들을 scope 별로 반환.

    scope:
      - 'all'         → README.md + docs/**/*.md + workflow-source/core/*.md
      - 'docs'        → docs/**/*.md 만
      - 'core'        → workflow-source/core/*.md 만
      - 'readme'      → README.md 만
    """
    out: list[Path] = []
    if scope in ("all", "readme") and README_PATH.exists():
        out.append(README_PATH)
    if scope in ("all", "core") and CORE_DOCS_DIR.exists():
        out.extend(sorted(CORE_DOCS_DIR.glob("*.md")))
    if scope in ("all", "docs") and DOCS_DIR.exists():
        out.extend(sorted(DOCS_DIR.rglob("*.md")))
    # de-dup
    seen: set[Path] = set()
    uniq: list[Path] = []
    for p in out:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        uniq.append(p)
    return uniq


def _today_iso() -> str:
    """UTC today ISO date (YYYY-MM-DD)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


#: `ai-workflow/core/` 배포 사본의 선두에 붙는 kit 버전 마커. 사본은 이 마커를
#: 뺀 나머지가 정본과 **byte 동일**해야 한다 (`check_standard_single_source`
#: case 4 가 강제).
DISTRIBUTED_CORE_MARKER_RE = re.compile(r"^(<!--\s*standard-ai-workflow-kit:[^>]*-->\n\n?)")


def _sync_distributed_core_mirror(dry_run: bool) -> list[str]:
    """`workflow-source/core/*.md` 정본을 `ai-workflow/core/*.md` 사본에 반영.

    v1.2.0 (TASK-2026-08-13-main-005) 신설. `cmd_doc_headers_update` 가 정본의
    '최종 수정일' 만 갱신하고 **사본을 몰랐다** — 그래서 v1.2.0 발행 직후 전량에서
    `check_standard_single_source` 가 23개 사본 드리프트로 red 를 냈다. 검출기는
    이미 있었고 없던 것은 *만드는 층의 규약 인지* 다 (파생물은 만드는 쪽이 규약을
    알아야 한다).

    사본에만 있는 파일(정본 없음)은 건드리지 않고, 선두 kit 버전 마커는 보존한다.

    Returns: 갱신된 사본의 repo-relative 경로 목록.
    """
    distributed_dir = REPO_ROOT.parent / "ai-workflow" / "core"
    if not distributed_dir.is_dir() or not CORE_DOCS_DIR.is_dir():
        return []
    synced: list[str] = []
    for copy_path in sorted(distributed_dir.glob("*.md")):
        canonical = CORE_DOCS_DIR / copy_path.name
        if not canonical.exists():
            continue
        try:
            current = copy_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        marker_match = DISTRIBUTED_CORE_MARKER_RE.match(current)
        marker = marker_match.group(1) if marker_match else ""
        new = marker + canonical.read_text(encoding="utf-8")
        if new == current:
            continue
        if not dry_run:
            if atomic_write_text is not None:
                atomic_write_text(copy_path, new)
            else:
                copy_path.write_text(new, encoding="utf-8")
        synced.append(str(copy_path.relative_to(REPO_ROOT.parent)))
    return synced


def cmd_doc_headers_update(args) -> dict:
    """docs/* + workflow-source/core/* + README.md 의 '- 최종 수정일: <date>' 헤더를 일괄 갱신.

    v0.11.23+ 신규. P1 (drift 재발 방지) 의 핵심. 매 release 마다 caller 가
    수동으로 "최종 수정일" 을 갱신하던 부담을 자동화. dry-run 으로 plan 검증 가능.

    Args (Namespace):
      scope    : 'all' (default) | 'docs' | 'core' | 'readme'
      date     : YYYY-MM-DD override (default: UTC today)
      dry_run  : True 면 plan 만 출력, write 안 함.

    Returns: dict { mode, scope, date, scanned, updated, files: [str] }
    """
    scope = getattr(args, "scope", "all") or "all"
    target_date = getattr(args, "date", None) or _today_iso()
    dry_run = getattr(args, "dry_run", False)

    files = _iter_doc_markdown_files(scope)
    updated_paths: list[str] = []
    scanned = 0
    for path in files:
        scanned += 1
        try:
            txt = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = DOC_HEADER_DATE_RE.sub(rf"\g<1>{target_date}\g<3>", txt)
        if new == txt:
            continue
        if dry_run:
            updated_paths.append(str(path.relative_to(REPO_ROOT.parent)))
            continue
        if atomic_write_text is not None:
            atomic_write_text(path, new)
        else:
            path.write_text(new, encoding="utf-8")
        updated_paths.append(str(path.relative_to(REPO_ROOT.parent)))

    # core 정본을 건드렸으면 배포 사본(ai-workflow/core/)도 같이 맞춘다 —
    # 사본 byte 동일은 저장소 규약이고, 그 규약은 *만드는 층*이 알아야 한다.
    mirror_synced = (
        _sync_distributed_core_mirror(dry_run) if scope in ("all", "core") else []
    )

    return {
        "mode": "dry-run" if dry_run else "applied",
        "scope": scope,
        "date": target_date,
        "scanned": scanned,
        "updated": len(updated_paths),
        "files": updated_paths,
        "distributed_core_synced": len(mirror_synced),
        "distributed_core_files": mirror_synced,
    }


def cmd_maturity_matrix_sync(args) -> dict:
    """Release note 의 frontmatter 를 읽어 maturity_matrix.json 의 SSOT 를 자동 patch.

    P2 핵심. closed_phases → done, promoted_skills → stage 전이 + provenance,
    added_harnesses → supported append. last_updated 도 today 로 갱신.

    Args (Namespace):
      from_release_note: Release note 경로 (required, YAML frontmatter 의 source)
      dry_run           : True 면 plan 만 출력, write 안 함.

    Returns: dict { mode, applied: [str], skipped: [str], files: [str], summary }
    """
    from_release_note = Path(args.from_release_note)
    if not from_release_note.exists():
        return {"mode": "error", "error": f"release note not found: {from_release_note}"}
    dry_run = getattr(args, "dry_run", False)

    fm, _rest = _parse_release_note_frontmatter(from_release_note)
    closed_phases = fm.get("closed_phases") or []
    promoted_skills = fm.get("promoted_skills") or []
    added_harnesses = fm.get("added_harnesses") or []
    deprecated_symbols = fm.get("deprecated_symbols") or []

    maturity_path = REPO_ROOT / "core" / "maturity_matrix.json"
    mm = json.loads(maturity_path.read_text(encoding="utf-8"))

    applied_ops: list[str] = []

    for phase_num in closed_phases:
        key = f"Phase {phase_num}"
        if key in mm["milestones"]:
            if mm["milestones"][key]["status"] != "done":
                mm["milestones"][key]["status"] = "done"
                applied_ops.append(f"phase:{key}→done")

    for entry in promoted_skills:
        if isinstance(entry, dict):
            name = entry.get("name", "")
            to_stage = entry.get("to", "stable")
            release = entry.get("release", "")
            if name in mm["skills"]:
                skill = mm["skills"][name]
                if skill["stage"] != to_stage:
                    skill["stage"] = to_stage
                    applied_ops.append(f"skill:{name}→{to_stage}")
                if release and "promoted_in_release" not in skill:
                    skill["promoted_in_release"] = release
                    applied_ops.append(f"skill:{name}.promoted_in_release=+{release}")

    for entry in added_harnesses:
        if isinstance(entry, dict):
            name = entry.get("name", "")
            release = entry.get("release", "")
            if name:
                supported = mm.setdefault("harnesses", {}).setdefault("supported", [])
                if name not in supported:
                    supported.append(name)
                    applied_ops.append(f"harness:{name}+supported")
                if release:
                    mm["harnesses"].setdefault("added_harness_log", []).append(
                        {"name": name, "release": release}
                    )

    for entry in deprecated_symbols:
        if isinstance(entry, dict):
            mod = entry.get("module", "")
            sym = entry.get("name", "")
            release = entry.get("release", "")
            if mod and sym:
                log = mm.setdefault("deprecation_log", [])
                log.append({"module": mod, "name": sym, "release": release})
                applied_ops.append(f"deprecated:{mod}.{sym}@{release}")

    mm["last_updated"] = _today_iso()

    summary = (
        f"closed_phases={len(closed_phases)} promoted_skills={len(promoted_skills)} "
        f"added_harnesses={len(added_harnesses)} deprecated_symbols={len(deprecated_symbols)}"
    )

    if dry_run:
        return {
            "mode": "dry-run",
            "applied": applied_ops,
            "summary": summary,
            "last_updated_after": mm["last_updated"],
            "files": [str(maturity_path.relative_to(REPO_ROOT.parent))],
        }

    # apply
    if atomic_write_json is not None:
        atomic_write_json(maturity_path, mm, indent=2, ensure_ascii=False)
    else:
        maturity_path.write_text(
            json.dumps(mm, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return {
        "mode": "applied",
        "applied": applied_ops,
        "summary": summary,
        "last_updated_after": mm["last_updated"],
        "files": [str(maturity_path.relative_to(REPO_ROOT.parent))],
    }


# ---------------------------------------------------------------------------
# Phase 13 AC3 self-recovering (v0.13.2+)
# ---------------------------------------------------------------------------
#
# drift prevention smoke (check_drift_prevention_v0_11_23.py) 의 6 case 가
# 검출한 drift 를 *자동 fix* 한다. 1-cycle close:
#   1. detect — smoke subprocess 실행, 6 case PASS/FAIL parse
#   2. classify — FAIL 중 auto-fixable / manual_required 분리
#   3. fix — auto-fixable case 각각 매핑된 fix 함수 호출
#   4. re-check — 동일 smoke 재실행 → 6/6 PASS 확인
#   5. emit — recovered / manual_required / re_check_pass 를 dict 로 반환
#             cmd_release 가 release note body 에 "## Self-recovery log" 섹션
#             자동 append.

# 6 case 의 fix 분류 매핑 (v0.13.2 baseline). 새 case 추가 시 본 dict 만 갱신.
# key = smoke 의 case func 이름, value = ("auto"|"manual", fix_callable_or_None)
_SELF_RECOVER_CASE_MAP: dict[str, tuple[str, str | None]] = {
    "test_case_1_pyproject_loud_fallback_sync": ("auto", "_fix_loud_fallback"),
    "test_case_2_maturity_matrix_phase_status": ("manual", None),
    "test_case_3_skill_stage_matches_promotion_set": ("manual", None),
    "test_case_4_readme_header_version_sync": ("auto", "_fix_readme_header_version"),
    "test_case_5_harness_supported_ssot_alignment": ("auto", "_fix_maturity_matrix_drift"),
    "test_case_6_maturity_last_updated_freshness": ("auto", "_fix_maturity_matrix_drift"),
}


def _classify_drift_failures(cases_fail: list[str]) -> tuple[list[str], list[str]]:
    """FAIL case 들을 (auto_fixable, manual_required) 2-bucket 분리.

    _SELF_RECOVER_CASE_MAP 정합 — 미등록 case 는 manual_required (fail-safe).
    """
    auto_fixable: list[str] = []
    manual_required: list[str] = []
    for case_name in cases_fail:
        entry = _SELF_RECOVER_CASE_MAP.get(case_name)
        if entry is None:
            manual_required.append(case_name)  # 미등록 → 보수적 manual
            continue
        bucket, _fix = entry
        (auto_fixable if bucket == "auto" else manual_required).append(case_name)
    return auto_fixable, manual_required


def _read_pyproject_version_str() -> str:
    """pyproject.toml [project] version 을 string 으로 read. atomic_write_text 의 source."""
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]


def _fix_loud_fallback() -> dict:
    """workflow_kit/__init__.py 의 loud fallback literal 을 pyproject version 으로 정합.

    return "<X.Y.Z>" 의 literal 을 regex 로 교체 (v1.2.1 부터 PEP 440 그대로 —
    이전 포맷 "v<X.Y.Z>-beta" 도 regex 가 함께 받아 마이그레이션한다).
    """
    if atomic_write_text is None:
        return {"ok": False, "error": "atomic_write_text unavailable"}
    py_v = _read_pyproject_version_str()
    src = WORKFLOW_KIT_INIT.read_text(encoding="utf-8")
    new_literal = f'return "{py_v}"'
    new_src, n = re.subn(r'return "v?[\d.]+(?:-beta)?"', new_literal, src, count=1)
    if n == 0:
        return {"ok": False, "error": "loud fallback literal not found"}
    atomic_write_text(WORKFLOW_KIT_INIT, new_src)
    return {"ok": True, "old": "loud_fallback", "new": py_v, "file": str(WORKFLOW_KIT_INIT.relative_to(REPO_ROOT))}


def _fix_readme_header_version() -> dict:
    """README.md 의 '- 버전: vX.Y.Z' 헤더 라인을 pyproject 와 정합."""
    if atomic_write_text is None:
        return {"ok": False, "error": "atomic_write_text unavailable"}
    py_v = _read_pyproject_version_str()
    src = README_PATH.read_text(encoding="utf-8")
    # v1.2.1: 새 포맷은 접미사 없음. 구 포맷(-beta) 도 받아 마이그레이션한다.
    new_src, n = re.subn(r"- 버전: v[\d.]+(?:-beta)?", f"- 버전: v{py_v}", src, count=1)
    if n == 0:
        return {"ok": False, "error": "README header version line not found"}
    atomic_write_text(README_PATH, new_src)
    try:
        rel = str(README_PATH.relative_to(REPO_ROOT))
    except ValueError:
        rel = str(README_PATH.relative_to(REPO_ROOT.parent))
    return {"ok": True, "old": "readme_header", "new": py_v, "file": rel}


def _fix_maturity_matrix_drift() -> dict:
    """case 5 / case 6 의 maturity_matrix drift 를 cmd_maturity_matrix_sync 로 fix.

    release note 의 frontmatter 가 source. 부재 시 last_updated 만 갱신 (case 6 fix).
    """
    # release note 가 있으면 frontmatter 기반 sync. 없으면 last_updated 만 갱신.
    try:
        version = read_version()
        notes_resolution = _resolve_notes_file(version, "default", dry_run=False)
        notes_file = notes_resolution.get("notes_file")
        if notes_file and Path(notes_file).exists():
            smm_ns = argparse.Namespace(
                from_release_note=str(notes_file),
                dry_run=False,
                apply=True,
                json=False,
            )
            return cmd_maturity_matrix_sync(smm_ns)
        # release note 부재: last_updated 만 today 로 patch.
        maturity_path = REPO_ROOT / "core" / "maturity_matrix.json"
        mm = json.loads(maturity_path.read_text(encoding="utf-8"))
        mm["last_updated"] = _today_iso()
        if atomic_write_json is not None:
            atomic_write_json(maturity_path, mm, indent=2, ensure_ascii=False)
        else:
            maturity_path.write_text(
                json.dumps(mm, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return {"ok": True, "mode": "last_updated_only", "last_updated_after": mm["last_updated"]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def _run_drift_prevention_smoke() -> dict:
    """drift prevention smoke 를 subprocess 로 inline 실행.

    Returns:
        dict with fields:
            guard_status: 'pass' | 'fail' | 'error'
            cases_pass: int
            cases_fail: int
            cases_total: int
            cases_fail_names: list[str]
            runtime_ms: int
    """
    import subprocess
    import time

    smoke_path = REPO_ROOT / "tests" / "check_drift_prevention_v0_11_23.py"
    if not smoke_path.exists():
        return {"guard_status": "error", "cases_pass": 0, "cases_fail": 0,
                "cases_total": 0, "cases_fail_names": [], "runtime_ms": 0,
                "error": f"smoke not found: {smoke_path}"}

    started = time.monotonic()
    try:
        completed = subprocess.run(
            [sys.executable, str(smoke_path)],
            cwd=str(REPO_ROOT),
            capture_output=True, text=True, check=False, timeout=30,
        )
    except subprocess.TimeoutExpired:
        return {"guard_status": "error", "cases_pass": 0, "cases_fail": 0,
                "cases_total": 0, "cases_fail_names": [], "runtime_ms": 30000,
                "error": "smoke timeout (>30s)"}

    runtime_ms = int((time.monotonic() - started) * 1000)
    stdout = completed.stdout or ""
    cases_pass = re.findall(r"^\s*PASS:\s+(\S+)", stdout, flags=re.MULTILINE)
    cases_fail = re.findall(r"^\s*FAIL:\s+(\S+)", stdout, flags=re.MULTILINE)
    summary_match = re.search(r"=== (PASS|FAIL):\s*(\d+)/6 ===", stdout)
    total = (int(summary_match.group(2)) if summary_match else len(cases_pass) + len(cases_fail))

    if completed.returncode == 0 and not cases_fail:
        return {
            "guard_status": "pass",
            "cases_pass": len(cases_pass) or 6,
            "cases_fail": 0,
            "cases_total": 6,
            "cases_fail_names": [],
            "runtime_ms": runtime_ms,
        }
    return {
        "guard_status": "fail",
        "cases_pass": len(cases_pass),
        "cases_fail": len(cases_fail),
        "cases_total": total or 6,
        "cases_fail_names": cases_fail,
        "runtime_ms": runtime_ms,
    }


def _emit_recovery_summary(recovered: list[dict], manual_required: list[str],
                           re_check: dict, dry_run: bool) -> dict:
    """recovered + manual_required + re-check 결과를 1 dict 로 emit.

    cmd_release 가 release note 본문에 본 dict 를 append 할 수 있도록 shape 안정.
    """
    return {
        "mode": "dry-run" if dry_run else "applied",
        "recovered": recovered,
        "manual_required": manual_required,
        "re_check": re_check,
        "summary": (
            f"recovered={len(recovered)} manual_required={len(manual_required)} "
            f"re_check_status={re_check.get('guard_status', 'unknown')}"
        ),
    }


def cmd_self_recover(args) -> dict:
    """Phase 13 AC3 — drift 발견 시 자동 fix + release note log emit (v0.13.2+).

    detect (smoke subprocess) → classify (auto/manual 2-bucket) → fix (auto case 만) →
    re-check (smoke 재실행) → emit (dict).

    Args (Namespace):
        dry_run: True 면 fix 안 함, plan 만 emit. default True.
        apply: True 면 fix 실행. --dry-run 과 배타적.
        json: stdout JSON.

    Returns:
        dict { mode, recovered, manual_required, re_check, summary, detection }
    """
    dry_run = getattr(args, "dry_run", False)
    apply = getattr(args, "apply", False)
    if apply and not dry_run:
        # _attr_ns 에서 apply=True 가 default 인 release step 과 정합
        pass

    # 1. detect
    detection = _run_drift_prevention_smoke()

    if detection["guard_status"] == "pass":
        # drift 없음 — 즉시 pass
        return _emit_recovery_summary(
            recovered=[],
            manual_required=[],
            re_check=detection,
            dry_run=dry_run,
        ) | {"detection": detection}

    if detection["guard_status"] == "error":
        return _emit_recovery_summary(
            recovered=[],
            manual_required=[],
            re_check=detection,
            dry_run=dry_run,
        ) | {"detection": detection, "error": detection.get("error", "smoke error")}

    # 2. classify
    auto_fixable, manual_required = _classify_drift_failures(detection["cases_fail_names"])

    # 3. fix (auto case 만)
    recovered: list[dict] = []
    if not dry_run:
        for case_name in auto_fixable:
            entry = _SELF_RECOVER_CASE_MAP[case_name]
            fix_callable_name = entry[1]
            fix_fn = globals().get(fix_callable_name) if fix_callable_name else None
            if fix_fn is None:
                continue
            try:
                result = fix_fn()
                recovered.append({"case": case_name, "fix": fix_callable_name, "result": result})
            except Exception as e:  # noqa: BLE001
                recovered.append({"case": case_name, "fix": fix_callable_name,
                                  "result": {"ok": False, "error": f"{type(e).__name__}: {e}"}})
    else:
        # dry-run: fix skip, plan 만 emit
        for case_name in auto_fixable:
            entry = _SELF_RECOVER_CASE_MAP[case_name]
            recovered.append({"case": case_name, "fix": entry[1], "result": {"ok": True, "dry_run": True}})

    # 4. re-check (fix 후 smoke 재실행)
    re_check = _run_drift_prevention_smoke()

    return _emit_recovery_summary(recovered, manual_required, re_check, dry_run) | {
        "detection": detection,
    }


# ---------------------------------------------------------------------------
# Phase 13 AC4+ bidir-link (v0.13.3+, wiki ↔ memory)
# ---------------------------------------------------------------------------


def cmd_bidir_link(args) -> dict:
    """Phase 13 AC4+ — wiki ↔ memory 양방향 link 자동화 (v0.13.3+).

    default: audit (R-C, read-only).
    --apply: sync (R-A, memory entry.mentioned_in → wiki related_pages 자동 갱신).

    sync --apply 시 pre-audit (drift 검출) → fix (sync) → post-audit (re-check, 정합 확인)
    의 1-cycle orchestrator (v0.13.2 self-recover 와 동일 정공법).

    Args (Namespace):
      workspace_root: workspace root (default: REPO_ROOT.parent)
      apply: True 면 sync 실행 (destructive, idempotent).
      json: stdout JSON.

    Returns:
        dict { mode, audit (post-sync), pre_audit (if apply), sync, summary }
    """
    from workflow_kit.common.state.bidir_link import (
        audit_bidirectional_links,
        sync_memory_to_wiki,
    )

    workspace_root = getattr(args, "workspace_root", None)
    ws = Path(workspace_root) if workspace_root else REPO_ROOT.parent

    pre_audit = audit_bidirectional_links(ws)
    apply = getattr(args, "apply", False)

    sync = None
    if apply:
        sync = sync_memory_to_wiki(ws, dry_run=False)
        # post-audit: sync 후 정합 확인
        post_audit = audit_bidirectional_links(ws)
    else:
        post_audit = pre_audit

    result = {
        "mode": "applied" if apply else "audit",
        "audit": {
            "total_wiki_pages": post_audit.total_wiki_pages,
            "total_memory_entries": post_audit.total_memory_entries,
            "symmetric_links": post_audit.symmetric_links,
            "asymmetric_count": len(post_audit.asymmetric),
            "is_symmetric": post_audit.is_symmetric,
            "asymmetric": [
                {"memory_entry_id": a.memory_entry_id, "wiki_page": a.wiki_page, "direction": a.direction}
                for a in post_audit.asymmetric
            ],
            "wiki_pages_with_related_memory": post_audit.wiki_pages_with_related_memory,
            "memory_entries_with_mentioned_wiki": post_audit.memory_entries_with_mentioned_wiki,
        },
        "audited_at": post_audit.audited_at,
    }
    if apply:
        result["pre_audit"] = {
            "asymmetric_count": len(pre_audit.asymmetric),
            "is_symmetric": pre_audit.is_symmetric,
        }
    if sync is not None:
        result["sync"] = {
            "mode": sync.mode,
            "total_changes": sync.total_changes,
            "summary": sync.summary,
            "changes": [
                {"wiki_page": c.wiki_page, "added_paths": c.added_paths,
                 "already_present": c.already_present}
                for c in sync.changes
            ],
        }
    return result


def _count_smoke_files() -> int:
    """`workflow-source/tests/check_*.py` 갯수 (dashboard 의 smoke_files_count 와 같은 기준)."""
    tests_dir = REPO_ROOT / "tests"
    if not tests_dir.is_dir():
        return 0
    return sum(1 for _ in tests_dir.glob("check_*.py"))


def verify_release_note_smoke_count(version: str) -> dict:
    """release note 의 `누적 smoke **N/N PASS**` 가 현재 smoke 파일 수와 맞는가.

    **자동으로 채우지 않는다.** 그 줄은 *전량 PASS 했다* 는 주장이고, 실제로 전량을
    돌린 사람만 할 수 있는 말이다. 도구가 대신 적으면 거짓 주장을 만든다 — 여기서는
    **빠졌거나 어긋난 것을 알려 주기만** 한다.

    왜 필요한가: 이 수치는 릴리스 시점 스냅샷이 아니라 *살아있는 지표* 이고
    (`check_smoke_trend_cross` case 2 가 강제한다), 노트에 적는 일은 사람 몫이라
    **v1.1.0 / v1.1.1 에서 통째로 빠졌다.** 그 사이 dashboard 는 옛 노트(v1.0.0 의
    234)를 읽었고 검사는 계속 red 였다. 릴리스 절차에 그걸 잡는 자리가 없었다.

    Returns:
        {"ok": bool, "note_path": str, "expected": int, "found": tuple|None, "error": str|None}
    """
    note = RELEASES_DIR / f"Beta-v{version}.md"
    expected = _count_smoke_files()
    result: dict = {
        "ok": False, "note_path": str(note), "expected": expected,
        "found": None, "error": None,
    }
    if not note.is_file():
        result["error"] = f"release note 부재: {note}"
        return result

    m = SMOKE_COUNT_RE.search(note.read_text(encoding="utf-8"))
    if m is None:
        result["error"] = (
            f"release note 에 `누적 smoke **N/N PASS**` 줄이 없다. "
            f"전량 smoke 를 돌린 뒤 `{expected}/{expected}` 로 적을 것 "
            f"(이 줄이 없으면 dashboard 가 *이전* release note 를 읽는다)."
        )
        return result

    found_pass = int(m.group(1))
    found_total = int(m.group(2)) if m.group(2) else found_pass
    result["found"] = (found_pass, found_total)
    if found_total != expected:
        result["error"] = (
            f"release note 의 누적 수치 {found_pass}/{found_total} 가 현재 smoke 파일 수 "
            f"{expected} 와 다르다. 전량 결과를 확인하고 갱신할 것."
        )
        return result
    result["ok"] = True
    return result


def cmd_release(args) -> dict:
    """GitHub Release 생성 (gh release create).

    v0.11.16+ args normalize: release subcommand argparse 의 attribute 와
    cmd_validate 가 기대하는 attribute 가 비대칭. dispatcher (CLI argparse) 는
    skip_packaging / skip_doctor / skip_state / skip_git / skip_mypy 를 add 안 해서
    args.normalize 없이 cmd_release 진입 시 cmd_validate 호출에서 AttributeError.
    memory #11 의 _make_args 정공법 정합.

    사전 점검: --skip-validate 미지정 시 validate 4 source 자동 호출.
    1+ source fail 시 release 중단 (exit 1).

    **v0.7.18+ release coordination observability**:
    `tag` 결정 후 `git ls-remote origin` 로 *원격 tag 존재 여부* 확인. 존재 시
    - default: exit 1 + auto-bump hint
    - `--auto-bump`: `next_available_version()` 로 다음 version 결정 + version-bump 자동 + re-flow
    v0.7.16 의 race lesson 반영 (memory #22 §release coordination race).

    **v0.11.13+ mypy CI cross-verify**:
    validate 5번째 source mypy (Layer 2, v0.11.12+) 와 GH Actions mypy-strict workflow
    (Layer 1, v0.11.11+) 의 *결과 정합* 을 advisory verify. verdict:
    - "sanity": CI success + local mypy 정합 (release 진행)
    - "drift_warning": CI success 인데 local fail (local drift, advisory)
    - "ci_stale": CI success 인데 headSha != HEAD (re-run 권고)
    - "ci_fail": CI failure (advisory)
    - "absent" / "skipped": gh CLI 부재 / no run (skip, advisory)
    default = advisory (release 진행). `--strict-cross-verify` flag 시 hard fail (drift / ci_stale / ci_fail).

    **v0.13.1+ dashboard post-release emit**:
    `gh release create` 성공 후 dashboard markdown snapshot 을 자동 emit.
    --skip-dashboard-emit 으로 skip 가능. 실패 시 *warning* — release 자체는 성공.
    --dashboard-output PATH 로 출력 위치 override (default: ai-workflow/dashboard/snapshot.md).

    gh auth 인증된 환경 가정. token 회전 부담은 caller 책임.
    """
    # v0.11.16+ args normalize: dispatcher (CLI argparse) 의 release subcommand 는
    # skip_packaging / skip_doctor / skip_state / skip_git / skip_mypy 를 add 안 해서
    # cmd_release 진입 시 cmd_validate 호출에서 AttributeError. memory #11 의 _make_args
    # 정공법 정합 — release library wrapper 가 dispatcher 의 kwargs → Namespace 변환 후
    # *모든 skip flag / optional attr* 의 default fill.
    for attr in ("skip_packaging", "skip_doctor", "skip_state", "skip_git", "skip_mypy",
                 "skip_validate", "skip_cross_verify", "strict_cross_verify",
                 "skip_ci_verify",  # v1.8.1 필수 CI 게이트 escape hatch
                 "skip_doc_headers_update", "skip_maturity_matrix_sync",
                 "skip_changelog_gen",  # v0.15.21+ CHANGELOG auto-gen lockdown
                 "skip_dashboard_emit", "dashboard_output",
                 "skip_self_recover",
                 "skip_bidir_link"):  # v0.13.3+ Phase 13 AC4+
        if not hasattr(args, attr):
            setattr(args, attr, False if attr == "skip_dashboard_emit" else None)

    # v1.1.4: destructive default 반전 — --apply 를 명시하지 않으면 dry-run 이다.
    # --dry-run 과 --apply 를 함께 주면 안전측(dry-run)이 이긴다. apply attr 가
    # 아예 없는 legacy caller 는 dry-run 으로 떨어진다 (모름 ≠ apply).
    if not getattr(args, "apply", False):
        args.dry_run = True

    def _attr_ns(**overrides) -> argparse.Namespace:
        """Create a fresh argparse.Namespace with default attrs + overrides.

        본 helper 는 cmd_release 내부에서 drift-prevention helpers 를 자동 호출할 때 사용.
        직접 argv → Namespace 변환 없이, 안전 default set 으로 helper 진입 가능.

        **`dry_run` / `apply` 는 반드시 바깥 release 의 mode 를 상속한다.** 이전에는
        `dry_run=False` / `apply=True` 가 하드코딩되어 있어, `release --dry-run` 이
        doc-headers-update / maturity-matrix-sync 를 통해 **실제 저장소 문서 63개를
        write** 했다(smoke 실행만으로 워킹트리가 더러워졌고, release_pipeline 의
        `git add` 와 겹치면 무관한 변경이 release commit 에 흡수된다).
        dry-run 은 아무것도 쓰지 않아야 한다.
        """
        base_defaults = {
            "scope": "all",
            "date": None,
            "dry_run": args.dry_run,
            "from_release_note": None,
            "json": False,
            "apply": not args.dry_run,
        }
        return argparse.Namespace(**{**base_defaults, **overrides})

    results: dict = {"pre_check": {}, "gh_commands": [], "mode": "dry-run" if args.dry_run else "apply"}

    # 1. mypy CI cross-verify (v0.11.13+, Layer 1 ↔ Layer 2 정합 advisory)
    # validate 보다 *먼저* 실행 — advisory 라서 validate fail 시에도 결과 포함.
    # default = advisory (release 진행). --strict-cross-verify 시 hard fail.
    if not getattr(args, "skip_cross_verify", False):
        ci_mypy = _cross_verify_ci_mypy()
        results["ci_mypy"] = ci_mypy
        # CI-only verdict (Layer 1 결과) 저장. final verdict 는 validate 후 결합.
        results["ci_mypy"]["ci_only_verdict"] = ci_mypy.get("verdict")
        ci_verdict = ci_mypy.get("verdict")
        # --strict-cross-verify: ci_stale / ci_fail 시 hard fail
        if getattr(args, "strict_cross_verify", False):
            if ci_verdict in ("ci_stale", "ci_fail"):
                return _attach_release_summary({
                    **results,
                    "error": (
                        f"strict cross-verify failed: ci_mypy.verdict={ci_verdict!r}, "
                        f"message={ci_mypy.get('message')!r}"
                    ),
                })

    # 1.5 필수 CI 게이트 (v1.8.1, TASK-2026-09-01-main-005) — **기본이 차단**이다.
    # 위 cross-verify 는 mypy 축 하나의 advisory 이고, 그 좁음 때문에 smoke 가 10 커밋
    # 연속 red 인 채 v1.8.0 이 발행됐다. 여기서는 `REQUIRED_CI_WORKFLOWS` 전부를
    # **HEAD sha 로** 조회해 하나라도 green 이 아니면 apply 를 멈춘다.
    # dry-run 은 보고만 한다 (태그를 안 만드므로) — smoke_count_check 와 같은 관례.
    # escape hatch: --skip-ci-verify (쓰면 결과에 그 사실이 남는다).
    if getattr(args, "skip_ci_verify", False):
        results["required_ci"] = {"skipped": True, "reason": "--skip-ci-verify"}
    else:
        required_ci = verify_required_ci()
        results["required_ci"] = required_ci
        if not required_ci["ok"] and not args.dry_run:
            return _attach_release_summary({
                **results,
                "ok": False,
                "error": (
                    f"{required_ci['error']} (HEAD={(required_ci.get('head_sha') or '?')[:8]}). "
                    "CI 가 green 인 커밋에 태그를 붙인다 — 고치고 push 한 뒤 다시 돌린다. "
                    "정말 넘겨야 하면 --skip-ci-verify 를 명시한다."
                ),
            })

    # 2. validate (사전 점검)
    if not args.skip_validate:
        val_result = cmd_validate(args)
        results["pre_check"] = val_result
        validate_failed = not all(v.get("ok", False) for v in val_result.values())
    else:
        validate_failed = False

    # 2.5 cross-verify final verdict (Layer 1 CI ↔ Layer 2 local mypy 결합)
    # validate fail 시에도 verdict 는 결합 (output 정합)
    if not getattr(args, "skip_cross_verify", False) and "ci_mypy" in results:
        local_mypy = results["pre_check"].get("mypy", {}) if not args.skip_validate else {}
        final_verdict = _resolve_cross_verify_verdict(results["ci_mypy"], local_mypy)
        results["ci_mypy"]["verdict"] = final_verdict
        results["ci_mypy"]["local_mypy"] = {
            "ok": local_mypy.get("ok") if local_mypy else None,
            "skipped": (not local_mypy) or local_mypy.get("skipped", False),
            "error_count": local_mypy.get("error_count") if local_mypy else None,
        }
        # --strict-cross-verify: final verdict 도 hard fail 대상
        if getattr(args, "strict_cross_verify", False):
            if final_verdict in ("drift_warning", "ci_stale", "ci_fail"):
                return _attach_release_summary({
                    **results,
                    "error": (
                        f"strict cross-verify failed: ci_mypy.verdict={final_verdict!r}, "
                        f"local_mypy={results['ci_mypy']['local_mypy']!r}, "
                        f"message={results['ci_mypy'].get('message')!r}"
                    ),
                })

    # 3. validate fail 시 early return (cross-verify 결과는 이미 results 에 포함됨)
    if validate_failed:
        return _attach_release_summary({**results, "error": "validate failed; abort release"})

    # 2.7 Phase 13 AC3 self-recovering (v0.13.2+) — drift 검출 시 자동 fix.
    # cmd_self_recover 의 emit 결과를 results 에 포함 (release note body injection 의 source).
    # manual_required > 0 이면 early return (drift fix 우선 — 사람의 명시 intervention 필요).
    # 원장 기록은 _self_recover_step 안에서 — early return 보다 앞이다 (v1.0.1+, 아래 docstring).
    # escape hatch: --skip-self-recover.
    if not getattr(args, "skip_self_recover", False):
        # self-recover 는 drift 를 *고치는* step 이므로 dry-run 에서는 plan 만 낸다.
        # (이전에는 apply=True / dry_run=False 를 강제해 dry-run 도 저장소를 고쳤다.)
        sr_ns = _attr_ns()
        sr_error = _self_recover_step(args, results, sr_ns)
        if sr_error:
            return _attach_release_summary({**results, "error": sr_error})

    # 2.8 Phase 13 AC4+ wiki ↔ memory 양방향 link audit (v0.13.3+).
    # cmd_bidir_link 의 audit 결과를 results 에 포함 (release note body injection 의 source).
    # asymmetric > 0 이면 advisory (release 차단 ❌). wiki 갱신은 자동 (R-A) 가능하지만
    # caller 가 --apply 명시해야 destructive. 본 step 는 default = audit 만.
    # escape hatch: --skip-bidir-link.
    if not getattr(args, "skip_bidir_link", False):
        try:
            bl_ns = _attr_ns()
            bl_ns.workspace_root = None  # default = REPO_ROOT.parent
            bl_ns.apply = False  # release step 은 audit 만 (caller 가 --apply 명시)
            bl_result = cmd_bidir_link(bl_ns)
            results["bidir_link_audit"] = bl_result
        except Exception as exc:  # noqa: BLE001
            results["bidir_link_audit"] = {
                "mode": "error",
                "error": f"{type(exc).__name__}: {exc}",
            }

    # 3.0 drift prevention auto-step (v0.11.23+) — release 시 docs/* / SSOT 자동 동기화.
    # 본 step 는 destructive 하지 않음 (write only on tracked files, atomic_write 보장).
    # escape hatch: --skip-doc-headers-update / --skip-maturity-matrix-sync.
    if not getattr(args, "skip_doc_headers_update", False):
        dhu = cmd_doc_headers_update(_attr_ns())
        results["doc_headers_update"] = dhu
        # P0 smoke fail 가능성: scan 결과 >= 1 인데 updated = 0 인 경우도 정상 (이미 정합).
        # 단, scan 결과 0 이면 silent skip (drift prevention 영역 밖).
    if not getattr(args, "skip_maturity_matrix_sync", False):
        # notes_file 결정은 3.4 step 에서 일어나므로, 그 전에 notes_file 가 이미 있는지 확인
        # (--notes-template 사용 가능). 없으면 skip (release note 가 없는 backfill 시나리오).
        try:
            _notes_template = getattr(args, "notes_template", "default") or "default"
            _notes_resolution = _resolve_notes_file(
                read_version(), _notes_template, dry_run=args.dry_run
            )
            _notes_file = _notes_resolution["notes_file"]
            if _notes_file.exists():
                smm_ns = _attr_ns()
                smm_ns.from_release_note = str(_notes_file)
                smm = cmd_maturity_matrix_sync(smm_ns)
                results["maturity_matrix_sync"] = smm
        except Exception as exc:  # noqa: BLE001
            results["maturity_matrix_sync"] = {
                "mode": "skipped",
                "reason": f"{type(exc).__name__}: {exc}",
            }

    # 3.4 release note 누적 smoke 수치 검증 (v1.1.3+).
    # 자동으로 채우지 않는다 — "전량 PASS" 는 사람이 확인해야 하는 주장이다.
    # escape hatch: --skip-smoke-count-check.
    if not getattr(args, "skip_smoke_count_check", False):
        _note_version = getattr(args, "version", None) or read_version()
        smoke_count_check = verify_release_note_smoke_count(_note_version)
        results["smoke_count_check"] = smoke_count_check
        if not smoke_count_check["ok"] and not args.dry_run:
            return _attach_release_summary({
                **results,
                "ok": False,
                "error": f"release note 누적 smoke 수치 검증 실패: {smoke_count_check['error']}",
            })

    # 3.5 changelog-gen auto-step (v0.15.21+) — CHANGELOG.md 를 git log 에서 재생성.
    # 전체 파일을 deterministic 하게 rewrite 하므로 marker guard 불필요 (idempotent-by-regen).
    # RELEASE_RE + RELEASE_RE_BARE 로 괄호형/맨몸형 release commit 를 모두 인식하며,
    # semver 정렬로 version section 을 최신 우선 정렬한다. dry_run 시 preview dict 만 반환.
    # escape hatch: --skip-changelog-gen.
    if not getattr(args, "skip_changelog_gen", False):
        results["changelog_gen"] = cmd_changelog_gen(_attr_ns(
            dry_run=args.dry_run,
            output=None,
            from_tag=None,
            to_tag="HEAD",
            unreleased_label="Unreleased",
        ))

    # 2. dist 파일 glob
    # v0.7.13+: --version override (backfill 시 staging 용도). default 는 read_version().
    if getattr(args, "version", None):
        version = args.version
        results["version_source"] = "cli-flag"
    else:
        version = read_version()
        results["version_source"] = "pyproject.toml"

    # v0.7.18+ auto-bump: pre-check 후 tag 결정 전에 호출
    if getattr(args, "auto_bump", False):
        bump_info = next_available_version(version)
        if bump_info["bumped"]:
            version = bump_info["next"]
            results["version_source"] = "auto-bump"
            results["auto_bump"] = bump_info
            # dry-run 은 **아무것도 쓰지 않는다.** auto-bump 는 pyproject.toml 과
            # workflow_kit/__init__.py 를 in-place 로 고치므로 dry-run 에서는 계획만
            # 보고한다. 이 결함은 `last_tag == 현재 version` 일 때만 발현하므로
            # (= 방금 release 한 직후) 오래 잠복해 있었다 — 실제로 v1.0.0-beta 발행
            # 직후 전량 smoke 가 저장소 version 을 1.0.0 → 1.0.1 로 bump 했다.
            if getattr(args, "dry_run", False):
                results["auto_bump"] = {**bump_info, "applied": False, "mode": "dry-run"}
                # 플러그인 산출물이 bump 를 따라가는지 dry-run 에서 확인할 수 있어야
                # 한다 (P4 완료 기준). 판정만 하고 쓰지 않는다.
                results["plugin_payload_status"] = plugin_payload_status(f"v{version}-beta")
            else:
                # version-bump 자동 적용 (in-place). write_version + write_workflow_kit_version
                write_version(version)
                suffix = "beta"
                if read_workflow_kit_version().endswith("-beta"):
                    suffix = "beta"
                elif read_workflow_kit_version().endswith("-alpha"):
                    suffix = "alpha"
                else:
                    suffix = ""  # default
                write_workflow_kit_version(version, suffix=("-" + suffix) if suffix else "")
                results["auto_bump"] = {**bump_info, "applied": True, "mode": "apply"}
                # 플러그인 산출물 정합 보고 (P4) — bump 3경로 전부에 건다. 쓰지 않는다.
                results["plugin_payload_status"] = plugin_payload_status(
                    f"v{version}{('-' + suffix) if suffix else ''}"
                )
        else:
            results["auto_bump"] = bump_info  # bumped=False, info only

    from workflow_kit.plugin_distribution import planned_plugin_archives

    def _release_plugin_files(release_version: str) -> list[Path]:
        archives = planned_plugin_archives(REPO_ROOT / "dist", release_version)
        missing = [path for path in archives if not path.is_file()]
        if missing:
            raise FileNotFoundError(
                "plugin archives missing; run `wk release-pipeline dist --apply` first: "
                + ", ".join(path.name for path in missing)
            )
        return archives

    dist_files = find_dist_files(version)
    if not dist_files:
        return _attach_release_summary({**results, "error": f"no dist files found for version {version} (run `python3 -m build` first)"})
    try:
        plugin_dist_files = _release_plugin_files(version)
    except FileNotFoundError as exc:
        return _attach_release_summary({**results, "error": str(exc)})

    # 3. tag 결정 + 원격 tag pre-check (v0.7.18+)
    tag = f"v{version}"
    # v0.7.24+: --notes-template flag 로 release notes format 자유도
    notes_template = getattr(args, "notes_template", "default") or "default"
    notes_resolution = _resolve_notes_file(version, notes_template, dry_run=args.dry_run)
    if notes_resolution.get("error"):
        return _attach_release_summary({**results, "error": notes_resolution["error"]})
    notes_file = notes_resolution["notes_file"]
    if not notes_file.exists():
        return _attach_release_summary({**results, "error": f"release note not found: {notes_file}"})

    # 3.5 원격 tag pre-check + tag push (v0.7.18+ race lesson, v0.7.21+ follow-up,
    # v0.9.1+ --full-auto: pre-check conflict 시 --auto-bump / --allow-existing-tag 자동 활성화)
    # v0.7.21 fix: tag push 와 release 의 coupling. *순서*:
    #   1. pre-check: remote 에 tag 가 이미 push 됐는지 확인
    #   2. tag push: pre-check fail 시 default = skip, --allow-existing-tag 면 skip + 진행, --auto-bump 면 bump
    #   3. gh release create: --verify-tag 가 tag 의 remote 존재 검증 (pre-check 와 *redundant* 한 부분)
    # v0.9.1+ --full-auto: pre-check fail 시 자동으로 다음 version 결정 (auto-bump 동작) 후
    #   새로 결정된 version 으로 tag + release 재실행. 1-cycle close.
    if not args.dry_run:
        tag_check = _check_remote_tag(tag)
        results["tag_pre_check"] = tag_check
        if tag_check["exists"]:
            # --full-auto: --auto-bump 와 동일 동작 (다음 version 자동 결정) 후 re-flow
            if getattr(args, "full_auto", False) and not getattr(args, "allow_existing_tag", False):
                bump_info = next_available_version(version)
                if bump_info["bumped"]:
                    new_version = bump_info["next"]
                    results["version_source"] = "full-auto-bump"
                    results["auto_bump"] = bump_info
                    # dry-run 은 쓰지 않는다 (--full-auto 경로도 동일 계약).
                    if getattr(args, "dry_run", False):
                        results["auto_bump"] = {**bump_info, "applied": False, "mode": "dry-run"}
                        results["plugin_payload_status"] = plugin_payload_status(
                            f"v{new_version}-beta"
                        )
                    else:
                        # in-place version-bump
                        write_version(new_version)
                        suffix = "beta"
                        if read_workflow_kit_version().endswith("-beta"):
                            suffix = "beta"
                        write_workflow_kit_version(new_version, suffix=("-beta" if suffix else ""))
                        results["auto_bump"] = {**bump_info, "applied": True, "mode": "apply"}
                        # 플러그인 산출물 정합 보고 (P4) — full-auto 경로도 동일 계약.
                        results["plugin_payload_status"] = plugin_payload_status(
                            f"v{new_version}{'-beta' if suffix else ''}"
                        )
                    # re-flow with new version
                    version = new_version
                    tag = f"v{version}"
                    dist_files = find_dist_files(version)
                    if not dist_files:
                        return _attach_release_summary({**results, "error": f"no dist files for {version} after --full-auto bump"})
                    try:
                        plugin_dist_files = _release_plugin_files(version)
                    except FileNotFoundError as exc:
                        return _attach_release_summary({**results, "error": str(exc)})
                    tag_check = _check_remote_tag(tag)
                    results["tag_pre_check"] = tag_check
                    results["full_auto_re_tag"] = tag
                    if tag_check["exists"]:
                        # full-auto 도 bump 했는데 여전히 존재 → --allow-existing-tag 활성화
                        results["full_auto_fallback"] = "allow-existing-tag"
            if tag_check.get("exists") and not getattr(args, "allow_existing_tag", False):
                return {
                    **results,
                    "error": (
                        f"remote tag {tag} already exists at {tag_check['remote_url']}. "
                        f"v0.7.16 race 정공법: --auto-bump 으로 다음 version 자동 bump, "
                        f"--allow-existing-tag 으로 *기존 tag* 에 re-attach, "
                        f"--full-auto 으로 1-cycle close, "
                        f"또는 --version=<next> 명시."
                    ),
                }
            # --allow-existing-tag: skip pre-check fail, 그대로 release 진행
            results["tag_pre_check_skipped"] = "allow-existing-tag"

    # 3.6 local tag create + push (v0.7.21+ — tag push 와 release 의 coupling,
    # v0.9.0 chapter 4 fix: local tag create step 추가 — 이전엔 push 만 해서
    # `src refspec does not match any` fail)
    if not args.dry_run:
        tag_create_proc = subprocess.run(
            ["git", "tag", tag, "HEAD"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10,
        )
        results["tag_create"] = {
            "tag": tag,
            "returncode": tag_create_proc.returncode,
            "stdout_tail": tag_create_proc.stdout.strip(),
            "stderr_tail": tag_create_proc.stderr.strip(),
        }
        # tag 가 이미 존재하면 returncode != 0 일 수 있으나, --allow-existing-tag 의 경우
        # 그대로 진행. 그 외는 다음 step (push) 에서 검증.
        push_tag_proc = subprocess.run(
            ["git", "push", "origin", f"refs/tags/{tag}"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30,
        )
        results["tag_push"] = {
            "tag": tag,
            "returncode": push_tag_proc.returncode,
            "stdout_tail": push_tag_proc.stdout.strip().split("\n")[-1] if push_tag_proc.stdout else "",
            "stderr_tail": push_tag_proc.stderr.strip().split("\n")[-1] if push_tag_proc.stderr else "",
        }
        if push_tag_proc.returncode != 0 and not getattr(args, "allow_existing_tag", False):
            return _attach_release_summary({**results, "error": f"git push tag {tag} failed: {push_tag_proc.stderr.strip()}"})
    else:
        # dry-run: pre-check 결과 + warning (plan 검증)
        tag_check = _check_remote_tag(tag)
        results["tag_pre_check"] = tag_check
        if tag_check["exists"]:
            results["tag_pre_check_warning"] = f"remote tag {tag} already exists (dry-run: pre-check only)"

    release_files = [*dist_files, *plugin_dist_files]
    rel_assets = [str(f.relative_to(REPO_ROOT)) for f in release_files]
    results["tag"] = tag
    results["assets"] = rel_assets
    # v0.7.24+: notes_file 가 in-repo 면 relative path, 그 외 (예: changelog) 면 absolute
    try:
        results["notes_file"] = str(notes_file.relative_to(REPO_ROOT))
    except ValueError:
        results["notes_file"] = str(notes_file)

    # 4. gh command build
    repo_remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10,
    )
    repo = repo_remote.stdout.strip().replace("https://github.com/", "").replace(".git", "")
    results["repo"] = repo

    gh_cmd = [
        "gh", "release", "create", tag,
        "--repo", repo,
        "--title", f"v{version}",
        "--notes-file", str(notes_file),
        "--target", "main",
        "--verify-tag",
    ] + [str(f) for f in release_files]
    results["gh_command"] = " ".join(gh_cmd)

    if args.dry_run:
        return results

    # 5. gh auth check + release create
    auth_proc = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=10)
    if auth_proc.returncode != 0:
        return _attach_release_summary({**results, "error": "gh auth not authenticated"})
    results["gh_auth_ok"] = True

    proc = subprocess.run(gh_cmd, capture_output=True, text=True, timeout=120)
    results["gh_exit_code"] = proc.returncode
    if proc.stdout:
        results["gh_stdout_tail"] = proc.stdout.strip().split("\n")[-1]
    if proc.stderr:
        results["gh_stderr_tail"] = proc.stderr.strip().split("\n")[-1]
    if proc.returncode != 0:
        return _attach_release_summary({**results, "error": f"gh release create failed: exit {proc.returncode}"})

    # 6. v0.13.1+ dashboard post-release emit. Warning 만 — release 자체는 성공.
    dashboard_emit = _emit_dashboard_post_release(args, results)
    results["dashboard_emit"] = dashboard_emit
    if dashboard_emit.get("status") == "ok":
        print(f"  [dashboard] {dashboard_emit.get('path', '?')} ({dashboard_emit.get('bytes', 0)} bytes)")
    elif dashboard_emit.get("status") == "skipped":
        print(f"  [dashboard] skipped ({dashboard_emit.get('reason', '')})")
    else:
        print(f"  [dashboard] WARN: {dashboard_emit.get('error', 'unknown error')}")

    # 6.5 v0.13.2+ self-recovery log emit (Phase 13 AC3). release note 본문 끝에 자동 append.
    # results["self_recover"] 가 있을 때만 (drift 가 검출/fix 되었을 때만). 미존재 시 no-op.
    if "self_recover" in results:
        recovery_log = _format_self_recovery_log(results["self_recover"])
        if recovery_log:
            log_emit = _emit_self_recovery_log(args, recovery_log)
            results["self_recovery_log_emit"] = log_emit

    # 6.5b (제거됨, v1.0.1+) north-star 원장 append 는 여기가 아니라 step 2.7 이다.
    # 여기에 두면 `gh release create` 성공 뒤라, manual_required 로 early return 한
    # cycle — 즉 **north-star 의 분자가 될 바로 그 cycle** — 이 기록되지 않는다.
    # 자세한 근거는 `_self_recover_step` docstring 참조.

    # 6.7 v0.14.6+ maturity_last_updated 자동 갱신 (Task 3 follow-up).
    # v0.15.3+ 변경: release_error (results["error"] 존재) 시에만 maturity refresh
    # 호출. v0.14.6 description 의 "Out of scope v0.15.0" 2건 중 2건 해소.
    # rationale: release 성공 후 (operator 가 이미 gh release create 성공 확인)
    # maturity 자체가 today 면 no-op 인 호출이 dashboard freshness 와 무관 —
    # release_error (gh release create fail) 상황 에서만 operator 가 retry 할
    # 수 있도록 panel 1 freshness 보강. release_error fallback 정공법.
    # v0.15.2+ legacy_memory strict opt-out (--no-legacy-memory) caller 정합 —
    # cmd_refresh_maturity 가 자체 skip + warning emit.
    release_error = "error" in results
    if release_error and not getattr(args, "dry_run", False) and refresh_maturity_last_updated is not None:
        try:
            maturity_result = cmd_refresh_maturity(args)
            results["maturity_refresh"] = maturity_result
            if maturity_result.get("legacy_memory_strict_opt_out"):
                # v0.15.2+ strict opt-out caller — maturity refresh skip.
                print(f"  [maturity] skip (--no-legacy-memory strict opt-out — v0.15.0+ ⚠️ BREAKING caller 정합)")
            elif maturity_result.get("refreshed"):
                print(f"  [maturity] {maturity_result['before']} → {maturity_result['after']} (release_error fallback)")
            else:
                print(f"  [maturity] no-op (already {maturity_result.get('before') or 'today'}) — release_error fallback")
        except Exception as exc:  # noqa: BLE001 — release_error 자체가 이미 set
            results["maturity_refresh"] = {"error": str(exc), "warning": True}
            print(f"  [maturity] WARN: {exc}")
    elif not release_error:
        # v0.15.3+ release 성공 시 maturity refresh skip (rationale 위 주석 참조).
        results["maturity_refresh"] = {
            "skipped_due_to_release_success": True,
            "reason": "v0.15.3+ release 성공 시 maturity refresh skip. release_error fallback 만 호출.",
        }

    # 6.6 v0.13.3+ bidir-link audit log emit (Phase 13 AC4+).
    # results["bidir_link_audit"] 가 있으면 release note 본문 끝에 audit 요약 자동 append.
    if "bidir_link_audit" in results:
        bl_log = _format_bidir_link_audit(results["bidir_link_audit"])
        if bl_log:
            bl_log_emit = _emit_bidir_link_audit_log(args, bl_log)
            results["bidir_link_log_emit"] = bl_log_emit

    return _attach_release_summary(results)


# ---------------------------------------------------------------------------
# 4.6 self-recovery log emit (v0.13.2+ Phase 13 AC3 close-out)
# ---------------------------------------------------------------------------


def _emit_self_recovery_log(args: argparse.Namespace, recovery_log: str) -> dict:
    """release note 본문 끝에 self-recovery log append (Phase 13 AC3 close-out).

    release note 가 없거나 (backfill 시나리오) recovery_log 가 empty 면 no-op.
    """
    try:
        version = getattr(args, "version", None) or read_version()
        notes_resolution = _resolve_notes_file(version, "default", dry_run=False)
        notes_file = notes_resolution.get("notes_file")
        if not notes_file or not Path(notes_file).exists():
            return {"status": "skipped", "reason": "release note not found (backfill scenario)"}
        body = Path(notes_file).read_text(encoding="utf-8")
        # "## Self-recovery log" 헤더가 이미 있으면 중복 append 방지 (idempotent).
        marker = "## Self-recovery log"
        if marker in body:
            return {"status": "skipped", "reason": "self-recovery log already present (idempotent)"}
        new_body = body.rstrip("\n") + "\n" + recovery_log
        if atomic_write_text is not None:
            atomic_write_text(notes_file, new_body)
        else:
            notes_file.write_text(new_body, encoding="utf-8")
        return {
            "status": "ok",
            "path": str(notes_file),
            "bytes_appended": len(recovery_log),
        }
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


def _append_drift_ledger_entry(args: argparse.Namespace, sr_result: dict) -> dict:
    """north-star 원장에 release cycle 1건을 append (Phase 13 AC1, v1.0.1+).

    원장은 append-only JSONL 이다. cycle 당 정확히 1 line — drift 가 없었던 cycle 도
    기록한다. 그래야 dashboard 가 "0/N cycle" 을 말할 수 있다 (기록이 없으면 *미측정*).

    dry-run 이면 아무것도 쓰지 않는다 (저장소 오염 금지).
    """
    if getattr(args, "dry_run", False):
        return {"status": "skipped", "reason": "dry-run"}
    try:
        manual_required = sr_result.get("manual_required") or []
        recovered = sr_result.get("recovered") or []
        re_check = sr_result.get("re_check") or {}
        entry = {
            "version": getattr(args, "version", None) or read_version(),
            "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "manual_required_count": len(manual_required),
            "manual_required": list(manual_required),
            "auto_recovered_count": len(recovered),
            "re_check_status": re_check.get("guard_status", "unknown"),
        }
        # workspace_root 는 test / 다중 workspace caller 가 주입할 수 있어야 한다.
        # 저장소 경로로 고정돼 있으면 왕복 계약 테스트가 실저장소를 오염시킨다.
        ws_override = getattr(args, "workspace_root", None)
        ledger = (Path(ws_override) if ws_override else REPO_ROOT.parent) / DRIFT_LEDGER_RELPATH
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return {"status": "ok", "path": str(ledger), "entry": entry}
    except Exception as e:  # noqa: BLE001 — 원장 기록 실패가 release 를 막지 않는다
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


def _self_recover_step(
    args: argparse.Namespace, results: dict, sr_ns: argparse.Namespace
) -> str | None:
    """self-recover 실행 → **원장 기록** → manual_required 판정 (v1.0.1+).

    원장 append 가 이 step 안에 있는 것이 핵심이다. v1.0.0 에서는 `gh release create`
    성공 뒤(step 6.5b)에 있었는데, `manual_required` 가 1+ 이면 cmd_release 는 그보다
    한참 앞(step 2.7)에서 early return 한다. 즉 **원장에 `manual_required_count > 0`
    인 line 이 기록될 수 있는 경로가 존재하지 않았다** — north-star
    `silent_failing_cycles_count` 는 분자가 구조적으로 도달 불가라 영구히 0 이고,
    release 가 한 번이라도 성공하면 `measured=True` 로 뒤집혀 정직한 *미측정* 이
    "N cycle 재봤더니 0건" 이라는 거짓 초록불이 된다.

    measure 대상(= drift 판정)이 확정되는 지점에서 기록한다. 그래야 clean cycle 은
    분모로, manual cycle 은 분자로 각각 들어간다.

    부수 효과 1: step 6 dashboard emit 보다 앞이므로, release 가 emit 하는 snapshot 이
    **자기 cycle 을 포함**한다 (이전에는 항상 한 cycle 씩 뒤처졌다).
    부수 효과 2: `--skip-self-recover` 면 drift 를 재지 않았으므로 원장에도 남기지
    않는다 (분모에서 빠진다). "안 쟀다" 를 "0건" 으로 적지 않는 쪽이 정직하다.

    Args:
        args: release 의 argparse Namespace (dry_run / version / workspace_root 참조).
        results: cmd_release 의 results dict — self_recover / drift_ledger_append 를 주입.
        sr_ns: cmd_self_recover 에 넘길 Namespace (`_attr_ns()` 산출 — dry_run 상속).

    Returns:
        manual_required 가 1+ 이면 release 를 멈출 error 문자열, 아니면 None.
    """
    sr_result = cmd_self_recover(sr_ns)
    results["self_recover"] = sr_result
    results["drift_ledger_append"] = _append_drift_ledger_entry(args, sr_result)
    manual_required = sr_result.get("manual_required")
    if manual_required:
        return (
            f"self-recover: {len(manual_required)} drift case 가 "
            f"manual_required (human review 필요): {manual_required}. "
            f"fix 후 release 재실행 또는 --skip-self-recover 로 진행."
        )
    return None


# ---------------------------------------------------------------------------
# 4.7 Phase 13 AC4+ bidir-link audit log emit (v0.13.3+)
# ---------------------------------------------------------------------------


def _emit_bidir_link_audit_log(args: argparse.Namespace, bl_log: str) -> dict:
    """bidir-link audit log 를 release note 끝에 append (idempotent marker)."""
    try:
        version = getattr(args, "version", None) or read_version()
        notes_resolution = _resolve_notes_file(version, "default", dry_run=False)
        notes_file = notes_resolution.get("notes_file")
        if not notes_file or not Path(notes_file).exists():
            return {"status": "skipped", "reason": "release note not found (backfill scenario)"}
        body = Path(notes_file).read_text(encoding="utf-8")
        marker = "## Bidirectional link audit"
        if marker in body:
            return {"status": "skipped", "reason": "bidir link audit log already present (idempotent)"}
        new_body = body.rstrip("\n") + "\n" + bl_log
        if atomic_write_text is not None:
            atomic_write_text(notes_file, new_body)
        else:
            notes_file.write_text(new_body, encoding="utf-8")
        return {
            "status": "ok",
            "path": str(notes_file),
            "bytes_appended": len(bl_log),
        }
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# 5. verify (Phase 2 — v0.7.10)
# ---------------------------------------------------------------------------


def cmd_verify(args) -> dict:
    """GitHub Release 의 tag + asset 검증 (read-only)."""
    tag = args.tag
    if tag.startswith("v"):
        tag_full = tag
    else:
        tag_full = f"v{tag}"
    # 1. gh release view (--json tagName,name,url,assets,isPrerelease,publishedAt)
    gh_cmd = [
        "gh", "release", "view", tag_full,
        "--repo", _get_repo(),
        "--json", "tagName,name,url,assets,isPrerelease,publishedAt",
    ]
    results: dict = {"tag": tag_full, "gh_command": " ".join(gh_cmd), "mode": "read-only"}

    if args.dry_run:
        return results

    proc = subprocess.run(gh_cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        return {**results, "error": f"release not found: {tag_full} (gh exit {proc.returncode})"}

    try:
        release_data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return {**results, "error": f"gh release view JSON parse failed: {e}"}

    results["name"] = release_data.get("name")
    results["url"] = release_data.get("url")
    results["is_prerelease"] = release_data.get("isPrerelease")
    results["created_at"] = release_data.get("publishedAt")
    results["assets"] = [a.get("name") for a in release_data.get("assets", [])]
    return results


def _get_repo() -> str:
    """git remote origin → 'owner/repo' 추출."""
    proc = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10,
    )
    return proc.stdout.strip().replace("https://github.com/", "").replace(".git", "")


# ---------------------------------------------------------------------------
# 6. rollback (Phase 2 — v0.7.10)
# ---------------------------------------------------------------------------


def cmd_rollback(args) -> dict:
    """GitHub Release + git tag 삭제 (destructive).

    --dry-run: 삭제 명령만 print, 실제 호출 0.
    --apply: gh release delete + git tag -d + git push --delete origin <tag>.
    """
    tag = args.tag if args.tag.startswith("v") else f"v{args.tag}"
    repo = _get_repo()

    commands = [
        # local tag delete
        ["git", "tag", "-d", tag],
        # remote tag delete
        ["git", "push", "--delete", "origin", tag],
        # gh release delete
        ["gh", "release", "delete", tag, "--repo", repo, "--yes"],
    ]
    results: dict = {
        "tag": tag,
        "repo": repo,
        "commands": [" ".join(c) for c in commands],
        "mode": "dry-run" if args.dry_run else "apply",
    }

    if args.dry_run:
        return results

    # 실제 실행
    executed: list[dict] = []
    for cmd in commands:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        executed.append({
            "cmd": " ".join(cmd),
            "exit_code": proc.returncode,
            "stdout_tail": (proc.stdout or "").strip().split("\n")[-1] if proc.stdout else "",
        })
        if proc.returncode != 0:
            results["error"] = f"command failed: {' '.join(cmd)} (exit {proc.returncode})"
            break
    results["executed"] = executed
    results["ok"] = "error" not in results
    return results


# ---------------------------------------------------------------------------
# 7. dist (Phase 3 — v0.7.11)
# ---------------------------------------------------------------------------


def cmd_dist(args) -> dict:
    """Wheel, sdist, and native plugin archives build.

    pre-check: `build` module 가용성 → 부재 시 graceful fail.
    dry-run: command + PEP 440 normalize 만 print. exit 0.
    apply: subprocess `python3 -m build` 실행. exit code + dist glob 결과 report.

    v0.8.15 (spec §7 + §9 #7): 1-command build + check + TestPyPI simulation.
    `release-dist --apply` = build + twine check + TestPyPI upload simulation.
    `release-dist --apply --production` = + production upload simulation.
    Both `--apply` and `--apply --production` *simulate* upload (no actual PyPI/TestPyPI
    deployment per release channel policy: GitHub Releases only).
    """
    from workflow_kit.plugin_distribution import build_plugin_archives, planned_plugin_archives

    _dist_dir = REPO_ROOT / "dist"
    results: dict = {"mode": "dry-run" if args.dry_run else "apply", "out_dir": str(_dist_dir)}

    # 1) pre-check: build module 가용성
    build_check = _check_build_module()
    results["build_module"] = build_check
    if not build_check["available"]:
        results["error"] = f"build module not installed: {build_check['hint']}"
        return results

    # 2) version read (pyproject.toml)
    try:
        current_version = read_version()
    except Exception as e:  # pragma: no cover
        results["error"] = f"pyproject.toml version read 실패: {e}"
        return results
    results["version"] = current_version
    cmd = _build_command(
        _dist_dir,
        sdist_only=getattr(args, "sdist_only", False),
        wheel_only=getattr(args, "wheel_only", False),
    )
    results["command"] = " ".join(cmd)
    results["expected_pattern"] = f"standard_ai_workflow-{_expected_dist_pattern(current_version)}*"
    results["planned_plugin_archives"] = [
        str(path.relative_to(REPO_ROOT)) for path in planned_plugin_archives(_dist_dir, current_version)
    ]

    # 4) skip-existing check (--skip-existing) — skip build but still run
    #    twine check + upload simulation on existing artifacts (v0.8.15).
    if getattr(args, "skip_existing", False) and _dist_dir.exists():
        existing = find_dist_files(current_version)
        if existing:
            results["mode"] = "skip"
            results["skipped"] = True
            results["existing"] = [f.name for f in existing]
            # Still run post-build steps on existing artifacts.
            twine_check = _twine_check(_dist_dir, timeout=getattr(args, "timeout", 300))
            results["twine_check"] = twine_check
            if not twine_check["ok"]:
                results["error"] = (
                    f"twine check failed: {twine_check.get('error', 'unknown')}"
                )
                results["ok"] = False
                return results
            results["testpypi_simulation"] = _simulate_testpypi_upload(
                existing, current_version,
            )
            if getattr(args, "production", False):
                results["production_simulation"] = _simulate_production_upload(
                    existing, current_version,
                )
            results["plugin_archives"] = (
                results["planned_plugin_archives"]
                if args.dry_run
                else [
                    str(path.relative_to(REPO_ROOT))
                    for path in build_plugin_archives(_dist_dir, version=current_version)
                ]
            )
            results["ok"] = True
            return results

    # 5) dry-run: command plan 만 반환
    if args.dry_run:
        results["plugin_archives"] = results["planned_plugin_archives"]
        results["ok"] = True
        return results

    # 6) apply: subprocess `python3 -m build` 실행
    _dist_dir.mkdir(parents=True, exist_ok=True)
    # 빌드 잔재부터 지운다 (v1.8.1, TASK-2026-09-01-main-001) — 남아 있으면
    # `include_package_data` 기본 True 가 낡은 `SOURCES.txt` 를 읽어, 지금 pyproject 가
    # 선언하지 않은 파일까지 wheel 에 싣는다. 그러면 로컬 산출물과 CI 산출물이 갈리고
    # check_packaging 은 "잘 실린 쪽" 을 재게 된다. 상세는 `_purge_build_residue`.
    results["purged_build_residue"] = _purge_build_residue()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=args.timeout,
            cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        results["error"] = f"build timeout after {args.timeout}s"
        return results

    results["returncode"] = proc.returncode
    # 마지막 5 line 의 stdout/stderr 만 report (full log 은 debug 용)
    out_tail = proc.stdout.strip().splitlines()[-5:] if proc.stdout.strip() else []
    err_tail = proc.stderr.strip().splitlines()[-5:] if proc.stderr.strip() else []
    results["stdout_tail"] = out_tail
    results["stderr_tail"] = err_tail

    if proc.returncode != 0:
        results["error"] = f"build failed: exit {proc.returncode}"
        results["ok"] = False
        return results

    # 7) post-check: dist glob 결과
    built = find_dist_files(current_version)
    results["built"] = [f.name for f in built]
    if not built:
        results["error"] = "no built artifacts found in dist/"
        results["ok"] = False
        return results

    results["plugin_archives"] = [
        str(path.relative_to(REPO_ROOT))
        for path in build_plugin_archives(_dist_dir, version=current_version)
    ]

    # 8) twine check (metadata validation) — spec §7.1 step 2, §9 #7
    twine_check = _twine_check(_dist_dir, timeout=getattr(args, "timeout", 300))
    results["twine_check"] = twine_check
    if not twine_check["ok"]:
        results["error"] = f"twine check failed: {twine_check.get('error', 'unknown')}"
        results["ok"] = False
        return results

    # 9) TestPyPI upload simulation — spec §7.1 step 3, §9 #7.
    # Policy: no actual PyPI/TestPyPI deployment (release channel: GitHub Releases only).
    # We *simulate* the upload by reporting what *would* be uploaded.
    testpypi_sim = _simulate_testpypi_upload(built, current_version)
    results["testpypi_simulation"] = testpypi_sim

    # 10) Production upload simulation (only if --production flag set) — spec §7.1 step 5.
    if getattr(args, "production", False):
        production_sim = _simulate_production_upload(built, current_version)
        results["production_simulation"] = production_sim

    results["ok"] = True
    return results


# ---------------------------------------------------------------------------
# 8. gen-schema (v0.8.0+ — runtime contract → JSON Schema SSOT)
# ---------------------------------------------------------------------------
# v0.7.59+ spec §6.1 정공법: Pydantic v2 model registry 의 모든 output/error schema 를
# JSON Schema (draft-07) 으로 dump. runtime contract (workflow_kit.common.output_contracts) 와
# byte-identical 임을 CI 의 `gen-schema --check` 가 검증. read-only MCP manifest 의
# outputSchema 가 generated schema 와 byte-identical 임을 assertion test 가 강제.
GEN_SCHEMA_DEFAULT_OUTPUT = REPO_ROOT / "schemas" / "generated_output_schemas.json"


def cmd_gen_schema(args) -> dict:
    """JSON Schema bundle 을 output path 에 write (또는 --check 으로 byte-identical 검증).

    Args:
        --output=PATH: 출력 file path (default: schemas/generated_output_schemas.json).
        --check: byte-identical 검증 (write 안 함, CI gate).
        --dry-run: write 안 함, write plan 만 출력.
        --json: JSON output.
        --family=NAME: 단일 family 만 dump (default: all families).
    """
    results: dict = {}
    output_path = Path(args.output) if args.output else GEN_SCHEMA_DEFAULT_OUTPUT
    results["output_path"] = str(output_path)
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from workflow_kit.common.output_contracts import output_json_schema_bundle, PYDANTIC_MODEL_REGISTRY
    except ImportError as e:
        results["error"] = f"output_contracts import failed: {type(e).__name__}: {e}"
        results["ok"] = False
        return results
    # 2. dump
    try:
        bundle = output_json_schema_bundle()
    except Exception as e:  # noqa: BLE001
        results["error"] = f"output_json_schema_bundle failed: {type(e).__name__}: {e}"
        results["ok"] = False
        return results
    # 3. family filter
    if args.family:
        if args.family not in bundle:
            results["error"] = f"family not in bundle: {args.family}. available: {sorted(bundle.keys())[:5]}..."
            results["ok"] = False
            return results
        bundle = {args.family: bundle[args.family]}
    results["family_count"] = len(bundle)
    results["registry_count"] = len(PYDANTIC_MODEL_REGISTRY)
    # 4. JSON encode (sort_keys=True 로 byte-identical 보장)
    try:
        encoded = json.dumps(bundle, sort_keys=True, indent=2, default=str)
    except (TypeError, ValueError) as e:
        results["error"] = f"JSON encode failed: {type(e).__name__}: {e}"
        results["ok"] = False
        return results
    results["encoded_bytes"] = len(encoded.encode("utf-8"))
    # 5. --check: byte-identical 검증 (no write)
    if args.check:
        if not output_path.exists():
            results["error"] = f"--check: output file does not exist: {output_path}"
            results["ok"] = False
            return results
        existing = output_path.read_text(encoding="utf-8")
        if existing != encoded:
            results["error"] = (
                f"--check: drift detected. existing={len(existing)} bytes, "
                f"expected={len(encoded)} bytes"
            )
            results["ok"] = False
            return results
        results["check_status"] = "identical"
        results["ok"] = True
        return results
    # 6. --dry-run: write 안 함
    if args.dry_run:
        results["dry_run_status"] = "plan-only"
        results["ok"] = True
        return results
    # 7. write (atomic)
    if atomic_write_text is not None:
        try:
            atomic_write_text(output_path, encoded)
        except Exception as e:  # noqa: BLE001
            results["error"] = f"atomic_write failed: {type(e).__name__}: {e}"
            results["ok"] = False
            return results
    else:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(encoded, encoding="utf-8")
        except OSError as e:
            results["error"] = f"write failed: {type(e).__name__}: {e}"
            results["ok"] = False
            return results
    results["written"] = str(output_path)
    results["ok"] = True
    return results


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(
        description="standard-ai-workflow release pipeline (v0.7.9+)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # validate
    p_val = sub.add_parser("validate", help="release-readiness 검증 (4 source + mypy)")
    p_val.add_argument("--skip-packaging", action="store_true", help="check_packaging skip")
    p_val.add_argument("--skip-doctor", action="store_true", help="doctor skip")
    p_val.add_argument("--skip-state", action="store_true", help="state.json check skip")
    p_val.add_argument("--skip-git", action="store_true", help="git status check skip")
    p_val.add_argument("--skip-mypy", action="store_true", help="mypy strict check skip (v0.11.12+)")
    p_val.add_argument("--dry-run", action="store_true")
    p_val.add_argument("--json", action="store_true")

    # version-bump (v0.7.14+ auto-sync workflow_kit/__init__.py)
    p_vb = sub.add_parser("version-bump", help="pyproject.toml version patch + workflow_kit/__init__.py __version__ auto-sync")
    p_vb.add_argument("--patch", action="store_true", help="patch bump (default)")
    p_vb.add_argument("--minor", action="store_true", help="minor bump")
    p_vb.add_argument("--major", action="store_true", help="major bump")
    p_vb.add_argument("--to", help="explicit version (e.g. 0.7.9)")
    p_vb.add_argument("--no-init", action="store_true", dest="no_init",
                       help="workflow_kit/__init__.py __version__ sync skip (CI / override 시나리오)")
    p_vb.add_argument("--dry-run", action="store_true", dest="dry_run",
                       help="bump plan 만 출력 (default: --apply)")
    p_vb.add_argument("--apply", dest="apply", action="store_true", default=True)
    p_vb.add_argument("--skip-sync-hash", action="store_true", dest="skip_sync_hash",
                       help="post-step sync_release_hash 자동 호출 skip (TASK-V0726-003, manual override)")
    p_vb.add_argument("--allow-dirty", action="store_true", dest="allow_dirty",
                       help="dirty working tree 여도 진행 (v1.0.0 guard override — amend 가 "
                            "미커밋 작업을 흡수할 수 있음)")
    p_vb.add_argument("--allow-pushed-amend", action="store_true", dest="allow_pushed_amend",
                       help="HEAD 가 이미 push 된 경우에도 post-step amend 허용 (원격 history 재작성)")
    p_vb.add_argument("--json", action="store_true", help="JSON output (CI integration)")

    # note-draft
    p_nd = sub.add_parser("note-draft", help="release note skeleton 자동 생성")
    p_nd.add_argument("--from", dest="from_tag", required=True, help="이전 release tag (e.g. v0.7.8)")
    p_nd.add_argument("--to", required=True, help="새 release version (e.g. 0.7.9)")
    p_nd.add_argument("--dry-run", action="store_true", dest="dry_run")
    p_nd.add_argument("--apply", dest="apply", action="store_true", default=True)

    # doc-headers-update (v0.11.23+ — drift prevention P1)
    p_dhu = sub.add_parser(
        "doc-headers-update",
        help="docs/* + workflow-source/core/* + README.md 의 '- 최종 수정일' 헤더를 일괄 갱신 (drift prevention)",
    )
    p_dhu.add_argument("--scope", default="all", choices=["all", "docs", "core", "readme"],
                       help="대상 scope (default: all)")
    p_dhu.add_argument("--date", default=None,
                       help="YYYY-MM-DD override (default: UTC today)")
    p_dhu.add_argument("--dry-run", action="store_true", dest="dry_run",
                       help="plan 만 출력 (write 안 함)")
    p_dhu.add_argument("--apply", dest="apply", action="store_true", default=True,
                       help="default: apply. --dry-run 으로 override")
    p_dhu.add_argument("--json", action="store_true")

    # sync-maturity-matrix (v0.11.23+ — drift prevention P2)
    p_smm = sub.add_parser(
        "sync-maturity-matrix",
        help=(
            "Release note (Beta-v<X>.md) 의 YAML frontmatter (closed_phases / promoted_skills / "
            "added_harnesses / deprecated_symbols) 를 읽어 workflow-source/core/maturity_matrix.json 자동 patch. "
            "drift prevention P2 핵심."
        ),
    )
    p_smm.add_argument("--from-release-note", required=True, dest="from_release_note",
                       help="Release note 경로 (e.g. workflow-source/releases/Beta-v0.11.23.md)")
    p_smm.add_argument("--dry-run", action="store_true", dest="dry_run",
                       help="plan 만 출력 (write 안 함)")
    p_smm.add_argument("--apply", dest="apply", action="store_true", default=True,
                       help="default: apply. --dry-run 으로 override")
    p_smm.add_argument("--json", action="store_true")

    # bidir-link (Phase 13 AC4+ — v0.13.3+, wiki ↔ memory 양방향 link sync + audit)
    p_bl = sub.add_parser(
        "bidir-link",
        help=(
            "Phase 13 AC4+ wiki ↔ memory 양방향 link 자동화. "
            "default: audit (read-only, R-C). --apply 로 sync (R-A). "
            "memory entry.mentioned_in → wiki related_pages 자동 갱신."
        ),
    )
    p_bl.add_argument("--workspace-root", dest="workspace_root", default=None,
                      help="workspace root (default: release --apply 의 cwd)")
    p_bl.add_argument("--apply", dest="apply", action="store_true", default=False,
                      help="sync 적용 (R-A, default: audit only)")
    p_bl.add_argument("--json", action="store_true")

    # self-recover (Phase 13 AC3 — v0.13.2+, drift prevention P3)
    p_sr = sub.add_parser(
        "self-recover",
        help=(
            "drift prevention smoke 의 FAIL case 자동 fix (Phase 13 AC3). "
            "detect → classify (auto_fixable / manual_required) → fix → re-check → emit. "
            "default: dry-run. --apply 로 실제 fix."
        ),
    )
    p_sr.add_argument("--apply", dest="apply", action="store_true", default=False,
                      help="fix 적용 (default: dry-run)")
    p_sr.add_argument("--dry-run", action="store_true", dest="dry_run",
                      help="plan 만 출력 (write 안 함, default)")
    p_sr.add_argument("--json", action="store_true")

    # changelog-gen (Phase 4 — v0.7.14+, Keep-a-Changelog 형식, v0.7.15+ filter)
    p_cl = sub.add_parser("changelog-gen", help="multi-release git log → CHANGELOG.md 본문 (Keep-a-Changelog 형식)")
    p_cl.add_argument("--output", default=None,
                      help="output file path (default: workflow-source/CHANGELOG.md)")
    p_cl.add_argument("--unreleased-label", default="Unreleased",
                      help="unreleased commit group 의 label (default: 'Unreleased')")
    p_cl.add_argument("--from-tag", default=None,
                      help="git log 시작 ref (e.g. v0.7.0-beta). 미지정 시 --all (전체 history)")
    p_cl.add_argument("--to-tag", default="HEAD",
                      help="git log 종료 ref (default: HEAD)")
    p_cl.add_argument("--dry-run", action="store_true", dest="dry_run")
    p_cl.add_argument("--apply", dest="apply", action="store_true", default=True)
    p_cl.add_argument("--json", action="store_true")

    # release (Phase 2 — v0.7.10, v0.7.13+ --version)
    p_rel = sub.add_parser("release", help="GitHub Release 생성 (gh release create)")
    p_rel.add_argument("--skip-validate", action="store_true", help="validate 사전 점검 skip")
    p_rel.add_argument("--skip-cross-verify", action="store_true",
                       help="mypy CI cross-verify skip (v0.11.13+, advisory 만 default)")
    p_rel.add_argument("--strict-cross-verify", action="store_true",
                       help="mypy CI cross-verify 시 drift / ci_stale / ci_fail hard fail (v0.11.13+)")
    p_rel.add_argument("--skip-ci-verify", dest="skip_ci_verify",
                       action="store_true", default=False,
                       help=("필수 CI 워크플로 게이트 skip (v1.8.1). 기본은 **차단**이다 — "
                             "REQUIRED_CI_WORKFLOWS 가 HEAD sha 에서 전부 green 이 아니면 "
                             "--apply 가 멈춘다. 넘기면 결과에 그 사실이 남는다"))
    p_rel.add_argument("--skip-self-recover", dest="skip_self_recover",
                       action="store_true", default=False,
                       help="drift prevention: Phase 13 AC3 self-recover step skip (v0.13.2+, manual override 용)")
    p_rel.add_argument("--skip-bidir-link", dest="skip_bidir_link",
                       action="store_true", default=False,
                       help="Phase 13 AC4+: wiki ↔ memory bidir-link audit step skip (v0.13.3+, manual override 용)")
    p_rel.add_argument("--skip-doc-headers-update", dest="skip_doc_headers_update",
                       action="store_true", default=False,
                       help="drift prevention: docs/ - 최종 수정일 헤더 자동 갱신 step skip (v0.11.23+)")
    p_rel.add_argument("--skip-maturity-matrix-sync", dest="skip_maturity_matrix_sync",
                       action="store_true", default=False,
                       help="drift prevention: release note frontmatter → maturity_matrix.json 자동 patch step skip (v0.11.23+)")
    # v0.7.24 에서 _resolve_notes_file() 은 구현됐으나 argparse 등록이 누락돼 CLI 로는
    # 쓸 수 없었다 (`unrecognized arguments: --notes-template`). v1.0.0 에서 노출 복원.
    p_rel.add_argument("--notes-template", dest="notes_template", default="default",
                       help="release notes 형식: default / detailed / simple / changelog / "
                            "custom:<path> (v0.7.24+)")
    p_rel.add_argument("--skip-changelog-gen", dest="skip_changelog_gen",
                       action="store_true", default=False,
                       help="drift prevention: CHANGELOG.md git-log 재생성 step skip (v0.15.21+)")
    p_rel.add_argument("--skip-smoke-count-check", dest="skip_smoke_count_check",
                       action="store_true", default=False,
                       help="release note 의 `누적 smoke **N/N PASS**` 검증 step skip (v1.1.3+)")
    p_rel.add_argument("--version", default=None,
                       help="version override (e.g. 0.7.5 for backfill). default: pyproject.toml [project] version")
    p_rel.add_argument("--auto-bump", dest="auto_bump", action="store_true", default=False,
                       help="remote tag pre-check fail 시 다음 version 으로 자동 bump + re-flow. "
                            "v0.7.18+: release coordination observability.")
    p_rel.add_argument("--allow-existing-tag", dest="allow_existing_tag", action="store_true", default=False,
                       help="remote tag pre-check 가 'already exists' 일 때 *skip* + 그대로 release 진행. "
                            "v0.7.21+ follow-up: tag push 와 release 의 coupling fix.")
    p_rel.add_argument("--full-auto", dest="full_auto", action="store_true", default=False,
                       help="release pipeline 1-step cycle close (v0.9.1+ automation): "
                            "pre-check conflict 시 자동으로 --auto-bump 동작 (다음 version 결정 + "
                            "version-bump + re-flow) 후 새로 결정된 tag 로 release 진행. "
                            "여전히 conflict 면 --allow-existing-tag 로 fallback. "
                            "최종적으로 *operator intervention 없이* tag push + gh release create "
                            "완료. release 채널 정책 (docs/RELEASE.md \u00a71: --dry-run 필수) 유지 — "
                            "본 flag 는 --dry-run 과 동시 사용 가능 (plan 검증용).")
    p_rel.add_argument("--dry-run", action="store_true", dest="dry_run",
                       help="destructive subcommand 정공법 (memory #5): tag push + gh release create 의 "
                            "plan 만 출력, 실제 호출 0. v1.1.4+ 부터 --apply 미지정 시 dry-run 이 "
                            "기본이므로 본 flag 는 명시용 (--apply 와 함께 주면 dry-run 이 이긴다).")
    p_rel.add_argument("--apply", dest="apply", action="store_true", default=False,
                       help="실제 발행 (tag push + gh release create). v1.1.4+ 기본값 반전 — "
                            "이전에는 default True 라 무인자 `release` 가 APPLY 로 진입했다. "
                            "되돌리기 어려운 명령의 기본은 dry-run 이다 (claim_workspace / "
                            "install_pre_push_hook / host_pull_registry 와 정합).")
    # 개별 pre_check skip (v1.1.4+): 이전에는 --skip-validate 뿐이라 doctor 하나를
    # 건너뛰려면 packaging/git/mypy 게이트까지 통째로 꺼야 했다 — 게이트 무력화를
    # 강요하는 all-or-nothing. validate subcommand 와 같은 5 flag 를 노출한다.
    p_rel.add_argument("--skip-packaging", action="store_true", default=False,
                       help="pre_check 중 packaging check 만 skip")
    p_rel.add_argument("--skip-doctor", action="store_true", default=False,
                       help="pre_check 중 doctor baseline check 만 skip")
    p_rel.add_argument("--skip-state", action="store_true", default=False,
                       help="pre_check 중 state.json freshness check 만 skip")
    p_rel.add_argument("--skip-git", action="store_true", default=False,
                       help="pre_check 중 git clean check 만 skip")
    p_rel.add_argument("--skip-mypy", action="store_true", default=False,
                       help="pre_check 중 mypy strict check 만 skip")
    p_rel.add_argument("--json", action="store_true")
    p_rel.add_argument(
        "--legacy-memory", dest="legacy_memory", default=None,
        action=argparse.BooleanOptionalAction,
        help="v0.15.0+ ⚠️ BREAKING 정렬. --no-legacy-memory (strict opt-out) 면 "
             "step 6.7 maturity refresh skip (silent fallback 비활성 caller 정합). "
             "default: None (정공법 진행).",
    )

    # refresh-maturity (v0.14.6+ Task 3 follow-up)
    p_rm = sub.add_parser(
        "refresh-maturity",
        help="maturity_matrix.json 의 `last_updated` field 자동 갱신 (Task 3 follow-up, v0.14.6+). "
             "idempotent. --dry-run 으로 plan 만 emit 가능. "
             "default: workflow-source/core/maturity_matrix.json.",
    )
    p_rm.add_argument("--today", dest="today", default=None,
                      help="명시적 today override (default: date.today().isoformat())")
    p_rm.add_argument("--maturity-path", dest="maturity_path", default=None,
                      help="maturity_matrix.json 의 path (default: workflow-source/core/maturity_matrix.json)")
    p_rm.add_argument("--dry-run", action="store_true", dest="dry_run",
                      help="dry-run mode — 실제 last_updated 갱신 안 함, plan 만 emit")
    p_rm.add_argument("--apply", dest="apply", action="store_true", default=True)
    p_rm.add_argument("--json", action="store_true")
    p_rm.add_argument(
        "--legacy-memory", dest="legacy_memory", default=None,
        action=argparse.BooleanOptionalAction,
        help="v0.15.0+ ⚠️ BREAKING 정렬. --no-legacy-memory (strict opt-out) 면 "
             "maturity refresh skip + warning emit (silent fallback 비활성 caller 정합). "
             "default: None (skip 없이 정공법 진행).",
    )
    p_rel.add_argument("--skip-dashboard-emit", dest="skip_dashboard_emit",
                       action="store_true", default=False,
                       help="dashboard markdown post-release 자동 emit skip (v0.13.1+ Phase 13). "
                            "default: emit. 실패 시 release 자체는 성공.")
    p_rel.add_argument("--dashboard-output", dest="dashboard_output", default=None,
                       help="dashboard snapshot 출력 경로 (default: ai-workflow/dashboard/snapshot.md). "
                            "v0.13.1+ Phase 13.")

    # gen-schema (v0.8.0+ — runtime contract → JSON Schema SSOT)
    p_gs = sub.add_parser("gen-schema", help="JSON Schema bundle dump (Pydantic v2 → JSON Schema draft-07). v0.8.0+ SSOT")
    p_gs.add_argument("--output", help="출력 file path (default: schemas/generated_output_schemas.json)")
    p_gs.add_argument("--check", action="store_true", help="byte-identical 검증 (write 안 함, CI gate)")
    p_gs.add_argument("--dry-run", action="store_true", dest="dry_run", help="write 안 함, plan 만 출력")
    p_gs.add_argument("--family", help="단일 family 만 dump (default: all families)")
    p_gs.add_argument("--json", action="store_true", help="JSON output")

    # verify (Phase 2 — v0.7.10)
    p_ver = sub.add_parser("verify", help="GitHub Release 의 tag + asset 검증 (read-only)")
    p_ver.add_argument("--tag", required=True, help="tag 이름 (e.g. v0.7.9-beta 또는 0.7.9)")
    p_ver.add_argument("--dry-run", action="store_true", dest="dry_run")
    # `--apply` 가 없으면 아래의 "둘 다 미지정 → dry-run" 기본값 때문에 verify 는
    # **항상** early return 하고, `gh release view` 를 부르는 본문 전체가 CLI 에서
    # 도달 불가능한 죽은 코드가 된다. verify 는 read-only(조회만) 이므로 --apply 는
    # 안전하며, rollback / dist 와 플래그 체계가 일치한다.
    p_ver.add_argument("--apply", dest="apply", action="store_true",
                       help="실제로 gh release view 를 호출해 검증 (기본은 command plan 만 출력)")
    p_ver.add_argument("--json", action="store_true")

    # rollback (Phase 2 — v0.7.10)
    p_rb = sub.add_parser("rollback", help="GitHub Release + git tag 삭제 (destructive)")
    p_rb.add_argument("--tag", required=True, help="tag 이름 (e.g. v0.7.9-beta 또는 0.7.9)")
    p_rb.add_argument("--dry-run", action="store_true", dest="dry_run")
    p_rb.add_argument("--apply", dest="apply", action="store_true", default=True)
    p_rb.add_argument("--json", action="store_true")

    # dist (Phase 3 — v0.7.11)
    p_dist = sub.add_parser("dist", help="wheel + sdist 자동 빌드 (`python3 -m build`)")
    p_dist.add_argument("--sdist-only", action="store_true", help="sdist 만 빌드")
    p_dist.add_argument("--wheel-only", action="store_true", help="wheel 만 빌드")
    p_dist.add_argument("--skip-existing", action="store_true", help="dist/ 의 current-version 파일 있으면 skip")
    p_dist.add_argument("--timeout", type=int, default=300, help="subprocess timeout in sec (default 300)")
    p_dist.add_argument("--dry-run", action="store_true", dest="dry_run")
    p_dist.add_argument("--apply", dest="apply", action="store_true", default=False,
                        help="실제 빌드 실행. v1.1.5+ 기본값 반전 — 이전에는 default True 라 "
                             "무인자 `dist` 가 빌드를 수행했다 (release 와 같은 결함, "
                             "main() 의 '둘 다 없으면 dry-run' 정규화가 무력화돼 있었다). "
                             "lib wrapper (`cmd_dist(apply=False)`) 와 이제 정합.")
    p_dist.add_argument("--production", action="store_true", help="simulate production PyPI upload (after TestPyPI sim). actual upload not performed per release policy.")
    p_dist.add_argument("--json", action="store_true")

    args = p.parse_args()
    if getattr(args, "dry_run", False):
        args.apply = False
    if not getattr(args, "dry_run", False) and not getattr(args, "apply", False):
        # default = dry-run when neither flag is specified
        args.dry_run = True

    if args.command == "validate":
        result = cmd_validate(args)
    elif args.command == "version-bump":
        result = cmd_version_bump(args)
    elif args.command == "note-draft":
        result = cmd_note_draft(args)
    elif args.command == "changelog-gen":
        result = cmd_changelog_gen(args)
    elif args.command == "doc-headers-update":
        result = cmd_doc_headers_update(args)
    elif args.command == "sync-maturity-matrix":
        result = cmd_maturity_matrix_sync(args)
    elif args.command == "self-recover":
        result = cmd_self_recover(args)
    elif args.command == "bidir-link":
        result = cmd_bidir_link(args)
    elif args.command == "release":
        result = cmd_release(args)
    elif args.command == "refresh-maturity":
        result = cmd_refresh_maturity(args)
    elif args.command == "verify":
        result = cmd_verify(args)
    elif args.command == "rollback":
        result = cmd_rollback(args)
    elif args.command == "dist":
        result = cmd_dist(args)
    elif args.command == "gen-schema":
        result = cmd_gen_schema(args)
    else:
        p.error(f"unknown command: {args.command}")
        return 2

    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        dry_run = getattr(args, "dry_run", False)
        mode_label = "DRY-RUN" if dry_run else "APPLY"
        if args.command == "verify":
            mode_label = "READ-ONLY"
        print(f"=== {args.command} ({mode_label}) ===")
        for k, v in result.items():
            if isinstance(v, dict):
                print(f"  {k}:")
                for k2, v2 in v.items():
                    if isinstance(v2, list) and len(str(v2)) > 80:
                        print(f"    {k2}: [{', '.join(str(x) for x in v2[:3])}...]")
                    else:
                        print(f"    {k2}: {v2}")
            elif isinstance(v, list):
                if len(str(v)) > 80:
                    print(f"  {k}: [{', '.join(str(x) for x in v[:3])}...]")
                else:
                    print(f"  {k}: {v}")
            else:
                print(f"  {k}: {v}")

    # exit code: validate / release / verify / rollback / dist 의 ok/error 기반
    if args.command in ("validate", "release", "verify", "rollback", "dist"):
        if "error" in result:
            return 1
        if args.command in ("release", "rollback", "dist") and not result.get("ok", True):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
