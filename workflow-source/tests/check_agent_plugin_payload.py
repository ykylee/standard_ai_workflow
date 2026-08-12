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

## 판정 규칙 (13 case)

1. **디스크 == 생성물** — `render_agent_plugin()` 재생성 결과와 완전 일치.
   미등록 파일이 payload 안에 있어도 FAIL (손으로 끼워 넣은 파일을 잡는다).
2. **frontmatter 스키마** — agentskills.io / skill-lint 규칙 (유효한 YAML 매핑,
   `name` 은 1–64자 소문자 `[a-z0-9-]`, `description` 은 1–1024자).
3. **§11 이 실린다** — 각 SKILL.md 가 정본 §11.1 명령과 §11.2 계약을 담는다.
   메모리 갱신을 지시하면서 방법을 안 알려주면 에이전트가 손으로 쓴다.
4. **version == `workflow_kit.__version__`** — 릴리스 bump 와 어긋난 manifest 는
   marketplace 가 낡은 버전을 광고하게 만든다 (P4 에서 릴리스 게이트로 강제).
5. **mcp.json == registry 파생** — read-only bundle 서버 하나만, command/args 는
   `mcp_server_command()` 와 일치, write 도구는 payload 에 없다 (ADR-003 opt-in).
6. **렌더러에 규칙 리터럴 없음** — `plugin_payload.py` 가 §1·§3·§8·§11 문장을
   직접 들고 있으면 그건 사본이다.
7. **탐지기가 동작한다** — temp 사본을 오염시키면 1번이 실제로 FAIL 해야 한다.
8. **Claude Code 어댑터가 로드되는 형태** — `claude plugin details` 실측이 못박은
   계약을 코드로 고정한다 (관례 경로 `.mcp.json`, manifest 의 `mcpServers` 경로
   필드 금지, `..` 금지, hook 2종이 `wk` 부재를 검사).
9. **marketplace 가 payload 를 가리키고 버전이 동기** — `/plugin install` 경로.
10. **버전이 호출 시점에 결정된다** — bump→재생성 stale 함정. 디스크 대조(1번)는
    매번 새 프로세스라 이 자리를 못 잡는다 (P4 실측).
11. **릴리스 게이트가 플러그인 드리프트를 막는다** — 파이프라인은 판정만 하고
    쓰지 않는다 (bump 부수효과로 쓰면 원본 오염을 낳았다).
12. **설명 문장의 스킬 개수가 실제와 맞는다** — 사용자에게 가장 먼저 보이는
    문장인데 아무 검사도 보고 있지 않았다 (session-end 추가 시 실측).
13. **판정 대상이 작업 트리다** — 모듈이 로드된 위치를 보면 사본을 릴리스하며
    원본의 정합을 확인하게 된다 (P4 구현 중 실제로 냈던 사고의 뿌리).

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

REQUIRES_QUIET_REPO = True
"""이 check 는 **원본 저장소의 산출물을 byte 대조**한다 (case 1·11·13) — 전역 상태
관찰이다. 병렬 구간에서 다른 check 의 transient write 와 race 하면 위양성이 난다.
CLAUDE.md 의 `REQUIRES_QUIET_REPO` 규약 그대로 정숙 구간에서 돈다.

실제로 그 race 는 실재한다: 릴리스 검사 여럿이 원본 `pyproject.toml` 의 version 을
bump 했다 되돌리고 (실측: 1.1.8 → 1.1.9 → 1.1.8, 왕복 86ms), case 1 의 재생성은
그 version 을 **호출 시점에** 읽는다 (P4 의 `current_kit_version()`).
"""

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


#: 버전 문자열을 **복사해 담는** 산출물. bump 를 따라가야 하는 것이 정확히 이 3장이다.
VERSION_BEARING_RELPATHS = (
    f"{PAYLOAD_DIRNAME}/plugin.json",
    f"{PAYLOAD_DIRNAME}/{CLAUDE_CODE_MANIFEST_RELPATH}",
    MARKETPLACE_RELPATH,
)


