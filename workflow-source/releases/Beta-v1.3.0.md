# Beta v1.3.0 (2026-08-20)

> **상태: 릴리스 준비.** package `1.3.0`, runtime `__version__ = 1.3.0`, tag `v1.3.0`.
> (tag 에서 `-beta` 접미사가 빠진 첫 릴리스다 — `docs/RELEASE.md` §2.2 의 규약이
> v1.2.1 부터 `v<X>.<Y>.<Z>` 로 정리됐고, 직전 `v1.2.0-beta` 가 옛 표기의 마지막이다.)
> **minor release** — 32~51차 세션 묶음. 축 셋을 닫았다: **배포 일관성·멱등성
> gap 4개 전부** · **wiki L2 파이프라인 회생과 계약 축소** · **OKF v0.2 이행**.
>
> `feat(okf)!` 커밋이 있지만 **major 가 아니다.** 그 `!` 가 가리킨 것은 외부
> OKF spec 의 버전이지 우리 API 가 아니다 — 공개 시그니처 변경 0, 은퇴한
> 진입점 2종은 남아서 rc=0, 번들은 legacy 형태를 유지해 v0.1 소비자도 그대로
> 읽는다. 판단 기준은 `docs/RELEASE.md` §1.5 에 정본으로 남겼다.

## 0. 릴리스 판정

이 사이클의 공통 주제는 **"검사가 정작 재야 할 자리를 재고 있는가"** 다.
같은 모양의 결함이 반복해서 나왔고, 그 반복 자체가 이번 릴리스의 내용이다.

- **'있는가' 단언은 개수와 정체를 놓친다.** 롤오버 포인터는 *개수*, git root 는
  *어느 저장소*, Citations 는 *헤딩 레벨*, 지표는 *분모*, 진입점은 *표 전체* —
  다섯 자리에서 존재만 확인하는 단언이 결함을 통과시켰다. 이 패턴을
  `MEM-2026-08-20-001` 로 승격했다.
- **dry-run 만 재는 검사는 apply 결함을 구조적으로 못 본다.** wiki 파이프라인의
  크래시 2건이 8 cases 를 전부 통과한 이유가 그것이었다.
- **도달 불가능한 분기는 검사되지 않은 분기다.** OKF 소비자 정책의
  `older → error` 는 우리가 최신 버전인 동안 무해했고, 전제가 바뀌는 순간
  결함이 됐다.
- **모름을 통과로 세지 않는다.** `installable`, `missing_l1`, `status` 어휘 밖 값,
  버전 판정 근거 — 전부 "모른다" 를 그대로 말하게 했다.

## 1. 릴리스 요약

- 범위: `v1.2.0-beta..HEAD` (101 commit, feat 17 · fix 24 · docs 21 · chore 20)
- 검사 **263 → 264**, 전량 2축 264/264 PASS, mypy strict 197파일 0 errors
- 배포 축 gap 4개 완결 · wiki L2 축 완결 · OKF v0.2 이행 · 관찰 축 3개 실측

## 2. deliverable

### 2.1 배포 일관성·멱등성 — gap 4개 전부 닫힘 (TASK-2026-08-14-main-016·017·019, 2026-08-18-main-005)

`wk doctor` 배포 탐침이 **6절**이 됐다 (environment · preflight · project_scope ·
global_scope · drift · content_drift). 축의 원칙은 **측정과 선언의 분리**다 —
실행 파일은 `shutil.which` 로 실제로 재고, 네트워크 도달성처럼 못 잰 것은
`declared_unmeasured` 로 남긴다. `installable: true` 는 "실행 파일 전제 충족"
이지 "설치 성공" 이 아니다.

`content_drift` 는 버전이 같은데 내용만 낡은 설치본을 잡는다. **정본은 생성기와
같은 함수**(`render_agent_plugin`)이고, 기대치는 채널별 파생이다.

> 이 축에서 드러난 사각지대: **editable 설치는 배포 결함을 영원히 숨긴다.**
> `wk wiki-emit` / `rotate-workflow-logs` / `install-pre-push-hook` 셋이
> 비-editable wheel 에서만 죽고 있었다 (TASK-2026-08-18-main-003).

### 2.2 wiki L2 — 회생 후 계약 축소 (TASK-2026-08-18-main-004, 2026-08-20-main-001)

`wk wiki-emit` 이 **3-step → 1-step** 이 됐다. 세 단계가 각각 다른 이유로 이미
유효하지 않았다:

| 단계 | 처리 | 이유 |
|---|---|---|
| `--refresh-raw` | 은퇴 | `state.json` 의 **두 번째 writer** — 생성기는 `wk refresh-state` 하나다 |
| `emit_wiki_l2_body` | 은퇴 | L1 wiki page 사본의 근거였던 **외부 vault 가 v0.7.17 에 사라졌다** |
| `--emit-l2` | 재작성 | 2026-06-14 스냅샷을 축자 재생성하고 `last_touched` 를 되돌렸다 |

L2 의 정의를 **"wiki 모양이 아닌 SSOT 의 압축 뷰"** 4종으로 고정했다
(`refresh_wiki_memory.L2_STUBS` 가 정본, 지표도 그 상수를 import 한다).

날짜가 박힌 붕괴 하나를 막았다 — L2 4장의 `last_touched` 가 `2026-07-22` 라
**2026-08-21 에 lifecycle 5.0 → 0.0** 이 예약돼 있었고, 갱신할 유일한 도구가
67일 전으로 되돌리고 있었다.

