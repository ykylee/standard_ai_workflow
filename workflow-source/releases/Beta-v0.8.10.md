# Beta v0.8.10 — read-only MCP manifest outputSchema byte-identical assertion (spec §9 #6) (2026-06-17)

> v0.8.0 spec §9 acceptance criterion #6 의 assertion test. read-only MCP manifest
> (`schemas/read_only_transport_descriptors.json`) 의 `outputSchema` 가 generated schema
> (`schemas/generated_output_schemas.json`) 와 byte-identical 임을 *runtime assertion* 으로 verify.
> dispatcher 30, 5 module 122 PASS, dispatcher 53 PASS, version auto-sync 4,
> **read-only manifest assertion 4 신규**. **PyPI 배포: no**.

## 핵심 추가 (1 TASK, 1 commit, 4 신규 test, 0 신규 subcommand)

### spec §9 #6 acceptance — read-only manifest outputSchema byte-identical

`schemas/read_only_transport_descriptors.json` 의 13 tool 의 `outputSchema` field 가
`schemas/generated_output_schemas.json` 의 `outputs` section 과 *runtime* byte-identical
임을 verify. 본 release 의 verification:

| Test | 결과 | 비고 |
|---|---|---|
| `test_descriptor_tools_have_output_schema_v0_8_10` | PASS | 13/13 tool `outputSchema` field 보유 |
| `test_modeled_tools_byte_identical_v0_8_10` | PASS | 9/9 modeled tool byte-identical |
| `test_unmodeled_tools_use_generic_schema_v0_8_10` | PASS | 4/4 unmodeled tool 의 generic schema pattern 유지 |
| `test_no_descriptor_orphans_v0_8_10` | PASS | 0 descriptor → gen contract orphan |

### 13 descriptor tool 분류

**Modeled (9)** — `gen.outputs[name]` 와 byte-identical:
- `latest_backlog`, `check_doc_metadata`, `check_doc_links`,
  `suggest_impacted_docs`, `check_quickstart_stale_links`,
  `create_session_handoff_draft`, `create_environment_record_stub`,
  `smart_context_reader`, `create_backlog_entry`

**Unmodeled (4)** — descriptor 의 generic schema pattern 유지 (의도적 fallback):
- `summarize_git_history`, `rotate_workflow_logs`,
  `assess_milestone_progress`, `apply_robust_patch`

Unmodeled 4 family 는 `workflow_kit.common.*` module 에 *구현* 은 존재하지만
Pydantic contract 가 없어서 `gen-schema` 가 generated schema 에 포함시키지 않음.
Descriptor 는 generic `{"type": "object", "description": "Generic schema for unmodeled family 'X'."}` 으로 fallback. 본 release 의 test 는 이 pattern 의 *drift* 를 감지 (현재 PASS, 향후 unmodeled → modeled 전환 시 자동 fail).

### 추가 변경
- 없음 (순수 test 추가)

## 운영 누적 (v0.8.0 → v0.8.10)

| | v0.8.0 | v0.8.7 | v0.8.9 | **v0.8.10** |
|---|---|---|---|---|
| **dispatcher** | 28 | 28 | 30 | **30** |
| **dispatcher test** | 47 | 47 | 53 | **53** |
| **5 module test** | 122 | 122 | 122 | **122** |
| **read-only manifest assertion** | ❌ | ❌ | ❌ | **4 PASS** |
| **cumulative mypy strict clean** | 1 | 13 | 17 | **17** |

## In-flight 발견 + fix

- **fix 1**: spec §9 #6 acceptance criterion 이 draft 상태로 *unchecked* 였음 (spec 자체).
  본 release 에서 assertion test 구현 + 4/4 PASS 로 spec §9 의 미완 1건 해소.
- (없음) — test 만 추가, production code 변경 0

## Test 결과

- 신규 (4 PASS, v0.8.10+):
  - `test_descriptor_tools_have_output_schema_v0_8_10` — 13/13 tool 의 `outputSchema` field 존재
  - `test_modeled_tools_byte_identical_v0_8_10` — 9/9 modeled tool byte-identical (deep equal)
  - `test_unmodeled_tools_use_generic_schema_v0_8_10` — 4/4 unmodeled 의 generic schema pattern 유지
  - `test_no_descriptor_orphans_v0_8_10` — descriptor → gen direction 0 orphan
- 회귀 (5 module + dispatcher): 변동 없음
  - 5 module: 122/122 PASS
  - dispatcher: 53/53 PASS
  - version auto-sync: 4/4 PASS
  - bitbucket_v2: 2/2 PASS
  - gen-schema --check: check_status: identical (85,743 bytes)

**cumulative spec §9 acceptance**: 7/12 → **8/12** done (criterion #6 해소)

## 변경 파일 (2 변경)

| 변경 | File | 변경량 |
|---|---|---|
| A | `tests/check_v0_8_10_read_only_manifest_byte_identical.py` | +170 (4 신규 test + helper) |
| A | `workflow-source/releases/Beta-v0.8.10.md` | release note |
| A | `ai-workflow/memory/release/v0.8.10/backlog/2026-06-17.md` | plan |

## 다음 (v0.8.11+ / v0.9.0)

1. **v0.8.11**: `workflow_kit/common/state/builder.py` 35 error (mypy strict 9단계)
2. **v0.8.12**: `workflow_kit/common/contracts/baselines.py` 27 error (mypy strict 10단계)
3. **v0.9.0** full mypy strict
4. (별도) phishing_keywords 2 pre-existing test fail fix
5. (별도) GH Actions weekly cron — `consumer-metrics --digest-markdown`
6. (별도) spec §9 acceptance 미완 (4/12): `release-dist --apply` 1-command build, `tools test ≥ 7`, `v0.7.59~v0.7.62 follow-up C (dispatcher 29/30)`, `v0.7.62 follow-up A (GH Actions cron)`
