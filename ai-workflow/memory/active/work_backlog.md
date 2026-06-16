# Work Backlog Index

- 문서 목적: 일별 작업 백로그에 대한 인덱스로, 최근 작업 흐름을 빠르게 복원한다.
- 범위: 인덱스 항목, 백로그 경로 규약, 갱신 규칙
- 대상 독자: AI agent, 저장소 maintainer
- 상태: stable
- 최종 수정일: 2026-06-09
- 관련 문서: [./PROJECT_PROFILE.md](./PROJECT_PROFILE.md), 브랜치별 daily backlog (각 브랜치 디렉터리 아래 `backlog/YYYY-MM-DD.md`)

## 인덱스 규칙

- 각 `### [[release/v0.5.X/backlog/YYYY-MM-DD.md]] {#release-v0-5-X}` 형식의 anchor entry 로 인덱스 표시
- anchor ID 로 직접 retrieval (session-start 의 index-based load)
- 각 일자 백로그는 TASK-NNN 식별자를 가진 작업 항목 1개 이상 포함
- 같은 일자에 여러 브랜치 작업이 있으면 브랜치별로 별도 백로그 파일

## 최근 작업 백로그

### [[release/v0.7.58/backlog/2026-06-17.md]] {#release-v0-7-58}
- 2026-06-17: v0.7.58 1개 TASK (consumer feedback metrics — tools/consumer_metrics.py 155 line + cmd_consumer_metrics subcommand 27 + 9 smoke)

### [[release/v0.7.24/backlog/2026-06-15.md]] {#release-v0-7-24}
- 2026-06-15: v0.7.24 1개 TASK (cmd_release --notes-template flag — 5 template: default/detailed/simple/changelog/custom + 5 smoke)

### [[release/v0.7.23/backlog/2026-06-15.md]] {#release-v0-7-23}
- 2026-06-15: v0.7.23 1개 TASK (wiki 운영 cross-link 1-command wrapper — tools/wiki_emit.py 3-step cycle + 5 smoke)

### [[release/v0.7.22/backlog/2026-06-15.md]] {#release-v0-7-22}
- 2026-06-15: v0.7.22 1개 TASK (linter symlink-resolve fix — workflow_kit/common/linter.py .resolve() → .absolute() 2 site + 3 smoke)

### [[release/v0.7.21/backlog/2026-06-15.md]] {#release-v0-7-21}
- 2026-06-15: v0.7.21 1개 TASK (F-4 design 결함 fix — --allow-existing-tag flag + tag push 자동화 + 1 smoke)

### [[release/v0.7.20/backlog/2026-06-15.md]] {#release-v0-7-20}
- 2026-06-15: v0.7.20 1개 TASK (release coordination observability — auto-bump chain 최종)

### [[release/v0.7.19/backlog/2026-06-15.md]] {#release-v0-7-19}
- 2026-06-15: v0.7.19 1개 TASK (release coordination auto-bump — v0.7.18 → v0.7.19)

### [[release/v0.7.18/backlog/2026-06-15.md]] {#release-v0-7-18}
- 2026-06-15: v0.7.18 1개 TASK (release coordination observability — _check_remote_tag + next_available_version + --auto-bump + 7 smoke)

### [[release/v0.7.17/backlog/2026-06-15.md]] {#release-v0-7-17}
- 2026-06-15: v0.7.17 1개 TASK (wiki in-repo storage isolation — 5 file redirect + ai-workflow/wiki/sources/ 신규 + 11 smoke)

### [[release/v0.7.16/backlog/2026-06-15.md]] {#release-v0-7-16}
- 2026-06-15: v0.7.16 4개 TASK (config score_alert + memory_alert_mb consumer + linter excluded_paths + linter IndentationError/dict-slice fix + 9 smoke)

### [[release/v0.7.15/backlog/2026-06-15.md]] {#release-v0-7-15}
- 2026-06-15: v0.7.15 2개 TASK (atomic_write helper + changelog-gen --from-tag/--to-tag filter + 5 smoke)

