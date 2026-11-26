#!/usr/bin/env python3
"""허브 부트스트랩 · 지침 렌더링 · 세션 시작 확인 (M-034) 을 잰다.

계약 정본: ``core/hub_spec.md`` §5 · §6.1 · §6.2 · §6.5, 표준 규칙 정본 ``core/hub_workflow_standard.md``.
실제 허브 프로세스 · 실제 git 저장소로 잰다. 에이전트 몫(쓰기 지시 적용 · 명령 실행)은 이 검사가
그대로 한다 — 단 하네스 등록 명령(``codex`` · ``agy``)은 실행하지 않고 rc 0 으로 보고한다
(하네스 쪽은 requirements §16.3 실측이 맡는다).

1. 표준 규칙 단일 출처 — 스냅샷 == core 표식 블록 · 4종 렌더가 예산 안 · 파일 이름은 하네스 표 (R7.2 · R7.3 · DS6)
2. 렌더 영역 병합 — 영역 밖 보존 · 자리 교체 · 로컬 수정 멈춤 · 끝 표식 없음 멈춤 (R7.5)
3. 셋업 — .gitignore 확인 전에는 토큰 지시 없음 · 확인 뒤 env · 진입 파일 · 하네스 설정 · 완료 (R4.2 · R2.4 · R2.5 · R2.5a)
4. .gitignore 가 듣지 않으면(부정 규칙 · 이미 추적) 멈춘다 — 토큰 지시 없음 (R4.2)
5. 해시가 다르면 미확인 · 완료 아님 (R2.4)
6. 로컬에서 고친 렌더 영역은 지시하지 않고 멈춤 (R7.5)
7. 세션 시작 — 결과 없음은 미확인 · 맞음 start · 뒤처짐 fast-forward · 미커밋/갈라짐 멈춤 · 지침 바뀜 · 없는 커밋 (R10)
9. 막힌 진입 파일 — 셋업 미완료 · MCP 단계 유지 · guide_render 같은 판정
8. 안내 페이지 — 4종 명령 · 토큰 없음 · CSP (R2.6)
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 300

# `python -m workflow_kit hub` 로 실제 프로세스를 띄우므로 dispatcher 를 거쳐 kit 전체를 읽는다.
WATCHES = (
    "workflow-source/workflow_kit/*",
    "hub-go/*",
    "workflow-source/core/hub_workflow_standard.md",
    "workflow-source/tests/check_hub_core.py",  # 허브 프로세스 도우미(Hub)를 빌려 쓴다
    "workflow-source/pyproject.toml",
)

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_hub_core import Hub, _env, _resolve_go_hub  # noqa: E402
from workflow_kit.bootstrap_lib.harnesses import spec_for  # noqa: E402
from workflow_kit.bootstrap_lib.harnesses.entry_sections import ENTRY_BUDGET_BYTES  # noqa: E402
from workflow_kit import __version__ as HUB_VERSION  # noqa: E402
from workflow_kit.hub import render  # noqa: E402

_failures: list[str] = []
_passes: list[str] = []
HARNESSES = list(render.SUPPORTED_HARNESSES)


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail and not ok else ''}")


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e")
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, encoding="utf-8", errors="replace",
                          env=env, check=check, timeout=60)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_clone(tmp: Path, name: str) -> tuple[Path, Path]:
    """bare origin + clone (한 커밋 push 됨)."""
    origin = tmp / f"{name}-origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True, timeout=60)
    repo = tmp / name
    subprocess.run(["git", "clone", "-q", str(origin), str(repo)], check=True, timeout=60, capture_output=True)
    _git(repo, "checkout", "-q", "-b", "main")
    (repo / "README.md").write_text("# demo\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "init")
    _git(repo, "push", "-q", "-u", "origin", "main")
    return origin, repo


def _scan(repo: Path) -> dict[str, Any]:
    files: dict[str, Any] = {}
    for rel in [".gitignore", ".mcp.json", *[render.entry_file(h) for h in HARNESSES]]:
        p = repo / rel
        files[rel] = p.read_text(encoding="utf-8") if p.exists() else None
    return {"files": files}


def _apply(repo: Path, steps: list[dict[str, Any]]) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """에이전트 몫 — 지시를 적용하고 확인 보고를 만든다."""
    files: list[dict[str, str]] = []
    checks: list[dict[str, Any]] = []
    for st in steps:
        op = st["op"]
        if op == "append_line":
            p = repo / st["path"]
            text = p.read_text(encoding="utf-8") if p.exists() else ""
            if st["content"].strip() not in [ln.strip() for ln in text.splitlines()]:
                if text and not text.endswith("\n"):
                    text += "\n"
                p.write_text(text + st["content"], encoding="utf-8")
        elif op == "write":
            p = repo / st["path"]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(st["content"], encoding="utf-8")
            if st.get("mode") == "600":
                os.chmod(p, 0o600)
            files.append({"path": st["path"], "sha256": _sha(p)})
        elif op == "run_and_report" and st["id"] == "check_ignore":
            r = subprocess.run(st["run"], cwd=repo, capture_output=True, encoding="utf-8", timeout=60)
            checks.append({"name": "check_ignore", "rc": r.returncode, "output": r.stdout})
        elif op in ("run_and_report", "user_scope_write"):
            checks.append({"name": st["id"], "rc": 0, "output": "(검사: 하네스 명령은 실행하지 않음)"})
    return files, checks


def case_1_single_source() -> None:
    from workflow_kit.hub._standard_snapshot import STANDARD_BLOCK

    same = STANDARD_BLOCK == render.standard_block_from_core()
    sizes, names = {}, {}
    for h in HARNESSES:
        region, _ = render.render_region(h, "P-x", "Demo", "- 테스트: make test", 1)
        sizes[h] = len(region.encode("utf-8"))
        names[h] = render.entry_file(h) == spec_for(h).entry_files[0]
    no_v1 = all("python -m workflow_kit" not in render.render_region(h, "P-x", "D", "", 0)[0] for h in HARNESSES)
    has_rules = all(k in STANDARD_BLOCK for k in ("hub_session_start", "compact 직후", "세션 끝"))
    _record("case 1 (표준 규칙 단일 출처 · 4종 예산 · 하네스 표)",
            same and all(s <= ENTRY_BUDGET_BYTES for s in sizes.values()) and all(names.values()) and no_v1 and has_rules,
            f"snapshot==core={same} sizes={sizes} names={names} no_v1={no_v1} rules={has_rules}")


def case_2_merge() -> None:
    region, _ = render.render_region("claude-code", "P-x", "Demo", "", 0)
    base = "# 손으로 쓴 머리\n\n본문\n"
    merged, why = render.merge_into(base, region)
    ok_append = why is None and merged is not None and merged.startswith(base) and merged.endswith(region)
    region2, _ = render.render_region("claude-code", "P-x", "Demo", "- 새 지침", 1)
    replaced, why2 = render.merge_into((merged or "") + "\n꼬리 문단\n", region2)
    ok_replace = (why2 is None and replaced is not None and replaced.startswith(base) and region2 in replaced
                  and region not in replaced and replaced.endswith("꼬리 문단\n"))
    tampered = (merged or "").replace("## 워크플로우 허브 규칙", "## 내가 고친 규칙")
    _, why3 = render.merge_into(tampered, region2)
    broken = (merged or "").replace(render.END_MARK, "")
    _, why4 = render.merge_into(broken, region2)
    _record("case 2 (렌더 영역 병합 · 로컬 수정 멈춤)",
            ok_append and ok_replace and why3 == "local_edit_detected" and why4 == "local_edit_detected",
            f"append={ok_append} replace={ok_replace} tampered={why3} broken={why4}")


def _register(hub: Hub, remote: str, callsign: str) -> tuple[str, str]:
    st, reg, _ = hub.call("hub_project_register", {"remote_url": remote, "display_name": "Demo", "callsign": callsign,
                                                     "kind": "agent"})
    if st != 200:
        raise AssertionError(f"등록 실패 {st} {reg}")
    return reg["project_id"], reg["token"]


def case_3_to_6(hub: Hub, tmp: Path) -> tuple[str, str, Path]:
    _, repo = _make_clone(tmp, "setup")
    pid, tok = _register(hub, "git@github.com:acme/demo.git", "claude-a")
    # 3 — 정상 셋업
    relay_scan = {"required": True, "config_present": True,
                  "status": {"registered": True, "paused": False, "allow": ["repo"]}}
    st1, plan1, _ = hub.call("hub_setup_plan", {"project_id": pid, "token": tok, "harnesses": HARNESSES,
                                                  "scan": {**_scan(repo), "relay": relay_scan}})
    relay_check = plan1.get("relay") == {**relay_scan, "next": "Python 우선: python -m workflow_kit hub relay status → 필요하면 init → allow add → serve"}
    stage1_has_token = tok in json.dumps(plan1, ensure_ascii=False)
    files1, checks1 = _apply(repo, plan1.get("steps", []))
    st2, conf1, _ = hub.call("hub_setup_confirm", {"project_id": pid, "token": tok, "files": files1, "checks": checks1})
    st3, plan2, _ = hub.call("hub_setup_plan", {"project_id": pid, "token": tok, "harnesses": HARNESSES, "scan": _scan(repo)})
    ids2 = [s["id"] for s in plan2.get("steps", [])]
    env_step = next((s for s in plan2.get("steps", []) if s["id"] == "env"), {})
    agy = next((s for s in plan2.get("steps", []) if s["id"] == "harness:antigravity"), {})
    files2, checks2 = _apply(repo, plan2.get("steps", []))
    st4, conf2, _ = hub.call("hub_setup_confirm", {"project_id": pid, "token": tok, "files": files2, "checks": checks2})
    mcp_json = json.loads((repo / ".mcp.json").read_text(encoding="utf-8"))
    header = mcp_json["mcpServers"]["workflow-hub"]["headers"]["Authorization"]
    # Claude Code 는 headersHelper 로 .workflow-hub/env 의 콜사인 토큰을 읽는다 — 환경 변수 없이 붙는 길 (2026-11-25)
    helper = mcp_json["mcpServers"]["workflow-hub"].get("headersHelper")
    committed_files = [render.entry_file(h) for h in HARNESSES] + [".mcp.json", ".gitignore"]
    token_in_repo_files = [f for f in committed_files if tok in (repo / f).read_text(encoding="utf-8")]
    ignored = subprocess.run(["git", "status", "--porcelain", "--ignored", ".workflow-hub"], cwd=repo,
                             capture_output=True, encoding="utf-8").stdout
    ok3 = (st1 == 200 and relay_check and plan1.get("stage") == "gitignore" and not stage1_has_token
           and st2 == 200 and conf1.get("confirmed") == ["gitignore"] and not conf1.get("setup_complete")
           and plan2.get("stage") == "files" and "env" in ids2
           and all(f"entry:{h}" in ids2 for h in HARNESSES) and "harness:mcp-json" in ids2 and "harness:codex" in ids2
           and tok in env_step.get("content", "") and agy.get("warning") and tok in " ".join(agy.get("run", []))
           and st4 == 200 and conf2.get("setup_complete") is True and not conf2.get("unconfirmed")
           and header == "Bearer ${WORKFLOW_HUB_TOKEN}" and helper == "python3 .workflow-hub/hub_client.py mcp-headers"
           and not token_in_repo_files
           and "!! .workflow-hub/" in ignored and oct((repo / ".workflow-hub/env").stat().st_mode & 0o777) == "0o600")
    _record("case 3 (셋업 — .gitignore 먼저 · env · 진입 파일 · 하네스 설정 · 완료)", ok3,
            f"stage1={plan1.get('stage')} token1={stage1_has_token} conf1={conf1} stage2={plan2.get('stage')} ids={ids2} "
            f"conf2={conf2} header={header} helper={helper} token_in={token_in_repo_files} ignored={ignored!r}")

    # 4 — .gitignore 가 듣지 않는다: 부정 규칙 · 이미 추적
    # git 의미: 부모 디렉터리가 무시되면 그 안의 파일은 `!` 로 다시 포함되지 않는다 (gitignore 문서).
    # 그래서 '듣지 않는' 경우는 디렉터리 자체를 부정하거나(negate_dir → rc 1), 디렉터리 규칙을 풀고
    # 파일 단위로 부정하거나(negate_file → rc 0 + `!` 패턴), 이미 추적 중(tracked → rc 1)이다.
    negations = {
        "negate_dir": "!/.workflow-hub/\n",
        "negate_file": "!/.workflow-hub/\n/.workflow-hub/*\n!/.workflow-hub/env\n",
    }
    results = {}
    for mode in ("negate_dir", "negate_file", "tracked"):
        _, r = _make_clone(tmp, f"bad-{mode}")
        p2, t2 = _register(hub, f"git@github.com:acme/bad-{mode}.git", "claude-b")
        if mode == "tracked":
            (r / ".workflow-hub").mkdir()
            (r / ".workflow-hub/env").write_text("X=1\n", encoding="utf-8")
            _git(r, "add", ".workflow-hub/env")
            _git(r, "commit", "-q", "-m", "tracked")
        pl = hub.call("hub_setup_plan", {"project_id": p2, "token": t2, "harnesses": ["codex"], "scan": _scan(r)})[1]
        _apply(r, pl.get("steps", []))
        if mode in negations:
            with (r / ".gitignore").open("a", encoding="utf-8") as fh:
                fh.write(negations[mode])
        _, checks = _apply(r, [s for s in pl.get("steps", []) if s["id"] == "check_ignore"])
        _, conf, _ = hub.call("hub_setup_confirm", {"project_id": p2, "token": t2, "files": [], "checks": checks})
        _, again, _ = hub.call("hub_setup_plan", {"project_id": p2, "token": t2, "harnesses": ["codex"], "scan": _scan(r)})
        results[mode] = (conf.get("error_code"), again.get("stage"), t2 in json.dumps(again, ensure_ascii=False))
    ok4 = all(v == ("ignore_not_effective", "gitignore", False) for v in results.values())
    _record("case 4 (.gitignore 가 안 들으면 토큰 지시 없음 — 디렉터리 부정 · 파일 부정 · 추적 중)", ok4, f"{results}")

    # 5 — 해시가 다르면 미확인
    _, repo5 = _make_clone(tmp, "sha")
    p5, t5 = _register(hub, "git@github.com:acme/sha.git", "claude-c")
    pl5 = hub.call("hub_setup_plan", {"project_id": p5, "token": t5, "harnesses": ["codex"], "scan": _scan(repo5)})[1]
    f5, c5 = _apply(repo5, pl5["steps"])
    hub.call("hub_setup_confirm", {"project_id": p5, "token": t5, "files": f5, "checks": c5})
    pl5b = hub.call("hub_setup_plan", {"project_id": p5, "token": t5, "harnesses": ["codex"], "scan": _scan(repo5)})[1]
    f5b, c5b = _apply(repo5, pl5b["steps"])
    (repo5 / "AGENTS.md").write_text((repo5 / "AGENTS.md").read_text(encoding="utf-8") + "\n덧붙임\n", encoding="utf-8")
    f5b = [{"path": f["path"], "sha256": _sha(repo5 / f["path"])} for f in f5b]
    _, conf5, _ = hub.call("hub_setup_confirm", {"project_id": p5, "token": t5, "files": f5b, "checks": c5b})
    bad = [u["id"] for u in conf5.get("unconfirmed", [])]
    _record("case 5 (해시 불일치 → 미확인 · 완료 아님)", bad == ["entry:codex"] and conf5.get("setup_complete") is False,
            f"unconfirmed={conf5.get('unconfirmed')} complete={conf5.get('setup_complete')}")

    # 6 — 로컬에서 고친 렌더 영역
    claude = repo / "CLAUDE.md"
    claude.write_text(claude.read_text(encoding="utf-8").replace("### 작업 중", "### 작업 중 (내가 고침)"), encoding="utf-8")
    _, plan6, _ = hub.call("hub_setup_plan", {"project_id": pid, "token": tok, "harnesses": HARNESSES, "scan": _scan(repo)})
    blocked = [b["id"] for b in plan6.get("blocked", [])]
    written = [s["id"] for s in plan6.get("steps", [])]
    _record("case 6 (로컬 수정 영역은 지시 없이 멈춤)",
            blocked == ["entry:claude-code"] and "entry:claude-code" not in written and "entry:codex" in written,
            f"blocked={blocked} steps={written}")
    claude.write_text(claude.read_text(encoding="utf-8").replace("### 작업 중 (내가 고침)", "### 작업 중"), encoding="utf-8")
    return pid, tok, repo


def _run_cmds(repo: Path, commands: dict[str, list[str]]) -> dict[str, Any]:
    out = {}
    for name, argv in commands.items():
        r = subprocess.run(argv, cwd=repo, capture_output=True, encoding="utf-8", errors="replace", timeout=60)
        out[name] = {"rc": r.returncode, "output": r.stdout}
    return out


def case_7_session(hub: Hub, tmp: Path, db: Path, pid: str, tok: str, repo: Path) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "hub setup")
    _git(repo, "push", "-q")
    _, t1, _ = hub.call("hub_task_create", {"title": "세션 task"}, tok)
    tid = t1["task"]["id"]
    hub.call("hub_task_claim", {"id": tid}, tok)
    hub.call("hub_task_link_commit", {"id": tid, "sha": "deadbeef" * 5}, tok)

    def start(results: dict[str, Any] | list[Any] | None) -> dict[str, Any]:
        args = {} if results is None else {"repo_results": results}
        return hub.call("hub_session_start", args, tok)[1]

    p1 = start(None)
    cmds = p1.get("repo_check", {}).get("commands", {})
    ok_p1 = (p1.get("verdict") == "unconfirmed" and "status" in cmds and any(k.startswith("entry_head:") for k in cmds)
             and any(k.startswith("commit:") for k in cmds) and [t["id"] for t in p1["hub"]["my_tasks"]] == [tid]
             and p1["hub"].get("handoff") is None and "hub: 내 handoff" in p1.get("confirmed", []))
    clean = start(_run_cmds(repo, cmds))
    # 목록 꼴 — 이름의 : · . 를 키로 못 싣는 하네스 (M-039 실측: Antigravity). 같은 판정이어야 한다.
    as_list = start([{"name": k, **v} for k, v in _run_cmds(repo, cmds).items()])
    same_list = all(as_list.get(k) == clean.get(k) for k in ("verdict", "confirmed", "unconfirmed", "findings"))
    st_dup, dup_list, _ = hub.call("hub_session_start", {"repo_results": [{"name": "status", "rc": 0, "output": ""}] * 2}, tok)
    # 뒤처짐 — 다른 클론이 push
    other = tmp / "other"
    subprocess.run(["git", "clone", "-q", str(tmp / "setup-origin.git"), str(other)], check=True, capture_output=True, timeout=60)
    (other / "x.txt").write_text("x\n", encoding="utf-8")
    _git(other, "add", "x.txt")
    _git(other, "commit", "-q", "-m", "other")
    _git(other, "push", "-q")
    behind = start(_run_cmds(repo, cmds))
    # 미커밋
    (repo / "dirty.txt").write_text("d\n", encoding="utf-8")
    dirty = start(_run_cmds(repo, cmds))
    (repo / "dirty.txt").unlink()
    # 갈라짐
    (repo / "mine.txt").write_text("m\n", encoding="utf-8")
    _git(repo, "add", "mine.txt")
    _git(repo, "commit", "-q", "-m", "mine")
    diverged = start(_run_cmds(repo, cmds))
    # 지침 바뀜
    gfile = tmp / "guide.md"
    gfile.write_text("- 이 프로젝트는 make check 로 검사한다\n", encoding="utf-8")
    g = subprocess.run([sys.executable, "-m", "workflow_kit", "hub", "admin", "--db", str(db), "guide", "set",
                        "--project", pid, "--file", str(gfile)], capture_output=True, encoding="utf-8", env=_env(), timeout=60)
    changed = start(_run_cmds(repo, cmds))
    rerender = hub.call("hub_guide_render", {"harness": "codex",
                                             "current": (repo / "AGENTS.md").read_text(encoding="utf-8")}, tok)[1]
    st_bad, bad_key, _ = hub.call("hub_session_start", {"repo_results": {"bogus": {"rc": 0, "output": ""}}}, tok)
    ok = (ok_p1 and clean.get("verdict") == "start"
          and behind.get("verdict") == "fast_forward_then_start"
          and dirty.get("verdict") == "stop_and_ask" and diverged.get("verdict") == "stop_and_ask"
          and any("없다" in f and tid in f for f in clean.get("findings", []))
          and g.returncode == 0 and changed["hub"]["guide"]["changed"] is True
          and any(f.startswith("[바뀜]") for f in changed.get("findings", []))
          and "make check" in rerender.get("step", {}).get("content", "")
          and st_bad == 400 and bad_key.get("error_code") == "invalid_field"
          and same_list and st_dup == 400 and dup_list.get("detail", {}).get("field") == "repo_results[1].name")
    _record("case 7 (세션 시작 — 미확인 · start · fast-forward · 멈춤 · 지침 바뀜 · 없는 커밋 · 목록 꼴 같은 판정)", ok,
            f"p1={ok_p1} clean={clean.get('verdict')}/{clean.get('findings')} behind={behind.get('verdict')} "
            f"dirty={dirty.get('verdict')} diverged={diverged.get('verdict')} guide_set_rc={g.returncode} "
            f"changed={changed['hub']['guide']} findings={changed.get('findings')} bad={st_bad} "
            f"list_same={same_list} list={as_list.get('verdict')} dup={st_dup}")


def case_8_page(hub: Hub, tok: str) -> None:
    r = urllib.request.urlopen(hub.base + "/", timeout=10)
    body = r.read().decode("utf-8")
    setup = urllib.request.urlopen(hub.base + "/setup.md", timeout=10).read().decode("utf-8")
    ok = (all(h in body for h in HARNESSES) and f"Hub {HUB_VERSION}" in body and "kit 호환 2.1.0" in body
          and "wfh_" not in body and tok not in body and "Hub " + HUB_VERSION in setup
          and "PC 로컬 중계" in setup and "--relay" in setup and "python -m workflow_kit hub relay status" in setup
          and "default-src 'none'" in (r.headers.get("Content-Security-Policy") or "") and "/mcp" in body)
    _record("case 8 (안내 페이지 — 버전 · 4종 · relay 가이드 · 토큰 없음 · CSP)", ok, f"len={len(body)} setup_len={len(setup)} csp={r.headers.get('Content-Security-Policy')}")


def case_9_blocked_entry(hub: Hub, tmp: Path) -> None:
    """1.x 진입 파일이 막히면 셋업은 끝난 것이 아니고, MCP 단계는 나오고, guide_render 도 같은 판정을 한다."""
    _, repo = _make_clone(tmp, "blocked")
    (repo / "CLAUDE.md").write_text("<!-- standard-ai-workflow-kit: v1.29.0 -->\n# 1.x\n", encoding="utf-8")
    pid, tok = _register(hub, "git@github.com:acme/blocked.git", "claude-k")
    args = {"project_id": pid, "token": tok, "harnesses": ["claude-code"]}

    def step() -> tuple[dict[str, Any], dict[str, Any]]:
        plan = hub.call("hub_setup_plan", {**args, "scan": _scan(repo)})[1]
        files, checks = _apply(repo, plan["steps"])
        return plan, hub.call("hub_setup_confirm", {"project_id": pid, "token": tok, "files": files, "checks": checks})[1]

    step()
    plan, conf = step()
    ids = [s_["id"] for s_ in plan["steps"]]
    forged = hub.call("hub_setup_confirm", {"project_id": pid, "token": tok, "files": [{"path": "CLAUDE.md", "sha256": ""}], "checks": []})[1]
    legacy_render = hub.call("hub_guide_render", {"harness": "claude-code", "current": (repo / "CLAUDE.md").read_text(encoding="utf-8")}, tok)[1]
    (repo / "CLAUDE.md").write_text("# 새 진입 파일\n", encoding="utf-8")
    again, done = step()
    ok = ("harness:mcp-json" in ids and "entry:claude-code" not in ids and [b["id"] for b in plan["blocked"]] == ["entry:claude-code"]
          and conf.get("setup_complete") is False and any(u["id"] == "entry:claude-code" for u in conf["unconfirmed"])
          and forged.get("setup_complete") is False and legacy_render.get("blocked") is True
          and legacy_render.get("reason") == "legacy_1x_requires_migration"
          and not again["blocked"] and done.get("setup_complete") is True)
    _record("case 9 (막힌 진입 파일 — 미완료로 남음 · MCP 단계는 나옴 · guide_render 같은 판정 · 풀리면 완료)", ok,
            f"ids={ids} blocked={plan['blocked']} conf={conf} forged={forged.get('setup_complete')} render={legacy_render.get('reason')} done={done}")


def _measure(tmp: Path, cmd: list[str] | None) -> None:
    impl = tmp.name
    print(f"  --- [{impl}] ---")
    tmp.mkdir()
    db = tmp / "hub.db"
    before = len(_failures)
    hub = Hub(db, cmd_prefix=cmd)
    try:
        # 예외로 죽어도 어느 case 가 왜 깨졌는지 요약에 남긴다 — 못 돈 case 는 통과가 아니다.
        try:
            pid, tok, repo = case_3_to_6(hub, tmp)
        except Exception as exc:  # noqa: BLE001
            _record("case 3~6 (셋업)", False, f"예외: {exc!r}")
            _record("case 7 (세션 시작)", False, "선행 case 3~6 실패로 돌지 못함")
            _record("case 8 (안내 페이지)", False, "선행 case 3~6 실패로 돌지 못함")
        else:
            try:
                case_7_session(hub, tmp, db, pid, tok, repo)
            except Exception as exc:  # noqa: BLE001
                _record("case 7 (세션 시작)", False, f"예외: {exc!r}")
            case_8_page(hub, tok)
        try:
            case_9_blocked_entry(hub, tmp)
        except Exception as exc:  # noqa: BLE001
            _record("case 9 (막힌 진입 파일)", False, f"예외: {exc!r}")
    finally:
        err = hub.stop()
        if len(_failures) > before:
            print(f"  --- [{impl}] 허브 stderr ---\n" + err[-2000:])


def main() -> int:
    print("=== 허브 부트스트랩 · 지침 · 세션 시작 (M-034) ===")
    case_1_single_source()
    case_2_merge()
    with tempfile.TemporaryDirectory(prefix="hubboot-") as d:
        _measure(Path(d) / "python", None)
        # 같은 계약을 Go 허브에도 잰다 — 홈랩이 실제로 도는 쪽이다 (TASK-2026-11-24-main-011)
        go_cmd, reason = _resolve_go_hub(Path(d))
        if go_cmd is None:
            print(f"    [unmeasured] go 허브 미측정: {reason}")
        else:
            _measure(Path(d) / "go", go_cmd)
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
