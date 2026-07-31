# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-07-31
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: v1.0.0-beta + `origin/main` = `14cd792` (§2.47 적용본, **CI 4종 green 실측** — smoke·mypy-strict·mkdocs·mcp-sdk-matrix. 러너 자기 측정으로 `All 227 check_*.py scripts passed`, 집힌 mcp `1.27.0`(smoke 정책 `pinned` 선언대로) / `2.0.0`(mypy-strict 정책 `floating`), mypy 는 `Config File: .../workflow-source/pyproject.toml` + `Success: no issues found in 121 source files`, matrix 3셀(1.27.0/1.29.0/2.0.0) 전부 success. `actionlint`/`mcp-inspector` 는 path 필터에 안 걸려 미실행. 로컬 전량 smoke 227/227, 되주입 3건)
- 현재 주 작업 축: "관대한 fallback 이 자기가 무엇을 못 했는지 말하지 않는다" — 실패하지 않는 loader 는 결함을 감추는 데도 똑같이 안전하다
- 최근 핵심 기준 문서:
  - [global_workflow_standard.md](../../../core/global_workflow_standard.md)
  - [Beta-v1.0.0.md §2.38~§2.45](../../../../workflow-source/releases/Beta-v1.0.0.md)
  - [MEMORY_GOVERNANCE.md "두 축을 섞지 않는다"](../../../../workflow-source/MEMORY_GOVERNANCE.md)

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
-
## 3. 차단 작업

- 현재 `blocked` 작업:
-
## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-07-27-main-004 backlog-update 결함 4건 + 정본 검사 구멍
- TASK-2026-07-28-main-001 recent_done_items 가 최신을 고른 적이 없었다 — 상한·정렬·완료 판정
- TASK-2026-07-28-main-002 status 칸에 출처를 적고 있었다 — 진행 상태 축과 출처 축의 분리
- TASK-2026-07-28-main-003 구분 heading 을 몰라서 두 가지를 동시에 잃고 있었다 — 이관 파서
- TASK-2026-07-29-main-001 mcp 2.0.0 이관 — fastmcp.FastMCP → mcpserver.MCPServer
- TASK-2026-07-29-main-003 read_only_mcp_sdk lowlevel 이관 — decorator → add_request_handler
- TASK-2026-07-29-main-002 ignore_missing_imports 가 사라진 optional dep 을 Any 로 덮는다 — 탐지층
- TASK-2026-07-31-main-001 mcp SDK 두 major 커버리지를 설치 순서의 우연에서 선언된 matrix 로
- TASK-2026-07-31-main-002 파생물의 상한과 포인터 — 쓰는 쪽이 규약을 모르고 있었다
- TASK-2026-07-31-main-003 기준 경로가 한 칸 어긋나 있었다 — 린터의 설정과 maturity
## 5. 다음 세션 시작 포인트

**기준 경로가 한 칸 어긋나 있었고, 그 사실을 아무도 말해 주지 않았다
(TASK-2026-07-31-main-003, §2.47).** §2.46 이 "별건" 으로 남긴 항목이다.

- `run_workflow_linter.py` 의 `project_root = project_profile_path.parent.parent.parent`
  는 `<root>/docs/PROJECT_PROFILE.md` 에서 root 가 아니라 **root 의 한 단계 위**다.
  되주입하면 fixture 에서 `project_root=/tmp` 가 나온다. 그 값이 두 곳으로 갔다.
  - `load_config(project_root)` → 없는 pyproject 를 물어 **언제나 기본값**.
    `[tool.workflow-doctor]` 의 `excluded_paths` 는 v0.7.15 도입 이래 한 번도 적용된
    적이 없다.
  - `--maturity` 의 matrix/roadmap 경로 → 늘 `skipped`. 그런데 runner 가 `issues_found`
    만 반영해서 **실행되지 못한 검사가 `status: ok / total_issues: 0`** 으로 보고됐다
    (v0.11.17 backlog 에 "정합 검증 통과" 로 기록돼 있다 — 그 기록은 사실이 아니었다).
