# 호스트 역할 — 개발 참여자와 읽기 전용 소비자

- 문서 목적: 이 저장소를 클론한 호스트가 **개발 참여자**인지 **읽기 전용 소비자**인지 가르고, 소비자가 pull · 업데이트 때 할 일과 하지 말 일을 정한다.
- 범위: **이 저장소(워크플로우 킷 원본) 한정** — 역할 표식(`git config workflow.role`), 미선언 호스트 처리, 소비자 업데이트 절차, 개선 제안 경로, pre-push 차단. 킷을 설치해 쓰는 다른 프로젝트에는 적용되지 않는다.
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-11-20
- 관련 문서: [`FEEDBACK.md`](./FEEDBACK.md), [`../CLAUDE.md`](../CLAUDE.md), [`../AGENTS.md`](../AGENTS.md), [`RELEASE.md`](./RELEASE.md) §2.8, [`INSTALLATION_AND_USAGE.md`](./INSTALLATION_AND_USAGE.md) §7.0, [`LOCAL_GATE.md`](./LOCAL_GATE.md)

## 1. 두 역할

| 역할 | 표식 | 하는 일 | 하지 않는 일 |
|---|---|---|---|
| 개발 참여자 | `contributor` | 코드 · 문서 변경, task · 메모리 갱신, 게이트, 커밋 · push, 발행 | — |
| 읽기 전용 소비자 | `consumer` | pull(fast-forward 만), 로컬 환경 맞추기, 버전 업데이트 | 추적 파일 변경, 커밋, push, 브랜치 작업, task · 메모리 갱신, 발행 |

이 구분은 **이 저장소에만** 있다. 소비자는 이 워크플로우를 자기 프로젝트에 설치해 쓰는 쪽이고, 이 저장소는 **킷을 설치 · 갱신하는 원본**으로만 쓴다. 자기 프로젝트에서 킷을 쓰며 메모리 · 문서를 쓰는 것은 이 문서와 무관하다.

소비자가 워크플로우 코드 · 문서에서 고칠 것을 찾아도 **이 클론에서 수정 · 커밋 · push 하지 않는다** — §4.1 의 이슈로 보낸다. 반영은 참여자 호스트의 일이다.

## 2. 역할 표식

역할은 클론마다 git 로컬 설정에 둔다. `.git/config` 에만 남아 커밋 · push 되지 않고, 같은 클론의 worktree 끼리 공유된다.

```bash
git config --get workflow.role          # 확인 — consumer / contributor / (빈 출력 = 미선언)
git config workflow.role consumer       # 소비자로 선언
git config workflow.role contributor    # 참여자로 선언
```

**pull · 업데이트 전에 먼저 확인한다.** 미선언이면 **멈추고 소유자에게 역할을 묻는다**. 답을 받으면 위 명령으로 선언한 뒤 진행한다 — 추측해서 진행하지 않는다. 한 번 선언하면 다시 묻지 않는다.

`consumer` · `contributor` 외의 값은 미선언과 같이 다룬다(멈추고 묻는다).

## 3. 소비자 업데이트 절차

순서대로 한다. 어느 단계든 예상과 다르면 **멈추고 보고한다** — 고쳐서 넘어가지 않는다.

### 3.1 시작 전 — 트리 확인

```bash
git status --porcelain
```

- 비어 있으면 3.2 로.
- 하네스의 세션 시작 hook 이 생성물(`ai-workflow/memory/active/**/state.json` · `roadmap/roadmap_state.json`)의 날짜를 다시 쓸 수 있다 — 이 둘의 `generated_at` 한 줄 변경은 알려진 잔여다.
- 그 밖의 추적 파일 변경은 소비자가 만들 일이 없는 변경이다. 어느 쪽이든 커밋하지 말고 목록을 소유자에게 보고한 뒤, 지시가 없으면 `git stash push -m "consumer-residue-<날짜>"` 로 비켜 둔다(지우지 않는다 — `git checkout --` · `git reset --hard` · `git clean` 금지).

### 3.2 pull — fast-forward 만

```bash
git switch main
git pull --ff-only origin main
```

