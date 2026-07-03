# Changelog

All notable changes to this project will be documented in this file.

본 파일은 `tools/release_pipeline.py changelog-gen` 으로 자동 생성됩니다 (v0.7.14+).
수동 편집도 가능하나 다음 release 시 자동 갱신 시 충돌 가능.

## [Unreleased] - 2026-07-02

### Added

- feat(skill): ADR-005 Memory Index Phase 3d backlog-update memory_index wiring (last skill) (2ab3b6c)
- feat(skill): ADR-005 Memory Index Phase 3c doc-sync memory_index wiring (opt-in) (c46d729)
- feat(skill): ADR-005 Memory Index Phase 3b session-start memory_index wiring (opt-in) (73564d9)
- feat(skill): ADR-005 Memory Index Phase 3 dispatcher entry (memory-index-query skill beta) (7be5029)
- feat(skill): ADR-005 Memory Index Phase 2b BM25 2단계 fallback (stdlib only) (5973146)
- feat(skill): ADR-005 Memory Index Phase 2 --merge opt-in canonical merge (d2d8a1c)
- feat(skill): ADR-005 Memory Index Phase 1.5 state.json hook (memory_entries optional merge) (4655e7c)
- feat(skill): ADR-005 Memory Index Phase 1 prototype (helper + schema + smoke) (e4c7343)
- feat(test): robust-patcher smoke test 신규 (5 case) (ba689a3)
- feat(skill): robust-patcher run_robust_patcher.py 표준화 + 4종 error_code (9249324)
- feat(skill): robust-patcher Pydantic schema 정합 + apply_robust_patch_detailed helper (d90f786)
- feat(test): 2 신규 smoke test (merge-doc-reconcile + project-status-assessment) (29ae1cc)
- feat(skill): 2 skill stable error_code 추가 (backlog-update + merge-doc-reconcile) (ddac80e)
- feat(skill): project-status-assessment Pydantic schema 정합 + missing_required_document error_code (65d5591)

### Changed

- chore(state): v0.11.22 release memory cycle — 8 phase + ADR-006 retrospective anchor + 3 skill wiring 3/3 (ea013a2)
- chore(release): Beta-v0.11.22 release note (작업내역 정리) (c0b49cf)
- chore(release): Beta-v0.11.22 release note (작업내역 정리) (185a1f1)
- chore(state): v0.11.22 ADR-006 retrospective 자리 memory cycle (a42cf61)
- docs(adr): ADR-006 ADR-005 Memory Index implementation retrospective 자리 박기 (34fb07f)
- chore(state): v0.11.22 Phase 3d backlog-update wiring memory cycle (skill wiring 3/3 완료) (d89beae)
- chore(state): v0.11.22 Phase 3c doc-sync wiring memory cycle (a598706)
- chore(state): v0.11.22 Phase 3b1 session-start wiring memory cycle (01ed22d)
- chore(state): v0.11.22 Phase 3 dispatcher entry memory cycle (2cc6179)
- chore(state): v0.11.22 Phase 2b BM25 fallback memory cycle (c90bde1)
- chore(state): v0.11.22 Phase 2 --merge opt-in memory cycle (a712c95)
- chore(state): v0.11.22 Phase 1.5 state.json hook memory cycle (fa0ac32)
- chore(state): v0.11.22 ADR-005 Phase 1 prototype memory cycle (348048c)
- chore(state): ADR-005 v0.11.22+ Phase 1 candidate memory cycle (0f10926)
- docs(adr): ADR-005 Memora-inspired Memory Index 추가 (v0.11.22+ Phase 1 계획) (468ec7d)
- docs: add Memora evaluation note (95d6eba)
- chore(state): v0.11.21 release memory cycle (b378284)
- chore(samples): output_samples tool_version v0.11.19 → v0.11.20 housekeeping (c90b437)
- chore(spec): robust-patcher SKILL.md status → stable + spec layer 동기화 (63c22c8)
- chore(state): v0.11.20 release memory cycle (a6c76bd)
- chore(samples): output_samples tool_version v0.11.17 → v0.11.19 housekeeping (af6baaf)
- chore(spec): 4 skill SKILL.md status → stable + skill catalog/beta_criteria 갱신 (cb32d6c)
- chore(state): v0.11.19 release memory cycle (143d2d3)
- chore(state): v0.11.18 release memory cycle (dfafdc4)
- chore(state): v0.11.18 release memory cycle (df506ed)
- chore(state): session 마무리 memory cycle (4c83ed9)
- chore(state): read_only_mcp_sdk + doc_sync 묶음 격상 memory cycle (f54d746)
- chore(state): mcp_v1_server + release_status 묶음 격상 memory cycle (7cf8f47)
- chore(state): v0.11.17 release memory cycle (4d991e8)
- chore(state): mypy strict 묶음 격상 memory cycle (508d92a)
- ... (51 more)

### Fixed

