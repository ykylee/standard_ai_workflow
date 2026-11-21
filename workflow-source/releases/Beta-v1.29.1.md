# Beta v1.29.1 (2026-11-21)

> **상태: 릴리스 준비.** package `1.29.1`, runtime `__version__ = 1.29.1`, tag `v1.29.1`.
> **patch release (1.x 결함 수리 줄 · `release/1.x` 머리에서 발행 — hub_spec R16.5)** — 오래 사는 브랜치의 메모리가
> 기본 브랜치에 합쳐질 때마다 반영 · 아카이브되던 결함을 막는다.
>
> 등급 근거 (§1.5 · R16.1 · R16.2): v1.29.0 이후 코드 커밋 1 — fix 1, feat 0, breaking 0 — **patch**.
> 공개 Python API 시그니처 제거 0, 진입점 제거 0. 상수 `archive_branch_memory.LONG_LIVED_MARKER` 는 **추가**다.
> **동작이 바뀌는 곳 하나**: `active/<branch>/.long-lived` 표시가 있는 브랜치는 git 에 브랜치가 있는 동안
> 기본 브랜치에 병합돼 있어도 `session-start` · `archive-branch-memory` 가 반영 · 아카이브하지 않는다.
> 표시가 없는 브랜치는 이전 동작 그대로다.

## 0. 릴리스 판정

`release/1.x` 분기(R16.5) 뒤 첫 1.x patch 다. 소유자 분류 (2026-11-21) — R16.1 ② 저장소 오염 결함.
소비 저장소에서 실측했다: 기본 브랜치 체크아웃의 `session-start` 가, 계속 쓰이면서 몇 시간마다 기본 브랜치에 합쳐지는
작업 브랜치의 네임스페이스를 '종료' 로 보고 125 개 파일을 `archived/` 로 옮기고 task 89 건을 반영했다 (커밋 전에 되돌렸다).
그대로 커밋되면 그 브랜치의 다음 병합이 아카이브된 경로와 충돌하거나 기록이 엉뚱한 곳에 쌓인다.

## 1. 릴리스 요약

- 범위: `v1.29.0..` **1 commit** — fix 1 (`7178acd9`, PR #31) (+ 메모리 · 세션 커밋 — `release/1.x` 브랜치 메모리 seed `e16ce897` · 발행 준비 1).
- 누적 smoke **333/333 PASS** (로컬 `--branch-context=all` = 333 × native/slash).
- 검사 파일 수 333 → 333 (`check_branch_join_reflect` 10 → 12 cases).
- 같은 수리가 2.0 줄(`main`)에도 들어갔다 — PR #32 (R16.5 1.x → 2.0).

## 2. 소비자에게 보이는 변화

### 2.1 오래 사는 브랜치 표시 `.long-lived` (`7178acd9`, `core/multi_workspace_orchestration.md` 합류 반영 절)

- 브랜치를 계속 쓰면서 기본 브랜치에 자주 합치면, 그 브랜치가 자기 네임스페이스에 `active/<branch>/.long-lived` 를 커밋한다
  (내용 자유 · 첫 줄 = 사유).
- 표시가 있고 git 에 브랜치가 있으면 브랜치 tip 이 HEAD 에 병합돼 있어도 합류 반영 · 아카이브하지 않는다.
  `archive-branch-memory` 결과에서 그 브랜치는 `skip` 이고 사유에 표시가 나온다.
- 브랜치가 git 에서 사라지면 표시와 관계없이 평소대로 종료로 본다 — 끝낼 때는 브랜치를 지우거나 표시를 지운다.
  명시적으로 고른 브랜치(`--branch`)는 표시보다 앞선다.

## 3. 검증

- **전량 게이트** `--branch-context=all` — native 333/333 · slash 333/333 · rc 0. 결과는 게이트 증거 파일(`<git common dir>/gate_evidence/<sha>.json`)에 남는다.
- **커밋 전** `--changed` 게이트 · **스모크** `check_self_application` 8/8.
- `check_branch_join_reflect` 12 cases — 새 case 9 (표시 → 병합돼도 유지) · 9b (브랜치 삭제 → 아카이브). 표시 판정을 빼면 case 9 가 red.
- 발행 호스트: macOS (MacBook Air).

## 4. 알려진 한계 (감추지 않는다)

- **표시는 사람이 둔다** — 브랜치 주인이 `.long-lived` 를 커밋하지 않으면 이전처럼 반영 · 아카이브된다. 표시를 둔 채 브랜치만 남겨 두면 그 메모리는 영원히 합류되지 않는다.
- **이 판 이전 킷은 표시를 모른다** — 기본 브랜치에서 `session-start` 를 돌리는 모든 호스트가 이 판 이상이어야 막힌다.
- 발행 준비 중 이 호스트의 MiniMax MCP 채널이 가리키는 주 체크아웃이 `origin/main` 보다 137 커밋 뒤처져 `check_mavis_attach_e2e` 가 red 였다 (도구 11 · `plan_inbox` 없음). 체크아웃을 앞으로 감아 고쳤다 — §2.8 재적용 누락의 한 예.
- **Windows 실측은 이번 판에도 없다** (M-028/WBS-28.3).
- **PyPI 업로드는 하지 않는다**(§1 각주 0 — 2026-08-14 소유자 최종 결정). 배포는 GitHub Releases 하나다.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-11-21T03:55:29Z)_

- total wiki pages: **99**
- total memory entries: **30**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
