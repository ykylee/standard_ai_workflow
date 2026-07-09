# ADR-002: Pydantic v2 contract v1 외부 spec + Python helper 결합 채택

- 문서 목적: orchestrator ↔ sub-agent contract v1 의 외부 markdown spec + Pydantic v2 helper 결합 정책 rationale 정식 기록.
- 범위: 외부 spec 구조 (§1-§8), Python enforcement helper 책임, Mavis 측 wire 의무, 후속 결정 인용.
- 대상 독자: maintainer, Mavis/Mavis engine 통합자, contract 진화 담당자.
- 상태: Accepted (v0.5.4, 이후 v0.5.6 / v0.5.7 / v0.5.10 / v0.5.11 로 incremental 발전)
- 최종 수정일: 2026-07-09
- 관련 문서: [`./ADR-001-source-state-knowledge-3-layer-separation.md`](./ADR-001-source-state-knowledge-3-layer-separation.md), [`./README.md`](./README.md), [`../../workflow-source/core/orchestrator_subagent_contract_v1.md`](../../workflow-source/core/orchestrator_subagent_contract_v1.md), [`../../workflow-source/core/orchestrator_contract_v1_wire_guide.md`](../../workflow-source/core/orchestrator_contract_v1_wire_guide.md)

- **Status**: Accepted (v0.5.4, 이후 v0.5.6 / v0.5.7 / v0.5.10 / v0.5.11 로 incremental 발전)
- **Date**: 2026-05-04 (v0.5.4), updated 2026-05-15 (v0.5.6), 2026-06-01 (v0.5.7), 2026-06-08 (v0.5.10), 2026-06-09 (v0.5.11)
- **Supersedes**: —
- **Superseded by**: —

## Context

v0.5.3 까지 orchestrator ↔ sub-agent 간 통신 contract 가 (a) docstring 으로만 정의되어 있거나, (b) Pydantic v1 모델로 in-code 정의되어 있었다. 이로 인해:

1. **외부 consumer 가 spec 을 알기 어려움**: docstring 은 IDE hover 로만 보이고, external document 로 export 되지 않음. Pydantic 모델은 import 해야만 보임.
2. **강제력 부족**: docstring 만으로는 enforcement 가 안 됨. orchestrator 가 spec 위반 응답을 그대로 downstream 에 흘려보내는 경우를 자동 검출할 수단이 없었음.
3. **spec 변경 추적 어려움**: docstring 은 git diff 로 추적되지만, 외부 spec (markdown) 보다는 가독성이 낮음. spec 변경 PR 의 리뷰 비용이 높았음.
4. **Pydantic v1 의 한계**: discriminated union, strict mode, JSON schema 자동 생성이 부족. v0.5.4 시점에 v2 가 stable.

## Decision

contract v1 을 **(a) 외부 markdown spec + (b) Pydantic v2 기반 Python enforcement helper** 의 결합으로 정의한다.

### (a) 외부 markdown spec

`workflow-source/core/orchestrator_subagent_contract_v1.md` 가 SSOT. 다음을 포함:

- §1 동기, §2 적용 범위, §3 역할 (4종)
- §4 위임 입력 스키마 (single + multi-component fan-out)
- §5 위임 출력 스키마 (single + fan-in)
- §6 위임 가능/불가 카탈로그 (MUST/SHOULD delegate / MUST NOT)
- §6.5 Mavis engine hook (P0 enforcement, v0.5.11 추가)
- §7 에러/폴백 정책
- §8 검증 시나리오

각 절은 필드 정의, 타입, 필수 여부, 예시 JSON 을 포함. wire 가이드 (`orchestrator_contract_v1_wire_guide.md`) 가 spec 의 §2/§3 reference code 를 Python 으로 보여줌.

### (b) Python enforcement helper

`workflow_kit/contract_v1/` 패키지가 spec 을 enforce:

- `output_validator.py`:
  - `validate_output(payload, expected_delegation_id=...)` → `OutputValidationResult(is_valid, errors, warnings)` (raise 안 함)
  - `validate_fanin_output(payload, expected_parent_delegation_id=...)` → §5.2 fan-in envelope 검증
  - `enforce_subagent_response(...)` / `enforce_fanin_response(...)` (v0.5.11): thin wrapper. invalid 시 `ValueError` raise