- fix(linter): broken_link check 의 .. segment 정규화 + smoke test fixture 정합 (9960e8f)
- fix(state): state.json path latent bug fix (v0.6.0.1 부터) + test fixture 정합 (4821b71)
- fix(ci): mypy-strict workflow install mcp-sdk extra — CI 의 [import-not-found] 해소 (80470cd)
- fix(workflow_kit): mypy strict 잔여 13 error 일괄 격상 — FULL mypy strict 도달 (107 file clean) (4253eed)
- fix(workflow_kit): mypy strict read_only_mcp_sdk + doc_sync 4 error 묶음 격상 (65f0b20)
- fix(workflow_kit): mypy strict mcp_v1_server + release_status 6 error 묶음 격상 (094cacf)
- fix(workflow_kit): mypy strict cli/doctor + common/decorators 10 error 묶음 격상 (97795bc)
- fix(samples): schema drift 회귀 방지 — sample 24 + schema 2 갱신 (00cc83e)
- fix(workflow_kit): mypy strict output_contracts 15 error 격상 (f6b65a4)
- fix(wiki): R9 lint false-positive 회피 — dashboard emit multi-line 분리 (1333cc8)
- fix(workflow): 세션 종료 단계 commit/memory 순서 정정 — memory → commit → push (32185c7)
- fix(release_pipeline): cmd_release --dry-run flag + local tag create (f531adb)
- fix: v0.8.0 hotfix + v0.8.8 mypy strict 4 file + v0.8.9 dispatcher 29/30 + release_pipeline SSOT (fcb4e8b)
- fix(state): v0.7.58 chore commit hash 동기화 (1c7d8e9) (d0c7c53)
- fix(state): v0.7.32 2nd hash sync (1348a3c)
- fix(state): v0.7.31 2nd hash sync (fae9157)
- fix(state): v0.7.30 2nd hash sync (264ab5c)
- fix(state): v0.7.29 backlog = 2ee6dbf (본 release 의 fix(state) hash, v0.7.21 정공법) (fda9379)
- fix(state): v0.7.29 2nd hash sync (6830993)
- fix(state): v0.7.28 squash + state.json + backlog = chore commit hash (7bb6259, v0.7.21 정공법) (ca7d385)
- fix(state): v0.7.27 version-bump + state.json 정합 (v0.7.21 정공법, 2aa1efa = 본 release 의 feat commit) (66c18e7)
- fix(state): v0.7.27 squash + 본 release 의 본 release 의 hash 정합 (v0.7.21 정공법, 2aa1efa = feat commit) (8ef94d6)
- fix(state): v0.7.26 squash + 본 release 의 본 release 의 hash 정합 (v0.7.21 정공법, ecb6ce1 = chore commit) (9413697)
- fix(state): v0.7.25 본 release hash (96a919d) 로 정합 (v0.7.21 정공법) (00e7ca8)
- fix(state): v0.7.25 hash 동기화 (squash 8 commits → 1) (2f5945d)
- fix(state): v0.7.24 backlog.commit 을 fix(state) hash(ef13691) 로 동기화 (6e302c1)
- fix(state): v0.7.24 chore commit hash 동기화 (e802e56 → 2c38d07 amend 후 hash) (ef13691)
- fix(state): v0.7.23 chore commit hash 동기화 (98442d1)
- fix(state): v0.7.22 chore commit hash 동기화 (8b02fe9)
- fix(state): v0.7.21 chore commit hash 동기화 (amend 후 hash drift 보정) (fa329b1)

## [0.9.6] - 2026-06-24

### Added

- feat+chore(v0.9.6): R-A follow-up part 3 (wiki-event-sync R-A trigger) (09282b0)

## [0.9.5] - 2026-06-24

### Added

- feat+chore(v0.9.5): R-A follow-up part 2 (skill context load integration) (96f9715)

## [0.9.4] - 2026-06-19

### Added

- feat+chore(v0.9.4): R-A follow-up part 1 (state.json.purpose_digest 1-line 자동 생성) (48a3380)

## [0.9.2] - 2026-06-19

### Added

- feat+chore(v0.9.2): purpose.md concept 흡수 (외부 reference 차용 정공법 1차 적용) (51e7bec)

## [0.9.1] - 2026-06-18

### Added

- feat+chore(v0.9.1): mypy workflow_kit_cli strict + release --full-auto + deprecation contract (50c688f)

## [0.9.0] - 2026-06-18

### Added

- feat+chore(v0.9.0): spec drift patch + release note + Phase 11 close (a1f8463)
- feat(v0.9.0): deprecation 1st cycle - phishing_federation_v4 DeprecationWarning (bf03b95)

## [0.8.15] - 2026-06-17

### Added

- feat+chore(v0.8.15): release-dist 1-command + housekeeping (spec §9 9/12) (841329f)

## [0.8.0] - 2026-06-17

### Added

- feat(v0.8.0): Stable API frozen + mypy strict + generated JSON Schema SSOT (5042df1)

## [0.7.9] - 2026-06-14

### Changed

- docs(v0.7.9): release note backfill + refresh_wiki_memory v0.7.9 tracking (283823e)

## [0.7.59] - 2026-06-17

### Added

- feat(v0.7.59): cmd_consumer_metrics in-process refactor (dispatcher 27 정합) (f2b92cf)

## [0.7.58] - 2026-06-17

### Added

- feat(v0.7.58): consumer feedback metrics tool + dispatcher subcommand 27 (38fe32a)

### Changed

- chore(v0.7.58): version bump 0.7.57 → 0.7.58 + release note + state sync (1c7d8e9)

## [0.7.57] - 2026-06-16

### Added