- **둘 다 조용했던 이유는 같다.** `load_config` 는 어떤 경우에도 실패하지 않는다(운영
  안정성). 그 대가로 "설정이 적용됨" 과 "조용히 기본값으로 떨어짐" 이 산출물에서
  구별되지 않았다. `load_config_with_provenance` 가 **물어본 경로 / 얻은 파일 / 출처 /
  기본값 이유**(`file_missing`·`section_missing`·`parse_error`)를 함께 돌려주고,
  린터 산출물의 `source_context` 에 남는다. `load_config` 는 그것을 부르는 얇은 wrapper다.
- **이 저장소는 `--config-path workflow-source` 가 필요하다.** `[tool.workflow-doctor]`
  정본이 `workflow-source/pyproject.toml` 인데 workspace root 는 저장소 루트다. 사본을
  하나 더 두지 않고 **호출을 명시**하는 쪽을 택했고 `docs/PROJECT_PROFILE.md` 의 린터
  명령줄을 그 형태로 갱신했다(그 줄은 v0.5.5 릴리스 아카이브를 가리키는 죽은 명령이었다).
- 검사 1종 신규 + 1종 교체(smoke 226 → **227**): `check_linter_config_resolution.py`(9).
  그리고 `check_v0_7_15_config_thresholds.py` 의 9번째 case 를 **문자열 검사에서 동작
  검사로** 바꿨다 — 그것은 runner 본문에서 `"load_config(project_root)"` 라는 *문자열*을
  찾고 있었다. 그 줄은 내내 있었고 다만 없는 경로를 묻고 있었다.
- **고치자마자 실제 드리프트가 나왔다** (내용 정정은 범위 밖, 드러낸 채로 남긴다):
  matrix 는 `Phase 13` 을 `in_progress` 로 적는데 roadmap 은 그 단계를 현재로 말하지
  않는다(메모리상 Phase 13 은 v0.13.3 에서 완료), `task-modes` 가 stable 인데
  `test_path` 가 없다.
- 실측: 전량 smoke **227/227**(`dev,release,mcp-sdk` venv, `--tmp-dir=/var/tmp/saw-smoke`),
  mypy strict 121 files 0 errors(`Config File:` 줄로 정본 로드 확인), 되주입 3건 스팟
  체크 각각 다른 신호. **CI 4종 green 실측 완료**(`14cd792`) — §1 기준선 참조.
  `gh run view --log` 대신 `gh api repos/<o>/<r>/actions/jobs/<job_id>/logs` 로 받아
  러너의 자기 측정 줄(`All 227 …`, `Config File:`, `mcp SDK 실측`)을 직접 확인했다.
- **스모크 중에 저장소를 건드리지 말 것.** 전량 smoke 가 도는 동안 backlog index 를
  편집했더니 `check_no_repo_write` 가 red 로 나왔다. 단독 재실행하면 PASS —
  검사가 옳고 편집이 틀렸다.

---

이전 세션 기록: **close-out 마다 반복되던 수작업을 없앴다 (TASK-2026-07-31-main-002, §2.46).**
두 결함 다 같은 모양이었다 — **파생물을 만드는 쪽이 규약을 모른다.**

- **handoff §4 상한이 쓰는 쪽에 없었다.** 상한을 아는 자리가 셋(쓰는 쪽 /
  state.json 조립 / 린터)인데 값을 만드는 쪽만 몰랐다. 그래서 `--apply` 마다 11번째
  줄이 생겼고 사람이 손으로 지웠다(2026-07-28, 07-31 연속 2회). 정본을
  `common/project_docs.RECENT_DONE_ITEMS_CAP` 한 곳으로 모으고 셋이 그 이름을 읽는다.
  **이번 close-out 에서 실제로 10을 유지했다** — 가장 오래된 1건이 자동으로 빠졌다.
