# Beta v0.15.20 — v1.0.0 pre-release final (2026-07-20)

> v1.0.0 stable 진입 직전의 **pre-release final** package.
> stable API 명세 final review + SemVer 2-year guarantee doc + migration guide final.
> v1.0.0 stable release 의 1 release 직전.

## 1. 릴리스 요약

- **stable API 명세 final review**: v0.8.0 spec 의 25 entries (`workflow_kit.__all__`) 와 runtime 정합 (25/25 importable).
- **SemVer 2-year guarantee 문서 신규**: `workflow-source/core/stable_guarantee.md` — 2026-07-20 ~ 2028-07-20 (2년) 의 public API backward compat guarantee.
- **Migration guide final**: v0.15.0 release note 의 3가지 migration 정공법 (opt-in flag / 명시 path / 자연 fallback) 정합 final review.
- **v1.0.0_entry_evaluation.md final update**: 5/6 gate PASS + 1 conditional (mypy) verdict.
- v1.0.0 stable 진입 준비 완료 (venv 활성화 후 mypy strict verify 만 남음).

## 2. deliverable (3개)

### 2.1 `workflow-source/core/stable_guarantee.md` (신규)

v1.0.0 stable 진입 시점의 **SemVer 2-year backward compat guarantee** 명세.

- **Public API Surface**: `workflow_kit.__all__` 25 entries frozen (bitbucket_v2 / cache_analytics* 8종 / lfu_config / lfu_integration / okf_export / okf_import / path_resolver / phishing_federation / phishing_keywords / release_status / upgrade_diff / url_validity / v_r13_commit_diff / workflow_kit_cli).
- **Skill Stable API**: 12 stable skill 의 CLI argparse / Pydantic schema / Error codes 정공법 정합.
- **MCP Stable API**: 11 stable MCP + transport contract (jsonrpc-bridge default + stdio-sdk variant).
- **Harness Stable API**: 11 harness overlay 의 entry point 자동 read 정합.
- **Guarantee 의 한계 (5개 명시 제외 영역)**:
  1. TST-WF-01 historical infrastructure (39% of 196 smoke).
  2. state.json / Panel 5 transient (release memory cycle).
  3. 외부 library 의존성 (`mcp>=1.27.0`).
  4. 외부 하네스 진입점 변경 (Codex / OpenCode / Grok Build 등).
  5. Beta / alpha / prototype stage 의 API.
- **Migration 가이드 3가지 정공법**: opt-in flag / 명시 path / 자연 fallback.

### 2.2 `workflow-source/core/v1_0_0_entry_evaluation.md` (final update)

- 6 gate criteria 의 verdict 갱신 (Gate 1~5 PASS + Gate 3 mypy conditional).
- §8 결론에 v0.15.17 + v0.15.18 + v0.15.19 close-out 반영.
- 다음에 읽을 문서에 `./stable_guarantee.md` link 추가.

### 2.3 stable API runtime 검증

`workflow_kit.__all__` 25 entries 의 runtime import 가능성 정합 검증:

```
Total __all__ entries: 25
__version__: v0.15.19-beta
All __all__ entries importable
```

## 3. 검증

- **stable API 25/25 importable**: `__version__` + 24 top-level public modules 모두 runtime 정합.
- **누적 smoke test 24/24 PASS** (회귀 0): v0.15.19 cross-panel final anchor 유지.
- **Panel 1~8 정합** (v0.15.19 close-out).
- **v1.0.0_entry_evaluation.md** 5/6 gate PASS + 1 conditional (mypy strict direct verify).

## 4. v1.0.0 진입 평가 최종 진행 상황

| Break Point / Anchor | 상태 |
|---|---|
| #1 state.json / Panel 5 | ✅ CLOSED-OUT (v0.15.17) |
| #2 TST-WF-01 non_compliant | ✅ CLOSED-OUT (v0.15.18) |
| Cross-panel final anchor | ✅ CLOSED-OUT (v0.15.19) |
| **v1.0.0 pre-release final** | ✅ **CLOSED-OUT (v0.15.20)** |
| #3 mypy strict 직접 verify | ⏳ venv 활성화 후 (CI 3-layer defense 정합으로 운영 risk 낮음) |

## 5. 다음 단계

- venv 활성화 후 `mypy workflow-source/ --strict --extra mcp-sdk` 0 errors 검증 (Break Point #3 close-out).
- **v1.0.0 stable release** (tag `v1.0.0-beta` 또는 `v1.0.0` 정식 release — 정책 결정 필요).
- Phase 12 in_progress close-out + Phase 13 (운영 지능화) follow-up 정의.

---

release target: `v0.15.20-beta`