- feat(v0.7.57): mkdocs cross-link audit + 1 broken link fix (cbcaaad)
- feat(v0.7.57): <in-memory> cleanup + dispatcher 23 → 26 (cache format interop) (ec1223c)

### Changed

- docs(v0.7.57): v0.7.57 release note + wiki log + memory log (1c83b6f)
- chore(v0.7.57): .gitignore 에 /site/ 추가 (mkdocs build output) (654e21e)

## [0.7.56] - 2026-06-16

### Added

- feat(v0.7.56): cache-lfu-decay-persist CSV in-place + dispatcher --inplace (7b4d6b7)
- feat(v0.7.56): release_pipeline wrapper 7 추가 + dispatcher 16 → 23 (fb6ebc4)
- feat(v0.7.56): score-wiki-trend in-process + dispatcher 16+ (c3ef125)

### Changed

- docs(v0.7.56): v0.7.56 release note + wiki log entry (094cc2c)
- docs(v0.7.56): GH Pages 외부 consumer feedback loop + FEEDBACK.md (1c5c1df)
- test(v0.7.56): OKF strict mode lint rule coverage 7 신규 (audit 3차) (58e2ac0)

## [0.7.55] - 2026-06-16

### Changed

- test(v0.7.55): tools/release_pipeline_lib wrapper test 2 신규 (cmd_validate) (428a2d2)
- chore(v0.7.55): version bump 0.7.54 → 0.7.55 + release note (0436eb3)
- test(v0.7.55): tools/release_pipeline_lib wrapper test 2 신규 (cmd_validate) (3ba61e8)
- refactor(v0.7.55): release-doctor in-process + cache-migrate LRU/LFU split + 3 subcommand (14 subcommand) (4b64b20)

## [0.7.54] - 2026-06-16

### Added

- feat(v0.7.54): workflow_kit_cli — okf-validate / cache-migrate / release-doctor (11 subcommand) (97adc0c)

### Changed

- chore(v0.7.54): version bump 0.7.53 → 0.7.54 + release note (58fbb32)
- test(v0.7.54): dispatcher test 4 신규 (okf-validate × 2 + cache-migrate + release-doctor) (cde0a45)

## [0.7.53] - 2026-06-16

### Added

- feat(v0.7.53): mkdocs 셋업 (GH Pages in-repo, public-facing consumer guide) (fda611b)
- feat(v0.7.53): workflow_kit_cli — okf-export / okf-import subcommand 추가 (a910988)

### Changed

- chore(v0.7.53): version bump 0.7.52 → 0.7.53 + release note (3d7e232)
- test(v0.7.53): url_validity test file 추가 (12 test, audit 2차 갭 해소) (0562931)

## [0.7.52] - 2026-06-16

### Added

- feat(v0.7.52): cache analytics snapshot diff (1/1 PASS) (f4adf8c)
- feat(v0.7.52): cache analytics alerting CLI (--alert, zero-dep, 2/2 PASS) (fbbd254)

### Changed

- chore(v0.7.52): version bump 0.7.6 → 0.7.52 + release note (b0491d0)
- docs(v0.7.52): log entry for retrospective consolidation cleanup (ee63739)
- refactor(v0.7.52): collapse 6 CLI modules into workflow_kit_cli dispatcher (6/6 PASS) (71bf15d)
- refactor(v0.7.52): inline v_r13_commit_diff_integration + v_r13_layer2_pipeline into v_r13_commit_diff (6/6 PASS) (25c7c1a)
- refactor(v0.7.52): consolidate cache_dashboard_export into cache_dashboard module (87f77bd)
- refactor(v0.7.52): remove v2/v3/v4/v5 federation module + test files (081b72c)
- refactor(v0.7.52): consolidate phishing_federation_v2/v3/v4/v5 into one module (4/4 PASS) (0d5a2c7)

## [0.7.51] - 2026-06-16

### Added

- feat(v0.7.51): phishing federation v5 CLI (--federate-v5, 2/2 PASS, FREE tier) (85be71c)
- feat(v0.7.51): cache dashboard export CLI (--dashboard-export --output=PATH, 2/2 PASS) (8810695)
- feat(v0.7.51): cache trend chart CLI (--trend-chart --snapshots=PATH, 2/2 PASS) (4c579ad)
- feat(v0.7.51): LFU decay score automatic aging (decay_age_scores, 2/2 PASS, no regression) (4247589)
- feat(v0.7.51): cache analytics threshold-based alerting (2/2 PASS) (5186836)

### Changed

- release(v0.7.51): cache alerting + decay aging + trend chart CLI + dashboard export CLI + federation v5 CLI (201/201 PASS, FREE tier) (22541e2)

## [0.7.50] - 2026-06-16

### Added

- feat(v0.7.50): LFU decay score CSV export/import (cross-process, 2/2 PASS, no regression) (17e9da9)
- feat(v0.7.50): phishing federation v5 (3 source weighted voting, FREE-tier 3rd source, 2/2 PASS) (5057e77)
- feat(v0.7.50): cache dashboard HTML export (2/2 PASS, no regression) (24939df)
- feat(v0.7.50): cache trend ASCII chart (zero-dep visualization, 2/2 PASS) (7e41eaa)
- feat(v0.7.50): V-R13 layer 2 CLI (one-call URL verification, 2/2 PASS) (5b6c6f6)

### Changed

