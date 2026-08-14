# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-14 (36차 세션 종료 — PR #25 병합, 브랜치 메모리 생애주기)
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: **44차 세션 종료 — task SSOT 3단계 완료, main-008 close (`feat/task-label-registry` 병합).** 라벨은 장식이 아니라 **파싱 계약**이라 순서가 정해져 있다: **리더가 먼저 두 표기를 받고, 그 다음 release 에서 쓰는 쪽을 바꾼다**. 반대로 하면 소비자의 옛 리더가 새 문서를 못 읽는다 — 그래서 이번 단계는 전환을 **하지 않았다**. 리터럴 12개 라벨 × **46곳**을 `TASK_FIELD_LABELS`(현재 표기) + `TASK_FIELD_ALIASES`(받아들일 표기)로 모았다. 원칙은 **찾기는 넓게, 쓰기는 좁게**. `check_task_label_registry` 8 cases — **case 6 이 '정본이 하나' 의 유일한 증거**(표를 바꾸면 산출물이 따라 바뀐다)이고, case 8 은 반대로 렌더 경로의 잔여 리터럴을 AST 로 훑어 세 번에 걸쳐 지목했다. 마지막 하나는 **읽는 비교**였다 — 영어 표기 문서에서 항상 거짓이라 '비어 있으니 채운다' 분기가 조용히 안 돌았다. **main-008 은 done**: 결함 6계열 중 **3개가 구조적으로 닫혔다**(status 혼동 · 반복 필드 소실 · update 줄 중복). 4단계(영어 전환)는 [TASK-2026-08-14-main-009] 로 이월 — release 경계여야 한다. **검증**: 전량 2축 **260/260 ×2 green**. 상세: [세션 기록](../../archived/feat/task-label-registry/sessions/task_label_registry_2026-08-14.md).
- 직전 기준선: **43차 세션 종료 — task SSOT 2단계: 쓰는 쪽 (`feat/task-ssot-writer` 병합).** **소실과 중복은 같은 뿌리였다** — 열거형 필드를 스칼라로 다뤘다. `--done-criteria` 를 5번 줘도 마지막 하나만 남았고(소실), 그걸 피하려 값 안에 개행을 넣으면 `_set_inline_field` 가 첫 줄만 교체해 2번째 이후가 남았다(중복). **우회책이 두 번째 결함을 만들었다** — 스칼라 API 를 목록처럼 쓰면 값 안에 구조를 넣게 되고, 그 구조는 읽는 쪽이 모른다. 처방도 하나: 네 필드(`완료 기준`/`작업 결과`/`남은 리스크`/`후속 작업`)를 `action="append"` 로 + **연속한 라벨 줄을 묶음으로 교체**(`_set_list_field`, 다른 절의 같은 라벨은 안 건드린다) + update 는 `list_updates` 로 분리, **멱등이 계약**. `check_task_multivalue_fields` 9 cases, **되주입 2종이 원래 증상을 그대로 재현**했다 (append 제거 → 마지막 하나만 / 묶음을 첫 줄만 → 중복 누적). **검증**: 전량 2축 **259/259 ×2 green**. 상세: [세션 기록](../../archived/feat/task-ssot-writer/sessions/task_ssot_writer_2026-08-14.md).
- 그 이전 기준선: **42차 세션 종료 — task SSOT 구조화 1단계 (TASK-2026-08-14-main-008 진행 중, `feat/task-ssot-structured` 병합).** 완료 기준의 첫 항목이 '읽는 자리 전수 조사' 였는데 **조사가 살아 있는 결함 셋을 찾았다**. ①**같은 필드에 소스가 둘** — 아카이브/축분리 검사는 frontmatter `status:`, backlog 파서는 본문 `- 상태:`. 277개 중 불일치는 0인데 **본문 줄이 없는 것이 105개(38%)** 였고 그것들은 파서에게 *상태 없음* 이라 어느 목록에도 안 들어갔다 → frontmatter 우선 (디스크 본문은 안 건드린다 — 소비자 리더 호환). ②**index 방언 셋 중 둘이 안 보였다**(링크/백틱/인라인) — `active/main` 의 daily index **20개가 task 를 0개로** 읽고 있었다. 파일은 있는데 어느 집계에도 없다. ③**fallback 이 두 겹으로 죽어 있었다** — glob 패턴이 실제 파일명을 안 잡았고 그 전에 생성자가 부재 파일에서 먼저 죽어 도달조차 못 했다. **결과: 0개 index 20→0, 읽힌 task 262, 상태 없는 task 0. `state.json` 산출은 전후 동일**(최신 backlog 는 이미 신형이라 회귀 없이 과거 커버리지만 증가). `check_task_ssot_source` 10 cases + 되주입 2종 — **되주입이 case 하나를 무력화 상태로 드러냈다**(백틱 해석을 지워도 case 5 가 glob fallback 으로 통과). 격리하니 fixture 디렉터리가 실물과 달라 실패 → 실물 모양으로 수정, **오늘 같은 실수 두 번째**. **검증**: 전량 2축 **258/258 ×2 green**. 상세: [세션 기록](../../archived/feat/task-ssot-structured/sessions/task_ssot_structured_2026-08-14.md).
- 그 이전 기준선: **41차 세션 종료 — handoff 기준선 롤오프 (TASK-2026-08-14-main-007, `perf/handoff-baseline-rolloff` 병합).** handoff **26,582 → 10,789 tok (−59%)**, 세션 시작 read set 약 36K → **21,076 tok**. **자르지 않고 이관한다** — 완료 목록은 SSOT 가 `backlog/tasks/` 에 있어 넘치면 버려도 되지만 기준선 산문은 **어디에도 없다**. 그래서 `BASELINE_ITEMS_CAP=4` 와 함께 `baselines.md` 이관을 만들었고, 검사의 중심 case 도 '줄었는가' 가 아니라 **'옮겨졌는가'** 다. `wk rollover-baselines` + `check_handoff_baseline_cap` 11 cases + 린터 `handoff_baseline_bloat`(fix_suggestion 이 도구를 가리킨다 — '지워라' 라고 적으면 사람이 지운다) + 정본 §11.1 에 명령 한 줄. **세 가지가 드러났다**: ①**fixture 가 실물을 안 닮아 결함이 실물에서만 났다** — 한 줄짜리 기준선만 재던 구현이 첫 줄만 옮겨 하위 불릿을 §1 에 고아로 남겼다(블록 단위로 수정 + case 11) ②**되주입이 검사 자신의 결함을 드러냈다** — 이관을 생략하자 case 3 이 예외로 죽으며 case 4~10 이 아예 안 돌았다(`AssertionError` 만 잡고 있었다) ③**§11.1 에 행을 늘리자 위치 가정이 깨졌다** — `check_agent_plugin_payload` 가 표의 **마지막 행**을 재생성 명령으로 보고 있었다 → 목적 기반 조회로 교체. **검증**: 전량 2축 **257/257 ×2 green** + 되주입 2종. 상세: [세션 기록](../../archived/perf/handoff-baseline-rolloff/sessions/handoff_baseline_rolloff_2026-08-14.md).
- 그 이전 기준선은 [`baselines.md`](./baselines.md) 에 있다 (이관 1건, 최신이 위).
- 그 이전 기준선은 [`baselines.md`](./baselines.md) 에 있다 (이관 1건, 최신이 위).
- 그 이전 기준선은 [`baselines.md`](./baselines.md) 에 있다 (이관 1건, 최신이 위).
- 그 이전 기준선은 [`baselines.md`](./baselines.md) 에 있다 (이관 1건, 최신이 위).
- 그 이전 기준선은 [`baselines.md`](./baselines.md) 에 있다 (이관 33건, 최신이 위).

