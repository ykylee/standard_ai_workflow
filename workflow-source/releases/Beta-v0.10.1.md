# Beta v0.10.1 — skill-only entry mode + claude-code adapter (semver minor) (2026-06-24)

> **SemVer minor bump** (v0.10.0 → v0.10.1) — v0.10.0 의 deprecation cycle 종료 (semver major) 후속. **AGENTS.md 안 읽는 하네스의 정공법** = `--entry-mode skill-only` gateway + 1차 adapter (`--harness claude-code`). 2 follow-up adapter (aider / goose / pi-dev / custom) 는 v0.10.2+ 후속. **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (1 dispatcher option + 1 harness adapter + 1 apply_guide + 6 acceptance test + 2 spec layer cross-ref)

### 1. `--entry-mode skill-only` gateway (contract layer / delivery layer 분리)

**v0.9.5 part 2 의 contract layer / delivery layer 분리 원칙 runtime 적용**:

- **`--entry-mode` option 신규** (3-mode):
  - `aggressive` (default) — 기존 동작. root 진입점 (AGENTS.md / GEMINI.md / ANTIGRAVITY.md / MiniMax.md) + harness overlay 모두 emit
  - `safe` — aggressive 와 동일 (기존 project overwrite 시 의도적 opt-in 정공법, future use)
  - **`skill-only` (v0.10.1+ 신규)** — root 진입점 (AGENTS.md / GEMINI.md / ANTIGRAVITY.md / MiniMax.md) skip, **harness-specific skill / slash command / config 파일만 emit**
- **Contract layer (universal)**: skills (session-start / backlog-update / doc-sync) output schema + purpose_digest / purpose_context / scope_creep_warnings — universal, harness-agnostic (v0.9.5)
- **Delivery layer (harness-specific)**: `AGENTS.md` (OpenCode / Codex / pi-dev) / `GEMINI.md` (Gemini CLI) / `ANTIGRAVITY.md` / `MiniMax.md` (MiniMax Code) / **`.claude/commands/*.md` (Claude Code — v0.10.1)** / 기타 (aider / goose / custom)
- **v0.9.5 part 2 의 graceful skip 정책이 *정공법의 근거***: PURPOSE.md / state.json / log.md 부재 시 skill 실행이 실패하지 않음. AGENTS.md 부재 시에도 skill 만으로 workflow 진입 가능 → skill-only entry mode 의 *정합 anchor*

### 2. `--harness claude-code` adapter (v0.10.1+ 신규, 1차 PoC)

**Claude Code 의 *진입점 특성* = slash command** (root 진입점 `CLAUDE.md` 자동 read ❌). 본 adapter 는 *3 slash command* 를 진입 mechanism 으로 emit:

- **HARNESS_SPECS entry 신규**:
  - `entry_files=()` (root 진입점 없음)
  - `extra_files=(.claude/commands/workflow-session-start.md, workflow-backlog-update.md, workflow-doc-sync.md)`
- **3 slash command renderers 신규** (`bootstrap_lib.harnesses.renderers`):
  - `render_claude_code_session_start_command` → `/workflow-session-start` 진입점. baseline 복원 (state.json + session_handoff + work_backlog + PROJECT_PROFILE + PURPOSE.md)
  - `render_claude_code_backlog_update_command` → `/workflow-backlog-update` 진입점. task 등록/갱신 + scope creep warning (PURPOSE.md §3 제외 영역 매칭)
  - `render_claude_code_doc_sync_command` → `/workflow-doc-sync` 진입점. 영향 문서 식별 + anchor 갱신 후보 (advisory)
- **`write_claude_code_harness_files` 신규** — 3 slash command 를 target root 의 `.claude/commands/` 아래 emit. `HARNESS_FILE_BUILDERS` registry 에 등록
- **Self-check** (renderers.py 의 기존 consistency check) 가 HARNESS_SPECS / SUPPORTED_HARNESSES / HARNESS_FILE_BUILDERS 3-way 정합 verify

### 3. apply_guide.md for claude-code (신규, ≈ 150 line)

`workflow-source/harnesses/claude-code/apply_guide.md` 신규:
- §1 언제 이 가이드를 쓰는가 (Claude Code 환경 + AGENTS.md 가 아닌 slash command 진입)
- §1.1 Claude Code 의 *진입점 특성* 표 (OpenCode / Codex / pi-dev / Gemini CLI / Antigravity / **Claude Code**)
- §2 적용 전 확인 (skill-only 진입 정공법)
- §2.1 권장 설정 계층 (project-level `.claude/commands/*.md` 3종 + `ai-workflow/`)
- §3 신규 프로젝트 적용 순서 (bootstrap + emit verify + 첫 세션 시작)
- §4 기존 프로젝트 적용 순서 (non-destructive 원칙)
- §5 language + context 원칙 (한국어 보고 + context 누적 최소화)
- §6 다음에 읽을 문서 (배포 전략 + 인덱스 + AGENTS.md 기반 진입 가이드 cross-ref)