def test_version_resolved_at_call_time() -> None:
    """10) 버전이 **호출 시점**에 결정되는가 (bump→재생성 stale 함정).

    P4 실측(TASK-2026-08-12-main-017)이 잡은 자리다. 버전이 두 겹으로 굳어 있었다:
    ``workflow_kit.__version__`` 은 import 시점 1회 파싱이고, 렌더러의
    ``version: str = KIT_VERSION`` 기본 인자는 **함수 정의 시점** 고정이다. 그래서
    릴리스 파이프라인이 한 프로세스에서 bump 한 뒤 재생성하면 낡은 버전이 조용히
    박힌다 — 실측에서 ``__version__`` 을 바꿔도 재생성 결과는 bump 이전 값이었다.

    검사는 매번 새 프로세스라 **디스크 대조(case 1)로는 영영 안 잡힌다.** 그래서
    호출 시점 결정 자체를 판정한다: :func:`current_kit_version` 을 갈아끼우면
    재생성 결과가 따라와야 한다. 기본 인자 고정이 되살아나면 여기서 FAIL 한다.
    """
    import workflow_kit.plugin_payload as pp

    sentinel = "v0.0.0-callsite"
    original = pp.current_kit_version
    try:
        pp.current_kit_version = lambda: sentinel  # type: ignore[assignment]
        rendered = pp.render_repo_plugin_files()
    finally:
        pp.current_kit_version = original  # type: ignore[assignment]

    problems: list[str] = []
    for relpath in VERSION_BEARING_RELPATHS:
        doc = json.loads(rendered[relpath])
        found = doc["plugins"][0]["version"] if relpath == MARKETPLACE_RELPATH else doc["version"]
        if found != sentinel:
            problems.append(
                f"{relpath}: {found!r} != {sentinel!r} — 버전이 import/정의 시점에 굳었다"
            )

    # 명시 인자 경로도 같은 3장을 덮어야 한다 (파이프라인이 쓰는 계약).
    explicit = render_repo_plugin_files(version="v0.0.0-explicit")
    for relpath in VERSION_BEARING_RELPATHS:
        doc = json.loads(explicit[relpath])
        found = doc["plugins"][0]["version"] if relpath == MARKETPLACE_RELPATH else doc["version"]
        if found != "v0.0.0-explicit":
            problems.append(f"{relpath}: 명시 version 인자가 반영되지 않는다 ({found!r})")

    _record(
        "test_version_resolved_at_call_time",
        not problems,
        "; ".join(problems[:3])
        if problems
        else f"manifest {len(VERSION_BEARING_RELPATHS)}장이 호출 시점 버전을 따른다",
    )


