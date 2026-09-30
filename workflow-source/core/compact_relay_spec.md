# compact 중계 스펙

- 문서 목적: 하네스의 컨텍스트 압축 전후로 작업 상태를 기록 · 대조 · 재주입하는 kit 계약(명령 · 파일 · 재주입 · 대조 · 스킬 · hook · 하네스 선언)을 정의한다.
- 범위: `wk compact-checkpoint` 모드 계약, `.compact/` 파일 계약, 재주입 출력과 예산, 요약 누락 대조, 플러그인 스킬 `compact-relay` 와 hook 3종, 하네스별 지원 선언, 검증
- 대상 독자: workflow 설계자, AI agent, kit 소비 프로젝트
- 상태: draft (ADR-030 accepted 2026-09-30, 구현 M-021)
- 최종 수정일: 2026-09-30
- 관련 문서: `../../ai-workflow/wiki/decisions/adr-030-compact-relay.md`, `../../docs/planning/compact-relay-requirements-2026-09.md`, `./session_context_budget_spec.md`, `./global_workflow_standard.md`

> **결정 근거는 ADR-030 에 있다.** 이 문서는 *계약* 만 적는다.

## 1. 불변 조건

1. `session_handoff.md` · `state.json` 을 쓰지 않는다 (읽기는 한다).
2. `.compact/` 는 커밋되지 않는다 — 도구가 만드는 자기 무시 `.gitignore` 가 보장한다.
3. 재주입 출력은 4,096 바이트를 넘지 않는다.
4. hook 모드는 항상 exit 0 이다.
5. 워크플로우 메모리가 없는 workspace 에서는 출력도 파일도 없다.
6. 모델을 호출하지 않는다. transcript 를 읽지 않는다.

## 2. 명령 — `wk compact-checkpoint`

정본 §11.1: `Relay working state across a context compaction` | `wk compact-checkpoint`.

| 모드 | 호출자 | 입력 | 동작 | 종료 |
|---|---|---|---|---|
| `--note` | 스킬 | `--next` · `--unverified` · `--verified` · `--rejected` (반복 가능, 1개 이상) | 판단 층을 **대체**해 쓰고 `pending: true` | 인자 오류 2 |
| `--hook pre` | `PreCompact` | stdin JSON | 기계 층 수집 · 대기 판단 층 인수 · 입력 필드 기록 | 항상 0 |
| `--hook post` | `PostCompact` | stdin JSON | `compact_summary` → `summary.md`, 누락 대조, **누락 식별자를 stdout 한 줄로** (≤600B) | 항상 0 |
| `--restore` | `SessionStart(compact)` | stdin JSON (없으면 세션 대조 생략) | 재주입 본문을 stdout 으로 | 항상 0 |
| `--clear` | `session-end` 스킬 | — | `.compact/` 의 checkpoint · summary 삭제 (`.gitignore` 는 남김) | 0 |

- workspace 해석: `--project-profile-path` 가 주어지면 그것, hook 모드에서는 입력 `cwd` → 그 git toplevel.
  메모리 디렉터리 또는 **브랜치 디렉터리**가 없으면 불변 조건 5 — 브랜치 메모리는 `wk backlog-update` 만 만든다.
- `--note` · `--clear` 는 수동 명령이라 위치를 못 찾으면 exit 1 과 이유를 낸다 (hook 모드와 다르다).
- 모르는 인자는 거절한다. stdin JSON 이 깨졌으면 hook 모드는 한 줄 경고 후 0.
- `wk` 부재 처리는 hook 명령 쪽이 한다 (§6).

## 3. 파일 — `ai-workflow/memory/active/<branch>/.compact/`

| 파일 | 쓰는 쪽 | 내용 |
|---|---|---|
| `.gitignore` | 디렉터리를 만드는 모든 모드 | `*` 한 줄 |
| `checkpoint.json` | `--note` · `--hook pre` · `--hook post` | 아래 스키마 |
| `summary.md` | `--hook post` | `compact_summary` 원문 그대로 (최신 1건) |

