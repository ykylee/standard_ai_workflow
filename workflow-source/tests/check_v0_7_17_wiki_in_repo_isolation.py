#!/usr/bin/env python3
"""v0.7.17+: wiki in-repo storage isolation smoke test.

외부 vault (`~/wiki/`) 와 본 project 의 연결 완전 차단. 본 project 의 wiki 가
*전부 in-repo* (`ai-workflow/wiki/` + `ai-workflow/memory/active/`) 에서 관리됨.

Test 구성 (9 test):
1. tools/refresh_wiki_memory.py: VAULT_ROOT/RAW_BASE/L2_BASE 가 in-repo path
2. tools/refresh_wiki_memory.py: l1_sources() 가 해석하는 L1 SSOT 4종이 in-repo (+ 은퇴한 write 경로 부재)
3. tools/refresh_wiki_memory.py: L2_STUBS 의 4 file 이 ai-workflow/wiki/sources/ 안
4. tools/emit_wiki_l2_body.py: 은퇴 후 경로 상수·git 호출 부재 (외부 vault 흔적 0)
5. tools/emit_wiki_l2_body.py: 은퇴 모듈이 저장소 경로를 해석하지 않음
6. tools/score_wiki_maintainability.py: L2_SOURCES 가 INREPO_WIKI/sources
7. tests/check_refresh_wiki_memory.py: VAULT_ROOT reference 없음
8. tests/check_wiki_drift.py: _raw_mtime 이 in-repo path 만 사용
9. 본 repo 의 ai-workflow/wiki/sources/ dir 존재 + .gitkeep 정합

Reference:
- workflow-source/workflow_kit/tools/refresh_wiki_memory.py (v0.7.17 본 release)
- workflow-source/workflow_kit/tools/emit_wiki_l2_body.py
- workflow-source/workflow_kit/tools/score_wiki_maintainability.py
- workflow-source/tests/check_refresh_wiki_memory.py
- workflow-source/tests/check_wiki_drift.py
- ai-workflow/wiki/sources/ (L2 dense emit target, 본 release 신규)
- memory "wiki in-repo isolation" (cross-project storage SSOT 패턴)
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "ai-workflow/wiki/sources/*",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/*",
    "workflow-source/workflow_kit/*",
)

import importlib.util
import re
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SOURCE_ROOT.parent
INREPO_WIKI = REPO_ROOT / "ai-workflow" / "wiki"
INREPO_MEMORY = REPO_ROOT / "ai-workflow" / "memory" / "active"


def _import_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# --- Test 1: refresh_wiki_memory 의 in-repo path ---


def test_refresh_wiki_memory_no_vault_root():
    """refresh_wiki_memory.py 에 VAULT_ROOT = Path.home() / 'wiki' 가 *없어야*."""
    src = _read(SOURCE_ROOT / "workflow_kit" / "tools" / "refresh_wiki_memory.py")
    assert "Path.home() / \"wiki\"" not in src, (
        "refresh_wiki_memory.py: VAULT_ROOT = Path.home() / 'wiki' 가 외부 vault 참조. "
        "in-repo path 로 redirect 필요 (v0.7.17)."
    )
    assert "VAULT_ROOT" not in src, (
        "refresh_wiki_memory.py: VAULT_ROOT 변수가 남아 있음. 제거 또는 in-repo path 로."
    )


def test_refresh_wiki_memory_raw_files_in_repo():
    """refresh_wiki_memory 가 읽는 L1 SSOT 가 전부 in-repo 경로다.

    이전에는 소스에서 `"memory/active/state.json"` 같은 **문자열이 보이는지**
    를 봤다. 그 단언은 (a) 경로 조립을 resolver 로 옮기면 문자열이 사라져 헛
    red 가 되고 (b) 정작 해석된 경로가 저장소 밖이어도 통과한다. L1 이 *쓰는*
    대상이 아니라 *읽는* 대상이 된 지금(TASK-2026-08-18-main-004,
    `RAW_FILES` 은퇴) 재야 할 것은 해석 결과다.
    """
    import importlib

    sys.path.insert(0, str(SOURCE_ROOT))
    mod = importlib.import_module("workflow_kit.tools.refresh_wiki_memory")
    importlib.reload(mod)

    sources = mod.l1_sources()
    assert set(sources) == set(mod.L2_STUBS), f"L1 SSOT 목록 불일치: {sorted(sources)}"
    repo_root = Path(mod.REPO_ROOT).resolve()

    # 후보 경로는 **부재해도** 해석된다. 부재 자체는 결함이 아니다 — 브랜치
    # 컨텍스트(`slash`)에는 그 브랜치의 `state.json` 이 아예 없고, 그 경우를
    # `l1_sources()` 는 None 으로, emit 은 `missing_l1` 로 밝힌다. 여기서 잴 것은
    # "있는가" 가 아니라 **어디를 가리키는가** 다.
    candidates = {
        "active-state": mod._active_path("state.json"),
        "active-session-handoff": mod._active_path("session_handoff.md"),
        "active-work-backlog": mod.latest_backlog_path() or mod._active_path("backlog"),
        "wiki-log": mod.L1_BASE / "wiki" / "log.md",
    }
    for name, path in candidates.items():
        resolved = Path(path).resolve()
        assert resolved.is_relative_to(repo_root), f"{name}: in-repo 밖 — {resolved}"
        assert "raw/projects" not in str(resolved), f"{name}: 외부 raw mirror path 잔존"
        assert (Path.home() / "wiki") not in resolved.parents, f"{name}: 외부 vault path 잔존"

    # 은퇴한 write 경로가 되살아나지 않았는가 (두 번째 writer 방지)
    src = _read(SOURCE_ROOT / "workflow_kit" / "tools" / "refresh_wiki_memory.py")
    for banned in ("RAW_FILES", "update_state_json", "update_work_backlog"):
        assert banned not in src, f"은퇴한 write 경로 잔존: {banned}"


def test_refresh_wiki_memory_l2_stubs_in_repo():
    """L2_STUBS 의 4 file 이 ai-workflow/wiki/sources/ 안."""
    src = _read(SOURCE_ROOT / "workflow_kit" / "tools" / "refresh_wiki_memory.py")
    l2_section = re.search(
        r"L2_STUBS\s*=\s*\{(.*?)\}",
        src,
        re.DOTALL,
    )
    assert l2_section is not None, "L2_STUBS dict 없음"
    # 4 stub name 이 있어야
    for stub in ["active-state", "active-work-backlog", "active-session-handoff", "wiki-log"]:
        assert stub in l2_section.group(1), f"L2_STUBS 에 {stub} 없음"
    # 외부 wiki/projects/.../sources/ 가 없어야
    assert "wiki/projects" not in l2_section.group(1), "L2_STUBS 에 외부 wiki/projects path 남아 있음"
    assert "Path.home() / \"wiki\"" not in l2_section.group(1), "L2_STUBS 에 VAULT_ROOT 흔적"


# --- Test 2: emit_wiki_l2_body 의 in-repo path ---


def test_emit_wiki_l2_body_no_vault_root():
    """emit_wiki_l2_body.py 에 외부 vault 흔적이 없다.

    이 모듈은 2026-08-20(TASK-2026-08-20-main-001)에 **은퇴**했다 — L1 wiki page
    파생 뷰의 근거였던 외부 vault retrieval 자체가 v0.7.17 in-repo 전환 때
    사라졌기 때문이다. 그래서 여기서 재는 것은 "in-repo path 를 쓰는가" 가 아니라
    **경로를 아예 안 만지는가** 다. (경로 계약은 `check_wiki_emit_pipeline` 이
    생성기 쪽에서 잡는다.)
    """
    src = _read(SOURCE_ROOT / "workflow_kit" / "tools" / "emit_wiki_l2_body.py")
    assert "Path.home() / \"wiki\"" not in src, "외부 vault 참조 잔존"
    for gone in ("RAW_MIRROR", "L2_SOURCES", "VAULT_ROOT"):
        assert gone not in src, f"은퇴 후에도 경로 상수 잔존: {gone}"


def test_emit_wiki_l2_body_repo_root_auto_detect():
    """은퇴한 모듈이 저장소 경로를 스스로 해석하지 않는다.

    이전 계약은 "`_detect_repo_root` 가 git rev-parse 를 쓴다" 였다. write 0 인
    지금은 **경로를 알 필요가 없다** — 남겨 두면 다음 사람이 그 위에 기능을
    다시 얹는다.
    """
    src = _read(SOURCE_ROOT / "workflow_kit" / "tools" / "emit_wiki_l2_body.py")
    assert "_detect_repo_root" not in src, "은퇴 모듈에 repo root 해석이 남아 있음"
    assert "git rev-parse" not in src, "은퇴 모듈에 git 호출이 남아 있음"


# --- Test 3: score_wiki_maintainability 의 in-repo path ---


def test_score_wiki_maintainability_l2_in_repo():
    """score_wiki_maintainability.py 의 L2_SOURCES 가 INREPO_WIKI/sources."""
    src = _read(SOURCE_ROOT / "workflow_kit" / "tools" / "score_wiki_maintainability.py")
    assert "L2_SOURCES = INREPO_WIKI / \"sources\"" in src, (
        "L2_SOURCES 가 in-repo path 가 아님"
    )
    # 외부 VAULT_ROOT 흔적 없어야
    assert "Path.home() / \"wiki\"" not in src, (
        "score_wiki_maintainability.py: VAULT_ROOT 가 남아 있음"
    )


# --- Test 4: test 파일의 in-repo path ---


def test_check_refresh_wiki_memory_no_vault_root():
    """tests/check_refresh_wiki_memory.py 에 VAULT_ROOT = Path.home() / 'wiki' 없음."""
    src = _read(SOURCE_ROOT / "tests" / "check_refresh_wiki_memory.py")
    # docstring / comment 의 *legacy* mention 은 OK. active code 에만 없으면.
    # "VAULT_ROOT" 변수가 *active code* 에 남아 있는지 확인.
    # heuristic: import + line 35 (line number may shift) 의 `VAULT_ROOT = ` line
    # 단순하게: `VAULT_ROOT = ` 가 *단일* 발생 (line 35 의 comment 한정).
    active_assignment = re.search(r"^VAULT_ROOT\s*=\s*Path\.home\(\)\s*/\s*\"wiki\"", src, re.MULTILINE)
    assert active_assignment is None, (
        "check_refresh_wiki_memory.py: VAULT_ROOT = Path.home() / 'wiki' 가 active code 에 남아 있음"
    )


def test_check_wiki_drift_raw_mtime_in_repo():
    """tests/check_wiki_drift.py 의 _raw_mtime 이 REPO_ROOT 기반 in-repo path."""
    src = _read(SOURCE_ROOT / "tests" / "check_wiki_drift.py")
    # _raw_mtime 함수의 body 가 REPO_ROOT / raw_path 사용
    fn_match = re.search(
        r"def _raw_mtime.*?(?=\ndef |\nclass |\Z)",
        src,
        re.DOTALL,
    )
    assert fn_match is not None, "_raw_mtime 함수 없음"
    fn_body = fn_match.group(0)
    assert "REPO_ROOT" in fn_body, "_raw_mtime 이 REPO_ROOT 사용 안 함"
    assert "VAULT_ROOT" not in fn_body, "_raw_mtime 이 VAULT_ROOT 사용 (외부 vault 참조)"
    # docstring comment 의 *legacy* mention 은 OK
    assert "Path.home() / \"wiki\"" not in fn_body, (
        "_raw_mtime 이 Path.home() / 'wiki' 사용 (외부 vault)"
    )


# --- Test 5: in-repo dir 존재 + .gitkeep 정합 ---


def test_inrepo_sources_dir_exists():
    """ai-workflow/wiki/sources/ dir + .gitkeep 존재 (v0.7.17+ 신규)."""
    sources_dir = INREPO_WIKI / "sources"
    assert sources_dir.exists(), f"sources dir 없음: {sources_dir}"
    assert sources_dir.is_dir(), f"sources 가 dir 아님: {sources_dir}"
    gitkeep = sources_dir / ".gitkeep"
    assert gitkeep.exists(), f".gitkeep 없음: {gitkeep}"
    # .gitkeep 의 주석이 in-repo storage 정합성 명시
    content = gitkeep.read_text(encoding="utf-8")
    assert "in-repo" in content or "v0.7.17" in content, (
        ".gitkeep 주석에 in-repo storage 정합성 명시 필요"
    )


def test_inrepo_memory_log_exists():
    """ai-workflow/memory/log.md 존재 (refresh 가 갱신할 대상)."""
    log_path = REPO_ROOT / "ai-workflow" / "memory" / "log.md"
    assert log_path.exists(), f"memory/log.md 없음: {log_path}"


def test_inrepo_no_legacy_symlink_or_legacy_path():
    """본 repo 에 legacy symlink (~/repos/standard_ai_workflow_minimax) 흔적 없음."""
    # memory #21 의 REPO_ROOT 4-priority auto-detect 도입 이후 legacy fallback 의
    # _LEGACY_REPO_ROOT 상수만 정공법 (deprecation 경고 + symlink 제거 후).
    # in-repo dir 구조에 ~/repos/ 흔적이 *없어야*.
    legacy = REPO_ROOT / "ai-workflow" / "raw" / "projects"  # in-repo 에 *raw* dir 이면 외부 vault 흔적
    assert not legacy.exists(), f"in-repo 에 raw dir 흔적: {legacy} (외부 vault mirror 가 in-repo 로 들어옴)"


# --- 메인 실행 ---


def main() -> int:
    test_funcs = [
        test_refresh_wiki_memory_no_vault_root,
        test_refresh_wiki_memory_raw_files_in_repo,
        test_refresh_wiki_memory_l2_stubs_in_repo,
        test_emit_wiki_l2_body_no_vault_root,
        test_emit_wiki_l2_body_repo_root_auto_detect,
        test_score_wiki_maintainability_l2_in_repo,
        test_check_refresh_wiki_memory_no_vault_root,
        test_check_wiki_drift_raw_mtime_in_repo,
        test_inrepo_sources_dir_exists,
        test_inrepo_memory_log_exists,
        test_inrepo_no_legacy_symlink_or_legacy_path,
    ]
    passed = 0
    failed = 0
    for func in test_funcs:
        try:
            func()
            print(f"  PASS  {func.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {func.__name__}: {e}")
            failed += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {func.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print()
    print(f"{passed} pass, {failed} fail")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
