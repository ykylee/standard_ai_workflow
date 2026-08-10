# ADR-006: ADR-005 Memory Index Implementation Retrospective

- 문서 목적: v0.11.22 의 ADR-005 memory_index 8 release (`Phase 1 prototype` ~ `Phase 3d backlog-update wiring`) 의 30일+ 실사용 retrospective. telemetry 실측 기반.
- 범위: merge rule / 3-tuple retrieval / skill wiring 의 실사용 데이터 회고 + 6 영역 평가 + 후속 작업 정의.
- 대상 독자: 워크플로우 설계자, 메모리 계층 설계자, 후속 release reviewer.
- 상태: **accepted (회고 완료, 2026-08-10)**
- 최종 수정일: 2026-08-10
- 관련 문서: [`./MICROSOFT_MEMORA_EVALUATION.md`](./MICROSOFT_MEMORA_EVALUATION.md), [`./ADR-005-memora-inspired-memory-index.md`](./ADR-005-memora-inspired-memory-index.md), [`./ADR-001-source-state-knowledge-3-layer-separation.md`](./ADR-001-source-state-knowledge-3-layer-separation.md), [`./ADR-004-llm-wiki-layer.md`](./ADR-004-llm-wiki-layer.md)

- **Status**: Accepted (placeholder v0.11.22 → 회고 본문 2026-08-10, TASK-2026-08-10-main-010)
- **Date**: 2026-07-02 (placeholder) / **2026-08-10 (retrospective)**
- **Supersedes**: —
- **Superseded by**: —
- **Resolves 후속**: ✅ 본 문서가 그 회고다. ADR 권장 창 (2026-08-01 ~ 2026-08-15) 안에 작성.

## Context

v0.11.22 (tag 2026-07-02) 의 ADR-005 memory_index 는 end-to-end milestone 에
도달했고, 본 ADR 은 당시 회고 *자리만* 박았다. 누적된 8 release / 8 commit
(`468ec7d → 2ab3b6c`):

```
ADR-005 결정 (468ec7d)
  ↓
Phase 1 prototype (e4c7343)         helper + schema + 8 smoke
Phase 1.5 state.json hook (4655e7c) 3 smoke (11/11)
Phase 2a --merge opt-in (d2d8a1c)   3 smoke (14/14)
Phase 2b BM25 fallback (5973146)    3 smoke (17/17, stdlib only)
Phase 3a dispatcher entry (7be5029) 2 smoke (19/19)
Phase 3b1 session-start wiring (73564d9) 2 smoke (21/21)
Phase 3c doc-sync wiring (c46d729)   2 smoke (23/23)
Phase 3d backlog-update wiring (2ab3b6c) 2 smoke (25/25)
```

placeholder 이후의 관련 이벤트 (회고 대상 기간에 포함):

- v0.13.1 (2026-07-09): telemetry sidecar (`memory_index/telemetry/events.jsonl`,
  subcommand 36) — 본 회고의 실측 데이터 원천.
- v0.13.2 (2026-07-09): drift auto-fix orchestrator (subcommand 37).
- v0.13.3 (2026-07-09): wiki↔memory bidirectional link sync (subcommand 38).
- 2026-07-09: 최초이자 유일한 entry 적재 — `MEM-2026-07-09-001` ~ `-007` (7건).
- v0.15.21 (2026-07-21): 3 skill 의 retrieval **자동 활성** (flag 없이도
  workspace 표준 `memory_index/` dir 존재 시 default query 로 조회) — AC2
  telemetry source 다양성 ≥ 4 달성의 수단.
- 2026-08-09 (TASK-014): `memory-index-query` skill beta → stable.

## 회고 데이터 (2026-08-10 실측)

**telemetry**: `events.jsonl` 256 events, 2026-07-09 ~ 2026-08-10 (33일 창,
활동 14일). 이하 모든 수치는 이 파일 전량 집계 + 당일 재현 실측이다.

