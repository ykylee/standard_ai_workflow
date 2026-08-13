# 27차 세션 기록 — 플러그인 전환 P3: 멀티 하네스 어댑터 (2026-08-13)

- 문서 목적: 27차 세션의 작업 내용·산출물·다음 시작 포인트 기록
- 범위: TASK-2026-08-12-main-016 (P3 — gemini-cli/goose/opencode 어댑터 + 수렴 판정)
- 상태: done
- 최종 수정일: 2026-08-13
- 관련 문서: [전환 계획 §3-P3](../../../../docs/planning/plugin-transition-plan-2026-08.md), [26차까지의 P2·P4 기록](./plugin_claude_code_adapter_2026-08-12.md)

## 1. 지시

사용자: "작업 내역 확인하고 플러그인 전환 작업 계속 진행해보자" — 기준선의 다음
작업 지정(TASK-016, P3)을 그대로 실행.

## 2. 이 세션의 핵심: 실측이 계획을 두 번, bootstrap 을 한 번 고쳤다

P2 와 같은 방법론 — CLI 가 있으면 추측하지 않는다. gemini 0.42.0 / opencode
1.17.12 / claude 2.1.229 로 실측했다 (goose 는 부재 — §5).

### (1) Gemini 도 확장 루트 = payload 루트

`gemini extensions new` 보일러플레이트로 스키마를 확인하고 validate → link →
`extensions list` 인벤토리까지 갔다. **확장 루트의 `skills/` 관례 경로를 무변환으로
읽어 payload 스킬 4종이 그대로 잡혔다** — Claude Code 와 같은 결론(루트 병합),
다른 이유(path traversal 거부가 아니라 관례 경로 공유). 어댑터는
`plugin/gemini-extension.json` (5필드, mcpServers 인라인) + `plugin/GEMINI.md`
(상시 주입 컨텍스트, `render_entrypoint_rules` 파생 — bootstrap 진입점과 **같은
파생 함수**) 두 장. 자기 적용: 이 저장소 `plugin/` 을 `extensions link` 로 등록,
Context file + MCP + 스킬 4종 로드 확인.

**모델 주입 계층은 실측 불가로 남았다**: headless 호출이 `IneligibleTierError`
(free tier 의 gemini-cli 지원 종료, Antigravity 이전 안내) 로 차단. 로드 계층
성립만 기록하고 **P5 게이트 ② 는 연 채로 둔다** — 실행 못 한 검사는 통과가 아니다.

### (2) OpenCode 실측이 bootstrap 방언을 반증했다

snippet 을 bootstrap `render_opencode_mcp_config` 형태(문자열 `command`+`args`,
`env`)로 만들자 opencode 1.17.12 가 거부: *"Expected array"* / *"Missing key
enabled"*. 실측 확정 형태(`command` 배열 전체 + `enabled` + `environment`)로
`opencode mcp list` 가 **connected** 까지 보고 — validate 급이 아니라 로드 실측이다.
**bootstrap 의 그 emit 을 따라한 사용자는 지금 서버를 못 본다** → 별건
[TASK-2026-08-13-main-002].

### (3) `.agents/skills/` 수렴 판정: 수렴하지 않는다

Claude Code 2.1.229 에 `.agents/skills/` + `.claude/skills/` 프로브 스킬을 나란히
심고 headless 로 물었다 — **`.claude/skills/` 쪽만 보인다.** 바이너리 문자열 교차
확인 동방향 (`.claude/skills` 73건 / `.agents/skills` 0건). bootstrap 스킬 emit 을
`.agents/skills/` 하나로 수렴하면 Claude Code 채널이 빠지므로 수렴 기각.
Codex·OpenCode·goose 용 **추가** emit 위치 도입은 bootstrap 쪽 별건 가치로만 남긴다.

### (4) `<plugin>/bin` 판정 (P2 잔여): 싣지 않는다

shim 이 해소하는 폭은 "PATH 에 없지만 import 는 되는" 좁은 틈뿐이고 Python 의존은
그대로다 (원칙 4 유지). 잘못 실리면 설치본을 가리는 그림자 경로 + 타 플랫폼 검증
수단 부재. SessionStart hook 의 graceful 안내가 이미 그 틈을 드러낸다. 마찰 실측이
쌓이면 명시 task 로 재론.

## 3. 산출물

- `workflow_kit/plugin_payload.py`: `render_gemini_manifest` / `render_gemini_context` /
  `render_goose_config_snippet` / `render_opencode_snippet` + `_payload_mcp_entry()`
  (어댑터 전부가 한 파생점에서 command 를 꺼낸다). payload 14 → **18 산출물**.
- `check_agent_plugin_payload` 13 → **15 case** (14 Gemini 로드 형태 / 15 방언
  파생 + goose 미검증 표기 강제). 되주입 3종 FAIL 실증 (contextFileName 오염 /
  방언 키 오염 / GEMINI.md 규칙 블록 제거). gemini-extension.json 이 **버전 넷째
  장**으로 릴리스 게이트(case 10·11, release-doctor) 에 합류.
- `check_docs`: payload 디렉터리 제외 (`PAYLOAD_DIRNAME` 상수 파생 — 이름 복제
  없음). 근거: payload .md 는 소비 하네스에 주입되는 생성물이라 산문 문서 계약을
  씌우면 소비자 컨텍스트에 메타데이터가 같이 주입된다 (snapshot.md 동계열).
- Claude Code 채널 무영향 실측: 새 파일 4장 후에도 validate --strict 통과 +
  인벤토리 Skills 4 / Hooks 2 / MCP 1 동일.
- 계획 문서 §3-P3 실행 결과 7항 + WBS 016 ✅.

## 4. 사고 1건 (이 세션)

되주입 실증 중 `git checkout -- <renderer>` 로 복원하다 **미커밋 P3 수정까지
되돌렸다** (되주입 대상 파일 = 작업 중 파일). 재적용으로 복구했고, 이후 되주입은
scratchpad 백업 사본 + `cp` 복원으로 바꿨다. 교훈: 작업 트리에서의 되주입 실증은
git 이 아니라 **사본 백업**으로 복원한다 — git 복원은 "HEAD 이후 전부" 를 지운다.

## 5. 남은 것

- goose: CLI 부재로 실기 검증 미완 — snippet 주석 + case 15 가 미완 표기를 강제.
  goose 가용 환경(예: MacBook 합류 시)에서 검증.
- Gemini 모델 주입 실효 + SessionStart hook 실효 + marketplace 자동 업데이트 = P5
  (TASK-018) 실측 3건.
- 별건: [TASK-2026-08-13-main-001] (원본 bump 검사 sandbox 이관),
  [TASK-2026-08-13-main-002] (bootstrap OpenCode 방언 갱신),
  [TASK-2026-08-12-main-019] (macOS PEP 668).

전량 2축 **252/252 ×2 green** (venv 인터프리터 — system python 으로 돌리면 dev
의존 부재로 mypy/build/mcp 계열이 위양성 FAIL 난다).