**은퇴 형태**가 이 릴리스의 관례가 됐다: 진입점은 남기고 **write 0 + 사유 보고**
(rc=0), 옛 인자도 계속 받는다, 그리고 **기계는 파일에서 지운다** — 분기로만
막으면 다음 사람이 다시 부른다.

### 2.3 OKF v0.2 이행 (ADR-026, TASK-2026-08-20-main-003)

SPEC §13 이 breaking 2건에 **소비자 fallback 을 모두 명시**하므로, legacy 형태를
남긴 채 정규 필드를 더하면 한 번들이 v0.1·v0.2 소비자를 다 만족한다.

- **`status` 어휘 매핑** — v0.2 에서 정규 필드로 승격돼 §11 의 관용 보장(unknown
  key 한정) 밖이 됐다. `stable` 필터를 건 소비자는 71장 중 69장을 조용히 버린다.
  `active`/`accepted`→`stable`, `proposed`/`draft`→`draft`, 원문은 `wiki_status`.
  **생략도 답이 아니다** — §5.4 의 `Absent status ⇒ stable` 때문이다.
- **`sources` emit** — in-repo 출처가 처음으로 본문 산문이 아니라 기계 판독
  필드에 들어갔다.
- **`generated` 는 안 낸다** — `by` 가 REQUIRED 인데 페이지별 actor 기록이 없다.
  지어내면 §5.3 trust tier 를 부풀리는 거짓말이 된다.
- **소비자가 v0.1 을 거부하던 결함 수리** — `older → error` 분기가 v0.2 로 올리는
  순간 살아나 실측된 상호운용(openwiki)을 끊을 뻔했다.

### 2.4 관찰 축 3개 실측 (TASK-2026-08-13-main-004, 2026-08-20-main-004·005)

- **mypy flake** — 원인 계열 확정: race 가 아니라 **mypy INTERNAL ERROR**.
  4번 터지도록 못 좁힌 이유는 **증거가 로그까지 못 온 것**이었다(요약 120자 +
  excerpt 400자 절단). 셋 다 넓히고 **신호를 앞으로** 정렬했다.
- **memory_index 3-tuple** — 저점 고착의 원인은 검색이 아니라 **배선**이었다.
  종료 절차 `wk suggest-memory-entries` 가 에이전트가 읽는 문서 체인 밖이라
  한 번도 안 돌았다. 정본 §8.1·§11.1 에 넣었다.
- **cross-host federation** — 두 번째 호스트가 없어 원리적으로 못 잰다. 대기.

### 2.5 도구 결함 수리

- **linter 의 3자 대조 출처** — `state.json` 은 `backlog/tasks/` 전체를 집계하는데
  linter 는 하루치 index 하나를 봤다. 날짜가 바뀔 때마다 구조적으로 어긋났고
  2세션 연속 사람이 손으로 이월해 풀었다 (TASK-2026-08-20-main-002).
- **`next_version` 이 커밋을 안 읽었다** — `unreleased=101` 옆에서 `patch+1` 을
  내놓고 있었다. 이제 유형에서 파생하고 근거를 동봉한다
  (TASK-2026-08-20-main-006).
- **`rollover-baselines` 포인터 누적** · **backlog-update 날짜 롤오버 이월** ·
  **`check_deprecation_3rd_cycle` 죽은 제외 목록** · **정본 §11.2 다중 줄 bullet
  절단**.

## 3. smoke 회귀

누적 smoke test **267/267 PASS** ×2축 (2026-08-24, `dev,release,mcp-sdk` extra 를
깐 격리 venv, `--tmp-dir` 실디스크). 이 줄은 릴리스 시점 스냅샷이 아니라 *최신
전량 결과* 를 반영하는 살아있는 지표다.

- 컨텍스트 2축: `native` / `slash`, mypy strict 197파일 0 errors
- 되주입 실증: 이 사이클에서 신규·개정 case 마다 원 결함 형태로 되주입해
  red 를 확인했다 (wiki 6종 · OKF 6종 · linter 3종 · 지표 3종 · 릴리스 3종)

## 4. 1차 출처 (cross-ref)

- [ADR-026 OKF v0.2 이행](../../ai-workflow/wiki/decisions/adr-026-okf-v02-migration.md)
- [OKF SPEC v0.2](https://raw.githubusercontent.com/GoogleCloudPlatform/knowledge-catalog/main/okf/SPEC.md) (§5 · §11 · §12 · §13)
- [배포 일관성·멱등성 컨셉](../core/workflow_deployment_idempotency.md)
- [L2 계약](../../ai-workflow/wiki/sources/.gitkeep)
- [릴리스 등급 판단 기준](../../docs/RELEASE.md) §1.5

## 5. 후속

- **[TASK-2026-08-14-main-009]** task SSOT 라벨 영어 전환 — 이 릴리스 경계가 푼다
- **mypy flake** — 다음 재발이 트레이스백을 남기면 상류 보고/우회 판단
- **memory_index 3-tuple** — 종료 절차가 문서에 실렸으니 30일 뒤 재측정
- **cross-host federation** — 두 번째 호스트(MacBook) 확보 시점

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-08-20T03:32:38Z)_

- total wiki pages: **94**
- total memory entries: **10**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