- **`latest_backlog_path` 가 항상 null, `task_count` 가 항상 0 이었다.** 경로 해석
  세 갈래가 `legacy_index_present` 하나에 매달려 있어서, append-only layout 에서는
  **명시한 `--latest-backlog-path` 인자까지 버려졌다**. 이제 (명시 인자 → legacy
  index → daily 디렉터리 최신) 순으로 보고, 실재할 때만 채택한다. `backlog` block 이
  통째로 죽어 있던 것이라 `task_count` 만의 문제가 아니었다.
- **죽은 필드는 소비자까지 얼려 둔다.** 살리자마자 두 건이 드러났다:
  `current_focus` 가 전부 done 인 날 **완료된 작업을 초점으로** 집었고(→ 미완료만
  고르도록), `run_workflow_linter` 가 state.json 의 상대 경로를 `branch_dir` 기준으로
  붙여 경로가 겹쳤다(→ workspace root 기준 + 실재 확인). 후자는
  `check_self_application` 이 잡았다.
- 검사 2종 신규(smoke 224 → **226**): `check_handoff_done_cap.py`(7) /
  `check_state_backlog_block.py`(8, 이 저장소 자신의 state.json 포함).
- 실측: 전량 smoke **226/226**(`dev,release,mcp-sdk` venv, 워킹트리 변경 0),
  mypy strict 121 files 0 errors, 되주입 9건 각각 다른 신호.
  **CI 4종 green 실측 완료**(`72bfbe0`) — §1 기준선 참조.

---

이전 세션 기록: **§2.43 이 남긴 "설치 순서에 기댄 우연" 을 선언으로 바꿨다 (TASK-2026-07-31-main-001,
§2.45).** 세 job 이 서로 다른 mcp 버전으로 돌고 있었는데 그렇게 정한 사람이 없었다.
smoke 의 설치 3줄을 매 줄 관측했다 — `requirements.txt` 뒤 **2.0.0**,
`requirements-dev.txt` 뒤 **1.27.0**, editable install 뒤 **1.27.0**. 즉 그 한 줄을
지우면 1.x 커버리지가 조용히 사라지는데 아무 검사도 실패하지 않았다.

- 정본 `workflow_kit/common/sdk_matrix.py` 가 (a) 밟을 버전 3종과 근거, (b) 각 job 의
  정책(`pinned`/`floating`/`matrix`)과 그 버전이 **어디서 오는지** 를 적는다.
- `mcp-sdk-matrix` workflow 는 registry 에서 목록을 뽑아 `fromJson` 으로 matrix 를
  만든다 — **yml 에 버전 문자열이 없다**. path 필터도 없다(§2.43 이 늦게 발견된 이유).
- 기존 3 job 은 `--record <job>` 으로 집힌 버전을 step summary 첫 화면에 남긴다.
  `pinned` 인 smoke 는 어긋나면 실패한다.
- `check_mcp_sdk_matrix.py` 13건이 registry ↔ `requirements-dev.txt` ↔ pyproject extra
  ↔ workflow yml 을 **양방향**으로 묶는다.

**matrix 가 만들자마자 실제 결함을 하나 잡았다** — `check_read_only_mcp_sdk_stdio.py` 가
mcp 2.x 에서 깨져 있었다(`serverInfo` → `server_info` 등). 서버는 §2.43 에서 이관했지만
**읽는 쪽은 범위 밖**이었고, 이 검사는 smoke 에서만 = 1.x 로만 돌아서 아무도 못 봤다.
이번엔 전수 sweep 을 먼저 해 클라이언트 표면이 이 파일 하나임을 확인하고 고쳤다.

**판정을 두 번 고쳐 썼다** (§2.45): skip 문자열 탐지 → 위양성(`check_mcp_server_sdk_compat`
가 fail-fast 를 확인하느라 그 문자열을 *의도적으로* 출력), `run_all_checks` 의 `last_line`
→ 증거를 못 나름(1.x 는 SDK 로그가 뒤에 붙는다). 최종은 **판정이 왕복 검사 2건을 직접
돌려** exit 0 + 성공 메시지를 요구한다.