- 현재 주 작업 축: **문서 개편 3축이 전부 닫혔다 — 다음 축을 정하는 자리다.** ①영어화(진입점·스킬) ②handoff 롤오프(−59%) ③task SSOT 구조화(1~3단계) 완료. **대기 축** (release 경계 / 관찰 / 판단 보류로 나뉜다): **release 경계** — [TASK-2026-08-14-main-009] 라벨 영어 전환(리더가 두 표기를 아는 버전이 배포된 뒤). **남은 구조 결함** — [main-005] seed 의 `sessions/` gap / [main-006] 아카이브의 살아있는-대상 링크 재작성(**오늘 세 번 밟았다**) / 정숙 구간 `no_repo_write` 39s. **판단 보류** — [main-004] 2축→1축 조건부(15연속 CI red 를 만든 비대칭이라, 위험이 절감보다 크면 **안 하는 것도 결론**). **관찰** — [TASK-2026-08-13-main-004] mypy flake 33 run 연속 green(현재 5) / macOS PEP 668 / cross-host federation / darwin mavis e2e / memory_index 3-tuple 추이.
- ~~소유자 결정 대기: state.json 생성물 여부~~ — ✅ **해소** (TASK-018, 2026-08-11): **생성물로 확정.** 정본 §11.2 에 선언, `wk refresh-state` 로 재생성, `check_state_json_generated` case 5 가 이 저장소의 정합을 상시 검사. 상세 요약·산문은 state.json 이 아니라 handoff §4 와 task 파일(SSOT)에 남긴다.
- 다음 후보 축: ~~PyPI 발행~~ → ⛔ **닫힘 (2026-08-14 소유자 최종 결정 = 발행 안 함, `RELEASE.md` §1 각주 0)** / cross-host federation (두 번째 호스트 = **MacBook 확정, 시점 추후**) / memory_index 3-tuple 지표 추이 관찰. ~~federation self-host add~~ ✅ (14차) · ~~v1.1.9/v1.2.0 미발행 누적~~ ✅ **해소 (32차 — v1.2.0-beta 발행, 누적분 0)**. (v1.1.0·v1.1.1 노트 누적 표기는 TASK-014 에서 **미삽입 확정**, branch protection 은 소유자가 **보류 결정** (2026-08-11) — 둘 다 후보 축에서 제거.)
- 발견한 cross-project 패턴 (agent memory 추가):
  - **Federation pattern** (4 후보 검토: central ❌ / git ❌ / S3 ❌ / federation ✅)
  - **MCP/CLI dual mode** (operational tool 의 4종 wrapper)
  - **3-layer defense** (규약 + client hook + server protection)
  - **Scope drift detection** (3-way enum: planned_done / planned_undone / unplanned_done)
  - **time.mktime → calendar.timegm** (UTC timestamp KST 환경 함정)
  - **[project.scripts] entry points** (CLI 化 A안, venv e2e 검증)
  - **기존 dispatcher 확장 > 새 dispatcher** (진입점이 둘로 갈리면 `--help` 도 갈린다)
  - **serving 없는 pull 은 반쪽** (API 만 있고 부를 CLI 가 없으면 기능이 없는 것과 같다)
  - **모름 ≠ 안전** (검사에서 못 읽은 필드를 통과로 치면 거짓 안심을 준다)
