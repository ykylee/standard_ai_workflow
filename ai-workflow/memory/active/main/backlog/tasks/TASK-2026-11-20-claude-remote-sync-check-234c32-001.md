---
merged_from: claude/remote-sync-check-234c32
id: TASK-2026-11-20-claude-remote-sync-check-234c32-001
status: done
created_at: 2026-11-20
source_anchor: generic-task-2026-11-20-claude-remote-sync-check-234c32-001
source_path: backlog/2026-11-20.md
kind: generic
wbs: M-007/WBS-7.4
---

# TASK-2026-11-20-claude-remote-sync-check-234c32-001 — 호스트 역할 가이드 — 읽기 전용 소비자는 pull · 환경 맞추기 · 버전 업데이트만, push 는 hook 이 막는다

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-20
- Owner:
- Host:
- Host IP:
- Affected documents:
  - 

- Description: 저장소 소비자는 개발 참여자와 읽기 전용 소비자 둘이다(소유자 2026-11-19). 소유자 결정: 역할 표식은 클론별 git config workflow.role(consumer|contributor) · 미선언은 멈추고 소유자에게 묻는다 · 문서 + pre-push 차단.
- Completion criteria: docs/HOST_ROLES.md — 역할 표식 · 미선언 처리 · 소비자 업데이트 절차(트리 확인 → ff pull → 환경 → §2.8 재적용 → doctor 확인) · 금지 목록
- Completion criteria: CLAUDE.md · AGENTS.md 에 pull · 업데이트 · 세션 시작 전 역할 확인 규칙 한 줄과 가이드 링크
- Completion criteria: pre-push: workflow.role=consumer 인 클론의 push 는 게이트 기록이 있어도 exit 1, 미선언 · contributor 는 기존 판정 그대로 — check_pre_push_gate 에 case, 수리를 되돌리면 red (되주입)
- Completion criteria: 전량 게이트 --branch-context=all native · slash green

## 🧭 Plan

- Claims: C1 소비자 클론은 push 할 일이 없으므로 hook 이 모든 push 를 막아도 정상 흐름을 해치지 않는다
- Files that change: docs/HOST_ROLES.md
- Files that change: CLAUDE.md
- Files that change: AGENTS.md
- Files that change: workflow-source/workflow_kit/common/gate_evidence.py
- Files that change: workflow-source/tests/check_pre_push_gate.py
- Files that change: docs/DOCUMENT_INDEX.md
- Order of work: 가이드 문서
- Order of work: gate_evidence 역할 판정 + 검사 case
- Order of work: 진입점 규칙
- Order of work: 검사 · verifier · 커밋 · push
- Plan risks: 소비자 클론의 기존 CLAUDE.md 는 pull 전 옛것 — 첫 pull 뒤에야 규칙이 보인다
- Plan risks: core.hooksPath 를 안 켠 소비자 클론에는 hook 이 안 걸린다
- Proof: check_pre_push_gate 되주입 · 이 호스트 git config workflow.role contributor 설정 후 실제 push 통과

## 🛠️ Implementation / Content

- Progress: `2026-11-20 00:30` done — 게이트 · push 완료
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: docs/HOST_ROLES.md + CLAUDE.md · AGENTS.md 역할 확인 규칙 + gate_evidence.check_consumer_push + check_pre_push_gate case. 이 호스트 workflow.role=contributor 선언.
- Result: 소유자 보충(2026-11-20): 구분은 이 저장소 한정 — 소비자가 워크플로우 코드를 고쳐 반영하려는 시도를 막는 것. 가이드에 범위 명시 + §4.1 개선은 FEEDBACK.md 의 GitHub Issue(제안 diff 는 본문 텍스트)로, pre-push 거절 문구도 이슈 경로로.
- Verification: verifier 기준 1~3 PASS(되주입 3건 red · 역할×sha hook 실측) · 기준 4 전량 게이트 1fdcddc5 native · slash 332×2 rc 0 · Proof: workflow.role=contributor 인 이 클론에서 실제 push 통과(219a8460..1fdcddc5)
- Follow-up: 소비자 클론에서 세션 시작 hook 이 생성물 날짜를 다시 써 트리가 더러워진다 — role=consumer 면 session-start 가 쓰지 않게 할지 소유자 결정 필요
- Follow-up: 소비자 호스트의 첫 pull 은 옛 CLAUDE.md 로 시작한다 — 소유자가 한 번 '역할 먼저 확인' 을 지시하거나 workflow.role 을 직접 선언
