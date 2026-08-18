# 세션 기록 — 49차: wiki L2 파이프라인 회생 — 화석 은퇴와 파생 뷰 재정의 (2026-08-19)

- 문서 목적: 49차 세션의 작업 축과 결정을 다음 세션이 이어받을 수 있게 남긴다.
- 범위: TASK-2026-08-18-main-004 (wiki 3-step 하위 단계) 단일 task
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-19
- 관련 문서: [handoff](../session_handoff.md), [backlog](../backlog/2026-08-19.md), [L2 계약](../../../../wiki/sources/.gitkeep)

## 0. 한 줄 요약

`wk wiki-emit` 이 **3-step → 2-step** 이 됐고, 파이프라인이 **처음으로 끝까지
실행된다**. 검사 263 → 264. 이 task 의 핵심은 크래시 두 개가 아니라, **세
단계가 각각 다른 이유로 이미 유효하지 않았다**는 것이었다 — 그래서 "고쳐서
rc=0 을 만든다" 가 오답이었다.

## 1. 진단 — task 설명보다 무거웠다

격리 클론(`git clone --local`)에서 3단계를 전부 실측했다. 저장소를 오염시키지
않으려는 조치였고, 실제로 3단계는 실행만으로 워킹 트리를 바꾼다.

| 단계 | 증상 | 실제 원인 |
|---|---|---|
| 1 `--refresh-raw` | `KeyError: 'memory'` | 스키마 드리프트가 아니라 **소유권 충돌** |
| 2 `emit_wiki_l2_body` | `ValueError` | vault 시대 경로 화석 **3종** |
| 3 `--emit-l2` | `rc=0` | 2026-06-14 스냅샷 **축자 재생성** |

**1단계의 write 대상 4개가 전부 무너져 있었다.** `state.json` 은 정본 §11.2 가
생성 산출물로 확정했고 생성기는 `wk refresh-state` 하나라 이 단계는 **두 번째
writer** 였다 · `work_backlog.md` 는 v0.14.0 append-only layout 에서 사라졌다 ·
`memory/log.md` 로 가는 write 는 entry 를 만들고 **쓰지 않는 죽은 코드**였다 ·
`wiki/log.md` 갱신은 날짜(`2026-06-13`)와 릴리스(`v0.7.0~v0.7.4`)가 하드코딩이라
돌릴수록 6월로 되돌렸다.

**2단계는 화석이 셋이었고 셋 다 실행 경로 위에 있었다.** 이중 경로
(`RAW_MIRROR/<project>/ai-workflow/wiki`) · `RAW_MIRROR.parts.index("raw")` ·
그리고 **정의된 적 없는 `VAULT_ROOT`**. 앞의 둘을 고쳐도 그 다음 줄이
`NameError` 였다 — 즉 이 코드는 v0.7.17 in-repo 전환 이후 **한 번도 끝까지 실행된
적이 없다**.

## 2. 날짜가 박힌 붕괴가 예약돼 있었다

`score_lifecycle` 은 L2 stub 4개의 `last_touched` 가 30일 이내여야 점수를 준다.
값은 `2026-07-22` 였다 — 진단 시점에 27일. 즉 **2026-08-21 에 lifecycle 5.0 →
0.0, overall 4.71 A → 3.88** 이 예정돼 있었다.

그리고 그것을 갱신할 유일한 도구인 3단계는 갱신은커녕 **67일 전(`2026-06-14`)으로
되돌린다**. 7/22 라는 값은 도구가 아니라 사람이 커밋(`dcbf2af7`)으로 올린
것이었다. **지표를 살려 두는 메커니즘이 구조적으로 지표를 살릴 수 없었고, 그
간극을 사람이 30일마다 메우고 있었다.**

## 3. 결정 — 은퇴 / 수리 / 재작성 (소유자 승인)

세 단계를 같은 방식으로 다룰 수 없어 소유자에게 범위를 물었고, **화석 은퇴 +
파생 뷰 재정의**로 확정했다.

- **1단계 은퇴** — write 0. 다만 **조용한 no-op 이 아니라** 사유를 stderr 로
  말한다(rc=0). 그리고 `update_state_json` 같은 함수를 **파일에서 지웠다**:
  CLI 분기로만 막으면 다음 사람이 함수를 다시 부른다. `check_refresh_wiki_memory`
  가 그 이름들의 부재를 정적으로 고정한다.
