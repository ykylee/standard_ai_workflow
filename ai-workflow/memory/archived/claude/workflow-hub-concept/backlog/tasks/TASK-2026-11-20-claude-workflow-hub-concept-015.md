---
carried_over_to: TASK-2026-11-20-claude-workflow-hub-concept-015@main
id: TASK-2026-11-20-claude-workflow-hub-concept-015
status: done
created_at: 2026-11-20
source_anchor: generic-task-2026-11-20-claude-workflow-hub-concept-015
source_path: backlog/2026-11-20.md
kind: generic
wbs: M-032/WBS-32.1
---

# TASK-2026-11-20-claude-workflow-hub-concept-015 — 허브 스키마 · 이관 — 프로젝트(git 주소 별칭) · 콜사인 · task · 이력 · handoff · 지침 · 위키 · 로드맵

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-20
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `workflow-source/core/hub_spec.md`

- Description: M-032/WBS-32.1. requirements(workflow-hub-requirements-2026-11.md) R0~R16 과 §16 실측을 core/hub_spec.md 로 고정.
- Completion criteria: hub_spec 의 해당 절이 있고 대응 R 누락 0
- Completion criteria: 새 결정은 DS 표에 있다

## 🧭 Plan

- Claims: C1 hub_spec §스키마: 표 · 칼럼 · version 409 · 이관 · 백업 이 requirements 의 해당 R 을 하나도 빠뜨리지 않고 대응표로 가리킨다
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

- Result: hub_spec §3 (정규화 · 표 21종 · version 409 · request_id 멱등 · 이관 · 백업)
- Verification: core/hub_spec.md §3 (정규화 · 표 21종 · version 409 · request_id 멱등 · 이관 · 백업) 작성 · 대응표 스크립트 대조: requirements R 106개 누락 0 · 새 결정은 §10 DS1~DS9 · --changed 132/132 · verifier 생략(검증 간소화 기간)
- Follow-up: DS1~DS9 소유자 확인 → WBS-32.4 ADR-033 Accepted
