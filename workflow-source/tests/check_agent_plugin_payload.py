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

## 판정 규칙 (19 case)

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
14. **Gemini 어댑터가 로드되는 형태다** — `gemini extensions list` 실측(0.42.0)이
    못박은 계약 (manifest 5필드 고정, 컨텍스트 = 진입점 규칙 파생, MCP 파생).
15. **goose/OpenCode snippet 이 방언 상수 파생이다** — 최상위 키·command 를 손으로
    적으면 그 사본만 낡는다. goose 는 실기 검증 미완 표기를 강제한다.
16. **Codex UI metadata가 각 skill에 있다** — `agents/openai.yaml`은 표시 이름,
    기본 prompt, 암시적 호출 정책을 모두 선언한다.
17. **Codex plugin manifest가 있다** — Codex marketplace가 읽는
    `.codex-plugin/plugin.json`이 skills 및 read-only MCP를 선언한다.
18. **Codex manifest 의 배포 신원이 packaging metadata 파생이다** — 저자 이메일과
    라이선스를 손으로 적으면 그 사본이 갈라진다 (실제로 `yklee@` 로 갈라졌다).
19. **pi.dev (pi-coding-agent) 어댑터가 로드되는 형태다** — pi 는 marketplace.json
    대신 npm/git 패키지 + ``pi`` manifest + ``pi-package`` keyword 로 갤러리에
    등록한다. ``pi.skills`` 경로가 실제 skill 집합과 일치하고, 각 SKILL.md
    description 은 [KO]+[EN] 이중 언어 (pi 시스템 프롬프트가 영어라 영문 매칭
    보장 필요)이며, MCP snippet 이 동봉되고 read-only alias 만 등록된다.

**한계**: Agent Plugins 1.0 (Claude Code 쪽) 의 선택 필드 전체 스펙은 아직 원문
확인이 안 됐다 (2026-08-06 출범). 이 검사는 계획 §3-P1 이 명시한 3필드
(name/version/description)를 **고정**한다 — 스펙 확인 후 필드를 늘릴 때 이 검사가
먼저 FAIL 하므로, 갱신이 명시 task 를 거치게 된다 (계획 §5 리스크 완화
"스키마를 fixture 로 고정").

