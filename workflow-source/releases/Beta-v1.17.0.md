# Beta v1.17.0 (2026-10-02)

> **상태: 릴리스 준비.** package `1.17.0`, runtime `__version__ = 1.17.0`, tag `v1.17.0`.
> **minor release** — worktree 가 **스스로 시작하고, 모 브랜치의 맥락을 이어받는다.**
>
> 등급 근거 (§1.5): `wk release-status` 의 파생 근거는 feat 1 · fix 3 · breaking 0 — **minor**.
> 공개 Python API 는 **추가만** 있다 — `workflow_kit.common.branch_inheritance` (신규 모듈),
> `common.git.short_head_sha`, `seed_workspace_memory.seed` 의 키워드 인자 `task_status` · `wbs_exempt_reason` ·
> `inherit_from` · `origin_sha` (기본값 — 기존 호출 그대로). 진입점 증감 0.
>
> **동작 변경 (계약 3)**: git 이 아닌 workspace 의 브랜치는 이제 `main` 이다 (이전: 모듈 저장소의 브랜치).
> CI 밖 detached HEAD 는 short sha 가 아니라 **기본 브랜치**로 해석한다 (CI 는 그대로 sha).

## 0. 릴리스 판정

하네스 데스크톱 앱은 세션마다 worktree 를 스스로 만든다 (Claude Code `claude/<name>`, Codex detached HEAD).
v1.16.0 까지 그런 worktree 에서 `wk session-start` 는 멈췄고, 이번 사이클의 첫 수리 뒤에도 모 브랜치의
맥락을 못 봤다. 두 수리가 합쳐져야 worktree 세션이 "어디서 이어 가는지" 를 안다.

## 1. 릴리스 요약

- 범위: `v1.16.0..` 발행 준비 직전까지 **14 commit** — 세션·메모리 기록 7건과 병합 1건을 빼면 실질은
  **6 commit** (`6118db3d` · `b963f22c` · `5d9b2228` · `306adeaf` · `bb1c6088` + 발행 마무리 `9d6c1436` 은 v1.16.0 몫).
- 누적 smoke **299/299 PASS** (로컬 `--branch-context=all` = 299 × native/slash).
- 검사 수 **298 → 299** (신설 1: `check_branch_memory_auto_seed`, 13 cases).

## 2. 소비자에게 보이는 변화

### 2.1 worktree 가 자기 네임스페이스로 시작한다 (`6118db3d`, TASK-2026-09-30-claude-session-start-e6eb83-002)

- `session-start` 가 브랜치 메모리(`active/<branch>/`)가 없으면 **스스로 seed** 한다 — 브랜치를 그 workspace 의
  git 에서 얻었고, 그 브랜치·legacy 평면 handoff 가 없고, 기본 브랜치 네임스페이스에 handoff 가 있을 때만.
  이전에는 `missing_required_document` 로 멈췄고, 이어진 `backlog-update` 가 state.json 만 만들어 메모리를 갈랐다.
- CI 밖 detached HEAD 는 기본 브랜치 네임스페이스로 시작한다 — sha 디렉터리(`active/6545f13/`)가 커밋마다
  고아가 되던 것.
- 로드맵 task 수집이 슬래시 브랜치(`active/claude/<name>/`)까지 센다 (`b963f22c` 가 형제 공유 디렉터리 오인 없음을 잰다).

### 2.2 worktree 가 모 브랜치의 내용을 이어받는다 (`bb1c6088`, TASK-2026-10-02-main-001)

자동 seed 는 빈 골격 handoff 에 산문 포인터만 남겨, worktree 세션이 "아직 작업 전" · `blocked=[]` 로 시작했다.
이제 seed 가 모 브랜치(기본 브랜치)의 내용을 **새 네임스페이스에 옮겨 적는다** — 모 브랜치에는 쓰지 않는다.

- 옮기는 것: handoff 의 현재 기준선 · 주 작업 축 · §5 다음 시작 포인트(앞머리 bullet), 열린 task(진행·차단·계획)를
  **같은 ID** 로. 옮긴 handoff 줄의 상대 링크는 새 위치 기준으로 다시 잡는다.
- **원류**: handoff §1 `원류: main@<sha>` (sha = seed 시점 HEAD), 옮긴 task frontmatter 맨 앞
  `inherited_from: main@<sha>` · `inherited_hash: sha256:<원문 해시>`. 두 줄을 걷으면 원문과 바이트가 같다.
- worktree 에서 `wk backlog-update --task-id <이어받은 ID>` 로 그대로 이어서 갱신한다.
- **합류**: `wk archive-branch-memory` 가 이동 전에 **고친 사본만** 원본 자리에 되돌려 적고 원본 daily index
  status 를 맞춘다. 원본이 그 사이 바뀌었으면 덮지 않고 그 브랜치를 막는다. 이어받은 사본은 '미완료 task'
  차단에서 빠진다.
- 로드맵 집계는 같은 ID 를 한 번만 센다 (안 고친 사본 = 원본, 고친 사본 = 사본).

### 2.3 게이트가 호스트 배치에 따라 red 이던 것 2건

- **meta-watch 가 저장소 안 worktree 를 좁은 선언 위반으로 잡던 것** (`5d9b2228`) — `.claude/worktrees/*` 처럼
  저장소 안에 worktree 가 있으면 main 체크아웃의 게이트가 구조적으로 통과 기록을 못 남겼다. 자기 `.git` 을 가진
  하위 디렉터리를 다른 작업 트리로 보아 판정에서 뺀다.
- **release-notes 템플릿 검사가 저장소 `releases/` 에 쓰던 것** (`306adeaf`) — 게이트의 저장소 write 감시가
  간헐로 잡았다. 임시 디렉터리 주입 + 저장소 전후 스냅샷 단언.

## 3. 검증

- 전량 게이트 `--branch-context=all` — 발행 준비 커밋에서 실행 (결과는 발행 기록에 남긴다)
- `check_branch_memory_auto_seed` 13/13 — 이어받기 case 5개는 결함 되주입 9건 각 해당 case red
- 임시 worktree 실측: 모 브랜치 차단 task · 기준선 · §5 · 원류 링크 노출, 이어받은 task 갱신(모 브랜치 불변),
  강제 아카이브의 되돌려 적기(안 고친 사본은 건너뜀) · 원본 변경 시 충돌 차단

## 4. 알려진 한계 (감추지 않는다)

- **모 브랜치는 기본 브랜치로 고정**이다 — feature 브랜치에서 딴 worktree 도 기본 브랜치를 이어받는다.
- 합류 때 모 브랜치 **handoff 목록**은 되돌려 적지 않는다 — 합류 뒤 첫 세션 종료가 맞춘다.
- 이어받은 `in_progress` task 는 모 브랜치에서도 진행 중일 수 있다 — 양쪽에서 고치면 합류 때 충돌로 막힌다.
- `TASK-2026-08-25-main-017` (MCP emit command 가 항상 `python3`) 는 blocked, minimax-code 채널
  (`TASK-2026-09-30-main-001`)은 planned 그대로다.
