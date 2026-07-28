# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-07-28
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: v1.0.0-beta + `origin/main` = `0206ac3` (CI smoke·mypy-strict green 실측)
- 현재 주 작업 축: 판정과 근거는 다른 칸에 — 근거를 버리지도, 없는 판정을 채우지도 않는다
- 최근 핵심 기준 문서:
  - [global_workflow_standard.md](../../../core/global_workflow_standard.md)
  - [Beta-v1.0.0.md §2.38~§2.40](../../../../workflow-source/releases/Beta-v1.0.0.md)
  - [MEMORY_GOVERNANCE.md "두 축을 섞지 않는다"](../../../../workflow-source/MEMORY_GOVERNANCE.md)

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
-
## 3. 차단 작업

- 현재 `blocked` 작업:
-
## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-07-25-main-001 선언과 사실을 맞춘다 (Pages / mypy strict / YAML·스킬·MCP 검사층)
- TASK-2026-07-27-main-001 진입점 규칙 단일 출처화 + 자기 적용을 검사로 고정
- TASK-2026-07-27-main-002 남은 결함 3건 + CI 자기참조 해소
- TASK-2026-07-27-main-003 남은 자기참조 3건 해소 + CI red 원인 계측 확정
- TASK-2026-07-27-main-004 backlog-update 결함 4건 + 정본 검사 구멍
- TASK-2026-07-28-main-001 recent_done_items 가 최신을 고른 적이 없었다 — 상한·정렬·완료 판정
- TASK-2026-07-28-main-002 status 칸에 출처를 적고 있었다 — 진행 상태 축과 출처 축의 분리
- TASK-2026-07-28-main-003 구분 heading 을 몰라서 두 가지를 동시에 잃고 있었다 — 이관 파서
## 5. 다음 세션 시작 포인트

TASK-2026-07-28-main-003 으로 종료했다. §2.39 후속으로 관측한 이관 파서 결함을 닫았다 —
세부는 릴리스 노트 §2.40. 구분 heading(`### Historical archives`)을 몰라서 **그 줄이 직전
entry 의 body 로 흘러들고**(실측 `TASK-2026-06-05-001`) **아래 entry 들의 소속이 소실**되고
있었다. 소속 소실이 §2.39 후속의 판정 비용을 만든 원인이었다.
**CI 는 green 이다** (`0206ac3` 에서 smoke·mypy-strict success 실측. `mkdocs` 는 해당 커밋의
변경 경로가 path 필터에 안 걸려 미실행 — 그 앞 `5be5ba4` 에서 green).
확인 방법: `gh run list --commit $(git rev-parse HEAD)` (**full SHA 필수** — short SHA 는
조용히 0건을 낸다). smoke 는 러너에서 약 8분 걸리므로 push 직후 조회는 `in_progress` 다.

- [x] ~~판정 근거가 없어 비워 둔 2건~~ → **둘 다 `done` 으로 판정 완료**.
      `archived/{codex/phase6,gemini/phase10}/` 의 handoff·day file 을 대조해 근거를 찾았다
      (task 파일 Outcome 에 근거 기록). `unknown_status_items` 는 이제 빈 목록이다.
- [x] ~~이관 도구가 비-task section 도 task 로 만든다~~ → **§2.40 에서 조치**. 파서가 구분
      heading 을 인식해 직전 entry 를 닫고, 소속을 `source_group:` 으로 보존하며, 이관
      summary 에 "확인 필요" 로 노출한다. **"아카이브 포인터면 task 가 아니다" 는 판정은
      도구가 하지 않는다** — 프로젝트 결정이라 드러내기만 한다.
- [ ] **아카이브 포인터 2건을 task 로 둘지는 미결.** 현재는 `source_group: Historical archives`
      가 붙은 채 `done` 으로 남아 있다. 정리(삭제/이동)할지는 프로젝트 결정.
- [ ] **`recent_done_items` 는 여전히 파생물이고 10개 상한이다.** 손으로 쓴 긴 서술은 다음
      `backlog-update` 실행에서 task SSOT 의 제목으로 재생성된다 — 상세의 집은 task SSOT 와
      릴리스 노트다. (정렬은 §2.38 에서 최신순으로 고쳤다. 상한 자체는 유지.)
- [ ] **daily index 의 "`status` 줄이 없으면 done" fallback 은 남아 있다**(builder §2 구간).
      task 파일이 있으면 그것이 SSOT 라 이 저장소에서는 발현하지 않지만(104건 전부 task 파일
      보유), *구형 index 만 있는 legacy 저장소* 에서는 여전히 추측이다. task 쪽은 §2.39 에서
      닫았고 이쪽은 호환 때문에 남겼다.
- [ ] **dashboard Panel 5 (`collect_recent_releases`)는 브랜치 간 정렬 키가 없다.** 브랜치별
      `state.json` 을 이어 붙인 뒤 앞에서 자른다 — 브랜치 *안* 은 이제 최신순이지만 브랜치
      *간* 은 여전히 concat 순서다 (항목 문자열에 날짜가 없다).
