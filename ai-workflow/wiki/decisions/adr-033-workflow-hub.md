---
type: decision
status: accepted
adr_id: ADR-033
decided_at: 2026-11-20
alternatives_considered: [git-ssot-hub-as-view, project-chooses-ssot, kit-protocol-client-only, move-go-portal-into-kit, kit-installed-on-every-env, instructions-ssot-in-repo-main]
related_pages: [decisions/adr-032-plan-workbench, decisions/adr-031-claim-plan, decisions/adr-027-roadmap-wbs-sdlc]
created: 2026-11-20
updated: 2026-11-21
r9_skip: true
---

# ADR-033: 워크플로우 허브 — kit 없는 환경을 허브가 워크플로우대로 관리한다

## Status

**Accepted** (2026-11-21, TASK-2026-11-21-claude-workflow-hub-concept-001, M-032/WBS-32.4) — requirements(M-031) · design(M-032) 완료, design 결정 DS1~DS9 소유자 확정. Proposed 2026-11-20 (TASK-2026-11-20-claude-workflow-hub-concept-002, M-030/WBS-30.1). 위키 (§11, WBS-30.2) · 등록 · 식별 · 콜사인 기억 · MCP (§12~§14, WBS-30.3) 도 같은 날 결정.
방향 H1~H14 와 결정 D1~D11 · E1~E6 · F1~F5 · G1~G3 · I1~I4 (concept 문서 `docs/planning/workflow-hub-review-2026-11.md` 의 권고안 전부, §10 · §15) 를 소유자가 정했다 (2026-11-20).
계약 정본: [`hub_spec.md`](../../../workflow-source/core/hub_spec.md) · 요구와 실측: [`workflow-hub-requirements-2026-11.md`](../../../docs/planning/workflow-hub-requirements-2026-11.md).

## Context

- arcturus-port 프로젝트가 공유 대시보드(Go · PostgreSQL · Astro, 홈랩)로 여러 작업 환경의 task 를 관리하는 실험을 했다
  (그 저장소 ADR-043, 2026-11-19 · 이식 W1 · W2, 2026-11-20). 모든 환경의 task 를 한곳에서 고치고, 콜사인으로 이력을 남기고,
  서버가 kit 판정으로 done 게이트를 걸었다.
- 같은 실험이 드러낸 문제: git task 와 포털 task 의 두 정본, kit 집계가 포털 task 를 모름, 프로젝트 규칙의 kit 예외,
  task 는 포털 · handoff 는 git 의 반쪽 이전, kit 서비스의 판 고정, 프로젝트마다 다시 지어야 하는 서버 (concept §2.3).
- kit 은 지금 각 작업 환경에 깔려 git 의 state 문서를 다룬다 (PURPOSE §4 명제). 워크벤치(ADR-032)는 checkout 하나에
  서버 하나이고, registry federation 은 읽기 전용이다.

## Decision

소유자 결정 (2026-11-20):

| # | 결정 |
|---|---|
| H1 | **task 정본 = 허브 DB.** git 은 내보내기다 |
| H2 | **허브는 kit 이 Python 으로 가진다.** 판정(계획 린트 · done 게이트 · 결정 상태 · 상태 생성)은 허브 프로세스 안의 kit 함수가 한다. PURPOSE 제외 '비 Python runtime' 은 그대로 |
| H3 | **개념 문서 + ADR 먼저** — 코드는 열린 결정 뒤 |
| H4 | **작업 환경에 kit 이 없어도 부트스트랩**하고, 허브가 워크플로우대로 task · handoff · 이력을 관리한다. 환경이 받는 것은 허브가 내려주는 표준 라이브러리 클라이언트와 진입 규칙이다 |
| H5 | **프로젝트 공유 지침(AGENTS.md · CLAUDE.md 등)을 허브가 들고**, 하네스별 진입 파일로 렌더링해 셋업 · 갱신한다 |
| H6 | **허브는 프로젝트 등록 전부터 부트스트랩퍼를 제공**하고, 부트스트랩퍼가 프로젝트 등록부터 한다 |
| H7 | **프로젝트는 git 원격 주소(정규화)로 구분**한다 — 세부는 concept §12 F1~F5 (권고안 결정) |
| H8 | **작업 이력 메모리 · handoff · state 는 콜사인별**로 관리한다 (kit 의 브랜치별 네임스페이스를 대신한다). task 는 프로젝트 공용 — 세부는 concept §13 G1~G3 (권고안 결정) |
| H9 | **콜사인 등록 정보(`.workflow-hub/`)는 `.gitignore` 에 넣는 규칙** — 부트스트랩퍼가 추가하고 `git check-ignore` 로 확인, 무시되지 않으면 토큰을 쓰지 않는다 |
| H10 | **부트스트랩퍼 등 필요한 도구는 허브가 원격 MCP 로 제공**한다 — 로컬 파일 쓰기 · 등록 전 인증 · 토큰 전달 · 첫 등록은 concept §14 I1~I4 (권고안 결정) |
| H11 | **세션 시작 때 항상 허브와 저장소의 최신 상태를 확인**하는 규칙을 표준 규칙 층(모든 진입 파일)에 넣는다 — 확인 항목은 concept §4.2.3 |
| H12 | **2.0.0 준비** — 2.0 의 흐름은 허브 하나. 로컬 kit + git 흐름은 1.x 유지보수 줄 (D1 을 고침) |
| H13 | **1.x 프로젝트는 처음 2.0.0 을 쓸 때 부트스트랩이 전환으로 이끈다** — 감지 · 전환 계획 · 들여오기 · git 표식 (concept §16.1) |
| H14 | **compact 직후에도 허브를 확인하고 기록된 작업을 이어 간다** — 체크포인트는 허브 콜사인 공간, hook 이 있으면 선택 로컬 클라이언트, 없으면 지침 (concept §4.2.4) |

