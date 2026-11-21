---
id: TASK-2026-11-20-claude-workflow-hub-concept-016
status: done
created_at: 2026-11-20
source_anchor: generic-task-2026-11-20-claude-workflow-hub-concept-016
source_path: backlog/2026-11-20.md
kind: generic
wbs: M-032/WBS-32.2
---

# TASK-2026-11-20-claude-workflow-hub-concept-016 — 허브 MCP 도구 · HTTP API 형식 — 부트스트랩 묶음 · 토큰 묶음 · 판 협상 · 오류 코드

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-20
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `workflow-source/core/hub_spec.md`

- Description: M-032/WBS-32.2. requirements(workflow-hub-requirements-2026-11.md) R0~R16 과 §16 실측을 core/hub_spec.md 로 고정.
- Completion criteria: hub_spec 의 해당 절이 있고 대응 R 누락 0
- Completion criteria: 새 결정은 DS 표에 있다

## 🧭 Plan

- Claims: C1 hub_spec §도구: 도구 표 · HTTP 거울 · 오류 코드 · 판 협상 이 requirements 의 해당 R 을 하나도 빠뜨리지 않고 대응표로 가리킨다
- Claims: C2 design 이 새로 정한 것은 결정 표(DS)에 권고와 함께 있다
- Files that change: workflow-source/core/hub_spec.md
- Order of work: 스펙 절 작성
- Order of work: 대응표 대조
- Order of work: 검사
- Order of work: 커밋 · push
- Plan risks: requirements 에 없는 범위를 스펙이 만들어 냄 — 새 것은 DS 로만
- Proof: 대응표 스크립트 대조 · --changed

## 🛠️ Implementation / Content

- Progress: `2026-11-20 23:45` 커밋 · push
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: hub_spec §4 (경로 · 판 협상 · 오류 코드 14 · 부트스트랩 묶음 5 · 토큰 묶음 9묶음 · 화면 인증) · §5.1 쓰기 지시
- Verification: core/hub_spec.md §4 (경로 · 판 협상 · 오류 코드 14 · 부트스트랩 묶음 5 · 토큰 묶음 9묶음 · 화면 인증) · §5.1 쓰기 지시 작성 · 대응표 스크립트 대조: requirements R 106개 누락 0 · 새 결정은 §10 DS1~DS9 · --changed 132/132 · verifier 생략(검증 간소화 기간)
- Follow-up: DS1~DS9 소유자 확인 → WBS-32.4 ADR-033 Accepted