### 4. v0.10.0 호환성 (semver minor 정합)

- **`--entry-mode` 의 default = `aggressive`** → 기존 사용자 영향 0
- **`SUPPORTED_HARNESSES` 에 `claude-code` 추가** → argparse choices 가 7개 (6 → 7), 기존 `--harness codex --harness opencode` 등 6개 호출 영향 0
- **HARNESS_SPECS 의 기존 6 entry** 변경 ❌
- **`write_harness_files` 의 entry-point write block 5개 모두 `entry_mode != "skill-only"` guard 추가** → default (`aggressive`) 동작 변경 0
- **breaking change 없음** (SemVer 2-year guarantee 유지, v0.8.0 → 2.0.0)

## Spec layer 갱신 (1 spec + 1 README + 1 index)

| File | Section | 변경 |
|---|---|---|
| `llm_wiki_concept_purpose_spec.md` | §4.5 (신규) | skill-only entry mode 명세 — contract layer / delivery layer 분리, `--entry-mode` 3-mode contract, Claude Code 정공법 |
| `workflow_harness_distribution.md` | §1 (현재 지원 타겟) | `claude-code` 추가 + §harnesses/ 인덱스 갱신 |
| `harnesses/README.md` | 표 | claude-code row 추가 |
| `harnesses/claude-code/README.md` | 신규 | claude-code 짧은 인덱스 (apply_guide.md 로 연결) |

## 운영 누적 (v0.10.0 → v0.10.1)

