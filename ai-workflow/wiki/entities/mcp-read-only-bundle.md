---
type: entity
status: active
last_ingested_from: workflow-source/core/workflow_mcp_candidate_catalog.md
related_pages: [entities/standard-ai-workflow, entities/workflow-kit, decisions/adr-003-read-only-mcp-default, concepts/mcp-transport]
created: 2026-06-12
updated: 2026-08-12
---

# MCP Read-Only Bundle (13 도구)

`workflow_kit/server/read_only_registry.py` 의 `READ_ONLY_TOOL_SPECS` 에 등록된 **13 도구 MCP bundle** (read-only 11 + write-capable 2). [[decisions/adr-003-read-only-mcp-default]] 정책의 실체이며, [[entities/workflow-kit]] 의 `workflow_kit/server/` 모듈이 통합 entrypoint 를 제공한다.

## Role

default 는 read-only — 도구 대부분은 외부 상태를 **조회** 하거나 **초안** 만 생성한다. **예외 2종** (`apply_robust_patch` / `rotate_workflow_logs`) 은 파일시스템을 실제로 변경하며, v1.1.7 부터 descriptor 가 `readOnlyHint=false` 로 정직하게 광고한다 (ADR-003 v1.1.7 개정, TASK-2026-08-11-main-024). **v1.1.8 부터는 별도 bundle 로 분리** — 서버 `--bundle read-only|write|all` 선택자, write 는 `workflow_write_bundle` 로 명시 opt-in (TASK-2026-08-12-main-003).

| # | 속성 | 값 |
|---|---|---|
| 도구 수 | 13 (registry `READ_ONLY_TOOL_SPECS`) | v0.5.0 의 6종에서 점진 확장 |
| Transport | dual-mode | `jsonrpc-bridge` (default) / `stdio-sdk` (experimental) |
| Entry point | `python3 -m workflow_kit.server.read_only_jsonrpc --stdio-lines` | `read_only_jsonrpc` / `read_only_mcp_sdk` 두 모듈 |
| Write 가능 도구 | **2** (`apply_robust_patch`, `rotate_workflow_logs`) | registry `WRITE_CAPABLE_TOOL_NAMES` 사실 목록. `create_*` 3종은 **draft 만** 반환 (실제 write X) |
| descriptor `readOnlyHint` | registry `read_only` 선언에서 파생 (read-only 11 = true / write 2 = false) | v0.5.7~v1.1.6 은 전 도구 true 하드코딩(허위) — v1.1.7 정정, 검사가 삼자 일치 강제 |

## Server List

초기 6종은 `workflow-source/mcp_servers/<kebab-case>/MCP.md` 가 인터페이스 정의서. 이후 확장분의 정본은 registry (`READ_ONLY_TOOL_SPECS`) 다. 전체 13종:

| # | 이름 (tool) | 디렉터리 | 목적 | 등장 |
|---|---|---|---|---|
| 1 | `latest_backlog` | `latest-backlog/` | `ai-workflow/memory/backlog/` 최신 날짜 파일 경로 탐색 | v0.5.0 |
| 2 | `check_doc_metadata` | `check-doc-metadata/` | markdown frontmatter / 메타데이터 무결성 검사 | v0.5.0 |
| 3 | `check_doc_links` | `check-doc-links/` | 문서 간 상대 링크 유효성 검사 | v0.5.0 |
| 4 | `create_backlog_entry` | `create-backlog-entry/` | `BacklogDraft` 객체 생성 (write 예외, **draft 만**) | v0.5.0 |
| 5 | `suggest_impacted_docs` | `suggest-impacted-docs/` | 변경 파일 경로 → 영향 문서 후보 추천 | v0.5.0 |
| 6 | `check_quickstart_stale_links` | `check-quickstart-stale-links/` | quickstart / README 계열 stale link / 핵심 진입 문서 누락 검사 | v0.5.0 |
| 7 | `read_only_mcp_sdk` | (server 모듈) | 정식 `mcp[cli]>=1.0` SDK 호환 entrypoint. v1.0 candidate | v0.5.7 |

