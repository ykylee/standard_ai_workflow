# Beta v0.9.2 — purpose.md concept 흡수 (외부 reference 차용 정공법 1차 적용, 2026-06-19)

> Phase 12 의 *외부 reference concept 흡수* 첫 release. Karpathy `llm-wiki.md` 패턴 + llm_wiki (nashsu) 의 *Purpose.md — The Wiki's Soul* 4-element concept 을 우리 workflow state docs layer 에 정형화. **bundle 비율 ~75%**, 1차 출처 GPLv3 영향 회피 (*코드 직접 차용 ❌*). **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (1 release, 1 task, 1 신규 spec + 1 신규 file + 1 file edit + 1 신규 test file)

### 1. purpose.md concept 흡수 (외부 reference 차용 정공법 1차 적용)

**1차 출처**:

- Karpathy `llm-wiki.md` (원본) — purpose.md 명시 ❌, 3-layer / 3 operations baseline
- llm_wiki (nashsu/llm_wiki) README §"Purpose.md — The Wiki's Soul" — 4-element 추가
- llm_wiki repo: <https://github.com/nashsu/llm_wiki>

**bundle 비율** (~75%):

| concept | bundle | 비고 |
|---|---|---|
| 4-element (Goals/Questions/Scope/Thesis) | 100% | 1차 출처와 동일 |
| LLM context read pattern | 80% | follow-up (R-A) |
| Suggest-update trigger (R-A) | 60% | R cycle 부분 통합 |
| schema/purpose 분리 (별도 file) | 100% | file 분리 정공법 |
| LLM suggest update 자동화 (UI) | 0% | Tauri 한정, stack 외 |

**우리 흡수 정공법**:

- **신규 `ai-workflow/memory/active/PURPOSE.md`** — 4-element (Goals / Key Questions / Research Scope / Evolving Thesis) + frontmatter (`purpose_version: 1`, `last_purpose_review: 2026-06-19`)
- **`PROJECT_PROFILE.md` §0 Purpose 참조 추가** — *directional intent* 의 SSOT 링크
- **신규 `workflow-source/core/llm_wiki_concept_purpose_spec.md`** — 1차 출처 + concept 정의 + 우리 흡수 정공법 + acceptance criterion + bundle 비율 + LICENSE 안전선
- **신규 `workflow-source/tests/check_purpose_concept_v0_9_2.py`** — 8 acceptance test (4-element + LLM-readable + structural verify)

**follow-up** (R-A Purpose Refresh, 별도 cycle 8):

- `state.json` 의 `purpose_digest` 1-line summary
- session-start / backlog-update / doc-sync skill 의 context load 에 PURPOSE.md 자동 read
- 30일 안 ingest/query 분포 → LLM suggest (advisory, human confirm)
- `wiki-event-sync` 의 release event hook

## 운영 누적 (v0.9.1 → v0.9.2)

| | v0.9.1 | **v0.9.2** |
|---|---|---|
| **외부 reference 흡수 정공법** | 미정립 | **1차 적용** (Karpathy + llm_wiki) |
| **directional intent SSOT** | PROJECT_PROFILE.md 안 섞여있음 (TODO placeholder) | **PURPOSE.md 분리, 4-element 정형화** |
| **LLM context read pattern** | 미정 | **follow-up R-A (cycle 8)** |
| **Suggest-update trigger** | 미정 | **follow-up R-A (cycle 8)** |
| **acceptance test 누적** | 162/162 PASS + 10 별도 subset | **162/162 PASS 유지 + 18 별도 subset** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8) |
| **spec layer chapter** | chapter 1+2+3+4+5 | **chapter 6** (cycle 7) |
| **Phase 12 진척** | 3/6 | **3/6 + 1 concept 흡수** |

## In-scope 발견 (cycle 7 검증 중)

