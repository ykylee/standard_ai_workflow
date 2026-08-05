# 세션 기록 — "여기는 스킬이 적용이 안 되어 있네" 한 줄에서 여덟 사이클 (2026-08-05)

- 문서 목적: 이 세션이 무엇을 결정하고, 무엇을 재고, 무엇을 남겼는지 다음 세션이 이어받게 한다.
- 범위: TASK-2026-08-05-main-001 ~ -008 (§2.59 ~ §2.66)
- 대상 독자: AI agent, 저장소 관리자
- 상태: closed
- 최종 수정일: 2026-08-05
- 관련 문서: [state.json](../state.json), [session_handoff.md](../session_handoff.md),
  [backlog/2026-08-05.md](../backlog/2026-08-05.md),
  `workflow-source/core/read_only_mcp_transport_promotion.md` §1.3/§6.1/§6.2,
  `workflow-source/core/mcp_installation_by_harness.md` §1.1/§1.2

## 1. 시작 지점

`c58111d` 기준선. 사용자가 세션을 열며 한 줄을 남겼다 — **"우리가 워크플로우와 스킬
MCP 등을 구성하고 있는데 정작 여기는 스킬이 적용이 안 되어 있네."**

확인해 보니 사실이었고, 파고들수록 층이 늘었다. 이 세션은 **자기 적용(self-application)
의 구멍을 끝까지 따라간 기록**이다.

## 2. 사이클 연쇄 (§2.59 → §2.66)

각 사이클이 다음 사이클을 열었다. 계획이 아니라 **발견의 순서**였다.

| § | 무엇을 고쳤나 | 무엇이 그 다음을 열었나 |
| --- | --- | --- |
| 2.59 | `.claude/` 가 통째로 없었다 — command 3종 + skill 발행 | 자기적용 검사가 왜 green 이었나 → 요구 목록이 손복사본 |
| 2.59 | `stamp_marker` 가 frontmatter 를 밀어내고 있었다 (배포된 8블록) | push 하자 하네스가 로드 → command 설명이 버전 마커로 떴다 |
| 2.60 | Claude Code MCP 렌더러 부재 (§4 표가 선언만) | grok 의 MCP 블록이 사본이라는 것이 보였다 |
| 2.61 | grok 사본 접기 | 접느라 산출물을 파싱하다 TOML dotted-key 결함 발견 |
| 2.62 | 세 번째 사본 — 이미 갈라져 있었다 (`mcp_servers` vs `mcp`) | `transport_ready` 승격 조건이 없다는 것이 남았다 |
| 2.63 | 축 분리 + 승격 기준을 실행되는 검사로 | 새 검사가 mcp 2.0.0 에서 red |
| 2.64 | SDK 매트릭스를 로컬로 (`--run-local`) | "작성 시점에 막는 층" 이 없다 |
| 2.65 | 버전 고정 필드 속성 접근 금지 (A안) | §6.2 의 wire 제거가 남았다 |
| 2.66 | `transport_ready` wire 제거 (51곳) | — |

## 3. 결정

**자기적용 검사의 요구 목록은 정본에서 파생시킨다.** `REQUIRED_ENTRYPOINTS` 가
`HarnessSpec.entry_files` 의 손복사본이라 `extra_files` 를 아예 안 봤고, 그래서
`.claude/` 가 통째로 없는데도 green 이었다. 이제 `HARNESS_SPECS` 에서 파생한다.

**승격 기준은 문서가 아니라 실행이다.** `transport_ready` 는 능력·단계·정책 셋을 한
boolean 에 섞고 있어 "무엇이 참이면 true 인가" 를 적을 수 없었다 — registry 의 상수
`False` 는 참·거짓을 가릴 명제조차 아니었다. 축을 셋으로 쪼개니 기준이 필요한 것은
정책 축 하나였고, `check_mcp_apply_mode_criterion.py` 가 그것을 **실행해서** 요구한다.