def test_release_gate_catches_plugin_drift() -> None:
    """11) 릴리스 파이프라인이 플러그인 정합을 **보고하고, 게이트가 막는가**.

    manifest 3장은 pyproject version 을 복사해 담으므로, 어긋난 채 릴리스하면
    marketplace 가 낡은 버전을 광고한다 (v1.1.7 stamp 누락 동형).

    **파이프라인은 쓰지 않는다** — 이게 소유자 판정이다 (2026-08-12). 처음에는
    bump 가 곧바로 재생성하게 짰는데, 릴리스 검사 여럿이 *원본 저장소*에서 bump 를
    apply 한 뒤 되돌리고 (실측: pyproject 가 86ms 만에 1.1.8→1.1.9→1.1.8) 그 복원은
    플러그인을 모른다 — manifest 만 낡은 채 남아 전량 검사가 매번 FAIL 했다. 그래서
    `state.json` 과 같은 규율로 바꿨다: 생성물은 사람이 명령으로 재생성하고,
    **게이트가 정합을 강제한다.**

    그래서 이 case 가 고정하는 것은 셋이다: ①bump 3경로가 상태를 보고한다
    ②파이프라인 어디에도 플러그인 **쓰기**가 없다 ③`cmd_validate` 가 어긋남을
    ``ok=False`` 로 낸다.
    """
    from workflow_kit.tools import release_pipeline as rp

    src = (SOURCE_ROOT / "workflow_kit" / "tools" / "release_pipeline.py").read_text(encoding="utf-8")
    lines = src.splitlines()
    problems: list[str] = []

    # ① bump 3경로가 정합을 보고한다.
    call_lines = [
        i for i, line in enumerate(lines)
        if "write_workflow_kit_version(" in line and not line.lstrip().startswith("def ")
    ]
    for i in call_lines:
        if "plugin_payload_status(" not in "\n".join(lines[i : i + 12]):
            problems.append(
                f"release_pipeline.py:{i + 1} 의 bump 뒤에 plugin_payload_status 보고가 없다"
            )
    if not call_lines:
        problems.append("bump 호출 지점을 찾지 못했다 — 검사가 낡았다")

    # ② 파이프라인은 플러그인 산출물을 쓰지 않는다 (오염 재발 차단).
    for writer in ("write_repo_plugin_files", "write_agent_plugin"):
        if writer in src:
            problems.append(
                f"release_pipeline.py 가 {writer} 를 부른다 — 파이프라인은 판정만 한다"
            )

    # ③ 게이트가 어긋남을 잡는다 + 판정이 원본을 건드리지 않는다.
    before = {
        rel: (default_repo_root() / rel).read_bytes() for rel in VERSION_BEARING_RELPATHS
    }
    drifted = rp.plugin_payload_status("v0.0.0-gatetest")
    if not drifted.get("ok"):
        problems.append(f"판정 실패: {drifted.get('error')}")
    else:
        if drifted.get("in_sync"):
            problems.append("다른 버전인데 in_sync=True — 게이트가 못 잡는다")
        if drifted.get("drifted_count") != len(VERSION_BEARING_RELPATHS):
            problems.append(
                f"{drifted.get('drifted_count')}장을 짚었다 — "
                f"버전 담은 {len(VERSION_BEARING_RELPATHS)}장이어야 한다"
            )
        if not drifted.get("fix"):
            problems.append("fix 명령이 비어 있다 — 어긋났을 때 무엇을 하라는 안내가 없다")

    in_sync = rp.plugin_payload_status(rp.read_workflow_kit_version())
    if not in_sync.get("in_sync"):
        problems.append(f"현재 산출물이 정본과 어긋나 있다: {in_sync.get('drifted')}")

    for rel, original in before.items():
        if (default_repo_root() / rel).read_bytes() != original:
            problems.append(f"판정이 {rel} 을 건드렸다 — 읽기만 해야 한다")

    _record(
        "test_release_gate_catches_plugin_drift",
        not problems,
        "; ".join(problems[:3])
        if problems
        else f"bump {len(call_lines)}경로 보고 + 쓰기 0 + 게이트가 {len(VERSION_BEARING_RELPATHS)}장 검출",
    )


def test_descriptions_count_skills() -> None:
    """12) 설명 문장이 말하는 스킬 개수가 실제와 맞는가.

    P4 에서 `session-end` 를 넣은 직후 실측이 잡은 자리다: `claude plugin details`
    인벤토리는 ``Skills (4)`` 인데, 바로 위에 뜨는 플러그인 설명은 여전히
    **"스킬 3종"** 이었다. 개수를 손으로 적어 둔 사본이라 스킬을 늘릴 때 갈라진다 —
    §11.1 명령 사본 7곳, MCP 도구 목록이 13 중 10 에서 멈춰 있던 사본과 같은 계열.

    사용자에게 **가장 먼저 보이는 문장**이라 틀리면 바로 눈에 띄는데, 정작 어떤
    검사도 보고 있지 않았다.
    """
    expected = len(PLUGIN_SKILLS)
    files = render_repo_plugin_files()
    manifest = json.loads(files[f"{PAYLOAD_DIRNAME}/plugin.json"])
    market_entry = json.loads(files[MARKETPLACE_RELPATH])
    targets = {
        "plugin.json description": manifest["description"],
        "marketplace description": market_entry["description"],
        "marketplace plugins[0].description": market_entry["plugins"][0]["description"],
    }
    problems: list[str] = []
    for label, text in targets.items():
        found = re.findall(r"스킬\s*(\d+)\s*종", text)
        if not found:
            continue  # 개수를 말하지 않는 문장은 갈라질 자리가 없다
        for n in found:
            if int(n) != expected:
                problems.append(f"{label}: '스킬 {n}종' != 실제 {expected}종")
    _record(
        "test_descriptions_count_skills",
        not problems,
        "; ".join(problems[:3]) if problems else f"설명 문장이 스킬 {expected}종을 정확히 말한다",
    )


