# Beta v1.20.0 (2026-10-06)

> **상태: 릴리스 준비.** package `1.20.0`, runtime `__version__ = 1.20.0`, tag `v1.20.0`.
> **minor release** — 진입점이 가벼워진다. 새로 만드는 진입점은 처음부터 작고, 이미 채택한 프로젝트의 진입점은
> `ensure-entrypoints --diet` 로 kit 가 생성한 그대로인 절만 줄인다. MiniMax Code 가 소비 채널로 추가된다.
>
> 등급 근거 (§1.5): `wk release-status` 의 파생 근거는 feat 4 · fix 4 · breaking 0 — **minor**.
> 공개 Python API 는 **추가만** 있다 — `workflow_kit.common.entry_diet` · `bootstrap_lib.harnesses.entry_sections` ·
> `workflow_kit.minimax_plugin` (신규 모듈), `workflow_writes.PLAN_HEADING`, `ensure_entrypoints.diet`.
> 진입점 증감 0. 인자 추가: `ensure-entrypoints --diet`, `backlog-update --plan-file / --plan-step / --plan-risk /
> --plan-proof` (`--replace-field plan_*`).
>
> **동작 변경**: 진입점 · 스킬에 생성 주입되는 정본 규칙 블록의 문구가 짧아졌다(규칙은 같다). 새 task 파일에
> `## 🧭 Plan` 절이 생긴다 — 리더는 모르는 절을 무시하므로 옛 kit 도 읽는다.

## 0. 릴리스 판정

진입점(CLAUDE.md · AGENTS.md · GROK.md …)은 세션마다 통째로 컨텍스트에 실린다. 이 저장소의 CLAUDE.md 는 자체 예산
12,288B 에 104B 를 남기고 있었고, 신규 bootstrap 진입점도 7~10KB 였다. Anthropic "The AI-native SDLC playbook"
(2026-08-21) 은 CLAUDE.md 를 "under a page" 로 두라고 한다 — 그 검토(`docs/planning/ai-native-sdlc-playbook-review-2026-10.md`)
에서 소유자가 고른 적용 3건과 진입점 다이어트 3단계를 함께 발행한다.

## 1. 릴리스 요약

- 범위: `v1.19.0..` 발행 준비 직전까지 **20 commit** — 세션 기록 · 발행 마무리 · 병합 커밋을 빼면 실질 **13 commit**
  (이 세션 6 · 다른 세션 7: MiniMax 채널 · 플러그인 문서 정정 · 테스트 관찰 경로 수리 4 · 아카이브 판정 수리).
- 누적 smoke **309/309 PASS** (로컬 `--branch-context=all` = 309 × native/slash).
- 검사 수 **302 → 309** (신설 7: `check_task_plan_section` · `check_verifier_agent` · `check_guard_check_weakening` ·
  `check_entry_budget` · `check_entry_diet` · `check_minimax_plugin_channel` · `check_session_start_observation`).

## 2. 소비자에게 보이는 변화

### 2.1 진입점 다이어트 (TASK-2026-10-06-main-002 ~ 004)

- **정본 규칙 블록** (`062c4d64`): 모든 진입점 · 스킬에 들어가는 §1 원칙 · §8 종료 순서 · §11 명령/계약을 3,635B →
  2,740B 로. 규칙은 그대로, "왜 그런가" 는 렌더되지 않는 정본 본문으로 옮겼다.
- **bootstrap 템플릿** (`b575b670`): 렌더러 5곳에 손으로 복제돼 있던 "Read these first" · 언어 절을
  `bootstrap_lib/harnesses/entry_sections.py` 정본으로 모으고 줄였다(경로 목록 대신 session-start 를 가리킨다).
  메타데이터와 겹치던 Purpose 절, CLAUDE.md 상용구(이 파일의 역할 · self-bootstrap · Read next), GROK.md 의 반복
  사실을 걷었다. 신규 진입점: CLAUDE.md 7,758→5,020B · AGENTS.md 7,044→5,407B · GROK.md 10,532→6,663B.
  하네스별 진입점은 `ENTRY_BUDGET_BYTES`(8KB) 이하가 검사로 고정된다.