Codex 쪽(`.codex-plugin/plugin.json`)은 사정이 다르다 — 원문을 확인했다.
Codex CLI 가 번들하는 `plugin-creator` 스킬의
`references/plugin-json-spec.md` 가 field guide 이고, 같은 번들의
`scripts/validate_plugin.py` 가 외부 검증기다 (codex-cli 0.143.0). 실기 로드도
실측했다 — `render_codex_manifest` docstring 참조. 이 검사는 CI 에 codex 가 없어도
돌아야 하므로 codex 를 부르지 않는다: **구조와 파생만** 본다 (case 16·17·18).
codex 를 쓴 실측은 재현 절차를 docstring 에 남기는 방식으로 고정한다.

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
from workflow_kit.common.standard_rules import find_memory_command, load_standard_rules  # noqa: E402
from workflow_kit.plugin_payload import (  # noqa: E402
    CLAUDE_CODE_HOOKS_RELPATH,
    CLAUDE_CODE_MANIFEST_RELPATH,
    CLAUDE_CODE_MCP_RELPATH,
    CODEX_MANIFEST_RELPATH,
    GEMINI_CONTEXT_RELPATH,
    GEMINI_MANIFEST_RELPATH,
    GOOSE_SNIPPET_RELPATH,
    MARKETPLACE_RELPATH,
    OPENCODE_SNIPPET_RELPATH,
    PAYLOAD_DIRNAME,
    PAYLOAD_MCP_BRIDGE,
    PAYLOAD_MCP_BUNDLE,
    PLUGIN_AUTHOR,
    PLUGIN_NAME,
    PLUGIN_SKILLS,
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


def test_codex_skill_metadata() -> None:
    """Codex skill 목록/칩을 위한 agents/openai.yaml이 모든 skill에 있는가."""
    yaml = _yaml()
    if yaml is None:
        # 같은 파일의 case 2 와 같은 판정이다 — PyYAML 은 dev extra 에 선언돼 있고,
        # 없으면 "검사를 못 돌린 것"이지 "통과"가 아니다. 처음 이 case 는 여기서
        # `continue` 로 조용히 넘어가 PyYAML 부재 환경에서 fail-open 이었다.
        _record("test_codex_skill_metadata", False, "PyYAML 부재 — dev extra 에 선언돼 있어야 한다")
        return
    payload = render_agent_plugin()
    problems: list[str] = []
    for spec in PLUGIN_SKILLS:
        relpath = f"skills/{spec.slug}/agents/openai.yaml"
        content = payload.get(relpath)
        if content is None:
            problems.append(f"{relpath} 누락")
            continue
        metadata = yaml.safe_load(content)
        interface = metadata.get("interface", {}) if isinstance(metadata, dict) else {}
        if not all(interface.get(key) for key in ("display_name", "short_description", "default_prompt")):
            problems.append(f"{relpath} interface 필드 누락")
        elif f"${spec.slug}" not in str(interface["default_prompt"]):
            problems.append(f"{relpath} default_prompt에 ${spec.slug} 호출이 없다")
        if metadata.get("policy", {}).get("allow_implicit_invocation") is not True:
            problems.append(f"{relpath} allow_implicit_invocation=true 누락")
    _record(
        "test_codex_skill_metadata",
        not problems,
        "; ".join(problems[:4]) if problems else f"Codex metadata {len(PLUGIN_SKILLS)}개 skill 일치",
    )


def test_codex_plugin_manifest() -> None:
    """Codex marketplace/install surface의 manifest를 검증한다."""
    payload = render_agent_plugin()
    manifest = json.loads(payload[CODEX_MANIFEST_RELPATH])
    problems: list[str] = []
    if manifest.get("name") != PLUGIN_NAME:
        problems.append("Codex manifest name 불일치")
    if manifest.get("version") != KIT_VERSION:
        problems.append("Codex manifest version 불일치")
    if manifest.get("skills") != "./skills/":
        problems.append("Codex manifest skills 경로 불일치")
    if manifest.get("mcpServers") != f"./{CLAUDE_CODE_MCP_RELPATH}":
        problems.append("Codex manifest read-only MCP 경로 불일치")
    interface = manifest.get("interface", {})
    if not all(interface.get(key) for key in ("displayName", "shortDescription", "longDescription", "developerName", "category")):
        problems.append("Codex manifest interface 필수 필드 누락")
    _record(
        "test_codex_plugin_manifest",
        not problems,
        "; ".join(problems) if problems else "Codex manifest + skills + read-only MCP 선언",
    )


def test_codex_manifest_identity_derived() -> None:
    """18) Codex manifest 의 배포 신원이 packaging metadata 파생인가.

    첫 Codex manifest 는 저자 이메일을 손으로 적었고 `yklee@…` — 정본
    (`pyproject [project].authors[0].email`) 의 `ykylee@…` 에서 `y` 하나가
    빠진 채 배포 payload 까지 갔다. 사본이 갈라진 것을 아무도 보지 못했다.
    이 case 는 **pyproject 를 직접 읽어** 대조한다 — 렌더러가 쓰는 helper 로
    대조하면 helper 가 틀렸을 때 같이 틀린다 (자기 자신과의 비교).
    """
    if sys.version_info >= (3, 11):
        import tomllib  # noqa: PLC0415
    else:  # pragma: no cover
        import tomli as tomllib  # noqa: PLC0415
    with (SOURCE_ROOT / "pyproject.toml").open("rb") as f:
        project = tomllib.load(f)["project"]
    manifest = json.loads(render_agent_plugin()[CODEX_MANIFEST_RELPATH])
    problems: list[str] = []
    if manifest["author"].get("email") != project["authors"][0]["email"]:
        problems.append(
            f"author.email {manifest['author'].get('email')!r} != pyproject {project['authors'][0]['email']!r}"
        )
    if manifest.get("license") != project["license"]:
        problems.append(f"license {manifest.get('license')!r} != pyproject {project['license']!r}")
    if manifest["author"].get("url") != f"https://github.com/{PLUGIN_AUTHOR['name']}":
        problems.append(f"author.url 이 PLUGIN_AUTHOR 파생이 아니다: {manifest['author'].get('url')!r}")
    _record(
        "test_codex_manifest_identity_derived",
        not problems,
        "; ".join(problems) if problems else "author.email / license / author.url 이 정본 파생",
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
    # 표의 **마지막 행**을 재생성 명령으로 가정하던 자리 (2026-08-14 실측: §11.1 에
    # 행을 하나 추가하자 깨졌다). 위치가 아니라 **목적**으로 찾는다 — 렌더러가
    # 쓰는 것과 같은 정본 helper 다.
    refresh_cmd = find_memory_command(rules, "Regenerate state.json")
    binary = refresh_cmd.split()[0]

    def _commands(event: str) -> list[str]:
        return [
            entry.get("command", "")
            for matcher in hooks.get(event, [])
            for entry in matcher.get("hooks", [])
        ]

    # `wk` 를 부르거나 그 부재를 알리는 hook 은 부재 검사를 가진다 (원칙 4).
    end_cmds = [cmd for cmd in _commands("SessionEnd") if refresh_cmd in cmd]
    if not end_cmds:
        problems.append(f"SessionEnd 가 §11.1 재생성 명령({refresh_cmd})을 부르지 않는다")
    notice_cmds = [cmd for cmd in _commands("SessionStart") if "not found" in cmd]
    if not notice_cmds:
        problems.append("SessionStart 에 `wk` 부재 안내 hook 이 없다")
    if not all(f"command -v {binary}" in cmd for cmd in end_cmds + notice_cmds):
        problems.append(
            f"`{binary}` 를 다루는 hook 에 부재 검사가 없다 — 조용한 실패 금지 (계획 원칙 4)"
        )

    # 조건부 규칙 주입 (TASK-2026-08-13-main-003) — P5 실측(hook stdout 주입 성립)의
    # 실채널. 진입점 마커가 있으면 생략해야 한다 (이중 주입 방지).
    from workflow_kit.common.standard_rules import GENERATED_MARKER, render_entrypoint_rules
    from workflow_kit.plugin_payload import CLAUDE_CODE_RULES_RELPATH

    probe = GENERATED_MARKER.split("—")[0].removeprefix("<!--").strip()
    inject_cmds = [cmd for cmd in _commands("SessionStart") if "CLAUDE_PLUGIN_ROOT" in cmd]
    if len(inject_cmds) != 1:
        problems.append(f"규칙 주입 hook 이 {len(inject_cmds)}개 — SessionStart 에 정확히 1개여야 한다")
    else:
        inject = inject_cmds[0]
        if probe not in inject:
            problems.append("주입 hook 이 생성 마커 탐침을 쓰지 않는다 — 항상 이중 주입이 된다")
        if CLAUDE_CODE_RULES_RELPATH not in inject:
            problems.append(f"주입 hook 이 {CLAUDE_CODE_RULES_RELPATH} 를 cat 하지 않는다")
        if "CLAUDE.md" not in inject or ".claude/CLAUDE.md" not in inject:
            problems.append("주입 hook 이 Claude Code 자동 read 진입점 2종을 확인하지 않는다")
    rules_doc = payload.get(CLAUDE_CODE_RULES_RELPATH, "")
    if render_entrypoint_rules(rules) not in rules_doc:
        problems.append(f"{CLAUDE_CODE_RULES_RELPATH} 가 진입점 규칙 블록 파생이 아니다")

    _record(
        "test_claude_code_adapter",
        not problems,
        "; ".join(problems[:4])
        if problems
        else "manifest 계약 + hooks(세션 경계 + 조건부 규칙 주입) + .mcp.json == mcp.json",
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


#: 버전 문자열을 **복사해 담는** 산출물. bump 를 따라가야 하는 것이 정확히 이 4장이다
#: (P3 에서 gemini-extension.json 이 넷째로 합류했다).
VERSION_BEARING_RELPATHS = (
    f"{PAYLOAD_DIRNAME}/plugin.json",
    f"{PAYLOAD_DIRNAME}/{CODEX_MANIFEST_RELPATH}",
    f"{PAYLOAD_DIRNAME}/{CLAUDE_CODE_MANIFEST_RELPATH}",
    f"{PAYLOAD_DIRNAME}/{GEMINI_MANIFEST_RELPATH}",
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
    gemini = json.loads(files[f"{PAYLOAD_DIRNAME}/{GEMINI_MANIFEST_RELPATH}"])
    targets = {
        "plugin.json description": manifest["description"],
        "marketplace description": market_entry["description"],
        "marketplace plugins[0].description": market_entry["plugins"][0]["description"],
        "gemini-extension.json description": gemini["description"],
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


def test_gemini_adapter() -> None:
    """14) Gemini 어댑터가 **로드되는 형태**인가 (gemini 0.42.0 실측으로 고정한 계약).

    `gemini extensions link` 후 `extensions list` 인벤토리 실측이 못박은 것:
    확장 루트 = payload 루트일 때 Context files(GEMINI.md) + MCP servers +
    Agent skills 4종이 전부 잡힌다. 이 case 는 그 형태를 고정한다:

    - manifest 필드 5개 고정 (validate 로 확인 안 된 필드를 지어 넣으면 FAIL)
    - `contextFileName` 이 가리키는 파일이 payload 에 실재하고, 내용이
      진입점 규칙 블록(`render_entrypoint_rules`) **그 자체**를 담는다 —
      채널이 둘이어도 규칙 정본은 하나다.
    - mcpServers 는 read-only bundle 하나, command 는 `mcp_server_command` 파생,
      `PYTHONPATH` 금지 (체크아웃 전제 금지 — 계획 원칙 4).
    """
    from workflow_kit.bootstrap_lib.mcp import (
        MCP_SERVER_ALIAS,
        MCP_WRITE_SERVER_ALIAS,
        mcp_server_command,
    )
    from workflow_kit.common.standard_rules import render_entrypoint_rules

    rules = load_standard_rules(SOURCE_ROOT)
    payload = render_agent_plugin(rules)
    problems: list[str] = []

    manifest = json.loads(payload[GEMINI_MANIFEST_RELPATH])
    expected_fields = {"name", "version", "description", "contextFileName", "mcpServers"}
    if set(manifest) != expected_fields:
        problems.append(
            f"필드 집합 {sorted(manifest)} != 실측 계약 {sorted(expected_fields)}"
        )
    if manifest.get("name") != PLUGIN_NAME or manifest.get("version") != KIT_VERSION:
        problems.append(f"name/version 불일치: {manifest.get('name')} {manifest.get('version')}")
    if manifest.get("contextFileName") != GEMINI_CONTEXT_RELPATH:
        problems.append(f"contextFileName {manifest.get('contextFileName')!r} != {GEMINI_CONTEXT_RELPATH!r}")

    context = payload.get(GEMINI_CONTEXT_RELPATH, "")
    if render_entrypoint_rules(rules) not in context:
        problems.append(
            f"{GEMINI_CONTEXT_RELPATH} 가 진입점 규칙 블록을 담지 않는다 — "
            "상시 주입 채널이 정본과 갈라졌다"
        )

    servers = manifest.get("mcpServers", {})
    if set(servers) != {MCP_SERVER_ALIAS}:
        problems.append(f"mcpServers alias {sorted(servers)} != {{{MCP_SERVER_ALIAS}}}")
    if MCP_WRITE_SERVER_ALIAS in servers:
        problems.append(f"write bundle({MCP_WRITE_SERVER_ALIAS}) 이 실렸다 — opt-in 이다 (ADR-003)")
    entry = servers.get(MCP_SERVER_ALIAS, {})
    expected_cmd = mcp_server_command(PAYLOAD_MCP_BRIDGE, PAYLOAD_MCP_BUNDLE)
    if [entry.get("command"), *entry.get("args", [])] != expected_cmd:
        problems.append(f"command/args 가 mcp_server_command 파생이 아니다: {entry.get('args')}")
    if "PYTHONPATH" in entry.get("env", {}):
        problems.append("env 에 PYTHONPATH — 플러그인은 체크아웃 구조를 모른다 (원칙 4)")

    _record(
        "test_gemini_adapter",
        not problems,
        "; ".join(problems[:4])
        if problems
        else "manifest 5필드 + 컨텍스트 = 진입점 규칙 파생 + MCP 파생",
    )


def test_goose_opencode_snippets() -> None:
    """15) goose / OpenCode snippet 이 방언 상수·registry 파생인가.

    두 하네스는 스킬을 `.agents/skills/` 에서 직접 읽으므로 어댑터가 나를 것은
    MCP 등록뿐이다. snippet 이 각자 command 를 조립하면 entry-point 개명 시 일부
    사본만 낡는다 — OpenCode 최상위 키는 `MCP_CONFIG_ROOT_KEY` 파생이어야 한다
    (예시 스크립트가 `mcp_servers` 를 잘못 가르치던 실측 사고의 재발 방지).

    goose snippet 은 실기 검증 미완이다 (goose CLI 부재 환경) — 그 사실이 snippet
    주석에 남아 있는지도 본다. 검증 안 된 산출물이 검증된 얼굴을 하면 안 된다.
    """
    from workflow_kit.bootstrap_lib.mcp import (
        MCP_CONFIG_ROOT_KEY,
        MCP_SERVER_ALIAS,
        mcp_server_command,
    )

    payload = render_agent_plugin()
    expected_cmd = mcp_server_command(PAYLOAD_MCP_BRIDGE, PAYLOAD_MCP_BUNDLE)
    problems: list[str] = []

    opencode = json.loads(payload[OPENCODE_SNIPPET_RELPATH])
    root_key = MCP_CONFIG_ROOT_KEY["opencode"]
    if set(opencode) != {root_key}:
        problems.append(f"opencode 최상위 키 {sorted(opencode)} != {{{root_key!r}}} (방언 상수 파생)")
    oc_entry = opencode.get(root_key, {}).get(MCP_SERVER_ALIAS, {})
    if not oc_entry:
        problems.append(f"opencode snippet 에 {MCP_SERVER_ALIAS} 항목이 없다")
    else:
        # opencode 1.17.12 실측 계약: command 는 배열 전체, enabled 필수,
        # env 키는 `environment`. (문자열 command + args 분리형은 거부된다.)
        if oc_entry.get("command") != expected_cmd:
            problems.append(f"opencode command 가 배열 파생이 아니다: {oc_entry.get('command')}")
        if oc_entry.get("enabled") is not True:
            problems.append("opencode enabled 누락 — 1.17.12 가 Missing key 로 거부한다")
        if "env" in oc_entry:
            problems.append("opencode 는 env 가 아니라 environment 를 쓴다 (실측)")
        if "PYTHONPATH" in oc_entry.get("environment", {}):
            problems.append("opencode environment 에 PYTHONPATH — 체크아웃 전제 금지 (원칙 4)")

    goose_text = payload[GOOSE_SNIPPET_RELPATH]
    yaml = _yaml()
    if yaml is None:
        problems.append("PyYAML 부재 — goose snippet 을 파싱하지 못한다")
    else:
        goose = yaml.safe_load(goose_text)
        entry = (goose or {}).get("extensions", {}).get(MCP_SERVER_ALIAS, {})
        if not entry:
            problems.append(f"goose snippet 에 extensions.{MCP_SERVER_ALIAS} 가 없다")
        elif [entry.get("cmd"), *entry.get("args", [])] != expected_cmd:
            problems.append(f"goose cmd/args 가 파생이 아니다: {entry.get('args')}")
        if "PYTHONPATH" in (entry.get("envs") or {}):
            problems.append("goose envs 에 PYTHONPATH — 체크아웃 전제 금지 (원칙 4)")
    if "not yet verified on real hardware" not in goose_text:
        problems.append("goose snippet 에 실기 검증 미완 표기가 없다 — 미검증을 침묵시키지 않는다")

    _record(
        "test_goose_opencode_snippets",
        not problems,
        "; ".join(problems[:4])
        if problems
        else "snippet 2장 전부 방언 상수·command 파생 + 미검증 표기",
    )


def test_pi_dev_adapter() -> None:
    """19) pi.dev (pi-coding-agent) 마켓플레이스 어댑터가 로드되는 형태인가 (v1.2.0+).

    pi 는 marketplace.json 이 없다 — npm/git 패키지 + ``pi`` manifest + ``pi-package``
    keyword 로 pi.dev 갤러리에 등록한다 (https://pi.dev/packages). ``pi install <pkg>``
    가 ``package.json`` 의 ``pi.skills`` 경로를 읽어 ``skills/`` 를 discover 한다.
    각 skill 디렉터리는 ``SKILL.md`` (frontmatter ``name``+``description``) 형식이다
    — Agent Skills 표준 그대로 받아들이므로 기존 SKILL.md 가 그대로 호환된다.

    pi 의 시스템 프롬프트는 영어라 skill description 이 한국어 only 면 매칭이 약해진다.
    그래서 [KO]+[EN] 이중 언어 표기로 정렬한다 (PLUGIN_SKILLS 와 동일).

    MCP 등록은 settings.json 의 ``mcpServers`` 섹션이 표준 경로다 — 패키지 안의
    snippet 으로 동봉한다.

    판정 항목:
    - ``plugin/package.json`` 존재 + ``pi-package`` keyword
    - ``pi.skills`` 경로가 payload 디렉터리의 실제 skill 디렉터리 집합과 일치
    - 각 SKILL.md description 이 [KO] + [EN] 두 표기를 모두 담는다 (영문 매칭 보장)
    - ``plugin/.pi-pkg/mcp-settings-snippet.json`` 가 존재하고 ``mcpServers`` 키를
      가지며 read-only alias 만 등록한다 (write 는 opt-in)
    """
    from workflow_kit.bootstrap_lib.mcp import MCP_SERVER_ALIAS, MCP_WRITE_SERVER_ALIAS

    problems: list[str] = []

    # 1) plugin/package.json 존재 + pi-package keyword + pi.skills 경로
    pkg_path = PAYLOAD_ROOT / "package.json"
    if not pkg_path.exists():
        problems.append(f"{pkg_path} 부재 — pi.dev 등록 불가")
    else:
        try:
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"package.json JSON 파싱 실패: {exc}")
            pkg = {}
        keywords = pkg.get("keywords") or []
        if "pi-package" not in keywords:
            problems.append(f"keywords 에 'pi-package' 부재 (갤러리 비공개) — 현재: {keywords}")
        pi_manifest = pkg.get("pi") or {}
        skills_paths = pi_manifest.get("skills") or []
        if not skills_paths:
            problems.append("pi.skills 경로가 비어있다 — pi 가 스킬을 못 발견한다")
        else:
            # skills 경로 해석 (payload 루트 기준 상대)
            declared_skills: set[str] = set()
            for sp in skills_paths:
                skill_root = (PAYLOAD_ROOT / sp).resolve()
                if not skill_root.exists():
                    problems.append(f"pi.skills 경로가 실제 디스크에 없다: {sp}")
                    continue
                declared_skills |= {p.parent.name for p in skill_root.glob("*/SKILL.md")}
            actual_skills = {spec.slug for spec in PLUGIN_SKILLS}
            if declared_skills != actual_skills:
                problems.append(
                    f"pi.skills 가 실제 skill 과 불일치: declared={sorted(declared_skills)} "
                    f"actual={sorted(actual_skills)}"
                )

    # 2) 각 SKILL.md description 이 [KO] + [EN] 두 표기를 모두 담는다
    for spec in PLUGIN_SKILLS:
        skill_md = PAYLOAD_ROOT / "skills" / spec.slug / "SKILL.md"
        if not skill_md.exists():
            problems.append(f"{skill_md} 부재")
            continue
        try:
            text = skill_md.read_text(encoding="utf-8")
        except OSError as exc:
            problems.append(f"{skill_md} read 실패: {exc}")
            continue
        yaml = _yaml()
        if yaml is None:
            problems.append("PyYAML 부재 — frontmatter 검증 스킵")
            break
        try:
            fm = yaml.safe_load(text.split("---", 2)[1])
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{skill_md} frontmatter 파싱 실패: {exc}")
            continue
        desc = (fm or {}).get("description") or ""
        if "[KO]" not in desc or "[EN]" not in desc:
            problems.append(
                f"{spec.slug} description 에 [KO]/[EN] 표기 누락 — pi 매칭 약화"
            )
        if len(desc) > 1024:
            problems.append(
                f"{spec.slug} description 길이 {len(desc)} > 1024 (pi Agent Skills spec)"
            )

    # 3) pi 용 MCP snippet 동봉 + read-only alias 만 등록
    pi_mcp = PAYLOAD_ROOT / ".pi-pkg" / "mcp-settings-snippet.json"
    if not pi_mcp.exists():
        problems.append(f"{pi_mcp} 부재 — pi 사용자가 MCP 등록 스니펫을 못 받는다")
    else:
        try:
            snippet = json.loads(pi_mcp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"pi MCP snippet JSON 파싱 실패: {exc}")
            snippet = {}
        servers = ((snippet or {}).get("mcpServers") or {})
        if not servers:
            problems.append("pi MCP snippet 에 mcpServers 가 없다")
        if set(servers) != {MCP_SERVER_ALIAS}:
            problems.append(
                f"pi MCP servers {sorted(servers)} != read-only alias {{{MCP_SERVER_ALIAS}}} 만 — "
                f"write({MCP_WRITE_SERVER_ALIAS}) 는 opt-in (ADR-003)"
            )

    _record(
        "test_pi_dev_adapter",
        not problems,
        "; ".join(problems[:4])
        if problems
        else "package.json (pi-package+pi.skills) + SKILL.md [KO]/[EN] + pi MCP snippet",
    )


def main() -> int:
    test_payload_matches_generator()
    test_skill_frontmatter_valid()
    test_codex_skill_metadata()
    test_codex_plugin_manifest()
    test_codex_manifest_identity_derived()
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
    test_gemini_adapter()
    test_goose_opencode_snippets()
    test_pi_dev_adapter()
    total = 19
    print(f"\n{total - len(FAILURES)}/{total} passed")
    if FAILURES:
        raise AssertionError(f"{len(FAILURES)} case(s) failed: {FAILURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
