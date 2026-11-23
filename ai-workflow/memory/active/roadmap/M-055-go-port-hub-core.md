---
id: M-055
title: 2.x 전면 Go 전환 — implementation S2-b (중앙 허브 코어 — db · assets · store · tools · httpapi · mcpserver)
sdlc_phase: implementation
status: done
order: 55
parallel_allowed:
  - M-007
  - M-028
  - M-039
deliverables:
  - hub-go/internal/db/
  - hub-go/internal/store/
  - hub-go/internal/httpapi/
  - hub-go/internal/mcpserver/
  - workflow-source/tests/check_go_assets_sync.py
goals: [G1, G3, G5]
---

# M-055 — S2-b 중앙 허브 코어 (`db` · `assets` · `store` · `tools` · `httpapi` · `mcpserver`)

설계 정본: [`hub_go_spec.md`](../../../../workflow-source/core/hub_go_spec.md) §2 · §2.1 · §5.3 · §5.4 · §9 DG2~DG5 (요구 R25 · R28 · R32 · Q1~Q5). `modernc.org/sqlite` 로 판 1~12 SQLite 스키마·이관·온라인 백업을 구현하고(이관 SQL 문자열은 Python 과 바이트 대조), 내장 자산 동기화(`check_go_assets_sync`), 저장 계층(`internal/store`), 도구 60종 입구(`internal/tools`), `net/http` (`internal/httpapi`), stateless JSON MCP (`internal/mcpserver`), `serve` · `backup` · `admin` 을 구현해 `check_hub_core` 가 Python 과 Go 양쪽에서 10/10 통과하게 만든다.

## WBS

- **WBS-55.1** `hub-go/internal/db` (SQLite `modernc.org/sqlite` · 이관 판 1~12 SQL 복사 · 이관 전 사본 · 온라인 백업) + `hub-go/internal/assets` + `check_go_assets_sync.py` — 산출물: `hub-go/internal/db/`, `workflow-source/tests/check_go_assets_sync.py`
- **WBS-55.2** `hub-go/internal/store` (`HubError` · `gitkey` · `Principal`/`Ctx` · 비밀 스캔 · 멱등 `applied_request` · 등록/콜사인/토큰/task CRUD/맡기/진행/커밋/이력) — 산출물: `hub-go/internal/store/`
- **WBS-55.3** `hub-go/internal/{tools,httpapi,mcpserver}` + `cmd/workflow-hub` (`serve` · `backup` · `admin`) + `check_hub_core` `WORKFLOW_HUB_IMPL=go` 10/10 통과 — 산출물: `hub-go/internal/httpapi/`, `hub-go/internal/mcpserver/`