- 최근 핵심 기준 문서:
  - [multi_workspace_orchestration.md](../../../../workflow-source/core/multi_workspace_orchestration.md) — **§0.7 상태표 + §7.1·§7.3 구현 표시** + §0.8 *아직 열려 있는 것* 4건
  - [global_workflow_standard.md §10](../../../../workflow-source/core/global_workflow_standard.md) — 다중 작업·협업 규칙
  - [MEMORY_GOVERNANCE.md](../../../../workflow-source/MEMORY_GOVERNANCE.md)

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
- TASK-2026-08-14-main-009 task SSOT 4단계 — 본문 라벨 영어 전환 (release 경계)
## 3. 차단 작업

- 현재 `blocked` 작업:
-
## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-08-14-main-011 무거운 check 2개의 CHECK_TIMEOUT_S 미선언 — slash 축 병렬에서 TIMEOUT flake
- TASK-2026-08-14-main-004 2축 전량을 조건부 1축으로 — 브랜치 컨텍스트 민감 경로 판정
- TASK-2026-08-12-main-019 CLAUDE.md install 기본값이 macOS homebrew 에서 PEP 668 로 실패
- TASK-2026-08-14-main-005 seed 직후 sessions/ 가 비어 layout 검사가 red — '한 벌이면 green' 이 아직 참이 아니다
- TASK-2026-08-14-main-006 아카이브가 '살아 있는 대상' 상대 링크를 안 고친다 — 같은 함정 2회째
- TASK-2026-08-14-main-010 검증 결과 주입이 작업 결과 묶음을 갈라 다음 갱신에서 고아 줄을 만든다
- TASK-2026-08-14-main-008 task SSOT 를 구조화 — markdown-as-database 결함 계열 제거
- TASK-2026-08-14-main-007 handoff 기준선 롤오프 — §1 이 handoff 의 66%
- TASK-2026-08-14-main-003 변경 범위 기반 선택 실행 — run_all_checks --changed
- TASK-2026-08-13-main-009 전량 검사 시간 — 정숙 구간 직렬화가 벽시계의 36%
그 이전 완료 항목은 [3차 세션 기록](./sessions/ci_reproducibility_and_smoke_parallelization_2026-08-10.md)·[2차 세션 기록](./sessions/adr006_retrospective_and_calibration_2026-08-10.md)과 각 task 파일에 있다.