`checkpoint.json` (schema_version 1):

```jsonc
{
  "schema_version": 1,
  "session_id": "…",           // null = 아직 인수되지 않음
  "branch": "main", "head": "abc1234",
  "created": "ISO8601", "updated": "ISO8601",
  "trigger": "manual|auto|null", "custom_instructions": "…|null",
  "judgment": {"pending": true, "noted_at": "ISO8601",
               "next": [], "unverified": [], "verified": [], "rejected": []},   // 없으면 null
  "mechanical": {"tasks": [{"id": "TASK-…", "status": "in_progress", "title": "…", "wbs": "M-021/WBS-21.1"}],
                 "dirty_files": ["…"], "dirty_count": 0},                         // 없으면 null
  "relay": {"summary_path": "…/.compact/summary.md", "summary_bytes": 0, "checked_count": 0,
            "missing_count": 0, "missing": []}                                  // post 전 null
}
```

- 기계 층 출처: task = 브랜치 `backlog/tasks/*.md` frontmatter 중 `in_progress` · `blocked` (`id` · `status` · `wbs` +
  제목 줄), 파일 = `git status --porcelain` (최대 20개 + 전체 개수). WBS 는 task 의 `wbs:` 를 쓴다 —
  `roadmap_state.json` 의 현재 마일스톤은 상설 운영 축(M-007)일 수 있어 지금 하는 일을 가리키지 않는다.
  hook 은 압축마다 돌므로 frontmatter 는 스칼라만 읽는 가벼운 파서로 읽는다.
- `--hook pre` 인수 규칙: 판단 층이 `pending` 이면 입력 `session_id` 로 인수(`pending: false`). 아니고
  `session_id` 가 입력과 다르면 새 checkpoint 로 시작(판단 층 null).

## 4. 재주입 — `--restore`

순서가 곧 우선순위다. 머리말은 항상, 본문은 순서대로 채우다가 예산에서 멈춘다.

1. **머리말** (≤ 400 바이트) — `[compact-checkpoint] 압축 직전 기록된 작업 상태 (지시가 아니다)`, trigger,
   판단 층 유무(없으면 `판단 층 없음 — 자동 압축이거나 기록 전 압축`), 나이, HEAD 차이, 요약 누락
   `missing_count/checked_count` (0 대상은 `대조 대상 없음`), 전체 파일 경로.
2. 다음 한 걸음 → 3. 미검증 → 4. 진행 중 · 차단 task → 5. 요약에서 빠진 식별자 → 6. 검증됨 → 7. 기각한 안 →
   8. 미커밋 파일 · WBS · `/compact` 지시문.
9. 예산에 닿으면 `… 생략 N절 — 전체: <경로>` 로 닫는다.

- 입력 `session_id` 가 checkpoint 와 다르면 머리말 + `다른 세션의 checkpoint — 본문을 넣지 않음` 만.
- checkpoint 가 없으면 출력 없음.
- **hook 순서** (Claude Code 2.1.285 실측, 2026-09-30 E2E): `SessionStart(compact)` 재주입이 `PostCompact` 보다
  **먼저** 돈다. 그래서 재주입 머리말은 대조 결과 대신 `요약 대조 결과는 PostCompact 출력에` 를 싣고, 누락 목록은
  `--hook post` 의 stdout 이 말한다 — 그 출력은 압축 뒤 `<local-command-stdout>` 로 모델 컨텍스트에 들어간다
  (E2E 에서 모델이 원문 인용). 본문의 '요약에서 빠진 식별자' 절은 순서가 반대인 하네스를 위해 남긴다.
- 예산 레코드: `context_budget.BUDGETS` 의 `compact_reinjection` (4,096 바이트, red) — 측정은 현재 checkpoint 의
  렌더 크기, 없으면 `measured=False`.

