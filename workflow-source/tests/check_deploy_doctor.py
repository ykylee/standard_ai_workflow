#!/usr/bin/env python3
"""`wk doctor` 배포 탐침의 계약을 고정한다 (TASK-2026-08-14-main-016 · main-005).

탐침은 **보고만 하는 도구**다. 그래서 이 검사가 지켜야 할 것은 "정답을 내는가"
보다 아래 셋이다:

1. **아무것도 쓰지 않는다** (컨셉 §5.2) — 양쪽 기설치는 오류가 아니라 상태이고,
   어느 쪽도 임의로 지우지 않는다. 트리 스냅샷 대조로 고정한다.
2. **실 홈을 읽지 않는다** — `home` 주입이 실제로 먹지 않으면 이 검사는 개발자의
   진짜 `~/.claude/settings.json` 을 읽게 되고, 그 순간 결과가 호스트마다 갈린다.
3. **존재를 적용으로 세지 않는다** — 마커 없는 파일 하나가 5개 하네스를 적용됨으로
   만든 실측(2026-08-16)을 되주입으로 고정한다.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.bootstrap_lib.harnesses import (  # noqa: E402
    HARNESS_SPECS,
    SUPPORTED_HARNESSES,
)
from workflow_kit.deploy_doctor import (  # noqa: E402
    CHANNEL_PREREQUISITES,
    GLOBAL_DECLARATION_HOMES,
    PLUGIN_INSTALL_CACHES,
    main as doctor_main,
    probe,
)
from workflow_kit.plugin_distribution import PLUGIN_HARNESS_SPECS, _included  # noqa: E402
from workflow_kit.plugin_payload import render_agent_plugin  # noqa: E402

#: fixture 가 흉내 내는 "설치된 버전". 정본 버전과 같아야 이 파일들이 재려는
#: 상황(버전 동일 · 내용만 낡음)이 성립한다.
from workflow_kit import __version__ as INSTALLED_VERSION  # noqa: E402

FAILURES: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS: {case}")
    else:
        print(f"FAIL: {case}{(' — ' + detail) if detail else ''}")
        FAILURES.append(case)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _tree_digest(root: Path) -> str:
    """트리의 경로 + 내용 해시. 쓰기가 있었는지 판정하는 유일한 근거."""
    parts: list[str] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_dir():
            parts.append(f"d:{rel}")
            continue
        parts.append(f"f:{rel}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _fixture(tmp: Path, *, marker_version: str | None = "1.0.0", declare_global: bool = True) -> tuple[Path, Path]:
    """claude-code 산출물이 깔린 프로젝트 + 글로벌 선언이 있는 홈."""
    project = tmp / "project"
    home = tmp / "home"
    spec = HARNESS_SPECS["claude-code"]
    for rel in (*spec.entry_files, *spec.extra_files):
        head = f"<!-- standard-ai-workflow-kit: v{marker_version} -->\n\n" if marker_version else ""
        _write(project / rel, f"{head}# probe\n")
    if declare_global:
        _write(
            home / ".claude" / "settings.json",
            json.dumps({"enabledPlugins": {"standard-ai-workflow@standard-ai-workflow": True}}),
        )
    return project, home


# --- Case 1 ----------------------------------------------------------------


def test_report_shape() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        project, home = _fixture(Path(tmpdir))
        report = probe(project_root=project, home=home)
    missing = [
        key
        for key in ("environment", "project_scope", "global_scope", "drift", "findings")
        if key not in report
    ]
    _record(
        "test_report_shape",
        not missing and report.get("report_only") is True,
        f"누락 {missing} / report_only={report.get('report_only')}",
    )


# --- Case 2 ----------------------------------------------------------------


def test_probe_writes_nothing() -> None:
    """report-only 계약 (§5.2) — 탐침이 프로젝트도 홈도 건드리지 않는다."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        project, home = _fixture(tmp)
        before_project, before_home = _tree_digest(project), _tree_digest(home)
        probe(project_root=project, home=home)
        after_project, after_home = _tree_digest(project), _tree_digest(home)
        # 되주입: 지문이 쓰기를 실제로 구분하는가. 이게 없으면 지문이 죽어도 green 이다.
        _write(project / "probe-canary.md", "written\n")
        canary = _tree_digest(project)
    problems: list[str] = []
    if before_project != after_project or before_home != after_home:
        problems.append("탐침이 트리를 변경했다 — report-only 계약 위반")
    if canary == after_project:
        problems.append("트리 지문이 쓰기를 구분하지 못한다 — 이 case 는 무엇도 판정하지 못한다")
    _record("test_probe_writes_nothing", not problems, "; ".join(problems))


