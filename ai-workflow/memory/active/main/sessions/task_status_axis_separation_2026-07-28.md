# 세션 기록 — `status` 칸에 출처를 적고 있었다 (2026-07-28)

- 문서 목적: 이 세션이 무엇을 결정하고, 무엇을 재고, 무엇을 남겼는지 다음 세션이 이어받게 한다.
- 범위: TASK-2026-07-28-main-002 (§2.39)
- 대상 독자: AI agent, 저장소 관리자
- 상태: closed
- 최종 수정일: 2026-07-28
- 관련 문서: [state.json](../state.json), [session_handoff.md](../session_handoff.md),
  [TASK-2026-07-28-main-002](../backlog/tasks/TASK-2026-07-28-main-002.md),
  `workflow-source/releases/Beta-v1.0.0.md` §2.39,
  `workflow-source/MEMORY_GOVERNANCE.md` "두 축을 섞지 않는다"

## 1. 시작 지점

직전 세션(TASK-2026-07-28-main-001)의 커밋·푸시부터. `047d4e5` push 후 CI 3종
(smoke / mypy-strict / mkdocs) 전부 success 실측. 그다음 §2.38 이 **governance 결정**으로
남긴 `status: recorded` 어휘 문제를 열었다.

## 2. 결정

사용자에게 세 선택지를 제시하고 **축 분리**를 선택받았다.

| 선택지 | 내용 | 채택 |
|---|---|---|
| 축 분리 | 어휘는 넷 유지, 출처는 `provenance` 로 분리, 근거 없으면 status 비움 | ✅ |
| 어휘 5개 확장 | `unknown`/`recorded` 추가 | ❌ 정본+소비자 validator breaking, 축 혼재 잔존 |
| 최소 변경 | 3건만 손으로 확정 + 툴은 `planned` | ❌ "이미 한 일"을 planned 로 적는 거짓 잔존 |

판단 근거: `recorded` 가 뜻한 것은 진행 상태가 아니라 **"legacy 에서 이관됐고 진행 상태는
모른다"** 는 출처 사실이었다. 축이 둘이면 칸도 둘이어야 한다.

미판정 2건 처리도 사용자가 **"미판정으로 노출 유지"** 를 선택했다.

## 3. 조치

- `project_docs`: `TASK_PROVENANCE_MIGRATED_LEGACY` / `MISSING_STATUS_MARKER` 단일 출처 추가
- `migrate_active_to_appendonly.py`: **release entry 에만** `status: done` (발행된 릴리스
  노트가 근거). generic/session 은 `status` 줄 없이 `provenance` 만
- `builder`: `status:` 줄이 없을 때 `planned` 로 떨어뜨리던 fallback 제거 → `<미기재>` 로 노출
- `builder`: **`session.unknown_status_items` 를 state payload 까지 emit** (아래 §5 참조)
- `check_appendonly_memory_layout`: `status` 필수 → **`status`|`provenance` 택일 필수** +
  `status` 가 있으면 어휘 안
- `MEMORY_GOVERNANCE.md`: task frontmatter 템플릿에 두 축 명시 + "섞지 않는다" 절 신설

기존 3건은 **판정 가능한 것만** 확정했다.

| task | 처리 | 근거 |
|---|---|---|
| `TASK-2026-06-30-002` | `status: done` | 본문에 commit 9건 + FULL mypy strict 도달로 종료 |
| `TASK-2026-04-24-001` | 미기재 | legacy 본문 한 줄 — 근거 없음 |
| `TASK-2026-05-01-001` | 미기재 | 〃 |

## 4. 검증

- 신규 `check_task_status_axis_separation.py` **6건**. 되주입 **4건이 각각 다른 증상으로**
  실패 확인 (이관 도구 `recorded` 복귀 → 어휘 검사 / builder `planned` fallback 복귀 →
  미기재 검사 / 실파일 `recorded` → layout·전수 검사 / `provenance` 삭제 → 택일 검사)
- 전량 smoke **219/219 PASS** (`.venv/bin/python`, 격리 tmp-dir, abort 0, 저장소 변경 0)
- mypy strict **119 files, 0 errors** (`--config-file workflow-source/pyproject.toml` 명시)
- E2E: `backlog-update --apply` 산출물을 `git diff` 로 검토 — 최신순 유지 + 상한 10 유지 +
  `unknown_status_items` 2건 노출 + `TASK-2026-06-30-002` 이 done 으로 이동 확인

## 5. 이번에 새로 드러난 것