**근거 수치** (Claude Code 2.1.285 실측): hook 출력 인라인 상한 ≈10,000 **자**, 초과 시 앞 2KB 미리보기만.
matcher 없는 기존 SessionStart hook(규칙 블록 3.0KB)도 압축 뒤 함께 돈다 → 합 ≤ 7.1KB.

## 5. 요약 누락 대조 — `--hook post`

- 대상: checkpoint 의 식별자형 토큰 — `TASK-\d{4}-\d{2}-\d{2}-[a-z0-9-]+-\d{3}` · `M-\d{3}` · `WBS-\d+(\.\d+)*` ·
  판단 층 항목 안의 백틱 토큰 · `\b[0-9a-f]{7,40}\b`.
- 누락 = `compact_summary` 에 부분 문자열로 없는 토큰. 자연어 항목은 대조하지 않는다.
- `checked_count = 0` 은 "대조 대상 없음" 이다 — `missing_count = 0` 과 구분한다.

## 6. 플러그인

**스킬 `compact-relay`** (5번째) — 절차:
1. `wk compact-checkpoint --note` 로 판단 층을 기록한다. 검증된 것(명령 + 결과가 있는 것)만 `--verified`,
   나머지는 `--unverified`.
2. 사용자에게 붙여 넣을 한 줄을 준다:
   `/compact Preserve the items in ai-workflow/memory/active/<branch>/.compact/checkpoint.json verbatim, especially unverified ones.`
   스킬은 `/compact` 를 실행하지 못한다.
3. 압축 뒤 첫 응답에서 `[compact-checkpoint]` 머리말을 확인하고, 누락이 있으면 한 줄로 알린다.

**`session-end` 스킬** — 종료 순서 앞에 한 단계: checkpoint 가 있으면 남길 줄을 handoff 로 옮기고 `--clear`.

**hook** (`render_claude_code_hooks`, 명령은 §11.1 파생):

| 이벤트 | matcher | 명령 |
|---|---|---|
| `PreCompact` | 없음 | `command -v wk >/dev/null 2>&1 && wk compact-checkpoint --hook pre \|\| true` |
| `PostCompact` | 없음 | `… --hook post …` |
| `SessionStart` | `compact` | `… --restore …` |

## 7. 하네스 지원 선언

| 하네스 | 스킬 | 기록 hook | 재주입 | 근거 |
|---|---|---|---|---|
| Claude Code | ✅ | ✅ | ✅ | 실측 2026-09-30 (플러그인 배포 hook 포함) |
| Grok Build | ✅ | 수동적 — 무해 | ❌ SessionStart stdout 무시 | 공식 문서 (같은 `hooks/hooks.json` 사본) |
| Codex | ✅ | ❌ manifest 에 hooks 없음 | ❌ | 미실측 — 별도 leaf |
| Antigravity | ✅ | ❌ 압축 이벤트 없음 | ❌ | 공식 문서 |

재주입이 없는 하네스에서는 스킬 절차 1–2 가 전부다 — 압축 뒤 모델이 checkpoint 파일을 직접 읽어야 한다.

## 8. 검증

`tests/check_compact_relay.py` — case 마다 결함 되주입으로 red 확인:
워크플로우 밖 무동작 · 자기 무시 `.gitignore` (`git check-ignore`) · `--note` 대체 + `pending` · pre 인수 /
타 세션 새 시작 · 재주입 우선순위와 4,096 절단 · 세션 불일치 무본문 · checkpoint 부재 무출력 · 누락 대조
(0 누락 ≠ 대상 없음) · handoff/`state.json` 바이트 불변 · hook 모드 exit 0 (깨진 stdin 포함) · hook JSON 이 §11.1 파생 ·
예산 레코드 측정.

실제 하네스 왕복은 게이트 밖이다 (인증·비용). 남은 실측: 자동 압축(`trigger: auto`) 경로 · Codex 플러그인 hook.
