# ADR-007: Deprecation 3rd Cycle Candidate Identification (Accepted no-op, v0.15.4+)

- 문서 목적: standard_ai_workflow 의 deprecation 정책 운영 안정화 추적. 1st + 2nd cycle 의 *운영 데이터* 후속 식별.
- 범위: 영향 symbol 식별 절차, 3rd cycle 의 영향 후보 (현재 codebase 의 public API 재스캔), 운영 데이터 기반 후속.
- 대상 독자: 워크플로우 설계자, deprecation 정책 운영자, 후속 release reviewer.
- **상태: accepted (no-op) — v0.15.4+ codebase re-scan 결과, 3rd cycle 영향 symbol 부재 확인 (infrastructure only, 실제 mark 0개). 후속 영향 식별 시 본 ADR 본문 작성.**
- 최종 수정일: 2026-07-21
- 관련 문서: [`./v0_9_0_deprecation_policy_spec.md`](./v0_9_0_deprecation_policy_spec.md), [`./ADR-001-source-state-knowledge-3-layer-separation.md`](./ADR-001-source-state-knowledge-3-layer-separation.md)

- **Status**: Accepted (no-op)
- **Date**: 2026-07-03 (initial), 2026-07-17 (v0.15.4 close-out)
- **Supersedes**: —
- **Superseded by**: —
- **Resolves 후속**: v1.0.0 진입 평가 시점의 legacy symbol audit (현 시점 대기)

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

**v0.15.4+ codebase 재스캔 결과 (ADR-007 close-out)**:

v0.11.24 시점 (placeholder 작성) 의 재스캔 결과 (`DeprecationWarning` 0건, `warnings.warn(..., DeprecationWarning)` 0건, `__deprecated__` marker 0건) 가 v0.15.4 시점에도 유지되는지 검증. 검증 결과:

- `DeprecationWarning` literal 을 *emit* 하는 call site: **2건 (모두 `workflow_kit/common/decorators.py:v0_7_4_deprecated` decorator 본체 안)**
- `__deprecated__ = True` marker 설정: **2건 (모두 `workflow_kit/common/decorators.py` 안, decorator 본체)**
- `@v0_7_4_deprecated` decorator 의 *실제 사용처*: **0건** — decorator 는 정의만 돼 있고 apply 된 symbol 이 0개
- 즉, **infrastructure (deprecation 표시 *수단*) 는 존재하지만 *현실적으로 mark 된* symbol 은 부재**

이는 의도된 결과:
- 1st/2nd cycle 가 *동일 module* (phishing_federation_v4) 의 모든 v4 API 를 cover.
- v0.10.0 의 SemVer major 에서 module 전체 제거.
- 후속 public API surface 에는 *deprecated* marker 가 *의도적으로 0개*.
- v0.7.4+ 의 deprecation decorator (`v0_7_4_deprecated`) 가 infrastructure 로 존재하지만, 적용된 *concrete symbol* 이 0건 — 즉, deprecation *정책* 과 *정책 적용 surface* 가 분리돼 있음.

**v0.15.4+ close-out (smoke `check_deprecation_3rd_cycle_v0_15_4.py` 3/3 PASS)**:
- case 1: `DeprecationWarning` emit 이 infrastructure (decorators.py) 안에서만 emit — non-infrastructure 0건
- case 2: `__deprecated__ = True` marker 가 infrastructure 안에서만 설정 — non-infrastructure 0건
- case 3: `@v0_7_4_deprecated` 의 *실제 apply* 0건 (docstring usage example 제외)

### 3rd cycle 영향 후보의 잠재적 source

1. **후속 major release 의 legacy symbol**: v1.0.0 milestone 진입 시 stable guarantee 의 *legacy symbol* 가 식별되면 3rd cycle 적용 가능. 본 시점은 v1.0.0 진입 평가 단계.
2. **internal helper 의 public exposure**: `workflow_kit.common.*` 의 helper 중 일부가 외부에서 import 가능. *unstable* marker 가 있을 수 있으나 현재 codebase 의 `__all__` 정의 module 에 명시적 *deprecated* symbol 0개. v0.15.4 re-scan 에서도 동일.
3. **운영 데이터 기반**: consumer 가 *implicit* 으로 사용하던 helper 가 major release 에서 제거될 위험. v0.10.0 ~ v0.15.4 의 consumer metrics 에서 *deprecated pattern* 발견 시 3rd cycle 적용.

## Decision

**본 ADR-007 은 v0.15.4+ `accepted (no-op)` 로 종결**. v0.11.24 ~ v0.15.4 시점 codebase 의 *2 차례* 재스캔 결과, 3rd cycle 영향 symbol 이 *의도적으로 부재* 함이 확인됨.

### 종결의 rationale