### [[release/v0.7.14/backlog/2026-06-15.md]] {#release-v0-7-14}
- 2026-06-15: v0.7.14 4개 TASK (cmd_version_bump auto-sync + cmd_changelog_gen subcommand + 8 smoke + state sync)

### [[release/v0.7.13/backlog/2026-06-15.md]] {#release-v0-7-13}
- 2026-06-15: v0.7.13 3개 TASK (cmd_release --version flag + 3 smoke + version sync)

### [[release/v0.7.12/backlog/2026-06-15.md]] {#release-v0-7-12}
- 2026-06-15: v0.7.12 3개 TASK (REPO_ROOT auto-detect + 4 smoke + v0.7.5~v0.7.10 backfill)

### [[release/v0.7.11/backlog/2026-06-15.md]] {#release-v0-7-11}
- 2026-06-15: v0.7.11 5개 TASK (dist subcommand + state sync backfill + version string sync + release note + session_handoff)

### [[release/v0.7.10/backlog/2026-06-14.md]] {#release-v0-7-10}
- 2026-06-14: v0.7.10 3개 TASK (release / verify / rollback — release_pipeline Phase 2)

### [[release/v0.7.9/backlog/2026-06-14.md]] {#release-v0-7-9}
- 2026-06-14: v0.7.9 3개 TASK (validate / version-bump / note-draft — release_pipeline Phase 1)

### [[release/v0.7.8/backlog/2026-06-14.md]] {#release-v0-7-8}
- 2026-06-14: v0.7.8 2개 TASK (state-aware evaluate_compliance + config actual apply)

### [[release/v0.7.7/backlog/2026-06-14.md]] {#release-v0-7-7}
- 2026-06-14: v0.7.7 1개 TASK (workflow_kit.cli.doctor × load_config integration)

### [[release/v0.7.6/backlog/2026-06-14.md]] {#release-v0-7-6}
- 2026-06-14: v0.7.6 2개 TASK (run_all_checks 통합 runner + workflow_kit.metadata loader)

### [[release/v0.7.5/backlog/2026-06-14.md]] {#release-v0-7-5}
- 2026-06-14: v0.7.5 2개 TASK (Extension audit 4 dispatcher + refresh_wiki_memory 정식화)

### [[release/v0.7.4/backlog/2026-06-13.md]] {#release-v0-7-4}
- 2026-06-13: v0.7.4 3개 TASK (workflow doctor CLI + @graceful_shutdown + optional dep)

### [[release/v0.7.3/backlog/2026-06-13.md]] {#release-v0-7-3}
- 2026-06-13: v0.7.3 2개 TASK (4 Runtime Helper + 7 baseline dispatcher)

### [[release/v0.7.2/backlog/2026-06-13.md]] {#release-v0-7-2}
- 2026-06-13: v0.7.2 2개 TASK (Extension sub-cat lint + 4 baseline 본 구현)

### [[release/v0.7.1/backlog/2026-06-13.md]] {#release-v0-7-1}
- 2026-06-13: v0.7.1 5개 TASK (score dashboard / L2 emit / 위치 lint / drift check / follow-up 묶음)

### [[release/v0.7.0/backlog/2026-06-13.md]] {#release-v0-7-0}
- 2026-06-13: v0.7.0 7개 TASK (AIDLC Extension + Reverse Engineering + UOW + audit log + Stage Completion + Security Baseline + packaging)

### [[release/v0.5.10/backlog/2026-06-09.md]] {#release-v0-5-10}
- 2026-06-09: v0.5.10 1개 TASK (TASK-V0510-001: 개발자용 설치·사용 가이드)

### [[release/v0.5.6/backlog/2026-06-07.md]] {#release-v0-5-6}
- 2026-06-07: v0.5.6 1개 TASK (§5 출력 validator + §6.1 자동 위임 delegator)