# --- Case 3 ----------------------------------------------------------------


def test_home_injection_is_honored() -> None:
    """주입한 홈만 읽는가.

    이게 깨지면 검사가 개발자의 진짜 홈을 읽고, 결과가 호스트마다 갈린다.
    빈 홈을 주면 어떤 하네스도 선언돼 있지 않아야 한다 — 실 홈에는 있는데도.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        project, _ = _fixture(tmp, declare_global=False)
        empty_home = tmp / "empty-home"
        empty_home.mkdir()
        report = probe(project_root=project, home=empty_home)
    global_scope = report["global_scope"]
    _record(
        "test_home_injection_is_honored",
        global_scope["declared_harnesses"] == []
        and global_scope["home"] == str(empty_home.resolve()),
        f"declared={global_scope['declared_harnesses']} home={global_scope['home']}",
    )


# --- Case 4 ----------------------------------------------------------------


def test_presence_without_marker_is_not_applied() -> None:
    """되주입: 마커를 지우면 '적용됨' 이 아니라 '후보' 여야 한다.

    실측(2026-08-16) — 다른 도구가 쓴 `AGENTS.md` 하나가 codex/grok-build/
    minimax-code/opencode/pi-dev **5개**를 적용됨으로 만들었다. 존재는 적용이
    아니다 (§3: kit 소유의 표식은 버전 마커다).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        marked_project, home = _fixture(tmp / "a", marker_version="1.0.0")
        unmarked_project, _ = _fixture(tmp / "b", marker_version=None)
        marked = probe(project_root=marked_project, home=home)["project_scope"]
        unmarked = probe(project_root=unmarked_project, home=home)["project_scope"]
    problems: list[str] = []
    if "claude-code" not in marked["applied_harnesses"]:
        problems.append("마커가 있는데 applied 로 안 셌다")
    if "claude-code" in unmarked["applied_harnesses"]:
        problems.append("마커가 없는데 applied 로 셌다 — 과보고 회귀")
    if "claude-code" not in unmarked["candidate_harnesses"]:
        problems.append("마커 없는 하네스를 candidate 로도 안 보고했다 — 조용히 사라졌다")
    _record("test_presence_without_marker_is_not_applied", not problems, "; ".join(problems))


# --- Case 5 ----------------------------------------------------------------


def test_stale_marker_is_reported() -> None:
    """낡은 마커를 드리프트로 보고하는가 (§7 gap 3)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        project, home = _fixture(tmp, marker_version="0.0.1")
        _write(project / "ai-workflow" / "VERSION", "1.2.0\n")
        stale = probe(project_root=project, home=home)["drift"]

        fresh_project, _ = _fixture(tmp / "fresh", marker_version="1.2.0")
        _write(fresh_project / "ai-workflow" / "VERSION", "1.2.0\n")
        fresh = probe(project_root=fresh_project, home=home)["drift"]
    problems: list[str] = []
    if not stale["stale_markers"]:
        problems.append("낡은 마커를 못 잡았다")
    if fresh["stale_markers"]:
        problems.append(f"최신 마커를 낡음으로 잡았다 (위양성): {fresh['stale_markers']}")
    if stale["kit_version"] != "1.2.0":
        problems.append(f"ai-workflow/VERSION 을 기준으로 안 썼다: {stale['kit_version']}")
    _record("test_stale_marker_is_reported", not problems, "; ".join(problems))


# --- Case 6 ----------------------------------------------------------------


def test_both_scopes_detected_and_not_removed() -> None:
    """양쪽 기설치를 **감지하고 보고**하되 지우지 않는다 (§5.2)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        project, home = _fixture(tmp, declare_global=True)
        before = _tree_digest(home)
        report = probe(project_root=project, home=home)
        after = _tree_digest(home)
    drift = report["drift"]
    _record(
        "test_both_scopes_detected_and_not_removed",
        drift["installed_in_both_scopes"] == ["claude-code"] and before == after,
        f"both={drift['installed_in_both_scopes']} home_changed={before != after}",
    )


