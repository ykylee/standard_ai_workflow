# Beta v0.10.2 — delivery layer 확장 (claude-code 진입점 정정 + aider / goose / custom adapters + session-start self-bootstrap) (SemVer minor) (2026-06-24)

> **SemVer minor bump** (v0.10.1 → v0.10.2) — v0.10.1 의 claude-code adapter 진입점 설계 오류 정정 (Claude Code 도 `CLAUDE.md` root 진입점 자동 read) + 3 신규 harness adapter (aider / goose / custom) + session-start self-bootstrap mode. **pi-dev 는 기존 adapter 활용** (정합 정공법). **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (1 진입점 정정 + 3 신규 adapter + 1 self-bootstrap + 4 apply_guide + 1 schema extension + 9 acceptance test)

### 1. claude-code adapter 진입점 정정 (v0.10.1 오류 정정)

v0.10.1 의 잘못된 가설:
- ❌ "Claude Code 는 root 진입점 자동 read 안 함, slash command 가 진입 mechanism"
- ✅ **v0.10.2 정정**: Claude Code 도 `CLAUDE.md` 를 root 진입점으로 자동 read (per https://docs.anthropic.com/en/docs/claude-code/memory). `AGENTS.md` 는 직접 read 안 함 → `CLAUDE.md` 에서 `@AGENTS.md` import 또는 symlink 으로 통합.

**정정 내용**:
- `HARNESS_SPECS["claude-code"].entry_files` = `()` → `("CLAUDE.md",)`
- `render_claude_code_agents` 신규 (`render_pi_dev_agents` 와 같은 패턴) — CLAUDE.md 진입점 render (한국어, AGENTS.md import 안내, 진입 slash command section, self-bootstrap 안내)
- `write_harness_files` 의 `if "claude-code" in harnesses:` block 신규 → CLAUDE.md emit (entry-mode=skill-only 일 때만 skip)
- 3 slash command (`.claude/commands/workflow-{session-start,backlog-update,doc-sync}.md`) 는 *additive 도구* 로 유지 (root 진입점과 별개)
- `harnesses/claude-code/apply_guide.md` 갱신 — v0.10.1 의 잘못된 가설 *정직하게 acknowledge* + 정정된 가이드

### 2. 3 신규 harness adapter (aider / goose / custom)

#### 2.1 aider (v0.10.2+ 신규, 1st follow-up)

- **HARNESS_SPECS entry 신규**:
  - `entry_files=("CONVENTIONS.md",)` (root 진입점)
  - `extra_files=(".aider/conventions.md", ".aider.conf.yml.example")` (config + mirror)
- **3 emit**: `CONVENTIONS.md` (root) + `.aider/conventions.md` (mirror) + `.aider.conf.yml.example` (caller 가 `.aider.conf.yml` 로 cp)
- **`render_aider_conventions` + `render_aider_config_example` + `write_aider_harness_files` 신규**
- Aider 의 `--read` flag 또는 `.aider.conf.yml` 의 `read:` list 로 CONVENTIONS.md 자동 read
- `commit-language: ko` + `weak-model: claude-3-5-haiku-20241022` (commit message 자동 생성)

#### 2.2 goose (v0.10.2+ 신규, 2nd follow-up)

- **HARNESS_SPECS entry 신규**:
  - `entry_files=()` (root 진입점 없음 — Goose 는 config 기반 진입)
  - `extra_files=(".goose/config.yaml",)` (single config)
- **`render_goose_config` + `write_goose_harness_files` 신규**
- `.goose/config.yaml` 구조: `version: 1` + `project: {name, workflow: standard-ai-workflow}` + `entry_points:` (3종 skill + trigger: on_session_start / manual) + `read_files:` (5종 workflow state docs) + `hooks: on_session_end:` (handoff 자동 갱신) + `language: ko`
- Goose 가 `.goose/config.yaml` 자동 load → read_files 자동 read → entry_points 등록 → hooks lifecycle 발화

#### 2.3 custom (v0.10.2+ 신규, 3rd follow-up)

- **HARNESS_SPECS entry 신규**:
  - `entry_files=()` (root 진입점 없음 — caller 자사 도구)
  - `extra_files=(".workflow-kits/custom/SKILL.md",)` (single reference template)
- **`render_custom_skill_template` + `write_custom_harness_files` 신규**
- Caller 자사 custom harness / IDE / CLI 의 *중립 진입점* — 특정 도구에 자동 load 안 됨
- `caller wire-up` 예시 3종: (1) symlink `~/.internal-cli/`, (2) Python `with open(...) as f`, (3) YAML `workflow_skill: { source: ..., auto_load: true }`
- 3 skill output schema contract (SessionStartOutput / BacklogUpdateOutput / DocSyncOutput) 정합 정공법 명시

#### 2.4 pi-dev (기존 adapter 활용)

- v0.9.0 부터 지원, v0.10.2 변경 ❌. `entry_files=("AGENTS.md",)` (Codex 와 동일 진입점)

#### 2.5 SUPPORTED_HARNESSES 7→10 + HARNESS_FILE_BUILDERS 7→10 + HARNESS_SPECS 7→10

3-way 정합 (renderers.py 의 self-check 가 verify).

### 3. session-start self-bootstrap mode (v0.10.2+ 신규)

**핵심 contract** (skill 진입 시 핵심 4 file 모두 부재):
- `status="warning"` (그레이스풀 skip + 권장)
- `self_bootstrap_suggested=True`
- `self_bootstrap_init_commands: list[str]` 에 scaffold 명령 emit

**변경 파일**:
- `workflow_kit.common.schemas.session.SessionStartOutput` 에 2 field 신규:
  - `self_bootstrap_suggested: bool = False`
  - `self_bootstrap_init_commands: list[str] = Field(default_factory=list)`
- `skills/session-start/scripts/run_session_start.py` 의 main() 에 self-bootstrap 감지 + init commands emit
- **부재 감지 조건**: `not handoff.exists() and not work_backlog.exists() and not state.json.exists()` (4 file 중 핵심 3 — PROJECT_PROFILE 는 caller 가 bootstrap 후 제공)
- **부재 시 init commands**:
  1. `python3 scripts/bootstrap_workflow_kit.py --target-root <workspace> --project-slug <slug> --project-name <name> --adoption-mode new --harness claude-code --entry-mode skill-only`
  2. `python3 skills/session-start/scripts/run_session_start.py --session-handoff-path <path> --work-backlog-index-path <path> --project-profile-path <path>` (재실행 안내)
- **`self-bootstrap` 정공법**: 기존 graceful skip 정책 (PURPOSE.md / state.json 부재 시 advisory) 과 정합. **skill 실행 실패 ❌**.

### 4. apply_guide 4개

| File | 변경 |
|---|---|
| `harnesses/claude-code/apply_guide.md` | v0.10.1 → v0.10.2 정정 (CLAUDE.md 진입점, AGENTS.md 통합 방법, self-bootstrap mode) |
| `harnesses/aider/apply_guide.md` | 신규 (CONVENTIONS.md + .aider.conf.yml.example 절차) |
| `harnesses/goose/apply_guide.md` | 신규 (.goose/config.yaml emit + entry_points/hooks) |
| `harnesses/custom/apply_guide.md` | 신규 (caller wire-up 3종 + self-bootstrap) |

## Spec layer 갱신 (1 spec + 1 README + 1 index)

| File | Section | 변경 |
|---|---|---|
| `llm_wiki_concept_purpose_spec.md` | §4.5 (v0.10.1) | v0.10.2 진입점 정정 + 3 adapter + self-bootstrap mode 갱신 |
| `workflow_harness_distribution.md` | §1 + §harnesses/ 인덱스 | 3 adapter 추가 (aider / goose / custom), 10 harness |
| `harnesses/README.md` | 표 | 3 row 추가 (aider / goose / custom) |

## 운영 누적 (v0.10.1 → v0.10.2)

| | v0.10.1 | **v0.10.2** |
|---|---|---|
| **SemVer bump** | minor | **minor** |
| **SUPPORTED_HARNESSES** | 7 | **10 (+ aider / goose / custom)** |
| **HARNESS_FILE_BUILDERS** | 7 | **10 (+ write_aider / write_goose / write_custom)** |
| **HARNESS_SPECS** | 7 | **10** |
| **claude-code entry_files** | `()` (v0.10.1 오류) | **`("CLAUDE.md",)` (v0.10.2 정정)** |
| **SessionStartOutput 신규 field** | ❌ | **`self_bootstrap_suggested` + `self_bootstrap_init_commands`** |
| **apply_guide.md** | 7 harness | **10 harness (claude-code 정정 + 3 신규)** |
| **cumulative acceptance** | 47/47 | **56/56** (v0.10.2 9 신규 + v0.10.1 6 + v0.10.0 6 + v0.9.6 6 + v0.9.5 환경의존 3 + v0.9.4 3 + v0.9.2 8 + v0.9.3 4 + v0.9.1 4 + v0.9.0 6 + deprecation contract 4 갱신 = 56) |
| **spec §9 acceptance** | 12/12 | **12/12** (변동 ❌) |
| **breaking change** | none | **none** (default = aggressive, v0.10.1 호환 + v0.10.1 진입점 정정) |

## Test 결과

- 신규 (9 PASS, v0.10.2):
  - `test_claude_code_entry_point_corrected_v0_10_2` — SUPPORTED_HARNESSES 7→10 + HARNESS_SPECS claude-code entry_files=('CLAUDE.md',) + 3-way 정합 verify
  - `test_claude_code_aggressive_emits_v0_10_2` — claude-code + aggressive → CLAUDE.md (root 진입점) + 3 slash commands emit + 본문에 "AGENTS.md 와의 관계" + "@AGENTS.md" import 안내 verify
  - `test_claude_code_skill_only_skips_claude_md_v0_10_2` — claude-code + skill-only → CLAUDE.md skip, 3 slash commands 유지
  - `test_aider_adapter_emits_v0_10_2` — aider → CONVENTIONS.md (root) + .aider/conventions.md + .aider.conf.yml.example emit + 본문 정합
  - `test_goose_adapter_emits_v0_10_2` — goose → .goose/config.yaml emit + entry_points 3종 + read_files 5종 + language: ko
  - `test_custom_adapter_emits_v0_10_2` — custom → .workflow-kits/custom/SKILL.md emit + caller wire-up + self-bootstrap 안내
  - `test_supported_harnesses_count_v0_10_2` — SUPPORTED_HARNESSES 10개 set 정합
  - `test_session_start_self_bootstrap_v0_10_2` — subprocess 로 session-start 실행 + 4 file 부재 시 self_bootstrap_suggested=True + init commands emit
  - `test_v0_10_0_v0_10_1_regression_v0_10_2` — v0.10.0 deprecation cycle 종료 + v0.10.1 entry-mode 3-mode 회귀 유지
- v0.10.1 회귀 (갱신): **6/6 PASS** ✅ (claude-code 진입점 정정 반영)
- v0.10.0 회귀: **6/6 PASS** ✅
- v0.9.6 회귀: 6/6 PASS ✅
- v0.9.4 회귀: **3/3 PASS** ✅
- v0.9.2 회귀: **8/8 PASS** ✅
- v0.9.1 deprecation contract: **4/4 PASS** ✅
- 누적 acceptance: **56/56 PASS** (v0.10.2 9 + v0.10.1 6 + v0.10.0 6 + v0.9.6 6 + v0.9.5 환경의존제외 3 + v0.9.4 3 + v0.9.2 8 + v0.9.3 4 + v0.9.1 4 + v0.9.0 6 + 누적 환경의존 v0.9.5 3 + deprecation contract 4 갱신 = 56)
- 누적 smoke: **162/162 + 56 별도 subset** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3 + v0.9.5 6 + v0.9.6 6 + v0.10.0 6 + v0.10.1 6 + v0.10.2 9)