### [[release/v0.5.5/backlog/2026-06-07.md]] {#release-v0-5-5}
- 2026-06-07: v0.5.5 1개 TASK (Phase 11 본격 pilot, contract v1 실전 검증)

### [[release/v0.5.4/backlog/2026-06-07.md]] {#release-v0-5-4}
- 2026-06-07: v0.5.4 3개 TASK (orchestrator delegation contract v1 / maturity matrix)

### [[release/v0.5.3/backlog/2026-06-07.md]] {#release-v0-5-3}
- 2026-06-07: v0.5.3 2개 TASK (antigravity MCP config 표준화 / cross-language stack)

### [[release/v0.5.2/backlog/2026-06-06.md]] {#release-v0-5-2}
- 2026-06-06: v0.5.2 3개 TASK (bootstrap 리팩터 / workflow_kit 패키지화)

### [[release/v0.5.1/backlog/2026-06-05.md]] {#release-v0-5-1}
- 2026-06-05: v0.5.1 self-dogfooding bootstrap + MCP 설치 가이드 (TASK-V051-001..006)

### Historical archives {#historical-archives}
### [[codex/phase6/backlog/2026-05-01.md]] {#codex-phase6}
- 2026-05-01: Phase 6 multi-agent delegation pilot
### [[gemini/phase10/backlog/2026-04-24.md]] {#gemini-phase10}
- 2026-04-24: Phase 10 MCP/JSON-RPC draft

## 다음에 읽을 문서

- [release/v0.5.6/session_handoff.md](../release/v0.5.6/session_handoff.md)
- [release/v0.5.6/backlog/2026-06-07.md](../release/v0.5.6/backlog/2026-06-07.md)
- [release/v0.5.5/session_handoff.md](../release/v0.5.5/session_handoff.md)
- [release/v0.5.5/backlog/2026-06-07.md](../release/v0.5.5/backlog/2026-06-07.md)
- [release/v0.5.4/session_handoff.md](../release/v0.5.4/session_handoff.md)
- [release/v0.5.4/backlog/2026-06-07.md](../release/v0.5.4/backlog/2026-06-07.md)
- [release/v0.5.3/session_handoff.md](../release/v0.5.3/session_handoff.md)
- [release/v0.5.3/backlog/2026-06-07.md](../release/v0.5.3/backlog/2026-06-07.md)
- [release/v0.5.2/session_handoff.md](../release/v0.5.2/session_handoff.md)
- [release/v0.5.2/backlog/2026-06-06.md](../release/v0.5.2/backlog/2026-06-06.md)
- [Maturity Matrix](../../workflow-source/core/maturity_matrix.json)

## v0.7.25 (2026-06-15) — Legacy L2 page in-repo migration (F-6)

- **commit**: TBD
- **status**: in-flight
- **scope**: tools/migrate_legacy_l2.py (~280 line) + tests/check_v0_7_25_legacy_l2_migration.py (5 smoke) + ai-workflow/memory/release/_external-wiki-legacy.md (mirror file, 35,032 bytes, 15 version 1:1 mirror)
- **정공법**: external wiki 의 legacy L2 page (15 version: v0.1.0~v0.6.3) → in-repo 의 단일 mirror file. v0.7.17 의 in-repo redirect 의 *closure*.


## v0.7.26 (2026-06-15) — Branch Detection Fix (F-7) + Automated Hash Sync (F-7+)

- **commit**: TBD
- **status**: in-flight
- **scope**: `workflow_kit/common/paths.py` (~15 line, F-7 detached HEAD → short SHA) + `tools/sync_release_hash.py` (~180 line, F-7+ automated hash sync) + 2 신규 test file (10 smoke, 10/10 PASS)
- **정공법**: F-7 = detached HEAD 의 stable identifier = short SHA (7자). F-7+ = automated hash sync 로 v0.7.25 의 infinite fix(state) loop 회피 (1 commit 으로 state.json + backlog 의 hash = latest commit hash).


