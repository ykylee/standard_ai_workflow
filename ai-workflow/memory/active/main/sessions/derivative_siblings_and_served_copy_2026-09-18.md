# 80차 세션 — 형제 파생물, 그리고 탐침이 재고 있던 사본

- 문서 목적: 파생물을 쓰는 층이 형제를 모르던 결함과, 배포 탐침이 *읽히지 않는 사본*을 재고 있었다는 사실을 남긴다.
- 범위: TASK-2026-09-18-main-004 · main-005 · main-006
- 대상 독자: AI agent, 저장소 관리자
- 상태: stable
- 최종 수정일: 2026-09-18
- 관련 문서: [session_handoff.md](../session_handoff.md), [roadmap_milestone_wbs_spec.md](../../../../../workflow-source/core/roadmap_milestone_wbs_spec.md), [INSTALLATION_AND_USAGE.md §7.0](../../../../../docs/INSTALLATION_AND_USAGE.md)

## 0. 이 기록이 남길 것

세 건이 한 줄로 꿰인다: **무엇을 재고 있었는지를 아무도 묻지 않았다.**

- main-004 — 도구가 파생물 *하나*를 갱신하고 있었고, 그것이 *전부* 갱신한다는
  뜻으로 읽혔다.
- main-005 — 탐침이 "설치 사본" 을 재고 있었는데, 그것이 **읽히는 사본이 아니었다.**
- main-006 — 그 사실을 탐침이 읽게 했다.

두 번째가 핵심이다. 그 자리는 **파일 비교로는 원리적으로 못 가른다** — 두 사본이
byte 동일이었기 때문이다. 동일한 두 사본 중 어느 쪽이 읽히는지는 **한쪽만
오염시켜야** 나온다.

## 1. main-004 — 형제 파생물

`backlog-update --apply` 는 `state.json` 을 이미 재생성하고 있었다(v1.0.1/v1.0.2).
형제 생성물 `roadmap_state.json` 만 그 규약 밖이었고, 유일한 갱신 창구가
`wk refresh-state` 였다. 그런데 `roadmap_state.json` 의 SSOT 는 roadmap 파일만이
아니라 **방금 이 도구가 쓴 task frontmatter**(`wbs` 링크·status)다.

뒤처짐에는 경고가 없다. push 게이트의 `check_roadmap_state_generated` 가 red 를
낼 때까지 아무 신호도 없고, 2026-09-17·09-18 **이틀에 두 번** 수동
`wk refresh-state` 로 풀었다.

- 수리: `--apply` 경로에서 `generate_roadmap_state()` 를 같이 부른다. roadmap
  부재는 `None` = 해당 없음(additive). write 는 `written_paths` 에 싣고 신규/기존을
  `created_paths` / `updated_paths` 로 갈라 적는다.
- 판정: `check_roadmap_wiring` case 신설(5→6). 소스 문자열이 아니라 **산출물**을
  잰다 — fixture 에서 CLI 를 돌린 뒤 `state_matches_regeneration` 과
  `written_paths` 를 본다. draft 무write / roadmap 부재 무생성 두 축도 함께 고정.
- 정본: 스펙 §7.1 이 "재생성은 `wk refresh-state`" 만 적고 있었고, **그 선언 자체가
  backlog-update 를 규약 밖에 둔 근거**였다. 창구가 아니라 "누가 SSOT 를 쓰는가"로
  다시 적었다.

## 2. main-005 — 노출 한 칸, 그리고 예상 밖

79차 잔여(프로세스가 설치보다 먼저 떠서 `runtime_load` 가 낡은 호스트 1 로 센다)는
재시작으로 풀렸다: 프로세스 01:21:06 > 설치 00:13:49, 낡은 호스트 0.

겸해서 §7.0.1 이 "실제 호출로만 재진다" 고 남겨 둔 **노출 한 칸**을 쟀다. 이
세션이 그 실제 호출이기 때문이다. 스킬 4종 전부 노출 + 호출 성공 — 2026-08-20 의
`Unknown skill` 과 정반대 방향의 확인. 중립 cwd(`/home/yklee`)에서 띄운 새
프로세스에서도 4종이 보였으므로, 노출하는 것은 프로젝트 오버레이가 아니라 user
스코프 설치다.

**그런데 그 호출이 읽은 것은 캐시 사본이 아니었다.** 보고된 skill base directory 가
`~/.claude/plugins/cache/<mp>/<plugin>/<version>/` 이 아니라 **저장소 워킹 트리**
(`<repo>/plugin/skills/…`)였다. 원인은 마켓플레이스 **소스 유형** —
`known_marketplaces.json` 에서 이 마켓플레이스는 `source: directory`,
`installLocation: <repo>` 다. 캐시 사본은 별도 inode 의 실사본으로 설치 시각에
만들어져 있지만 서빙되지 않는다.

### 되주입이 필요했던 이유

두 사본이 byte 동일이었다. `diff -r` 는 "동일" 이라고만 말하고, base directory
문자열 하나로는 그것이 실제 read 경로인지 표시용인지 가를 수 없다. 그래서 캐시
사본의 `doc-sync/SKILL.md` 에 마커를 넣고(사본 백업 후) 중립 cwd 에서 새
프로세스를 띄워 **스킬 지시문에 그 문자열이 있는지** 물었다 — 없었다. 원복 후
저장소 사본과 byte 동일 확인.

