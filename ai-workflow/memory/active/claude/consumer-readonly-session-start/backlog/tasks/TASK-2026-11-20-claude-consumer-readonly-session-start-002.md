---
id: TASK-2026-11-20-claude-consumer-readonly-session-start-002
status: done
created_at: 2026-11-20
source_anchor: generic-task-2026-11-20-claude-consumer-readonly-session-start-002
source_path: backlog/2026-11-20.md
kind: generic
wbs: M-007/WBS-7.4
---

# TASK-2026-11-20-claude-consumer-readonly-session-start-002 — 소비자 클론(workflow.role=consumer)에서 session-start 가 저장소에 쓰지 않는다

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-20
- Owner:
- Host:
- Host IP:
- Affected documents:
  - 

- Description: 소유자 결정(2026-11-20, 135차 열린 결정): 소비자 클론이면 session-start 가 쓰지 않게 한다. 쓰기 경로 5 — 브랜치 메모리 자동 seed · 기본 브랜치 합류 반영/아카이브 · 부재 진입점 생성 · 워크벤치 자동 기동 · memory_index telemetry. 역할 판정은 pre-push 와 같은 정본(git config --local workflow.role).
- Completion criteria: role=consumer 인 클론에서 session-start 실행 전후 작업 트리 전체(무시 파일 포함) 스냅샷이 같다 — seed 가 필요한 브랜치 · 기본 브랜치 합류 반영 대상이 있는 상태 둘 다
- Completion criteria: consumer 출력이 읽기 전용임을 warnings 로 알리고 HOST_ROLES.md 를 가리킨다 · contributor · 미선언은 기존 동작(seed 가 일어난다)
- Completion criteria: 역할 판정은 한 곳(common 모듈) — gate_evidence 와 session_start 가 같은 함수를 쓰고 --local 만 읽는다(전역 설정 무시)
- Completion criteria: 회귀 검사 case — 수리를 되돌리면 red(되주입) · 전량 게이트 native · slash green

## 🧭 Plan

- Files that change: workflow-source/workflow_kit/common/host_role.py
- Files that change: workflow-source/workflow_kit/common/gate_evidence.py
- Files that change: workflow-source/workflow_kit/tools/session_start.py
- Files that change: docs/HOST_ROLES.md
- Order of work: host_role 공용 모듈 + gate_evidence 이전
- Order of work: session_start 읽기 전용 분기
- Order of work: 스냅샷 회귀 검사 + 되주입
- Order of work: 가이드 갱신 · verifier · 커밋 · 게이트 · push
- Plan risks: 모르는 쓰기 경로 — 검사를 파일 목록이 아니라 트리 전체 스냅샷으로
- Proof: 검사 case 되주입 red · 실제 이 저장소 임시 클론에서 consumer session-start 전후 git status --ignored 동일

## 🛠️ Implementation / Content

- Progress: `2026-11-20 03:50` done — 게이트 · push 완료
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: 작성 세션 측정: check_consumer_readonly_session_start 6/6 · 되주입 7건(seed · 합류 반영 · telemetry · 안내 warning · --local · 대소문자 · 진입점 생성) 각각 red · 실물: origin/main 임시 클론 2벌에서 수정 코드로 session-start — consumer 바뀐 파일 0 · 미선언은 telemetry events.jsonl 1 (실물 클론에서는 미선언도 합류 반영이 일어나지 않아 합류 경로는 fixture case 2 로만 측정) · 워크벤치 자동 기동 차단은 검사 환경이 자동 기동을 끄므로 미측정 · 검사 수 332→333 문서 2곳 반영
- Result: verifier 1차 FAIL 2 · UNMEASURED 1 반영: 오류 경로 warnings 에도 읽기 전용 안내 · case 추가(조기 경로 진입점 · --archive-stale-branches · 워크벤치 자동 기동) · 중복 역할 재판정 줄 삭제. 재측정: 6/6, 되주입 11건(seed · 조기/끝 진입점 · archive 플래그 · reflect · 자동 기동 · telemetry · 오류/정상 안내 · --local · 대소문자) 각각 red, 복원 cmp 일치, 남은 서버 프로세스 0
- Result: verifier 2차: 기준 1~3 PASS · 되주입 16곳 중 red 14 · SKIP 1(삭제된 줄) · green 1(recovery_hint) → case_1 에 recovery_hint 판정 추가, 되주입 red 확인. 기준 4 전량 게이트는 커밋 뒤
- Result: verifier 2회 — 2차 기준 1~3 PASS(6/6 · 실물 클론 consumer diff 0 · 대조군 seed/server.log) · 되주입 16곳 red 14, 남은 green 1(recovery_hint) 은 case_1 판정 추가 후 red 확인. 기준 4: 전량 게이트 cb31e317 native · slash 333×2 rc 0 · 브랜치 push 완료
- Verification: verifier 2회 — 2차 기준 1~3 PASS(6/6 · 실물 클론 consumer diff 0 · 대조군 seed/server.log) · 되주입 16곳 red 14, 남은 green 1(recovery_hint) 은 case_1 판정 추가 후 red 확인. 기준 4: 전량 게이트 cb31e317 native · slash 333×2 rc 0 · 브랜치 push 완료
- Follow-up:
