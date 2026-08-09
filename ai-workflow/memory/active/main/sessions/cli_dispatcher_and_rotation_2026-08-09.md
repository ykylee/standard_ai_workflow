# CLI 化 B안부터 rotate 결함까지 — 고장난 도구가 숨긴 것들 (2026-08-09)

- 문서 목적: 이번 세션의 판단 근거와 실측을 남긴다. handoff 가 담기엔 긴 맥락.
- 범위: memory 정합성 정리 → 후보 축 4건 구현 → rotate 도구 수정 → red 검토
- 대상 독자: 다음 세션의 AI agent, 저장소 관리자
- 상태: closed
- 최종 수정일: 2026-08-09
- 관련 문서: [multi_workspace_orchestration.md](../../../../../workflow-source/core/multi_workspace_orchestration.md) (§0.7 상태표 · §7.4 · §7.5), [backlog/2026-08-09.md](../backlog/2026-08-09.md)

## 1. 무엇을 했나 (커밋 3건, TASK 6건)

| 커밋 | 내용 |
| --- | --- |
| `4e31d8c` | memory 문서 정합성 정리 (TASK-001) |
| `ad3ab02` | 후보 축 4건 close — `wk` / HTTP server / branch protection / title drift v2 (TASK-002~005) |
| `6cfb168` | rotate 도구 순서 규약 통일 + 사전 존재 red 정리 (TASK-006) |

시작은 "작업 내역 확인"이었고, 끝난 자리는 **"고장난 도구가 무엇을 숨기고 있었나"**
였다. 아래가 그 사이에서 방향을 바꾼 것들이다.

## 2. 이미 있는 것을 다시 만들 뻔한 일 2건

### 2.1 dispatcher — TASK-020 노트를 그대로 따랐으면 진입점이 둘이 됐다

TASK-020 은 후속으로 `tools/cli/dispatcher.py` **신설** 을 적어 뒀다. 그런데
`workflow_kit_cli.py` 를 열어 보니 이미 38 subcommand dispatcher 였다. 그대로
만들었으면 `--help` 가 둘로 갈리고 어느 쪽이 정본인지 흐려진다.

정공법도 이미 저장소 안에 있었다. `score-wiki-trend` (v0.7.56+) /
`consumer-metrics` (v0.7.59+) wrapper 가 쓰던 **sys.argv 치환 + SystemExit → rc**
패턴이 그것이다. 29개로 일반화한 것이 `tool_dispatch.run_tool()` 이다.

`main()` 시그니처가 `main(argv)` 13 : `main()` 16 으로 갈려 있었는데, 29개 파일을
통일하는 대신 `inspect.signature` 로 읽어서 맞췄다 — 변경면이 훨씬 작고, 각 tool 의
`__main__` 블록을 따라 고칠 필요도 없다.

### 2.2 federation — 서버가 없던 게 아니라, 등록할 방법도 없었다

TASK-016 이 pull 을 닫았으니 서버만 만들면 된다고 봤다. 그런데
`add_known_host()` 를 누가 부르는지 grep 해 보니 **호출부가 없었다.** API 는
TASK-015 부터 있었는데 CLI 가 없어 상대 호스트를 등록할 수단이 아예 없었다.
서버를 띄워도 federation 은 어느 쪽으로도 돌지 않는 상태였다.

> **API 만 있고 부를 CLI 가 없으면 기능이 없는 것과 같다.** 검사도 그 사실을
> 잡지 못했다 — API 단위 테스트(`check_host_federation` 8 case)는 전부 green 이었다.

## 3. 고장난 도구가 숨긴 것들

`handoff_bloat` 경고를 해소하라고 있는 `rotate_workflow_logs` 가 `status: error` 만
냈다. 원인을 파 보니 결함이 **둘** 이었다:

1. 섹션을 고정 문자열(`## 5. 최근 완료 작업` / `## 6. 잔여 작업`)로 찾았다. 실제
   문서는 `## 4.` 이고 다음 섹션은 `## 5. 다음 세션 시작 포인트` 다.
2. `items[-max:]` 로 **뒤** 를 남겼다. §4 는 **앞이 최신** 이다.

**1번만 고쳤다면 도구가 "동작하면서" 최신 항목을 지웠을 것이다.** 고장이 두 번째
결함을 가리고 있었던 셈이다.

### 3.1 규약은 새로 정할 필요가 없었다

문서를 뒤집을지 도구를 바꿀지 물어보려다, 정본을 먼저 찾았다.
`check_recent_done_items_order.py` 계약 1: *"`recent_done_items` 는 최신순이다"*.

| 자리 | 규약 |
| --- | --- |
| `state.json.recent_done_items` | 최신이 앞 (계약 1) |
| handoff §4 실제 문서 | 최신이 앞 (사람·에이전트가 줄곧 앞에 붙였다) |
| handoff §4 writer | **뒤가 최신** (`append`) ← 혼자 반대 |

둘이 일치하고 writer 만 어긋났으므로 writer 를 고쳤다. 규약 선택이 아니라
**이미 있는 규약에 맞추는 일** 이었다.

### 3.2 그리고 검사 하나가 저장소를 오염시키고 있었다