# --- Case 7 ----------------------------------------------------------------


def test_strict_flag_governs_return_code() -> None:
    """기본은 rc 0 (보고는 실패가 아니다), `--strict` 일 때만 rc 1."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        project, home = _fixture(tmp, marker_version="0.0.1")
        _write(project / "ai-workflow" / "VERSION", "1.2.0\n")
        args = ["--project-root", str(project), "--home", str(home), "--json"]
        # 보고 본문은 이 case 의 판정 대상이 아니다 — 검사 출력을 덮지 않도록 삼킨다.
        with contextlib.redirect_stdout(io.StringIO()):
            rc_default = doctor_main(args)
            rc_strict = doctor_main([*args, "--strict"])
    _record(
        "test_strict_flag_governs_return_code",
        rc_default == 0 and rc_strict == 1,
        f"default={rc_default} strict={rc_strict}",
    )


# --- Case 8 ----------------------------------------------------------------


def test_registries_are_derived_not_copied() -> None:
    """탐침의 목록이 정본에서 파생되는가 (§2 선언 계약).

    글로벌 거주지 표에 registry 에 없는 하네스가 들어가면 유령 항목이 되고,
    반대로 프로젝트 절이 `HARNESS_SPECS` 를 안 읽고 손 목록을 들면 하네스를
    추가해도 탐침이 모른다.
    """
    problems: list[str] = []
    ghosts = [e.harness for e in GLOBAL_DECLARATION_HOMES if e.harness not in SUPPORTED_HARNESSES]
    if ghosts:
        problems.append(f"registry 에 없는 하네스: {ghosts}")
    dupes = [e.harness for e in GLOBAL_DECLARATION_HOMES]
    if len(dupes) != len(set(dupes)):
        problems.append("글로벌 거주지 표에 중복 하네스가 있다")

    # 되주입: HARNESS_SPECS 에 없는 파일은 프로젝트 절이 보지 않아야 한다.
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        project, home = _fixture(tmp)
        _write(project / "NOT_A_HARNESS_FILE.md", "<!-- standard-ai-workflow-kit: v9.9.9 -->\n")
        report = probe(project_root=project, home=home)
    seen = {
        record["path"]
        for info in report["project_scope"]["harnesses"].values()
        for record in info["files_present"]
    }
    if "NOT_A_HARNESS_FILE.md" in seen:
        problems.append("registry 밖 파일을 산출물로 셌다")
    _record("test_registries_are_derived_not_copied", not problems, "; ".join(problems))


# --- Case 9 ----------------------------------------------------------------


def test_dispatcher_registers_doctor() -> None:
    """`wk doctor` 로 실제 도달하는가 — 모듈만 있고 등록이 빠지면 기능이 없는 것과 같다."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "workflow_kit.workflow_kit_cli",
            "--command=doctor",
            "--json",
            "--project-root",
            str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
        cwd=str(SOURCE_ROOT),
        env={"PYTHONPATH": str(SOURCE_ROOT), "PATH": "/usr/bin:/bin", "HOME": str(REPO_ROOT)},
    )
    ok = proc.returncode == 0
    payload: dict[str, object] = {}
    if ok:
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            ok = False
    _record(
        "test_dispatcher_registers_doctor",
        ok and payload.get("report_only") is True,
        f"rc={proc.returncode} stderr={proc.stderr.strip()[:160]}",
    )


