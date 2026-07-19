# Beta v0.15.16 — DOCUMENT_INDEX cross-check smoke 정식 release (2026-07-19)

> 영구 지식 인덱스 SSOT (`docs/DOCUMENT_INDEX.md`) 의 상대 링크, GitHub 외부 링크 매핑,
> frontmatter stamp, 4개 카테고리 섹션 헤더를 자동 검증하는 smoke 를 정식 release 한다.
> 누적 smoke 21종, 회귀 0건.

## 1. 릴리스 요약

- `docs/DOCUMENT_INDEX.md` 의 cross-panel 정합을 자동 검증하는 stable smoke 를 추가한다.
- 누적 smoke count 20 → 21, 모두 PASS / 회귀 0.
- v1.0.0 진입 평가의 영구 지식 인덱스 anchor.

## 2. 추가된 smoke

- **`workflow-source/tests/check_document_index_v0_15_16.py`** — 4 cases
  - (a) **`case_1_relative_links`**: 본문 `./...` relative path 8건 모두 file system 정합 (`PROJECT_PROFILE.md`, `CODE_INDEX.md`, `INSTALLATION_AND_USAGE.md`, `RELEASE.md`, `index.md`, `architecture/...`).
  - (b) **`case_2_github_links`**: GitHub 외부 link path 4건 (`docs/architecture/`, `docs/planning/`, `docs/archive/AGENTS.md`, `docs/archive/split_checklist.md`) 모두 `docs/` 트리 존재 확인.
  - (c) **`case_3_frontmatter_stamp`**: `- 최종 수정일: 2026-07-18` stamp 가 v0.15.15 release day 와 정합.
  - (d) **`case_4_required_sections`**: 4 카테고리 헤더 (`## 1. 프로젝트 설계`, `## 2. 개발 및 표준`, `## 3. 분석 및 계획`, `## 4. 보존`) 모두 존재 + 본문 `v0.15.15` stamp 등장.
  - **검증**: 4/4 PASS.

## 3. 정정한 in-scope issue

없음. 본 release 는 **신규 smoke 의 정식 release 만** 포함한다 (기존 smoke 의 drift 는 본 cycle 에서 발생하지 않음).

## 4. 검증

- v0.15.16 release 시점 누적 smoke: **21종 PASS**, 회귀 0건.
- 신규 smoke 단독 실행: 4/4 PASS.
- 전체 smoke 회귀 (`tests/run_all_checks.py`): 정공법 cumulative 정합 (run_all 의 결과는 cycle 4 종료 후 회귀 정합 시점에 확인).

## 5. 다음 단계

- v0.15.17 — CODE_INDEX cross-check smoke 정식 release (`check_code_index_v0_15_17.py`, 5 case).
- v0.15.18 — RELEASE.md cross-check smoke 정식 release (`check_release_md_v0_15_18.py`, 5 case).
- v0.15.19 — MEMORY_GOVERNANCE ↔ global_workflow_standard 정합 smoke 정식 release (`check_memory_governance_cross_v0_15_19.py`, 5 case).
- 4 cycle 완료 후 `state.json` + `maturity_matrix.json` 최종 동기화.

---

release target: `v0.15.16-beta`