- [ ] 슬래시(`/`) 가 들어간 브랜치에서 `check_branch_scoped_memory` 와
      `check_self_application` 이 깨진다 (probe 브랜치에서 실측). main 에서는 안 드러난다.
- [ ] 스케줄 workflow 2건 여전히 red — `consumer-metrics-digest` (issue 게시 스텝),
      `okf-validate` (V-R10 online URL 검증). 이번 작업과 무관한 별건.
- [ ] `active/<branch>/` 로 바뀐 bootstrap layout 을 실제 소비자 프로젝트에 적용해 볼 것
      (기존 평면 프로젝트는 유지되지만, 옮기려면 `tools/migrate_memory_to_branch_scoped.py`)

## 6. 남은 리스크 / 확인하지 못한 것

- **이번 세션의 교훈(§2.40)**: §2.39 는 "판정 근거가 없으면 채우지 말라" 였는데, 이건 그 앞
  단계다 — **판정 근거를 애초에 버리지 말 것.** 아카이브 포인터인지 작업 항목인지 구분할
  단서는 구분 heading 하나뿐이었고, 이관이 그걸 버려서 판정 자체가 불가능해졌다.
  **이관은 형식을 바꾸는 일이지 사실을 줄이는 일이 아니다.**
- **이번 세션의 교훈(§2.39)**: 어휘가 모자라 보일 때 **먼저 의심할 것은 축이 섞였는지**다.
  `recorded` 는 다섯 번째 진행 상태가 아니라 *출처* 였다. 어휘를 늘렸다면 정본과 소비자
  validator 를 다 깨면서도 축 혼재는 그대로 남았을 것이다.
- **이번 세션에서 발견(§2.39)**: §2.38 이 만든 `unknown_status_items` 는 **payload 까지 오지
  않고 aggregate 안에만 있었다**. 테스트에서만 보이고 `state.json` 을 읽는 사람에게는 안
  보였다 — 노출을 만들었으면 **소비자가 실제로 보는 자리까지 왔는지** 확인할 것.
- **이전 세션의 교훈(§2.38)**: 증상은 "정렬이 시간순이 아니다" 한 줄이었는데, 열어 보니
  **정렬 키라는 것이 애초에 없었다**. 상한 `10` 이 두 곳에 있었고 자르는 방향이 반대라
  서로를 무효화했고, 완료 판정이 task 파일과 daily index 두 곳에 있어 파생물이 SSOT 를
  덮어썼다. **셋 다 각자의 자리에서는 말이 됐다** — §2.24/§2.37 과 같은 모양이다.
- **확인 못 함(§2.38)**: `_task_recency_key` 는 완료일이 아니라 **등록일 근사**다. 완료 시각
  필드가 표준이 아니라서, `completed_at`/`updated_at` 을 먼저 보게 해 두고 `created_at` 으로
  떨어진다. 같은 날 여러 건이 서로 다른 날 완료된 경우는 구분하지 못한다.
- **이전 세션의 교훈**: §2.35 (6) 에서 **관측하지 않은 값을 관측한 것처럼 적었다**. CI 의
  실패 사유가 어디에도 안 남아 있는 상태에서 로컬 출력을 CI 의 것으로 서술했고, 그래서
  원인을 mypy 로 잘못 지목했다. 실제 원인은 `gh` 인증 부재였다(§2.36). 처방이 맞았던 건
  운이다. **로컬 재현의 출력과 CI 의 출력은 다른 증거다.**
- **`gh` 인증 유무는 verdict 를 바꾸는 1급 환경 변수다** — CI 에서는 `skipped`, 로컬에서는
  `ci_sanity`/`ci_stale`. verdict 를 보는 검사는 전부 집합 검사 + 주입 검증이어야 한다.
- **도구 산출물은 diff 로 검토한다**(§2.37). stable 로 선언된 skill 이 상태 문서를 파괴하고
  있었고, `status: ok` 를 냈다. 발견 계기는 결과를 믿지 않고 `git diff` 를 읽은 것 하나다.
  close-out 에서 `backlog-update --apply` 를 쓴 뒤에는 반드시 diff 를 확인할 것.
- **확인 못 함**: 새로 생성한 진입점을 실제 에이전트 세션에서 로드해 보지는 않았다.
  파일 내용과 bootstrap 산출물, `check_self_application.py` 까지만 검증했다.
- **확인 못 함**: branch-scoped bootstrap 을 *기존 소비자 프로젝트* 에 재실행해 본 적은
  없다. 평면 layout 보존 분기는 temp fixture 로만 확인했다.
- **주요 제약**: 발표자료(`docs/presentations/`)의 11·12·15·22번 주장이 이제 사실이다.
  덱의 원리는 `core/workflow_design_principles.md` 가 정본이다.