## 5. 다음 세션 시작 포인트

### 다음에 할 일 — 전량 검사 시간 (소유자 승인 2026-08-14)

"전량 검사가 매번 도는 게 진행을 더디게 한다" 는 지적에서 나왔다. 실측 결론:
**벽시계를 정하는 것은 255개가 아니라 8개다.** 그리고 **가장 큰 낭비는 도구가 아니라
사용 패턴이었다** — 이 세션에 전량 2축을 5번 돌렸는데 게이트로서 의미 있던 것은 1번뿐.

| | 1축 실측 (2026-08-14, 부하 있는 상태) |
|---|---|
| 벽시계 / CPU | 196s / 819s (255 checks) |
| 정숙 구간(직렬) | 61s — 그중 `no_repo_write` **39s (64%)** |
| 병렬 임계경로 | `wiki_score` **68s** 단독 |
| 1초 미만 | **160개** (개수는 비용이 아니다) |

- ✅ **즉시 적용**: `CLAUDE.md` 에 3단 규칙 명문화 — 편집 중 `--filter` / 커밋 전
  관련 검사 + `check_self_application` / **push 직전 1회만 2축 전량**.
- ① [TASK-2026-08-13-main-009] 무거운 8개 (임계경로 둘부터)
- ② [TASK-2026-08-14-main-003] `--changed` 선택 실행 (미선언은 항상 실행 + 스킵 출력)
- ③ [TASK-2026-08-14-main-004] 2축→1축 조건부 — **앞의 둘을 끝낸 뒤에.**
  절감은 가장 크지만 15연속 CI red 를 만든 그 비대칭이다. 안 하는 것도 결론이다.

### ⛔ 닫힌 안건 — PyPI 발행 안 함 (2026-08-14, 소유자 최종 결정)

**배포는 이 저장소의 GitHub Releases 하나로 간다.** 토큰·OIDC 운영 비용을 상시로 지는
대신 얻는 것이 지금 없고, 공개는 되돌릴 수 없는 2년 backward compat 약속을 낯선
소비자에게 지운다.

