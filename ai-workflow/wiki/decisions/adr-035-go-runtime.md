---
type: decision
status: proposed
adr_id: ADR-035
decided_at: 2026-11-22
alternatives_considered: [keep-python, relay-only-go, hub-frontend-go-python-sidecar, rust-runtime]
related_pages: [decisions/adr-033-workflow-hub, decisions/adr-034-hub-orchestration]
created: 2026-11-22
updated: 2026-11-22
r9_skip: true
---

# ADR-035: 2.x 런타임(허브 · 공유 판정 · PC 중계)을 Go 로 옮긴다

## Status

**Proposed** (2026-11-22, M-050/WBS-50.3). 범위 결정은 소유자가 concept 에서 내렸다 (2026-11-22 — R1 = D 전면 Go, R2 Go, R3 이 ADR, R4 서명은 실측 뒤, R5 `mcp` 2.x).
concept: [`runtime-port-review-2026-11.md`](../../../docs/planning/runtime-port-review-2026-11.md) §11. 요구: [`go-port-requirements-2026-11.md`](../../../docs/planning/go-port-requirements-2026-11.md) (R25~R35, 정할 것 Q1~Q6).
Accepted 는 requirements 의 Q1~Q6 이 정해지고 design 이 끝난 뒤.

## Context

- 2.x 허브(ADR-033) · 오케스트레이션(ADR-034)은 Python 이다 — PURPOSE 가 'Python 외 runtime' 을 제외 영역으로 두고, hub_spec R0.3 이 허브 · 클라이언트 · 부트스트랩 원문을 Python 으로 정했다. 예외는 VS Code 확장 껍데기뿐이다.
- 소유자 (2026-11-22): 다음 판에서 Go 또는 Rust 로 전환을 고려 → concept 실측 뒤 **전면 Go** 결정.
- 실측 (concept §2, Linux): Go 공식 MCP SDK `go-sdk` v1.8.0 · Rust `rmcp` 3.11.0 탐침 서버 모두 Claude Code 2.1.330 · Codex 0.167.1 이 붙어 도구를 불렀다. Go 는 정적 단일 바이너리 12.6 MB · RSS 12.6 MB · Windows 크로스 빌드에 추가 도구가 없다. Python 허브는 RSS 79 MB(도구 74).
- 이식량 (concept §3): 허브 7.0k 줄 + **공유 판정 19.3k 줄** + 중계 909 줄. 허브는 1.x 판정 함수를 그대로 부른다 (hub_spec §1-6) — 1.x(`release/1.x`, 2028-07-20 까지)는 Python 그대로다.

## Decision

1. **허브 · 공유 판정 · PC 중계를 Go 로 옮긴다.** 언어는 Go (concept §5 — 크로스 빌드 · 정적 링크 · SDK 안정판).
2. **바깥 계약을 바꾸지 않는다** — 도구 · HTTP 경로 · DB 판과 표 · 1.x 생성물 형식 · 진입 파일 렌더 바이트 (요구 R25 · R26 · R29). Go 허브는 Python 허브의 DB 를 그대로 연다.
3. **같은 답을 검사로 고정한다** — 판정은 Python · Go 차분 검사 (R27), 허브 전체는 기존 허브 검사를 두 구현에 돌리는 적합성 검사 (R28). 불일치 0 이 전환 조건이다.
4. **단계로 옮긴다** — S1 중계 → S2 허브 그림자 운영 → S3 전환 → S4 Python 판 은퇴 (R30).
5. **PURPOSE 제외 영역의 예외를 2.x 런타임(Go)으로 넓힌다.** hub_spec R0.3 을 개정한다 (R35). 1.x 는 Python 그대로.

## Consequences

- 같은 판정 규칙이 이행 기간 · 1.x 지원 기간에 **두 언어**에 있다. 스펙이 정본이고, 규칙 변경은 두 구현 · corpus 를 같은 커밋에서 바꾼다 (R33.3). 이 저장소가 겪은 '복제는 갈라진다' 를 차분 검사가 막아야 한다 — 차분 검사가 꺼지면 이 결정의 전제가 무너진다.
- 개발 호스트에 Go 도구 사슬이 필요해진다. 게이트는 하나(Python 러너)로 두고 Go 검사를 감싼다 (R32).
- 배포가 wheel 에서 OS별 바이너리로 바뀐다 — 설치 · 실행 방법이 바뀌므로 판은 major 후보 (요구 Q1). Windows · macOS 서명 · 공증 비용은 실측 뒤 (R31.2).
- 허브 메모리 · 기동이 줄고 단일 바이너리로 배포되지만, 허브 규모에서 Python 병목이 측정된 적은 없다 — 이 결정의 근거는 성능보다 **배포 · 런타임 단일화**다.

## Alternatives

| 대안 | 기각 이유 |
|---|---|
| Python 유지 | 소유자가 전환을 결정 |
| 중계만 Go (concept 권고 B) | 소유자가 전면 전환 선택 — 허브까지 단일 바이너리 · 런타임 단일화 |
| 허브 앞단만 Go + 판정 Python 사이드카 (C) | 런타임 둘 · 프로세스 둘 — 배포가 무거워진다 |
| Rust | 바이너리 · 메모리는 우위(3.4 MB · 5.9 MB)지만 Windows 빌드에 MSVC/xwin 이 필요하고 SDK 주판이 자주 바뀐다 (concept §5) |