- **기존 진입점** (`14fd87be`): `python -m workflow_kit ensure-entrypoints --diet` 가 진입점을 `## ` 절 단위로 판정한다.
  과거 kit 버전이 **생성한 그대로**인 절(발행 태그 11개를 실제로 bootstrap 해 채취한 해시)은 현행 템플릿 절로
  교체하거나 걷고, 본문이 다른 절(사용자 편집 · 프로젝트 값)은 보존한다 — 걷힌 제목이면 `edited` 로 보고한다.
  `--apply` 일 때만 쓰고, 포크 선언 파일은 보고만 한다. v1.19.0 으로 만든 CLAUDE.md 7,636→5,107B · GROK.md
  10,410→6,663B.

### 2.2 작업 전 계획 기록 (`d8bbf1e4`, TASK-2026-10-05-main-002)

task 파일에 `## 🧭 Plan` 절 — 바뀌는 파일 · 작업 순서 · 위험 · 검증 방법. `backlog-update --plan-*` 로 쓰고(기본 병합,
`--replace-field plan_*` 교체), 절이 없는 옛 task 는 update 가 끼워 넣는다. 정본 §1 원칙이 계획을 task 파일에 남기라고
지시한다 — 대화가 compact · 세션 경계에서 사라져도 계획이 남는다.

### 2.3 MiniMax Code 소비 채널 (`d8e4ebee`, 다른 세션)

`.minimax-plugin/plugin.json` 매니페스트(스킬 목록은 정본 파생) · 아이콘 · 로컬 sync(`workflow_kit/minimax_plugin.py`,
기본 dry-run · 기존본 백업 · 멱등) · 릴리스 ZIP.

### 2.4 이 저장소 운영 (wheel 에는 실리지 않는다)

- verifier subagent `.claude/agents/verifier.md` — task 를 done 으로 닫기 전 완료 기준을 새 컨텍스트에서 다시 잰다
  (읽기 계열 도구만, 미측정은 통과가 아니다). 대역 실측에서 mypy strict 회귀를 실제로 잡았다.
- 검사 약화 차단 hook `.claude/hooks/guard_check_weakening.py` — `git push --no-verify` · `run_all_checks --no-lock` ·
  `gate_evidence/` 쓰기를 이유와 함께 막는다. 판정은 셸 토큰 단위(따옴표 안의 언급은 명령이 아니다).
- CLAUDE.md 12,184B → 6,838B.

### 2.5 수리 (다른 세션)

- `archive-branch-memory`: 브랜치 오버라이드가 기본 브랜치여도 실제 checkout 브랜치는 합류 반영 · 아카이브하지
  않는다 (`f1a4b633` — worktree 에서 게이트가 자기 브랜치 메모리를 옮기던 것).
- 자기 적용 관찰 검사들이 저장소를 쓰지 않는 공용 헬퍼로 session-start 를 부른다 (`ed9eb423` · `582763f4` ·
  `4b1b5256` · `e98bc3a6`).

## 3. 검증

- 전량 게이트 `--branch-context=all` — 발행 준비 커밋에서 실행 (결과는 발행 기록에 남긴다)
- 해석기 매트릭스 3.11 · 3.13 각 309/309
- 신설 검사마다 결함 되주입 — Plan 5 · verifier 5 · guard 4(1건은 동치 변형) · 예산 3 · diet 6 건, 각 해당 case red

## 4. 알려진 한계 (감추지 않는다)

- `--diet` 뒤에도 진입점의 버전 마커는 옛 값이다 — 편집된 절이 남을 수 있어 현행 생성물이라 주장하지 않는다.
- 새 발행이 템플릿을 바꾸면 `scripts/harvest_entry_sections.py` 를 다시 돌려야 그 버전 생성물을 알아본다(안 돌리면
  그 절을 보수적으로 남길 뿐이다).
- verifier subagent 의 실제 로드(도구 제한 포함)는 Claude Code 재시작 뒤 실측 대기 (TASK-2026-10-05-main-003).
- Windows 실물(cp949 · `python -m workflow_kit`)은 여전히 실측 대기 (TASK-2026-10-02-main-006 · 007).