## 변경 파일 (8 변경 + 4 신규 + 1 doc sync)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/scripts/bootstrap_lib/harnesses/__init__.py` | SUPPORTED_HARNESSES 7→10 + HARNESS_SPECS claude-code 진입점 정정 + aider / goose / custom 3 entry 추가 |
| M | `workflow-source/scripts/bootstrap_lib/harnesses/renderers.py` | `render_claude_code_agents` + `render_aider_conventions` + `render_aider_config_example` + `render_goose_config` + `render_custom_skill_template` + 4 write function + 4 register 호출 |
| M | `workflow-source/scripts/bootstrap_lib/__main__.py` | `write_harness_files` 의 claude-code / aider dispatch block 신규 (entry-mode guard 정합) |
| M | `workflow-source/workflow_kit/common/schemas/session.py` | SessionStartOutput 에 `self_bootstrap_suggested` + `self_bootstrap_init_commands` 2 field 신규 |
| M | `workflow-source/skills/session-start/scripts/run_session_start.py` | self-bootstrap 감지 + init commands emit + status="warning" 처리 |
| M | `workflow-source/harnesses/claude-code/apply_guide.md` | v0.10.1 → v0.10.2 정정 (CLAUDE.md 진입점 + AGENTS.md 통합) |
| M | `workflow-source/tests/check_v0_10_1_skill_only_entry_mode.py` | claude-code 진입점 정정 반영 (entry_files=('CLAUDE.md',)) |
| A | `workflow-source/harnesses/aider/apply_guide.md` | 신규 (CONVENTIONS.md + .aider.conf.yml.example 절차) |
| A | `workflow-source/harnesses/goose/apply_guide.md` | 신규 (.goose/config.yaml emit + entry_points/hooks) |
| A | `workflow-source/harnesses/custom/apply_guide.md` | 신규 (caller wire-up 3종 + self-bootstrap) |
| A | `workflow-source/tests/check_v0_10_2_delivery_layer_extension.py` | 신규 (9 acceptance test, ≈ 340 line) |
| M | `workflow-source/pyproject.toml` | version 0.10.1 → 0.10.2 |
| M | `workflow-source/workflow_kit/__init__.py` | `_read_pyproject_version` loud fallback literal `"v0.10.1-beta"` → `"v0.10.2-beta"` (suffix 정상) |
| A | `workflow-source/releases/Beta-v0.10.2.md` | release note (본 file) |
| M | `README.md` | §0 (버전) + §10 (v0.8.0 → v0.10.2 누적 변경 요약, v0.10.2 entry 추가) + release URL list 갱신 |
| A | `ai-workflow/memory/release/v0.10.2/backlog/2026-06-24.md` | v0.10.2 plan |
| M | `ai-workflow/memory/active/work_backlog.md` | v0.10.2 index entry 추가 + 최종 수정일 갱신 |

## 다음 (v0.10.3+ / v1.0.0)

1. **v0.10.3 follow-up** — external reference 흡수 cycle 2: file deletion cascade cleanup (3-method matching).
2. **v0.10.4 follow-up** — external reference 흡수 cycle 3: two-step CoT ingest (session-start → backlog-update 2-step contract) 명문화.
3. **v0.10.5 follow-up** — external reference 흡수 cycle 4: graph insights (surprising + gaps) 정형화.
4. **v0.10.6 follow-up** — release pipeline 의 `--apply default=False` 전환 (memory #5 의 "destructive subcommand 정공법" 정착). breaking change 회피로 minor release 에서 점진적 전환.
5. **v0.10.7 follow-up** — mypy strict cumulative 격상 (19 → 20-21 file). 1 release = 1-2 file 단계적 격상.
6. **v1.0.0 milestone** — full mypy strict 도달 (semver major 정렬, 100+ release 후 예상). spec §9 acceptance 12/12 도달 유지. phase 12 close 6/6 ✅ (v0.10.0 동시 종료로 이미 도달).
