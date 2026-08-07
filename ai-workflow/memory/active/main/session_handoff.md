# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-08
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: v1.0.0-beta + `origin/main` = `c51d052` (2026-08-07~08 커밋 5건) + **후속 1건 (TASK-2026-08-08-main-003 완료)**.
- 현재 주 작업 축: 다중 워크스페이스 오케스트레이션 — **설계 → 표준 반영 → 도구 3종 → dashboard 복수 root 취합** 까지 닫혔다.
  표준 §10.2 세션 시작 플로우 + dashboard Panel 5 가 모두 "여러 worktree" 친화.
- 직전 축: "mavis attach 가 안 붙는다" — 글로벌 mcp.json 등록(§2.68)은 **아직 미완**.
- 최근 핵심 기준 문서:
  - [multi_workspace_orchestration.md](../../../../workflow-source/core/multi_workspace_orchestration.md) — **§0.7 상태표 + §7.3 구현 표시**
  - [global_workflow_standard.md §10](../../../../workflow-source/core/global_workflow_standard.md) — 다중 작업·협업 규칙
  - [MEMORY_GOVERNANCE.md](../../../../workflow-source/MEMORY_GOVERNANCE.md)

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
-
## 3. 차단 작업

- 현재 `blocked` 작업:
-
## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-08-08-main-003 dashboard `_branch_state_paths` 복수 root 취합 (smoke 6/6)
- TASK-2026-08-08-main-002 워크스페이스 선점 도구 — §10.2 플로우 완결 (smoke 9)
- TASK-2026-08-08-main-001 원격 워크스페이스 현황 조회 도구 (smoke 8)
- TASK-2026-08-07-main-004 메모리 seed 도구 (smoke 8)
- TASK-2026-08-07-main-003 다중 작업·팀웍 워크플로우 정식 반영 (표준 §10 + §1)
- TASK-2026-08-07-main-002 멀티 워크스페이스 오케스트레이션 설계 + union merge 적용
- TASK-2026-08-07-main-001 MCP 도구 13종 세션 로드 검증 — 안 붙음 (mavis 가 글로벌 mcp.json 만 본다)
- TASK-2026-08-06-main-004 학습회 발표자료 32번 장표 그리드 개편 + 37번 라이트 테마 통일
- TASK-2026-08-06-main-003 학습회 덱 38장 헤더/본체 수직 정렬 표준화
- TASK-2026-08-06-main-002 학습회 마스터 HTML 덱 제작·검증
- TASK-2026-08-06-main-001 학습회 발표자료 컨셉·설계 v2

## 5. 다음 세션 시작 포인트

**이번 세션 기록**: [sessions/multi_workspace_orchestration_2026-08-08.md](./sessions/multi_workspace_orchestration_2026-08-08.md)
— 판단을 뒤집은 실측 6건, 검사 설계 원칙, 사고 1건이 거기 있다. 맥락이 필요하면 그걸 읽는다.

### 무엇이 끝났나

`origin/main` = `c51d052` + 후속 1커밋 (TASK-2026-08-08-main-003). 5건 + 1건으로
설계부터 도구화 + dashboard 다중 root 확장까지 닫았다.

- **표준 §10 "다중 작업과 협업"** 신설 + §1 bullet 2건 → **12 하네스 진입점에 자동 전파**
  (빈 저장소 bootstrap 으로 `AGENTS.md` 2/2 · `GEMINI.md` 2/2 실측).
- **`.gitattributes`** (저장소 최초) — `log.md` / telemetry / daily backlog 에 `merge=union`.
  `state.json` 은 **의도적 제외** (union 이 JSON 을 깨뜨린다).
- **도구 3종** (smoke 25 assertions, 전부 green):
  - `survey_remote_workspaces.py` — 원격 현황. fetch 기본, stale 은 **보고만**.
  - `claim_workspace.py` — 브랜치+seed+push 1회. **`--force` 수단 없음**.
  - `seed_workspace_memory.py` — `active/<branch>/` 생성. `state.json` 은 안 만든다.
