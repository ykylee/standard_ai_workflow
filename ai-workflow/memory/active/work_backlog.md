# Work Backlog Index

- 문서 목적: 일별 작업 백로그에 대한 인덱스로, 최근 작업 흐름을 빠르게 복원한다.
- 범위: 인덱스 항목, 백로그 경로 규약, 갱신 규칙
- 대상 독자: AI agent, 저장소 maintainer
- 상태: stable
- 최종 수정일: 2026-06-18
- 관련 문서: [./PROJECT_PROFILE.md](./PROJECT_PROFILE.md), 브랜치별 daily backlog (각 브랜치 디렉터리 아래 `backlog/YYYY-MM-DD.md`)

## 인덱스 규칙

- 각 `### [[release/v0.5.X/backlog/YYYY-MM-DD.md]] {#release-v0-5-X}` 형식의 anchor entry 로 인덱스 표시
- anchor ID 로 직접 retrieval (session-start 의 index-based load)
- 각 일자 백로그는 TASK-NNN 식별자를 가진 작업 항목 1개 이상 포함
- 같은 일자에 여러 브랜치 작업이 있으면 브랜치별로 별도 백로그 파일

## 최근 작업 백로그

### [[release/v0.9.0/backlog/2026-06-18.md]] {#release-v0-9-0}
- 2026-06-18: v0.9.0 chapter 1 — Deprecation Policy Operational Spec 작성 + SSOT 정합 (pyproject 0.8.1 → 0.9.1, __version__ = v0.9.1-beta) + mypy config 정합 ([tool.mypy] unknown option 5개 → [tool.workflow-doctor] section 분리) + syntax fix. commit 841329f force-push.
- 2026-06-18: v0.9.0 chapter 2 — Deprecation 1st Cycle 실제 적용 (phishing_federation_v4.fetch_federated_phishing_urls_v4 DeprecationWarning 추가 + 6 신규 test + 4 acceptance verify + zero behavior change). mypy strict 18 file baseline 유지.
- 2026-06-18: v0.9.0 chapter 3 — Spec drift patch (§4.2/§4.3/§7.1 v0.9.0-beta → v0.9.1-beta 정직하게) + Beta-v0.9.0.md release note 신규 + workflow_kit_roadmap.md Phase 11 close + Phase 12 kickoff 갱신. spec §7.5 acceptance 4/4 verify 완료.
- 2026-06-18: v0.9.0 chapter 4 — Release pipeline 실행 (git tag v0.9.0-beta push + gh release create + 3-way 정합 verify). cmd_release in-scope fix 2건: (1) argparse --dry-run flag 누락 fix (v0.7.10~v0.7.58 14 release 동안 모든 호출 fail 이었던 진짜 bug), (2) local tag create step 누락 fix. release URL: https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.0-beta.

### [[release/v0.9.1/backlog/2026-06-18.md]] {#release-v0-9-1}
- 2026-06-18: v0.9.1 chapter 5 — Phase 12 (운영 지능화 + deprecation 운영 안정화) 의 첫 release. 3 deliverables: (1) mypy strict workflow_kit_cli.py 49 → 0 error (register decorator Callable 명시 cascade fix + 6개 cast), cumulative 18 → 19 file clean. (2) cmd_release --full-auto flag 신규 (pre-check conflict 시 자동 --auto-bump + 1-cycle close). 2 in-scope fix 동반: cmd_rollback dispatch 누락 fix, test_release_dry_run_no_dist error message acceptance 확장. (3) deprecation policy contract test 신규 (check_v0_9_1_deprecation_contract.py, 4 test) — workflow_kit.__all__ 의 모든 public symbol 의 deprecation-free/deprecation-marked contract 자동 verify. release URL: https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.1-beta.

### [[release/v0.7.59/backlog/2026-06-17.md]] {#release-v0-7-59}
- 2026-06-17: v0.7.59 1개 TASK (cmd_consumer_metrics in-process refactor — subprocess → import_module, v0.7.56+ score-wiki-trend 정공법)

