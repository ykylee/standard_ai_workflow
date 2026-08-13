# 31차 세션 기록 — 플러그인 hook 조건부 규칙 주입 (2026-08-13)

- 문서 목적: 31차 세션의 작업 내용·산출물·다음 시작 포인트 기록
- 범위: TASK-2026-08-13-main-003 (SessionStart 조건부 규칙 주입)
- 상태: done
- 최종 수정일: 2026-08-13
- 관련 문서: [30차 세션 기록](./opencode_dialect_update_2026-08-13.md), 계획 §3-P5

## 1. 지시

사용자: "다음 작업 진행하자" — 별건 대기 중 TASK-003 실행 (P5 가 열어 둔 hook
규칙 주입의 실채널화).

## 2. 설계 — 조건부가 핵심이다

P5 실측이 "hook stdout 은 모델 컨텍스트에 주입된다" 를 성립시켰지만, bootstrap
이 이미 진입점(CLAUDE.md)에 규칙을 넣은 프로젝트에서는 **이중 주입 + 세션당
~2.5KB 비용**이 된다. 그래서:

- `plugin/adapters/claude-code/rules.md` 신설 — 내용은 bootstrap 진입점·Gemini
  컨텍스트와 **같은** `render_entrypoint_rules` 파생 (채널 셋, 정본 하나).
- SessionStart 두 번째 hook: `CLAUDE.md` / `.claude/CLAUDE.md` (Claude Code 가
  자동 read 하는 두 파일) 에서 **생성 마커를 grep** — 있으면 생략, `@AGENTS.md`
  import 패턴(kit 권장 통합안)은 AGENTS.md 쪽 마커로 인정, 없을 때만
  `cat "${CLAUDE_PLUGIN_ROOT}/adapters/claude-code/rules.md"`.
- 마커 탐침은 `GENERATED_MARKER` 에서 파생 (`_rules_marker_probe`) — 손으로
  박으면 마커 개정 시 hook 만 낡아 항상 이중 주입이 된다.

## 3. 실측

| 경로 | 결과 |
|---|---|
| 진입점 없는 프로젝트 | ✔ **PRESENT** — 규칙 블록 주입 + `${CLAUDE_PLUGIN_ROOT}` 전개 실측 성립 |
| 마커 있는 CLAUDE.md | ✔ **SKIPPED** — rules.md 고유 제목이 컨텍스트에 없음 (이중 주입 없음) |
| validate / 인벤토리 | ✔ --strict 통과, Skills 4 / Hooks 2 이벤트 유지 |

**부수 발견**: CLAUDE.md 안의 HTML 주석(생성 마커)은 **모델 컨텍스트에서
스트립된다** (마커 카운트 ZERO 인데 규칙 섹션은 보임). 판정은 파일 대상 grep
이라 무영향이지만, "모델에게 마커가 보이는가" 를 판정에 쓰면 안 된다는 뜻이다.

## 4. 검사

`check_agent_plugin_payload` case 8 확장 (15 case 유지): 주입 hook 정확히 1개 +
마커 탐침 + 진입점 2종 확인 + rules.md 가 진입점 규칙 파생. 되주입 2종 실증
(탐침 제거 → FAIL / rules.md 등록 누락 → FAIL). 전량 2축 **252/252 ×2 green**.

## 5. 남은 것

- 별건 대기: [TASK-2026-08-12-main-019] macOS PEP 668 (MacBook 전원 시),
  [TASK-2026-08-13-main-004] CI mypy flake 재발 관찰.
- v1.1.9/v1.2.0 릴리스 — 소유자 발행 지시 대기. **P1~P5 + 어댑터 + 조건부 주입이
  전부 미발행 상태로 쌓여 있다** — 플러그인 채널의 marketplace 소비자는 발행
  전까지 이 개선을 받지 못한다.