| 항목 | 실측값 |
| --- | --- |
| source 분포 | session-start 211 / backlog-update 43 / doc-sync 1 / dispatcher 1 |
| query_tokens_count | **전 256건이 3** (= default `session,handoff,workflow`) |
| cue_hits | **전 256건이 1** (항상 `MEM-2026-07-09-001`, 재현 확인) |
| bm25_hits / expansion_hits / error | **전부 0 / 0 / 0** |
| selected_count | 전 256건이 1 |
| entries | 7건 (전부 2026-07-09 생성, **이후 33일간 신규 0**) |
| merge_state | 전 7건 `active` (LINKED / MERGED 0건) |
| query latency (100회 재현) | p50 **0.18ms** / p95 0.19ms / max 0.21ms |

한 줄 요약: **30일+ 의 "실사용" 은 사실상 단 하나의 고정 질의가 단 하나의 고정
entry 를 돌려받은 기록이다.** 3-tuple retrieval 은 1단계(cue exact) 로 수렴했고,
2단계(BM25)·3단계(expansion)·merge 는 한 번도 발동하지 않았다.

## 6 영역 회고

### 1. Phase 1 prototype (helper + schema)

- **평가: ✅ 설계대로 동작, 비용 무시 가능.** 7 entries 로드 + 3-tuple 전체
  query 가 p50 0.18ms — stdlib only 구현의 성능 목표는 논쟁의 여지 없이 달성.
  schema (Pydantic) 는 33일간 validation issue 0건.
- **한계**: prototype 이 상정한 "entry 가 쌓이는 세계" 가 오지 않았다 (영역 6).
  N=7 에서는 retrieval 계층의 설계 대부분이 검증 불가능하다 — smoke 가 검증한
  것은 *로직*이고, 실사용이 검증한 것은 *로직의 극히 일부 경로*다.

### 2. Phase 1.5 state.json hook

- **평가: ✅ 정합 유지.** `state.json.memory_entries` 는 entries/ 7건과 33일간
  일치 (rebuild 마다 재생성, 본 세션 재확인). branch-scoped 전환
  (2026-07-21) 과 layout 개편을 모두 무사 통과 — hook 이 reader/writer 양쪽에
  걸려 있던 덕분에 [state-json-silent-failing 류의 결함]이 여기서는 없었다.
- **주의**: `memory_entries` 는 state.json 에 **전문 복제** 된다. entry 가
  수십 건이 되면 state.json 비대의 첫 후보 — 현재는 문제가 아니나 영역 6 의
  write-path 후속과 함께 상한 규칙이 필요해질 것이다.

### 3. Phase 2a `--merge` opt-in canonical merge

- **placeholder 의 질문**: "advisory default 가 caller 의 aggro merge 를
  의도대로 막았는지."
- **실측: 호출 0건.** 33일간 `apply_memory_merge` 의 production 호출은 없다
  (전 entry `merge_state=active`, LINKED/MERGED 0건, merge 관련 telemetry 없음).
- **평가: ⚖️ 판정 불가가 정직한 결론이다.** "advisory default 가 aggro merge 를
  막았다" 고 쓰면 거짓이다 — 막은 게 아니라 **쓸 일이 없었다**. entry 7건이
  전부 서로 다른 주제라 병합 후보 자체가 없다. merge 는 entry 개수가 늘어나
  중복이 생길 때에만 의미가 생기는 기능이고, 그 전제(쓰기 경로)가 침묵했다.
- **의사결정**: default advisory **유지** (변경할 실측 근거 없음). Phase 4
  활성화 논의는 write-path 후속(§후속 작업 W-1) 이후로 연기.

### 4. Phase 2b BM25 fallback

- **placeholder 의 질문**: "`cue_hits < top_k` 인 비율, BM25 hit 의 quality,
  stdlib 구현의 latency."
