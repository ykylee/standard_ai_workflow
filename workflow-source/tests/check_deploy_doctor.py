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

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/core/*",
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
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
    VOLATILE_PATH_PREFIXES,
    _render_text,
    GLOBAL_DECLARATION_HOMES,
    PLUGIN_INSTALL_CACHES,
    _parse_etime,
    _pip_absence_verdict,
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


# --- Case 1b ---------------------------------------------------------------


def test_pip_absence_reads_uv_tool_receipt() -> None:
    """pip 부재 판정은 선언(`uv-receipt.toml`)을 읽는다 — 잰 단위를 결과에 남긴다.

    되주입 계보 (2026-08-24, main-009): `wk` 를 `uv tool install` 로 깐 호스트에서
    'venv 에 pip 이 없다' 가 **상시 오탐**이었다 — 탐침이 자기 인터프리터(도구
    venv)를 재면서 개발 `.venv` 를 향한 처방(ensurepip)을 냈고, 그 venv 에는
    pip 이 이미 있었다. uv tool venv 의 pip 부재는 설계다.
    """
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        prefix = Path(tmpdir) / "toolvenv"
        prefix.mkdir()
        # 선언 없는 venv → 결함 finding + 잰 인터프리터 명시
        verdict, finding = _pip_absence_verdict(prefix, "/x/bin/python")
        if verdict != "defect":
            problems.append(f"선언 없는 venv 인데 verdict={verdict!r}")
        if not finding:
            problems.append("finding 이 없다")
        elif "/x/bin/python" not in finding:
            problems.append("finding 이 잰 인터프리터를 명시하지 않는다 — 처방이 엉뚱한 venv 로 간다")
        # 선언 있는 venv → by-design, finding 없음 (안 낸 이유는 라벨로 남는다)
        (prefix / "uv-receipt.toml").write_text("[tool]\n", encoding="utf-8")
        verdict2, finding2 = _pip_absence_verdict(prefix, "/x/bin/python")
        if verdict2 != "by_design_uv_tool":
            problems.append(f"uv-receipt.toml 을 선언으로 읽지 않는다 — verdict={verdict2!r}")
        if finding2 is not None:
            problems.append("설계상 부재를 결함으로 보고한다 (오탐 재현)")
    _record("test_pip_absence_reads_uv_tool_receipt", not problems, "; ".join(problems))


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


def test_forked_entry_is_not_advised_to_reapply() -> None:
    """포크를 선언한 진입점은 **낡음이 아니라 갈라짐**이다 (§3 소유권 4분류).

    되주입 실측(2026-08-20): 이 저장소의 `CLAUDE.md` 는 마커가 낡았고 탐침은
    그것을 "재적용 대상" 으로 조언했다. 조언대로 재적용하면 측정으로 얻은
    운영 규칙 90여 줄이 `TODO` placeholder 로 바뀐다 — **갱신이 상태를 나쁘게
    만드는 조언은 틀린 조언이다.** 그렇다고 숨기지도 않는다: 갈라져 나온
    버전을 같이 내야 그 버전과 diff 해 병합할 수 있다.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        project, home = _fixture(tmp, marker_version="0.0.1")
        _write(project / "ai-workflow" / "VERSION", "1.2.0\n")
        before = probe(project_root=project, home=home)["drift"]

        entry = project / "CLAUDE.md"
        entry.write_text(
            "<!-- standard-ai-workflow-kit: v0.0.1 -->\n"
            "<!-- standard-ai-workflow-kit-fork: project owns this -->\n\n# probe\n",
            encoding="utf-8",
        )
        after = probe(project_root=project, home=home)["drift"]

    problems: list[str] = []
    if "CLAUDE.md" not in [record["path"] for record in before["stale_markers"]]:
        problems.append("선언 전에는 낡음으로 잡혀야 한다 — 되주입이 성립하지 않는다")
    if "CLAUDE.md" in [record["path"] for record in after["stale_markers"]]:
        problems.append("포크를 선언했는데 여전히 '재적용 대상' 으로 조언한다")
    forked_paths = [record["path"] for record in after.get("forked_files", [])]
    if "CLAUDE.md" not in forked_paths:
        problems.append(f"포크된 파일을 보고하지 않았다 — 조용히 사라졌다: {forked_paths}")
    else:
        record = next(r for r in after["forked_files"] if r["path"] == "CLAUDE.md")
        if record.get("forked_from") != "0.0.1":
            problems.append(
                f"갈라져 나온 버전을 잃었다 ({record.get('forked_from')}) — "
                "그 버전과의 diff 가 유일한 병합 경로다"
            )
    if not any("포크" in finding for finding in after["findings"]):
        problems.append("findings 에 포크 상태를 안 냈다")
    _record("test_forked_entry_is_not_advised_to_reapply", not problems, "; ".join(problems))


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


def test_kit_resolution_flags_foreign_checkout() -> None:
    """실행 인터프리터가 project root 밖에서 workflow_kit 을 해석하면 두 경로를 명시해 보고한다 (main-019).

    '탐침은 잰 단위가 맞아야 한다'의 4번째 단위 = 해석되는 패키지의 출처.
    61차 실측: 전역 도구가 다른 체크아웃(v1.1.8-beta)의 workflow_kit 을 조용히
    돌려 legacy 산출물이 이 저장소로 나갔다. by-design 두 자리(자기 checkout ·
    인터프리터 site-packages)는 finding 없이 라벨만 남고, 그 밖은 잰 인터프리터·
    해석 출처·project root 를 **전부** 명시한 finding 이 최상위 findings 까지
    도달해야 한다 — 증거는 소비 지점까지 가야 한다 (50차 규칙).
    """
    import sys as _sys

    from workflow_kit.deploy_doctor import _kit_resolution_verdict

    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="doctor-kitres-") as tmp:
        root = Path(tmp) / "project"
        (root / "workflow-source" / "workflow_kit").mkdir(parents=True)
        own = root / "workflow-source" / "workflow_kit" / "__init__.py"
        own.write_text("", encoding="utf-8")

        label, finding = _kit_resolution_verdict(None, root, _sys.executable)
        if (label, finding) != ("not_importable", None):
            problems.append(f"None origin: {label}")

        label, finding = _kit_resolution_verdict(own, root, _sys.executable)
        if (label, finding) != ("project_checkout", None):
            problems.append(f"own checkout: {label}, {finding}")

        site = Path(_sys.prefix) / "lib" / "site-packages" / "workflow_kit" / "__init__.py"
        label, finding = _kit_resolution_verdict(site, root, _sys.executable)
        if (label, finding) != ("interpreter_site_packages", None):
            problems.append(f"site-packages: {label}, {finding}")

        foreign = Path(tmp) / "other-checkout" / "workflow_kit" / "__init__.py"
        label, finding = _kit_resolution_verdict(foreign, root, _sys.executable)
        if label != "foreign_path" or finding is None:
            problems.append(f"foreign origin not flagged: {label}")
        else:
            for needle in (_sys.executable, str(foreign), str(root)):
                if needle not in finding:
                    problems.append(f"finding 에 경로 누락: {needle}")

        # 실 probe 에서 판정 라벨이 payload 에 남고, foreign 이면 최상위 findings
        # 까지 도달하는가 — 조용한 통과 금지.
        report = probe(project_root=root, home=Path(tmp) / "home")
        env = report["environment"]
        if "kit_resolution" not in env:
            problems.append("environment 에 kit_resolution 키가 없다")
        elif env["kit_resolution"] == "foreign_path":
            if not any("해석 출처" in f for f in report["findings"]):
                problems.append("foreign finding 이 최상위 findings 에 안 닿았다")
    _record("test_kit_resolution_flags_foreign_checkout", not problems, "; ".join(problems))


def test_preflight_bootstrap_channel_resolves_platform_launcher() -> None:
    """bootstrap 채널의 인터프리터 전제는 emit 과 같은 정본으로 플랫폼을 따른다 (main-017).

    win32 에서 emit 되는 command 는 `python` 이므로 preflight 도 `python` 을 재야
    한다 — `python3` 리터럴을 재면 emit 이 뜨는 호스트를 blocked 로 보고한다
    (61차 실측: Windows 에서 6채널 전부 block 의 주원인). 반대로 플러그인 채널은
    payload 가 `python3` 를 체크인하므로 (platform="posix" 고정) **리터럴 그대로**
    재야 한다 — 완화하면 payload 가 못 뜨는 호스트가 green 이 된다. 세 자리
    (payload 리터럴 · 채널 전제 · launcher 정본)를 대조한다.
    """
    from workflow_kit import deploy_doctor as _dd
    from workflow_kit.common.python_launcher import (
        POSIX_PYTHON,
        WIN32_PYTHON,
        python_launcher,
    )
    from workflow_kit.plugin_payload import _payload_mcp_entry

    problems: list[str] = []
    if python_launcher("win32") != WIN32_PYTHON or python_launcher("linux") != POSIX_PYTHON:
        problems.append("python_launcher 매핑이 관례와 다르다")

    # payload 리터럴 ↔ 플러그인 채널 전제 3자 대조 — 갈라지면 전제가 거짓말한다.
    _, payload_cmd = _payload_mcp_entry()
    plugin_entries = [e for e in CHANNEL_PREREQUISITES if e.channel != "bootstrap"]
    if not all(payload_cmd[0] in e.executables for e in plugin_entries):
        problems.append(f"플러그인 채널 전제에 payload command {payload_cmd[0]!r} 가 없다")
    if any(e.launcher_adaptive for e in plugin_entries):
        problems.append("플러그인 채널이 launcher_adaptive 다 — payload 는 리터럴을 spawn 한다")

    # sys.platform 전역 패치는 이 호스트의 shutil.which 까지 win32 분기로 민다
    # (_winapi 부재로 크래시) — probe 가 부르는 이음새(python_launcher)만 바꾼다.
    saved_launcher = _dd.python_launcher
    _dd.python_launcher = lambda platform=None: python_launcher("win32")
    try:
        pf = _dd._probe_preflight()
    finally:
        _dd.python_launcher = saved_launcher
    boot = next(c for c in pf["channels"] if c["channel"] == "bootstrap")
    plugin = next(c for c in pf["channels"] if c["channel"] == "claude-code")
    if WIN32_PYTHON not in boot["executables"] or POSIX_PYTHON in boot["executables"]:
        problems.append(f"win32 에서 bootstrap 채널이 잰 이름: {sorted(boot['executables'])}")
    if POSIX_PYTHON not in plugin["executables"]:
        problems.append(f"win32 에서도 플러그인 채널은 python3 을 재야 한다: {sorted(plugin['executables'])}")
    _record(
        "test_preflight_bootstrap_channel_resolves_platform_launcher",
        not problems,
        "; ".join(problems),
    )


def test_preflight_writes_nothing() -> None:
    """report-only 계약은 preflight 절에도 그대로다."""
    with tempfile.TemporaryDirectory(prefix="doctor-preflight-") as tmp:
        home = Path(tmp) / "home"
        home.mkdir()
        before = _tree_digest(home)
        probe(project_root=Path(tmp), home=home)
        _record("test_preflight_writes_nothing", _tree_digest(home) == before)


def test_content_drift_declares_surface_as_unmeasured() -> None:
    """`in_sync` 를 **쓸 수 있음**으로 읽지 않게 한계를 명시한다 (2026-08-20).

    실측: 설치본의 `skills/` 가 정본과 in-sync 였고 `claude plugin details` 도
    `Skills (4)` 로 셌는데, 세션에는 그중 하나도 로드되지 않았다
    (`Unknown skill: standard-ai-workflow:doc-sync`). 이 절이 재는 것은
    **파일이 같은가** 이지 **하네스가 그것을 노출하는가** 가 아니다.

    노출은 세션이 켜져 봐야 알 수 있어 탐침 밖이다. 그러면 재지 못한다고
    **말해야** 한다 — `installable` 이 "설치 성공" 이 아니듯이
    (main-019 와 같은 원칙). 이 선언이 사라지면 다음 사람이 in_sync 를
    "쓸 수 있음" 으로 읽는다.
    """
    with tempfile.TemporaryDirectory(prefix="doctor-unmeasured-") as tmp:
        report = probe(project_root=Path(tmp), home=Path(tmp) / "home")
    content = report.get("content_drift") or {}
    declared = content.get("declared_unmeasured")
    problems = []
    if not isinstance(declared, list) or not declared:
        problems.append(f"declared_unmeasured 가 비었다: {declared!r}")
    elif not any("노출" in item for item in declared):
        problems.append(f"노출 미측정 선언이 없다: {declared!r}")
    _record("test_content_drift_declares_surface_as_unmeasured", not problems, "; ".join(problems))


# --- Case 18~20 ------------------------------------------------------------


def _runtime_fixture(tmp: Path) -> Path:
    """claude-code 플러그인이 깔린 홈 — 설치 시각 선언까지 포함."""
    home = tmp / "home"
    root = home / ".claude" / "plugins" / "cache" / "mp" / "standard-ai-workflow" / "1.2.0"
    root.mkdir(parents=True, exist_ok=True)
    _write(
        home / ".claude" / "plugins" / "installed_plugins.json",
        json.dumps(
            {
                "version": 2,
                "plugins": {
                    "standard-ai-workflow@mp": [
                        {"scope": "user", "version": "1.2.0", "installedAt": _INSTALL_ISO}
                    ]
                },
            }
        ),
    )
    return home


#: fixture 가 선언하는 설치 시각. **문자열 하나에서 파생**한다 — epoch 를 손으로
#: 적으면 그 상수가 fixture 와 조용히 갈린다 (첫 작성 때 실제로 1년 어긋났다).
_INSTALL_ISO = "2026-08-18T00:57:53.300Z"
_INSTALL_EPOCH = datetime.fromisoformat(_INSTALL_ISO.replace("Z", "+00:00")).timestamp()


def test_runtime_load_flags_host_older_than_install() -> None:
    """**세션이 아니라 프로세스를 잰다** (2026-08-20 실측, main-009).

    되주입하는 상황: 플러그인이 in-sync 이고 인벤토리도 4종을 세는데 세션에서
    부르면 `Unknown skill` 이던 자리. 원인은 충돌이 아니라 **시간**이었다 —
    호스트 프로세스가 설치보다 35시간 먼저 시작했고, 플러그인은 프로세스 시작
    때 로드된다. 대화를 새로 여는 것으로는 그 프로세스가 바뀌지 않는다.
    """
    with tempfile.TemporaryDirectory(prefix="doctor-runtime-") as tmpdir:
        home = _runtime_fixture(Path(tmpdir))
        now = _INSTALL_EPOCH + 3600
        report = probe(
            project_root=Path(tmpdir) / "project",
            home=home,
            now=now,
            # 설치보다 35시간 먼저 시작한 호스트 — 실측 그대로의 배치다.
            processes=[{"pid": 6397, "command": "claude", "elapsed_sec": 3600 + 35 * 3600}],
        )
    runtime = report.get("runtime_load") or {}
    channels = runtime.get("channels") or []
    problems = []
    if runtime.get("stale") != ["claude-code"]:
        problems.append(f"낡은 채널이 안 잡혔다: {runtime.get('stale')!r}")
    if not any("pid 6397" in item for item in runtime.get("findings", [])):
        problems.append(f"finding 에 pid 가 없다: {runtime.get('findings')!r}")
    if not any("재시작" in item for item in runtime.get("findings", [])):
        problems.append("finding 이 재시작을 말하지 않는다 — 사용자가 할 일이 빠진다")
    if channels and channels[0].get("install_time_source") != "installed_plugins.json":
        problems.append(f"설치 시각 출처를 안 남겼다: {channels[0].get('install_time_source')!r}")
    if not any("pid 6397" in item for item in report.get("findings", [])):
        problems.append("절의 finding 이 보고서 상위로 안 올라갔다")
    _record("test_runtime_load_flags_host_older_than_install", not problems, "; ".join(problems))


def test_runtime_load_clears_host_started_after_install() -> None:
    """재시작한 호스트는 낡지 않았다 — 경고가 남으면 그 뒤로 아무도 안 읽는다."""
    with tempfile.TemporaryDirectory(prefix="doctor-runtime-ok-") as tmpdir:
        home = _runtime_fixture(Path(tmpdir))
        now = _INSTALL_EPOCH + 7200
        report = probe(
            project_root=Path(tmpdir) / "project",
            home=home,
            now=now,
            # 설치 뒤 1시간에 시작한 호스트.
            processes=[{"pid": 4242, "command": "claude", "elapsed_sec": 3600}],
        )
    runtime = report.get("runtime_load") or {}
    channels = runtime.get("channels") or []
    problems = []
    if runtime.get("stale"):
        problems.append(f"재시작한 호스트를 낡음으로 셌다: {runtime.get('stale')!r}")
    if runtime.get("findings"):
        problems.append(f"발견이 남았다: {runtime['findings']!r}")
    if not channels or len(channels[0].get("current_hosts") or []) != 1:
        problems.append(f"최신 호스트를 못 셌다: {channels!r}")
    if not runtime.get("measurement_note"):
        problems.append("0개와 '해당 없음' 을 가르는 읽는 법이 없다")
    _record("test_runtime_load_clears_host_started_after_install", not problems, "; ".join(problems))


def test_runtime_load_parses_etime_not_lstart() -> None:
    """시작 시각은 `etime` 에서만 온다 — `lstart` 는 **로케일로 번역**된다.

    이 호스트의 `ps -o lstart` 는 `2026년 8월 16일 일요일 22시 53분 10초` 를 낸다.
    그걸 파싱하는 순간 탐침은 로케일에 묶인다. 그래서 형식이 고정된 `etime` 만
    읽고 지금에서 뺀다 — 그 파싱 계약을 여기서 고정한다.
    """
    cases = {"03-14:27:54": 3 * 86400 + 14 * 3600 + 27 * 60 + 54, "14:27:54": 52074, "27:54": 1674}
    problems = [
        f"{raw!r} → {_parse_etime(raw)!r} (기대 {want})"
        for raw, want in cases.items()
        if _parse_etime(raw) != want
    ]
    for bad in ("", "not-a-time", "1:2:3:4"):
        if _parse_etime(bad) is not None:
            problems.append(f"{bad!r} 를 파싱했다고 주장한다: {_parse_etime(bad)!r}")
    src = (SOURCE_ROOT / "workflow_kit" / "deploy_doctor.py").read_text(encoding="utf-8")
    if "lstart" in src.split("def _running_processes")[1].split("def ")[0]:
        problems.append("_running_processes 가 lstart 를 읽는다 — 로케일에 묶인다")
    _record("test_runtime_load_parses_etime_not_lstart", not problems, "; ".join(problems))



# --- Case 21~23 ------------------------------------------------------------


def _seed_cache_at(home: Path, harness: str, version: str) -> Path:
    """`_seed_cache` 와 같되 **버전 디렉터리를 지정**한다.

    갱신 뒤 상태를 세우려면 한 채널에 사본이 둘 있어야 한다 — 그 상황이
    이 절의 결함이 드러난 자리다.
    """
    entry = next(e for e in PLUGIN_INSTALL_CACHES if e.harness == harness)
    parts = [
        p.replace("*standard-ai-workflow*", "standard-ai-workflow").replace("*", "standard-ai-workflow")
        for p in entry.glob.split("/")
    ]
    root = home.joinpath(*parts[:-1], version)
    spec = PLUGIN_HARNESS_SPECS.get(harness)
    for rel, body in render_agent_plugin().items():
        if spec is not None and not _included(rel, spec):
            continue
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return root


def _seed_updated_claude_home(tmp: Path) -> tuple[Path, Path, Path]:
    """`plugin update` 직후의 실제 배치 — 옛 사본이 남고 선언은 새것을 가리킨다.

    2026-08-20 실측: `1.2.0` 과 `1.3.0` 이 나란히 있었고 `installed_plugins.json`
    의 `installPath` 만 `1.3.0` 을 가리켰다. 옛 사본은 아무도 읽지 않는다.
    """
    home = tmp / "home"
    old_root = _seed_cache_at(home, "claude-code", "0.0.1-old")
    new_root = _seed_cache_at(home, "claude-code", INSTALLED_VERSION)
    # 옛 사본만 낡게 만든다 — 새 사본은 정본 그대로다.
    victim = next(f for f in sorted(old_root.rglob("*.md")) if f.is_file())
    victim.write_text(victim.read_text(encoding="utf-8") + "\n<!-- 옛 사본 -->\n", encoding="utf-8")
    _write(
        home / ".claude" / "plugins" / "installed_plugins.json",
        json.dumps(
            {
                "version": 2,
                "plugins": {
                    "standard-ai-workflow@standard-ai-workflow": [
                        {
                            "scope": "user",
                            "installPath": str(new_root),
                            "version": INSTALLED_VERSION,
                            "installedAt": _INSTALL_ISO,
                            "lastUpdated": _INSTALL_ISO,
                        }
                    ]
                },
            }
        ),
    )
    return home, old_root, new_root


def test_content_drift_reads_which_copy_is_installed() -> None:
    """**갱신이 보고를 나쁘게 만들면 안 된다** (2026-08-20 실측, main-010).

    `plugin update` 로 1.2.0 → 1.3.0 을 올린 직후, 탐침은 발견이 늘었다.
    옛 디렉터리가 남는데 `installPath` 선언을 읽지 않아 **아무도 안 읽는 사본**을
    드리프트로 보고했고, 게다가 `installed_version` 이 **옛 버전**을 말했다.
    사본을 *하나* 찾은 것과 *로드되는 그것* 을 찾은 것은 다르다.
    """
    with tempfile.TemporaryDirectory(prefix="doctor-active-") as tmpdir:
        home, old_root, new_root = _seed_updated_claude_home(Path(tmpdir))
        content = probe(project_root=Path(tmpdir) / "project", home=home)["content_drift"]
    active = [c for c in content["caches"] if c.get("active")]
    problems = []
    if content["out_of_sync"]:
        problems.append(f"옛 사본을 발견으로 셌다: {content['out_of_sync']!r}")
    if [c["harness"] for c in content.get("superseded") or []] != ["claude-code"]:
        problems.append(f"옛 사본을 superseded 로 안 남겼다: {content.get('superseded')!r}")
    if len(active) != 1 or active[0].get("installed_version") != INSTALLED_VERSION:
        problems.append(f"설치본을 못 골랐다: {[c.get('installed_version') for c in active]!r}")
    if active and "installPath" not in str(active[0].get("active_source")):
        problems.append(f"무엇을 근거로 골랐는지 안 남겼다: {active[0].get('active_source')!r}")
    if str(old_root) not in json.dumps(content.get("superseded"), ensure_ascii=False):
        problems.append("옛 사본 경로를 숨겼다 — 사람이 정리할 수 없다")
    if str(new_root) == str(old_root):
        problems.append("fixture 가 사본 둘을 안 만들었다")
    _record("test_content_drift_reads_which_copy_is_installed", not problems, "; ".join(problems))


def test_runtime_load_does_not_duplicate_per_stale_copy() -> None:
    """설치 시각은 **플러그인 단위**다 — 사본마다 돌면 같은 발견이 복제된다.

    실측: 갱신 직후 claude-code 발견이 **글자까지 같은 두 줄**로 나왔다. 사유는
    채널당 하나이므로 잔재까지 세면 보고가 잡음이 된다.
    """
    with tempfile.TemporaryDirectory(prefix="doctor-dup-") as tmpdir:
        home, _old, _new = _seed_updated_claude_home(Path(tmpdir))
        report = probe(
            project_root=Path(tmpdir) / "project",
            home=home,
            now=_INSTALL_EPOCH + 600,
            processes=[{"pid": 77951, "command": "claude", "elapsed_sec": 600 + 1260}],
        )
    runtime = report["runtime_load"]
    claude_findings = [f for f in runtime["findings"] if "claude-code" in f]
    problems = []
    if len(claude_findings) != 1:
        problems.append(f"발견이 사본 수만큼 복제됐다: {len(claude_findings)}건")
    if runtime.get("superseded_skipped") != 1:
        problems.append(f"건너뛴 잔재를 안 셌다: {runtime.get('superseded_skipped')!r}")
    if len(runtime["channels"]) != 1:
        problems.append(f"채널 행이 사본 수만큼 늘었다: {len(runtime['channels'])}")
    _record("test_runtime_load_does_not_duplicate_per_stale_copy", not problems, "; ".join(problems))


def test_install_root_fallback_is_declared() -> None:
    """선언이 없는 채널은 **폴백이라고 말한다** — 조용히 하면 근거가 못 된다."""
    with tempfile.TemporaryDirectory(prefix="doctor-fallback-") as tmpdir:
        home = Path(tmpdir) / "home"
        _seed_cache(home, "codex")
        content = probe(project_root=Path(tmpdir) / "project", home=home)["content_drift"]
    caches = content["caches"]
    problems = []
    if len(caches) != 1 or not caches[0].get("active"):
        problems.append(f"선언 없는 채널의 사본을 설치본으로 안 봤다: {caches!r}")
    source = str(caches[0].get("active_source")) if caches else ""
    if "선언" not in source or "전부" not in source:
        problems.append(f"폴백임을 안 밝혔다: {source!r}")
    if "installPath" in source:
        problems.append("선언을 읽은 것처럼 말한다 — codex 는 선언하지 않는다")
    _record("test_install_root_fallback_is_declared", not problems, "; ".join(problems))


def _seed_grok_home(home: Path, *, installed: bool) -> Path | None:
    """grok 의 실제 설치 모양을 재현한다 (2026-08-29 이 호스트 실측).

    핵심은 **디렉터리 이름이 플러그인 이름이 아니라는 것** — `plugin-<hash>` 다.
    이름으로 glob 하면 원리적으로 못 찾는다. 매핑은 `registry.json` 이 쥔다.
    """
    (home / ".grok").mkdir(parents=True, exist_ok=True)
    (home / ".grok" / "config.toml").write_text(
        '[plugins]\nenabled = ["standard-ai-workflow"]\n', encoding="utf-8")
    reg_dir = home / ".grok" / "installed-plugins"
    reg_dir.mkdir(parents=True, exist_ok=True)
    if not installed:
        reg_dir.joinpath("registry.json").write_text(
            json.dumps({"version": 1, "repos": {}}), encoding="utf-8")
        return None
    root = reg_dir / "plugin-da9172c3"
    for rel, body in render_agent_plugin().items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    reg_dir.joinpath("registry.json").write_text(json.dumps({
        "version": 1,
        "repos": {"plugin-da9172c3": {
            "path": str(root),
            "plugins": {"standard-ai-workflow": {"version": INSTALLED_VERSION}},
        }},
    }), encoding="utf-8")
    return root


def test_content_drift_finds_grok_copy_by_declaration_not_name() -> None:
    """grok 설치본은 **이름으로 찾을 수 없다** (2026-08-29 실측, main-002).

    grok 은 설치 디렉터리를 `plugin-<hash>` 로 짓는다. 이름 glob 에 기대던
    이전 판은 실재하는 사본을 0개로 봤고, 그래서 `content_drift` 에서 grok 이
    **통째로 사라져** 있었다 — 낡음도 미측정도 아닌 침묵이었다. 디렉터리 이름
    규칙은 하네스의 것이지 우리 것이 아니므로, 정본은 `registry.json` 이다.
    """
    with tempfile.TemporaryDirectory(prefix="doctor-grok-") as tmpdir:
        home = Path(tmpdir) / "home"
        root = _seed_grok_home(home, installed=True)
        content = probe(project_root=Path(tmpdir) / "project", home=home)["content_drift"]
    grok = [c for c in content["caches"] if c["harness"] == "grok-build"]
    problems = []
    if not grok:
        problems.append("선언된 사본을 못 찾았다 — 이름 glob 에 기대고 있다")
    else:
        if not grok[0].get("in_sync"):
            problems.append(f"정본 그대로 깐 사본을 드리프트로 봤다: {grok[0].get('missing')!r}")
        if "registry.json" not in str(grok[0].get("active_source")):
            problems.append(f"무엇을 근거로 골랐는지 안 남겼다: {grok[0].get('active_source')!r}")
        if str(root) != str(grok[0].get("path")):
            problems.append(f"선언된 경로가 아니다: {grok[0].get('path')!r}")
    _record("test_content_drift_finds_grok_copy_by_declaration_not_name",
            not problems, "; ".join(problems))


def test_content_drift_reports_channel_with_zero_copies() -> None:
    """사본 0 도 **한 줄을 남긴다** (main-003).

    선언은 있는데 실체가 없는 상태를 이전에는 아무도 못 봤다: `global_scope` 는
    '선언 있음' 이라 말하고 `content_drift` 는 침묵했다. 침묵은 통과로 읽힌다.
    이 case 는 2026-08-29 아침의 실제 상태다 — grok 이 config 에 enable 만 남고
    `registry.json` 의 repos 가 비어 있었다.
    """
    with tempfile.TemporaryDirectory(prefix="doctor-nocopy-") as tmpdir:
        home = Path(tmpdir) / "home"
        _seed_grok_home(home, installed=False)
        report = probe(project_root=Path(tmpdir) / "project", home=home)
    content = report["content_drift"]
    gaps = {g["harness"]: g for g in content.get("no_copy") or []}
    problems = []
    grok = gaps.get("grok-build")
    if grok is None:
        problems.append(f"사본 0 인 채널이 출력에서 사라졌다: {sorted(gaps)!r}")
    else:
        if not grok.get("declared_globally"):
            problems.append("글로벌 선언이 있는데 그 사실을 안 실었다")
        if "registry.json" not in str(grok.get("why")):
            problems.append(f"사유가 없다 — 미설치인지 못 읽은 것인지 구별 안 된다: {grok.get('why')!r}")
    if not any("설치 사본이 0개" in f and "grok-build" in f for f in report["findings"]):
        problems.append("선언만 남고 실체가 없는 상태를 발견으로 안 셌다")
    _record("test_content_drift_reports_channel_with_zero_copies",
            not problems, "; ".join(problems))


def _seed_codex_marketplace(home: Path, source: str) -> None:
    """codex `config.toml` 에 플러그인 선언 + marketplace source 를 심는다."""
    cfg = home / ".codex"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "config.toml").write_text(
        'model = "gpt-5.6-terra"\n\n'
        '[plugins."standard-ai-workflow@standard-ai-workflow"]\n'
        "enabled = true\n\n"
        "[marketplaces.standard-ai-workflow]\n"
        'source_type = "local"\n'
        f'source = "{source}"\n',
        encoding="utf-8",
    )


def _codex_source_row(home: Path, project: Path) -> dict:
    content = probe(project_root=project, home=home)["content_drift"]
    rows = content.get("marketplace_sources") or []
    return rows[0] if rows else {}


def _usable_volatile_root() -> str:
    """`VOLATILE_PATH_PREFIXES` 중 **이 호스트에 실재하는** 접두사 하나.

    v1.8.1 (TASK-2026-09-01-main-004): 이 자리는 `/private/tmp` 리터럴이었다.
    macOS 에만 있는 경로라 Linux CI 에서 `mkdir(parents=True)` 가 루트에 `/private`
    를 만들려다 `PermissionError` 로 죽었고, **smoke 가 10 커밋 연속 red** 였다
    (2026-08-30 `6d9ad763` ~ 2026-09-01, v1.8.0 발행 커밋 포함).

    저장소가 이미 겪은 것의 **거울상**이다 — 예전에는 Linux 에서 쓴 검사가 macOS 의
    `/private` symlink 에서 깨졌고(TASK-2026-08-10-main-017), 이번에는 macOS 에서
    쓴 검사가 Linux 에서 깨졌다. 어느 쪽이든 **로컬 green / 반대편 red** 다.

    그래서 경로를 리터럴로 적지 않고 **판정 규칙의 목록에서 고른다**. 목록이 바뀌면
    이 검사가 따라간다. 쓸 수 있는 접두사가 하나도 없으면 조용히 넘기지 않고 죽는다 —
    못 잰 것을 통과로 세지 않는다.
    """
    for prefix in VOLATILE_PATH_PREFIXES:
        root = Path(prefix)
        if root.is_dir() and os.access(root, os.W_OK):
            return prefix
    raise AssertionError(
        f"이 호스트에서 쓸 수 있는 휘발 접두사가 없다: {VOLATILE_PATH_PREFIXES!r}"
    )


def test_codex_marketplace_source_on_volatile_path_is_a_finding() -> None:
    """휘발 경로의 marketplace source 는 **지금 존재해도** 발견이다 (main-004).

    2026-08-31 이 호스트 실측: source 가 사흘 전 끝난 Claude Code 세션의
    스크래치패드(`/private/tmp/claude-501/…`)를 가리키고 있었다. 설치 캐시는
    정본과 in-sync 였고 `content_drift` 는 통과라고 말했다 — OS 가 `/private/tmp`
    를 비우면 플러그인이 사라지는데 **탐침 어디에도 단서가 없었다.**

    존재 여부만 보면 비워지기 전에는 늘 통과다. 그래서 **경로 규칙**으로 판정한다.
    """
    with tempfile.TemporaryDirectory(prefix="doctor-codex-vol-") as tmpdir:
        home = Path(tmpdir) / "home"
        volatile = Path(_usable_volatile_root()) / f"doctor-probe-{os.getpid()}"
        volatile.mkdir(parents=True, exist_ok=True)
        try:
            _seed_codex_marketplace(home, str(volatile))
            row = _codex_source_row(home, Path(tmpdir) / "project")
            report = probe(project_root=Path(tmpdir) / "project", home=home)
        finally:
            volatile.rmdir()
    problems = []
    if not row:
        problems.append("marketplace source 를 아예 안 읽었다")
    else:
        if not row.get("exists"):
            problems.append("실재하는 경로를 부재로 봤다 — 휘발 판정과 존재 판정이 섞였다")
        if not row.get("volatile"):
            problems.append(f"휘발 경로를 항구로 봤다: {row.get('source')!r}")
    findings = report["content_drift"]["findings"]
    if not any("휘발" in f for f in findings):
        problems.append(f"휘발을 발견으로 세지 않았다: {findings!r}")
    _record("test_codex_marketplace_source_on_volatile_path_is_a_finding",
            not problems, "; ".join(problems))


def test_codex_marketplace_source_missing_is_a_finding() -> None:
    """source 가 사라졌으면 설치 캐시가 멀쩡해도 발견이다."""
    with tempfile.TemporaryDirectory(prefix="doctor-codex-gone-") as tmpdir:
        home = Path(tmpdir) / "home"
        _seed_codex_marketplace(home, str(Path(tmpdir) / "없는-경로"))
        report = probe(project_root=Path(tmpdir) / "project", home=home)
    row = (report["content_drift"].get("marketplace_sources") or [{}])[0]
    findings = report["content_drift"]["findings"]
    problems = []
    if row.get("exists"):
        problems.append("없는 경로를 있다고 봤다")
    if not any("source 가 존재하지" in f for f in findings):
        problems.append(f"부재를 발견으로 세지 않았다: {findings!r}")
    _record("test_codex_marketplace_source_missing_is_a_finding",
            not problems, "; ".join(problems))


def test_codex_marketplace_source_durable_is_silent() -> None:
    """항구 경로면 발견이 없다 — 정상을 시끄럽게 하지 않는다."""
    with tempfile.TemporaryDirectory(prefix="doctor-codex-ok-") as tmpdir:
        home = Path(tmpdir) / "home"
        durable = home / ".codex" / "local-marketplaces" / "standard-ai-workflow-codex-plugin-1.7.0"
        durable.mkdir(parents=True, exist_ok=True)
        _seed_codex_marketplace(home, str(durable))
        report = probe(project_root=Path(tmpdir) / "project", home=home)
    row = (report["content_drift"].get("marketplace_sources") or [{}])[0]
    findings = report["content_drift"]["findings"]
    problems = []
    if not row.get("exists") or row.get("volatile"):
        problems.append(f"항구 경로를 문제로 봤다: {row!r}")
    noisy = [f for f in findings if "marketplace" in f]
    if noisy:
        problems.append(f"정상인데 발견을 냈다: {noisy!r}")
    _record("test_codex_marketplace_source_durable_is_silent",
            not problems, "; ".join(problems))


def _seed_kit_tree(package_root: Path, version: str | None, extra: str = "") -> None:
    """`workflow_kit` 트리 한 벌 — 사본 옆 `pyproject.toml` 은 version 이 None 이면 안 쓴다."""
    package_root.mkdir(parents=True, exist_ok=True)
    (package_root / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (package_root / "deploy_doctor.py").write_text(
        f"def probe():\n    return 'body'\n{extra}", encoding="utf-8"
    )
    (package_root / "assets").mkdir(exist_ok=True)
    # 자산은 대조 단위가 아니다 — 채널마다 담기는 것이 달라 포장 차이가 샌다.
    (package_root / "assets" / "note.md").write_text("asset\n", encoding="utf-8")
    if version is not None:
        (package_root.parent / "pyproject.toml").write_text(
            f'[project]\nname = "standard_ai_workflow"\nversion = "{version}"\n',
            encoding="utf-8",
        )


def test_kit_provenance_flags_same_version_content_drift() -> None:
    """돌고 있는 사본이 저장소 소스와 **버전은 같고 내용이 다르면** 발견이다 (main-002).

    doctor 는 배포 페이로드에 대해선 '버전 동일 · 내용만 낡음' 을 이미 해시로
    잡으면서 자기 자신에겐 그 규율을 안 썼다. 2026-08-31 실측: 전역 wk(릴리스
    v1.7.0 휠)가 저장소 소스(같은 1.7.0 자칭)와 갈라진 채 돌며 지원 종료된
    gemini-cli 를 '막힘' 으로 · 신설 antigravity 를 부재로 보고했고, 출력엔
    `kit version : 1.7.0` 한 줄뿐이었다. 버전 문자열은 최신의 증거가 아니다.
    """
    from workflow_kit.deploy_doctor import _probe_kit_provenance

    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="doctor-prov-drift-") as tmp:
        project = Path(tmp) / "project"
        _seed_kit_tree(project / "workflow-source" / "workflow_kit", "1.7.0")
        copy = Path(tmp) / "wheel"
        _seed_kit_tree(copy / "workflow_kit", "1.7.0", extra="# drifted\n")

        record = _probe_kit_provenance(project, copy / "workflow_kit" / "__init__.py")
        if record["verdict"] != "content_drift_same_version":
            problems.append(f"판정: {record['verdict']}")
        if record["differing_count"] != 1 or record["differing_files"] != ["deploy_doctor.py"]:
            problems.append(f"어긋난 파일: {record['differing_files']}")
        if not record["findings"]:
            problems.append("내용이 갈라졌는데 finding 이 없다")
        else:
            finding = record["findings"][0]
            for needle in ("1.7.0", str(copy / "workflow_kit"), "deploy_doctor.py"):
                if needle not in finding:
                    problems.append(f"finding 에 근거 누락: {needle}")
    _record("test_kit_provenance_flags_same_version_content_drift", not problems, "; ".join(problems))


def test_kit_provenance_matching_copy_is_silent() -> None:
    """내용이 같은 사본은 발견이 아니다 — 늘 red 인 판정은 게이트가 못 된다.

    자산 파일만 다른 경우도 통과해야 한다. wheel 은 `package-data` 로 고른 것만
    담고 소스 트리에는 런타임 산출물이 남아, 자산을 대조 단위에 넣으면 포장
    차이가 영구 오탐이 된다.
    """
    from workflow_kit.deploy_doctor import _probe_kit_provenance

    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="doctor-prov-sync-") as tmp:
        project = Path(tmp) / "project"
        _seed_kit_tree(project / "workflow-source" / "workflow_kit", "1.7.0")
        copy = Path(tmp) / "wheel"
        _seed_kit_tree(copy / "workflow_kit", "1.7.0")
        # 소스 트리에만 있는 런타임 산출물 — 포장 차이지 내용 차이가 아니다.
        (project / "workflow-source" / "workflow_kit" / "assets" / "only-source.md").write_text(
            "x\n", encoding="utf-8"
        )

        record = _probe_kit_provenance(project, copy / "workflow_kit" / "__init__.py")
        if record["verdict"] != "in_sync":
            problems.append(f"판정: {record['verdict']} (자산 차이가 발견으로 샜다)")
        if record["findings"]:
            problems.append(f"일치인데 finding: {record['findings']}")
    _record("test_kit_provenance_matching_copy_is_silent", not problems, "; ".join(problems))


def test_kit_provenance_reads_version_from_the_copy() -> None:
    """사본의 버전은 **사본에서** 읽는다 — 인터프리터의 메타데이터가 아니다.

    `current_kit_version()` 의 폴백은 사본이 아니라 설치된 배포본을 읽으므로,
    사본 옆에 버전 선언이 없으면 무관한 dist 의 값이 사본 버전으로 둔갑한다.
    2026-08-31 실측: `/tmp` 사본(1.7.0 파생)이 이 호스트의 낡은 editable
    메타데이터를 물어 **1.2.0** 으로 보고됐고, 그 값이 맞았다면 판정이
    `version_mismatch` 로 갈려 '버전 같고 내용만 다름' 을 영영 못 잡는다.
    모름은 같음으로 세지 않는다.
    """
    from workflow_kit.deploy_doctor import _probe_kit_provenance

    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="doctor-prov-unit-") as tmp:
        project = Path(tmp) / "project"
        _seed_kit_tree(project / "workflow-source" / "workflow_kit", "9.9.9")
        copy = Path(tmp) / "loose"
        _seed_kit_tree(copy / "workflow_kit", None, extra="# drifted\n")

        record = _probe_kit_provenance(project, copy / "workflow_kit" / "__init__.py")
        if record["running_version"] is not None:
            problems.append(
                f"선언 없는 사본에 버전이 붙었다: {record['running_version']} "
                f"({record['running_version_source']}) — 인터프리터를 읽었다"
            )
        if record["running_version"] == INSTALLED_VERSION:
            problems.append("사본 버전이 인터프리터 설치본의 값과 같다 — 잰 단위가 어긋났다")
        if record["verdict"] != "content_drift_unknown_version":
            problems.append(f"판정: {record['verdict']}")
        if not any("확인할 수 없다" in f for f in record["findings"]):
            problems.append(f"모름이 발견으로 안 나왔다: {record['findings']}")
        if record["repo_version"] != "9.9.9":
            problems.append(f"저장소 버전: {record['repo_version']}")
    _record("test_kit_provenance_reads_version_from_the_copy", not problems, "; ".join(problems))


def test_kit_provenance_always_labels_verdict() -> None:
    """판정은 어떤 상황에서도 **남는다** — 조용한 통과 금지 (컨셉 §5).

    kit 소스가 없는 소비자 프로젝트는 대조 대상이 없다. 그건 정상이지만 침묵이
    아니라 '측정 안 됨' 라벨이어야 한다. 실 `probe()` 의 environment 절에도
    키가 실려 소비 지점까지 도달하는지 같이 본다.
    """
    from workflow_kit.deploy_doctor import _probe_kit_provenance, _render_provenance

    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="doctor-prov-label-") as tmp:
        consumer = Path(tmp) / "consumer"
        consumer.mkdir()
        copy = Path(tmp) / "wheel"
        _seed_kit_tree(copy / "workflow_kit", "1.7.0")

        record = _probe_kit_provenance(consumer, copy / "workflow_kit" / "__init__.py")
        if record["verdict"] != "no_repo_source":
            problems.append(f"kit 소스 없는 프로젝트 판정: {record['verdict']}")
        if record["findings"]:
            problems.append("소비자 프로젝트의 정상 상태가 발견이 됐다")
        if not _render_provenance(record):
            problems.append("판정이 출력에 안 나온다 — 침묵")

        report = probe(project_root=consumer, home=Path(tmp) / "home")
        env = report["environment"]
        if "kit_provenance" not in env:
            problems.append("environment 에 kit_provenance 키가 없다")
        elif not env["kit_provenance"].get("verdict"):
            problems.append("실 probe 의 판정이 비었다")
        if not any(line.startswith("  kit 사본") for line in _render_text(report).splitlines()):
            problems.append("텍스트 보고서에 kit 사본 줄이 없다")
    _record("test_kit_provenance_always_labels_verdict", not problems, "; ".join(problems))

def main() -> int:
    # 총계는 **세어서** 낸다 — `total = 23` 리터럴이었을 때는 case 를 늘려도
    # 숫자가 안 따라왔고, 그 숫자가 곧 "몇 개를 쟀나" 의 유일한 증거다.
    cases = [
        test_report_shape,
        test_pip_absence_reads_uv_tool_receipt,
        test_probe_writes_nothing,
        test_home_injection_is_honored,
        test_presence_without_marker_is_not_applied,
        test_stale_marker_is_reported,
        test_forked_entry_is_not_advised_to_reapply,
        test_both_scopes_detected_and_not_removed,
        test_strict_flag_governs_return_code,
        test_registries_are_derived_not_copied,
        test_dispatcher_registers_doctor,
        test_content_drift_clean_install_is_in_sync,
        test_content_drift_catches_same_version_stale_payload,
        test_content_drift_expects_only_channel_files,
        test_content_drift_writes_nothing,
        test_content_drift_declares_surface_as_unmeasured,
        test_preflight_separates_measured_from_declared,
        test_preflight_blocks_channel_with_missing_executable,
        test_kit_resolution_flags_foreign_checkout,
        test_preflight_bootstrap_channel_resolves_platform_launcher,
        test_preflight_writes_nothing,
        test_runtime_load_flags_host_older_than_install,
        test_runtime_load_clears_host_started_after_install,
        test_runtime_load_parses_etime_not_lstart,
        test_content_drift_reads_which_copy_is_installed,
        test_runtime_load_does_not_duplicate_per_stale_copy,
        test_install_root_fallback_is_declared,
        test_content_drift_finds_grok_copy_by_declaration_not_name,
        test_content_drift_reports_channel_with_zero_copies,
        test_codex_marketplace_source_on_volatile_path_is_a_finding,
        test_codex_marketplace_source_missing_is_a_finding,
        test_codex_marketplace_source_durable_is_silent,
        test_kit_provenance_flags_same_version_content_drift,
        test_kit_provenance_matching_copy_is_silent,
        test_kit_provenance_reads_version_from_the_copy,
        test_kit_provenance_always_labels_verdict,
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
