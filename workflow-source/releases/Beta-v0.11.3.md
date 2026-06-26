# Beta v0.11.3 — mypy strict 단계적 격상 11-12단계 (purpose_ingest + purpose_graph) (2026-06-26)

> **SemVer patch** (v0.11.2 → v0.11.3) — v0.11.0 release note 의 "다음" §3 follow-up. **mypy strict 누적 격상 19 → 21 file** (cycle 3 / cycle 4 의 신규 작성 module 의 strict clean 정식 인정). v0.8.0 spec §5.3 의 단계적 격상 정공법 정합 — **1 release = 1-2 file 단계적 격상**. **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (1 신규 검증 + 1 누적 갱신 + 1 acceptance test)

### 1. mypy strict clean verify (purpose_ingest + purpose_graph)

**v0.11.0 cycle 3 / v0.11.1 cycle 4 의 신규 작성 module 의 strict clean 정식 인정**:

| File | 신규 작성 | strict error | 누적 file count |
|---|---|---|---|
| `workflow-source/workflow_kit/common/purpose_ingest.py` | v0.11.0 (15,455 bytes, 5 dataclass + 6 public 함수) | **0** | +1 (19 → 20) |
| `workflow-source/workflow_kit/common/purpose_graph.py` | v0.11.1 (17,603 bytes, 7 dataclass + 6 public 함수) | **0** | +1 (20 → 21) |

**mypy 2.1.0 strict 기준 verify**:
```bash
$ mypy --no-incremental workflow-source/workflow_kit/common/purpose_ingest.py
# purpose_ingest.py: 0 strict errors
$ mypy --no-incremental workflow-source/workflow_kit/common/purpose_graph.py
# purpose_graph.py: 0 strict errors
```

### 2. 누적 strict clean file count 갱신 (19 → 21)

**`workflow_kit/__init__.py` docstring 갱신** (cumulative count 명시):
```
Cumulative mypy strict clean file count (v0.8.0 spec §5.3 단계적 격상 정합):
    - v0.8.0~v0.8.15: 19 file strict clean
    - v0.11.0 cycle 3 (TASK-V1110-001): + purpose_ingest.py
    - v0.11.1 cycle 4 (TASK-V1111-001): + purpose_graph.py
    - v0.11.3 누적: 21 file strict clean (mypy 2.1.0 strict 기준)
```

### 3. Mypy baseline context (참고)

전체 `workflow_kit/` 의 mypy 2.1.0 strict error = **34 errors in 14 files** (v0.11.2 시점). 본 release 는 신규 작성 module 의 strict clean 만 정식 인정하며, 기존 14 file 의 strict error 는 v0.11.4+ follow-up cycle 에서 단계적 해소 (1 release = 1-2 file 격상 정공법 정합).

## 운영 누적 (v0.11.2 → v0.11.3)

| | v0.11.2 | **v0.11.3** |
|---|---|---|
| **SemVer bump** | patch | **patch** |
| **mypy strict clean file** | 19 | **21** (+2) |
| **전체 workflow_kit/ strict error** | 34 errors in 14 files | **34 errors in 14 files** (변동 ❌, 기존 file 격상 follow-up) |
| **cumulative acceptance** | 82/82 | **83/83** (v0.11.3 1 신규) |
| **breaking change** | none | **none** (strict 검증만) |

## Test 결과

- 신규 (1 PASS, v0.11.3):
  - `test_mypy_strict_clean_v0_11_3` — purpose_ingest.py + purpose_graph.py strict clean verify (0 errors each) + workflow_kit/__init__.py cumulative count 갱신 verify (max=21)
- 회귀 (82/82 PASS, 변동 ❌)
  - v0.11.2: 5/5
  - v0.11.1: 8/8
  - v0.11.0: 6/6
  - v0.10.3: 7/7
  - v0.10.2: 9/9
  - v0.10.1: 6/6
  - v0.10.0: 6/6
  - v0.9.x (purpose series): 27/27
  - v0.9.0 + v0.9.3 + v0.9.1: 14/14
- 누적 acceptance: **83/83 PASS**
- 누적 smoke: **162/162 + 83 별도 subset**

## 변경 파일 (3 변경 + 2 신규)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/workflow_kit/__init__.py` | loud fallback `"v0.11.2-beta"` → `"v0.11.3-beta"` + cumulative strict clean count docstring 추가 (19 → 21 명시) |
| M | `workflow-source/pyproject.toml` | version 0.11.2 → 0.11.3 |
| M | `ai-workflow/memory/active/state.json` | in_progress + latest_backlog_path 갱신 + recent_done prepend |
| A | `workflow-source/tests/check_mypy_strict_v0_11_3.py` | 신규 (1 acceptance test, ≈ 130 line) |
| A | `workflow-source/releases/Beta-v0.11.3.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.11.3/backlog/2026-06-26.md` | v0.11.3 plan |

## 다음 (v0.11.4+ / v1.0.0)

1. **v0.11.4+** — strict clean file count 추가 격상 (22 → 23-24 → ...). 1 release = 1-2 file 단계적 (기존 14 file 의 strict error 단계적 해소).
2. **v1.0.0 milestone** — full mypy strict 도달 (semver major 정렬, 100+ release 후 예상). spec §9 acceptance 12/12 도달 유지.
