---
id: TASK-2026-08-14-perf-handoff-baseline-rolloff-001
status: done
created_at: 2026-08-14
source_anchor: generic-task-2026-08-14-perf-handoff-baseline-rolloff-001
source_path: backlog/2026-08-14.md
kind: generic
---

# TASK-2026-08-14-perf-handoff-baseline-rolloff-001 — handoff 기준선 롤오프

## 📝 Description

- 상태: done
- 요청일: 2026-08-14
- 담당: AI Agent
- 작업 내용: handoff §1 기준선 롤오프 — 최근 N개만 남기고 나머지는 이관 (삭제 아님), 재증식은 검사로 막는다
- 범위 밖: task SSOT 구조화(main-008) / 메모리 필드 라벨 영어화
- 완료 기준: (작성 필요 — 검증 방법을 구체적으로 적는다)

## 🛠️ Implementation / Content

- 진행 현황: `2026-08-14 06:16` 기준 §1 기준선이 handoff 의 66%이고 세션마다 단조 증가한다

## ✅ Outcome

- 작업 결과: 계약 검사 10/10 PASS + 되주입 실측(이관 생략 → case 3·6 FAIL). 전량 2축은 병합 후 main 에서 실제 이관을 돌린 뒤 잰다
- 작업 결과: `BASELINE_ITEMS_CAP=4` / `BASELINES_FILENAME` / `BASELINE_LABELS` 를 `RECENT_DONE_ITEMS_CAP` 과 같은 정본 자리에
- 작업 결과: `wk rollover-baselines` 신설 (기본 계획만 · `--apply` 로 이관 · 멱등 · `--cap 0` 거부) + console script 등록
- 작업 결과: `check_handoff_baseline_cap` 10 cases — 중심은 "줄었는가" 가 아니라 **"옮겨졌는가"**(case 3). 생성기 입력 불변(case 9)과 헤더 미적층(case 6)도 고정
- 작업 결과: 린터 `handoff_baseline_bloat` — fix_suggestion 이 **도구를 가리킨다**. "지워라" 라고 적으면 사람이 지우고 그 세션 이력이 사라진다
- 작업 결과: 정본 §11.1 에 명령 + 파싱 계약에 "손으로 지우지 말 것" 추가 → 스냅샷·진입점·플러그인 재생성
- 작업 결과: **되주입이 검사 자신의 결함을 드러냈다** — 이관을 생략하자 case 3 이 예외로 죽으며 case 4~10 이 아예 안 돌았다. `_run` 이 AssertionError 만 잡고 있었다
- 작업 결과: **행을 하나 늘리자 위치 가정이 깨졌다** — `check_agent_plugin_payload` 가 §11.1 의 **마지막 행**을 재생성 명령으로 보고 있었다. 목적 기반 조회(`find_memory_command`)로 교체
- 검증 결과: 계약 검사 10/10 PASS + 되주입 실측(이관 생략 → case 3·6 FAIL). 전량 2축은 병합 후 main 에서 실제 이관을 돌린 뒤 잰다 — 브랜치에서 active/main 을 고치는 것은 네임스페이스 가드가 막는 일이고 그게 맞다
- 후속 작업: 병합 후 main 에서 `wk rollover-baselines --handoff-path ai-workflow/memory/active/main/session_handoff.md --apply` 실행 → 토큰 전후 실측