def test_status_targets_working_tree() -> None:
    """13) 정합 판정이 **작업 트리**를 보는가 (모듈이 로드된 위치가 아니라).

    P4 구현 중 실제로 낸 사고의 뿌리다. 목적지를
    ``plugin_payload.default_repo_root()`` (= *모듈이 로드된 위치*) 로 잡았더니,
    릴리스 검사가 sandbox 사본에서 파이프라인을 돌리는데 ``PYTHONPATH`` 는 원본
    소스를 가리키므로 **사본의 작업이 원본 저장소의 manifest 3장을 `v0.7.29-beta`
    로 덮어썼다.** 지금은 쓰기가 없으니 덮일 일은 없지만, 판정이 엉뚱한 트리를 보면
    **사본을 릴리스하면서 원본의 정합을 확인하는** 셈이 된다 — 게이트가 무의미해진다.

    아래는 그 둘이 **갈라진 상황**을 직접 만든다: 파이프라인의 작업 트리만 temp 로
    옮기고 판정을 돌려, 판정 대상이 temp 인지 본다. 모듈 위치에서 오면 FAIL 한다.
    """
    import tempfile

    from workflow_kit.tools import release_pipeline as rp  # noqa: PLC0415

    repo = default_repo_root()
    targets = [repo / rel for rel in VERSION_BEARING_RELPATHS]
    if not all(p.is_file() for p in targets):
        _record("test_status_targets_working_tree", False, "산출물 부재 — 먼저 생성한다")
        return

    before = {p: p.read_bytes() for p in targets}
    problems: list[str] = []
    original_repo_root = rp.REPO_ROOT

    with tempfile.TemporaryDirectory() as tmp:
        work_tree = Path(tmp) / "repo"
        (work_tree / "workflow-source").mkdir(parents=True)
        try:
            # 파이프라인의 작업 트리만 옮긴다 — 모듈은 그대로 원본에서 로드된 상태다.
            rp.REPO_ROOT = work_tree / "workflow-source"
            result = rp.plugin_payload_status("v0.0.0-treetest")
        finally:
            rp.REPO_ROOT = original_repo_root

        if not result.get("ok"):
            problems.append(f"판정 실패: {result.get('error')}")
        elif Path(result.get("repo_root", "")) != work_tree:
            problems.append(
                f"판정 대상이 작업 트리가 아니다: {result.get('repo_root')} != {work_tree}"
            )
        elif result.get("in_sync"):
            problems.append("빈 작업 트리인데 in_sync=True — 엉뚱한 트리를 본다")

    for path, original in before.items():
        if path.read_bytes() != original:
            problems.append(f"원본이 오염됐다: {path.relative_to(repo)}")
            path.write_bytes(original)  # 검사가 저장소를 오염된 채 두지 않는다

    _record(
        "test_status_targets_working_tree",
        not problems,
        "; ".join(problems[:3]) if problems else "판정이 작업 트리를 보고 원본은 무손상",
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
    test_version_resolved_at_call_time()
    test_release_gate_catches_plugin_drift()
    test_descriptions_count_skills()
    test_status_targets_working_tree()
    total = 13
    print(f"\n{total - len(FAILURES)}/{total} passed")
    if FAILURES:
        raise AssertionError(f"{len(FAILURES)} case(s) failed: {FAILURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