- 실측: 격리 venv 3종(1.27.0/1.29.0/2.0.0) 각각 요청=설치 일치 + subset 12/12 +
  왕복 증거 2/2. mypy strict 121 files 0 errors. 전량 smoke **224/224**
  (`dev,release,mcp-sdk` venv, 누수 0, 워킹트리 변경 0). 되주입 7건 각각 다른 신호.
- **수치에는 extra 조합을 함께 적을 것.** `release` 없는 venv 에서는 같은 트리가
  219/224 다 (3건은 문서가 223 이라 적고 있어서, 2건은 `build` 부재).
- **CI 러너 실측 완료**: 6종 green + matrix 3 셀 전부 요청=설치 일치·12/12·증거 2/2.
  `gh run view --log` 가 일부 run 에서 **빈 출력**을 낸다 (rc=0, size=0) — 없는 것이
  아니라 못 받은 것이다. `gh api repos/<o>/<r>/actions/jobs/<job_id>/logs` 로 받으면
  나온다. 이 경로로 세 job 의 `mcp SDK 실측` 줄을 확인했다.

---

이전 세션 기록: **의존성 드리프트로 `mypy-strict` 가 red 로 넘어갔다 — 상한 핀으로
되돌리고 원인 2건을 task 로 등록했다.** 문서 2줄만 바꾼 `23874d1` 에서 mypy-strict 가 실패했는데, 커밋
내용과 무관했다. CI 설치 로그에 **`mcp-2.0.0`** 이 찍혀 있고 (extra 가 `mcp[cli]>=1.0` 로
상한이 없었다) 같은 소스에 버전만 갈아 끼워 재현했다 — `1.28.1` green / `2.0.0` 에서
`mcp_v1_server.py:27 no-any-return`.

**에러 메시지가 원인에서 한 칸 떨어진 곳을 가리키고 있었다.** 실제 사실은 mcp 2.0.0 이
`mcp.server.fastmcp` 모듈 자체를 없애고 `mcp.server.mcpserver.MCPServer` 로 옮긴 것이다
(2.0.0 의 `mcp.server` 하위 모듈 목록 실측). 즉 타입 문제가 아니라 `HAS_FASTMCP=False` →
`sys.exit(1)` 인 **런타임 파손**인데, `pyproject.toml` 의 `ignore_missing_imports = true` 가
사라진 모듈을 error 가 아니라 `Any` 로 바꿔 놓아 27번 줄에서야 표면화됐다.

1차 조치는 상한 핀이었고(red 를 켜 둔 채로는 다음 커밋의 신호를 읽을 수 없어서지, 그것이
해결이어서가 아니다), 이후 TASK-2026-07-29-main-001 로 **wrapper 이관**을 마쳤다 — 세부는
릴리스 노트 §2.41. wrapper 가 2.x → 1.x 순으로 두 이름을 시도하고 어느 쪽을 잡았는지
`MCP_SERVER_SOURCE` 로 남긴다. `1.27.0`/`1.28.1`/`1.29.0`/`2.0.0` 네 버전에서 mypy strict
119 files 0 errors + 런타임(실제 서버 2종 tool 등록까지)을 각각 실측했다.

**거기서 핀을 한 번 풀었는데 그것이 틀렸다.** "이관했다" 의 범위를 SDK 표면이 아니라
**파일 하나**로 잡았다. 같은 SDK 를 쓰는 표면이 하나 더 있었고(`read_only_mcp_sdk.py` 의
lowlevel 서버), 핀을 푼 커밋이 처음으로 `server/**` 를 건드려 `mcp-inspector` 를 깨우기
전까지는 어느 검사도 그것을 보지 않았다. `grep '^from mcp'` 는 wrapper 만 짚어 준다 —
두 번째 표면은 `importlib.import_module("mcp…")` 로 들어와서 안 걸렸다.

**그 표면도 TASK-2026-07-29-main-003 으로 닫았다(§2.43).** import 문법 4가지로 전수
조사해 표면이 정확히 둘임을 먼저 확인한 뒤 **상한 핀을 해제**했다. 지금 `mcp` 는 상한이
없고, 두 표면 모두 1.x/2.x 를 해석한다.

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

