---
type: decision
status: accepted
adr_id: ADR-027
decided_at: 2026-08-25
alternatives_considered: [single-roadmap-md, maturity-matrix-json-extension, advisory-only-no-gate, milestone-only-no-wbs]
related_pages: [concepts/stage-gate-pattern, concepts/unit-of-work]
created: 2026-08-25
updated: 2026-08-25
r9_skip: true
---

# ADR-027: 로드맵·마일스톤·WBS 진척 관리 + SDLC 온보딩 기본 흐름

## Status

**Accepted** (2026-08-25, 60차 세션 소유자 결정). 정본 스펙은
`workflow-source/core/roadmap_milestone_wbs_spec.md` 이고, 이 페이지는 결정과
근거만 기록한다.

## Context

워크플로우의 문서 계층에 **한 층이 비어 있다.**

- `PURPOSE.md` (4-element) 는 *왜* 를 말하고, backlog task 는 *오늘 무엇을* 을
  말한다. 그 사이 — **무엇을 어떤 순서로, 어디까지 왔는가** — 를 말하는 자리가
  없다. 다음 작업 축 선정이 매번 소유자 판단 대기로 남는 구조적 이유다.
- `workflow_kit/common/milestones.py` 의 `assess_milestone_progress` 는 데모
  수준이다: phase→thread 매핑이 하드코딩("simplified for demo")이고, 이 저장소
  자신의 `maturity_matrix.json` 만 읽는다. 소비 프로젝트가 쓸 수 있는 형태가
  아니다.
- 온보딩(`workflow_adoption_entrypoints.md` 의 신규/기존 2경로)은 문서 세트를
  깔지만 **어떤 순서로 일할지**는 말하지 않는다. 컨셉이 정리되지 않은 채
  구현 task 부터 쌓이는 것을 막는 장치가 없다.

## Decision

1. **계층 신설**: `PURPOSE.md(왜) → roadmap(무엇을 어떤 순서로) → TASK(오늘)`.
   로드맵은 SDLC 단계를 선언한 마일스톤의 순서이고, 각 마일스톤은 WBS 로
   산출물을 분해하며, WBS leaf 가 기존 task SSOT 와 연결된다.
2. **문서 형태 = 혼합** (소유자 결정): 사람이 쓰는 SSOT 는
   `ai-workflow/memory/active/roadmap/` **디렉터리**(index + 마일스톤별 파일,
   task SSOT 패턴과 동일), 기계가 읽는 정본은 정식 Pydantic 스키마의
   **생성물 JSON** (`roadmap_state.json` — state.json 과 같은 계약: 손편집
   금지, 재생성). `maturity_matrix.json` 의 milestones 키는 이 스키마로
   이행하고 데모 휴리스틱은 은퇴한다.
3. **온보딩 기본 = SDLC**: 신규 프로젝트 bootstrap 은 컨셉 정리 →
   요구사항 → 설계 → 구현 순의 기본 로드맵 씨앗을 심고, 첫 마일스톤
   (Concept, 산출물 = PURPOSE.md 4-element 완성)을 `in_progress` 로 시작한다.
   기존 프로젝트는 `repository_assessment` 로 현재 단계를 추정한 초안을 받는다.
4. **강제 = 게이트** (소유자 결정): 로드맵이 있는 프로젝트에서 task 생성은
   WBS 링크가 필수이고, 앞 단계 마일스톤이 끝나지 않은 뒤 단계에는 task 를
   열 수 없다. **우회는 침묵이 아니라 선언이다** — 예외는 task 에 사유와 함께
   선언하고 검사가 그 수를 센다; 병행 허용은 로드맵 파일이 선언한다
   (게이트를 코드가 아니라 로드맵 선언이 결정한다).

## Alternatives Considered

- **single-roadmap-md**: 단일 `ROADMAP.md`. 시작은 얇지만 마일스톤이 늘면
  한 파일이 SSOT·이력·WBS 를 다 담아 부푼다. task SSOT 를 파일 분리로 간
  전례(v0.14.0)와 어긋난다 — 기각.
- **maturity-matrix-json-extension**: 기존 JSON 확장 단독. 사람이 쓰기
  불편하고 이 저장소 전용 파일이라 소비 프로젝트 표준으로 부적합 — 단독으로는
  기각하되, **스키마 정형화 부분은 혼합안에 흡수**.
- **advisory-only-no-gate**: 경고만. 이 저장소의 기존 원칙이지만, 소유자가
  게이트를 명시 선택했다. 컨셉 없는 구현 task 누적은 되돌리기 비싼 종류의
  드리프트라는 판단 — 기각.
- **milestone-only-no-wbs**: WBS 없이 마일스톤만. task 가 마일스톤에 직접
  붙으면 중간 산출물 단위의 진척이 안 보이고, 롤업이 'task 개수' 로 왜곡된다
  (50차 규칙: 지표의 분모는 찾은 것이 아니라 선언한 것) — 기각.

## Consequences

- 진척은 손으로 적지 않는다 — WBS leaf ← task 상태에서 **파생**한다
  (55차 규칙: 산문이 SSOT 를 복제하면 반드시 갈라진다).
- 게이트 도입으로 backlog-update 의 계약이 바뀐다 (breaking 후보 —
  `RELEASE.md` §1.5 로 등급 판정). 로드맵이 **없는** 프로젝트는 게이트가
  성립하지 않으므로 기존 동작 그대로다 (additive 채택).
- 구현은 6개 마일스톤으로 단계 실행하며, 그 계획 자체가 이 저장소의 첫
  roadmap 이 된다 (자기 적용). 상세는 스펙 §10.

## References

- 정본 스펙: `workflow-source/core/roadmap_milestone_wbs_spec.md`
- 결정 task: `TASK-2026-08-25-main-002`
- 재사용 조각: `llm_wiki_concept_purpose_spec.md` (4-element) ·
  `workflow_adoption_entrypoints.md` (온보딩 2경로) ·
  `existing_project_onboarding_contract.md`
