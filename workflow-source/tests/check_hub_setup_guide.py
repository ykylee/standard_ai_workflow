#!/usr/bin/env python3
"""에이전트용 셋업 가이드 ``/setup.md`` · 클라이언트 ``bootstrap`` · 원격 없는 등록 (M-039 WBS-39.1, 소유자 2026-11-21).

계약 정본: ``core/hub_spec.md`` §4.1 · §4.4 · §6.1. 실제 허브 프로세스 · 실제 git 저장소 · 허브가 내려준 클라이언트
원문으로 잰다. 하네스 명령(``codex``)은 PATH 앞의 가짜로 받는다 — 사용자 설정을 건드리지 않는다.

1. 페이지 — 토큰 없이 text/markdown, 주소 · 하네스 4종 명령이 안내 페이지와 한 정본, 부르는 도구가 도구 표에 있음, 토큰 없음
2. git 저장소가 아니면 멈춘다 — not_git_repo, 쓴 파일 0
3. 원격 없는 빈 저장소 — 로컬 키 등록 · .gitignore · env(600) · 진입 파일, .mcp.json 은 for_agent 로 넘김 → 에이전트가 쓰고
   다시 부르면 complete (resumed). 출력에 토큰 없음
4. 원격 묶기 — agent 403 · 소유자 묶기 · 같은 주소 already · 다른 프로젝트 주소 409 alias_taken, 묶은 뒤 주소 조회가 찾는다
5. 같은 원격의 두 번째 환경 — 합류(같은 프로젝트), codex 단계는 명령 실행 결과로 확인
6. 1.x kit 흔적 — 진입 파일을 쓰지 않고 pending · legacy_1x, 진입 파일 바이트 그대로
7. Antigravity — 등록 전에는 pending(토큰 가린 명령), 다른 주소 · 꺼진 항목도 pending, 사람이 등록한 뒤(`agy mcp list` 에
   이 주소 · enabled) 다시 부르면 complete. 클라이언트는 agy 에 등록 명령을 내지 않는다
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 300

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/check_hub_core.py",  # 허브 프로세스 도우미(Hub)를 빌려 쓴다
    "workflow-source/pyproject.toml",
    "docs/HUB_OPERATIONS.md",
    "workflow-source/core/hub_go_spec.md",
)

import json
import os
import stat
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

from check_hub_core import Hub  # noqa: E402
from workflow_kit.hub import guide_page, setup  # noqa: E402
from workflow_kit.hub.tools import TOOLS  # noqa: E402

_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail and not ok else ''}")


def _clean_env(fake_bin: Path, home: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("WORKFLOW_HUB_", "GIT_"))}
    env.update({"PATH": f"{fake_bin}{os.pathsep}{env.get('PATH', '')}", "HOME": str(home),
                "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
                "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"})
    return env


class Env:
    def __init__(self, hub: Hub, root: Path, env: dict[str, str], client_src: str) -> None:
        self.hub, self.root, self.env, self.client_src = hub, root, env, client_src
        root.mkdir(parents=True, exist_ok=True)

    def git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.root, env=self.env, check=True, capture_output=True)

    def bootstrap(self, *args: str) -> tuple[int, dict[str, Any], str]:
        client = self.root / ".workflow-hub" / "hub_client.py"
        client.parent.mkdir(exist_ok=True)
        client.write_text(self.client_src, encoding="utf-8")
        p = subprocess.run([sys.executable, "-I", str(client), "bootstrap", self.hub.base, *args], cwd=self.root,
                           env=self.env, capture_output=True, text=True, encoding="utf-8", timeout=120)
        try:
            out = json.loads(p.stdout)
        except ValueError:
            out = {}
        return p.returncode, out, p.stdout + p.stderr

    def files(self) -> list[str]:
        return sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*")
                      if p.is_file() and ".git" not in p.relative_to(self.root).parts[:1])

    def token(self) -> str:
        for line in (self.root / ".workflow-hub" / "env").read_text(encoding="utf-8").splitlines():
            if line.startswith("WORKFLOW_HUB_TOKEN="):
                return line.split("=", 1)[1]
        return ""


def case_1_page(hub: Hub) -> None:
    r = urllib.request.urlopen(hub.base + "/setup.md", timeout=10)
    body = r.read().decode("utf-8")
    ctype = r.headers.get("content-type") or ""
    cmds = guide_page.harness_commands(hub.base)
    problems = []
    if not ctype.startswith("text/markdown"):
        problems.append(f"content-type={ctype}")
    if f"{hub.base}/v1/bootstrap/hub_client.py" not in body:
        problems.append("클라이언트 주소 없음")
    problems += [f"{h} 명령 다름" for h, c in cmds.items() if f"`{c['before']}`" not in body]
    problems += [f"없는 도구 {t}" for t in guide_page.SETUP_TOOLS if t not in TOOLS]
    problems += [f"페이지에 없는 도구 {t}" for t in guide_page.SETUP_TOOLS if t not in body]
    if "wfh_" in body:
        problems.append("토큰 머리")
    landing = urllib.request.urlopen(hub.base + "/", timeout=10).read().decode("utf-8")
    if 'href="setup.md"' not in landing:
        problems.append("안내 페이지에 링크 없음")
    _record("case 1 (페이지 — markdown · 한 정본 명령 · 도구 표 · 토큰 없음 · 안내 링크)", not problems, "; ".join(problems))


def case_2_not_git(e: Env) -> None:
    rc, out, raw = e.bootstrap("--harness", "claude-code", "--callsign", "yk-plain", "--kind", "human")
    left = [f for f in e.files() if f != ".workflow-hub/hub_client.py"]
    _record("case 2 (git 저장소 아님 — 멈춤 · 쓴 파일 0)", rc == 1 and out.get("status") == "not_git_repo" and not left,
            f"rc={rc} out={raw[:300]} files={left}")


def case_3_local(e: Env) -> tuple[str, str]:
    e.git("init", "-q", "-b", "main")
    rc, out, raw = e.bootstrap("--harness", "claude-code", "--callsign", "yk-local", "--kind", "human", "--name", "빈 저장소")
    problems = []
    tok = e.token() if (e.root / ".workflow-hub/env").is_file() else ""
    if rc != 3 or out.get("status") != "partial":
        problems.append(f"첫 실행 rc={rc} status={out.get('status')}")
    if not out.get("local_key") or not str(out.get("key", "")).startswith("local:"):
        problems.append(f"로컬 키 아님 key={out.get('key')}")
    if not tok or tok in raw or "wfh_" in raw:
        problems.append("토큰 없음 또는 출력에 토큰")
    mode = stat.S_IMODE((e.root / ".workflow-hub/env").stat().st_mode) if tok else None
    if os.name == "posix" and mode != 0o600:
        problems.append(f"env 권한 {oct(mode or 0)}")
    if "/.workflow-hub/" not in (e.root / ".gitignore").read_text(encoding="utf-8").split():
        problems.append(".gitignore 줄 없음")
    claude = e.root / "CLAUDE.md"
    if not claude.is_file() or "workflow-hub:begin" not in claude.read_text(encoding="utf-8"):
        problems.append("CLAUDE.md 렌더 영역 없음")
    fa = {f["id"]: f for f in out.get("for_agent", [])}
    if set(fa) != {"harness:mcp-json"} or (e.root / ".mcp.json").exists():
        problems.append(f"for_agent={sorted(fa)} .mcp.json 있음={(e.root / '.mcp.json').exists()}")
    if "harness:mcp-json" in fa and ("wfh_" in fa["harness:mcp-json"]["content"]):
        problems.append(".mcp.json 내용에 토큰")
    # 에이전트 몫 — 내용 그대로 쓰고 다시 부른다
    if "harness:mcp-json" in fa:
        (e.root / ".mcp.json").write_text(fa["harness:mcp-json"]["content"], encoding="utf-8")
    rc2, out2, raw2 = e.bootstrap("--harness", "claude-code", "--callsign", "yk-local", "--kind", "human")
    if rc2 != 0 or out2.get("status") != "complete" or not out2.get("resumed") or (tok and tok in raw2):
        problems.append(f"두 번째 rc={rc2} status={out2.get('status')} resumed={out2.get('resumed')} pending={out2.get('pending')}")
    _record("case 3 (원격 없음 — 로컬 키 · 셋업 · for_agent 넘김 → 다시 불러 complete, 토큰 비노출)", not problems,
            "; ".join(problems))
    return str(out.get("project_id")), tok


def case_4_bind(hub: Hub, pid: str, owner_tok: str) -> str:
    remote = "https://git.example.invalid/team/fresh.git"
    problems = []
    st, ag, _ = hub.call("hub_callsign_register", {"project_id": pid, "callsign": "bot-one", "kind": "agent"})
    st_a, _, _ = hub.call("hub_project_bind_remote", {"remote_url": remote}, ag.get("token"))
    if st_a != 403:
        problems.append(f"agent 묶기 {st_a}")
    st_b, b, _ = hub.call("hub_project_bind_remote", {"remote_url": remote}, owner_tok)
    if st_b != 200 or b.get("already") is not False:
        problems.append(f"소유자 묶기 {st_b} {b}")
    st_c, c, _ = hub.call("hub_project_bind_remote", {"remote_url": "git@git.example.invalid:team/fresh"}, owner_tok)
    if st_c != 200 or c.get("already") is not True:
        problems.append(f"같은 주소 {st_c} {c}")
    _, lk, _ = hub.call("hub_project_lookup", {"remote_url": remote})
    if lk.get("project_id") != pid:
        problems.append(f"조회 {lk}")
    hub.call("hub_project_register", {"remote_url": "https://git.example.invalid/team/other", "display_name": "o",
                                      "callsign": "yk-other", "kind": "human"})
    st_d, d, _ = hub.call("hub_project_bind_remote", {"remote_url": "https://git.example.invalid/team/other"}, owner_tok)
    if st_d != 409 or d.get("error_code") != "alias_taken":
        problems.append(f"남의 주소 {st_d} {d.get('error_code')}")
    _record("case 4 (원격 묶기 — agent 403 · 묶기 · already · alias_taken 409 · 조회)", not problems, "; ".join(problems))
    return remote


def case_5_join(e: Env, pid: str, remote: str, fake_log: Path) -> None:
    e.git("init", "-q", "-b", "main")
    e.git("remote", "add", "origin", remote)
    rc, out, raw = e.bootstrap("--harness", "codex", "--callsign", "codex-two", "--kind", "agent")
    calls = fake_log.read_text(encoding="utf-8").splitlines() if fake_log.is_file() else []
    problems = []
    if rc != 0 or out.get("status") != "complete" or not out.get("joined") or out.get("project_id") != pid:
        problems.append(f"rc={rc} status={out.get('status')} joined={out.get('joined')} pid={out.get('project_id')} "
                        f"pending={out.get('pending')} for_agent={[f['id'] for f in out.get('for_agent', [])]}")
    if not any("mcp add workflow-hub" in c and "--bearer-token-env-var WORKFLOW_HUB_TOKEN" in c for c in calls):
        problems.append(f"codex 명령 {calls}")
    if not (e.root / "AGENTS.md").is_file():
        problems.append("AGENTS.md 없음")
    _record("case 5 (같은 원격의 두 번째 환경 — 합류 · codex 단계 실행 확인 · complete)", not problems, "; ".join(problems))


def case_6_legacy(e: Env) -> None:
    e.git("init", "-q", "-b", "main")
    claude = e.root / "CLAUDE.md"
    original = f"# 프로젝트\n\n<!-- {setup.LEGACY_1X_MARKERS[0]} 1.29.0 -->\n본문\n"
    claude.write_text(original, encoding="utf-8")
    rc, out, raw = e.bootstrap("--harness", "claude-code", "--callsign", "yk-legacy", "--kind", "human")
    pend = {p["id"] for p in out.get("pending", [])}
    ok = (rc == 3 and out.get("status") == "partial" and "entry:claude-code" in pend
          and (out.get("legacy_1x") or {}).get("files") and claude.read_text(encoding="utf-8") == original
          and (e.root / ".workflow-hub/env").is_file())
    _record("case 6 (1.x 흔적 — 진입 파일 안 씀 · pending · legacy_1x · env 는 씀)", ok,
            f"rc={rc} status={out.get('status')} pending={pend} legacy={out.get('legacy_1x')}")


def case_7_antigravity(e: Env, agy_list: Path, agy_log: Path) -> None:
    e.git("init", "-q", "-b", "main")
    problems = []
    mcp = e.hub.base + "/mcp"
    rows = {"none": "No MCP servers configured.\n",
            "other": "NAME          TYPE  STATUS   COMMAND/URL\nworkflow-hub  http  enabled  http://127.0.0.1:1/mcp\n",
            "disabled": f"NAME          TYPE  STATUS   COMMAND/URL\nworkflow-hub  http  disabled  {mcp}\n"}
    for label, listing in rows.items():
        agy_list.write_text(listing, encoding="utf-8")
        rc, out, raw = e.bootstrap("--harness", "antigravity", "--callsign", "agy-one", "--kind", "human")
        pend = {x["id"]: x for x in out.get("pending", [])}
        masked = " ".join(pend.get("harness:antigravity", {}).get("run_masked", []))
        tok = e.token() if (e.root / ".workflow-hub/env").is_file() else "?"
        if rc != 3 or "harness:antigravity" not in pend or tok in raw or "<WORKFLOW_HUB_TOKEN>" not in masked:
            problems.append(f"{label}: rc={rc} pending={sorted(pend)} 가림={'<WORKFLOW_HUB_TOKEN>' in masked}")
    agy_list.write_text(f"NAME          TYPE  STATUS   COMMAND/URL\nworkflow-hub  http  enabled  {mcp}\n", encoding="utf-8")
    rc, out, raw = e.bootstrap("--harness", "antigravity", "--callsign", "agy-one", "--kind", "human")
    if rc != 0 or out.get("status") != "complete" or "harness:antigravity" not in out.get("confirmed", []):
        problems.append(f"등록 뒤 rc={rc} status={out.get('status')} confirmed={out.get('confirmed')}")
    calls = agy_log.read_text(encoding="utf-8").splitlines() if agy_log.is_file() else []
    if any(c.startswith("mcp add") for c in calls):
        problems.append(f"클라이언트가 agy 등록 명령을 냈다 {calls}")
    _record("case 7 (Antigravity — 사람 몫 pending · 다른 주소/꺼짐 pending · 등록 뒤 list 로 complete · 등록 명령 0)",
            not problems, "; ".join(problems))


def case_8_operator_runtime_policy() -> None:
    """사내/보안 관리 Windows는 setup 때 Go 실행 파일 대신 Python만 권한다."""
    ops = (REPO_ROOT / "docs" / "HUB_OPERATIONS.md").read_text(encoding="utf-8")
    spec = (REPO_ROOT / "workflow-source" / "core" / "hub_go_spec.md").read_text(encoding="utf-8")
    start = ops.find("#### 셋업 전 사내 Windows 확인")
    end = ops.find("\n## 9.", start)
    section = ops[start:end] if start >= 0 and end >= 0 else ""
    problems = []
    for token in ("사내 관리형 Windows", "Python 허브만 선택", "담당자가 모르면", "Go 실행 파일", "백신을 끄거나 격리를 우회하지 않는다"):
        if token not in section:
            problems.append(f"운영 안내에 정책이 없다: {token}")
    if "-m workflow_kit hub serve" not in section:
        problems.append("Windows Python hub serve 예시가 없다")
    if "TASK-2026-11-23-main-014" not in spec or "원인이나 오탐 여부는 미판정" not in spec:
        problems.append("Go 정본 스펙에 탐지 보고와 미판정 경계가 없다")
    _record("case 8 (사내 Windows 셋업은 Python-only · 미확인 탐지를 오탐 단정하지 않음)",
            not problems, "; ".join(problems))


def main() -> int:
    print("=== 에이전트용 셋업 가이드 · bootstrap · 원격 없는 등록 (M-039 WBS-39.1) ===")
    with tempfile.TemporaryDirectory(prefix="hubguide-") as d:
        tmp = Path(d)
        fake_bin, home = tmp / "bin", tmp / "home"
        fake_bin.mkdir()
        home.mkdir()
        fake_log = tmp / "codex.log"
        codex = fake_bin / "codex"
        codex.write_text(f"#!/bin/sh\necho \"$@\" >> {fake_log}\n", encoding="utf-8")
        codex.chmod(0o755)
        agy_list, agy_log = tmp / "agy.list", tmp / "agy.log"
        agy = fake_bin / "agy"
        agy.write_text(f"#!/bin/sh\necho \"$@\" >> {agy_log}\n[ \"$1 $2\" = \"mcp list\" ] && cat {agy_list}\nexit 0\n",
                       encoding="utf-8")
        agy.chmod(0o755)
        env = _clean_env(fake_bin, home)
        hub = Hub(tmp / "hub.db")
        try:
            src = urllib.request.urlopen(hub.base + "/v1/bootstrap/hub_client.py", timeout=10).read().decode("utf-8")
            case_1_page(hub)
            case_2_not_git(Env(hub, tmp / "plain", env, src))
            pid, tok = "", ""
            try:
                pid, tok = case_3_local(Env(hub, tmp / "fresh", env, src))
                remote = case_4_bind(hub, pid, tok)
                case_5_join(Env(hub, tmp / "second", env, src), pid, remote, fake_log)
            except Exception as exc:  # noqa: BLE001 — 못 돈 case 는 통과가 아니다
                _record("case 3~5", False, f"예외: {exc!r}")
            case_6_legacy(Env(hub, tmp / "legacy", env, src))
            case_7_antigravity(Env(hub, tmp / "agy", env, src), agy_list, agy_log)
            case_8_operator_runtime_policy()
        finally:
            err = hub.stop()
            if _failures:
                print("  --- 허브 stderr ---\n" + err[-2000:])
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
