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

## 5. Not done — next stages

- `workflow-source/skills/*/SKILL.md` (13 files, ~16K tokens) — skill sources
- Korean strings inside the renderers (`renderers.py` 735 lines, `plugin_payload.py` 324,
  `standard_rules.py` 97) — these are what consumer projects receive
- The rest of `global_workflow_standard.md` (§1.1–§10 remain Korean, so the canonical is
  currently mixed-language — deliberate staging, not an oversight)
