# v0.8.0 Stable API Spec

- 문서 목적: v0.8.0 의 *stable-grade 약속* 범위와 그에 따르는 breaking change / API freeze / mypy strict / generated schema SSOT 기준을 정의한다.
- 범위: public API surface, deprecation policy, breaking change list, mypy strict 단계, generated JSON Schema 단일 출처, PyPI 정식 배포 절차
- 대상 독자: workflow_kit consumer, 저장소 maintainer, AI workflow 설계자
- 상태: draft (v0.7.62 종료 후 freeze)
- 최종 수정일: 2026-06-17
- 관련 문서: [`./workflow_release_spec.md`](./workflow_release_spec.md), [`./output_schema_guide.md`](./output_schema_guide.md), [`./workflow_kit_roadmap.md`](./workflow_kit_roadmap.md), [`./prototype_promotion_scope.md`](./prototype_promotion_scope.md), [`./read_only_mcp_transport_promotion.md`](./read_only_mcp_transport_promotion.md)

## 1. 목적

v0.7.x 는 consumer signal / dispatcher surface / release pipeline 의 *수직 확장* 중심이었다. v0.8.0 은 major 버전이므로 *수평 약속의 격상* 이 필요하다.

본 문서는 v0.8.0 이 external consumer 가 *stable library* 처럼 의존 가능한 *API surface* 와 *운영 약속* 을 정의한다. v0.7.59 ~ v0.7.62 의 follow-up 흡수가 끝난 시점의 *마지막 단계* 이다.

## 2. v0.8.0 의 정체성 (Thesis)

- v0.8.0 = **"real product surface"** — 외부 consumer 가 `pip install standard-ai-workflow` 로 받아 *1.x 처럼* 의존 가능
- v0.8.0 의 *Beta-prefix* 는 유지한다 (workflow_release_spec.md §4 정공법). 다만 release note 에 *Stable API frozen* 섹션 명시
- v0.8.0 종료 시점: Phase 11 (실전 파일럿 검증) + prototype_promotion_scope §3.1 (reusable package 1단계) 모두 close

## 3. Public API Surface

### 3.1 stable 로 약속할 import surface

`workflow_kit/__init__.py` 의 `__all__` 로 명시. v0.8.0 부터 external consumer 는 `__all__` 의 심볼만 import 가능 (이름 변경 / 제거 시 SemVer deprecation policy 적용).

```python
# workflow_kit/__init__.py (v0.8.0)
__all__ = [
    # version
    "__version__",
    # public re-exports (stable)
    "constants",     # workflow_kit.constants
    "okf_import",
    "okf_export",
    "url_validity",
    "cache_lfu_decay",
    "cache_lfu_decay_persist",
    "cache_migration",
    "cache_dashboard",
    "cache_analytics",
    "phishing_federation",
    "phishing_keywords",
    "lfu_config",
    "lfu_integration",
    "path_resolver",
    "v_r13_commit_diff",
]
```

내부 submodule (예: `workflow_kit.common.*`, `workflow_kit.server.*`, `workflow_kit.contract_v1.*`, `workflow_kit.cli.*`, `workflow_kit.harness.*`) 은 internal prefix `_` 또는 `common.` 으로 표시. external import 가능하나 *no stability guarantee*.

### 3.2 deprecation policy

- v0.8.0 = **deprecation-free release**. 0.7.x 의 모든 public symbol 은 0.8.0 에서도 동일하게 import 가능
- v0.9.0 부터: deprecation 1 release (DeprecationWarning) → 1 release (실제 제거). 최소 2 release 의 notice 기간
- breaking change 는 major 버전에서만 허용 (SemVer)

### 3.3 tools/ 디렉터리

`tools/` 는 v0.8.0 부터 *public surface 의 일부* 이다. `__all__` 의 submodule 이 *in-process* 로 dispatcher (workflow_kit_cli) 가 호출하는 정공법 (v0.7.55+ release-doctor, v0.7.56+ score-wiki-trend, v0.7.59+ consumer-metrics).

- `tools/release_pipeline.py` — `validate` / `version-bump` / `note-draft` / `release` / `verify` / `rollback` / `dist` / `gen-schema` (v0.8.0 신규)
- `tools/score_wiki_trend.py` — `--record-current` / `--record-range` / `--show` / `--alert`
- `tools/consumer_metrics.py` — `--repo` / `--days` / `--json`
- `tools/score_wiki_maintainability.py` — 6 dim dashboard
- `tools/sync_release_hash.py` — post-step hash sync
- `tools/wiki_emit.py` — 3-step cycle
- `tools/archive_stale_memory.py` — cron + log rotation + metrics aggregation
- `tools/refresh_wiki_memory.py` — version tracking
- `tools/migrate_legacy_l2.py` — external wiki → in-repo
- `tools/emit_wiki_l2_body.py` — L2 page emit
- `tools/check_packaging.py` — wheel + sdist 검증

