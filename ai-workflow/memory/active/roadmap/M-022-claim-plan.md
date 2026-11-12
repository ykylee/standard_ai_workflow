---
id: M-022
title: 주장 트리 계획 — html-plan 개념 흡수 (task Plan 계약 + 검토 브리지)
sdlc_phase: concept
status: done
order: 22
parallel_allowed:
  - M-007
deliverables:
  - docs/planning/html-plan-absorption-review-2026-11.md
goals: [G2, G5]
---

# M-022 — 주장 트리 계획

소유자 제기(2026-11-12, 123차): Anthropic 커뮤니티 플러그인 저장소의 `html-plan`
(Thariq Shihipar, v1.0.0) 개념을 워크플로우에 흡수한다. html-plan 은 구현 계획을
**참·거짓을 가를 수 있는 동작 주장의 트리**로 쓰고, 사람이 정할 결정을 그 결정이 바꾸는
주장 위에 두고, 읽는 사람의 답을 마크다운 응답 하나로 돌려받는다.

**소유자 결정 (착수 시)**:

- 범위 = **A + B 함께 설계** — A: task 파일 `## 🧭 Plan` 계약 흡수(주장 · 결정 · 린트),
  B: html-plan 플러그인과의 브리지(`plan-export` 뼈대 생성 + `plan-import` 응답 반영).
- 흡수 방식 = 개념만 재구현 (PURPOSE 제외 영역 — 런타임 JS/CSS · node 를 저장소에 들이지 않는다).
- 진행 = SDLC 온보딩 기본 순서 (concept → requirements → design → implementation).

**전제 이력** (concept 검토가 대면할 것):

- task 파일은 `state.json` 생성기 입력이다 — 라벨은 곧 파싱 계약이고
  (`project_docs.TASK_FIELD_LABELS`), 기존 task 파일 160여 개는 고치지 않는다.
- `## 🧭 Plan` 절은 TASK-2026-10-05-main-002 (AI-native SDLC 플레이북) 이 넣었다 —
  지금은 파일 · 순서 단위다. html-plan 은 그 분할을 정면으로 금지한다.
- 플러그인 스킬은 정본 §11.1 명령과 1:1 이다 — 새 명령은 새 §11.1 줄을 전제한다.

**종결 (2026-11-12)**: 소유자 결정 = concept 문서 §7 기본값 D1~D5 전부 (Claims 선택 · 미열람 결정은
done 거부 · 완료 기준 `[C<n>]` 인용 연결 · import 는 결정 상태만 · 응답 원문 브랜치 메모리 커밋, 산출물 §10).
requirements 단계는 [`M-023`](./M-023-claim-plan-requirements.md) 로 이어진다.

## WBS

- **WBS-22.1** concept 검토 — html-plan 구성 실측, task Plan 계약 흡수안(A) · 브리지안(B)
  설계 초안, 소유자 선택지 — 산출물: `docs/planning/html-plan-absorption-review-2026-11.md`
  (TASK-2026-11-12-claude-remote-sync-check-234c32-002)
