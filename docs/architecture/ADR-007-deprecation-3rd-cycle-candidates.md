# ADR-007: Deprecation 3rd Cycle Candidate Identification (Placeholder)

- 문서 목적: standard_ai_workflow 의 deprecation 정책 운영 안정화 추적. 1st + 2nd cycle 의 *운영 데이터* 후속 식별.
- 범위: 영향 symbol 식별 절차, 3rd cycle 의 영향 후보 (현재 codebase 의 public API 재스캔), 운영 데이터 기반 후속.
- 대상 독자: 워크플로우 설계자, deprecation 정책 운영자, 후속 release reviewer.
- **상태: draft (placeholder, 1st/2nd cycle 완료, 3rd cycle 영향 후보 식별 필요)**
- 최종 수정일: 2026-07-09
- 관련 문서: [`./v0_9_0_deprecation_policy_spec.md`](./v0_9_0_deprecation_policy_spec.md), [`./ADR-001-source-state-knowledge-3-layer-separation.md`](./ADR-001-source-state-knowledge-3-layer-separation.md)

- **Status**: Draft (placeholder)
- **Date**: 2026-07-03
- **Supersedes**: —
- **Superseded by**: —
- **Resolves 후속**: 3rd cycle 영향 symbol 의 정식 식별 (운영 데이터 후속)

## Context

`standard_ai_workflow` 의 deprecation 정책 (v0.9.0 spec, "1 release DeprecationWarning → 1 release removal") 의 운영 이력:

### 1st cycle (v0.9.0 → v0.9.3 → v0.10.0)

- **대상 symbol**: `phishing_federation_v4.fetch_federated_phishing_urls_v4`
- **DeprecationWarning 시점**: v0.9.0 (2026-06-18)
- **Removal 시점**: v0.10.0 (SemVer major, 2026-06-26)
- **운영 검증 결과**: 0 consumer 영향 (v0.9.0 + v0.9.1 + v0.9.2 의 warning log 빈도 0)

### 2nd cycle (v0.9.3 → v0.10.0)

- **대상 symbol**: `phishing_federation_v4.build_default_sources_v4`
- **DeprecationWarning 시점**: v0.9.3 (2026-06-19)
- **Removal 시점**: v0.10.0 (SemVer major, 2026-06-26, 1st cycle 와 동시)
- **운영 검증 결과**: dispatcher (`cmd_federate`) 가 이미 consolidated 호출 → v4 module 자체가 dead code 신호. consumer 영향 0.

### 3rd cycle 후보 식별 필요성

**현재 codebase 의 영향 symbol 재스캔 결과 (v0.11.24 시점)**:

- `phishing_federation_v4` module 전체가 v0.10.0 에서 제거됨. 후속 cycle 의 후보가 *동일 module* 내에서 식별 안 됨.
- 다른 module 의 public symbol 중 deprecation 후보:
  - 본 시점 codebase 재스캔 (grep 기반):
    - `DeprecationWarning` literal 을 emit 하는 call site: 0개 (1st/2nd cycle 후 모두 제거)
    - `warnings.warn(..., DeprecationWarning)` 호출: 0개
    - `__all__` 정의 module 의 deprecated marker 가 있는 symbol: 0개
  - 즉, **현재 codebase 는 3rd cycle 의 영향 symbol 이 *부재***.

이는 의도된 결과:
- 1st/2nd cycle 가 *동일 module* (phishing_federation_v4) 의 모든 v4 API 를 cover.
- v0.10.0 의 SemVer major 에서 module 전체 제거.
- 후속 public API surface 에는 *deprecated* marker 가 *의도적으로 0개*.

### 3rd cycle 영향 후보의 잠재적 source

1. **후속 major release 의 legacy symbol**: v1.0.0 milestone 진입 시 stable guarantee 의 *legacy symbol* 가 식별되면 3rd cycle 적용 가능. 본 시점은 v1.0.0 진입 평가 단계.
2. **internal helper 의 public exposure**: `workflow_kit.common.*` 의 helper 중 일부가 외부에서 import 가능. *unstable* marker 가 있을 수 있으나 현재 codebase 의 `__all__` 정의 module 에 명시적 *deprecated* symbol 0개.
3. **운영 데이터 기반**: consumer 가 *implicit* 으로 사용하던 helper 가 major release 에서 제거될 위험. v0.10.0 ~ v0.11.24 의 consumer metrics 에서 *deprecated pattern* 발견 시 3rd cycle 적용.