## v0.7.27 (2026-06-15) — TASK-V0726-003 (sync_release_hash post-step auto-call)

- **commit**: TBD
- **status**: in-flight
- **scope**: `release_pipeline.py:cmd_version_bump` post-step sync_release_hash 자동 호출 + `_run_post_step_sync_hash` 신규 helper + `--skip-sync-hash` flag + 1 신규 test file (5 smoke, 5/5 PASS)
- **정공법**: post-step 의 *in-process* + caller opt-in flag (--skip-sync-hash) 의 *3종 정합* (v0.7.18/21/27) + post-step 의 *graceful fail* (sync_hash fail 해도 version-bump 성공). v0.7.25 의 infinite fix(state) loop 의 *closure*.


## v0.7.28 (2026-06-15) — TASK-V0726-004 (Detached HEAD Memory Dir Cleanup)

- **commit**: TBD
- **status**: in-flight
- **scope**: `tools/archive_stale_memory.py` (~250 line, 4-priority REPO_ROOT + 3 subcommand + 5 helper) + `tests/check_v0_7_28_archive_stale_memory.py` (5 smoke, 5/5 PASS)
- **정공법**: F-7 (v0.7.26) 의 detached HEAD → short SHA fix 의 *closure*. age-based auto-archive: N day 이전의 short SHA dir → `archive/<YYYY-MM-DD>/<sha>/` 로 move. SHA256-based idempotency (v0.7.25 의 F-6 의 1차 출처).


## v0.7.29 (2026-06-15) — TASK-V0727-001 (Post-Step 2-Phase + Amend Integration)

- **commit**: TBD
- **status**: in-flight
- **scope**: `release_pipeline.py:_run_post_step_sync_hash` (~50 line, 2-phase: sync + amend) + 1 신규 test file (5 smoke, 5/5 PASS)
- **정공법**: post-step 의 *sequential dependency* (sync → add → amend → rev-parse). sync fail → amend 호출 0. amend fail → final_hash = None + ok = False. **별도 fix(state) commit 불필요** — feat + chore = 2 commit (v0.7.28 의 3 commit 대비 *33% 감소*).


## v0.7.30 (2026-06-15) — TASK-V0728-001 (Archive Stale Memory Cron Integration)

- **commit**: TBD
- **status**: in-flight
- **scope**: `tools/archive_stale_memory.py` (~80 line 추가: 3 cmd + 3 flag + 2 config) + 1 신규 test file (5 smoke, 5/5 PASS)
- **정공법**: `mavis cron create <agent> <cronName> --schedule <interval> --prompt <text>` 자동 호출. *manual* → *automated* 정공법 (caller discipline → system automation).


## v0.7.31 (2026-06-15) — TASK-V0729-001 + TASK-V0730-001 (Run-Time Metrics + Cron Idempotency)

- **commit**: TBD
- **status**: in-flight
- **scope**: `archive_stale_memory.py` (~110 line: 3 helper + 1 subcommand + idempotency + check_already_archived file catch) + 1 신규 test file (10 smoke, 10/10 PASS) + 1 v0.7.28 test fix
- **정공법**: append-only metrics log (ISO 8601 + tab-separated 5 field) + `mavis cron info` existence check + `--force-install` caller opt-in + `check_already_archived` file catch (v0.7.28 의 *dst 가 file* 시나리오 보강).


## v0.7.32 (2026-06-15) — TASK-V0731-001 + TASK-V0732-001 (Log Rotation + Metrics Aggregation)

- **commit**: TBD
- **status**: in-flight
- **scope**: `archive_stale_memory.py` (~180 line: 3 helper + 2 subcommand + argparse flags) + 1 신규 test file (10 smoke, 10/10 PASS, 5-run stable)
- **정공법**: log rotation (line > 10000 → gzip + truncate) + metrics aggregation (weekly/monthly/daily/all + ISO 8601 week) + `--include-rotated` flag (dedup with main log).

