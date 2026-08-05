# Read-Only MCP Bundle Manifest

- 문서 목적: 첫 번째 읽기 전용 MCP 도구 번들의 매니페스트 및 예시 정의
- 범위: 번들 스펙, 하네스별 예시
- 대상 독자: AI 에이전트, 개발자
- 상태: stable
- 최종 수정일: 2026-05-02
- 관련 문서: [README.md](./README.md)

> **이 자리에 있던 JSON 사본은 제거했다 (2026-08-05).**
>
> 생성 산출물을 문서에 붙여 두면 반드시 갈라진다 — 실제로 갈라져 있었다:
> `tool_count: 12`(현재 13), `tool_version: "v0.4.1-beta"`(현재 `v1.0.0-beta"`),
> `apply_robust_patch` 누락, 그리고 §6.2 로 제거된 `transport_ready` 잔존.
> 아무도 이 블록이 틀렸다는 것을 몰랐다.
>
> 정본은 [`../schemas/read_only_harness_mcp_examples.json`](../schemas/read_only_harness_mcp_examples.json)
> 이고, 생성기는 [`../scripts/generate_read_only_harness_mcp_examples.py`](../scripts/generate_read_only_harness_mcp_examples.py),
> 커밋본이 생성기 출력과 같은지는 `tests/check_read_only_harness_mcp_examples.py` 가 강제한다.

번들이 무엇을 담는지 요약하면:

- `tool_names` / `tool_count` — registry(`workflow_kit/server/read_only_registry.py`)가 정본
- `harness_examples.<harness>` — Codex(TOML) / OpenCode(JSONC) **수동 검토용 draft**
  (`apply_mode: manual_review_only`). 실제 활성 설정은 `bootstrap --enable-mcp` 가 emit 한다.
- `transport_phase` — 그 예시가 가리키는 bridge 의 구현 단계
  (`core/read_only_mcp_transport_promotion.md` §1.3 의 세 축)
