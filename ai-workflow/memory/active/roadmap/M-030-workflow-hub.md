---
id: M-030
title: 워크플로우 허브 — 여러 환경이 함께 쓰는 task 관리 서버 (arcturus-port 대시보드의 일반화)
sdlc_phase: concept
status: in_progress
order: 30
parallel_allowed:
  - M-007
  - M-028
deliverables:
  - docs/planning/workflow-hub-review-2026-11.md
  - ai-workflow/wiki/decisions/adr-033-workflow-hub.md
goals: [G1, G2, G5]
---

# M-030 — 워크플로우 허브

소유자 제기(2026-11-20): arcturus-port 프로젝트에서 시험 중인 대시보드를 통한 작업 관리 방식을
워크플로우 전체(kit)로 넓힌다.

**이미 정한 방향 (소유자, 2026-11-20)**:

- task 정본 = **허브 DB** (arcturus ADR-043 과 같은 쪽)
- 허브는 **kit 이 Python 으로** 가진다 (Go 포털을 옮기지 않는다 — PURPOSE '비 Python runtime 제외' 유지)
- 첫 단계 = **개념 문서 + ADR** — 코드는 결정 뒤

**전제 이력**:

- arcturus-port ADR-043 (공유 대시보드 · task 원본 = 포털) · `docs/plan/표준-워크플로우-포털-이식-개념-2026-11-20.md`
  (W1 규칙 배달 + W2 표준 task 칸 · done 게이트, 판정은 kit 서비스 `kitd.py`).
- kit 의 기존 층: 워크벤치(ADR-032, checkout 하나에 서버 하나) · workspace registry federation
  (`multi_workspace_orchestration.md` §7, 읽기 전용) · push 선점.

**concept §1~§10 종결 (2026-11-20)**: 소유자 결정 = concept 문서 §8 권고안 D1~D11 전부 (§10) — 목표 보충 H4 (kit 없는 부트스트랩 · 허브가 task · handoff · 이력 관리) · H5 (공유 지침 허브 셋업 · 공유). requirements 는 M-031 (미개설). **열림**: 위키 검토 (WBS-30.2, E1~E6) · 프로젝트 등록 · 식별 · 콜사인별 작업 기억 (WBS-30.3, H6~H10 지시, F1~F5 · G1~G3 · I1~I4) — 소유자 제기 2026-11-20.

## WBS

- **WBS-30.1** concept 검토 + ADR-033 초안 — arcturus 실험의 효과 · 문제, 허브 개념, kit 표면 영향, 단계, 결정 H1~H5 · D1~D11 (ADR Proposed, design 뒤 Accepted) — 산출물: `docs/planning/workflow-hub-review-2026-11.md` §1~§10 · `ai-workflow/wiki/decisions/adr-033-workflow-hub.md`
- **WBS-30.2** 위키 허브 관리 검토 — kit 위키를 허브에서 관리할 수 있는지, 구성안 · 어려운 점 · 소유자 선택지 E1~E6 — 산출물: `docs/planning/workflow-hub-review-2026-11.md` §11
- **WBS-30.3** 프로젝트 등록 · 식별 — 등록 전 부트스트랩퍼 · git 주소 기반 식별 (H6 · H7), 선택지 F1~F5 · 콜사인별 작업 기억 (H8), 선택지 G1~G3 · 콜사인 등록 정보 `.gitignore` (H9) · MCP 로 도구 제공 (H10), 선택지 I1~I4 — 산출물: `docs/planning/workflow-hub-review-2026-11.md` §4.2 · §12 · §13 · §14