- release(v0.7.50): layer 2 CLI + trend ASCII chart + dashboard HTML + federation v5 + decay CSV (191/191 PASS) (00d2de4)

## [0.7.49] - 2026-06-16

### Added

- feat(v0.7.49): cache dashboard export (JSON + Markdown, 2/2 PASS) (5834a9a)
- feat(v0.7.49): cache analytics trend (snapshot over time, 2/2 PASS) (00a255d)
- feat(v0.7.49): V-R13 layer 2 full pipeline (one-call parse+dispatch+format, 2/2 PASS) (5726fc0)
- feat(v0.7.49): per-URL LFU decay score persistence (cache_lfu_decay_persist, 2/2 PASS) (d9e050b)
- feat(v0.7.49): phishing federation v4 (weighted voting, 2/2 PASS) (bd7c8cb)

### Changed

- release(v0.7.49): federation v4 + decay persistence + layer 2 pipeline + cache trend + dashboard export (181/181 PASS) (4093fcc)

## [0.7.48] - 2026-06-16

### Added

- feat(v0.7.48): CLI --cache-dashboard flag (cache_dashboard_cli module, 2/2 PASS) (83ee37a)
- feat(v0.7.48): phishing federation v3 (cross-source verification, 2/2 PASS) (ffacc80)
- feat(v0.7.48): per-strategy cache dashboard (cache_dashboard module, 2/2 PASS) (6d9ca13)
- feat(v0.7.48): LFUConfig + _save_cache full refactor (save_cache_lfu_decay_full, 2/2 PASS) (d27004f)
- feat(v0.7.48): V-R13 layer 2 commit-level diff integration (2/2 PASS) (9461ed1)

### Changed

- release(v0.7.48): V-R13 commit diff integration + LFU full refactor + cache dashboard + federation v3 + CLI flag (171/171 PASS) (74e3d59)

## [0.7.47] - 2026-06-16

### Added

- feat(v0.7.47): per-strategy eviction trigger by size cap (evict_lru/lfu_over_size, 2/2 PASS) (1c92875)
- feat(v0.7.47): per-strategy cross-strategy analytics (cache_analytics module, 2/2 PASS) (90f83fb)
- feat(v0.7.47): LFUConfig + _save_cache direct integration (cache_lfu_decay module, 2/2 PASS) (1a606ea)
- feat(v0.7.47): V-R13 layer 2 commit-level diff (cross-vendor, 2/2 PASS) (75be24c)

### Changed

- release(v0.7.47): V-R13 commit diff + LFU decay + ADR formal + analytics + eviction trigger (159/159 PASS) (a4e1522)
- docs(v0.7.47): ADR-023/024/025 revision log v0.2.1 (1 release cycle 운영 evidence) (1475374)

## [0.7.46] - 2026-06-16

### Added

- feat(v0.7.46): multi-source phishing federation v2 (extensible, 2/2 PASS) (e7a5919)
- feat(v0.7.46): Bitbucket v2 API commit history support (2/2 PASS) (cff0f2c)
- feat(v0.7.46): LFUConfig + temporal decay integration (4/4 PASS) (d5b1ddc)
- feat(v0.7.46): per-strategy cache size comparison (2/2 PASS) (0dffe7f)

### Changed

- release(v0.7.46): CLI test fix + cache size + LFU decay + Bitbucket v2 + federation v2 (149/149 PASS) (92d9c2d)
- test(v0.7.46): CLI --per-strategy + --cache-stats-strategy flag tests (2/2 PASS) (f4f0200)

## [0.7.45] - 2026-06-16

### Added

- feat(v0.7.45): CLI --per-strategy + --cache-stats-strategy flags (V-R10 v4) (c01d4f6)
- feat(v0.7.45): cache_stats_per_strategy_with_hit_rate (39/39 PASS) (1fde081)
- feat(v0.7.45): LRU/LFU split in cache_migration (split_to_per_strategy, 2/2 PASS) (5073cf7)
- feat(v0.7.45): multi-source phishing federation (PhishTank + OpenPhish, 2/2 PASS) (6533a4d)

### Changed

- release(v0.7.45): multi-source phishing federation + LRU/LFU split + hit rate + CLI --per-strategy (137/137 PASS) (43a0322)
- docs(v0.7.45): OKF quick-start walkthrough output examples + verification table (227e1e8)

## [0.7.44] - 2026-06-16

### Added

- feat(v0.7.44): cache_migration module (migrate v0.7.41 -> per-strategy, 1/1 PASS) (6726577)
- feat(v0.7.44): OpenPhish API integration (fetch_openphish_feed, 2/2 PASS) (27793af)
- feat(v0.7.44): lfu_integration module (LFUConfig + _save_cache, 2/2 PASS) (8eb116c)

### Changed

- release(v0.7.44): ADR-025 formal + OKF quick-start + LFUConfig + OpenPhish + cache migration (134/134 PASS) (d107dd3)

## [0.7.43] - 2026-06-16

### Added

- feat(v0.7.43): lfu_config module (V-R10 v3 LFU threshold tuning, 2/2 PASS) (53f774a)
- feat(v0.7.43): cache_stats_per_strategy (cross-strategy compare, 39/39 PASS) (e289b19)
- feat(v0.7.43): PhishTank API integration (fetch_phishtank_feed, 13/13 PASS) (df088ee)