- **실측: production 발동 0건 — 그리고 켰어도 기여 0.**
  - 발동 0 의 직접 원인: `use_bm25_fallback` 은 opt-in 인데 **켜는 production
    caller 가 없다** (3 skill 자동 활성 경로 모두 default False).
  - 본 회고에서 켜고 재현한 결과: default query 는 cue 가 이미
    `MEM-001` 을 선점하고, 나머지 6 entries 는 해당 질의에 대해 **전부 score
    0** → score-0 제외 규칙에 걸려 fill 0건. 다른 질의 4종
    (`mypy` / `strict,type-check` / `workflow` / `memora`) 도 동일 패턴 —
    score>0 entry 는 매번 정확히 1건이고 그 1건은 cue 로도 잡힌다.
  - 즉 **N=7 + 잘 큐레이션된 cue_anchors 세계에서 BM25 는 구조적으로 기여할
    공간이 없다.** cue 가 놓치는 질의는 BM25 도 놓친다 (`federation`,
    `registry` — 2026-08 의 주요 작업 키워드인데 entry 가 없어서 양쪽 다 0).
  - latency: BM25 를 포함해도 p95 0.19ms — placeholder 가 걱정한
    "rank_bm25 대비 성능" 은 무의미한 걱정이었다.
- **의사결정**: BM25+ tuning **기각**, embedding 3단계 추가 **기각** (둘 다
  실측 근거 없음 — 병목은 검색 품질이 아니라 질의와 데이터다). 코드는
  유지한다 (제거 비용 > 유지 비용, entry 가 늘면 재평가).

### 5. Phase 3a dispatcher entry

- **평가: ✅ 계약으로서 성공, 직접 사용은 0에 수렴.** telemetry 상 dispatcher
  직접 호출은 1건 (2026-07-09, 최초 검증) 뿐이지만, 3 skill wiring 이 전부
  `query_memory_index_for_dispatcher` **하나를 경유** 한다 — "다른 caller 가 본
  wrapper 만 호출하면 retrieval layer 자동 활용" 이라는 설계 의도가 그대로
  실현됐다. 2026-08-09 의 skill stable 승격 (error_code 3종 정비) 도 이 단일
  진입점 위에서 이뤄졌다.
- 교훈: **진입점 통일은 사용량이 아니라 계약으로 평가해야 한다.** 이 wrapper 의
  가치는 호출 횟수 1 이 아니라, 255건의 skill 호출이 전부 같은 코드 경로와
  telemetry 를 통과했다는 사실이다.

### 6. Phase 3b1~3d — 3 skill wiring (+ v0.15.21 자동 활성)

- **placeholder 의 질문**: "wiring 이 더한 wall-clock latency."
- **실측 (latency)**: query 전체가 p50 0.18ms — skill 실행 시간에서 측정
  오차 수준. **latency 는 비문제로 종결.**
- **실측 (사용 형태)**: 여기가 본 회고의 핵심 발견이다.
  - source 다양성 4 는 달성됐지만 분포는 session-start 82% / backlog-update
    17% / 나머지 2건. doc-sync 와 dispatcher 는 사실상 미사용.
  - **질의 다양성은 1** — 255건의 skill 호출 전부가 default
    `session,handoff,workflow` 다. caller 가 `--memory-query-tokens` 를 넘긴
    사례는 0건. 그 결과 cue 1단계에서 항상 같은 entry
    (`MEM-2026-07-09-001`, 2026-07-09 audit snapshot) 가 잡히고, 나머지
    6 entries 는 33일간 **한 번도 조회되지 않았다**.
  - Phase 13 AC 지표였던 hit_rate 1.0 은 참이지만, **같은 질의가 같은 1건을
    돌려받는 시스템의 hit_rate 1.0 은 검색 품질이 아니라 캐시 적중이다.**
    지표가 질의 다양성을 재지 않으면 1.0 은 공허하다 — north-star 재정의
    (2026-07-22) 가 지적한 "항상 green 인 지표는 판정식이 나쁜 것" 의 완전한
    대칭이다 (항상 red 든 항상 green 이든, 변하지 않는 지표는 정보가 없다).
- **v0.15.21 자동 활성 평가**: ✅ 목적 (telemetry 다양성 확보) 은 달성했고
  zero-risk skip 설계로 사고 0건. 단, 자동 활성이 **default query 고정** 과
  결합하면서 위의 균질화를 만들었다 — 자동화가 사용량을 늘렸지만 사용의
  *다양성* 은 늘리지 못했다.

### (보강) write-path — placeholder 가 묻지 않은 것