| 8 | `create_environment_record_stub` | (registry 등록) | 환경 기록 stub draft 생성 | v0.6+ |
| 9 | `create_session_handoff_draft` | (registry 등록) | session handoff draft 생성 | v0.6+ |
| 10 | `summarize_git_history` | (registry 등록) | git 이력 요약 | v0.6+ |
| 11 | `rotate_workflow_logs` | (registry 등록) | handoff done 목록 rotate — **write-capable** (`readOnlyHint=false`) | v0.6+ |
| 12 | `assess_milestone_progress` | (registry 등록) | maturity matrix 기반 milestone 진행 평가 | v0.6+ |
| 13 | `smart_context_reader` | (registry 등록) | Python 파일에서 심볼 블록 추출 | v0.6+ |
| +  | `apply_robust_patch` | (registry 등록) | SEARCH/REPLACE 패치 적용 — **write-capable** (`readOnlyHint=false`, dry-run 입력 없음) | v0.11+ |

`create_backlog_entry` 는 ADR-003 §3.3 "draft 생성기" 정책 — 출력은 `BacklogDraft` (제목/본문/메타) 이고 `ai-workflow/memory/backlog/` 에 저장하지 않음, orchestrator 자동 commit 금지, 사용자 검토 후 수동 commit.

## Transport

[[concepts/mcp-transport]] 상세. `--mcp-bridge` 플래그로 선택.

| 우선순위 | Transport | Entry point | 상태 | 회귀 |
|---|---|---|---|---|
| 1 (default) | `jsonrpc-bridge` | `python3 -m workflow_kit.server.read_only_jsonrpc --stdio-lines` | **stable** (v0.5.0+) | 없음. `tools/list` + `tools/call` round-trip 정상 |
| 2 (opt-in) | `stdio-sdk` | `python3 -m workflow_kit.server.read_only_mcp_sdk --stdio-sdk` | **experimental** | `mcp 1.27.0` `CallToolResult(structuredContent=...)` API 불일치 → `Connection closed`. `check_read_only_mcp_sdk_stdio.py` fail |

권장: 처음 도입은 `jsonrpc-bridge`. SDK 호환 필요 시 별도 TASK 로 추적 후 점진 전환. 정식 default 전환 기준: `workflow-source/core/read_only_mcp_transport_promotion.md`.

## Bootstrap

`python3 -m bootstrap_lib --enable-mcp` (또는 `bootstrap_workflow_kit.py --enable-mcp`) 실행 시, 선택한 하네스별로 read-only MCP config snippet 이 자동 emit 된다 (ADR-003 §1 결정 #5). `transport_ready=false` 이면 **manual review only** (v0.5.10 정책, ADR-003 §1 결정 #6).

| Harness | Emit 경로 | Format |
|---|---|---|
| Codex CLI | `<root>/.codex/mcp.toml` | TOML |
| OpenCode CLI | `<root>/mcp.opencode.json` | JSONC |
| Gemini CLI | `<root>/.gemini/mcp.json` | JSON |
| Antigravity | `<root>/antigravity.mcp.json` | JSON |
| Mavis (MiniMax Code) | `<root>/.MiniMax/mcp.json` | JSON |

호출 예시:

```bash
python3 -m bootstrap_lib \
  --target-root <project_root> \
  --project-slug <slug> --project-name "<name>" \
  --harness opencode \
  --adoption-mode existing --copy-core-docs \
  --enable-mcp                            # ← read-only MCP 동시 emit
  # --mcp-bridge stdio-sdk                 # 선택: 실험적 stdio-sdk (회귀 감수)
```

5종 하네스 config 예시 원본: `workflow-source/examples/mcp_config_examples/`. 글로벌 심을 때 `PYTHONPATH` 는 절대 경로 권장 (상대 경로 시 `ModuleNotFoundError: workflow_kit`).

## Related

**Entities:**
- [[entities/standard-ai-workflow]] — hub entity (저장소 SSOT, 6-harness overlay)
- [[entities/workflow-kit]] — `workflow_kit/server/{read_only_jsonrpc,read_only_mcp_sdk}` 모듈 host
- [[entities/bootstrap-wiki-py]] — `--enable-wiki` skeleton emitter (대칭 패턴)

**Concepts:**
- [[concepts/mcp-transport]] — `jsonrpc-bridge` vs `stdio-sdk` 비교, failure mode F-1~F-5, wiki layer 와의 분리
- [[concepts/harness-distribution]] — 6-harness overlay registry/builder + MCP config emit 흐름

**Decisions:**
- [[decisions/adr-003-read-only-mcp-default]] — read-only 우선 정책, `create_backlog_entry` draft 예외, transport 우선순위, `transport_ready=false` manual review only