- `delegator.py`:
  - `choose_role(task)` → `DelegationDecision(role, must_not_delegate, delegation_id, ...)`
  - `choose_roles(task, strict=True)` → 배치 위임 결정 (multi-component)
  - `recommend_model_tier(task)` → main / small 자동 결정 (v0.5.7)

### Mavis 측 wire 의무 (v0.5.11 §6.5)

`delegate_to_subagent` / `fanout_to_subs` 함수는 sub-agent 응답 수신 직후 helper (`enforce_subagent_response` / `enforce_fanin_response`) 호출 의무. opt-out 없음 (P0 enforcement). 위반 시 `ValueError` propagate.

## Consequences

### Positive

- **외부 consumer 가 spec 을 markdown 으로 즉시 읽음**: Mavis / Mavis / OpenCode / Gemini CLI 통합자가 import 없이 spec 검토 가능.
- **자동 enforce**: Pydantic v2 strict mode + custom validation 으로 응답 envelope 의 모든 필드/타입/enum/필수여부 자동 검사. v0.5.6 부터 P0 enforcement (이전엔 docstring-only).
- **spec 변경 추적 가능**: spec 변경 PR 의 review 가 markdown diff 로 명확. 후속 enforcement helper 변경이 spec 과 1:1 대응.
- **JSON schema 자동 생성**: `workflow_kit.common.output_contracts` 가 runtime output contract map 을 export. downstream consumer 가 JSON schema 로 응답 검증 가능.
- **Pydantic v2 의 strict mode + discriminated union + model_validator** 활용 가능.

### Negative / Trade-offs

- **spec duplication 위험**: markdown spec 과 Pydantic 모델이 둘 다 정의되므로, 한쪽만 갱신 시 drift 발생. 완화: `check_contract_v1_*` smoke test 가 양쪽을 cross-check.
- **enforcement helper 가 spec 의 subset 일 수 있음**: markdown spec 의 모든 규칙이 helper 로 enforce 되는 것은 아님 (e.g. §7.4 "재위임 1회" 정책은 caller 책임). spec → helper 의 partial mapping 이 자연스러우나, helper 가 enforce 안 하는 규칙은 docstring + 주석으로 명시.
- **Pydantic v2 의 의존성**: workflow_kit 이 pydantic>=2.0 필요. v0.5.4 시점에 모든 target Python 버전에서 available.

### 후속 결정의 인용

본 ADR 이 가능케 한 후속 결정들:

- **v0.5.6**: P0 enforcement 으로 `output_validator.validate_output` + `delegator.choose_role` 자동 enforce. spec 위반 시 `DelegationRejected` raise.
- **v0.5.7**: multi-component fan-out/in 지원. `choose_roles` (배치), `validate_fanin_output` (§5.2), `recommend_model_tier` (main/small 자동).
- **v0.5.10**: `choose_roles` 가 sub.delegation_id 에 parent prefix (`{parent_id}-st-N`) 강제.
- **v0.5.11**: Mavis engine hook (§6.5) — `enforce_subagent_response` / `enforce_fanin_response` thin wrapper. invalid 시 `ValueError` raise. opt-out 없음.

## References

- `workflow-source/core/orchestrator_subagent_contract_v1.md` — 외부 spec
- `workflow-source/core/orchestrator_contract_v1_wire_guide.md` — wire 가이드 (Mavis 측 reference)
- `workflow_kit/contract_v1/output_validator.py` — `validate_output`, `validate_fanin_output`, `enforce_subagent_response`, `enforce_fanin_response`
- `workflow_kit/contract_v1/delegator.py` — `choose_role`, `choose_roles`, `recommend_model_tier`
- Beta v0.5.4 release note
- `check_contract_v1_delegator.py`, `check_contract_v1_multi_component.py`, `check_contract_v1_output_validator.py`, `check_contract_v1_roundtrip.py`, `check_contract_v1_role_mapping.py`, `check_contract_v1_direct_only.py` — 6 종의 contract v1 회귀 test
