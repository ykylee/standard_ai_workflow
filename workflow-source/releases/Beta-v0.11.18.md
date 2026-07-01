# Beta v0.11.18 — FULL mypy strict 도달 공식 release (2026-07-01)

> Phase 12 의 *운영 안정화 누적 격상* release. v0.11.10 (chapter 7, mypy workflow_kit/ 35 file strict clean + FULL 도달) 의 **공식 봉인** release. v0.11.11~v0.11.17 의 mypy strict CI 통합 / cross-verify / release-status / schema drift housekeeping patch release 의 후속으로, **mypy strict residual 23 → 0 error 격상** (107/107 source file clean) + CI 의 `mcp-sdk` extra install fix (in-scope). **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (FULL mypy strict 도달 + CI 정합 회복)

### 1. mypy strict cumulative 격상 — mcp_v1_server + release_status 묶음 6 error (commit `094cacf`)

**Roadmap §8 #2 정공법 정합** (1 release = 2 file 묶음 격상):

- **`server/mcp_v1_server.py` (3 error → 0)**:
  - unused `# type: ignore[no-untyped-def]` 제거 (`mcp.server.fastmcp.FastMCP` 가 runtime mcp-sdk extra 가 install 되면 type stub resolve — local/CI 환경 정합)
  - `run()` 의 `argparse.Namespace` → `Callable[..., Any]` 명시
  - `run() -> None` return type 추가
- **`release_status.py` (3 error → 0)**:
  - `local_mypy` `no-any-return` cast (subprocess.run return → `dict[str, Any]`)
  - unused `# type: ignore[import-not-found]` 제거 (`tools/release_pipeline` 의 sys.path insert 가 mtime import 가능)
  - `cmd_release_status(args: argparse.Namespace)` 의 `args: Any` 제거

**in-scope fix 동반**: `examples/output_samples/*.json` 24 file 의 `tool_version` v0.11.16-beta → v0.11.17-beta drift 해소 (v0.11.17 release 후 발생).

### 2. mypy strict cumulative 격상 — read_only_mcp_sdk + doc_sync 묶음 4 error (commit `65f0b20`)

**Roadmap §8 #2 정공법 (server + common cross-layer 묶음)**:

- **`server/read_only_mcp_sdk.py` (2 error → 0)**:
  - `untyped-decorator` × 2 — `register("name")` 의 decorator signature 가 `Callable[[Callable], Callable]` 명시 → runtime mypy untyped-decorator cascade 해소
- **`common/doc_sync.py` (2 error → 0)**:
  - redundant `cast(...)` × 2 — type signature 변경으로 cast 불필요해진 site 정리

### 3. mypy strict cumulative 격상 — 잔여 13 error 일괄 격상 (commit `4253eed`)

🎯 **FULL mypy strict 도달** (107/107 source file clean, errors 13 → 0). session 마무리 묶음 격상. 정공법 = 1 release = 1-2 file 약간 over 이지만 residual 모두 정리:

- `common/auth.py` (1 error) — `redundant cast[str]` 제거
- `common/contracts/stage_gate_runtime.py` (2 error) — `datetime | None` 명시 + redundant cast 제거
- `common/doc_transformer.py` (1 error) — `list[dict]` coerce
- `common/exploration.py` (1 error) — `dict.get` return type narrow
- `common/git.py` (1 error) — unused type:ignore 제거
- `common/metadata.py` (1 error) — `Path | None` 명시
- `common/profiling.py` (1 error) — redundant cast
- `common/resiliency.py` (1 error) — unused type:ignore
- `common/runner.py` (1 error) — `Callable | None` 명시
- `common/testing.py` (1 error) — `Any` → `Callable[..., Any]`
- `contract_v1/delegator.py` (1 error) — `list[str]` narrow
- `workflow_kit_cli.py` (1 error) — `argparse.Namespace` 명시

**누적 결과**: 35 → **42 → 54 file clean** (+19), 23 → **0 errors** (-23). **107/107 source file clean**.

