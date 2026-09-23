# Beta v1.11.0 (2026-09-23)

> **상태: 릴리스 준비.** package `1.11.0`, runtime `__version__ = 1.11.0`, tag `v1.11.0`.
> **minor release** — **판정이 아무것도 재지 않는데 숫자는 멀쩡했던 사이클.**
>
> 등급 근거 (§1.5): 공개 Python API 시그니처 변경 **0** (새 심볼 전부 순증 —
> `case_count.count_cases` · `CaseCount`, `repo_write_watch.RepoWriteWatch` · `Sighting`,
> `doc_layers.is_frozen_document` 외 3, `doc_stamp.last_content_change_date` ·
> `dirty_paths` · `check_frontmatter_stamp`, `python_floor.declared_floor_string`) ·
> 진입점 제거 **0** (`--case-count-dump` 는 순증) · 산출물 형식 **후방 호환**
> (`MemoryIndexQueryOutput.empty_reason` 은 기본값 `""` 인 추가 필드 — 구 소비자가
> 읽던 키는 전부 남아 있다) · 외부 spec 무관. `!` 커밋 **0**.
> `wk release-status` 파생도 minor (`next_version: 1.11.0`, unreleased 34).

## 0. 릴리스 판정

이 사이클의 주제는 **"통과했다는 것과 무엇을 쟀다는 것은 다른 질문이다"** 다.

다섯 개의 판정이 전부 같은 모양으로 고장나 있었고, 전부 **아무 검사도 실패하지 않은
채로** 그랬다.

| 판정 | 무엇을 재고 있었나 | 무엇을 재야 했나 |
|---|---|---|
| memory_index 승격 후보 | 제목↔entry **어휘 겹침** (평균 0.22 · 임계 0.5 미도달 → 매 세션 '0건' 상수) | entry 가 `source_paths` 로 인용한 **task 선언** |
| 검사 요약의 `N/M` | 손으로 박은 상수 (20건 중 4건이 이미 갈려 있었다) | 실제로 **발화한 case 수** |
| memory_index 검색 | seed 와 확장분을 **ID 사전순**으로 잘라 매칭된 것 자신이 밀림 | seed 먼저, 확장은 hop 거리순 |
| 질의 token 유도 | `current_axis` 한 줄이 130 token 이라 상한 8을 독점 (`done_items` 기여 **0**) | 출처마다 몫 — 변하는 쪽이 절반 |
| 건너뛴 테스트 | `SKIP` 만 찍고 `True` — **미측정이 통과로** | 요약에 숫자로 (`5/5 PASS (1 skipped)`) |

네 번째가 특히 고약했다. ADR-006 W-2 가 *'고정 trio 가 33일간 같은 entry 를 집었다'*
를 고치려고 질의를 컨텍스트 유도로 바꿨는데, **유도 결과가 또 다른 고정 질의**가 돼
있었다 — 증상은 그대로고 이름만 바뀌었다.

**이 릴리스에 발행할 이유가 있다.** `wk session-start` · `doc-sync` · `backlog-update`
세 소비자의 memory_index 조회가 **내내 `selected_count: 0`** 이었고 아무도 몰랐다.
이제 같은 호출이 실제로 entry 를 돌려준다 (이 저장소 실측 0 → 4건).

## 1. 릴리스 요약

- 범위: `v1.10.0..HEAD` (34 commit). 이 중 14건은 memory·환경 기록이고 1건
  (`138304ac`)은 **v1.10.0 발행 마무리**가 태그 뒤에 착지한 것이라 실질은
  **19 commit** 이다.
- 누적 smoke **292/292 PASS** (브랜치 2 × 해석기 2 = **4셀** 전량 · FAIL 0,
  로컬 `--branch-context=all` 은 584/584 = 292 × native/slash).
- 검사 **290 → 292** (`check_case_count` · `check_memory_index_retrieval` 신설).
- memory_index entry **22 → 29**.

## 2. 소비자에게 보이는 변화

### 2.1 memory_index 조회가 실제로 돌아온다 (가장 큰 변화)

세 도구(`session-start` · `doc-sync` · `backlog-update`)의 retrieval 배선이 **장식**
이었다. 원인이 셋 겹쳐 있었다:

1. **선택이 매칭된 것을 버렸다.** `sorted(seed_and_linked)[:top_k]` — ID 가
   `MEM-<날짜>-<번호>` 라 사전순 = 날짜순이고, 링크 관례가 최신 → 기존(단방향)이라
   확장분이 항상 seed 보다 오래됐다. entry 의 **정확한 cue** 로 질의해도 그 entry 가
   상위 3에 한 번도 안 들었다 (실측 3/3). `cue_hits=1` 을 보고하면서 그 1건을 안
   돌려주는 상태였다.