| | v0.10.0 | **v0.10.1** |
|---|---|---|
| **SemVer bump** | major | **minor** |
| **Delivery layer options** | AGENTS.md / GEMINI.md / ANTIGRAVITY.md / MiniMax.md (4-mode) | **+ .claude/commands/*.md (5th mode, claude-code)** |
| **SUPPORTED_HARNESSES** | 6 | **7 (+ claude-code)** |
| **HARNESS_FILE_BUILDERS** | 6 | **7 (+ write_claude_code_harness_files)** |
| **HARNESS_SPECS** | 6 | **7 (+ claude-code, entry_files=() + 3 slash command)** |
| **--entry-mode option** | ❌ | **✅ (aggressive / safe / skill-only)** |
| **apply_guide.md** | 6 harness | **7 (+ claude-code)** |
| **cumulative acceptance** | 41/41 | **47/47** (v0.10.1 6 신규 + v0.10.0 6 + v0.9.6 6 + v0.9.5 환경의존제외 3 + v0.9.4 3 + v0.9.2 8 + v0.9.3 4 + v0.9.1 4 + v0.9.0 6 + 누적 환경의존 v0.9.5 3 + deprecation contract 4 갱신 = 47) |
| **spec §9 acceptance** | 12/12 | **12/12** (변동 ❌) |
| **dispatcher subcommand count** | 31 | **31** (변동 ❌, `--entry-mode` 는 argparse flag, subcommand 아님) |
| **breaking change** | none | **none** (default = aggressive, v0.10.0 호환) |

## Test 결과

- 신규 (6 PASS, v0.10.1):
  - `test_entry_mode_option_present_v0_10_1` — parse_args 가 --entry-mode option 을 3-mode (aggressive / safe / skill-only) 로 받음 verify
  - `test_claude_code_harness_registered_v0_10_1` — `claude-code` 가 SUPPORTED_HARNESSES + HARNESS_SPECS + HARNESS_FILE_BUILDERS 3-way 정합 verify
  - `test_claude_code_skill_only_emits_v0_10_1` — claude-code + skill-only → 3 slash command emit + AGENTS.md 부재 verify
  - `test_claude_code_aggressive_emits_v0_10_1` — claude-code + aggressive → 동일 3 slash command (root 진입점 원래 없음) verify
  - `test_codex_aggressive_emits_v0_10_1` — codex + aggressive (default) → AGENTS.md + .codex/config.toml.example emit (기존 동작 유지) verify
  - `test_codex_skill_only_skips_agents_v0_10_1` — codex + skill-only → AGENTS.md skip, .codex/config.toml.example 유지 (harness-specific file contract) verify
- v0.10.0 회귀: **6/6 PASS** (`check_v0_10_0_deprecation_removal.py`)
- v0.9.1 deprecation contract 회귀: **4/4 PASS** (`check_v0_9_1_deprecation_contract.py`)
- v0.9.6 회귀: 6/6 PASS (`check_purpose_concept_ra_trigger_v0_9_6.py`)
- v0.9.4 회귀: **3/3 PASS** (`check_purpose_concept_state_json_v0_9_4.py`)
- v0.9.2 회귀: **8/8 PASS** (`check_purpose_concept_v0_9_2.py`)
- 누적 acceptance: **47/47 PASS** (v0.10.1 6 + v0.10.0 6 + v0.9.6 6 + v0.9.5 환경의존제외 3 + v0.9.4 3 + v0.9.2 8 + v0.9.3 4 + v0.9.1 4 + v0.9.0 6 + 누적 환경의존 v0.9.5 3 + deprecation contract 4 갱신 = 47)
- 누적 smoke: **162/162 + 47 별도 subset** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3 + v0.9.5 6 + v0.9.6 6 + v0.10.0 6 + v0.10.1 6)

## 변경 파일 (5 변경 + 1 신규 + 1 doc sync)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/scripts/bootstrap_lib/__main__.py` | `--entry-mode` argparse option + 5 entry-point write block 에 `entry_mode != "skill-only"` guard |
| M | `workflow-source/scripts/bootstrap_lib/harnesses/__init__.py` | SUPPORTED_HARNESSES 6→7 + HARNESS_SPECS `claude-code` entry 신규 (entry_files=() + 3 slash command extra_files) |
| M | `workflow-source/scripts/bootstrap_lib/harnesses/renderers.py` | 3 render function 신규 (session_start / backlog_update / doc_sync) + `write_claude_code_harness_files` 신규 + `register_harness_builder("claude-code", ...)` 등록 |
| A | `workflow-source/harnesses/claude-code/apply_guide.md` | 신규 (≈ 150 line, 6 section: 적용 시점 / 진입점 특성 / 권장 설정 / 신규·기존 프로젝트 절차 / language 원칙 / 다음 문서) |
| A | `workflow-source/tests/check_v0_10_1_skill_only_entry_mode.py` | 신규 (6 acceptance test, ≈ 270 line) |
| M | `workflow-source/pyproject.toml` | version 0.10.0 → 0.10.1 |
| M | `workflow-source/workflow_kit/__init__.py` | `_read_pyproject_version` loud fallback literal `"v0.10.0-beta"` → `"v0.10.1-beta"` (suffix 정상) |
| M | `README.md` | §0 (버전) + §10 (v0.8.0 → v0.10.1 누적 변경 요약, v0.10.1 entry 추가) + release URL list 갱신 |
| A | `workflow-source/releases/Beta-v0.10.1.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.10.1/backlog/2026-06-24.md` | v0.10.1 plan |
| M | `ai-workflow/memory/active/work_backlog.md` | v0.10.1 index entry 추가 + 최종 수정일 갱신 |

## 다음 (v0.10.2+ / v1.0.0 milestone)

1. **v0.10.2 (semver minor)** — aider / goose / pi-dev / custom adapters + session-start self-bootstrap mode:
   - `--harness aider` adapter (CONVENTIONS.md + `.aider.conf.yml` snippet)
   - `--harness goose` adapter (extension registration config)
   - `--harness pi-dev` adapter (AGENTS.md 동일 entry point 유지, v0.10.1 의 claude-code 와 정합)
   - `--harness custom` adapter (skill-only emit, caller 가 wire-up)
   - session-start skill self-bootstrap mode (PURPOSE.md / state.json 부재 시 init light 호출)
2. **v0.10.3 follow-up** — external reference 흡수 cycle 2: file deletion cascade cleanup (3-method matching).
3. **v0.10.4 follow-up** — external reference 흡수 cycle 3: two-step CoT ingest (session-start → backlog-update 2-step contract) 명문화.
4. **v0.10.5 follow-up** — external reference 흡수 cycle 4: graph insights (surprising + gaps) 정형화.
5. **v0.10.6 follow-up** — release pipeline 의 `--apply default=False` 전환 (memory #5 의 "destructive subcommand 정공법" 정착). breaking change 회피로 minor release 에서 점진적 전환.
6. **v0.10.7 follow-up** — mypy strict cumulative 격상 (19 → 20-21 file). 1 release = 1-2 file 단계적 격상.
7. **v1.0.0 milestone** — full mypy strict 도달 (semver major 정렬, 100+ release 후 예상). spec §9 acceptance 12/12 도달 유지. phase 12 close 6/6 ✅ (v0.10.0 동시 종료로 이미 도달).