- **2단계 수리** — 화석 3종 제거. 그런데 고쳐도 할 일이 없었다: 게이트가
  `<needs content>` placeholder **하나**라 한 번 emit 된 page 는 L1 이 아무리
  바뀌어도 영원히 대상이 아니었다. 게이트를 **신선도**(placeholder 이거나 L1 이
  L2 보다 새로움)로 바꿨다. 재emit 이 본문 *전체* 를 갈아끼우게 되므로
  `> Generated:` 표식 없는 page 는 **manual 로 보고 건드리지 않는다**.
- **3단계 재작성** — 스냅샷 재생성을 걷어내고 현재 SSOT(`state.json` / 최신
  backlog index / `session_handoff.md` / `wiki/log.md`)에서 파생한다.
  `last_touched` 는 실제 emit 일자, 결과 바이트가 같으면 write 하지 않는다
  (`unchanged`), L1 이 없는 stub 은 채우지 않고 `missing_l1` 로 밝힌다.

소유가 둘로 갈리므로 **한쪽에만 둔다**: memory 파생 stub 4종은
`refresh_wiki_memory`, L1 wiki page 파생은 `emit_wiki_l2_body`. 계약은
`ai-workflow/wiki/sources/.gitkeep` 에 적었다.

## 4. 이 세션이 남긴 규칙

- **`rc=0` 은 무해의 증거가 아니다.** 3단계는 성공 코드를 내면서 지표를
  무너뜨렸다. 종료 코드만 보는 계약은 퇴행을 통과시킨다.
- **dry-run 만 재는 검사는 apply 결함을 구조적으로 못 본다.** 이전 8 cases 는
  전부 dry 경로였고, 두 크래시는 apply 에서만 났다. 새 22 cases 는 임시 fixture
  저장소에 **실제로 쓰고 결과 파일을 읽는다**.
- **하드코딩된 날짜/버전은 도구를 스냅샷 재생성기로 만든다.** 정식화됐다고
  적혀 있어도 안이 1회용 백필이면 그건 도구가 아니다.
- **은퇴는 함수까지 지운다.** 분기만 막으면 되살아난다.
- **없는 것을 있는 것처럼 채우지 않는다** (`missing_l1`). 저장소 규칙
  *모름 ≠ 안전* 의 같은 계열.
- **생성물에 표식을 박아 둔다.** 사람 글과 파생물을 구분하지 못하면 재emit 이
  사람의 글을 지운다.

## 5. 남긴 것 — L1→L2 갭 85개 (소유자 판단 대기)

`emit_wiki_l2_body` 는 이제 동작하지만 **이 저장소에 살아 있는 입력이 없다**
(후보 0, 갭 85). 이전의 0 은 크래시와 일회성 게이트가 만든 **거짓 0** 이었고,
지금의 0 은 **측정된 0** 이다 — 도구가 "L2 파생 뷰 없는 L1 page: 85개" 를
스스로 보고한다.

`.gitkeep` 계약은 L1 wiki page 마다 L2 파생 뷰를 두라고 하지만, 그 근거였던
외부 vault retrieval 은 **v0.7.17 in-repo 전환 때 사라졌다**. in-repo 에서 L1 은
이미 검색 가능하므로 85장은 절삭 사본 ~170KB 증가일 뿐이다. 그래서
`--bootstrap-missing` 을 **기본 off** 로 두고 갭만 보고한다. 켜는 것도, 계약을
'L2 = memory 파생 4종' 으로 좁히는 것도 한 줄이면 된다.

## 6. 검증

- `check_refresh_wiki_memory` **11/11** (8 cases 재작성, apply 경로 실측)
- `check_wiki_emit_pipeline` **11/11** (신설 — 263 → 264)
- `check_v0_7_17_wiki_in_repo_isolation` 11/11 — case 2 를 문자열 grep 에서
  **해석된 경로 실측**으로 바꿨다 (resolver 로 옮기면 문자열이 사라져 헛 red 가
  나고, 정작 경로가 저장소 밖이어도 통과하던 단언이었다)
- `check_v0_7_23_wiki_cross_link` 5/5 (2-step 계약으로 갱신)
- 되주입 **6종** 전부 red 실증: `last_touched` 하드코딩 · `status: reviewed` ·
  `state.json` writer 부활 · `VAULT_ROOT` · one-shot 게이트 · 사람 글 보호 제거
- 개수 표기 3곳 263 → 264: `INSTALLATION_AND_USAGE` · `CODE_INDEX` ·
  `Beta-v1.2.0` 노트