def _seed_cache(home: Path, harness: str) -> Path:
    """해당 채널의 설치 사본을 **정본 그대로** 만든다. 반환값은 사본 루트."""
    entry = next(e for e in PLUGIN_INSTALL_CACHES if e.harness == harness)
    # glob 의 `*` 를 실제 이름으로 채운다 — 레지스트리의 모양을 그대로 쓴다.
    parts = [p.replace("*standard-ai-workflow*", "standard-ai-workflow").replace("*", "standard-ai-workflow")
             for p in entry.glob.split("/")]
    # 버전 디렉터리 이름은 **현재 패키지 버전**에서 온다. 리터럴을 박으면 릴리스마다
    # 이 fixture 가 red 가 되고, 그때 고치는 것은 계약이 아니라 그 시점 상수다.
    # 이 case 의 전제는 "설치 버전 == 정본 버전, 내용만 낡음" 이므로 같은 출처를 쓴다.
    root = (home.joinpath(*parts[:-1], INSTALLED_VERSION)
            if parts[-1] == "standard-ai-workflow" else home.joinpath(*parts))
    spec = PLUGIN_HARNESS_SPECS.get(harness)
    for rel, body in render_agent_plugin().items():
        if spec is not None and not _included(rel, spec):
            continue
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return root


def test_content_drift_clean_install_is_in_sync() -> None:
    """정본 그대로 깐 사본은 드리프트가 아니다 — 거짓 양성이 없어야 쓸 수 있다."""
    with tempfile.TemporaryDirectory(prefix="doctor-drift-") as tmp:
        home = Path(tmp) / "home"
        _seed_cache(home, "codex")
        report = probe(project_root=Path(tmp), home=home)
        caches = report["content_drift"]["caches"]
        _record(
            "test_content_drift_clean_install_is_in_sync",
            len(caches) == 1 and caches[0]["in_sync"] is True and not report["content_drift"]["out_of_sync"],
            json.dumps(caches, ensure_ascii=False)[:300],
        )


def test_content_drift_catches_same_version_stale_payload() -> None:
    """**핵심 case.** 버전은 그대로, 내용만 낡은 상태를 잡는가.

    2026-08-16 에 Codex 설치본이 정확히 이 상태였다 — 마커도 디렉터리 이름도
    `1.2.0` 으로 정본과 같은데 페이로드만 구버전이었다. 마커 비교로는 원리적으로
    안 걸리므로, 이 case 가 red 를 못 내면 gap 3 은 닫힌 것이 아니다.
    """
    with tempfile.TemporaryDirectory(prefix="doctor-drift-") as tmp:
        home = Path(tmp) / "home"
        root = _seed_cache(home, "codex")
        victim = next(p for p in sorted(root.rglob("*.md")) if p.is_file())
        victim.write_text(victim.read_text(encoding="utf-8") + "\n<!-- 낡은 페이로드 -->\n",
                          encoding="utf-8")
        report = probe(project_root=Path(tmp), home=home)
        content = report["content_drift"]
        cache = content["caches"][0]
        paths = [d["path"] for d in cache["differs"]]
        ok = (
            cache["in_sync"] is False
            and content["out_of_sync"] == ["codex"]
            and str(victim.relative_to(root)) in paths
            and cache["installed_version"] == INSTALLED_VERSION
            and any("codex" in f for f in content["findings"])
        )
        _record(
            "test_content_drift_catches_same_version_stale_payload",
            ok,
            json.dumps(cache, ensure_ascii=False)[:300],
        )


def test_content_drift_expects_only_channel_files() -> None:
    """채널이 담지 않는 파일을 '없음' 으로 세지 않는다.

    codex 는 매니페스트·MCP·skills 만 담는다. payload 20개를 그대로 기대하면
    정상 설치가 **없음 10건**으로 보고된다 (2026-08-18 실측). 기대치는 손 목록이
    아니라 `PLUGIN_HARNESS_SPECS.include_prefixes` 에서 파생돼야 한다.
    """
    with tempfile.TemporaryDirectory(prefix="doctor-drift-") as tmp:
        home = Path(tmp) / "home"
        _seed_cache(home, "codex")
        cache = probe(project_root=Path(tmp), home=home)["content_drift"]["caches"][0]
        full = len(render_agent_plugin())
        _record(
            "test_content_drift_expects_only_channel_files",
            not cache["missing"] and 0 < cache["files_compared"] < full,
            f"compared={cache['files_compared']} full={full} missing={cache['missing']}",
        )