### Changed

- release(v0.7.43): ADR-023/024 formal + ADR-025 quick-start draft + PhishTank API + cache_stats_per_strategy + lfu_config (129/129 PASS) (62a6507)

## [0.7.42] - 2026-06-16

### Added

- feat(v0.7.42): per-strategy cache file (cache_file_for_strategy helper, 38/38 PASS) (e80cca8)
- feat(v0.7.42): R-2 audit precise (git log --oneline, 16/16 PASS) (386d68c)
- feat(v0.7.42): V-R13 check 5 per-host extension (GitLab + Bitbucket API, 25/25 PASS) (64ca96c)

### Changed

- release(v0.7.42): ADR-023/024 formal + V-R13 per-host + V-R12 composite + R-2 audit precise + per-strategy cache (124/124 PASS) (f592bff)
- test(v0.7.42): V-R12 layer 1+2 composite URL emission (18/18 PASS) (77b0b87)

## [0.7.41] - 2026-06-16

### Added

- feat(v0.7.41): V-R12 composite layer 1+2 verification (check_url_semantic_composite, 23/23 PASS) (6a480ac)
- feat(v0.7.41): R-2 batch compliance audit (audit_r2_batch_history, 15/15 PASS) (a595fbb)
- feat(v0.7.41): V-R10 v3 per-strategy eviction metric (evictions_lru/evictions_lfu, 36/36 PASS) (46b6b7a)
- feat(v0.7.41): V-R13 ?range=A..B commit-level diff (git diff subprocess, 21/21 PASS) (6fcda94)

### Changed

- release(v0.7.41): ADR-020/021/022 formal + V-R13 range diff + per-strategy metric + R-2 audit + V-R12 composite (118/118 PASS) (62d6e9a)

## [0.7.40] - 2026-06-16

### Added

- feat(v0.7.40): R-2 batch compliance warning (5-15 page heuristic, 14/14 PASS) (85ecff6)
- feat(v0.7.40): CLI --semantic/--perform-head/--perform-github flags (18/18 PASS) (f4cf909)
- feat(v0.7.40): okf_export per-page ?range=<sha>..<sha> emission (V-R12 layer 2, 17/17 PASS) (e365168)
- feat(v0.7.40): V-R13 full 8/8 check (HEAD + GitHub API, 16/16 PASS) (7c69789)

### Changed

- release(v0.7.40): ADR-021/022 formal + V-R13 full 8/8 + V-R12 layer 2 + R-2 batch (110/110 PASS) (b98e1eb)

## [0.7.39] - 2026-06-16

### Added

- feat(v0.7.39): okf_export per-page ?hash=sha256:... emission (ADR-019 layer 1, 16/16 PASS) (dd8c177)
- feat(v0.7.39): phishing_keywords module + 11 tests (V-R11 v2 PoC, 11/11 PASS) (e1904fd)
- feat(v0.7.39): LFU eviction strategy + access_count tracking (34/34 PASS) (eab4d2e)
- feat(v0.7.39): check_url_semantic() PoC (6/8 check, 13/13 PASS) (563ac5c)

### Changed

- release(v0.7.39): V-R13 PoC + LFU cache + PhishTank + V-R12 carrier (102/102 PASS) (863c3b6)

## [0.7.38] - 2026-06-16

### Added

- feat(v0.7.38): _CacheLock stale lock file orphan cleanup (32/32 PASS) (9f622d3)
- feat(v0.7.38): cache gzip compression (4KB threshold, 31/31 PASS) (2e1a541)
- feat(v0.7.38): okf-bundle.yaml emit (per-bundle vcs_commit + integrity_hash, 15/15 PASS) (c3a0f24)
- feat(v0.7.38): _CacheLock timeout + advisory wait (30/30 PASS) (fbf93b5)
- feat(v0.7.38): per-page frontmatter vcs_commit + vcs_ref (12/12 PASS) (96b6ef0)
- feat(v0.7.38): cache_stats session evictions + last_eviction_timestamp (29/29 PASS) (d06053a)

### Changed

- release(v0.7.38): V-R13 formal + okf-bundle.yaml + cache gzip + lock orphan + OKF consumer guide (a04cf56)

## [0.7.37] - 2026-06-16

### Added

- feat(v0.7.37): okf_export vcs_commit integration (ADR-018, 11/11 PASS) (2eac0d3)
- feat(v0.7.37): --body CLI flag + --timeout flag (28/28 PASS) (1da10ef)
- feat(v0.7.37): cache_stats() extension (bytes + evictions_total, 27/27 PASS) (8e88b47)
- feat(v0.7.37): V-R12 commit-pinned URL (ADR-018 + 3 new tests, 9/9 PASS) (7aec7cf)
- feat(v0.7.37): V-R11 body content audit (ADR-017 + 5 new tests, 27/27 PASS) (9ec0aad)
- feat(v0.7.37): GHA actions/cache for cross-PR cache (ADR-016) (6a622ee)
- feat(v0.7.37): V-R10 v3 file lock (ADR-015 + 2 new tests, 22/22 PASS) (735beac)
- feat(v0.7.37): V-R10 v3 cache LRU (ADR-014 + 4 new tests, 20/20 PASS) (3349e79)

### Changed

- ci(v0.7.37): --body + --vcs-commit CI integration (f1a7bd3)