rotate 를 고치자 `check_no_repo_write` 가 red 로 바뀌었다. 추적해 보니
`check_cli_wrappers` 가 **실제 `session_handoff.md` 를 대상으로** rotate 를
부르고 있었다. rotate 가 늘 `error` 였던 탓에 아무것도 안 써서 드러나지 않았다.

같은 자리에 두 번째 문제도 있었다: CLI 호출이 먼저 파일을 자르면 이어지는 MCP
호출은 no-op 이 되어 `rotated_count` 가 당연히 어긋난다 — **비교 자체가
불공정** 해진다. 호출마다 tempdir 복사본을 주도록 고쳤다.

> `check_cli_wrappers` 는 v1.1.1 에서 4 case ALL PASS 였다. 그 검사가 본 것은
> *CLI 와 MCP 의 출력이 같은가* 였고, 둘 다 똑같이 `error` 를 냈으므로 통과였다.
> **출력 일치는 정확성이 아니다.**

## 4. 실측이 뒤집은 구현 2건

### 4.1 title 추출 — TASK-ID 는 줄의 어디에나 온다

처음엔 ID *뒤* 를 제목으로 삼았다. 실제 handoff 에 돌려 보니
`", 본 세션). 4-level enum + Panel 5"` 를 집었다. §5 는
`- **항목명** — ✅ 닫힘 (TASK-xxx, …)` 형식이라 **ID 가 뒤에** 온다.

```
- TASK-xxx 제목 — 상세…               (handoff §4: 앞)
- **TASK-xxx** [tag] 제목              (backlog:    앞)
- **항목명** — ✅ 닫힘 (TASK-xxx, …)   (handoff §5: 뒤)  ← 놓쳤던 형식
```

지금은 ID 앞에 텍스트가 있으면 그쪽을 쓴다. 이 케이스를 회귀 검사(3b)에 넣었다.

### 4.2 `importlib.util` — 우연히 동작하고 있었다

`import importlib` 만으로는 `.util` 이 안 붙는다. 다른 모듈이 먼저 import 해준
덕에 런타임에서는 통과했고, **mypy 가 잡았다.**

## 5. 검사를 어떻게 잡았나

- **왕복으로 본다** — registry 서버는 응답만 확인하지 않고 실제로 띄워
  `pull_remote_registry()` 로 되받는다. 서버 단독 검사는 `_fetch_url` 쪽 계약
  위반을 놓친다.
- **모름을 안전으로 치지 않는다** — branch protection 판정에서 필드를 못 읽으면
  (권한 부족의 `null`) 통과로 세지 않는다. 실제로 꺼진 것과 섞이면 검사가 거짓
  안심을 준다. 같은 이유로 `gh` 부재는 skip 이지 pass 가 아니다.
- **두 표면이 같은 것을 가리키는지 강제한다** — `TOOL_MODULES` ↔
  `[project.scripts]` 를 양방향 집합 + target 까지 비교한다. 이름만 맞고 대상이
  갈리면 더 나쁘다.
- **판정은 pure function 으로 분리한다** — 네트워크/권한에 흔들리는 검사는 회귀
  검사로 쓸 수 없다.

## 6. 사고 1건 — 검사 결과를 두 번 잘못 셌다

1. `[FAIL]` 패턴만 grep 해 red 를 **7건** 이라고 보고했다. `✗` 로 세면 다르다.
2. 이어서 보고한 **31 → 24** 는 전체 검사가 **내가 파일을 편집하는 도중에** 돌아
   반쯤 바뀐 트리를 본 결과다. 무효다.

편집을 멈추고 돌린 최종 실행만 유효하다: **red 5건, 전부 사전 존재**
(`git stash` 로 개별 확인), 본 세션이 만든 red 0건.

> 검사는 트리가 멈춘 뒤에 돌린다. 그리고 결과를 세는 방법이 틀리면 그 위의
> 판단이 전부 틀어진다.

## 7. 남긴 것

- **`check_smoke_trend_cross_v0_15_5`** — `cumulative_total` 은 *가장 최근 릴리스
  노트* 에서 파싱하는데 v1.1.0 / v1.1.1 노트에 "누적 smoke **N/N PASS**" 줄이 없어
  v1.0.0 의 234 를 읽는다. 고치려면 발행된 노트를 사후 수정해야 해서 릴리스
  사이클에 맡겼다. **다음 릴리스 노트에 그 줄을 반드시 넣는다.**
- **사전 존재 red 4건** — `check_source_without_runtime_layer` (fixture stale) /
  `check_tempdir_leak_guard` (11건) / `check_wiki_url_validity` (PicklingError) /
  `check_workflow_kit_cli` (1 case). 본 세션 범위 밖.
- **branch protection 미설정** — 이 저장소 `main` 에 보호가 없다 (404 실측).
  3rd layer 가 비어 있고, 켜는 것은 소유자 판단이라 손대지 않았다.
- **검증 못 한 것** — registry HTTP server 는 loopback 왕복만 실측했다. LAN /
  방화벽 너머 / reverse proxy / TLS 종단은 확인한 적 없다. title drift 임계 0.6 도
  운영 데이터로 고른 값이 아니다.

## 8. 다음 세션에

`v1.1.2-beta` 발행 여부가 첫 판단이다. 발행한다면 릴리스 노트에 *누적 smoke* 줄을
넣어 `check_smoke_trend_cross` 를 같이 닫는다.
