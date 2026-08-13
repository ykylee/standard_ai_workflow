# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-13 (PR #23 정합 보완)
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: **작업 브랜치 `feat/plugin-harness-distribution` — Codex·Claude Code native plugin release asset 분리 (PR [#23](https://github.com/ykylee/standard_ai_workflow/pull/23)).** 공유 payload 에 Codex `.codex-plugin/plugin.json` 을 더하고 `PLUGIN_HARNESS_SPECS` registry 가 하네스별 ZIP 을 분리 생성하며, `release-pipeline dist/release` 가 두 asset 을 만들고 첨부한다. **Codex 실기 로드 실측 완료** (codex-cli 0.143.0, 격리 `CODEX_HOME`): 스킬 4종이 `standard-ai-workflow:<slug>` 로 model-visible prompt 에 잡히고 read-only MCP 번들이 `enabled` 로 잡힌다. manifest 필드는 Codex 번들 스펙 원문의 정식 필드이고 공식 검증기도 통과한다. **main 병합 + 정합 보완 7건**: task ID 충돌 재발급 / `RELEASE.md §1` TestPyPI 정책 유지 / 살아있는 수치 252→253 / TST-WF-01 이 `raise AssertionError` 를 못 보던 사각지대 수리 / 저자 이메일 손 사본(`yklee@`) → packaging metadata 파생 / PyYAML fail-open → fail-closed / 브랜치 메모리 디렉터리 신설 / 두 검사가 임시 workspace 를 판정한다면서 호스트 저장소의 state.json 을 읽던 자리 (로컬 green·CI red 비대칭 3번째, detached worktree 로 재현). 전량 2축 **253/253 ×2 green**, mypy strict 193 files 0. 상세: [세션 기록](./sessions/plugin_harness_distribution_pr23_2026-08-13.md).

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
-
## 3. 차단 작업

- 현재 `blocked` 작업:
-
## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-08-13-feat-plugin-harness-distribution-001 Codex·Claude Code native plugin release asset 분리 및 release pipeline 연결

## 5. 다음 세션 시작 포인트

- PR #23 의 CI 결과 확인 (native / slash 두 셀).
- 병합 후 이 브랜치를 삭제하면 `active/feat/plugin-harness-distribution/` 은 자동
  아카이브 대상이 된다 (`tools/archive_branch_memory.py` — 역방향 점검).

## 6. 남은 리스크 / 확인하지 못한 것

- Codex manifest 의 `interface` 블록(UI 표면)은 실기 효과를 관측할 경로를 찾지
  못해 미확인이다. `codex debug prompt-input` 에는 나타나지 않는다 — 스펙 원문
  근거로만 싣는다.
- `skills/<slug>/agents/openai.yaml` 도 같다: model-visible prompt 의 스킬 설명은
  `SKILL.md` frontmatter 에서 오고 `openai.yaml` 의 `display_name` 은 거기 없다.
- 작업 브랜치에 `active/<branch>/` 가 없어도 그 사실을 직접 지목하는 검사가 없다.
  지금은 `check_branch_context_matrix` / `check_claim_workspace` /
  `check_seed_workspace_memory` 3종의 간접 증상으로만 드러난다.