## [0.7.36] - 2026-06-16

### Added

- feat(v0.7.36): V-R10 v2 cache (ADR-013 + 4 new tests, 16/16 PASS) (5fec664)

### Changed

- chore(v0.7.36): version bump v0.7.35 to v0.7.36 + log entry for follow-up bundle (208042d)
- ci(v0.7.36): .github/workflows/okf-validate.yml (V-R10 online + cache + weekly cron) (c26349f)

## [0.7.35] - 2026-06-16

### Added

- feat(v0.7.35): V-R10 online HEAD layer (ADR-012 + 6 new tests, 12/12 PASS) (515a352)
- feat(v0.7.35): ADR-011 + OKF version auto-detect (5 new tests, 12/12 PASS) (e0f2ffc)
- feat(v0.7.35): ADR-010 + V-R10 URL validity lint (offline 8 check, 6/6 PASS) (077b5a4)

## [0.7.34] - 2026-06-16

### Added

- feat(v0.7.34): bundle root index.md auto-emit + test 10 (10/10 PASS) (2fb014e)
- feat(v0.7.34): ADR-008 accepted + path_resolver.py PoC + okf_export --no-resolve (24f8589)
- feat(v0.7.34): ADR-007 accepted + workflow_kit/okf_import.py PoC (7/7 PASS) (9e8b06d)

## [0.7.33] - 2026-06-16

### Changed

- chore(v0.7.33): ADR-006 accepted + Beta-v0.7.33 release note + version bump (00942ef)

## [0.7.32] - 2026-06-16

### Added

- feat(v0.7.32): TASK-V0731-001 log rotation + TASK-V0732-001 metrics aggregation + 10 smoke (5-run stable) (75a8b4c)

### Changed

- chore(v0.7.32): version bump 0.7.31 → 0.7.32 (auto-sync verified) + Beta-v0.7.32.md + state/work_backlog sync (ec72360)

## [0.7.31] - 2026-06-16

### Added

- feat(v0.7.31): TASK-V0729-001 run-time metrics + TASK-V0730-001 install-cron idempotency + 10 smoke (a9b510e)

### Changed

- chore(v0.7.31): version bump 0.7.30 → 0.7.31 (auto-sync verified) + Beta-v0.7.31.md + state/work_backlog sync (6732f48)

## [0.7.30] - 2026-06-15

### Added

- feat(v0.7.30): TASK-V0728-001 archive_stale_memory cron integration (mavis cron create/disable/list) + 5 smoke (57d996d)

### Changed

- chore(v0.7.30): version bump 0.7.29 → 0.7.30 (auto-sync verified) + Beta-v0.7.30.md + state/work_backlog sync (23a2078)

## [0.7.29] - 2026-06-15

### Added

- feat(v0.7.29): TASK-V0727-001 post-step 2-phase + amend integration (1 commit 통합, 33% 감소) + 5 smoke (850b798)

### Fixed

- fix(v0.7.29): rev-parse 2-step fix (full SHA → short=7) + state.json + backlog 정합 (2ee6dbf)

## [0.7.28] - 2026-06-15

### Added

- feat(v0.7.28): TASK-V0726-004 detached HEAD memory dir age-based auto-archive + 5 smoke (b1b32f1)

## [0.7.27] - 2026-06-15

### Added

- feat(v0.7.27): TASK-V0726-003 sync_release_hash post-step (release_pipeline.py version-bump auto-call) + 5 smoke (2aa1efa)

## [0.7.26] - 2026-06-15

### Added

- feat(v0.7.26): F-7 branch detection (detached HEAD → 7-char SHA) + F-7+ automated hash sync (infinite fix(state) loop 회피) + 10 smoke (e5fbd2b)

### Changed

- chore(v0.7.26): version bump 0.7.25 → 0.7.26 (auto-sync verified) + Beta-v0.7.26.md + state/work_backlog sync (ecb6ce1)

## [0.7.25] - 2026-06-15

### Added

- feat(v0.7.25): tools/migrate_legacy_l2.py (F-6 closure, 15 legacy L2 page → in-repo mirror) + 5 smoke (8a61bd3)

### Changed

- chore(v0.7.25): version bump 0.7.24 → 0.7.25 (auto-sync verified) + Beta-v0.7.25.md + state/work_backlog sync (96a919d)

## [0.7.24] - 2026-06-15

### Added

- feat(v0.7.24): cmd_release --notes-template flag (5 template: default/detailed/simple/changelog/custom) + 5 smoke (1dfa8fb)

### Changed

- chore(v0.7.24): version bump 0.7.23 → 0.7.24 (auto-sync verified) + Beta-v0.7.24.md + state/work_backlog sync (2c38d07)

## [0.7.23] - 2026-06-15

### Added

- feat(v0.7.23): tools/wiki_emit.py 1-command wrapper (3-step cycle: refresh_raw + emit_l2 + reemit_stubs) + 5 smoke (b4936a2)

### Changed

- chore(v0.7.23): version bump 0.7.22 → 0.7.23 (auto-sync verified) + Beta-v0.7.23.md + state/work_backlog sync (8e33940)

## [0.7.22] - 2026-06-15

### Changed

- chore(v0.7.22): version bump 0.7.21 → 0.7.22 (auto-sync verified) + Beta-v0.7.22.md + state/work_backlog sync (2d3cdbc)

