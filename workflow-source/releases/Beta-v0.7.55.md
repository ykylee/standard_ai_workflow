# Beta v0.7.55 — release-doctor in-process + cache-migrate LRU/LFU split + 3 subcommand (2026-06-16)

> v0.7.54 의 "dispatcher 14+ / release-doctor in-process / cache-migrate LRU/LFU split" follow-up.
> 4 follow-up: (a) tools/release_pipeline 모듈화 + (b) release-doctor in-process + (c) cache-migrate split + (d) 3 subcommand 추가.
> dispatcher 11 → 14.

## 핵심 추가 (4 follow-up, 2 commit, 9 신규 test, 3 신규 file)

### a. tools/release_pipeline_lib.py (in-process wrapper)

기존 `tools/release_pipeline.py` (1478 line, `if __name__ == "__main__": main()`) 의 *in-process wrapper*. script → module 변환.

```python
# 1 line 핵심: importlib.util.spec_from_file_location + sys.modules cache
spec = importlib.util.spec_from_file_location("tools_release_pipeline", str(path))
mod = importlib.util.module_from_spec(spec)
sys.modules["tools_release_pipeline"] = mod
spec.loader.exec_module(mod)
```

**cmd_validate(skip_packaging, skip_doctor, skip_state, skip_git) → dict** 1 함수 노출. 내부적으로 `cmd_validate` 의 `_Args` class instance 만들어서 그대로 호출.

**REPO_ROOT 정합**: lib 위치 = `tools/release_pipeline.py` 의 sibling (`workflow-source/tools/`) → `parents[1]` = `workflow-source/` — 동일. drift 위험 0.

### b. release-doctor in-process 호출 (subprocess → in-process)

`cmd_release_doctor` handler 의 *subprocess* wrapper 제거 → *in-process* import. **subprocess overhead 200ms → <10ms**.

```python
# 변경 핵심
sys.path.insert(0, str(workflow_source))  # tools 의 parent
from release_pipeline_lib import cmd_validate
results = cmd_validate(skip_packaging=..., ...)
```

**rc 의미 정합**:
- `result[k].get("ok") is False` 인 source 1+ 개 → rc=1
- all ok → rc=0
- exception → rc=2

### c. cache-migrate LRU/LFU split (--mode=migrate|split|both)

v0.7.54 의 *단일 migrate* → 2 step (migrate + split) 으로 확장.

```bash
# default: both
python -m workflow_kit.workflow_kit_cli --command=cache-migrate --cache-path=/path/to/cache.json

# step 1 only: v0.7.41 single → mixed
python -m workflow_kit.workflow_kit_cli --command=cache-migrate --cache-path=... --mode=migrate

# step 2 only: mixed → LRU + LFU
python -m workflow_kit.workflow_kit_cli --command=cache-migrate --cache-path=... --mode=split --lfu-threshold=10
```

**Real cache smoke** (3 entry, access_count 3/15/20, threshold=10):
- LRU = 1 (access_count 3)
- LFU = 2 (access_count 15, 20)
- ✅ PASS

### d. 3 신규 subcommand (L/M/N)

| | Subcommand | 1차 layer | Type |
|---|---|---|---|
| **L** | `okf-version-check` | `okf_import._check_version_compatibility` | in-process |
| **M** | `cache-decay` | `cache_lfu_decay_persist.decay_age_scores` | in-process |
| **N** | `score-wiki-trend` | `tools/score_wiki_trend.py` | **subprocess** |

**L. okf-version-check** (ADR-011 / OKF spec §11):
- 2 input mode: `--okf-version=X.Y` (explicit) OR `--bundle=PATH` (read `okf-bundle.yaml` 의 `okf_version` regex extract)
- Policy: exact match=pass / minor higher=warn / major higher=error / older=error / missing=warn / malformed=warn
- Status → rc: pass=0, warn=1, error=2

**M. cache-decay** (LFU temporal, v0.7.51+):
- Args: `--scores=PATH` (JSON file), `--saved-at=ISO8601` (default file mtime), `--output=PATH`, `--half-life=N` (default 86400s = 1 day)
- 1차 layer: `cache_lfu_decay_persist.decay_age_scores` 의 *in-process* 호출

**N. score-wiki-trend** (v0.7.1+):
- *in-process* 가 아닌 *subprocess* wrapper — **`score_wiki_trend.py` 의 dataclass KW_ONLY + `sys.modules[cls.__module__]` lookup 이 importlib loaded module 에서 fail (Python 3.14 bug)**. memory rule #8 의 *test-harness interface drift* case → subprocess boundary 가 well-tested path.
- Args forwarded verbatim: `--record-current` / `--record-range=N` / `--show` / `--json`

## 검증

- **dispatcher 14 subcommand**: **20/20 test PASS** (v0.7.52 6 → v0.7.53 9 → v0.7.54 13 → **v0.7.55 20**)
- **release_pipeline_lib test**: **2/2 test PASS** (in-process wrapper 자체 검증)
- **Real cache smoke**: 3 entry migrate + split (1 LRU + 2 LFU) PASS
- **OKF version check 4 case + no-arg**: 0.1=0 / 0.2=1 / 1.0=2 / 0.0.5=2 / no-arg=2
- **5 module test 회귀 0**: 68 PASS (변동 없음)

## Commit

| Hash | Subject |
|---|---|
| `4b64b20` | refactor(v0.7.55): release-doctor in-process + cache-migrate LRU/LFU split + 3 subcommand (14 subcommand) |
| `3ba61e8` | test(v0.7.55): dispatcher test 7 신규 + tools/release_pipeline_lib wrapper test 2 신규 (총 9 test) |
| `chore(v0.7.55)` | version bump 0.7.54 → 0.7.55 + release note (본 commit) |

## 다음 (v0.7.56 / v0.7.60 후보)

- **score_wiki_trend.py Python 3.14 호환 fix** — `tools/__init__.py` 추가 후 `import tools.score_wiki_trend` in-process 가능. 또는 dataclass 의 `KW_ONLY` / `sys.modules` 패턴 fix.
- **dispatcher 16+** — `--command=okf-cleanup` (deprecated frontmatter key strip), `--command=cache-prune` (LFU/LRU size cap eviction)
- **cache-lfu-decay-persist CSV** — `decay_age_scores` 의 *in-place* 변형 (memory layer)
- **release_pipeline 의 다른 subcommand wrapper** — `cmd_version_bump` / `cmd_note_draft` / `cmd_release` / `cmd_verify` / `cmd_rollback` 의 in-process 노출 (현재 `cmd_validate` 만)
- **5 module audit 3차** — `okf_export` / `okf_import` 의 *strict mode* 별 lint rule coverage 보강 (V-1 / V-4 / V-R9 / V-T1 / OKF §4.1 hard 3 rule)
- **외부 consumer feedback loop** — public GH Pages site 운영 후 issue 기반 follow-up

## Reference

- [v0.7.54 release note](Beta-v0.7.54.md) (직전, dispatcher 11 subcommand: I/J/K)
- [v0.7.53 release note](Beta-v0.7.53.md) (OKF CLI Dispatcher + audit 2차 + GH Pages)
- [v0.7.52 release note](Beta-v0.7.52.md) (Retrospective consolidation 통합본)
- `workflow-source/tools/release_pipeline_lib.py` (NEW, 67 line)
- `workflow-source/workflow_kit/workflow_kit_cli.py` (14 subcommand dispatcher, registry pattern)
- `workflow-source/tests/check_workflow_kit_cli.py` (20 dispatcher test)
- `workflow-source/tests/check_release_pipeline_lib.py` (NEW, 2 test)