### 세부 결정 (D1~D11, concept §10)

- D1 ~~허브 모드는 프로젝트가 켠다~~ → 2.0 은 허브 단일, 1.x 유지보수 (H12) · D2 허브 하나에 여러 프로젝트 · D3 진입 규칙만 필수 (플러그인 · hook 선택)
- D4 닿지 않으면 로컬 보낼편지함, 충돌은 409 · D5 A2A · 유휴 점검은 첫 판 제외 · D6 git 내보내기는 선택
- D7 arcturus 의 task · handoff 는 kit 허브로 옮긴다 · D8 로드맵 · WBS 는 허브로 · D9 PURPOSE 명제 문구 (concept §10)
- D10 허브가 쓴 진입 파일은 커밋 (판 대조, 직접 수정 시 멈춤) · D11 지침 편집은 권한 콜사인, 에이전트 변경은 제안 → 사람 승인
- E1~E6 위키 · F1~F5 등록 · 식별 · G1~G3 콜사인 기억 · I1~I4 MCP — concept §15 요약

### requirements · design 결정 (2026-11-20 ~ 21)

- requirements Q1~Q10 (요구 §20): 1.x 전환 같은 ID 정본 = 마지막 커밋이 가장 늦은 브랜치 · 브랜치 기록 원문 보관 · `human` 콜사인은 소유자 승인 · **화면 인증 = arcturus 과제 대시보드 방식** (로그인 없음, 브라우저 콜사인 · Bearer · 공용 `web` 토큰 기본 꺼짐) · 저장소 확인은 명령을 내주고 결과 대조 · 1.x 2028-07-20 까지 결함 수리 · 참조 못 하는 하네스(Antigravity)는 사용자 범위 토큰 · **지원 하네스 4종 Claude Code · Codex · MiniMax Code · Antigravity** · PURPOSE 2.0판은 이 ADR Accepted 때 적용 · 2.0 은 같은 이름의 kit 플러그인 채널을 내지 않음.
- design DS1~DS9 (스펙 §10): MCP 공식 SDK + `workflow_kit[hub]` · task 계획은 1.x Plan 원문 · 새 task ID 네임스페이스 = 콜사인 · 등록 직후 셋업 도구만 `token` 인자 · HTTP API = MCP 도구 거울 · 2.0 표준 규칙 정본 `core/hub_workflow_standard.md` · 콜사인은 프로젝트마다 · 주소 대소문자는 대형 호스트만 소문자 · 표식 `ai-workflow/HUB_MIGRATED.json`.
- 실측 근거 (요구 §16): 판정 핵심은 데이터로 부를 수 있다 (리팩터는 상태 생성 입력 층) · 위키 검사는 펼친 디렉터리에서 같은 판정 · 4종 원격 MCP 실측 (Antigravity 는 헤더 환경 변수 참조 미지원).

## Consequences

- **2.0.0 으로 낸다** (H12). PURPOSE 를 2.0판(`purpose_version: 2`)으로 적용했다 (2026-11-21, Q9) — 1.x 분기 브랜치의 PURPOSE 는 v1 그대로.
- 1.x 프로젝트는 2.0 부트스트랩의 전환 과정으로 옮긴다 (H13). 1.x 유지보수 판은 '허브로 옮김' 표식에서 쓰기를 거절하고 2.0 을 안내한다.
- 새 표면: 허브 서버(표준 라이브러리 HTTP + SQLite) · **원격 MCP** · 얇은 클라이언트(선택) · 지침 렌더링 · 허브 화면(워크벤치 확장) · 들여오기 / 내보내기.
- 지켜야 할 것: 생성물 형식(`state.json` v1 · `roadmap_state` v1 · `workbench-state/1` · `workflow-kit-plan-response/1`)은 허브가 같은 형식으로 낸다 · 로컬 흐름은 1.x 유지보수 줄에서 그대로 (G3 의 범위는 1.x, 2.0 은 major — H12).
- kit 이 서버 운영(백업 · 업그레이드 · 노출)의 기본값과 가이드를 떠안는다. 배치는 프로젝트 몫이다.

## Alternatives

- git 정본 + 허브는 모아 보기 / 프로젝트가 정본을 고름 — H1 에서 버림.
- kit 은 규약 + 클라이언트만, 서버는 프로젝트가 (Go 포털이 참조 구현) / Go 포털을 kit 으로 이전 — H2 에서 버림.
- 작업 환경마다 kit 설치 (arcturus 의 지금) — H4 에서 버림.
- 지침 정본 = 저장소 main 의 파일, 허브는 나르기만 (arcturus 브리핑) — H5 에서 버림.