### Fixed

- fix(v0.7.22): workflow_kit/common/linter.py .resolve() → .absolute() (mavis data dir 격리 환경 + macOS /var symlink fix) + 3 smoke (3c12950)

## [0.7.21] - 2026-06-15

### Changed

- chore(v0.7.21): version bump 0.7.20 → 0.7.21 (auto-sync verified) + Beta-v0.7.21.md + state/work_backlog sync (f014d59)

### Fixed

- fix(v0.7.21): cmd_release --allow-existing-tag flag + tag push 자동화 (pre-check + release coupling) (0ef97db)

## [0.7.20] - 2026-06-15

### Changed

- chore(v0.7.20): Beta-v0.7.20.md release note (release coordination observability + auto-bump chain) (5758657)
- chore(v0.7.20): version bump 0.7.19 → 0.7.20 (auto-bump chain) (556eb04)

## [0.7.19] - 2026-06-15

### Changed

- chore(v0.7.19): version bump 0.7.18 → 0.7.19 (release coordination auto-bump) (8ada0f1)

## [0.7.18] - 2026-06-15

### Added

- feat(v0.7.18): release coordination observability (_check_remote_tag + next_available_version + --auto-bump) + 7 smoke (07bf145)

### Changed

- chore(v0.7.18): version bump 0.7.17 → 0.7.18 (auto-sync verified) + Beta-v0.7.18.md + state/work_backlog sync (46066c3)

## [0.7.17] - 2026-06-15

### Added

- feat(v0.7.17): wiki in-repo storage isolation (5 file redirect + ai-workflow/wiki/sources/ 신규 + 11 smoke) (6f6f1af)

### Changed

- chore(v0.7.17): version bump 0.7.16 → 0.7.17 (auto-sync verified) + Beta-v0.7.17.md + state/work_backlog sync (4d09dee)

## [0.7.16] - 2026-06-15

### Added

- feat(v0.7.16): [tool.workflow-doctor] config thresholds/excluded_paths 적용 (B-1/B-2/B-3) + linter IndentationError fix + 9 smoke (33f5243)

### Changed

- chore(v0.7.16): version bump 0.7.15 → 0.7.16 (auto-sync verified) + Beta-v0.7.16.md + state/work_backlog sync (f012601)

## [0.7.15] - 2026-06-15

### Added

- feat(v0.7.15): atomic_write helper + changelog-gen --from-tag/--to-tag filter + 5 smoke (8d7acc4)
- feat(v0.7.15): atomic_write helper + changelog-gen --from-tag/--to-tag filter + 5 smoke (5cd1fe1)

### Changed

- chore(v0.7.15): version bump 0.7.14 → 0.7.15 (auto-sync verified) + Beta-v0.7.15.md (0dc813a)
- chore(v0.7.15): state sync (atomic_write 적용) + 1 daily backlog (3049651)
- chore(v0.7.15): version bump 0.7.14 → 0.7.15 (auto-sync verified) + Beta-v0.7.15.md (a369e7c)

### Fixed

- fix(v0.7.15): Beta-v0.7.15.md Commit table 정상화 (Deferred 표에서 중복 row 제거 + 4 commit hash) (68b0ae9)
- fix(v0.7.15): Beta-v0.7.15.md Commit section + 3 commit hash (3dfb5a1)

## [0.7.14] - 2026-06-15

### Added

- feat(v0.7.14): cmd_version_bump auto-sync workflow_kit/__init__.py + cmd_changelog_gen subcommand + 8 smoke (23eb7fd)

### Changed

- chore(v0.7.14): version bump 0.7.13 → 0.7.14 (auto-sync verified) + Beta-v0.7.14.md + CHANGELOG.md + state/work_backlog sync (63ab483)

### Fixed

- fix(v0.7.14): Beta-v0.7.14.md Commit + Reference section 정상화 (line 정렬 + 헤더) (29af65d)
- fix(v0.7.14): Beta-v0.7.14.md commit table TBD → 23eb7fd + 63ab483 (a01c7b4)

## [0.7.13] - 2026-06-15

### Added

- feat(v0.7.13): cmd_release --version flag (staging backfill, pyproject 일시 patch 불필요) (922ebc0)

### Changed

- chore(v0.7.13): state sync (v0.7.12 + v0.7.13 backfill) + 2 daily backlog (afc685a)
- chore(v0.7.13): version bump 0.7.11 → 0.7.13 + __version__ sync + Beta-v0.7.13.md (628bf93)

### Fixed

- fix(v0.7.13): Beta-v0.7.13.md Commit section + 3 commit hash (727c59c)

## [0.7.12] - 2026-06-15

### Added

- feat(v0.7.12): refresh_wiki_memory REPO_ROOT auto-detect (CLI flag > env var > git rev-parse > legacy fallback) + 4 smoke (63080ba)

### Changed

- chore(v0.7.12): v0.7.5~v0.7.10 release backfill (6 wheel/sdist + 6 git tag + 6 GH release) + Beta-v0.7.12.md 갱신 (89b7af5)

### Fixed

- fix(v0.7.12): Beta-v0.7.12.md commit table TBD → 89b7af5 (5b8e730)
- fix(v0.7.12): Beta-v0.7.12.md commit table TBD → 63080ba (0b3e704)

## [0.7.11] - 2026-06-15

### Added

- feat(v0.7.11): release_pipeline Phase 3 (dist subcommand) + state sync + 8 smoke (b2650f5)

### Changed

- chore(v0.7.11): version bump 0.7.10 → 0.7.11 + __version__ sync (ec407f1)

### Fixed

- fix(v0.7.11): cmd_verify --json field names (tag → tagName, createdAt → publishedAt) + release note commit table (aa4e837)

## [0.7.10] - 2026-06-14

### Added

- feat(v0.7.10): release_pipeline Phase 2 (release / verify / rollback) + 8 smoke test (fdf8159)

### Changed

- docs(v0.7.10): release note backfill + refresh_wiki_memory v0.7.10 tracking (fc87fdd)
- chore(v0.7.10): version bump 0.7.9 → 0.7.10 + release note (67d4a37)

## [0.11.9] - 2026-06-26

### Changed

- chore(v0.11.9): mypy strict 단계적 격상 23-24단계 (testing + runner) (41ef022)

## [0.11.8] - 2026-06-26

### Changed

- chore(v0.11.8): mypy strict 단계적 격상 21-22단계 (read_only_mcp_sdk + workflow_writes) (ae4058a)

## [0.11.7] - 2026-06-26

### Changed

- chore(v0.11.7): mypy strict 단계적 격상 19-20단계 (workflow_kit_cli + doc_sync) (5c82bc3)

## [0.11.6] - 2026-06-26

### Changed

- chore(v0.11.6): mypy strict 단계적 격상 17-18단계 (session_outputs + read_only_bundle) (c82bf72)

## [0.11.5] - 2026-06-26

### Changed

- chore(v0.11.5): mypy strict 단계적 격상 15-16단계 (decorators + linter) (1a7e665)

## [0.11.4] - 2026-06-26

### Changed

- chore(v0.11.4): mypy strict 단계적 격상 13-14단계 (output_contracts + milestones) (6f6bf38)

## [0.11.3] - 2026-06-26

### Changed

- chore(v0.11.3): mypy strict 단계적 격상 11-12단계 (purpose_ingest + purpose_graph) (bfbd100)

## [0.11.2] - 2026-06-26

### Added

- feat+chore(v0.11.2): cycle 4 deferred 통합 (graph_insights schema + 3 skill context load) (372b153)

## [0.11.17] - 2026-06-30

### Changed

- chore(v0.11.17): version bump + release note — mypy strict cumulative 25 error 격상 + schema drift housekeeping (3d3387d)

## [0.11.16] - 2026-06-27

### Added

- feat+chore(v0.11.16): cmd_release_status --auto-bump flag (read-only → opt-in write) (d81c639)

## [0.11.15] - 2026-06-26

### Added

- feat+chore(v0.11.15): release summary 1-line (jq-friendly verdict) (9ae4682)

## [0.11.14] - 2026-06-26

### Added

- feat+chore(v0.11.14): release-status dispatcher (신규 module mypy strict clean 2-layer defense 실증) (ed5148a)

## [0.11.13] - 2026-06-26

### Added

- feat+chore(v0.11.13): mypy CI cross-verify (Layer 1 ↔ Layer 2 정합 advisory) (b3075ef)

## [0.11.12] - 2026-06-26

### Added

- feat+chore(v0.11.12): mypy strict release-time gate (cmd_release pre-check 확장) (731b202)

## [0.11.11] - 2026-06-26

### Added

- feat+chore(v0.11.11): mypy strict CI 통합 (GH Actions mypy-strict workflow) (0994f14)

## [0.11.10] - 2026-06-26

### Changed

- chore(v0.11.10): mypy strict 단계적 격상 25-26단계 (project_docs + profiling) — FULL STRICT 도달 (b73799b)

## [0.11.1] - 2026-06-26

### Added

- feat+chore(v0.11.1): graph insights (R-A follow-up cycle 4) (fef6374)

## [0.11.0] - 2026-06-26

### Added

- feat+chore(v0.11.0): two-step CoT ingest (R-A follow-up cycle 3) (f71dde8)

### Changed

- docs(v0.11.0): plan two-step CoT ingest (R-A follow-up cycle 3) (f4eeba2)

## [0.10.4] - 2026-07-03

### Added

- feat: CodeWhale harness support (v0.10.4) - HARNESS_SPECS+SUPPORTED_HARNESSES+builder registration - single SKILL.md overlay (Constitution handles verification/parallelism/context) - additive rules only: session start, Korean output, backlog mgmt - harness docs + apply guide + distribution spec (cf0060d)

## [0.10.3] - 2026-06-24

### Added

- feat+chore(v0.10.3): wiki file deletion cascade cleanup (R-A follow-up cycle 2) (3ca3a49)

## [0.10.2] - 2026-06-24

### Added

- feat+chore(v0.10.2): delivery layer 확장 (claude-code 진입점 정정 + aider/goose/custom + self-bootstrap) (c657853)

## [0.10.1] - 2026-06-24

### Added

- feat+chore(v0.10.1): skill-only entry mode + claude-code adapter (SemVer minor) (afccdab)

## [0.10.0] - 2026-06-24

### Added

- feat+chore(v0.10.0): deprecation 1st + 2nd cycle 동시 종료 (SemVer major) (c5fb94c)