**함정은 앎이 아니라 재현 수단이 막는다.** `CallToolResult.isError` 함정은 이미
주석과 검사에 적혀 있었는데 새 파일에서 또 밟았다. 개발 venv 가 하한 하나뿐이라
로컬에서 재현할 방법이 없었기 때문이다. 이제 3층이다 — 작성 시점(A) / 로컬 매트릭스(B)
/ CI 매트릭스.

## 4. 실측으로 뒤집힌 판단 (기록해 둘 것)

- **"Claude Code 는 정식 MCP 니까 `stdio-sdk`"** → 정반대였다. emit 되는 `command` 는
  시스템 `python3` 이고 거기엔 `mcp` SDK 가 없어 `Connection closed` 로 죽는다.
  이름이 초라한 `jsonrpc-bridge` 가 공식 클라이언트 왕복 정상. **갈리는 건 프로토콜이
  아니라 의존성이었다.**
- **"우리 mcp 를 2.0.0 에 맞게 다 고쳐야겠다"** → 고칠 production 이 **0건**. 생성 시
  camelCase kwarg 는 alias 로 받고, `protocolVersion`/`listChanged` 문자열은 프로토콜
  wire 필드명이다. 깨진 건 새 테스트 하나였다.
- **"표가 렌더러 산출물과 같은가" 검사** → 렌더러도 같은 표를 읽어 **동어반복**.
  결함 되주입에도 6/6 PASS 였다. 외부 증인(`examples/mcp_config_examples/`)이 필요했다.
- **버전 고정 필드 전역 금지** → 30건 중 **28건 위양성**(`task_id`, `created_at`).
  범위를 "실제 mcp 를 import 하는 파일" 로 좁혀야 했다.

## 5. 남긴 것

**다음 세션 첫 확인**: `.mcp.json` 을 이 세션은 로드하지 못했다(세션 시작 시점에 없었다).
**MCP 도구 13종이 실제로 붙는지** 확인할 것. skill 때는 같은 확인이 결함을 하나 더 냈다
(command 설명이 버전 마커로 뜬 건) — 그냥 넘기지 말 것.

**후속 후보** (급하지 않은 순):
1. `check_mcp_apply_mode_criterion` 을 mcp-sdk-matrix 의 `--assert-exercised` 대상에
   넣을지 — 파일명 때문에 `--filter mcp` 에는 이미 걸린다.
2. `claude-code` 용 독립 설정 예시를 `examples/mcp_config_examples/` 에 추가하면 방언
   대조가 4종 → 5종이 된다(지금은 `[info] 대조 못 함` 으로 매번 노출된다).
3. A안의 사각지대 — mcp 를 import 하지 않는 파일이 남에게서 받은 SDK 객체를 읽는 경우.
   범위를 넓히면 위양성이 압도하므로 지금은 열어 둔다.

**소비자 영향(§2.66 breaking)**: `_meta.transport_ready` 를 읽던 코드는 §6.2 표대로
옮긴다 — 단계는 `transport_phase`, 정책은 `apply_mode`, 런타임 능력은
`sdk_runtime_status()["sdk_available"]`.

## 6. 검증 (이 세션 마지막 상태)

- `origin/main` = `76db79c`, 커밋 15건
- 격리 venv 전량 smoke **234/234** (220 test cases)
- mypy strict **123 files 0 errors**
- 로컬 SDK 매트릭스 **3버전(1.27.0 / 1.29.0 / 2.0.0) 전부 PASS**
- 자기적용 **8/8**, `check_standard_single_source` 7/7
- CI: 마지막 커밋에서 트리거된 **5종 green**(smoke 2셀 · mypy-strict · mcp-sdk-matrix ·
  mcp-inspector · mkdocs). wire 를 건드려 inspector 가, 문서를 건드려 mkdocs 가 함께 돌았다
- 실제 서버 기동 확인: `tools/list meta = {descriptor_target, tool_count: 13,
  transport_phase: "jsonrpc_draft"}`, `transport_ready` 없음
