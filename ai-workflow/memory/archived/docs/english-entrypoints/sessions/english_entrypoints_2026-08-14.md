# Session log — English entry-point rules (2026-08-14)

- Purpose: record the first stage of moving AI-facing entry points to English.
- Scope: `core/global_workflow_standard.md` §1 · §3 · §8 · §11, the rules extractor, entry-point blocks, plugin payload.
- Audience: AI agent, repository maintainer
- Status: active
- Related: [task](../backlog/tasks/TASK-2026-08-14-docs-english-entrypoints-001.md)

## 0. Why — measured, not assumed

Korean is 17–27% of *characters* but **45–62% of tokens**. The same sentence costs
39 tokens in Korean and 15 in English (**2.6×**). What is read at every session start —
`CLAUDE.md` + `state.json` + `session_handoff.md` — is about **36K tokens**.

An earlier judgment in this session ("language is the wrong lever") was based on the
character share and was wrong. Characters are not the unit that is paid for.

## 1. The order is forced by the generator, not by preference

The rule blocks in entry points are **generated**:

```
core/global_workflow_standard.md  §1 · §3 · §8 · §11      ← canonical
  → common/_standard_rules_snapshot.py                    ← generated (wheel installs have no core/)
  → "## Working Principles" / "## Session Close Order" / "## Memory Update Paths"
                                                          ← generated into every entry point
```

Editing the output first would be overwritten on the next render and would fail
`check_standard_single_source`. So: canonical first, then regenerate.

## 2. What the parser anchored on — and what it did not

`standard_rules.py` anchors sections by **heading string** (`_SECTION_PRINCIPLES` …),
so translating the headings required moving those constants in the same change. The
parser **failed loudly** when one was missed (`StandardParseError: 섹션을 찾지 못했다`)
rather than emitting a half block — the right failure mode.

The renderers also look up §11.1 commands by **keyword** —
`find_memory_command(rules, "재생성")` and four siblings. Those are the same class of
coupling and had to move together.

**What did *not* break**: the SessionStart hook's duplicate-injection probe. It derives
from `GENERATED_MARKER.split("—")[0]` = `generated-from: core/global_workflow_standard.md …`,
a path string, not a Korean heading. Keeping that prefix identical means consumer
projects that already carry the old block are still detected and not double-injected.

## 3. Checks that read Korean literals

Three checks asserted Korean strings from the canonical document and went red:

| Check | What it asserted | Fix |
|---|---|---|
| `check_state_json_generated` | `"생성물" in standard` | → `"generated artifact"` — same question, new wording |
| `check_convention_single_source` | literal `memory 갱신 → commit → push` | → `update memory → commit → push` |
| `check_appendonly_memory_layout` | (unrelated — the known seed `sessions/` gap, main-005) | wrote this file |

The first two are the reason a translation is not a text edit: **detectors keyed on
prose move with the prose**, and a detector that silently stops matching is worse than
one that fails.

## 4. Done in this stage

- Canonical §1 · §3 · §8 · §11 → English (headings and bodies)
- `standard_rules.py`: section anchors, rendered block headings, `GENERATED_MARKER` tail,
  `DEFAULT_STATE_DOCS`
- 5 `find_memory_command` keyword lookups across 3 modules
- Regenerated: snapshot module, plugin payload (`plugin/GEMINI.md`, claude-code rules,
  4 skill payloads), distributed `ai-workflow/core/` mirror
- `CLAUDE.md` / `AGENTS.md` rule blocks replaced with the rendered English block

## 5. Stage 2 — the 13 skill sources

All 13 `workflow-source/skills/*/SKILL.md` are now English: **16,253 → 12,437 tokens (−23%)**.

One constraint drove the wording. `check_maturity_registry` requires a section heading
matching `##.*(실행|사용|Usage)` for any skill registered as `stable`. The first file used
`## Run` and went red — the detector already accepts `Usage`, so every file now carries a
`Usage` heading rather than widening the detector. Same rule as stage 1: **a detector keyed
on prose moves with the prose**, and the cheaper move is to speak the vocabulary it
already knows.

Nothing else broke. The plugin payload (`plugin/skills/*`) is generated from
`plugin_payload.py`, not from these sources, so the two sets are independent — stage 3
covers that one.

## 6. Stage 3 — the renderers, and where the line is

Everything a consumer *receives* as prose is now English:

| Surface | Korean template lines | After |
|---|---|---|
| `harnesses/renderers.py` (12 harness templates) | 625 | **0** |
| `bootstrap_lib/renderers.py` (workflow README, assessment) | 99 | **19** (see below) |
| `plugin_payload.py` (skill bodies, descriptions, hooks) | 84 | **0** |

### The line: memory field labels are a parsing contract, not prose

The 19 lines left in `bootstrap_lib/renderers.py` are substitution keys
(`"<핵심 사용자 가치 및 목표>"`, `"TODO: 작업 목표"`, `"- 진행 현황:"`). They pair with
`templates/*.md`, and those templates carry the field labels that the tooling **parses**:

```python
# workflow_kit/common/project_docs.py:49
STATUS_RE = re.compile(rf"- 상태:\s*({_STATUS_ALT})\s*$")
```

Four writers emit the same literal (`read_only_bundle`, `seed_workspace_memory`,
`workflow_writes`, `backlog_update`). So translating those labels is **a data-format
migration, not a text edit** — it would touch 257 task files here plus every consumer
repository's existing memory, under a 2-year backward-compat guarantee. That work belongs
inside TASK-2026-08-14-main-008 (task SSOT restructuring), where the format changes anyway.

### What moved with the prose

Translating a surface is never just the surface. Nine detectors/parsers keyed on the Korean
text had to move in the same change, and each one announced itself as a red check:

| Where | What it read |
|---|---|
| `check_bootstrap` ×6 | reporting rule, `- 문서 목적:`, exploration-scope sentence, minimax heading |
| `check_standard_single_source` | `(있으면)` optional-path marker |
| `check_agent_plugin_payload` ×2 | `찾지 못했다` in the SessionStart hook, `실기 검증 미완` in the goose snippet |
| `check_v0_10_2_delivery_layer_extension` ×2 | CLAUDE.md section titles, aider entry title |
| `check_state_json_generated` | `생성물` in the canonical §11 |
| `check_convention_single_source` | the literal `memory 갱신 → commit → push` |
| `run_existing_project_onboarding` | **14 field labels** of the assessment document |

Two of those got a *both-ways* fix rather than a straight swap — `(있으면)`/`(if present)`
and the 14 assessment labels now accept either language. The reason is the same in both
cases: **consumer repositories still hold the Korean artifacts**, and a detector that only
knows the new wording goes silently blind on them. `extract_section_value` gained a
tuple-of-labels form for exactly that.

One assertion was deliberately *left* in Korean and then reverted after I had already
translated it — its source sentence had not moved yet. A detector that runs ahead of its
source stops measuring anything.

## 7. Not done — next stage

- **Memory document field labels** (`templates/*.md` 330 lines + the 19 substitution keys) —
  blocked on TASK-2026-08-14-main-008 by design, see §6.
- Internal Python docstrings and comments (`harnesses/renderers.py` 102,
  `plugin_payload.py` 235, `standard_rules.py` 97) — code documentation, not entry-point
  docs; out of the stated scope.
- The rest of `global_workflow_standard.md` (§1.1–§10 remain Korean, so the canonical is
  currently mixed-language — deliberate staging, not an oversight)