> 이 저장소의 기존 규칙과 같은 모양이다: [사본을 접으면 외부 증인이 필요하다].
> 내부 대조는 동어반복이고, 갈라지지 않은 두 사본은 서로의 증인이 못 된다.

## 3. main-006 — 탐침이 소스 유형을 읽는다

`content_drift` 는 캐시 사본을 정본 페이로드와 대조한다. directory 소스에서는
그것이 로드되는 사본이 아니다 — **재는 대상과 읽히는 대상이 다르다.**

- `_claude_marketplace_sources` 신설 — `installed_plugins.json` 의
  `<plugin>@<market>` 키에서 마켓 이름을, `known_marketplaces.json` 에서 소스
  유형과 `installLocation` 을 읽는다. codex 의 `_codex_marketplace_sources` 와
  같은 부류지만 한 칸 더 간다: codex 에서는 경유지가 *사라지면* 문제였고, 여기서는
  경유지의 **유형이 무엇이 읽히는지를 바꾼다.**
- directory 소스면 **서빙 경로를 실제로 대조한다.** 그 루트는
  `<소스>/.claude-plugin/marketplace.json` 의 `plugins[].source` 에서 읽는다 —
  `plugin/` 을 관례로 가정하면 다른 저장소에서 조용히 틀린다.
- 캐시 레코드에 `served` 축. `served=False` 는 `out_of_sync` 에서 빼고 `unserved`
  에 남긴다 — `superseded` 와 같은 규율이다(아무도 안 읽는 사본으로 거짓 발견을
  만들지 않되, 침묵으로 지우지도 않는다). 대신 "캐시가 아니라 `<경로>` 가 읽힌다"
  를 **발견으로 말한다** — 오류가 아니라 상태이지만, 모르면 in-sync 를 오독한다.
- 덤: 보고 렌더러가 marketplace 행을 무조건 `codex marketplace …` 로 찍고 있었다.
  목록이 단일 채널이던 동안은 맞았고, 채널이 하나 늘어나는 순간 조용히 틀렸다.

### 착수 전에 정정한 전제

main-006 의 완료 기준 3번을 "서빙 경로가 정본 생성기의 **입력**과 같은 디렉터리라
자기 자신과의 비교가 된다" 로 적어 두었다. 틀렸다. `_canonical_payload` 는
`render_agent_plugin()` 을 부르고 그것은 `load_standard_rules` 로
`core/global_workflow_standard.md` 에서 **렌더**한다 — `plugin/` 을 읽지 않는다.
`plugin/` 은 같은 생성기의 산출물이지 입력이 아니다. 따라서 서빙 경로 대조는
동어반복이 아니라 **커밋된 `plugin/` 이 낡았는지를 재는 실제 대조**다.

## 4. 검증

되주입 3종, 전부 red 후 원복 green:

| 주입 | 기대 red | 실제 |
|---|---|---|
| `backlog-update` 의 roadmap 재생성 호출 제거 | `check_roadmap_wiring` | "roadmap_state 가 뒤처졌다" + "written_paths 에 안 보인다" |
| doctor 의 소스 유형 축 제거 | `check_deploy_doctor` | "served=False 로 안 적었다" + "아무도 안 읽는 사본으로 발견을 만들었다" |
| doctor 의 서빙 경로 대조 제거 | `check_deploy_doctor` | "아예 대조하지 않았다" + "읽히는 사본이 오염됐는데 발견이 없다" |

오염을 **캐시에 넣느냐 서빙 경로에 넣느냐**로 판정이 갈리는 것까지 case 로
고정했다 — 둘 다 통과하거나 둘 다 red 면 그 절은 자기가 무엇을 재는지 모르는 것이다.

게이트: `check_deploy_doctor` 36→39 · `check_roadmap_wiring` 5→6 ·
`--changed` 3회 전부 green · `check_self_application` 8/8 · mypy strict ·
push 게이트 전량 2축 **284/284 ×2 green ×3회** · push 후 CI 3회 전부 success
(smoke 6m3s / 5m22s / 5m39s · mcp-sdk-matrix · os-matrix · mypy-strict · mkdocs).

## 5. 남은 것

- **`github` 소스 셀은 실측이 아니다.** 이 호스트에 원격 마켓플레이스 설치가 없어
  재현할 수 없었다. 탐침은 원격 소스를 "캐시가 읽힌다" 는 **가정**으로 두되 그
  사실을 `declared_unmeasured` 에 적는다. 소비자가 그 경로로 설치하면 전제가 틀릴
  여지가 남아 있다.
- **roadmap 마일스톤 파일의 선언 status 를 손으로 고치는 경로**는 여전히 세션
  종료의 `wk refresh-state` 가 유일한 창구다. 사람이 여는 파일이라 "쓰는 층" 논리가
  안 붙는다.
- `TASK-2026-09-07-main-009` (낡은 호스트 3개) 는 macOS 호스트의 값이다 — 이
  호스트(plex)는 오늘 0 으로 실측됐다.