- 1st/2nd cycle (v0.9.0 ~ v0.10.0) 가 phishing_federation_v4 module 의 모든 v4 API 를 cover.
- v0.10.0 의 SemVer major 에서 module 전체 제거.
- 후속 codebase (v0.10.0 ~ v0.15.4) 는 *deprecation 표시* 자체를 사용하지 않음 (consumer feedback channel 의 deprecation request 0건).
- v0.7.4+ 의 `v0_7_4_deprecated` decorator 는 *infrastructure* 로만 존재 (apply 0건).

### 후속 영향 식별 시의 정공법

3rd cycle 영향 후보의 3가지 source (§Context 의 #1, #2, #3) 중 어느 것이든 *영향 symbol* 이 식별되면:
1. 본 ADR 의 본문에 symbol / module / cycle 진행 (v0.X.Y 에 DeprecationWarning 시작) 명시.
2. v0.X.Y+1 에 removal (SemVer major 시).
3. 운영 검증 결과 (consumer warning log 빈도, migration 비용) 후속 release 의 본문에 보강.
4. status 를 `accepted (no-op)` → `reopened` 로 갱신.

## Consequences

### Positive

- **deprecation 정책 운영 추적 anchor**: 1st/2nd cycle 완료 + 3rd cycle *운영상 부재* 가 *문서화된 자리*. 후속 영향 symbol 발견 시 본 ADR 의 본문 작성으로 즉시 갱신 가능.
- **cyclical discipline**: 매 major release 시 본 ADR 을 확인하는 *discipline anchor*. v0.15.4+ 부터는 smoke `check_deprecation_3rd_cycle_v0_15_4.py` 3/3 PASS 로 정합성 자동 검증. `__all__` 정의 module 의 `__deprecated__` marker 와의 cross-check 가능.
- **close-out 의 verifiable anchor**: status `accepted (no-op)` 는 *의도적 부재* 의 explicit declaration 이며, 후속 영향 symbol 등장 시 status 를 `reopened` 로 갱신하는 *trigger 명시*.
- **cross-ref 정합**: ADR-001 (3-layer 분리) 와 ADR-002 (Pydantic v2 contract) 의 본문 정합 유지.

### Negative / Trade-offs

- **consumer-side observability**: downstream consumer 가 *implicit* 으로 사용하던 helper 의 deprecation 은 *consumer metrics* 가 부족할 경우 silently 누락 가능. consumer feedback channel (GitHub Issues + `feedback` label) 의 운영이 본 ADR 의 *근거 data*. v0.15.4 시점 consumer feedback 0건으로 부재 추정.
- **infrastructure vs surface 분리**: v0.7.4+ 의 `v0_7_4_deprecated` decorator 는 정의만 존재 (apply 0건). infrastructure 와 surface 가 분리된 상태가 *의도된* 결과인지, *누락된* 결과인지 후속 audit 필요.

### 후속 작업 (close-out 상태)

- v1.0.0 milestone 진입 평가 시 본 ADR 의 status `accepted (no-op)` → `reopened` 가능성 검토 (legacy symbol audit 결과에 따라).
- consumer feedback (`feedback` label) 의 운영 — 매 release 의 consumer metrics 검토 시 본 ADR 의 영향 symbol 후보 갱신.
- 매 major release 시 smoke `check_deprecation_3rd_cycle_v0_15_4.py` 회귀 검증 (deprecation policy 의 discipline anchor).
- consumer feedback (`feedback` label) 의 운영 — 매 release 의 consumer metrics 검토 시 본 ADR 의 영향 symbol 후보 갱신.
- 매 major release 시 smoke `check_deprecation_3rd_cycle_v0_15_4.py` 회귀 검증 (deprecation policy 의 discipline anchor).

## References

- 1st/2nd cycle 정공법: [./v0_9_0_deprecation_policy_spec.md](./v0_9_0_deprecation_policy_spec.md)
- 1st cycle release note: [../../workflow-source/releases/Beta-v0.9.0.md](../../workflow-source/releases/Beta-v0.9.0.md) (chapter 2 §결제)
- 2nd cycle release note: [../../workflow-source/releases/Beta-v0.9.3.md](../../workflow-source/releases/Beta-v0.9.3.md)
- Removal release note (1st+2nd 동시 종료): [../../workflow-source/releases/Beta-v0.10.0.md](../../workflow-source/releases/Beta-v0.10.0.md) (SemVer major)
- 3-layer 분리 정합: [./ADR-001-source-state-knowledge-3-layer-separation.md](./ADR-001-source-state-knowledge-3-layer-separation.md)
- ADR-006 (Memory Index retrospective 자리): [./ADR-006-memory-index-retrospective.md](./ADR-006-memory-index-retrospective.md)