- [x] ~~TASK-2026-07-29-main-001 — mcp 2.0.0 이관(wrapper)~~ → **완료(§2.41)**. `.tool()` 은
      두 SDK 모두 "함수를 그대로 돌려주는 decorator" 라 wrapper 계약(`Callable[..., Any]`)이
      유효함을 확인했고, `cast` 로 좁혀 반환한다. **1.x 지원은 끊지 않았다** — 두 이름을
      모두 시도한다.
- [x] ~~`mcp-inspector` red — Python 문제인 줄 알았다~~ → **§2.42 에서 조치**. 핀 복원 후에도
      red 였고, 이번엔 Python 이 아니었다. `npx -y @modelcontextprotocol/inspector` 가
      버전 고정이 없어 Node 쪽 인스펙터도 **2.0.0** 으로 넘어갔고, `[target...]` 인자를
      삼켰다 (argv wrapper 로 `ARGC=0` 실측 → 맨 python 이 REPL 로 떠서 JSON-RPC 의
      `true` 를 Python 으로 실행 → `NameError`). `--config`/`--server` 선언 방식 +
      `@2` major 고정 + 빈 응답 실패화. 로컬 전 구간 13/13 일치 확인.
- [x] ~~TASK-2026-07-29-main-003 — lowlevel 이관~~ → **완료(§2.43). 상한 핀 해제.**
      분기 기준을 버전 문자열이 아니라 **계약의 존재**로 잡았다
      (`uses_handler_registration` = `hasattr(server, "add_request_handler")`).
      프로토콜 왕복을 실제로 돌려 확인했다 — 1.28.1/2.0.0 에서 `tools/list` 13개,
      `tools/call` 성공·실패 경로, **두 버전의 wire 산출물이 JSON 동일**.
      - `isError` 를 나중에 대입하던 것이 2.x 에서 `is_error` 라 빗나가 **실패한 tool
        호출이 성공으로 보고될** 자리였다 → 생성 시점 `force_error` 로 이동.
      - `Tool`/`CallToolResult` field 는 2.x 가 snake_case 로 바꿨지만 camel alias 로
        양쪽을 받아 payload 조립은 갈라 쓰지 않았다.
      - 핀 해제 전에 import 문법 4가지로 전수 조사해 표면이 정확히 **2개**임을 확인했다
        (§2.41 에서 이 조사를 안 한 것이 그때의 실수였다).
      - `version` 은 계속 전달하지 않는다. 2.x `MCPServer` 는 받지만 1.x `FastMCP` 는
        받지 않고, 여기서 넘기기 시작하면 서버 2종이 광고하는 version 이 바뀐다 —
        이관 범위 밖이라 기존 동작을 유지했다. 바꾸려면 별도 결정이 필요하다.
- [x] ~~핀 해제로 CI 가 두 major 를 동시에 밟는다 — 설치 순서에 기댄 우연~~ →
      **완료(§2.45)**. matrix 는 `pinned` 3종만 본다. **새 major 조기 경보는 여전히
      floating job(`mypy-strict`/`mcp-inspector`)에 의존한다 — 이것은 의도다.** 그 층이
      2.0.0 을 물어 왔고, 없애면 경보를 잃는다. 대신 부동이라고 적고 집힌 값을 남긴다.
      다음 major 를 matrix 에 넣는 것은 registry 에 한 줄 추가하는 일이다.