## 4. Breaking Change List (v0.7.x → v0.8.0)

본 release 에서 *breaking change 0건* 을 기본으로 한다. 단, 다음 *내부 contract* 가 *공식화* 되며 *외부 consumer 가 의존할 경우* 영향을 줄 수 있다.

### 4.1 mypy strict 단계 격상

`pyproject.toml [tool.mypy] strict = true` 격상. 기존 internal module 중 type annotation 이 부족한 경우 annotation 추가 (소규모 follow-up 1~2 release 가능, 본 release 범위 외로 분리). 외부 consumer 영향: 없음 (import 시점 contract 가 아니라 dev-time).

### 4.2 generated JSON Schema SSOT

`schemas/generated_output_schemas.json` 의 *source-of-truth* 가 `tools/release_pipeline.py gen-schema` (v0.8.0 신규) 로 통일. runtime contract (`workflow_kit.common.output_contracts`) = generated schema 단일 참조.

외부 영향: read-only MCP manifest / descriptor 의 `outputSchema` 가 *generated schema 와 byte-identical* 임을 assertion test 가 강제. 외부 consumer 가 *outputSchema* 를 신뢰 가능한 정적 schema 로 사용 가능.

### 4.3 `__version__` 단일 출처

`workflow_kit/__version__` = `pyproject.toml [project] version` 단일 출처. 기존 `workflow_kit/__init__.py` 의 `__version__ = "v0.7.58-beta"` literal 은 *generated* 으로 교체 (cmd_release --apply 의 side effect).

외부 영향: `__version__` 의 suffix 가 `"v0.8.0-beta"` 형식으로 통일됨.

### 4.4 dispatcher 27 → 28+ (v0.7.60+ 에서 흡수)

v0.7.60 에서 dispatcher 28~30 추가 (`cache-lru-decay` / `cache-lfu-decay-persist` / `cache-merge-csv`). v0.8.0 시점에는 subcommand surface 가 *28+ stable* 임을 약속. subcommand 이름 / argv surface 의 breaking change 는 major 버전에서만.

## 5. mypy strict 단계

### 5.1 목표

- `pyproject.toml [tool.mypy] strict = true`
- `disallow_untyped_defs = true`
- `warn_return_any = true`
- `warn_unused_configs = true`
- `ignore_missing_imports = true` (third-party SDK, e.g. `mcp[cli]`, 는 유지)

### 5.2 검증

```bash
mypy workflow-source
# expected: Success: no issues found in N source files
```

CI 단계에서 `mypy workflow-source` 가 0 error 이어야 release 가능.

### 5.3 단계적 격상 (선택)

v0.8.0 RC 단계에서 annotation 이 부족한 internal module 이 발견되면:

1. `tool.mypy.overrides` 로 module 별 단계적 enable (예: `module = ["workflow_kit.common.contracts", "workflow_kit.contract_v1"]`, `disallow_untyped_defs = true`)
2. v0.8.0 final 직전 *남은 module* 에도 override 추가 → `strict = true` 격상
3. annotation 추가 PR 은 v0.8.0 final 직전까지 1~3 release (0.8.0-rc1 ~ 0.8.0-rc3) 로 분할 가능

## 6. generated JSON Schema SSOT

### 6.1 source-of-truth

`tools/release_pipeline.py gen-schema --output=schemas/generated_output_schemas.json` 가 runtime contract 로부터 schema 를 *재생성*. manual edit 불가 (CI 가 *generated* 임을 검증 — header 의 `// GENERATED: do not edit` marker + 마지막 commit 의 author 가 `release-pipeline` 인지).

### 6.2 runtime contract 참조

`workflow_kit.common.output_contracts` 의 모든 tool family 의 `output_schema` field 가 *generated* schema 의 path 또는 inlined dict 를 참조. read-only MCP manifest / descriptor 의 `outputSchema` 도 같은 source.

### 6.3 verification

```bash
python tools/release_pipeline.py gen-schema --check
# exit 0 = generated schema 가 runtime contract 와 byte-identical
# exit 1 = drift detected (regen 필요)
```

CI 단계에서 `gen-schema --check` 가 0 이어야 release 가능.

## 7. PyPI 정식 배포

### 7.1 절차

