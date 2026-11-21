---
merged_from: claude/workflow-hub-concept@8ef1ee07
id: TASK-2026-11-20-claude-workflow-hub-concept-011
status: done
created_at: 2026-11-20
source_anchor: generic-task-2026-11-20-claude-workflow-hub-concept-011
source_path: backlog/2026-11-20.md
kind: generic
wbs: M-031/WBS-31.1
---

# TASK-2026-11-20-claude-workflow-hub-concept-011 — 2.0 허브 지원 하네스 4종으로 — Claude Code · Codex · MiniMax Code · Antigravity (소유자 결정)

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-20
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `docs/planning/workflow-hub-requirements-2026-11.md`

- Description: 소유자 2026-11-20: 지원 하네스 목록을 claude · codex · minimax · antigravity 로 우선 추린다. requirements 의 하네스 범위(R7.2 · R2.6 · §16.3)와 결정 기록에 반영.
- Completion criteria: R7.2 · R2.6 · §16.3 · §20 이 4종 결정과 일치한다
- Completion criteria: Q7 이 design 진입 조건으로 표시된다

## 🧭 Plan

- Claims: C1 requirements 의 하네스 범위가 4종으로 일관된다 (R7.2 진입 파일 · R2.6 안내 · R2.1 검증 · §16.3)
- Claims: C2 빠진 하네스(Grok · OpenCode · pi-dev · Aider 등)의 처리가 적혀 있다
- Files that change: docs/planning/workflow-hub-requirements-2026-11.md
- Order of work: 하네스 언급 전수 조사
- Order of work: 문서 반영
- Order of work: 검사
- Order of work: 커밋 · push
- Plan risks: Antigravity 가 포함되므로 Q7(환경 변수 참조 미지원)이 design 진입 전 필수 결정이 된다
- Proof: 하네스 이름 grep 전수 · --changed green

## 🛠️ Implementation / Content

- Progress: `2026-11-20 23:24` 커밋 · push
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: Q8 확정 — 지원 4종, 나머지는 실측 뒤 추가 결정. Antigravity 포함으로 Q7 이 design 진입 필수 조건
- Verification: 하네스 언급 전수 grep 후 R2.1 · R2.6 · R7.1 · R7.2 · R14.9 · §16.3 · §20 반영, R2.8 신설(파생 목록 하나 요구) · 진입 파일 이름은 bootstrap_lib/harnesses 표와 대조(CLAUDE.md · AGENTS.md · MiniMax.md · ANTIGRAVITY.md) · R 97 전부 [검증] · 미정의 참조 0 · --changed 108/108 · verifier 생략(검증 간소화 기간)
- Follow-up: 소유자 결정 Q7 (Antigravity 토큰 전달)
- Follow-up: Antigravity 도구 호출 경로 재실측 (S3 리터럴 실행은 경로 미구분)