**이 안건을 다시 제안하지 않는다.** 기술 준비는 v1.2.0 에서 이미 끝나 있으므로("이제
올릴 수 있다") 제안이 계속 생길 자리다 — 그래서 결정과 함께 **재검토 트리거 3개**를
정본에 박아 두었다: [`docs/RELEASE.md` §1 **각주 0**](../../../../docs/RELEASE.md).
그 트리거(외부 사용자의 실제 요청 / 저장소 밖 배포 사유 / 소유자 지시)가 성립하기
전에는 열지 않는다.

- [TASK-2026-08-13-main-008] TestPyPI 리허설 → **취소**. 업로드는 실행되지 않았고
  앞으로도 하지 않는다. 업로드 직전까지의 실측 8종은 **이력으로 보존** — GitHub
  Releases 소비자에게도 유효한 검증이다(README 렌더링·메타데이터·이름 해석·라이선스
  동봉·진입점 등).
- `RELEASE.md` §1 의 **각주 1**(TestPyPI 1회 한정 허용, 2026-08-13)은 **만료**.
- 검토 문서 2건(`pypi-publication-policy-review` / `cli-distribution-review`)은
  **종결 표기** 후 근거 자료로만 남는다.

### 무엇이 끝났나 (2026-08-14, 37차 세션)

**브랜치 정리 — 36차 기능의 첫 자기 적용** (TASK-2026-08-14-main-001). 상세는
[세션 기록](./sessions/branch_cleanup_and_case7_false_positive_2026-08-14.md).

아래 36차의 종료 순서를 그대로 밟았고 **도구는 설계대로 동작했다**:
`origin/fix/archive-history-integrity` 삭제(고유 커밋 0, tip `f798947` 은 main 이력에 남음)
→ `wk archive-branch-memory --apply` 가 **이 handoff 의 세션 기록 링크 2건**과 아카이브된
`state.json` **5경로 전부**를 재작성했다. `.archived.json` 의 `open_task_ids` 는 `[]` 다.
`active/` 에 남은 브랜치 네임스페이스는 `main` 하나.

**종료 순서에 0번이 빠져 있었다.** 브랜치 task 가 `in_progress` 인 채였고(일은 끝났는데
파일이 안 따라왔다) 아카이브가 정당하게 막혔다. 아래 1번은 "이월" 만 말하고 **"내 일이
끝났으면 닫는다"** 를 안 말하고 있었다:

```bash
# 0) 내 브랜치 task 를 먼저 done 으로 마감한다 (완료 기준·작업 결과·검증 결과를 채워서)
#    --validation-result 가 없으면 backlog-update 가 done 을 in_progress 로 낮춘다
#    함정: --done-criteria / --result-note 는 반복해도 마지막 하나만 남는다 (append 아님)
```

**유령 ID 2건.** 이 handoff §4 와 36차 세션 기록이 가리키던
`TASK-2026-08-13-fix-…-001` 은 **존재한 적 없는 ID** 였다 (실재는 `…-08-14-…`) — 세션
기록의 `관련 문서` 링크는 태어날 때부터 죽어 있었고, §4 의 완료 기록은 어느 task 파일과도
연결되지 않았다. 호스트가 UTC 라 도구 기본 날짜는 `08-13`, 사람이 쓴 문장은 KST `08-14`
였다. 둘 다 실재 ID 로 교정.

**아카이브 직후 `check_archive_history_integrity` 가 red — 위양성이었다.** case 7 의 링크
정규식이 **자체 사본**이라 label 을 요구하지 않아(`](path "제목")` 형태), 링크 문법을
*설명하는* 산문을 링크로 오인했다. 하필 그 문서가 방금 아카이브한 세션 기록이다 —
**검사가 자기 세션의 기록을 못 견뎠다.** 문서를 고치지 않고 판정을
정본(`workflow_kit.common.markdown`)에 맞추고 사본을 걷었다. 위양성을 내는 검사는
무시당한다. case 14 를 **양방향**으로 새로 두었다 (예시 산문은 안 잡고, 진짜 깨진 링크는
잡는다) — case 7 은 살아 있는 저장소를 관찰할 뿐이라 "안 잡는" 쪽으로 무력화돼도 조용히
green 이기 때문이다. 되주입으로 실측 확인. 13 → 14 cases.

### 무엇이 끝났나 (2026-08-14, 36차 세션)

**브랜치 메모리 생애주기** (PR #25 병합). 상세는
[세션 기록](../../archived/fix/archive-history-integrity/sessions/archive_history_integrity_2026-08-13.md).

**브랜치 종료 순서** — 아카이브가 이제 미완료 task 를 막는다:

```bash
# 1) 미완료 task 를 먼저 처리한다 (이월했으면 원본에 carried_over_to: <새 ID>)
# 2) 브랜치 삭제 (아카이브는 '브랜치 부재' 를 종료 신호로 쓴다 — 역방향 점검)
git push origin --delete <branch> && git branch -D <branch>
wk archive-branch-memory --dry-run   # 막히면 어느 task 때문인지 알려준다
wk archive-branch-memory --apply     # 참조(링크·state.json)도 함께 재작성한다
```

막히면 우회하지 말고 이월한다. `archived/` 는 state 생성기도 dashboard 도 읽지
않으므로, 미완료인 채 넘어가면 그 작업은 어디에서도 안 보이게 된다.

### 무엇이 끝났나 (2026-08-13, 35차 세션)

**브랜치 메모리 네임스페이스 가드** (PR #24 병합). 상세는
[세션 기록](../../archived/fix/branch-memory-namespace-guard/sessions/branch_memory_namespace_guard_2026-08-13.md).

**브랜치를 파면 제일 먼저 이걸 돌린다** — 순서가 거꾸로면 절반짜리 네임스페이스가 되고
3검사가 red 다 (이번에 그 순서로 밟아 실측):

```bash
git checkout -b <branch>
wk seed-workspace-memory --branch <branch> --axis '<작업 축>' --task-title '<제목>' --apply
# ↑ 여기까지가 한 벌 — handoff + backlog + sessions + state.json 이 다 생긴다 (v1.2.1+)
wk backlog-update ... --mode update    # 이후 갱신
```

`wk backlog-update` 는 `backlog/` 만 만든다 (`tasks_dir.mkdir()` 의 부수효과).
`sessions/` 와 `session_handoff.md` 가 빠진다. 이제 `check_branch_memory_namespace` 가
커밋 전에 지목한다.

~~**미결로 남긴 것**: `fix/branch-memory-namespace-guard` 미아카이브~~ — ✅ **완료**
(`archived/fix/branch-memory-namespace-guard/`). 이제 `active/` 에 남은 브랜치
네임스페이스는 `main` 하나다.

### 무엇이 끝났나 (2026-08-10, 3차 세션)

**CI 재현성 회복 + smoke 병렬화** (TASK-016~019). 상세는
[세션 기록](./sessions/ci_reproducibility_and_smoke_parallelization_2026-08-10.md).
2차 세션(TASK-008~015, ADR-006 후속 + v1.1.6-beta 발행)은 §4 하단 항목 참조.

**push 전 재현 명령이 둘로 늘었다** — 둘 다 CLAUDE.md 에 적혀 있다:

```bash
# 브랜치 매트릭스 (CI 는 2축, 로컬 무인자는 1축 — 이 비대칭이 15연속 red 를 만들었다)
python3 workflow-source/tests/run_all_checks.py --branch-context=all --tmp-dir=<실디스크경로>

# SDK 매트릭스 (mcp 를 쓰는 코드를 건드렸으면)
PYTHONPATH=workflow-source python3 -m workflow_kit.common.sdk_matrix --run-local
```

전량 검사는 이제 **기본이 병렬**(`--jobs auto`)이다. 재현이 필요하면 `--jobs 1`.
저장소 전역을 관찰하는 검사를 새로 만들면 파일 안에 `REQUIRES_QUIET_REPO = True` 를
선언해야 한다 — 안 하면 병렬에서 오탐이 난다.

### 다음에 할 일 (순서)

이 세션에서 **저장소 리팩터링 조사**를 했고, 아래는 그 결과다 (근거는 §6 아래
"조사로 확정된 것" 참조). 사용자가 우선순위를 정한 항목만 실행했다 (정숙 구간 근본
수정 = TASK-019). 나머지는 미착수:

- ~~`check_mypy_strict_v0_11_3` ~ `v0_11_10` 8개 제거~~ — ✅ **완료**
  (TASK-2026-08-11-main-001, smoke 268→260).
- ~~`ai-workflow` 아카이브 정리~~ — ✅ **완료** (TASK-2026-08-11-main-003,
  185파일 제거, wiki 참조 1건 + freeze 최소 세트 6건 보존, README 링크 교정).
- ~~`check_cache_*` 13개 통합~~ — ✅ **완료** (TASK-2026-08-11-main-004,
  31 case verbatim 보존, smoke 260→248).
- ~~`release_pipeline.py` 분할~~ — ✅ **완료** (TASK-2026-08-11-main-007,
  3908→3174 + 모듈 4개, 분석 지도 방식). `dashboard_data.py` ✅ (TASK-010, 2488→1526),
  `workflow_kit_cli.py` ✅ (TASK-011, 2095→583) — **대형 파일 분할 완결**.
- ~~`docs/presentations/*.pdf|pptx` 5.2MB~~ — ✅ **완료** (TASK-2026-08-11-main-009, 파생 바이너리 제거·소스 보존).
- ~~branch protection~~ — **보류 결정** (2026-08-11, 소유자). `main` 미보호 (404 실측)
  상태를 인지한 채 일단 켜지 않기로 함. 재검토 시 `wk check-branch-protection` 으로
  현황 판정부터 (도구는 판정만 한다 — v1.1.2 §2.3).
- ~~`mooneye` 브랜치 처리~~ — ✅ **완료** (TASK-2026-08-11-main-012, `origin/mooneye`
  삭제. 고유 커밋 0 — 172 커밋 전부 main 에 존재, `active/mooneye/` 부재로
  memory 아카이브 해당 없음).

## 6. 남은 리스크 / 확인하지 못한 것

- ~~`cmd_release --apply` 실전 미검증~~ — ✅ **해소** (v1.1.4-beta 발행으로 apply
  경로 전체 실증: tag push / gh release / dashboard emit / audit append).
- **호스트 환경 의존 게이트** — 시스템 python 에는 mypy/mcp/twine 이 없어 관련 검사가
  fail 한다 (venv 에서 전부 PASS — `.venv` 에 dev,release,mcp-sdk 설치돼 있음).
  release 는 반드시 venv 에서 돌린다.
- ~~TST-WF-01 advisory red~~ — ✅ **해소** (TASK-004, 측정 재설계로 hard 복귀 +
  compliant). 남은 흔적: v0.15.18 dummy wrapper 는 측정에서 배제될 뿐 파일에
  남아 있다 — 물리 제거는 115 파일 churn 이라 별건.
- **darwin homelab 에서 mavis e2e 재확인 필요** — 검사를 정본 읽기로 바꿨으므로 mavis
  설치 호스트에서 한 번 돌려 기존과 동일하게 green 인지 확인하는 것이 안전하다.
- ~~title drift 임계 0.6 heuristic~~ — ✅ **해소** (TASK-008, 실측 캘리브레이션으로
  0.6 유지 확정 + `check_title_drift_calibration` 이 재캘리브레이션을 강제).
- ~~registry loopback 만 실측~~ — **부분 해소** (TASK-009, 비-loopback bind + pull
  왕복은 이 호스트에서 실측). **잔여**: 진짜 cross-host / 방화벽 / reverse proxy /
  TLS 종단 — 두 번째 호스트 필요 (darwin homelab).
- ~~`check_no_repo_write` 의 계약 한계~~ — ✅ **해소** (TASK-2026-08-12-main-009, 실행-중 폴링 + 원장). 이전 기술: 판정이 "실행 **후** 복원되었는가"
  라, 건드렸다 되돌리면 통과한다. `check_bidir_link_v0_13_3` 은 **이미 감시 목록에
  있었는데도** 그 이유로 안 잡혔다. 실행 *중* 감시(폴링)로 강화하면 남은 감시 대상
  다수가 같은 이유로 red 가 될 수 있어 범위가 크다. **되돌리는 것은 안 건드리는 것이
  아니다.**
- ~~amend Guard 2 의 staged-삭제 fatal~~ — ✅ **해소** (TASK-2026-08-11-main-002,
  `needs_add_only` 선별 + case 10 되주입으로 고정. §4 참조).
- **transient pyproject writer 정체 미상 (2026-08-11 1회 관측)** — 병렬 전량
  실행 중 원본 `pyproject.toml` 이 일시 변경됐다 되돌아왔다 (version_auto_sync
  byte-대조가 포착). 재현 실패 (표적 3회 + 전량 2회 + 50ms md5 watcher).
  관찰자 3검사는 정숙화(TASK-008)로 위양성 차단됨. **감시 수단은 저장소에
  고정됨** (TASK-013, `workflow-source/tools/watch_transient_writer.py` —
  일회용 `~/tmp` 스크립트의 승격판): 재발 의심 시 전량 검사 옆에 백그라운드로
  세워 두면 diff + ps 전량 + fuser 를 이벤트별로 남긴다 (로그는 temp 에만,
  저장소 안 로그는 거부). `check_watch_transient_writer` 5 case 가 되주입
  양방향으로 계약을 고정. `check_no_repo_write` 의 "실행 후 복원" 계약 한계와
  같은 뿌리로 추정 — writer 특정 자체는 재발 시의 일이다.
- **정숙 구간 6건** (TASK-008 로 3→6) — `check_no_repo_write`(전역 관찰) /
  `check_parallel_smoke`(runner 호출) / `check_source_without_runtime_layer`
  (저장소 복사) 는 본질적 직렬이고, `version_auto_sync` / `self_recovering` /
  `bidir_link` 는 원본 byte-대조 관찰 때문 (TASK-008). 병렬화로 더 줄이려면
  이들의 설계 자체를 바꿔야 한다.
- 이 밖의 과거 세션 리스크 (`--force` 3rd layer 미가동)는 변화 없음 —
  2026-08-09 까지의 세션 기록 참조.

## 7. 저장소 구성 조사 (2026-08-10 3차 세션)

리팩터링 판단 근거. git 추적 **1766 파일**:

| 영역 | 파일 | 비고 |
|---|---|---|
| `workflow-source` | 898 | tests 268, workflow_kit 129, releases 171, tools 74 |
| `ai-workflow` | 778 | **backlog tasks 193 + 아카이브 142**, wiki 81, sessions 18 |
| `docs` | 36 | presentations PDF/PPTX 가 **5.2MB** |

- **"버전 접미사 71개 = 중복" 은 틀렸다** (이 세션에서 정정). 주제별로 갈라보니
  대부분 고유하고, 진짜 중복은 `mypy_strict_v0_11_3~10` 8개뿐이다.
- 테스트가 느렸던 주된 원인은 **저장소 크기가 아니라 실행 방식**이었다 (순차 →
  병렬로 345s→118.8s). 위 정리 항목 중 실행 시간을 실제로 줄이는 것은 mypy 8개
  (15초) 뿐이고 나머지는 저장소 위생 문제다 — 섞어서 "정리하면 빨라진다" 고 말하지
  않는 편이 정확하다.

**이전 세션들의 교훈**은 각 세션 기록에 있다:
[2026-08-09](./sessions/cli_dispatcher_and_rotation_2026-08-09.md) ·
[2026-08-08](./sessions/multi_workspace_orchestration_2026-08-08.md) ·
[2026-08-05](./sessions/self_application_and_mcp_2026-08-05.md) ·
[2026-08-07 MCP](./sessions/mcp_load_verification_2026-08-07.md) ·
[2026-07-27](./sessions/selfref_cleanup_and_ci_measurement_2026-07-27.md)
