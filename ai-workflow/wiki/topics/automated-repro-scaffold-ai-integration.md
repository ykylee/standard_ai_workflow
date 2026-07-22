---
type: topic
status: draft
last_ingested_from: ai-workflow/memory/active/main/session_analysis_2026-07-09.md + workflow-source/skills/automated-repro-scaffold/SKILL.md + workflow-source/core/automated_repro_scaffold_skill_spec.md
related_pages:
  - topics/workflow-audit-2026-07-09
  - topics/phase-13-definition-north-star
  - workflow-source/skills/automated-repro-scaffold/SKILL.md
  - workflow-source/core/automated_repro_scaffold_skill_spec.md
created: 2026-07-09
updated: 2026-07-09
---

# automated-repro-scaffold AI 에이전트 연동 강화 (2026-07-09)

## TL;DR

본 토픽은 2026-07-09 audit 의 P2-4 후보 (`automated-repro-scaffold` AI 에이전트 연동 강화) 를 해소하기 위한 *제안*. 현 상태 (v0.11.24 stable) 의 한계 — `existing_test_code` / `project_profile` 입력 option 미흡, AI summary 의 단순 1~3 line, memory_index / contract_v1 / orchestrator-subagent wiring 부재 — 를 식별하고 4 단계 강화 roadmap (R-1~R-4) 을 제안한다.

## 1. 현 상태 (v0.11.24 stable)

### 1.1 기존 기능

- 입력: `--report` (bug_report.md) + `--output` (repro_X.py) + `--dry-run` + `--json`
- 출력: BaseOutput 패턴 + 4 error_code + stage_completion + next_stage=validation-plan
- 안정성: 6 조건 stable 정합 (Pydantic schema / stdio 등록 / error_code / 단일 명령 / 예시 실행 / smoke 5 case)

### 1.2 한계 (audit 관점)

| # | 한계 | 영향 | severity |
|---|---|---|---|
| L1 | `existing_test_code` option 미구현 | AI 가 기존 테스트 컨벤션을 모르고 scaffold 생성. project 의 일관성 ↓ | P2 |
| L2 | `project_profile` 입력 option 미구현 | PROJECT_PROFILE.md 의 validation command / Python version 을 scaffold 에 자동 반영 ❌ | P2 |
| L3 | AI summary (`notes`) 가 단순 1~3 line | AI 에이전트가 다음 stage 진행 시 활용할 rich summary 부재 | P3 |
| L4 | memory_index opt-in wiring 부재 | doc-sync / backlog-update 가 본 skill 의 신규 entry 를 자동 link 못함 (P2-2 의 R-B 와 정합) | P3 |
| L5 | orchestrator-subagent contract v1 fan-out 미지원 | multi-bug repro 의 병렬 scaffold 생성 ❌ | P3 |

### 1.3 spec 만 있고 미구현인 항목

`automated_repro_scaffold_skill_spec.md` §2 에 *선택* 입력으로 명시된 `existing_test_code` 와 `project_profile` 이 실제 코드 (skill/scripts/run_automated_repro_scaffold.py) 에는 미반영.

## 2. 강화 roadmap (R-1 ~ R-4)

### 2.1 R-1 — 입력 option 확장 (P2)

**목표**: spec §2 의 `existing_test_code` 와 `project_profile` 입력 option 을 실제 코드에 반영.

**메커니즘**:
```bash
python3 .../run_automated_repro_scaffold.py \
  --report bug.md \
  --output tests/repro_X.py \
  --existing-test-code tests/conftest.py \
  --project-profile docs/PROJECT_PROFILE.md
```

- `existing_test_code`: AI 가 기존 컨벤션 (fixture / mock 패턴 / import 구조) 분석.
- `project_profile`: PROJECT_PROFILE.md 의 검증 command + Python version + deprecation policy 자동 주입.

**구현**:
- `scripts/run_automated_repro_scaffold.py` argparse 확장.
- `workflow_kit/common/schemas/automated_repro_scaffold.py` 의 input schema 확장.
- 신규 smoke test 2개 (existing_test_code 사용 / project_profile 사용).

**acceptance**:
- v0.13.0 (P2-4 의 1st sub-milestone) 출시 시 stable 정합 유지 + 신규 option 2개.

### 2.2 R-2 — AI summary 강화 (P3)

**목표**: `stage_completion.notes` (1~3 line) 를 *구조화* (3-5 line + section).

**메커니즘**:
```json
{
  "notes": [
    "Root cause: foo() returns None for empty input",
    "Affected: tests/test_foo.py::test_empty",
    "Next: validation-plan 실행 시 회귀 test 1건 추가 권장"
  ],
  "notes_structured": {
    "root_cause_guess": "...",
    "affected_tests_guess": ["..."],
    "next_steps": ["..."]
  }
}
```