def test_content_drift_writes_nothing() -> None:
    """report-only 계약은 새 절에도 그대로다 (컨셉 §5.2)."""
    with tempfile.TemporaryDirectory(prefix="doctor-drift-") as tmp:
        home = Path(tmp) / "home"
        _seed_cache(home, "claude-code")
        before = _tree_digest(home)
        probe(project_root=Path(tmp), home=home)
        _record("test_content_drift_writes_nothing", _tree_digest(home) == before)


def test_preflight_separates_measured_from_declared() -> None:
    """**핵심 case.** 측정한 것과 선언만 한 것을 섞지 않는가.

    네트워크 도달성처럼 재지 않은 전제를 `installable` 에 넣으면 탐침이 *모름*
    을 *괜찮음* 으로 보고하게 된다 — 이 저장소가 규칙으로 삼은 `모름 ≠ 안전`
    이다. `installable` 은 **측정 가능한 전제(실행 파일)만** 반영해야 하고,
    선언뿐인 전제는 별도 키로 남아야 한다.
    """
    with tempfile.TemporaryDirectory(prefix="doctor-preflight-") as tmp:
        report = probe(project_root=Path(tmp), home=Path(tmp) / "home")
        pf = report["preflight"]
        declared_total = sum(len(e.declared) for e in CHANNEL_PREREQUISITES)
        seen_declared = sum(len(c["declared_unmeasured"]) for c in pf["channels"])
        ok = (
            len(pf["channels"]) == len(CHANNEL_PREREQUISITES)
            and seen_declared == declared_total
            and all(
                c["installable"] == (not c["missing_executables"])
                for c in pf["channels"]
            )
            and "모름을 통과로 세지 않는다" in pf["measurement_note"]
        )
        _record(
            "test_preflight_separates_measured_from_declared",
            ok,
            json.dumps(pf, ensure_ascii=False)[:300],
        )


def test_preflight_blocks_channel_with_missing_executable() -> None:
    """없는 실행 파일이 있으면 그 채널은 `blocked` 로 보고된다.

    PATH 를 비운 채로 재면 **모든 채널**이 막혀야 한다 — 하나라도 통과하면
    측정이 실제로 이뤄지지 않고 있다는 뜻이다.
    """
    import os

    with tempfile.TemporaryDirectory(prefix="doctor-preflight-") as tmp:
        saved = os.environ.get("PATH", "")
        os.environ["PATH"] = str(Path(tmp) / "empty-bin")
        try:
            report = probe(project_root=Path(tmp), home=Path(tmp) / "home")
        finally:
            os.environ["PATH"] = saved
        pf = report["preflight"]
        ok = (
            pf["ready_channels"] == []
            and sorted(pf["blocked_channels"]) == sorted(e.channel for e in CHANNEL_PREREQUISITES)
            and len(pf["findings"]) == len(CHANNEL_PREREQUISITES)
        )
        _record(
            "test_preflight_blocks_channel_with_missing_executable",
            ok,
            f"ready={pf['ready_channels']} blocked={pf['blocked_channels']}",
        )


def test_preflight_writes_nothing() -> None:
    """report-only 계약은 preflight 절에도 그대로다."""
    with tempfile.TemporaryDirectory(prefix="doctor-preflight-") as tmp:
        home = Path(tmp) / "home"
        home.mkdir()
        before = _tree_digest(home)
        probe(project_root=Path(tmp), home=home)
        _record("test_preflight_writes_nothing", _tree_digest(home) == before)


def main() -> int:
    test_report_shape()
    test_probe_writes_nothing()
    test_home_injection_is_honored()
    test_presence_without_marker_is_not_applied()
    test_stale_marker_is_reported()
    test_both_scopes_detected_and_not_removed()
    test_strict_flag_governs_return_code()
    test_registries_are_derived_not_copied()
    test_dispatcher_registers_doctor()
    test_content_drift_clean_install_is_in_sync()
    test_content_drift_catches_same_version_stale_payload()
    test_content_drift_expects_only_channel_files()
    test_content_drift_writes_nothing()
    test_preflight_separates_measured_from_declared()
    test_preflight_blocks_channel_with_missing_executable()
    test_preflight_writes_nothing()
    total = 16
    print(f"\n{total - len(FAILURES)}/{total} passed")
    if FAILURES:
        raise AssertionError(f"{len(FAILURES)} case(s) failed: {FAILURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
