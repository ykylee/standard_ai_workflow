# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-07-29
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: v1.0.0-beta + `origin/main` = `71feef3` (CI smoke·mypy-strict green 실측, mcp 1.29.0)
- 현재 주 작업 축: 상한 없는 의존성은 측정을 조용히 갈아 끼운다 — 핀은 시한을 미룰 뿐이고, 이관과 탐지층이 닫는다
- 최근 핵심 기준 문서:
  - [global_workflow_standard.md](../../../core/global_workflow_standard.md)
  - [Beta-v1.0.0.md §2.38~§2.41](../../../../workflow-source/releases/Beta-v1.0.0.md)
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
- TASK-2026-07-29-main-001 mcp 2.0.0 이관 — fastmcp.FastMCP → mcpserver.MCPServer
## 5. 다음 세션 시작 포인트

**의존성 드리프트로 `mypy-strict` 가 red 로 넘어갔다 — 상한 핀으로 되돌리고 원인 2건을
task 로 등록한 상태다.** 문서 2줄만 바꾼 `23874d1` 에서 mypy-strict 가 실패했는데, 커밋
내용과 무관했다. CI 설치 로그에 **`mcp-2.0.0`** 이 찍혀 있고 (extra 가 `mcp[cli]>=1.0` 로
상한이 없었다) 같은 소스에 버전만 갈아 끼워 재현했다 — `1.28.1` green / `2.0.0` 에서
`mcp_v1_server.py:27 no-any-return`.

**에러 메시지가 원인에서 한 칸 떨어진 곳을 가리키고 있었다.** 실제 사실은 mcp 2.0.0 이
`mcp.server.fastmcp` 모듈 자체를 없애고 `mcp.server.mcpserver.MCPServer` 로 옮긴 것이다
(2.0.0 의 `mcp.server` 하위 모듈 목록 실측). 즉 타입 문제가 아니라 `HAS_FASTMCP=False` →
`sys.exit(1)` 인 **런타임 파손**인데, `pyproject.toml` 의 `ignore_missing_imports = true` 가
사라진 모듈을 error 가 아니라 `Any` 로 바꿔 놓아 27번 줄에서야 표면화됐다.

1차 조치는 상한 핀이었고(red 를 켜 둔 채로는 다음 커밋의 신호를 읽을 수 없어서지, 그것이
해결이어서가 아니다), **이후 TASK-2026-07-29-main-001 로 이관을 마치고 핀을 해제했다** —
세부는 릴리스 노트 §2.41. wrapper 가 2.x → 1.x 순으로 두 이름을 시도하고 어느 쪽을
잡았는지 `MCP_SERVER_SOURCE` 로 남긴다. `1.27.0`/`1.28.1`/`1.29.0`/`2.0.0` 네 버전에서
mypy strict 119 files 0 errors + 런타임(실제 서버 2종 tool 등록까지)을 각각 실측했다.

- 기준선을 `71feef3` 으로 옮겼다. smoke(7m40s)·mypy-strict 둘 다 success 실측이고,
  설치 로그에서 러너가 실제로 집은 버전이 `mcp-1.29.0` 임을 확인했다 — 핀이 상한을
  걸고 있다는 것을 선언이 아니라 로그로 확인한 것이다. `mkdocs` 는 이번 변경 경로가
  path 필터에 안 걸려 미실행.
- 확인 방법: `gh run list --commit $(git rev-parse HEAD)` (**full SHA 필수** — short SHA 는
  조용히 0건을 낸다). smoke 는 러너에서 약 8분 걸리므로 push 직후 조회는 `in_progress` 다.
- smoke 가 이 드리프트에 안 걸린 것은 설계가 아니라 **설치 순서 덕**이다 —
  `requirements-dev.txt` 의 `mcp[cli]==1.27.0` 이 뒤에 깔리며 되돌려 놓는다. mypy-strict
  job 은 그 파일을 안 깔아서 그대로 맞았다.

앞 세션(TASK-2026-07-28-main-003)은 §2.39 후속의 이관 파서 결함을 닫았다 — 세부는 릴리스
노트 §2.40. 구분 heading(`### Historical archives`)을 몰라서 그 줄이 직전 entry 의 body 로
흘러들고(실측 `TASK-2026-06-05-001`) 아래 entry 들의 소속이 소실되고 있었다.

- [x] ~~TASK-2026-07-29-main-001 — mcp 2.0.0 이관~~ → **완료(§2.41)**. `.tool()` 은 두
      SDK 모두 "함수를 그대로 돌려주는 decorator" 라 wrapper 계약(`Callable[..., Any]`)이
      유효함을 확인했고, `cast` 로 좁혀 반환한다. **1.x 지원은 끊지 않았다** — 두 이름을
      모두 시도한다. 상한 핀 해제 완료.
      - `version` 은 계속 전달하지 않는다. 2.x `MCPServer` 는 받지만 1.x `FastMCP` 는
        받지 않고, 여기서 넘기기 시작하면 서버 2종이 광고하는 version 이 바뀐다 —
        이관 범위 밖이라 기존 동작을 유지했다. 바꾸려면 별도 결정이 필요하다.
- [ ] **TASK-2026-07-29-main-002 — `ignore_missing_imports` 탐지 구멍.** 선언한 optional
      dep 의 import 가 실제로 되는지 판정하는 층이 없다. 되주입했을 때 `no-any-return` 이
      아니라 "모듈 없음" 으로 실패해야 한다. `mcp.*` 만 override 에서 빼면 SDK 미설치
      로컬이 red 가 되므로 판정 기준을 먼저 정할 것.
- [ ] **`state.json` 의 `backlog.task_count` 는 항상 0, `latest_backlog_path` 는 항상
      `null` 이다.** 이번에 `--latest-backlog-path` 를 넘겨 재생성해도 그대로였다 (task 파일
      107건 존재). 이번 변경으로 생긴 것이 아니라 그 전부터 그랬다 — 관측만 해 둔다.
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