- fast-forward 가 안 되면(로컬 커밋이 있거나 갈라짐) 병합 · rebase · 강제 갱신을 하지 않는다. 그대로 멈추고 `git log --oneline origin/main..HEAD` 를 소유자에게 보고한다.
- 특정 발행 버전에 고정하려면 `git switch --detach v<X>.<Y>.<Z>` (태그는 [Releases](https://github.com/ykylee/standard_ai_workflow/releases)).

### 3.3 로컬 환경 맞추기

```bash
git config core.hooksPath .githooks     # 한 번 — push 차단 hook 을 켠다 (§4)
python3 -m venv .venv                   # .venv 가 없을 때만
.venv/bin/python3 -m pip install -r requirements.txt
.venv/bin/python3 -m pip install -e "./workflow-source[mcp-sdk]"
```

Windows 는 `.venv\Scripts\python.exe`, 하네스 호출은 `python -m workflow_kit` (wk.exe 는 백신이 막는다).

### 3.4 버전 업데이트 — 소비 채널 재적용

[`RELEASE.md`](./RELEASE.md) §2.8 의 채널별 명령으로 이 호스트에 깔린 하네스(claude-code · codex · grok-build · antigravity · minimax-code)를 새 버전으로 맞춘다. 깔리지 않은 채널은 건너뛴다.

### 3.5 확인

```bash
.venv/bin/python3 -c "import workflow_kit; print(workflow_kit.__version__)"
.venv/bin/python3 -m workflow_kit doctor --json
```

- `content_drift.behind` 와 `disabled` 가 `[]` 여야 한다.
- `runtime_load.stale_hosts` 에 프로세스가 남아 있으면 그 하네스 CLI 를 재시작한다(`/clear` 로는 안 된다).

### 3.6 끝 — 트리가 그대로인지

```bash
git status --porcelain
```

비어 있어야 한다. 무언가 생겼으면 커밋하지 말고 보고한다.

## 4. 소비자가 하지 않는 일

- 추적 파일 편집, 커밋, push(`--no-verify` 포함), 브랜치 · 태그 생성, 병합 · rebase
- `ai-workflow/` 메모리를 쓰는 명령 — `session-start` · `backlog-update` · `refresh-state` · `compact-checkpoint` · `plan-import` (이 저장소 안에서. 소비자가 *자기 프로젝트*에서 킷을 쓰는 것은 별개다)
- 게이트 · 발행 — `run_all_checks.py`, `release`, `release-dist`
- 결함 수리 · 개선 반영 — §4.1 로 보낸다

`.githooks/pre-push` 는 `workflow.role=consumer` 인 클론의 push 를 **모두 막는다** (`workflow_kit.common.gate_evidence`). 에이전트가 이 문서를 놓쳐도 push 는 나가지 않는다 — 단 `core.hooksPath` 가 켜져 있어야 한다(§3.3).

### 4.1 고칠 것을 찾았을 때 — 이슈로

[`FEEDBACK.md`](./FEEDBACK.md) 의 GitHub Issues(bug / enhancement, `consumer-feedback` 라벨)로 낸다. 본문에 담는 것:

- 재현 명령과 실제 출력, 기대 결과
- 킷 버전(`python3 -c "import workflow_kit; print(workflow_kit.__version__)"`) · OS · 하네스
- 고치는 방법을 안다면 **제안 diff 를 본문에 텍스트로** — 이 클론에 적용하지 않는다

이미 로컬에서 고쳐 버렸다면 `git diff > <이 저장소 밖 경로>/proposal.patch` 로 이슈에 첨부할 사본을 만들고, `git stash push -m "consumer-proposal-<날짜>"` 로 트리를 되돌린다(지우지 않는다). 그다음 §3 을 이어간다.

## 5. 참여자

참여자의 흐름은 [`../CLAUDE.md`](../CLAUDE.md) 그대로다 — `session-start` 로 시작하고, 게이트 통과 기록이 있는 커밋만 push 한다.

역할이 바뀌면 `git config workflow.role <새 역할>` 로 다시 선언한다.