## Decision

**본 ADR-007 은 3rd cycle 영향 식별의 placeholder**. 후속 영향 symbol 식별 시 본 ADR 의 본문 작성.

### placeholder (회고 자리)

3rd cycle 영향 후보의 3가지 source (위 §Context 의 #1, #2, #3) 중 어느 것이든 *영향 symbol* 이 식별되면:
1. 본 ADR 의 본문에 symbol / module / cycle 진행 (v0.X.Y 에 DeprecationWarning 시작) 명시.
2. v0.X.Y+1 에 removal (SemVer major 시).
3. 운영 검증 결과 (consumer warning log 빈도, migration 비용) 후속 release 의 본문에 보강.

### 영향 symbol 부재 시의 정공법

3rd cycle 영향 후보가 *식별 안 됨* 상태가 지속되면:
- 본 ADR 의 status 를 `accepted (no-op)` 로 갱신 (즉, "3rd cycle 는 운영상 부재").
- 다음 deprecation cycle 은 v1.0.0 milestone 진입 시점의 *legacy symbol audit* 후 식별.

## Consequences

### Positive

- **deprecation 정책 운영 추적 anchor**: 1st/2nd cycle 완료 + 3rd cycle 영향 식별 절차의 *문서화된 자리*. 후속 영향 symbol 발견 시 본 ADR 의 본문 작성으로 즉시 갱신.
- **cyclical discipline**: 매 major release 시 본 ADR 을 확인하는 *discipline anchor*. `__all__` 정의 module 의 `__deprecated__` marker 와의 cross-check 가능.
- **cross-ref 정합**: ADR-001 (3-layer 분리) 와 ADR-002 (Pydantic v2 contract) 의 본문 정합 유지.

### Negative / Trade-offs

- **placeholder 의 단기 한계**: 본 ADR-007 은 본 release 에 정합성 검증 안 됨 (영향 symbol 부재). *no-op accepted* 전환 시 본 ADR 의 본문 작성.
- **consumer-side observability**: downstream consumer 가 *implicit* 으로 사용하던 helper 의 deprecation 은 *consumer metrics* 가 부족할 경우 silently 누락 가능. consumer feedback channel (GitHub Issues + `feedback` label) 의 운영이 본 ADR 의 *근거 data*.

### 후속 작업

- v1.0.0 milestone 진입 평가 시 본 ADR 의 본문 작성 (legacy symbol audit 결과).
- consumer feedback (`feedback` label) 의 운영 — 매 release 의 consumer metrics 검토 시 본 ADR 의 영향 symbol 후보 갱신.
- 매 major release 시 본 ADR 의 status 확인 (placeholder → accepted no-op, 또는 본문 작성).

## References

- 1st/2nd cycle 정공법: [./v0_9_0_deprecation_policy_spec.md](./v0_9_0_deprecation_policy_spec.md)
- 1st cycle release note: [../../workflow-source/releases/Beta-v0.9.0.md](../../workflow-source/releases/Beta-v0.9.0.md) (chapter 2 §결제)
- 2nd cycle release note: [../../workflow-source/releases/Beta-v0.9.3.md](../../workflow-source/releases/Beta-v0.9.3.md)
- Removal release note (1st+2nd 동시 종료): [../../workflow-source/releases/Beta-v0.10.0.md](../../workflow-source/releases/Beta-v0.10.0.md) (SemVer major)
- 3-layer 분리 정합: [./ADR-001-source-state-knowledge-3-layer-separation.md](./ADR-001-source-state-knowledge-3-layer-separation.md)
- ADR-006 (Memory Index retrospective 자리): [./ADR-006-memory-index-retrospective.md](./ADR-006-memory-index-retrospective.md)