### [[release/v0.8.15/backlog/2026-06-17.md]] {#release-v0-8-15}
- 2026-06-17: v0.8.15 1개 TASK (release-dist 1-command + housekeeping — spec §9 #7 release-dist 1-command + #11 tools test ≥ 7 PASS + .gitignore history + work_backlog stale 정리)

### [[release/v0.8.14/backlog/2026-06-17.md]] {#release-v0-8-14}
- 2026-06-17: v0.8.14 1개 TASK (mypy strict 단계적 격상 10단계 — common/contracts/baselines.py 27 error → 0 + 2 real bug fix: AuditLogEvent → StageCompletion, append_audit_log arg 순서)

### [[release/v0.8.13/backlog/2026-06-17.md]] {#release-v0-8-13}
- 2026-06-17: v0.8.13 1개 TASK (mypy strict 단계적 격상 9단계 — common/state/builder.py 13 error → 0, cumulative fix 잔여분 흡수)

### [[release/v0.8.12/backlog/2026-06-17.md]] {#release-v0-8-12}
- 2026-06-17: v0.8.12 1개 TASK (GH Actions weekly cron — consumer-metrics --digest-markdown 자동화, .github/workflows/consumer-metrics-digest.yml 신규)

### [[release/v0.8.11/backlog/2026-06-17.md]] {#release-v0-8-11}
- 2026-06-17: v0.8.11 1개 TASK (phishing_keywords 2 pre-existing test fail fix — _load_external_feed lowercase + dedup + openphish mock-based verify)

### [[release/v0.8.10/backlog/2026-06-17.md]] {#release-v0-8-10}
- 2026-06-17: v0.8.10 1개 TASK (read-only MCP manifest byte-identical assertion — spec §9 #6, spec §9 8/12)

### [[release/v0.8.9/backlog/2026-06-17.md]] {#release-v0-8-9}
- 2026-06-17: v0.8.9 1개 TASK (dispatcher surface 28 → 30 — cache-lru-decay + cache-merge-csv, v0.7.58 의 3 subcommand 잔여분)

### [[release/v0.8.8/backlog/2026-06-17.md]] {#release-v0-8-8}
- 2026-06-17: v0.8.8 1개 TASK (mypy strict 단계적 격상 8단계 — upgrade_diff + bitbucket_v2 + lfu_integration + cache_size_compare 8 error → 0 + tools/release_pipeline.py SSOT refactor)

### [[release/v0.8.7/backlog/2026-06-17.md]] {#release-v0-8-7}
- 2026-06-17: v0.8.7 1개 TASK (mypy strict 단계적 격상 7단계 — v_r13_commit_diff + cache_analytics + cache_analytics_trend_chart 13 error → 0)

### [[release/v0.8.6/backlog/2026-06-17.md]] {#release-v0-8-6}
- 2026-06-17: v0.8.6 1개 TASK (mypy strict 단계적 격상 6단계 — workflow_kit_cli.py 44 error → 0, register decorator Callable 명시로 cascade untyped-ness 해소)

### [[release/v0.8.5/backlog/2026-06-17.md]] {#release-v0-8-5}
- 2026-06-17: v0.8.5 1개 TASK (mypy strict 단계적 격상 5단계 — phishing_keywords + cache_lfu_decay + cache_lfu_decay_persist 11 error → 0)

### [[release/v0.8.4/backlog/2026-06-17.md]] {#release-v0-8-4}
- 2026-06-17: v0.8.4 1개 TASK (mypy strict 단계적 격상 4단계 — phishing_federation + phishing_federation_v4 8 error → 0, _UrlRecord TypedDict 신규)

### [[release/v0.8.3/backlog/2026-06-17.md]] {#release-v0-8-3}
- 2026-06-17: v0.8.3 1개 TASK (mypy strict 단계적 격상 3단계 — workflow_kit/okf_export.py 2 error → 0)

### [[release/v0.8.2/backlog/2026-06-17.md]] {#release-v0-8-2}
- 2026-06-17: v0.8.2 1개 TASK (mypy strict 단계적 격상 2단계 — workflow_kit/okf_import.py 9 error → 0, opening docstring + → 제거 + cast(Mode) + lambda→def + e→err)

### [[release/v0.8.1/backlog/2026-06-17.md]] {#release-v0-8-1}
- 2026-06-17: v0.8.1 1개 TASK (mypy strict 단계적 격상 1단계 — workflow_kit/url_validity.py 25 error → 0, Severity='info' 확장 + EvictionStrategy + CacheEntry.timestamp real bug fix)

### [[release/v0.8.0/backlog/2026-06-17.md]] {#release-v0-8-0}
- 2026-06-17: v0.8.0 1개 TASK (Stable API frozen + mypy strict base + generated JSON Schema SSOT — pyproject.toml [project] version SSOT + __version__ 자동 derive + 21 family 85,743 bytes + __all__ 27 entry, spec §9 7/12)

### [[release/v0.7.62/backlog/2026-06-17.md]] {#release-v0-7-62}
- 2026-06-17: v0.7.62 1개 TASK (consumer-metrics trend snapshot + weekly digest — B+D 통합, 5 신규 function + 4 신규 flag, history jsonl local-only)

### [[release/v0.7.61/backlog/2026-06-17.md]] {#release-v0-7-61}
- 2026-06-17: v0.7.61 1개 TASK (mkdocs --strict 진짜 활성화 — 50+ cross-link GitHub URL rewrite + exclude_docs 4 dir + docs/README.md 삭제, 116 warnings → 0)

### [[release/v0.7.60/backlog/2026-06-17.md]] {#release-v0-7-60}
- 2026-06-17: v0.7.60 2개 TASK (5 module audit 4차 path_resolver + phishing_keywords 정합 + dispatcher 27→28 cache-lfu-decay-persist in-process)

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

## v0.7.25~v0.7.32 (2026-06-15) — in-flight 8 housekeeping (v0.8.15 release note 의 housekeeping 의도 정합)

- **status**: **DONE** (2026-06-15 merged to main, 8 release / 25 commit / housekeeping by v0.8.15 commit 841329f)
- **8 release commit hash**: v0.7.25=`8a61bd3` / v0.7.26=`e5fbd2b` / v0.7.27=`2aa1efa` / v0.7.28=`b1b32f1` / v0.7.29=`850b798` / v0.7.30=`57d996d` / v0.7.31=`a9b510e` / v0.7.32=`75a8b4c`
- **정공법 (1줄)**: F-6 in-repo wiki mirror → F-7 detached HEAD short SHA → post-step sync_hash 자동화 → archive_stale_memory + cron 통합 → log rotation + metrics aggregation. v0.8.15 housekeeping 으로 in-flight 8 → 0 정리, 본 housekeeping 으로 detail block (62 line) → 1-line summary compactify.
- **detail 참조**: ai-workflow/memory/release/v0.7.25~v0.7.32/backlog/2026-06-15.md (per-release detail 파일 SSOT)

