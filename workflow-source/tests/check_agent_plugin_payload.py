#!/usr/bin/env python3
"""`plugin/` payload 가 **정본에서 생성된 파생물인가** (v1.1.9+).

## 왜 필요한가

플러그인 배포 전환 계획(`docs/planning/plugin-transition-plan-2026-08.md`)의 원칙 1은
"플러그인은 파생본이다" 이고, §5 리스크 표는 그 실패 모드를 이렇게 적어 뒀다:
**"플러그인 산출물이 손 편집으로 오염"**. 이 저장소는 그 실패를 이미 두 번 실측했다
— §11.1 명령의 손 사본 7곳, 그리고 MCP 도구 목록이 13개 중 10개에서 멈춰 있던 사본.
사본은 갈라지고, 갈라져도 아무 검사가 실패하지 않으면 아무도 모른다.

그래서 `plugin/` 은 `state.json` 과 같은 지위다 — **생성물**이고, 손으로 고치면
이 검사가 FAIL 한다.

## 판정 규칙 (9 case)

1. **디스크 == 생성물** — `render_agent_plugin()` 재생성 결과와 완전 일치.
   미등록 파일이 payload 안에 있어도 FAIL (손으로 끼워 넣은 파일을 잡는다).
2. **frontmatter 스키마** — agentskills.io / skill-lint 규칙 (유효한 YAML 매핑,
   `name` 은 1–64자 소문자 `[a-z0-9-]`, `description` 은 1–1024자).
3. **§11 이 실린다** — 각 SKILL.md 가 정본 §11.1 명령과 §11.2 계약을 담는다.
   메모리 갱신을 지시하면서 방법을 안 알려주면 에이전트가 손으로 쓴다.
4. **version == `workflow_kit.__version__`** — 릴리스 bump 와 어긋난 manifest 는
   marketplace 가 낡은 버전을 광고하게 만든다 (P4 에서 선재생성 목록에 편입).
5. **mcp.json == registry 파생** — read-only bundle 서버 하나만, command/args 는
   `mcp_server_command()` 와 일치, write 도구는 payload 에 없다 (ADR-003 opt-in).
6. **렌더러에 규칙 리터럴 없음** — `plugin_payload.py` 가 §1·§3·§8·§11 문장을
   직접 들고 있으면 그건 사본이다.
7. **탐지기가 동작한다** — temp 사본을 오염시키면 1번이 실제로 FAIL 해야 한다.
8. **Claude Code 어댑터가 로드되는 형태** — `claude plugin details` 실측이 못박은
   계약을 코드로 고정한다 (관례 경로 `.mcp.json`, manifest 의 `mcpServers` 경로
   필드 금지, `..` 금지, hook 2종이 `wk` 부재를 검사).
9. **marketplace 가 payload 를 가리키고 버전이 동기** — `/plugin install` 경로.

**한계**: Agent Plugins 1.0 의 선택 필드 전체 스펙은 아직 원문 확인이 안 됐다
(2026-08-06 출범). 이 검사는 계획 §3-P1 이 명시한 3필드(name/version/description)를
**고정**한다 — 스펙 확인 후 필드를 늘릴 때 이 검사가 먼저 FAIL 하므로, 갱신이
명시 task 를 거치게 된다 (계획 §5 리스크 완화 "스키마를 fixture 로 고정").

Cross-ref: `workflow_kit/plugin_payload.py`, `docs/planning/plugin-transition-plan-2026-08.md` §3-P1.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit import __version__ as KIT_VERSION  # noqa: E402
from workflow_kit.common.standard_rules import load_standard_rules  # noqa: E402
from workflow_kit.plugin_payload import (  # noqa: E402
    CLAUDE_CODE_HOOKS_RELPATH,
    CLAUDE_CODE_MANIFEST_RELPATH,
    CLAUDE_CODE_MCP_RELPATH,
    MARKETPLACE_RELPATH,
    PAYLOAD_DIRNAME,
    PLUGIN_NAME,
    PLUGIN_SKILLS,
    PAYLOAD_MCP_BRIDGE,
    PAYLOAD_MCP_BUNDLE,
    default_payload_root,
    default_repo_root,
    diff_payload,
    diff_repo_plugin_files,
    render_agent_plugin,
    render_repo_plugin_files,
    write_agent_plugin,
)

PAYLOAD_ROOT = default_payload_root()
RENDERER = SOURCE_ROOT / "workflow_kit" / "plugin_payload.py"
NAME_RE = re.compile(r"^(?!-)(?!.*--)[a-z0-9-]{1,64}(?<!-)$")

#: manifest 가 선언해도 되는 필드 — 계획 §3-P1 의 계약. 스펙 확인 전까지 고정.
MANIFEST_FIELDS = {"name", "version", "description"}

FAILURES: list[str] = []


def _record(name: str, ok: bool, detail: str = "") -> None:
    print(f"\n[{name}]")
    if ok:
        print("  PASS" + (f": {detail}" if detail else ""))
    else:
        print(f"  FAIL: {detail}")
        FAILURES.append(name)


def _yaml():
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        return None
    return yaml


def _skill_frontmatter(text: str) -> str | None:
    m = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    return m.group(1) if m else None


def test_payload_matches_generator() -> None:
    """1) 디스크의 산출물(payload + 어댑터 + marketplace)이 재생성 결과와 같은가."""
    if not PAYLOAD_ROOT.is_dir():
        _record(
            "test_payload_matches_generator",
            False,
            f"{PAYLOAD_ROOT.relative_to(REPO_ROOT)} 부재 — "
            "`python3 -m workflow_kit.plugin_payload --apply` 로 생성한다",
        )
        return
    problems = diff_repo_plugin_files(default_repo_root())
    _record(
        "test_payload_matches_generator",
        not problems,
        "; ".join(problems[:5]) if problems else f"산출물 {len(render_repo_plugin_files())}개 일치",
    )


def test_skill_frontmatter_valid() -> None:
    """2) SKILL.md frontmatter 가 agentskills.io 규칙을 지키는가."""
    yaml = _yaml()
    if yaml is None:
        _record("test_skill_frontmatter_valid", False, "PyYAML 부재 — dev extra 에 선언돼 있어야 한다")
        return
    payload = render_agent_plugin()
    problems: list[str] = []
    slugs = {spec.slug for spec in PLUGIN_SKILLS}
    seen: set[str] = set()
    for relpath, content in payload.items():
        if not relpath.endswith("SKILL.md"):
            continue
        fm = _skill_frontmatter(content)
        if fm is None:
            problems.append(f"{relpath}: frontmatter 없음")
            continue
        try:
            data = yaml.safe_load(fm)
        except Exception as e:  # noqa: BLE001
            problems.append(f"{relpath}: YAML 파싱 실패 {type(e).__name__}")
            continue
        if not isinstance(data, dict):
            problems.append(f"{relpath}: frontmatter 가 매핑이 아니다")
            continue
        name = data.get("name")
        if not isinstance(name, str) or not NAME_RE.match(name):
            problems.append(f"{relpath}: name 형식 위반 {name!r}")
        else:
            seen.add(name)
            if not relpath.startswith(f"skills/{name}/"):
                problems.append(f"{relpath}: name({name}) 과 디렉터리가 어긋난다")
        desc = data.get("description")
        if not isinstance(desc, str) or not 1 <= len(desc) <= 1024:
            problems.append(f"{relpath}: description 누락 또는 길이 위반")
    if seen != slugs:
        problems.append(f"스킬 집합 불일치: 선언 {sorted(slugs)} vs 산출 {sorted(seen)}")
    _record(
        "test_skill_frontmatter_valid",
        not problems,
        "; ".join(problems[:5]) if problems else f"스킬 {len(seen)}종 frontmatter 유효",
    )


def test_skills_carry_memory_section() -> None:
    """3) 각 SKILL.md 가 정본 §11 명령·계약을 담는가."""
    rules = load_standard_rules(SOURCE_ROOT)
    payload = render_agent_plugin(rules)
    memory_cmd = rules.memory_commands[0][1]
    contract_probe = rules.parse_contract[0]
    problems: list[str] = []
    for relpath, content in payload.items():
        if not relpath.endswith("SKILL.md"):
            continue
        if memory_cmd not in content:
            problems.append(f"{relpath}: §11.1 갱신 명령 누락")
        if contract_probe not in content:
            problems.append(f"{relpath}: §11.2 파싱 계약 누락")
    _record(
        "test_skills_carry_memory_section",
        not problems,
        "; ".join(problems[:5]) if problems else "스킬 전부 §11 명령 + 계약 포함",
    )


def test_manifest_version_matches_kit() -> None:
    """4) plugin.json 이 kit 버전과 계약 필드를 지키는가."""
    manifest = json.loads(render_agent_plugin()["plugin.json"])
    problems: list[str] = []
    if set(manifest) != MANIFEST_FIELDS:
        problems.append(
            f"필드 집합 {sorted(manifest)} != 계약 {sorted(MANIFEST_FIELDS)} "
            "(Agent Plugins 스펙 확인 후 명시 task 로만 늘린다 — 계획 §5)"
        )
    if manifest.get("version") != KIT_VERSION:
        problems.append(f"version {manifest.get('version')!r} != __version__ {KIT_VERSION!r}")
    if not manifest.get("description"):
        problems.append("description 이 비어 있다")
    _record(
        "test_manifest_version_matches_kit",
        not problems,
        "; ".join(problems[:3]) if problems else f"manifest 3필드 + version {KIT_VERSION}",
    )


def test_mcp_matches_read_only_bundle() -> None:
    """5) mcp.json 이 registry 의 read-only bundle 파생인가."""
    from workflow_kit.bootstrap_lib.mcp import (
        MCP_SERVER_ALIAS,
        MCP_WRITE_SERVER_ALIAS,
        mcp_server_command,
    )
    from workflow_kit.server.read_only_registry import tool_specs_for_bundle

    config = json.loads(render_agent_plugin()["mcp.json"])
    servers = config.get("mcpServers", {})
    problems: list[str] = []
    if set(servers) != {MCP_SERVER_ALIAS}:
        problems.append(f"서버 alias {sorted(servers)} != {{{MCP_SERVER_ALIAS}}}")
    if MCP_WRITE_SERVER_ALIAS in servers:
        problems.append(
            f"write bundle({MCP_WRITE_SERVER_ALIAS}) 이 payload 에 실렸다 — "
            "파일을 바꾸는 도구는 명시 opt-in 이다 (ADR-003)"
        )
    entry = servers.get(MCP_SERVER_ALIAS, {})
    expected = mcp_server_command(PAYLOAD_MCP_BRIDGE, PAYLOAD_MCP_BUNDLE)
    if [entry.get("command"), *entry.get("args", [])] != expected:
        problems.append(f"command/args 가 mcp_server_command 파생이 아니다: {entry.get('args')}")
    if not tool_specs_for_bundle(PAYLOAD_MCP_BUNDLE):
        problems.append(f"registry 의 {PAYLOAD_MCP_BUNDLE} bundle 이 비었다")
    if any(not spec.read_only for spec in tool_specs_for_bundle(PAYLOAD_MCP_BUNDLE)):
        problems.append("read-only bundle 에 write 도구가 섞였다 — registry 선언을 확인하라")
    _record(
        "test_mcp_matches_read_only_bundle",
        not problems,
        "; ".join(problems[:3])
        if problems
        else f"read-only bundle {len(tool_specs_for_bundle(PAYLOAD_MCP_BUNDLE))}개 도구, write 미탑재",
    )


def test_renderer_has_no_rule_literals() -> None:
    """6) 렌더러가 규칙 문장을 직접 들고 있지 않은가."""
    rules = load_standard_rules(SOURCE_ROOT)
    src = RENDERER.read_text(encoding="utf-8")
    literals = [
        *rules.principles,
        *rules.parse_contract,
        rules.close_order,
        *(cmd for _, cmd in rules.memory_commands),
    ]
    hits = [text for text in literals if text in src]
    _record(
        "test_renderer_has_no_rule_literals",
        not hits,
        f"규칙 리터럴 사본 {hits[:2]} — 정본 파생 함수를 거쳐야 한다"
        if hits
        else f"리터럴 사본 0건 ({len(literals)}개 문장 대조)",
    )


def test_detector_catches_drift() -> None:
    """7) 오염을 실제로 잡는가 (temp 사본에서 실증 — 저장소는 건드리지 않는다)."""
    payload = render_agent_plugin()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "plugin"
        write_agent_plugin(root, payload)
        if diff_payload(root, payload):
            _record("test_detector_catches_drift", False, "갓 생성한 payload 가 이미 드리프트로 판정된다")
            return

        # (a) 손 편집
        target = root / "skills" / PLUGIN_SKILLS[0].slug / "SKILL.md"
        target.write_text(target.read_text(encoding="utf-8") + "\n손으로 덧붙인 줄\n", encoding="utf-8")
        if not diff_payload(root, payload):
            _record("test_detector_catches_drift", False, "손 편집을 검출하지 못했다")
            return
        write_agent_plugin(root, payload)

        # (b) 파일 삭제
        (root / "plugin.json").unlink()
        if not diff_payload(root, payload):
            _record("test_detector_catches_drift", False, "파일 삭제를 검출하지 못했다")
            return
        write_agent_plugin(root, payload)

        # (c) 미등록 파일 끼워 넣기
        (root / "skills" / "hand-written" / "SKILL.md").parent.mkdir(parents=True, exist_ok=True)
        (root / "skills" / "hand-written" / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
        if not diff_payload(root, payload):
            _record("test_detector_catches_drift", False, "미등록 파일을 검출하지 못했다")
            return
        shutil.rmtree(root / "skills" / "hand-written")

        if diff_payload(root, payload):
            _record("test_detector_catches_drift", False, "복원 후에도 드리프트가 남는다")
            return
    _record("test_detector_catches_drift", True, "손 편집 / 삭제 / 미등록 파일 3종 전부 검출")


def test_claude_code_adapter() -> None:
    """8) Claude Code 어댑터가 **로드되는 형태**인가 (실측으로 고정한 계약).

    `claude plugin details` 실측이 두 가지를 못박았다:
    - manifest 에 ``mcpServers`` 경로 필드를 선언하면 validate 는 통과하지만
      서버가 **로드되지 않는다** (인벤토리 0). 관례 경로 `.mcp.json` 만 잡힌다.
    - 경로 필드의 ``..`` 는 거부된다 → 플러그인 루트 = payload 루트.
    """
    payload = render_agent_plugin()
    problems: list[str] = []

    manifest = json.loads(payload[CLAUDE_CODE_MANIFEST_RELPATH])
    if manifest.get("name") != PLUGIN_NAME or manifest.get("version") != KIT_VERSION:
        problems.append(f"manifest name/version 불일치: {manifest.get('name')} {manifest.get('version')}")
    if not manifest.get("author"):
        problems.append("author 누락 — `claude plugin validate --strict` 가 경고를 에러로 올린다")
    if "mcpServers" in manifest:
        problems.append(
            "manifest 에 mcpServers 경로 필드가 있다 — validate 는 통과하지만 "
            "로더가 무시한다 (실측: 인벤토리 MCP servers 0). 관례 경로 .mcp.json 을 쓴다"
        )
    for key, value in manifest.items():
        if isinstance(value, str) and ".." in value:
            problems.append(f"{key} 에 '..' 경로 — Claude Code 가 traversal 로 거부한다")

    if payload.get(CLAUDE_CODE_MCP_RELPATH) != payload.get("mcp.json"):
        problems.append(f"{CLAUDE_CODE_MCP_RELPATH} 와 mcp.json 의 내용이 다르다 — 같은 렌더러 파생이어야 한다")

    hooks = json.loads(payload[CLAUDE_CODE_HOOKS_RELPATH]).get("hooks", {})
    if set(hooks) != {"SessionStart", "SessionEnd"}:
        problems.append(f"hook 이벤트 {sorted(hooks)} != SessionStart/SessionEnd")
    rules = load_standard_rules(SOURCE_ROOT)
    refresh_cmd = rules.memory_commands[-1][1]
    commands = [
        entry.get("command", "")
        for matchers in hooks.values()
        for matcher in matchers
        for entry in matcher.get("hooks", [])
    ]
    if not any(refresh_cmd in cmd for cmd in commands):
        problems.append(f"SessionEnd 가 §11.1 재생성 명령({refresh_cmd})을 부르지 않는다")
    binary = refresh_cmd.split()[0]
    if not all(f"command -v {binary}" in cmd for cmd in commands):
        problems.append(
            f"`{binary}` 부재 검사가 없는 hook 이 있다 — 조용한 실패 금지 (계획 원칙 4)"
        )
    _record(
        "test_claude_code_adapter",
        not problems,
        "; ".join(problems[:4])
        if problems
        else f"manifest 계약 + hooks 2종 + .mcp.json == mcp.json",
    )


def test_marketplace_manifest() -> None:
    """9) marketplace 가 payload 를 가리키고 버전이 동기인가."""
    files = render_repo_plugin_files()
    market = json.loads(files[MARKETPLACE_RELPATH])
    problems: list[str] = []
    if not market.get("description"):
        problems.append("description 누락 — `validate --strict` 가 경고를 에러로 올린다")
    if not market.get("owner"):
        problems.append("owner 누락")
    entries = market.get("plugins", [])
    if len(entries) != 1:
        problems.append(f"plugins 항목 {len(entries)}개 — 1개여야 한다")
    else:
        entry = entries[0]
        if entry.get("source") != f"./{PAYLOAD_DIRNAME}":
            problems.append(f"source {entry.get('source')!r} 가 payload 를 가리키지 않는다")
        if entry.get("version") != KIT_VERSION:
            problems.append(f"version {entry.get('version')!r} != __version__ {KIT_VERSION!r}")
        if entry.get("name") != PLUGIN_NAME:
            problems.append(f"name {entry.get('name')!r} != {PLUGIN_NAME!r}")
    _record(
        "test_marketplace_manifest",
        not problems,
        "; ".join(problems[:3]) if problems else f"marketplace → ./{PAYLOAD_DIRNAME}, version {KIT_VERSION}",
    )


def main() -> int:
    test_payload_matches_generator()
    test_skill_frontmatter_valid()
    test_skills_carry_memory_section()
    test_manifest_version_matches_kit()
    test_mcp_matches_read_only_bundle()
    test_renderer_has_no_rule_literals()
    test_detector_catches_drift()
    test_claude_code_adapter()
    test_marketplace_manifest()
    total = 9
    print(f"\n{total - len(FAILURES)}/{total} passed")
    if FAILURES:
        raise AssertionError(f"{len(FAILURES)} case(s) failed: {FAILURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