§2.38 이 만든 `unknown_status_items` 는 **`_aggregate_from_appendonly_layout` 반환값 안에만
있었고 state payload 까지 오지 않았다.** 직접 그 함수를 부르는 테스트에만 보였고,
`state.json` 을 읽는 사람과 skill 에게는 안 보였다 — 조용히 사라지는 것과 다르지 않다.
이번에 `session.unknown_status_items` 로 emit 했다.

> 노출을 만들었으면 **소비자가 실제로 보는 자리까지 왔는지** 확인할 것. 아무도 안 읽는
> 자리에 놓인 지표는 없는 것과 같다.

## 5-1. 후속 — 미판정 2건을 판정했다

노출된 김에 근거를 찾았고 둘 다 남아 있었다. 찾는 과정에서 **이 둘이 애초에 task 가
아니었다**는 게 드러났다 — legacy `work_backlog.md` 의 `### Historical archives` 아래
**아카이브 포인터 한 줄**이었고, 이관 도구가 `### [[path]] {#anchor}` block 을 일괄
task 화하면서 포인터까지 task 가 됐다. 본문이 한 줄이었던 이유가 이것이다.

| task | 판정 | 근거 |
|---|---|---|
| `TASK-2026-05-01-001` | `done` | `archived/codex/phase6/backlog/2026-05-01.md` `상태: done` + handoff `Status: done` (TASK-038~045 / WF-042-01~06 전부 done, "No active blocker") + 산출물 실재 |
| `TASK-2026-04-24-001` | `done` | `archived/gemini/phase10/session_handoff.md`(Updated 2026-05-04, 최신 기록) Work Status 에 `TASK-001 …: done` 명시 |

두 번째 건은 **기록 셋이 어긋나 있었다** — handoff(05-04) `done` / work_backlog §3
체크박스(05-02) 미체크 / day file(04-24, `draft`) `planned` 방치. 같은 브랜치의
`2026-04-26.md` 는 `done` 으로 갱신돼 있어 그 날짜 파일만 안 고쳐진 것으로 보인다.
가장 나중이면서 유일하게 명시적인 handoff 를 따랐고, **어긋난다는 사실 자체는 task 파일
Outcome 에 남겼다**. 셋이 왜 어긋났는지는 알 수 없다.

`unknown_status_items` 는 이제 빈 목록이다 (노출 기구는 그대로 유지).

## 5-2. 후속 2 — 이관 파서의 구분 heading 결함 (§2.40)

위에서 "별건" 으로 적었던 것을 이어서 닫았다. 열어 보니 손실이 **둘**이었다.

| 손실 | 실측 |
|---|---|
| 본문 오염 | `TASK-2026-06-05-001.md` Implementation 절에 `### Historical archives {#historical-archives}` 가 박혀 있었다 — 그 entry 의 내용이 아니라 다음 묶음의 시작 |
| 소속 소실 | 아카이브 포인터와 작업 항목은 형태가 같다(`### [[path]] {#anchor}` + 한 줄). 구분 단서가 그 heading 뿐인데 파서가 버렸다 |

**두 번째가 비쌌다.** §5-1 의 판정이 어려웠던 건 판정이 원래 어려워서가 아니라
**판정에 필요한 사실이 이관에서 버려졌기 때문**이다.

조치: `GROUP_HEADING_RE` 로 구분 heading 인식 → 직전 entry 를 닫고 소속 갱신,
`Entry.group` → frontmatter `source_group:`, 이관 summary 에 "확인 필요" 묶음 노출.
**"아카이브 포인터면 task 가 아니다" 는 판정은 도구가 하지 않는다** (§2.39 와 같은 원칙).

검증: 실제 legacy 파일(git 이력 복원)로 entry **93건 그대로**, body 오염 **1→0**,
포인터 2건 소속 부여. 신규 `check_migration_group_heading.py` 6건 + 되주입 3건 각각 다른
증상으로 실패. 전량 smoke **220/220**.

## 6. 남긴 것

- **아카이브 포인터 2건을 task 로 둘지는 미결.** `source_group: Historical archives` 가
  붙은 채 `done` 으로 남아 있다. 정리(삭제/이동) 여부는 프로젝트 결정.
- **daily index 의 "`status` 줄 없으면 done" fallback 은 남겼다.** task 파일이 SSOT 라 이
  저장소(103건 전부 task 파일 보유)에서는 발현하지 않지만, 구형 index 만 있는 legacy
  저장소에서는 여전히 추측이다. 호환 때문에 두었다.
- dashboard Panel 5 의 브랜치 간 정렬 키 부재 — 별건 (§2.38 에서 이월).
- 슬래시(`/`) 브랜치에서 `check_branch_scoped_memory` / `check_self_application` 파손 — 별건.

## 7. 다음 세션에

`git status` 로 커밋 여부부터 확인할 것.
