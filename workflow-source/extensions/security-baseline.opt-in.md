# Security Baseline Opt-In Prompt

- 문서 목적: v0.7.0 의 security-baseline extension 의 opt-in prompt 정의. workflow 시작 시 1회 표시.
- 범위: opt-in question 형식, 응답 처리, baseline_status.md 형식
- 관련 문서: [`./security-baseline.md`](./security-baseline.md) (rules)

## Question: Security Baseline Extension

본 workflow 에 AIDLC 차용 security baseline rule (SEC-WF-01 ~ 06) 을 enforce 하시겠습니까?

A) Yes — enforce all SEC-WF rules as blocking constraints (recommended for production-grade applications)

B) No — skip all SEC-WF rules (suitable for PoCs, prototypes, experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]:

## Response Format

답변은 `ai-workflow/memory/active/security_baseline_status.md` 에 저장:

```markdown
# Security Baseline Status

- **Enabled**: <yes|no>
- **Decided At**: <ISO 8601>
- **Decided By**: <user|orchestrator>
- **Reason**: <optional free text>

## Extension Configuration

| Extension | Enabled | Decided At |
|---|---|---|
| security-baseline | yes | 2026-06-12T22:30:15Z |
```

## Default 정책

- **신규 project (Greenfield)**: 기본값 = "A) Yes" (production 권장)
- **Brownfield / 기존 project**: opt-in prompt 가 *없음* (이미 결정된 status 사용)
- **CI/CD**: opt-in prompt 표시 안 함, `security_baseline_status.md` 의 기존 값 사용

## 적용 (v0.7.1+ follow-up)

`workflow_kit/skills/session-start/scripts/run_session_start.py` 에 opt-in prompt 통합:
- `security_baseline_status.md` 가 없으면 prompt 표시
- 응답을 즉시 write 후 compliance check 시작
- enabled 시: stage completion message 에 Security Compliance 섹션 자동 추가

## Note

opt-in prompt 자체는 본 commit 범위 외 (v0.7.1+ follow-up). 본 file 은 spec 정의만. 실제 prompt 통합은 session-start runtime 변경 시.
