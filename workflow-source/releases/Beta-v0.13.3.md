---
release: v0.13.3
closed_phases: []
promoted_skills: []
added_harnesses: []
deprecated_symbols: []
phase_13_sub_milestones:
  - { name: v0.13.3, scope: "wiki↔memory bidirectional link sync + audit", status: shipped }
---

# Beta v0.13.3 — wiki ↔ memory bidirectional link sync + audit (Phase 13 AC4+ close) (2026-07-09)

> Phase 13 (Operational Intelligence v1.0) 의 sub-milestone 4th + **마지막**
> release. AC1 (drift zero) + AC2 (telemetry) + AC3 (self-recover) +
> **AC4+ (bidir link)** 모두 ✅. **Phase 13 v1.0 완성**. AC4+ close-out.

## 핵심 (R-A sync + R-C audit 통합)

### 1. bidir_link.py 신규 (`workflow_kit/common/state/bidir_link.py`, 260 line)

3 helper + 3 dataclass:

- `normalize_memory_path_to_wiki_relative(path, workspace_root)` —
  in-repo 절대 path → wiki root relative 변환.
- `audit_bidirectional_links(workspace_root) -> BidirLinkAudit` — wiki
  pages × memory entries 의 cross-reference 검증 (R-C). `total_wiki_pages` /
  `total_memory_entries` / `symmetric_links` / `asymmetric: list[BidirLinkAsymmetry]` /
  `is_symmetric` emit.
- `sync_memory_to_wiki(workspace_root, dry_run=True) -> BidirSyncResult` —
  memory entry.mentioned_in 의 wiki page path 순회 → 각 wiki page 의
  frontmatter `related_pages` 에 memory entry file 의 in-repo relative path
  자동 추가 (R-A). idempotent — 이미 있으면 skip.

dataclass:
- `BidirLinkAudit` (total_wiki_pages / total_memory_entries /
  symmetric_links / asymmetric / is_symmetric / ...)
- `BidirSyncResult` (mode / total_changes / changes / summary)
- `BidirLinkAsymmetry` (memory_entry_id / wiki_page / direction)

`Frontmatter.parse` 재사용 (`workflow_kit/okf_export.py`) 로 yaml dep
회피. `_emit_yaml_frontmatter` 신규 yaml subset emitter (parse 와
round-trip).

### 2. cmd_bidir_link dispatcher subcommand 38

- **detect → sync → re-audit** 1-cycle orchestrator (v0.13.2 self-recover 와
  동일 정공법):
  - pre-audit (drift 검출)
  - sync (auto-apply if --apply)
  - post-audit (정합 확인)
- ARGS: `--workspace-root`, `--apply`, `--json`.
- default = audit only (read-only). `--apply` 명시 시 sync.
- §6.3 MUST-NOT-delegate 정합.

### 3. cmd_release 자동 wiring + release note log emit

- **`cmd_release` step 2.8** — sync-maturity-matrix step 후
  `cmd_bidir_link` (default audit) 자동 호출. `--skip-bidir-link`
  escape hatch. asymmetric > 0 이면 advisory 만 (release 차단 ❌).
- **`_format_bidir_link_audit`** + **`_emit_bidir_link_audit_log`** —
  release note 본문 끝에 `## Bidirectional link audit` 섹션 자동 append
  (idempotent marker). v0.13.2 self-recovery log 와 동일 정공법.
- **`tools/release_pipeline.py`** dispatcher 등록 (`bidir-link` argparse
  subcommand).

## Phase 13 v1.0 close-out 종합

| AC | Status | Release |
|---|---|---|
| AC1 (drift zero) | ✅ | v0.11.23 |
| AC1.5 (north-star) | ✅ | v0.13.0 |
| AC1.6 (inline guard) | ✅ | v0.13.0 |
| AC2 (memory_index 활용) | ✅ | v0.13.1 |
| AC3 (self-recovering) | ✅ | v0.13.2 |
| **AC4+ (self-documenting)** | ✅ | **v0.13.3** (본 release) |

## 신규 파일 / 변경

| 변경 | 파일 | 비고 |
|---|---|---|
| 신규 | `workflow-source/tests/check_bidir_link_v0_13_3.py` | 6 case smoke (audit shape / path normalization / dry-run / sync apply / re-audit / format) |
| 신규 | `workflow_kit/common/state/bidir_link.py` | 260 line, 3 helper + 3 dataclass |
| 신규 | `ai-workflow/memory/release/v0.13.3/backlog/2026-07-09.md` | release note (cycle archive) |
| extend | `tools/release_pipeline.py` | `cmd_bidir_link` dispatcher subcommand 38 + `_format_bidir_link_audit` + `_emit_bidir_link_audit_log` + `cmd_release` step 2.8 + `--skip-bidir-link` flag + `_attr_ns.normalize` 갱신 |

## housekeeping

- samples 24 file `tool_version` v0.13.2-beta → v0.13.3-beta
- schemas regen (generated_output_schemas + output_sample_contracts)
- dashboard HTML regen
- pyproject.toml 0.13.2 → 0.13.3
- workflow_kit/__init__.py loud fallback v0.13.2-beta → v0.13.3-beta
- README.md header v0.13.2-beta → v0.13.3-beta + Phase 13 v0.13.3 follow-up 1줄
- maturity_matrix.json v0.13.3 1줄 추가

## 검증 결과

- 신규 smoke **6/6 PASS** (check_bidir_link_v0_13_3)
- 3 skill smoke (session-start / doc-sync / backlog-update) **3/3 PASS**
- memory_index smoke **25/25 PASS**
- memory_index telemetry smoke **6/6 PASS**
- self_recovering smoke **8/8 PASS**
- Quality Dashboard smoke **10/10 PASS**
- drift prevention smoke **6/6 PASS** (clean state)
- output samples + schema validation **3/3 PASS**
- mypy strict **0 new error** (21 errors 유지)
- **audit 실측**: `is_symmetric=true`, `asymmetric_count=0`

**누적 smoke 225+ PASS** (v0.13.2 219+ + 신규 6 + 회귀 0 net new)

## release URL

- tag: `v0.13.3-beta`
- breaking change: ❌
- PyPI 배포: no
- 후속 (v0.13.4+): R-B (Wiki → Memory reverse lookup) — 별도 sub-milestone