- **fix 1 (real)**: 우리 `PROJECT_PROFILE.md` 의 §1~§5 가 *placeholder 상태* (대부분 "TODO" 비어있음). 이 자체가 *directional intent 부재* 의 1차 출처 — llm_wiki 의 purpose.md concept 이 *정확히* 이 gap 을 채움. cycle 7 의 PURPOSE.md 신규가 이 gap 의 *운영적 fix*.
- **fix 2 (real)**: 우리 R-1~R9 cycle 에 *purpose refresh* 단계 부재. R-A 추가가 *운영 lifecycle* 의 gap fill. follow-up (cycle 8).
- **fix 3 (real)**: 1차 출처 llm_wiki 가 GPLv3. 우리 저장소 LICENSE 미보유 (default all-rights-reserved). *코드 직접 차용* 시 우리도 GPLv3 영향. **concept/정공법만 차용** + 우리 own implementation 정공법으로 안전선 확보. spec §8 LICENSE 안전선.

## Test 결과

- 신규 (8 PASS, v0.9.2+):
  - `test_purpose_file_exists_v0_9_2` — PURPOSE.md exists
  - `test_purpose_4_element_sections_v0_9_2` — §1~§4 non-empty
  - `test_purpose_frontmatter_v0_9_2` — `purpose_version: 1` + `last_purpose_review: YYYY-MM-DD`
  - `test_project_profile_purpose_reference_v0_9_2` — §0 + PURPOSE.md reference
  - `test_goals_minimum_count_v0_9_2` — Goals G1+ (≥3)
  - `test_key_questions_minimum_count_v0_9_2` — Q1+ (3-5)
  - `test_research_scope_include_exclude_v0_9_2` — 포함/제외 영역
  - `test_evolving_thesis_hypothesis_v0_9_2` — hypothesis / 가설 명시
- 누적 smoke test: **162/162 PASS 유지** (신규 8 test 별도 subset)

## 변경 파일 (4 변경 + 1 doc sync)

| 변경 | File | 변경량 |
|---|---|---|
| A | `workflow-source/core/llm_wiki_concept_purpose_spec.md` | spec 신규 (외부 reference 흡수 정공법 1차 적용, 1차 출처 명시 + LICENSE 안전선) |
| A | `ai-workflow/memory/active/PURPOSE.md` | 4-element 본문 + frontmatter 신규 |
| A | `workflow-source/tests/check_purpose_concept_v0_9_2.py` | 8 acceptance test 신규 |
| A | `workflow-source/releases/Beta-v0.9.2.md` | release note (본 file) |
| M | `ai-workflow/memory/active/PROJECT_PROFILE.md` | §0 Purpose 참조 추가 |
| M | `README.md` + `ai-workflow/memory/active/work_backlog.md` | doc sync (cumulative summary + index) |

## 다음 (v0.9.3+ / v1.0.0 milestone)

1. **v0.9.3 follow-up** — R-A Purpose Refresh follow-up: `state.json.purpose_digest` + session-start context load + R-A trigger (wiki-event-sync release event hook). spec §5 follow-up 항목 3건.
2. **v0.9.4 follow-up** — deprecation 2nd cycle 영향 symbol 식별 + 적용 (1st cycle 운영 검증 결과 기반). 1st cycle 의 consumer feedback (warning log 빈도, migration 비용) 분석 후 2nd cycle 대상 결정.
3. **v0.9.5 follow-up** — external reference 흡수 cycle 2: file deletion cascade cleanup (3-method matching) 정공법 우리 wiki 운영 R 단계에 적용.
4. **v0.9.6 follow-up** — external reference 흡수 cycle 3: two-step CoT ingest (session-start → backlog-update 2-step contract) 명문화.
5. **v0.9.7 follow-up** — external reference 흡수 cycle 4: graph insights (surprising + gaps) 정형화.
6. **v0.10.0** — **deprecation 1st cycle 종료**: `phishing_federation_v4` 를 `__all__` 에서 제거 + `ImportError` raise. consumer 가 *명시적 except* 없으면 hard fail.
7. **v1.0.0 milestone** — full mypy strict 도달 (semver major 정렬, 100+ release 후 예상). spec §9 acceptance 12/12 (현재 9/12).
