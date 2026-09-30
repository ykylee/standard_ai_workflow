---
type: decision
status: accepted
adr_id: ADR-030
decided_at: 2026-09-30
alternatives_considered: [markdown-checkpoint, root-gitignore-entry, separate-commands-per-mode, skill-named-compact, restore-on-startup, ship-hooks-to-codex-now]
related_pages: [decisions/adr-029-session-context-budget, decisions/adr-027-roadmap-wbs-sdlc]
created: 2026-09-30
updated: 2026-09-30
r9_skip: true
---

# ADR-030: compact 중계 — 압축 경계를 워크플로우 메모리로 건너뛴다

## Status

**Accepted** (2026-09-30 소유자 승인 — requirements 대비 변경 두 건(`checkpoint.json` · 스킬 이름 `compact-relay`) 포함, requirements sign-off 를 받은 design 단계 — TASK-2026-09-30-main-005,
M-020/WBS-20.1). requirements 정본은 `docs/planning/compact-relay-requirements-2026-09.md`,
kit 계약 정본은 `workflow-source/core/compact_relay_spec.md`. 이 페이지는 결정과 근거만 적는다.

## Context

하네스가 컨텍스트를 압축하면 요약이 "확인했다 / 아직 안 확인했다" 의 구분과 다음 한 걸음을 잃을 수
있다. Claude Code 2.1.285 실측(concept §2.1 · requirements §1): `PreCompact` 는 `trigger` ·
`custom_instructions` 를, `PostCompact` 는 요약 원문 `compact_summary` 를 주고, 압축 직후
`SessionStart(source=compact)` 의 stdout 은 컨텍스트에 들어간다 — 플러그인 배포 hook 도 같다. hook
출력은 ≈10,000 **자**를 넘으면 앞 2KB 미리보기만 남는다.

requirements sign-off 가 고정한 것: 명령 하나(모드 5개) · hook 3 · 스킬 1 · 워크트리 로컬 비커밋
checkpoint · 재주입 4,096 바이트 · 식별자형 누락 대조 · 자동 압축도 기계 층 기록 · 오래된 checkpoint 는
표시 후 주입 · handoff / `state.json` 무쓰기 · hook exit 0.

design 이 정할 것: 모듈 배치 · 워크플로우 밖 프로젝트의 hook 동작 · gitignore 보장 주체 · 파일 형식 ·
세션 식별 · 예산 편입 · §11.1 문구와 스킬 · 검사.

## Decision

1. **모듈은 둘이다.** 계약 로직(형식 · 합치기 · 대조 · 재주입 렌더 · 절단)은
   `workflow_kit/common/compact_relay.py`, CLI 는 `workflow_kit/tools/compact_checkpoint.py` 이고
   `common/tool_dispatch.py` 에 `compact-checkpoint` 로 등록한다. 검사와 예산 측정은 `common` 쪽을 import 한다.
2. **워크플로우 밖에서는 아무것도 하지 않는다.** 플러그인은 사용자 전역에 설치되므로 hook 은 모든
   프로젝트에서 돈다. workspace 는 hook 입력의 `cwd` → 없으면 그 `git rev-parse --show-toplevel` 순서로
   찾고, 그 아래 `docs/PROJECT_PROFILE.md` 로 해석한 메모리 디렉터리가 **없으면 출력 없이 exit 0**, 파일을
   만들지 않는다. 브랜치 디렉터리는 기존 `workflow_branch_dir` 를 쓴다.
3. **gitignore 는 도구가 스스로 보장한다.** `.compact/` 를 만들 때 그 안에 `*` 한 줄짜리 `.gitignore` 를 함께
   쓴다 — 디렉터리가 자기 자신을 무시한다 (이 저장소에서 `git check-ignore` 로 확인: 상위의
   `!/ai-workflow/memory/` 재포함 규칙 아래에서도 무시된다). 소비자 루트 `.gitignore` 를 bootstrap 이
   건드리지 않아도 되고, 이미 bootstrap 된 프로젝트에도 재적용 없이 성립한다.
4. **checkpoint 는 JSON 이다 — `.compact/checkpoint.json`** (requirements 의 `current.md` 를 바꾼다).
   쓰는 쪽이 도구뿐이므로(스킬도 `--note` 인자로만 쓴다) 사람이 읽을 형식이 필요 없고, markdown 이면
   파서 경계가 또 하나 생긴다 — handoff 가 산문 한 줄로 `state.json` 을 조용히 오염시킨 선례와 같은
   자리다. 사람이 읽는 형식은 `--restore` 출력이 전부다. 요약 원문은 `.compact/summary.md` (텍스트 그대로).
5. **세션 식별은 "대기 중인 판단 층" 으로 한다.** 스킬(모델)은 `session_id` 를 모른다. `--note` 는 판단 층을
   `pending: true` 로 쓰고, 다음 `--hook pre` 가 자기 `session_id` 로 그것을 **인수**한다. `pending` 이 아니고
   `session_id` 가 다른 checkpoint 는 `--hook pre` 가 새로 시작하고, `--restore` 는 본문 없이 불일치만 알린다.
   한 워크트리 동시 세션은 지원하지 않는다 — `CLAUDE.md` 의 "두 에이전트는 워크트리를 나눈다" 를 따른다.
6. **재주입 예산은 `context_budget.BUDGETS` 에 레코드로 올린다** — key `compact_reinjection`, 4,096 바이트,
   강도 red. 측정은 현재 checkpoint 로 `--restore` 를 렌더한 크기이고 checkpoint 가 없으면
   `measured=False`. 절단은 렌더러가 하므로 초과는 **절단 로직의 회귀**를 뜻한다.
7. **§11.1 에 한 줄**: `Relay working state across a context compaction` | `wk compact-checkpoint`. 생성 블록은
   정본을 고치고 재생성한다 (`_standard_rules_snapshot.py` 포함).
8. **스킬 이름은 `compact-relay`** 다. `compact` 는 하네스 내장 `/compact` 와 같은 이름이라, 사용자가 스킬을
   부르려다 압축을 실행하거나 그 반대가 된다. 스킬 본문은 §6 절차 셋(기록 → `/compact` 지시문 제시 → 압축 뒤
   머리말 확인)이다. `session-end` 스킬 본문에 한 단계: checkpoint 에서 남길 줄을 handoff 로 옮기고 `--clear`.
9. **hook 은 `render_claude_code_hooks` 에 셋을 더한다** — `PreCompact` · `PostCompact` (matcher 없음) ·
   `SessionStart(matcher=compact)`. `wk` 부재 시 **조용히** 끝난다 (`… || true`) — 부재 안내는 기존
   SessionStart hook 이 이미 한다. 같은 JSON 이 Grok 사본으로 나가고, Grok 은 재주입이 없다는 선언은
   스펙 §하네스 표와 `plugin_payload` 주석에 둔다. Codex manifest 에는 hooks 를 싣지 않는다 (미실측).
10. **검사는 `check_compact_relay.py` 하나**, requirements R7 의 case 마다 결함 되주입으로 red 를 확인한다.
    실제 하네스 왕복(`claude -p`)은 인증·비용이 필요해 게이트에 넣지 않고, 스펙에 실측 기록으로 남긴다.

## Alternatives Considered

| 대안 | 기각 이유 |
|---|---|
| markdown checkpoint (`current.md`) | 쓰는 쪽이 도구뿐인데 파서 경계를 하나 더 만든다. 사람이 읽을 출력은 `--restore` 가 이미 낸다 |
| 루트 `.gitignore` 에 항목 추가 (bootstrap) | 기존 소비자는 재적용 전까지 무방비 — 첫 checkpoint 가 커밋될 수 있다. 자기 무시 디렉터리는 쓰는 순간 성립한다 |
| 모드마다 명령 분리 | requirements Q1 에서 기각 — §11.1 이 다섯 줄 늘고 스킬 1:1 규약과 어긋난다 |
| 스킬 이름 `compact` | 하네스 내장 명령과 충돌 |
| 새 세션 `startup` 에서도 재주입 | 세션 경계는 handoff 가 정본이다. 압축은 **같은 세션** 안의 경계라서 checkpoint 가 필요한 것이다 |
| Codex 에 지금 hooks 적재 | 플러그인 hook 적재 · 입력 필드(`custom_instructions` 부재) 미실측. 실측 leaf 로 뺀다 |

## Consequences

- 플러그인 스킬이 5종이 된다 — `PLUGIN_DESCRIPTION` 의 개수는 파생이라 자동으로 바뀐다. 설명 문구의
  나열("세션 시작 / 백로그 갱신 / …")은 손으로 한 항목을 더한다.
- `CLAUDE.md` 가 §11.1 한 줄만큼 커진다 (현재 11,341 / 12,288 바이트).
- 전역 설치된 플러그인이 워크플로우 밖 프로젝트에서 압축마다 `wk` 를 한 번 띄운다 — 결정 2 로 출력·파일은 없다.
- 자동 압축에서는 판단 층이 없다. 재주입 머리말이 그것을 말하므로 모델이 "기록이 전부" 라고 오해하지 않는다.
- 자동 압축 경로와 Codex 는 미실측으로 남는다 (requirements R9).

## References

- `docs/planning/compact-relay-review-2026-09.md` (concept, §9 결정)
- `docs/planning/compact-relay-requirements-2026-09.md` (requirements, §11 sign-off)
- `workflow-source/core/session_context_budget_spec.md` — 예산 레코드 계약
- `workflow-source/workflow_kit/plugin_payload.py` — 스킬 · hook 파생
