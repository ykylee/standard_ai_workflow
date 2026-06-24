# Beta v0.10.3 — Wiki file deletion cascade cleanup (R-A follow-up cycle 2) (2026-06-24)

> **SemVer minor** (v0.10.2 → v0.10.3) — v0.9.2 cycle 1 (외부 reference concept 흡수) 의 후속. **`wiki-event-sync.py` 의 3-method matching 을 `workflow_kit.common.wiki_cascade` 로 흡수** (delete 방향). *file deletion cascade cleanup* 정공법: source file 삭제 시 wiki page cascade-delete 대상 식별 + destructive subcommand 정공법 (apply=False default dry-run). **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (1 신규 helper + 1 CLI subcommand + 1 spec layer extension + 7 acceptance test)

### 1. Wiki file deletion cascade cleanup (R-A follow-up cycle 2)

**v0.9.2 cycle 1 (PURPOSE.md concept 흡수) 의 후속** — Karpathy `llm-wiki.md` + llm_wiki (nashsu) 의 *wiki 운영 R-1~R9 cycle* 의 *file deletion cascade* 정공법을 standard_ai_workflow 에 흡수.

**기존 wiki 운영 도구**:
- `~/wiki/skills/wiki-event-sync/scripts/wiki-event-sync.py` — *edit* 방향 3-method matching (commit / push / PR / merge / release 시 영향 page 식별)
- **본 release (v0.10.3)** — *delete* 방향 3-method matching (source file 삭제 시 cascade-delete 대상 wiki page 식별) + destructive subcommand 정공법 (apply=False default dry-run)

**`workflow_kit.common.wiki_cascade` helper module 신규** (≈ 200 line):
- `file_to_stem(path: str) -> str` — kebab-case + lower SSOT. 예: `"workflow-source/core/v0_9_0_deprecation_policy_spec.md"` → `"workflow-source-core-v0-9-0-deprecation-policy-spec"`
- `find_cascade_targets(deleted_path, wiki_root, project)` — 3-method matching (basename + stem + project-relative) 으로 cascade-delete 대상 식별. dedup 시 `Path.samefile()` 사용 (case-insensitive filesystem 정합)
- `emit_cascade_plan(deleted_paths, wiki_root, project)` — 다중 deleted_paths 의 JSON plan emit
- `apply_cascade(targets, apply=False)` — destructive subcommand 정공법 (apply=False default dry-run, --apply 명시 시 실제 delete)
- `render_cascade_plan_text(plan)` — human-readable text render (advisory emit)

**3-method matching** (wiki 운영 R-1~R9 cycle 2 정공법):
1. **(1) basename** — `Path(deleted_path).name` 그대로 매치 (legacy v0.1.0 rule)
2. **(2) stem** — `file_to_stem(deleted_path)` 으로 kebab-case + lower 변환 후 매치
3. **(3) project-relative stem** — `project/<prefix>/<rest>` 형태 prefix 제거 후 stem 변환. v0.9.2 L3 raw mirror 구조 (`raw/projects/<project>/...`) 정합

**Bug 발견 + fix** (v0.10.3 acceptance test 작성 중):
- `Path(deleted_path).name` 가 이미 `.md` 확장자 포함 → `f"{p.name}.md"` 는 `AGENTS.md.md` 가 됨 (이중 .md). fix: `wiki_root / p.name` (확장자 추가 안 함)
- macOS case-insensitive filesystem 에서 `AGENTS.md` 와 `agents.md` 가 같은 file → dedup 필요. fix: `Path.samefile()` 기반 dedup
- v0.9.2 L3 raw mirror 의 `raw/projects/<project>/` prefix 매칭 누락 → fix: project-relative prefix 후보에 추가

### 2. CLI dispatcher subcommand `cascade-delete` (v0.10.3+ 신규)

`workflow_kit/workflow_kit_cli.py` 의 dispatcher registry 에 subcommand 32 신규:

- `--deleted-paths=PATH` (repeatable, ≥1 required) — 삭제된 source file path
- `--wiki-root=PATH` (required) — wiki vault 의 *project source* 디렉토리
- `--project=SLUG` (optional) — project slug (project-relative matching 용)
- `--apply` (default dry-run) — destructive subcommand 정공법 memory #5 정합
- `--json` (optional) — JSON output