2. **질의가 상수였다.** `current_axis` 가 token 상한을 독점해 `done_items` 기여가
   정확히 0 — 세 도구가 전부 같은 질의를 냈다.
3. **1단계가 구조적으로 못 맞췄다.** `cue_anchors` 는 영문 kebab 관례인데 유도 질의는
   한국어 산문이고, `use_bm25_fallback` 기본값이 `False` 였다.

셋을 고쳤고 세 도구의 BM25 를 켰다. 빈 결과는 이제 **사유를 내놓는다**
(`empty_reason` + `warnings`) — `count: 0` 만으로는 색인이 빈 것인지, 질의가 안 맞은
것인지, 단계가 꺼진 것인지 구분되지 않았고 셋의 처방이 다르다.

### 2.2 승격 후보 제안이 의미 있는 목록을 낸다

`wk suggest-memory-entries` 의 coverage 가 어휘 겹침에서 **선언(entry 의 task 인용)**
으로 바뀌었다. `covered=0 / candidates=10` 상수 → `covered=7 / candidates=3 /
unmeasured=8`. 인용이 없는 entry 는 '안 덮음' 이 아니라 `entries_without_task_citation`
으로 **따로** 나온다 — 못 잰 것을 나쁨으로 세지 않는다. skeleton 의 `source_paths` 에
출처 task 경로를 미리 채워, 다음 승격부터 규약이 자동으로 지켜진다.

### 2.3 게이트에 축이 하나 늘었다 — 요약이 발화 수와 갈리면 red

검사가 찍는 `N/M` 의 `M` 이 상수이면 case 를 늘려도 줄여도 숫자가 안 바뀐다.
**무력화가 숫자에서도 안 보인다.** 판정은 러너가 매 실행 전수로 하고 재실행 비용이
0이다 (이미 각 검사의 출력을 전량 받아 두므로 — 경고 축 · 저장소 write 축과 같은 자리).

측정 범위를 **실측으로** 정했다: 처음엔 290 중 28개만 읽혔고, 세 번의 확장 끝에
**212/292** 가 됐다. 미측정은 통과로 세지 않고 사유별로 보고한다.

새 조사 수단: `run_all_checks.py --case-count-dump <PATH>` — 검사별 (선언·발화·측정·
사유)를 JSON 으로 낸다.

### 2.4 CI flake 하나 제거

`check_release_wrapper_args` case 6 이 `git add --dry-run` 을 써서 **dry-run 이어도
index 락**을 잡았고, 병렬 구간에서 간헐적으로 `fatal: Unable to create .git/index.lock`
로 죽었다. 읽기 전용(`git ls-files --error-unmatch`)으로 바꿨다 — 락을 인위로 쥐고
재면 add 는 rc=128, ls-files 는 rc=0.

## 3. 새 심볼 (전부 순증)

| 모듈 | 심볼 |
|---|---|
| `workflow_kit/common/case_count.py` (신설) | `count_cases` · `CaseCount` |
| `workflow_kit/common/repo_write_watch.py` (신설) | `RepoWriteWatch` · `Sighting` |
| `workflow_kit/common/doc_layers.py` (신설) | `is_frozen_document` · `is_record_layer` · `is_frozen_claim_layer` · `is_gitignored` |
| `workflow_kit/common/doc_stamp.py` (승격) | `last_content_change_date` · `dirty_paths` · `check_frontmatter_stamp` |
| `workflow_kit/common/python_floor.py` | `declared_floor_string` |
| `MemoryIndexQueryOutput` | `empty_reason` (기본값 `""`, 추가 필드) |

## 4. 검증

- 게이트 `--branch-context=all` **584/584** (292 × native/slash) rc=0, 불일치 0.
- CI 4셀(브랜치 2 × 해석기 2) green — HEAD `709eb23c`.
- 이 사이클의 수리마다 **되주입**으로 각 판정이 살아 있음을 실증했다 (main-003 5종 ·
  main-004 7종 · main-005 6종 · main-006 5종 · main-007 4종). 각각 서로 다른 지문을
  남겼고 복원 해시가 원본과 일치했다.

## 5. 알려진 한계 (감추지 않는다)

- case 수 대조 축이 **292 중 212** 만 읽는다. 남은 80건 중 76건은 case 줄을 아예 안
  찍는 단일 판정 검사라 계약 밖이고, 4건은 개수만 선언하고 나열이 없어 대조 대상이
  없다. **실질 잔여는 0** — 선언 없이 case 줄을 찍는 검사는 하나도 남지 않았다.
- memory_index entry 29건 중 **8건은 task 인용이 없다** (2026-08-10 이전 생성분).
  소급이 불가해 `entries_without_task_citation` 으로 미측정에 남는다.
- entry 간 링크는 **단방향**(최신 → 기존)이고 이 릴리스는 그것을 바꾸지 않았다.
