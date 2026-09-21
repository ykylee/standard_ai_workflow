---
type: meta
status: draft
r9_skip: true
title: active-session-handoff
created: 2026-07-22
last_touched: 2026-09-21
---

# Active Session Handoff (Derived View, 2026-09-21)

> L1 SSOT: `ai-workflow/memory/active/main/session_handoff.md` (766 lines)
> 본 L2 파생 뷰는 in-repo retrieval 용 압축 요약이다. 정본은 L1 SSOT 를 본다.
> 생성: `2026-09-21` by `workflow_kit.tools.refresh_wiki_memory --emit-l2`

## 현재 기준선

**80차 세션 (2026-09-18, plex 호스트/linux) — 파생물 3건을 닫았고, 그 중 둘은 *탐침이 무엇을 재고 있었는가* 를 뒤집었다 (task 3건 close: main-004 · -005 · -006).** **① 이틀에 두 번 손으로 풀던 자리를 도구가 잡는다**: `backlog-update --apply` 는 `state.json` 은 이미 재생성하면서 **형제 생성물** `roadmap_state.json` 은 두고 갔다 — 그 SSOT 가 *방금 자기가 쓴* task frontmatter(`wbs`·status)인데도. 뒤처짐은 경고 없이 push 게이트에서야 드러났다. 같은 호출에서 같이 재생성하게 하고, 정본 스펙 §7.1 의 '재생성은 `wk refresh-state`' 선언도 고쳤다 — **그 선언 자체가 backlog-update 를 규약 밖에 둔 근거**였다. **② 79차 잔여(`runtime_load` 오측정)는 재시작으로 풀렸다**: 프로세스 01:21:06 > 설치 00:13:49, 낡은 호스트 0. 겸해서 §7.0.1 이 '실제 호출로만 재진다' 고 남겨 둔 **노출 한 칸을 처음 쟀다** — 스킬 4종 전부 노출 + 호출 성공, 중립 cwd 의 새 프로세스에서도 4종. **③ 그런데 그 호출이 읽은 것은 캐시 사본이 아니었다**: base directory 가 `~/.claude/plugins/cache/.../1.9.4/` 가 아니라 **저장소 워킹 트리**였다. 마켓플레이스가 `directory` 소스로 저장소 자신을 가리키기 때문이다. 두 사본이 byte 동일이라 **파일 비교로는 원리적으로 못 가르는** 자리였고, 캐시에 마커를 넣어 되주입으로 확정했다(새 프로세스에 안 보임 → 원복 byte 동일). **④ 그래서 `content_drift` 는 아무도 안 읽는 사본을 재고 있었다** — 소스 유형을 읽어 ⓐ directory 면 서빙 경로를 실제로 대조하고 ⓑ 캐시는 `served=false` 로 `unserved` 에 남기며(읽히지 않는 사본의 드리프트는 발견이 아니다 — `superseded` 와 같은 규율) ⓒ 그 상태를 발견으로 말한다. 덤으로 보고 렌더러가 marketplace 행을 무조건 `codex` 로 찍던 리터럴을 걷었다. **⑤ 착수 전에 전제를 하나 정정했다**: '서빙 경로가 정본 생성기의 입력이라 자기 자신과의 비교' 라고 적었는데 아니다 — 정본은 `core/global_workflow_standard.md` 에서 **렌더**되고 `plugin/` 은 입력이 아니라 산출물이다. **⑥ 검증**: 되주입 총 3종(재생성 호출 제거 / 소스 유형 축 제거 / 서빙 경로 대조 제거) 전부 red 후 원복 green, 오염을 캐시·서빙 어느 쪽에 넣느냐로 판정이 갈리는 것까지 case 로 고정 · `check_deploy_doctor` 36→39 · `check_roadmap_wiring` 5→6 · push 게이트 전량 2축 **284/284 ×2 green ×3회** · CI 3회 전부 success. **⑦ 잔여**: `github` 소스 셀은 이 호스트에 원격 설치가 없어 실증 불가 — 탐침이 그것을 가정으로 두고 `declared_unmeasured` 에 적는다.

## 진행 중

- (없음)

## 차단

- TASK-2026-08-25-main-017 MCP emit command 가 항상 python3 — PATH 에 python3 이 없는 Windows 에서 emit 설정으로 서버를 spawn 할 수 없다