**destructive subcommand 정공법** (memory #5):
- `apply=False` (default) — prompt + distribution preview 만 emit, file I/O ❌
- `--apply` 명시 시 — 실제 delete, `executed` list emit (per plan), `skipped` list emit (apply=False 시)
- **3-step crash safety**: 적용 안 함 (cascade-delete 는 단순 unlink 1 operation)

### 3. Spec layer 갱신 (1 spec)

| Spec | Section | 변경 |
|---|---|---|
| `llm_wiki_concept_purpose_spec.md` | §4.4 (R-A trigger) §6 cross-reference | R-A follow-up cycle 2 (file deletion cascade cleanup) 7 detail 명시 + `workflow_kit/common/wiki_cascade.py` + `cmd_cascade_delete` + test file cross-ref |

## 운영 누적 (v0.10.2 → v0.10.3)

| | v0.10.2 | **v0.10.3** |
|---|---|---|
| **SemVer bump** | minor | **minor** |
| **`workflow_kit.common.wiki_cascade`** | ❌ | **✅ (5 함수 + CascadeTarget / CascadeResult dataclass)** |
| **`cmd_cascade_delete` subcommand** | ❌ | **✅ (subcommand 32, destructive 정공법 정합)** |
| **HARNESS_FILE_BUILDERS** | 10 | **10** (변동 ❌) |
| **SessionStartOutput self_bootstrap** | ✅ | **✅** (변동 ❌) |
| **cumulative acceptance** | 56/56 | **63/63** (v0.10.3 7 신규 + v0.10.2 9 + v0.10.1 6 + v0.10.0 6 + v0.9.6 6 + v0.9.5 환경의존 3 + v0.9.4 3 + v0.9.2 8 + v0.9.3 4 + v0.9.1 4 + v0.9.0 6 + deprecation contract 4 갱신 = 63) |
| **spec §9 acceptance** | 12/12 | **12/12** (변동 ❌) |
| **breaking change** | none | **none** (default dry-run, v0.10.2 호환) |

## Test 결과

- 신규 (7 PASS, v0.10.3):
  - `test_file_to_stem_v0_10_3` — `file_to_stem` SSOT (basename / nested path / lowercase / 중복 dash / 비-alphanumeric 5 case)
  - `test_find_cascade_targets_3_methods_v0_10_3` — 3-method matching (basename + stem + project-relative) 3 case verify
  - `test_cascade_graceful_missing_v0_10_3` — 부재 / wiki_root 부재 / deleted_path empty 시 graceful skip + advisory warning
  - `test_emit_cascade_plan_v0_10_3` — 다중 deleted_paths 의 plan emit (deleted_count + total_targets + plans + warnings)
  - `test_apply_cascade_destructive_pattern_v0_10_3` — apply=False (default) dry-run, apply=True 실제 delete + 재감지 (cascade 대상 0)
  - `test_render_cascade_plan_text_v0_10_3` — human-readable text render (advisory 정합)
  - `test_cascade_delete_cli_registered_v0_10_3` — CLI subcommand 등록 + dry-run subprocess verify (file 보존)
- v0.10.2 회귀: **9/9 PASS** ✅
- v0.10.1 회귀: **6/6 PASS** ✅
- v0.10.0 회귀: **6/6 PASS** ✅
- v0.9.6 회귀: 6/6 PASS ✅
- v0.9.4 회귀: **3/3 PASS** ✅
- v0.9.2 회귀: **8/8 PASS** ✅
- v0.9.1 deprecation contract: **4/4 PASS** ✅
- 누적 acceptance: **63/63 PASS**
- 누적 smoke: **162/162 + 63 별도 subset** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3 + v0.9.5 6 + v0.9.6 6 + v0.10.0 6 + v0.10.1 6 + v0.10.2 9 + v0.10.3 7)

## 변경 파일 (3 변경 + 2 신규)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/workflow_kit/workflow_kit_cli.py` | `cmd_cascade_delete` 등록 (subcommand 32) + docstring + usage 표 갱신 |
| M | `workflow-source/pyproject.toml` | version 0.10.2 → 0.10.3 |
| M | `workflow-source/workflow_kit/__init__.py` | `_read_pyproject_version` loud fallback literal `"v0.10.2-beta"` → `"v0.10.3-beta"` (suffix 정상) |
| A | `workflow-source/workflow_kit/common/wiki_cascade.py` | helper module 신규 (5 함수 + 2 dataclass, ≈ 230 line) |
| A | `workflow-source/tests/check_wiki_cascade_cleanup_v0_10_3.py` | 신규 (7 acceptance test, ≈ 250 line) |
| A | `workflow-source/releases/Beta-v0.10.3.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.10.3/backlog/2026-06-24.md` | v0.10.3 plan |
| M | `README.md` | §0 (버전) + §10 (v0.8.0 → v0.10.3 누적 변경 요약, v0.10.3 entry 추가) + release URL list 갱신 |
| M | `ai-workflow/memory/active/work_backlog.md` | v0.10.3 index entry 추가 + 최종 수정일 갱신 |

## 다음 (v0.10.4+ / v1.0.0)

1. **v0.10.4 follow-up** — external reference 흡수 cycle 3: two-step CoT ingest (session-start → backlog-update 2-step contract) 명문화.
2. **v0.10.5 follow-up** — external reference 흡수 cycle 4: graph insights (surprising + gaps) 정형화.
3. **v0.10.6 follow-up** — release pipeline 의 `--apply default=False` 전환 (memory #5 의 "destructive subcommand 정공법" 정착). breaking change 회피로 minor release 에서 점진적 전환.
4. **v0.10.7 follow-up** — mypy strict cumulative 격상 (19 → 20-21 file). 1 release = 1-2 file 단계적 격상.
5. **v1.0.0 milestone** — full mypy strict 도달 (semver major 정렬, 100+ release 후 예상). spec §9 acceptance 12/12 도달 유지.
