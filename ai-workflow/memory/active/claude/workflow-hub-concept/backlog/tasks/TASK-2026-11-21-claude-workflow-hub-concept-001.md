---
id: TASK-2026-11-21-claude-workflow-hub-concept-001
status: done
created_at: 2026-11-21
source_anchor: generic-task-2026-11-21-claude-workflow-hub-concept-001
source_path: backlog/2026-11-21.md
kind: generic
wbs: M-032/WBS-32.4
---

# TASK-2026-11-21-claude-workflow-hub-concept-001 — ADR-033 Accepted · DS1~DS9 확정 · PURPOSE 2.0판 적용 · M-032 close

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-21
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `ai-workflow/wiki/decisions/adr-033-workflow-hub.md`
  - `workflow-source/core/hub_spec.md`
  - `ai-workflow/memory/active/PURPOSE.md`
  - `ai-workflow/memory/active/roadmap/M-032-workflow-hub-design.md`

- Description: M-032/WBS-32.4. 소유자 2026-11-21 DS1~DS9 권고안 확정. hub_spec §10 확정 표시, ADR-033 status accepted + design 결정 요약, Q9 에 따라 PURPOSE.md 를 requirements §17.1 의 2.0판(purpose_version 2)으로, M-032 done.
- Completion criteria: ADR-033 status accepted
- Completion criteria: PURPOSE.md 가 §17.1 과 일치하고 purpose_version 2
- Completion criteria: M-032 선언 · 파생 done

## 🧭 Plan

- Claims: C1 ADR-033 이 accepted 이고 requirements · hub_spec · DS 결정을 가리킨다
- Claims: C2 PURPOSE.md 가 §17.1 개정안의 칸과 글자 그대로 일치하고 purpose_version 2 다
- Claims: C3 M-032 가 선언 · 파생 done 이다
- Files that change: ai-workflow/wiki/decisions/adr-033-workflow-hub.md
- Files that change: workflow-source/core/hub_spec.md
- Files that change: ai-workflow/memory/active/PURPOSE.md
- Order of work: hub_spec §10 확정
- Order of work: ADR-033 Accepted
- Order of work: PURPOSE 2.0 적용
- Order of work: M-032 close · refresh · 검사
- Order of work: 커밋 · push
- Plan risks: PURPOSE 를 읽는 검사 · state 생성(purpose_digest)이 새 문구에 깨질 수 있다
- Plan risks: 이 브랜치를 1.x 분기(R16.5) 전에 main 에 합치면 1.x 의 PURPOSE 가 2.0판이 된다
- Proof: §17.1 대 PURPOSE 칸별 대조 스크립트 · roadmap_state M-032 · --changed

## 🛠️ Implementation / Content

- Progress: `2026-11-21 00:13` 커밋 · push
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: ADR-033 Accepted · hub_spec §10 DS 확정 · PURPOSE 2.0판 · M-032 done · 검사 1건 판 고정 해제(형식 계약으로)
- Verification: §17.1 10칸 대 PURPOSE 글자 대조 일치 · purpose_version 2 · ADR-033 accepted · M-032 선언 · 파생 done 1.0 · 첫 --changed 3 red: 문서 스탬프(→ 2026-11-21) · check_purpose_concept_v0_9_2 가 살아 있는 판 1 을 고정(→ 양의 정수 형식 계약 + 판 ≥2 면 본문 근거 필수, 되주입 판 0 · 근거 없는 판 2 red / v1 통과) · check_state_json_generated case 5 가 main 네임스페이스 생성물 드리프트(→ CODEX_WORKFLOW_BRANCH=main refresh-state, diff 는 purpose 키 3개만) · 재실행 --changed 142/142 · smoke 8/8 · verifier 생략(검증 간소화 기간)
- Follow-up: 이 브랜치를 main 에 합치기 전에 1.x 분기(R16.5) — 합치면 1.x 의 PURPOSE 가 2.0판이 된다