placeholder 의 4 metric 은 전부 **읽기** 를 물었다. 실측이 드러낸 진짜 병목은
**쓰기** 다: entries 7건은 전부 2026-07-09 하루에 audit 산출물로 일괄 적재된
것이고, 이후 33일간 신규 0건. 같은 기간 이 저장소의 실제 "기억할 것" 은
폭발적으로 늘었다 (federation, cmd_release 정상화, TST-WF-01 재설계, title
drift 캘리브레이션, ... — handoff / 세션 기록 / agent memory / wiki 가 그걸
담았다). 즉 **memory_index 는 다른 memory 계층들과의 경쟁에서 write 유입을
확보하지 못했다.** 읽기 자동화 (v0.15.21) 에 대응하는 쓰기 운영 루프가 없다는
것 — 이것이 ADR-005 구현이 30일 뒤에도 "7건 스냅샷 조회기" 에 머문 이유다.

### (보강) 3-layer + wiki SSOT 정합 audit (placeholder metric 4)

- 8 commit 의 파일 분포 실측: 결정 커밋 `468ec7d` = knowledge 3 file,
  구현 8 커밋 = **source only** (state / knowledge 0 file). 경계 침범 0건.
- entry 적재 (state) 는 별도 커밋 (`c966ca2`, 2026-07-09) 으로 분리됐다 —
  ADR-001 의 source / state / knowledge 분리가 release 단위에서도 유지.
- ADR-004 (wiki SSOT) 정합: v0.13.3 의 bidir-link sync 가 wiki↔memory 링크를
  기계 검증하고 있고, 본 회고 기간 중 위반 보고 0건.
- **평가: ✅ clean. ADR-001 / ADR-004 본문 갱신 불요.**

## 회고 결론

1. **아키텍처는 건강하고, 비용은 실측으로 무시 가능하다** (p50 0.18ms,
   error 0, 정합 위반 0). Phase 1~3 의 구현 품질 자체에 결함은 발견되지 않았다.
2. **그러나 시스템은 설계된 대로 "사용" 되지 않았다.** 3-tuple 중 1단계만
   발동했고, 질의는 1종, 조회되는 entry 는 1건, 신규 entry 는 0건. 검색
   계층의 정교함 (BM25, expansion, merge) 은 전부 전제 조건 (다양한 질의,
   자라는 entry 집합) 이 없어 잠들어 있다.
3. **따라서 후속 투자의 우선순위는 검색이 아니라 운영이다** — 질의를 현재
   작업 컨텍스트에서 뽑는 것, 그리고 세션이 남기는 것을 entry 로 적재하는
   루프. 검색 계층 개선 (BM25 tuning, embedding) 은 그 두 개가 살아난 뒤에만
   의미를 가진다.
4. **지표 교훈**: hit_rate 1.0 + source 다양성 4 는 AC 로서 "달성" 이었지만,
   질의 다양성 1 을 함께 보지 않으면 시스템이 살아있다는 증거가 되지 못한다.
   변하지 않는 지표는 항상 green 이어도 정보가 없다.

## 후속 작업

- **W-1 (write-path 운영 루프, 최우선)**: 세션 close 절차에 "이번 세션에서
  memory_index entry 로 승격할 것" 후보 제안 단계를 추가. 자동 적재가 아니라
  advisory 제안 (자동으로 쓰면 [노트 누적 수치와 같은 이유로] 거짓이 된다).
  ✅ **구현** (같은 날, TASK-2026-08-10-main-011): `wk suggest-memory-entries`
  — handoff §4 제목을 entry corpus 와 대조해 coverage < 0.5 인 작업을 후보로
  제안 (skeleton 포함, 무-write). 첫 실측: 최근 10 task 전부 후보 (max
  coverage 0.14) — 회고 발견의 재확인. `tests/check_memory_entry_suggestions.py`
  8 case (되주입 포함).