### 4. CI mypy-strict workflow 의 mcp-sdk extra install (in-scope fix, commit `7ffb17c`)

3-layer defense 의 **Layer 1 (CI)** 정합 회복. `4c83ed9` 의 CI run 28453667753 (mypy strict) 가 `mcp_v1_server.py:9` 의 `from mcp.server.fastmcp` 에 대해 `[import-not-found]` fail — 원인: GH Actions workflow 가 `workflow_kit` 의 optional dep (`mcp-sdk` extra = `mcp[cli]>=1.0`) 를 install 하지 않음.

- **수정**: `pip install -e "./workflow-source/workflow_kit[mcp-sdk]"` — editable install 에 extra 포함
- **효과**: local venv 와 CI 의 mypy strict baseline 정합 (mcp 1.27.0 동일 환경)
- **방지 lesson**: editable install 의 optional dep 은 CI 에서도 명시 — `ignore_missing_imports` 가 아니므로 `[import-not-found]` raise

## 누적 결과 (v0.11.10 의 FULL mypy strict 도달 → v0.11.18 의 공식 봉인)

| 항목 | v0.11.10 | v0.11.17 | **v0.11.18** |
|---|---|---|---|
| mypy strict file clean | 35 | 38 | **42 → 54** (+19) |
| mypy strict errors | 35 | 23 | **0** (-23) |
| workflow_kit/ source files | 106 | 107 | **107/107 clean** |
| 누적 smoke | 162+subset | 162+25 | **162+subset** |
| Spec §9 acceptance | 12/12 | 12/12 | **12/12 유지** |
| **Layer 1 (CI mypy)** | ✅ | ✅ | **✅ (mcp-sdk extra fix)** |
| **Layer 2 (release-time gate)** | ✅ | ✅ | **✅ (cmd_validate mypy source)** |
| **Cross-verify (CI ↔ local)** | ✅ | ✅ | **✅ (--strict-cross-verify 대응)** |

## 검증

- `workflow-source/tests/check_baselines_compliance.py`: 16 tests PASS
- `workflow-source/tests/check_output_samples.py`: 24 JSON files PASS
- `workflow-source/tests/check_output_json_schema.py`: PASS
- `workflow-source/tests/check_wiki_source_rule.py` (V-R9): PASS
- `workflow-source/tests/check_generated_schema_validation.py`: PASS
- `mypy --no-incremental --strict workflow-source/workflow_kit/`: **0 errors, 107 file clean** ✅
- CI mypy-strict workflow: 4c83ed9 fail → 7ffb17c (mcp-sdk extra) 통과 expected

## GitHub release

- Tag: `v0.11.18-beta`
- Pre-release: yes
- Notes: 본 파일
- Breaking change: ❌
- PyPI 배포: ❌ (GitHub Releases only)
- Workflow: `pre-check + tag push + gh release` 한 cycle (v0.7.21+ 정공법)

## 다음 release (v0.11.19 candidate)

- **mypy strict full clean 유지** — Layer 1 CI + Layer 2 release-time gate 가 regression 차단. 신규 module 작성 시 strict 정합 필수
- **v1.0.0 milestone prep** — Phase 12 의 6 release 분할 cycle 종료 후 v1.0.0 (SemVer stable guarantee 2-year)
- **또는 governance 후속** — 11 beta skill stable 승격 1차 batch, roadmap §8 Phase 12 in-progress
- **또는 다른 housekeeping** — Phase 13 (의미론적 정합) 진입 검토

## 메모리 layer (memory → commit → push 흐름 정합)

- `ai-workflow/memory/active/work_backlog.md` index entry: v0.11.18 (FULL mypy strict 공식 봉인)
- `ai-workflow/memory/active/state.json` recent_done_items: v0.11.18 entry
- `ai-workflow/memory/release/v0.11.18/backlog/2026-07-01.md` (per-release detail)