**구현**:
- 기존 `notes: str` → `notes_structured: dict` 추가.
- 기존 `notes` 는 1-line summary (back-compat 유지).

**acceptance**:
- v0.13.1 출시 시 notes_structured 필드 emit + 기존 smoke 회귀 0.

### 2.3 R-3 — memory_index opt-in wiring (P3, P2-2 정합)

**목표**: scaffold 생성 시 자동으로 memory_index entry 1건 생성.

**메커니즘**:
- scaffold 생성 후 `--memory-index-add` flag 명시 시 `memory_index/entries/MEM-YYYY-MM-DD-NNN.json` 1건 emit.
- entry 의 `primary_abstraction` = "Automated repro scaffold for bug <bug_id>".
- `cue_anchors` = bug_id + error_message 의 token (≤5).

**구현**:
- `save_memory_entry` 호출 (P0-3 의 helper 활용).
- 신규 smoke test 1개 (entry 생성 + retrieval hit 확인).

**acceptance**:
- v0.13.2 출시 시 opt-in flag 정상 + memory_index query 검증 PASS.

### 2.4 R-4 — contract v1 fan-out (P3)

**목표**: multi-bug repro 의 병렬 scaffold 생성 (orchestrator-subagent contract v1 fan-out).

**메커니즘**:
- `--reports <bug1.md>,<bug2.md>,<bug3.md>` 로 다중 입력.
- 내부에서 `choose_roles()` (contract v1 delegator) 호출 → sub-agent fan-out.
- 각 sub-agent 가 1 scaffold 생성 → fan-in 결과.

**구현**:
- v0.5.7 의 multi-component fan-out 패턴 차용.
- `output_validator.validate_fanin_output()` 적용.
- 신규 smoke test 1개 (3 reports → 3 scaffolds 검증).

**acceptance**:
- v0.13.3 출시 시 fan-out 정상 + contract v1 정합.

## 3. acceptance criteria (제안)

| AC | 조건 |
|---|---|
| AC1 | R-1~R-4 모두 PASS 후에도 기존 stable 정합 (6 조건) 유지 |
| AC2 | v0.13.0~v0.13.3 의 4 release 동안 smoke 누적 ≥ 5 case 신규 추가 + 회귀 0 |
| AC3 | memory_index / contract_v1 / orchestrator-subagent 와의 cross-link 자동 |

## 4. Risk / Open issues

1. **R-1 의 project_profile parse**: PROJECT_PROFILE.md 의 §4 (검증 포인트) / §3 (기본 명령) 자동 parse. helper module 신규.
2. **R-4 의 fan-out 비용**: 3 reports → 3 sub-agent 동시 실행. cost / latency 증가. dry-run 권장.
3. **back-compat**: 기존 caller (single `--report`) 의 동작 보장. 신규 option 모두 optional.

## 5. 적용 일정 (제안)

| sub-milestone | release | acceptance |
|---|---|---|
| R-1 입력 option 확장 | v0.13.0 | existing_test_code + project_profile 정상 |
| R-2 AI summary 강화 | v0.13.1 | notes_structured emit + 회귀 0 |
| R-3 memory_index wiring | v0.13.2 | opt-in entry 생성 + retrieval PASS |
| R-4 contract v1 fan-out | v0.13.3 | 3 reports → 3 scaffolds fan-out PASS |

각 sub-milestone = 1 release. Phase 13 의 sub-milestone 으로 통합.

## 6. 인용 및 후속

- 2026-07-09 audit: [`workflow-audit-2026-07-09.md`](workflow-audit-2026-07-09.md) §3.3 P2-4
- 현 spec: [`../../../workflow-source/core/automated_repro_scaffold_skill_spec.md`](../../../workflow-source/core/automated_repro_scaffold_skill_spec.md) §2
- 현 SKILL: [`../../../workflow-source/skills/automated-repro-scaffold/SKILL.md`](../../../workflow-source/skills/automated-repro-scaffold/SKILL.md)
- 본 P0-3 follow-up: [`../../../ai-workflow/memory/active/memory_index/README.md`](../../../ai-workflow/memory/active/memory_index/README.md) (R-3 의 helper)
- 본 P2-2 follow-up: [`wiki-memory-bidirectional-link-design.md`](wiki-memory-bidirectional-link-design.md) (R-3 의 cross-link)

## 다음에 읽을 문서
- [`workflow-audit-2026-07-09.md`](workflow-audit-2026-07-09.md)
- [`phase-13-definition-north-star.md`](phase-13-definition-north-star.md)
- [`../../../workflow-source/core/automated_repro_scaffold_skill_spec.md`](../../../workflow-source/core/automated_repro_scaffold_skill_spec.md)
