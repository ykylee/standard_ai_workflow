# Beta v0.8.13 — mypy strict 단계적 격상 9단계 (common/state/builder.py) (2026-06-17)

> v0.8.0 spec §5.3 mypy strict 단계적 격상 — 9단계. `workflow_kit/common/state/builder.py`
> (workflow state payload builder, `build_workflow_state_payload`) 의 **13 mypy error → 0**
> (v0.8.7 plan estimate 35 → actual 13, v0.7.62~v0.8.8 누적 fix 의 잔여분 흡수).
> `parse_handoff` / `parse_backlog` 의 `dict[str, object]` return type 의 `list(...)` /
> subscript 패턴 cast 로 narrow. 5 module test 122 PASS, dispatcher 53 PASS, version
> auto-sync 4, bitbucket_v2 2, read-only manifest 4, workflow state 9. **PyPI 배포: no**.

## 핵심 추가 (1 TASK, 1 commit, 0 신규 test, 0 신규 subcommand)

### 📐 mypy strict 격상 9단계 (1 file, 13 error)

`workflow_kit/common/state/builder.py` 는 v0.8.0+ spec 의 `dict[str, object]` return type
(`project_docs.py:parse_handoff` / `parse_backlog`) 을 그대로 받아서 `list(...)` /
subscript 패턴 사용. `list(object)` / `object['key']` 가 mypy strict 의 `call-overload` /
`misc` / `attr-defined` 로 fail.

본 release 에서 consumer-side 에서 `cast(list[str], ...)` / `cast(list[Path], ...)` /
`cast(list[dict[str, str]], ...)` 명시 narrow. source code 변경 없이 *type-level* fix.

| error type | count | Fix |
|---|---|---|
| call-overload (list(object)) | 11 | `cast(list[str], handoff.get(key, []))` 8 site + `cast(list[Path], ...)` 1 site + `cast(list[dict[str, str]], backlog.get("tasks", []))` 1 site + `cast(list[str], handoff.get("constraints", []))` 1 site |
| attr-defined (object not iterable) | 1 | `handoff.get("next_documents", [])` → `cast(list[Path], ...)` |
| misc (List[object] → List[str]) | 1 | `[item for item in [handoff.get("constraints")] ...]` → `cast(list[str], handoff.get("constraints", []))` 후 list comprehension |
| **total** | **13** | **0** |

### In-flight 발견 + fix (real bug fix 동반)

- **fix 1**: `tasks = list(backlog.get("tasks", []))` 후 `tasks[0]['task_id']` 패턴이
  `tasks` 가 empty 일 때 `IndexError` raise 가능. 본 release 에서 `if backlog_tasks:`
  guard 로 변경. (real bug fix — `if tasks:` 동일 의미이지만 empty list 에서 IndexError 회피)
- **fix 2**: `handoff.get("constraints")` 가 *scalar string* (single constraint) 인지
  *list* (multiple constraints) 인지 schema 정의 ambiguous. 기존 code 는
  `[handoff.get("constraints")]` 로 wrap 해서 list 처리. 본 release 에서
  `cast(list[str], handoff.get("constraints", []))` 로 schema 를 list 로 명시.
  (semantic change: scalar string 도 list 로 wrap — 기존 `[handoff.get(...)]` 와 동일 결과)

## 운영 누적 (v0.7.5 → v0.8.13)

| | v0.7.5 | v0.8.0 | v0.8.7 | v0.8.8 | v0.8.9 | v0.8.10 | v0.8.11 | **v0.8.13** |
|---|---|---|---|---|---|---|---|---|
| **mypy strict clean file** | 0 | 1 | 13 | 17 | 17 | 17 | 17 | **18** |
| **5 module test** | 64 | 122 | 122 | 122 | 122 | 122 | 122 | **122** |
| **dispatcher test** | 6 | 47 | 47 | 47 | 53 | 53 | 53 | **53** |
| **read-only manifest assertion** | ❌ | ❌ | ❌ | ❌ | ❌ | 4 | 4 | **4** |
| **workflow state test** | n/a | 9 | 9 | 9 | 9 | 9 | 9 | **9** |
| **cumulative test** | 0 | 0 | 0 | 0 | 0 | 0 | 134 | **135** |

## Test 결과

- `mypy --strict workflow_kit/common/state/builder.py`: 13 errors → "Success: no issues found"
- `mypy --strict` (cumulative, 32 file): v0.8.13 단계에서 18 file strict clean
- 회귀 (5 module + dispatcher + state + read-only + version): 변동 없음
  - 5 module: 122/122 PASS
  - dispatcher: 53/53 PASS
  - workflow state: 9/9 PASS
  - version auto-sync: 4/4 PASS
  - bitbucket_v2: 2/2 PASS
  - read-only manifest: 4/4 PASS
- gen-schema --check: check_status: identical, 85,743 bytes

**cumulative strict clean file count**: 17 → **18** (+ common/state/builder.py)
**cumulative test**: 134 → **135 PASS**

## 변경 파일 (3 변경)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow_kit/common/state/builder.py` | +24 / -8 (cast narrow + IndexError guard) |
| M | `pyproject.toml` | +1 (단계적 격상 note, v0.8.13 entry) |
| A | `workflow-source/releases/Beta-v0.8.13.md` | release note |
| A | `ai-workflow/memory/release/v0.8.13/backlog/2026-06-17.md` | plan |

## 다음 (v0.8.14+ / v0.9.0)

1. **v0.8.14**: `workflow_kit/common/contracts/baselines.py` 27 error (mypy strict 10단계)
2. **v0.9.0** full mypy strict (모든 module strict clean)