1. `python -m build` (wheel + sdist) → `dist/`
2. `python -m twine check dist/*` → metadata 검증
3. TestPyPI dry run: `twine upload --repository testpypi dist/*`
4. TestPyPI install 검증: `pip install -i https://test.pypi.org/simple/ standard-ai-workflow==0.8.0b0`
5. Production upload: `twine upload dist/*`

### 7.2 자동화

`tools/release_pipeline.py release-dist --apply` 가 *1-command* 로 build + check + TestPyPI dry run 까지. production upload 는 `--apply --production` 명시 필요 (의도적 2-step).

### 7.3 release note 의 PyPI 명시

`Beta-v0.8.0.md` 의 *Assets* 섹션에 PyPI URL 명시:
- `pip install standard-ai-workflow==0.8.0b0` (beta)
- `pip install standard-ai-workflow==0.8.0` (stable, v0.8.0+ 후속 release 부터)

## 8. Beta-prefix 유지 + Stable-grade 약속

### 8.1 명명

- release note: `workflow-source/releases/Beta-v0.8.0.md`
- git tag: `v0.8.0-beta`
- GH Release: `Beta v0.8.0 — Stable API frozen`
- pyproject version: `0.8.0-beta` (PEP 440: `0.8.0b0`)
- `__version__`: `"v0.8.0-beta"`

### 8.2 release note 의 *Stable API frozen* 섹션

필수 포함 항목:

- 📌 **Stable API frozen**: public surface (`workflow_kit.__all__`), tools/ surface, dispatcher subcommand surface, `__version__` 단일 출처
- 🔒 **Stable guarantees**: SemVer 2-year (0.8.0 → 2.0.0 까지) — breaking change 없음, deprecation 2 release notice
- 🚨 **Breaking changes from 0.7.x**: §4 의 list (없으면 "None" 명시)
- 📦 **PyPI**: `pip install standard-ai-workflow==0.8.0b0` (TestPyPI / Production 분리 명시)
- ✅ **Verification**: mypy strict clean, gen-schema --check clean, cumulative test ≥ 5 module 98 + dispatcher ≥ 43 + tools ≥ 7

## 9. Acceptance Criterion (v0.8.0 done 의 정의)

본 release 가 *done* 으로 인정되려면 아래가 모두 true 여야 한다.

- [ ] `mypy workflow-source` exit 0, "no issues found" 출력
- [ ] `python -c "import workflow_kit; assert workflow_kit.__version__ == 'v0.8.0-beta'"`
- [ ] `workflow_kit/__init__.py` 의 `__all__` 에 §3.1 의 public surface 명시
- [ ] `tools/release_pipeline.py gen-schema --check` exit 0
- [ ] `tools/release_pipeline.py gen-schema --output=schemas/generated_output_schemas.json` 가 byte-identical
- [ ] `read-only MCP manifest / descriptor` 의 `outputSchema` 가 generated schema 와 byte-identical (assertion test)
- [ ] `tools/release_pipeline.py release-dist --apply` 가 1-command 로 build + check + TestPyPI dry run 완료
- [ ] `Beta-v0.8.0.md` 에 *Stable API frozen* 섹션 + *Breaking changes* 섹션 + *PyPI* 섹션 존재
- [ ] cumulative 5 module test ≥ 98 PASS
- [ ] cumulative dispatcher test ≥ 43 PASS
- [ ] cumulative tools test ≥ 7 PASS
- [ ] v0.7.59 ~ v0.7.62 follow-up (A~F) 모두 done

## 10. 의존성 (의존하는 release)

- v0.7.59 (A. consumer-metrics in-process) — done
- v0.7.60 (E. 5 module audit 4차 + C. dispatcher 28+) — done
- v0.7.61 (F. mkdocs `--strict` 진짜 활성화) — done
- v0.7.62 (B + D. consumer-metrics trend + weekly digest) — done

본 spec 은 v0.7.59 흡수 시점의 *초안* 이다. v0.7.62 종료 후 *최종 freeze*.

## 11. 다음에 읽을 문서

- 릴리스 규격: [`./workflow_release_spec.md`](./workflow_release_spec.md)
- 출력 스키마 가이드: [`./output_schema_guide.md`](./output_schema_guide.md)
- 워크플로우 키트 로드맵: [`./workflow_kit_roadmap.md`](./workflow_kit_roadmap.md)
- 프로토타입 승격 범위: [`./prototype_promotion_scope.md`](./prototype_promotion_scope.md)
- read-only transport 승격 기준: [`./read_only_mcp_transport_promotion.md`](./read_only_mcp_transport_promotion.md)
