---
id: M-060
title: 미등록 하네스 제보와 승인 등록 흐름
sdlc_phase: implementation
status: done
order: 60
parallel_allowed:
  - M-007
  - M-028
  - M-039
  - M-057
  - M-059
deliverables:
  - docs/planning/unknown-harness-intake-requirements-2026-11.md
  - workflow-source/core/hub_harness_registry_spec.md
  - workflow-source/workflow_kit/hub/
  - hub-go/internal/
  - hub-go/internal/assets/static/
goals: [G1, G3, G5]
---

# M-060 — 미등록 하네스 제보와 승인 등록 흐름

허브가 모르는 하네스를 세션에서 만났을 때, 클라이언트가 감지한 비밀 없는
호환성 정보를 제출한다. 제보는 검토 대기 상태로만 저장하고, 사람은 웹 허브에서
승인한다. 담당자 명부는 하네스 등록과 독립적으로 관리하며 한 하네스에 여러
사람을 연결할 수 있다. 승인 메타데이터와 셋업 adapter 지원은 분리한다.

## WBS

- **WBS-60.1** 제보 정보·웹 승인·별도 사람 명부·등록 수명주기 정의 및 Python/Go 구현 — 산출물: 계약 문서, DB/API/MCP/UI 동작, 최초 등록의 사람 담당자 지정
- **WBS-60.2** 민감 정보 차단·권한·멱등성·런타임 parity 검증과 운영 안내 — 산출물: 회귀 증거, Python/Go 동등 계약, 웹 검토 안내
