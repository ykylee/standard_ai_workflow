# Beta v1.18.0 (2026-10-02)

> **상태: 릴리스 준비.** package `1.18.0`, runtime `__version__ = 1.18.0`, tag `v1.18.0`.
> **minor release** — worktree 가 모 브랜치로 **돌아올 때** 그 기록이 모 브랜치 메모리에 남는다.
>
> 등급 근거 (§1.5): `wk release-status` 의 파생 근거는 feat 1 · fix 0 · breaking 0 — **minor**.
> 공개 Python API 는 **추가만** 있다 — `workflow_kit.common.branch_join` (신규 모듈),
> `branch_inheritance.handoff_line` · `insert_frontmatter_line`, `archive_branch_memory` 의 `branch_ref` ·
> `merged_into_head` · `short_sha`. `wk archive-branch-memory` 에 인자 `--no-reflect` (기본은 반영). 진입점 증감 0.
>
> **동작 변경**: 기본 브랜치 체크아웃에서 `session-start` 와 `wk archive-branch-memory` 가 **HEAD 에 병합된**
> 브랜치 네임스페이스를 — 브랜치·worktree 가 git 에 살아 있어도 — 모 브랜치 메모리에 반영하고 아카이브한다.
> 이전에는 git 에서 사라진 브랜치만 대상이었고, session-start 는 안내만 했다.

## 0. 릴리스 판정

v1.17.0 은 worktree 가 모 브랜치 맥락을 **이어받게** 했다. 반대 방향 — worktree 작업이 모 브랜치로 돌아올 때
기록이 따라오는 것 — 은 손일이었다 (110·111차: main 세션이 강제 아카이브하고 handoff 포인터를 손으로 적었다).
두 방향이 다 있어야 worktree 세션이 메모리 왕복을 끊김 없이 한다.

## 1. 릴리스 요약

- 범위: `v1.17.0..` 발행 준비 직전까지 **3 commit** — 발행 마무리 1건(`e543e589`, v1.17.0 몫)과 세션 기록
  1건을 빼면 실질은 **1 commit** (`82fece56`).
- 누적 smoke **300/300 PASS** (로컬 `--branch-context=all` = 300 × native/slash).
- 검사 수 **299 → 300** (신설 1: `check_branch_join_reflect`, 5 cases).

## 2. 소비자에게 보이는 변화

### 2.1 worktree 합류 반영 (`82fece56`, TASK-2026-10-02-main-004)

worktree 브랜치가 모 브랜치(기본 브랜치)에 병합되면, 그 체크아웃에서 다음 `session-start` 가 브랜치 메모리를
모 브랜치 메모리에 옮기고 아카이브한다. 무엇을 했는지는 warning 으로 말하고, 변경은 그 브랜치의 다음 커밋에 실린다.

- **이어받은 task**(v1.17.0) 중 worktree 에서 고친 것 → 원본에 되돌려 적고 모 브랜치 handoff 의 진행·차단·완료
  목록을 그 status 로 옮긴다.
- worktree **자체의 열린 task** → 같은 ID 로 모 브랜치에 이월. frontmatter 맨 앞 `merged_from: <branch>@<sha>`,
  아카이브되는 브랜치 사본에는 `carried_over_to`.
- worktree **자체의 완료 task** → 모 브랜치 handoff '최근 완료' (자동 seed 사건 task 는 뺀다).
- 모 브랜치 handoff §5 맨 앞에 합류 줄(브랜치@sha · 건수 · 아카이브 링크), `sessions/merge_<branch>_<date>.md` 합류 기록.
- 반영하지 않는 경우: 병합 뒤 브랜치가 더 나갔다 · 기본 브랜치가 아닌 체크아웃 · `--no-reflect` ·
  이월할 ID 가 모 브랜치에 이미 있다(막고 warning).

## 3. 검증

- 전량 게이트 `--branch-context=all` — 발행 준비 커밋에서 실행 (결과는 발행 기록에 남긴다)
- `check_branch_join_reflect` 5/5 — origin + clone + 살아 있는 `git worktree` 로 이어받기 → 작업 → fast-forward
  병합 → main session-start 왕복. 결함 되주입 9건 각 해당 case red
- 같은 시나리오 수동 E2E: 되돌려 적음 1 · 완료 1 · 이월 1 · §5 합류 줄 · 합류 기록, 두 번째 시작에 정합 경고 0 · 재반영 0

## 4. 알려진 한계 (감추지 않는다)

- **반영·아카이브 뒤 같은 worktree 에서 계속 작업해 다시 병합하면** 아카이브된 경로와 충돌한다 — 이어서 일할 때는
  새 브랜치로 시작한다 (소유자 결정: worktree 가 살아 있어도 아카이브).
- 모 브랜치는 기본 브랜치로 고정이다. origin 없는 저장소는 기본 브랜치 판정이 현재 브랜치로 떨어져 seed ·
  이어받기가 돌지 않는다 (`TASK-2026-10-02-main-003`).
- `TASK-2026-08-25-main-017` (MCP emit command 가 항상 `python3`) 는 blocked, minimax-code 채널
  (`TASK-2026-09-30-main-001`)은 planned 그대로다.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-10-02T03:02:12Z)_

- total wiki pages: **97**
- total memory entries: **30**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