- **W-2 (질의 다양화)**: 3 skill 의 default query 를 고정 3-token 에서 현재
  컨텍스트 유래 token (브랜치 축, 최근 backlog 키워드 등) 으로 확장. telemetry
  에 `query_tokens` 자체(개수 아니라 내용의 해시 또는 상위 토큰)를 남겨 질의
  다양성을 측정 가능하게.
  ✅ **구현** (같은 날, TASK-2026-08-10-main-012): `derive_context_query_tokens()`
  (state.json 의 current_axis + 최근 done 제목 3건 → token 유도, 실패 시 skill
  별 기존 trio fallback + 출처 보고) 를 3 skill 공용으로. telemetry 에
  `query_tokens`/`query_source`("context"/"default"/"explicit") additive.
  실측 정밀화: 3 skill 의 고정 질의는 각자 다른 trio (`session,handoff,workflow`
  / `doc,sync,workflow` / `backlog,task,workflow`) 였고 **공통 token
  "workflow"** 가 항상 MEM-001 을 집었다. 첫 컨텍스트 질의는 정직한 miss
  (cue 0) — 그리고 그 miss 가 33일간 hit_rate=1.0 뒤에 숨어 있던 **패널 간
  반올림 불일치** (Panel 3 raw vs Panel 8 round-4) 를 즉시 드러내
  round-at-source 로 통일했다. 변하지 않는 지표는 자기 소비자의 결함도 숨긴다.
  `tests/check_context_query_tokens.py` 8 case.
- **W-3 (entry 간 링크)**: 현재 7 entries 는 서로 고아라 expansion 이 구조적으로
  발동 불가. 신규 entry 적재 시 기존 entry 참조를 권장하는 규약 (agent memory
  의 `[[name]]` 링크 관행을 이식).
- **W-4 (지표 재정의)**: hit_rate 단독 → (질의 다양성, 30일 신규 entry 수,
  조회된 distinct entry 수) 3-tuple 로. 항상 1.0 인 지표는 은퇴시킨다.
- 기각 명시: BM25+ tuning ❌ / embedding 3단계 ❌ / merge default 변경 ❌
  (전부 실측 근거 부재 — 전제가 살아난 뒤 재평가).
- 본 ADR status: `draft (placeholder)` → **`accepted` 전환 완료** (본 커밋).
- wiki topic: `ai-workflow/wiki/topics/memory-index-retrospective-2026.md`
  (본 회고의 knowledge-layer 사본, P2-1 acceptance).

## References

- ADR-005 implementation history (8 release):
  - 결정: `468ec7d docs(adr): ADR-005 Memora-inspired Memory Index 추가`
  - Phase 1 prototype: `e4c7343`
  - Phase 1.5 state.json: `4655e7c`
  - Phase 2a --merge opt-in: `d2d8a1c`
  - Phase 2b BM25 fallback: `5973146`
  - Phase 3a dispatcher entry: `7be5029`
  - Phase 3b1 session-start wiring: `73564d9`
  - Phase 3c doc-sync wiring: `c46d729`
  - Phase 3d backlog-update wiring: `2ab3b6c`
- 회고 실측 원천: `ai-workflow/memory/active/memory_index/telemetry/events.jsonl`
  (256 events, 2026-07-09 ~ 2026-08-10) + 2026-08-10 재현 실측
  (TASK-2026-08-10-main-010).
- 후속 릴리스: v0.13.1 (telemetry) / v0.13.2 (self-recover) / v0.13.3
  (bidir-link) / v0.15.21 (자동 활성) / 2026-08-09 skill stable (TASK-014).
- 평가: [`./MICROSOFT_MEMORA_EVALUATION.md`](./MICROSOFT_MEMORA_EVALUATION.md)
- 결정: [`./ADR-005-memora-inspired-memory-index.md`](./ADR-005-memora-inspired-memory-index.md)
- 3-layer 분리 정합: [`./ADR-001-source-state-knowledge-3-layer-separation.md`](./ADR-001-source-state-knowledge-3-layer-separation.md)
- wiki SSOT 정합: [`./ADR-004-llm-wiki-layer.md`](./ADR-004-llm-wiki-layer.md)
- Source-of-truth 평가: Microsoft Research Blog, "Memora: A Harmonic Memory Representation Balancing Abstraction and Specificity", 2026-06-29.
- Reference impl: github.com/microsoft/Memora (MIT).