- **dashboard Panel 5 다중 root** (smoke 6/6):
  - `_branch_state_paths(*roots)` — union + dedupe + sort. **파생 뷰 원칙 유지**.
  - `collect_recent_releases(extra_roots=)` + `git worktree list --porcelain` 자동
    합류 + `WORKFLOW_EXTRA_ROOTS` env. registry 가 들어오면 `extra_roots` 를 채워주는
    자리가 된다.

세션 시작 플로우:

```bash
python3 workflow-source/tools/survey_remote_workspaces.py
python3 workflow-source/tools/claim_workspace.py --branch <b> --axis "<축>" --task-title "<제목>" --apply
python3 workflow-source/tools/seed_workspace_memory.py --branch <b> --axis "<축>" --task-title "<제목>" --apply  # 선점 시 자동 호출
python3 workflow-source/scripts/generate_workflow_state.py \
  --project-profile-path docs/PROJECT_PROFILE.md --output-path ai-workflow/memory/active/<b>/state.json
```

대시보드(Panel 5) 가 자동으로 모든 worktree 의 state.json 을 합쳐 본다. 다른 worktree
를 명시적으로 합류시켜야 하면 `WORKFLOW_EXTRA_ROOTS=/path1:/path2` env 1개면 충분.

### 다음에 할 일 (순서)

1. **registry 신규** — 후보 1 의 다음 단계. `_branch_state_paths` 가 `extra_roots` kwarg
   로 이미 받으니, registry 가 `extra_roots` 를 만들어주는 자리가 자연스럽게 마련됐다.
   단일 호스트면 아직 불필요.
2. **사전 존재 red 정리** — §6. 2건 닫았고 2건 남았다
   (`mcp_installation_by_harness.md` 사본 / bootstrap picker import).
3. **registry** — 범위가 계속 줄어 *다중 호스트 경로 매핑* 만 남았다. 단일 호스트면 불필요하고,
   비어 있는 `environments/` 전례대로 **소비자가 생길 때** 만든다.
4. **§2.68 (이전 축, 미완)** — mavis 글로벌 `~/.minimax/mcp/mcp.json` 에
   `standardAiWorkflowReadOnly` 등록 + 새 세션에서 13종 attach 검증. **절대 경로 필수**.

## 6. 남은 리스크 / 확인하지 못한 것

**사전 존재 red — 2건 닫음, 2건 남음**:

| 검사 | 상태 |
| --- | --- |
| `check_appendonly_memory_layout` | ✅ **닫음** — 2026-08-06 task 3건에 frontmatter 추가 |
| `check_self_application` (`handoff_bloat`) | ✅ **닫음** — 본 문서 1096줄 → 106줄, done items 10/10. **8/8 passed** |
| `check_standard_single_source` | ⚠️ 남음 — `mcp_installation_by_harness.md` 사본 divergence (`c63b54e`~) |
| `check_bootstrap_interactive_picker` | ⚠️ 남음 — `ModuleNotFoundError: bootstrap_lib.__main__` |

**별건**: dashboard `drift_prevention.guard_status: fail` — `maturity_last_updated` stale.
갱신 힌트는 dashboard 출력의 `maturity_refresh_hint`.

**구현했지만 검증 못 한 것**:

- 도구 3종은 **로컬 bare remote** 로만 검증했다. GitHub 등 실제 원격의 protected branch /
  push 권한 정책 아래에서는 다르게 동작할 수 있다.
- `--force` 는 도구가 제공하지 않지만, **사람이 직접 실행하는 것은 막지 못한다.**
  서버측 branch protection 이중화는 미적용.
- stale 임계 24h 는 heuristic 이다. 실제 운영 데이터로 조정한 적 없다.

**이전 세션들의 교훈**은 각 세션 기록에 있다:
[2026-08-08](./sessions/multi_workspace_orchestration_2026-08-08.md) ·
[2026-08-05](./sessions/self_application_and_mcp_2026-08-05.md) ·
[2026-08-07 MCP](./sessions/mcp_load_verification_2026-08-07.md) ·
[2026-07-27](./sessions/selfref_cleanup_and_ci_measurement_2026-07-27.md)