- [x] ~~TASK-2026-07-29-main-002 — `ignore_missing_imports` 탐지 구멍~~ → **완료(§2.44)**.
      **판정 기준을 먼저 정했다: 설정을 좁히지 않는다.** optional dep 은 실제로 optional 이라
      `mcp.*` 만 빼면 SDK 미설치 로컬이 red 가 되고, 더 근본적으로 **mypy 는 "안 깔림" 과
      "깔렸는데 모듈이 사라짐" 을 구분할 수 없다** — 그 구분은 런타임 import 에서만 된다.
      설정은 그대로 두고 판정을 옮겼다.
      - `common/optional_deps.py` 가 import 대상 정본. `required`(전부) /
        `alternative`(하나만) 두 종류로 나눴다 — 이 구분이 없으면 2.x 에서 검사가
        **틀린 실패**를 낸다. `read_only_mcp_sdk.SDK_IMPORT_TARGETS` 의 사본은 제거.
      - **완료 기준 확인**: 이관 전 가정을 되주입하면 1.28.1 은 통과, 2.0.0 은
        `'mcp.server.fastmcp' 모듈이 없다 (ModuleNotFoundError)` 로 실패한다. 같은
        상황에서 mypy 가 냈던 `no-any-return` 과 대비된다.
      - skip 은 조용히 넘기지 않는다 — 몇 건을 왜 건너뛰었는지 출력한다
        (로컬 2건, mcp 없는 venv 6건 실측).
- [x] ~~`backlog-update` 가 handoff §4 에 상한을 적용하지 않는다~~ → **완료(§2.46)**.
      쓰는 쪽(`sync_handoff_status`)이 상한을 적용한다. 정본은
      `common/project_docs.RECENT_DONE_ITEMS_CAP` 한 곳이고 린터의 리터럴 사본도 없앴다.
- [x] ~~`state.json` 의 `backlog.task_count` 는 항상 0, `latest_backlog_path` 는 항상
      `null`~~ → **완료(§2.46)**. 경로 해석을 세 갈래로 분리했다. `backlog` block 이
      통째로 죽어 있던 것이라 `task_count` 만의 문제가 아니었다.
- [x] ~~**`run_workflow_linter.py` 의 `project_root` 가 저장소 루트보다 한 단계 위를
      가리킨다**~~ → **완료(§2.47)**. 기준을 `project_workspace_root` 로 통일하고,
      정본이 `workflow-source/pyproject.toml` 인 문제는 사본이 아니라 `--config-path`
      명시로 풀었다. **같은 값이 `--maturity` 경로에도 쓰이고 있어서, 그쪽은 늘
      `skipped` 인데 `status: ok` 로 보고되고 있었다** — 그것도 같이 닫았다.
- [ ] **`--maturity` 를 처음 실제로 돌리니 내용 드리프트 2건이 나왔다** (§2.47 범위 밖):
      matrix 의 `Phase 13` 이 `in_progress` 인데 roadmap 은 그 단계를 현재로 말하지
      않는다, `task-modes` 가 stable 인데 `test_path` 가 없다.
- [ ] **`workflow_kit.cli.doctor` 는 아직 provenance 를 안 쓴다** (`load_config(args.project_root)`).
      같은 "조용한 default" 가 CLI 쪽에는 그대로 남아 있다.
- [ ] **handoff §4 는 상한만 생겼고 정렬 기준은 여전히 없다.** `tasks_dir` 이 있는
      저장소는 builder 가 task SSOT 를 먼저 쓰므로 무해하지만, legacy 저장소(task 파일
      부재)에서는 handoff 가 tail fallback 이 되고 builder 가 **앞에서** 자르므로
      오래된 것이 남는다.
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

- **이번 세션의 교훈(§2.47)**: §2.44 는 "관대한 *설정* 이 판정을 지운다" 였고 이건 그
  사촌이다 — **관대한 *fallback* 이 자기가 무엇을 못 했는지 말하지 않는다.** 실패하지
  않는 loader 를 만들 거면, 무엇을 물었고 무엇을 얻었는지는 반드시 함께 내놓아야 한다.
  그러지 않으면 "적용됨" 과 "떨어짐" 이 같은 모양이고, 같은 모양인 동안에는 아무도
  결함을 볼 수 없다.
- **이번 세션의 교훈(§2.47, 검사 쪽)**: `check_v0_7_15_config_thresholds` 의 9번째 case 는
  runner 본문에서 `"load_config(project_root)"` 라는 **문자열**을 찾고 있었다. 그 줄은
  내내 있었고 다만 없는 경로를 묻고 있었다 — **통과하면서 아무것도 보장하지 못하는
  검사**였다. 문자열이 아니라 **산출물의 사실**로 판정할 것.
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
