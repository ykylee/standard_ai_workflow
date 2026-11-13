---
id: TASK-2026-11-13-claude-remote-sync-check-234c32-006
status: in_progress
created_at: 2026-11-13
source_anchor: generic-task-2026-11-13-claude-remote-sync-check-234c32-006
source_path: backlog/2026-11-13.md
kind: generic
wbs: M-027/WBS-27.1
---

# TASK-2026-11-13-claude-remote-sync-check-234c32-006 — 계획·진척 워크벤치 design — 프록시 · 브라우저 실측 + ADR-032 + core 스펙

## 📝 Description

- Status: in_progress
- Priority: high
- Request date: 2026-11-13
- Owner:
- Host:
- Host IP:
- Affected documents:
  - 

- Description: requirements(docs/planning/plan-workbench-requirements-2026-11.md) 를 받아 워크벤치 서버의 design 을 정한다. 먼저 R11 의 design 전 실측(nginx · Caddy 실물을 docker 로, 실제 브라우저에서 쿠키 Path · SameSite · 리다이렉트 · 폼 제출)을 하고, ADR-032 와 core 스펙 plan_workbench_spec.md 를 쓴다. ADR-031 이 넘긴 것(MCP 도구 둘 · 쓰는 쪽 LF · 번호 규칙)과 2단계 구현이 넘긴 것을 소비한다. Codex hook 주입 실측은 하지 않는다(소유자 결정).
- Completion criteria: [C1] nginx 와 Caddy 실물(docker, 판 고정) 뒤에서 실제 브라우저(Chrome 판 기록)로 requirements §1.3 의 네 구성(직접 · 상대 리다이렉트 + Path=접두사 · 절대 Location · Path=/)을 재고, 쿠키 Path · SameSite 가 로그인 뒤 리다이렉트 · 폼 제출 · 다른 사이트에서 들어오는 링크에서 어떻게 되는지 숫자 · 표로 문서에 남긴다; 측정 스크립트는 저장소 밖에 두고 절차와 결과만 남긴다
- Completion criteria: [C2] ADR-032 가 M-027 의 결정 대상(서버 모듈 배치 · CLI 등록 · 토큰 설정 형태 · 세션 표 · 화면 렌더러 · 내장 정적 자원 · .workbench/ 와 받은편지함의 git 무시 수단 · MCP 도구 둘 · §11.1 문구와 스킬 · 검사 구성)을 하나씩 대안과 함께 정한다
- Completion criteria: [C3] core 스펙 plan_workbench_spec.md 의 각 절이 requirements 의 R 번호에 대응하고(대응표), requirements 대비 바꾼 것은 ADR 의 변경 표에 사유와 함께 있다; 받은편지함 쓰기 · 번호 · 응답 형식은 claim_plan_spec.md 를 가리키고 다시 정하지 않는다
- Completion criteria: [C4] ADR-031 결정 23 · 25 와 2단계 구현이 넘긴 항목(원본 받은편지함 미반영 + 되돌려 적기, 같은 디렉터리 배치의 보고, 받은편지함 건수의 단일 출처, pending_responses 의미 둘, 응답 이름의 비파일 항목 보고)이 ADR-032 에서 정해지거나 남길 곳이 명시된다
- Completion criteria: 열린 결정이 없고(소유자가 연 결정은 답이 기록됨), 문서 메타 · 링크 검사와 --changed 가 green 이다

## 🧭 Plan

- Claims: C1 프록시 · 브라우저 실측이 requirements §1.3 의 네 열을 실물로 다시 잰다
- Claims: C2 ADR-032 가 M-027 의 결정 대상을 빠짐없이 정한다
- Claims: C3 core 스펙이 requirements 의 R0~R10 과 ADR-031 계약에 어긋나지 않는다
- Claims: C4 앞 단계가 넘긴 항목이 소비되거나 남긴 곳이 명시된다
- Decisions: D1 [C1] 세션 쿠키의 SameSite 는? | default: lax | options: lax = 다른 사이트의 링크(GET)에 쿠키를 싣는다, POST 는 Origin · CSRF 가 막는다; strict = requirements 대로, 다른 사이트의 링크는 로그인 화면을 거친다 | state: answered:lax
- Files that change: ai-workflow/wiki/decisions/adr-032-plan-workbench.md (신규)
- Files that change: workflow-source/core/plan_workbench_spec.md (신규) · ai-workflow/core 사본이 필요하면 함께
- Files that change: docs/planning/plan-workbench-requirements-2026-11.md (R11 실측 결과 · 상태 줄)
- Files that change: ai-workflow/wiki/index (ADR 색인) · ai-workflow/memory/active/roadmap/M-027-plan-workbench-design.md · ai-workflow/memory/active/** (task · handoff · state)
- Order of work: [C1] 프로토타입 서버(scratchpad) + nginx · Caddy docker + playwright-core 로 Chrome 측정 → requirements 문서에 결과
- Order of work: [C2][C4] ADR-032 초안 — 결정 대상 하나씩, ADR-031 · 2단계 이월 항목 소비
- Order of work: [C3] core 스펙 — R 대응표 · claim_plan_spec 포인터
- Order of work: verifier → 소유자 승인(accepted) → M-027 닫기
- Plan risks: [C1] 브라우저 자동화 도구가 저장소 밖(다른 저장소의 playwright-core)이다 — 판을 기록하고, 측정이 도구가 아니라 브라우저의 쿠키 판정을 재는지 대조(음성 구성)로 확인한다
- Plan risks: [C1] docker 이미지 태그를 고정하지 않으면 측정이 바뀐다 — 판 고정 태그와 digest 를 기록한다
- Plan risks: [C3] requirements 의 R5.3-7 (번호 = 최대 + 1) 은 ADR-031 결정 13 이 바꿨다 — 스펙이 옛 문면을 옮기지 않게 claim_plan_spec 을 가리킨다
- Proof: 실측 표 (docker 이미지 digest · Chrome 판 · 음성 대조 포함), ADR · 스펙의 대응표, verifier

## 🛠️ Implementation / Content

- Progress: 2026-11-13 verifier 1차: FAIL 3 (대안 없는 결정 대상 넷 · 스펙에 없는 requirements 문장 넷 · 1단계에서 넘긴 4건 기록 소실 + 게이트의 배치 동작 미정). 수리: 대안 · 결정 24(정리 거리를 M-029 ① 로) · 25(게이트는 배치로 막지 않는다) · V6 · V7 · 스펙 보강 · 모순 넷. 2차 대기
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result:
- Follow-up:
