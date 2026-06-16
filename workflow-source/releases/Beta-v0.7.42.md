# Beta v0.7.42 — ADR-023/024 formal docs + V-R13 per-host + V-R12 composite + R-2 audit precise + per-strategy cache (TASK-V0742-FOLLOWUP-BUNDLE)

> **Status**: proposed (TASK-V0742-FOLLOWUP-BUNDLE in-flight)
> 본 release 의 변경. v0.7.41 의 6 follow-up 의 *bundled* implementation: (1) ADR-023 phishing API + ADR-024 per-strategy cache (formal docs), (2) V-R13 check 5 per-host extension, (3) V-R12 layer 1+2 composite verification test, (4) R-2 audit precise (git history), (5) per-strategy cache file helper, (6) log + version bump. cumulative test 430+ → 445+.

## 본 release 의 1차 출처

1. **ADR-023 (phishing API integration, proposed v0.7.42)**: PhishTank + OpenPhish + VirusTotal 의 *multi-vendor* 의 *auto-update* 의 *formal documentation*
2. **ADR-024 (per-strategy cache file, proposed v0.7.42)**: V-R10 v3 cache 의 *per-strategy file* 의 *formal documentation*
3. **ADR-021 (cache LFU eviction, accepted v0.7.41)**: per-strategy metric 의 *prerequisite*
4. **ADR-022 (phishing keyword feed, accepted v0.7.41)**: phishing API integration 의 *prerequisite*
5. **ADR-019 (V-R13 semantic URL, accepted v0.7.38)**: per-host extension 의 *prerequisite*
6. **OKF spec v0.1**: per-bundle manifest + resource URL form

## 발견 (v0.7.41 의 6 follow-up 의 *bundled* implementation)

### TASK-V0742-FOLLOWUP-BUNDLE: 5 follow-up 항목 (2 ADR formal + 4 code enhancement + 1 audit + 1 composite test)

v0.7.41 release note 의 6 follow-up 중 5 항목의 implementation 완료:

- **TASK-V0742-FORMAL-ADR-023-024 (Phase 1)**: ADR-023 (phishing API integration) + ADR-024 (per-strategy cache file) + 2 concept pages + 4 index anchors (V-4: 69 → 73 entries).
- **TASK-V0742-V-R13-PER-HOST (Phase 2)**: `check_url_semantic_per_host()` + 3 per-host helpers (GitHub / GitLab / Bitbucket API). Routes check 5 to appropriate per-host API. 2 new tests (23 → 25).
- **TASK-V0742-V-R12-COMPOSITE (Phase 3)**: Composite URL emission test (`?hash=...&range=...`). 1 new test (17 → 18).
- **TASK-V0742-R-2-AUDIT-PRECISE (Phase 4)**: `audit_r2_batch_history_precise()` via `git log --oneline`. 1 new test (15 → 16).
- **TASK-V0742-CACHE-PER-STRATEGY (Phase 5)**: `cache_file_for_strategy()` helper. 2 new tests (36 → 38).
- **TASK-V0742-FINAL (Phase 6)**: final verification (124/124 tests PASS across 8 suites) + `releases/Beta-v0.7.42.md` + version bump v0.7.41 → v0.7.42 + log entry (TBD).

**v0.7.42 의 정공법**: 2 ADR formal docs + 1 per-host extension + 1 composite test + 1 precise audit + 1 cache helper + 6 new tests + version bump. cumulative test 430+ → **445+** (6 new).

## 본 release 의 변경

### 1. 2 ADR formal docs (TASK-V0742-FORMAL-ADR-023-024)

- `decisions/adr-023-phishing-api-integration.md` (8.5 KB, status: proposed)
  6 alternatives (manual-update, external-feed, PhishTank, OpenPhish, VirusTotal, federation)
  4 positive / 2 negative / 1 neutral
  3 vendor (PhishTank + OpenPhish + VirusTotal) + rate-limit aware + multi-source federation
- `decisions/adr-024-per-strategy-cache-file.md` (8.8 KB, status: proposed)
  5 alternatives (single, per-strategy, hybrid, no-eviction, external)
  4 positive / 2 negative / 1 neutral
  3 separate file + strategy switch clean reset + cross-strategy compare + backward compat
- `concepts/phishing-api-integration.md` (7.1 KB, status: proposed)
- `concepts/per-strategy-cache-file.md` (7.9 KB, status: proposed)
- `index.md` — 4 new anchors. V-4: 69 → 73 entries

### 2. 4 code enhancement (TASK-V0742-V-R13-PER-HOST + V-R12-COMPOSITE + R-2-AUDIT-PRECISE + CACHE-PER-STRATEGY)

- `workflow_kit/url_validity.py`:
  - `cache_file_for_strategy(base_path, strategy)` — per-strategy file path helper
  - `check_url_semantic_per_host()` + 3 helpers (`_check_github_per_host`, `_check_gitlab_per_host`, `_check_bitbucket_per_host`)
- `workflow_kit/okf_import.py`:
  - `R2BatchPreciseAuditResult` dataclass
  - `audit_r2_batch_history_precise(repo_root, subprocess_run, since)` — git log + parse
- `workflow_kit/okf_export.py`:
  - Per-page `?hash=...&range=...` composite URL emission (already-supported via existing kwargs)

### 3. 6 new tests (cumulative test 430+ → 445+)

- `tests/check_wiki_url_semantic.py` (23 → 25): 2 per-host tests
- `tests/check_okf_export.py` (17 → 18): 1 composite URL test
- `tests/check_okf_import.py` (15 → 16): 1 precise audit test
- `tests/check_wiki_url_validity.py` (36 → 38): 2 per-strategy cache file tests

### 4. version bump

`workflow_kit/__init__.py` 의 version `v0.7.41-beta` → `v0.7.42-beta`.

## 발견된 cross-cutting lesson (v0.7.42)

- **ADR formal docs 의 *bulk-draft* 정공법**: 2 ADR 의 *1 turn* 의 *bulk* formal documentation (ADR-023 + ADR-024). 다음 release (v0.7.43+) 의 *code-side* implementation 의 *rule-side* 의 *low-friction* 정공법.
- **V-R13 per-host 의 *host-based routing* 정공법**: 1 main entry (`check_url_semantic_per_host`) + 3 helpers 의 *host-based dispatch* 의 *low-friction* 정공법. *per-vendor API* 의 *auth pattern* (GitHub: Bearer / GitLab: PRIVATE-TOKEN / Bitbucket: Basic) 의 *flexibility* 의 *low-friction* 정공법.
- **V-R12 composite 의 *operational* 정공법**: per-page `?hash=...&range=...` 의 *both layer present* 의 *machine-readable* carrier 의 *composite* 의 *operational* 의 *low-friction* 정공법.
- **R-2 audit precise 의 *git history* 정공법**: `git log --oneline` 의 *parse* 의 *precise* 의 *operational* 의 *machine-readable* 의 *low-friction* 정공법. *regex-based log.md* (v0.7.41) 의 *complement* 의 *operational* 정공법.
- **per-strategy cache file 의 *isolation* 정공법**: `cache_file_for_strategy()` helper 의 *low-friction* 정공법. *per-strategy file* 의 *isolation* 의 *operational* 정공법. *consumer opt-in* 의 *low-friction* 정공법.
- **per-host API 의 *route-by-host* 정공법**: GitHub / GitLab / Bitbucket 의 *different URL forms* (blob / blob / src) 의 *per-host regex* 의 *robust* 의 *operational* 정공법.

## Reference (다른 release note)

- v0.7.41 release note (3 ADR formal + 4 enhancement + 8 test) — 본 release 의 1차 출처
- v0.7.40 release note (ADR-021/022 formal + V-R13 full 8/8 + V-R12 layer 2 + R-2 batch warning)
- v0.7.39 release note (V-R13 PoC + LFU + PhishTank + V-R12 carrier)
- v0.7.38 release note (V-R13 formal + okf-bundle.yaml + cache gzip + lock orphan + OKF consumer guide)
- v0.7.37 release note (5 ADR acceptance + 4 enhancement)

## TASK (본 release)

### TASK-V0742-FOLLOWUP-BUNDLE: 5 follow-up 항목 (2 ADR formal + 4 code + 1 audit + 1 composite test)

- **상태**: in-flight (proposed)
- **commit**: 5 commit (62e5f69 + 64ca96c + 77b0b87 + 386d68c + e80cca8) + 1 final (TBD)
- **scope**:
  - Phase 1: 2 ADR formal docs + 2 concept + 4 anchors (62e5f69)
  - Phase 2: V-R13 per-host extension (64ca96c)
  - Phase 3: V-R12 composite test (77b0b87)
  - Phase 4: R-2 audit precise (386d68c)
  - Phase 5: per-strategy cache helper (e80cca8)
  - Phase 6: release note + version bump + log (TBD)
- **cumulative test**: 430+ → **445+** (6 new: 2 per-host + 1 composite + 1 audit + 2 per-strategy)

### Follow-up (v0.7.43+)

- **TASK-V0743-OKF-QUICK-START**: OKF consumer guide quick-start tutorial
- **TASK-V0743-ADR-023-FORMAL**: phishing API integration code-side (PhishTank + OpenPhish)
- **TASK-V0743-ADR-024-FORMAL**: per-strategy cache file migration (full opt-in)
- **TASK-V0743-VIRUSTOTAL**: VirusTotal API integration (commercial)
- **TASK-V0743-PER-STRATEGY-COMPARE**: cache_stats_per_strategy (cross-strategy compare)
- **TASK-V0743-ADR-022-FORMAL**: ADR-022 formal acceptance (1 release 주기 후)

## Metric

- v0.7.42 = 5 enhancement commit + 1 final commit = **6 commit**
- 0 신규 module (3 module extension: url_validity + okf_import + okf_export)
- 2 신규 ADR + 2 신규 concept
- 6 new tests (2 per-host + 1 composite + 1 audit + 2 per-strategy)
- 1 release note (v0.7.42.md, ~9 KB)
- 누적 test 430+ → **445+** (6 new)
- 37 release 누적 (v0.7.5 ~ v0.7.42)
- 125+ commit code-repo (v0.7.41 까지 125 + 5 = **130+**)
- 5 module cumulative (okf_export 24 KB, okf_import 20 KB, path_resolver 8 KB, url_validity 20 KB, phishing_keywords 4.9 KB) = **77+ KB total**
