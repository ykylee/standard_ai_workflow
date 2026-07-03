# ADR-001: Source / State / Knowledge 3-layer 분리

- 문서 목적: standard_ai_workflow 저장소의 source / state / knowledge 3-layer 분리 결정 (v0.5.2) 의 rationale 와 운영 impact 를 정식 기록.
- 범위: 각 레이어의 책임, 갱신 정책, git tracked 여부, PRESERVE_RELATIVE_PATHS 정의, 후속 작업.
- 대상 독자: maintainer, Mavis consumer, 새 contributor.
- 상태: Accepted (v0.5.2)
- 최종 수정일: 2026-07-03
- 관련 문서: [`./README.md`](./README.md), [`../../workflow-source/core/workflow_state_vs_project_docs.md`](../../workflow-source/core/workflow_state_vs_project_docs.md), [`../../workflow-source/workflow_kit/constants.py`](../../workflow-source/workflow_kit/constants.py), [`./ADR-002-pydantic-v2-contract-v1-external-spec.md`](./ADR-002-pydantic-v2-contract-v1-external-spec.md)

- **Status**: Accepted (v0.5.2, commit `96431f1 refactor(workflow): separate source from runtime layer`)
- **Date**: 2026-05-04
- **Supersedes**: —
- **Superseded by**: —

## Context

v0.5.1 까지 `standard_ai_workflow` 저장소는 단일 레이어로 운영됐다. bootstrap 이 `ai-workflow/` 를 생성할 때 (a) workflow kit 원본 파일, (b) 사용자가 채워야 할 workflow state (handoff, backlog, state.json), (c) 영구 지식 문서 (PROJECT_PROFILE, README 등) 가 한 디렉토리에 섞여 있었다. 이로 인해:

1. **갱신 정책 혼란**: 모든 파일이 git 으로 tracked 되므로, 사용자가 handoff 를 갱신할 때마다 PR 리뷰가 필요했다. workflow state 는 휘발성/진행성 데이터인데 영구 지식과 같은 변경 정책이 적용된 셈.
2. **재배포 어려움**: 새 버전을 적용할 때 (`apply_workflow_upgrade`) 가이드 문서와 사용자 state 가 같은 트리에 있어서, source 갱신이 사용자 데이터를 덮어쓸 위험이 있었다.
3. **CI 부담**: smoke test 가 모든 markdown 파일을 검증하므로, 사용자 작성 handoff 까지 smoke test 의 검증 대상에 포함되어 false positive 가 잦았다.

## Decision

저장소를 **3-layer** 로 분리한다. 각 레이어의 책임과 갱신 정책은 명확히 구분된다.

| Layer | 경로 | 책임 | 갱신 정책 | Git tracked |
|---|---|---|---|---|
| **Source (SSOT)** | `workflow-source/` | 모든 skill / MCP / template / helper / doc 의 원본. workflow kit 의 단일 진실 공급원. | PR 리뷰 + merge | ✅ |
| **State (runtime)** | `ai-workflow/memory/` | 세션별 workflow state (handoff, backlog, state.json). 휘발성/진행성 데이터. | 자유롭게 갱신, PR 리뷰 불필요 | ⚠️ selective (`.gitignore` 로 대부분 제외, README 만 tracked) |
| **Knowledge (영구)** | `docs/` | 영구 지식 자산 (PROJECT_PROFILE, CODE_INDEX, RELEASE 등). maintainer 가 작성. | PR 리뷰 + merge | ✅ |

### 핵심 경계

- **`workflow-source/` 가 SSOT**: 사용자가 bootstrap 으로 받는 모든 파일은 이 디렉토리에서 렌더링됨. `ai-workflow/` 나 `docs/` 의 파일을 직접 수정해서 다시 bootstrap 하면 덮어써짐.
- **`ai-workflow/memory/` 는 자유 영역**: 사용자가 handoff 를 갱신하거나 backlog 에 task 를 추가할 때 PR 리뷰 없이 commit 가능. `.gitignore` 가 `ai-workflow/scripts/`, `ai-workflow/skills/` 등을 제외해서 source 의 재렌더링이 사용자 state 를 덮어쓰지 않음.
- **`docs/` 는 maintainer 영역**: 영구 지식은 maintainer 가 작성하고 PR 리뷰를 거쳐 머지. `docs/README.md` 가 governance 를 명시.

### PRESERVE_RELATIVE_PATHS

`workflow_kit.constants.PRESERVE_RELATIVE_PATHS` 가 `ai-workflow/memory/`, `ai-workflow/WORKFLOW_INDEX.md`, `ai-workflow/README.md` 를 명시. upgrade / bootstrap 시 이 경로는 절대 덮어쓰지 않음. v0.5.10.1 hotfix 에서 smart update 정책과 결합 — PRESERVE 경로에 존재하는 파일은 marker/hash 와 무관하게 무조건 보존.

## Consequences

### Positive

- **재배포 안전**: `apply_workflow_upgrade` 가 source 만 갱신하고 사용자 state 는 보존.
- **PR 부담 경감**: 사용자의 일상적 workflow state 갱신이 PR 리뷰를 거치지 않음.
- **CI 정확도**: smoke test 가 source 만 검증하므로 false positive 가 줄어듦.
- **책임 명확화**: 각 레이어의 owner / 변경 빈도 / 리뷰 정책이 다르므로, 운영 부담이 owner 별로 분산됨.

### Negative / Trade-offs

- **사용자 학습 비용**: "어떤 파일을 어디 두는지" 사용자가 처음에 헷갈릴 수 있음. `docs/PROJECT_PROFILE.md` 가 이 경계를 명시.
- **cross-layer 의존 명시 필요**: `ai-workflow/README.md` 가 workflow 의 진입점인데, 이 파일은 state layer 에 있지만 workflow 의 source 에서도 참조됨. 양쪽에 동기화된 marker 가 필요할 수 있음 (현 v0.5.10 은 marker 만으로 해결).
- **bootstrap 두 번 실행 시 충돌 가능성**: 사용자가 `ai-workflow/README.md` 를 손으로 수정한 후 다시 bootstrap 하면 smart update 가 marker 가 같고 hash 가 다른 경우 `UPDATED` 결정 → 사용자 편집 손실. `--preserve-user-edits` 옵션은 v0.5.11+ 후속.

### 후속 작업

- **v0.5.10.1**: smart update 정책 (VERSION marker + content hash fallback) 이 본 ADR 의 "PRESERVE_RELATIVE_PATHS" 와 결합되어, 다른 환경에서 wheel 설치 후 bootstrap 시 silent 갱신 가능.
- **v0.5.11+ (후속)**: `--preserve-user-edits` 옵션으로 사용자 편집 보호. `ai-workflow/README.md` 의 smart update marker 자동 stamping.

## References

- commit `96431f1 refactor(workflow): separate source from runtime layer`
- `workflow_kit/constants.py:47` — `PRESERVE_RELATIVE_PATHS` 정의
- `docs/README.md` §1 — 문서 분류 governance
- `workflow-source/core/workflow_state_vs_project_docs.md` — state vs project docs 경계 가이드
- Beta v0.5.10.1 release note — smart update 정책이 본 ADR 의 PRESERVE 와 어떻게 결합되는지
