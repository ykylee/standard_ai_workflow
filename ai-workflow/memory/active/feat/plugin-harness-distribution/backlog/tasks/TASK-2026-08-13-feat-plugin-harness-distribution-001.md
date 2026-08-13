---
id: TASK-2026-08-13-feat-plugin-harness-distribution-001
status: done
created_at: 2026-08-13
source_anchor: generic-task-2026-08-13-feat-plugin-harness-distribution-001
source_path: backlog/2026-08-13.md
kind: generic
---

# TASK-2026-08-13-feat-plugin-harness-distribution-001 — Codex·Claude Code native plugin release asset 분리 및 release pipeline 연결

## 📝 Description

- 상태: done
- 우선순위: high
- 요청일: 2026-08-13
- 담당:
- 호스트명:
- 호스트 IP:
- 영향 문서:
  - `plugin/`
  - `workflow-source/workflow_kit/plugin_distribution.py`
  - `workflow-source/workflow_kit/tools/release_pipeline.py`
  - `docs/RELEASE.md`

- 작업 내용: Codex native plugin과 기존 Claude Code plugin을 개별 GitHub Release asset으로 배포하고, plugin-capable harness를 확장 가능한 registry로 관리한다.
- 완료 기준: `dist --apply` 가 두 ZIP 을 만들고, Codex ZIP 은 marketplace 설치 구조와 manifest validation 을 통과하며 release 가 두 asset 을 포함한다.

## 🛠️ Implementation / Content

- 진행 현황: `2026-08-13` 기준 완료. PR [#23](https://github.com/ykylee/standard_ai_workflow/pull/23).
- **이 task 가 이 디렉터리에 있는 이유**: 처음에는 `active/main/` 에
  `TASK-2026-08-13-main-008` 로 손으로 등록됐고, 같은 날 `main` 세션이 같은 번호로
  TestPyPI 리허설을 등록해 충돌했다. `MEMORY_GOVERNANCE.md §Branch-scoped layout`
  이 정한 대로 **작업 브랜치의 기록은 그 브랜치 디렉터리에** 둔다 — 번호를 브랜치
  안에서만 매기므로 동시 작업해도 겹치지 않는다. 재발급 경위는 "원인 분석" 참조.
- 다음 세션 시작 포인트: PR #23 의 CI 결과 확인. 병합 후 이 브랜치를 지우면
  `active/feat/plugin-harness-distribution/` 은 자동 아카이브 대상이 된다
  (`tools/archive_branch_memory.py`, 역방향 점검).
- 남은 리스크: Codex manifest 의 `interface` 블록(UI 표면)은 실기 효과를 관측할
  경로를 찾지 못해 미확인이다 — 스펙 원문 근거로만 싣는다. `skills` / `mcpServers`
  는 실측으로 로드를 확인했다.

## ✅ Outcome

- 작업 결과: 공유 payload 에 Codex `.codex-plugin/plugin.json` 추가.
  `PLUGIN_HARNESS_SPECS` registry 가 Codex/Claude Code 별 ZIP 을 분리 생성한다.
  Codex ZIP 은 `.agents/plugins/marketplace.json` + `plugins/standard-ai-workflow/`,
  Claude ZIP 은 Claude manifest/hooks 만 담는다. `release-pipeline dist` 가 ZIP 을
  만들고 `release` 는 asset 이 없으면 중단한 뒤 GitHub Release attach 목록에 포함한다.
- 검증 결과: payload 18/18, plugin distribution smoke, 전량 2축 **253/253 ×2**,
  mypy strict 193 files 0, 대상 ruff 신규 지적 0.
- **Codex 실기 로드 실측** (codex-cli 0.143.0, 격리 `CODEX_HOME`): ZIP →
  `codex plugin marketplace add` → `codex plugin add` → `installed, enabled`.
  `codex debug prompt-input` 의 `<skills_instructions>` 에 스킬 4종이
  `standard-ai-workflow:<slug>` 로 잡히고, `codex mcp list` 에 read-only 번들이
  `enabled` 로 잡힌다. manifest 필드는 Codex 가 번들한 스펙 원문
  (`plugin-creator/references/plugin-json-spec.md`) 의 field guide 에 전부 있는
  정식 필드였고, 같은 번들의 공식 검증기 `validate_plugin.py` 도 통과한다 —
  `interface.displayName` 을 빼서 되주입하면 그 필드를 지목하며 실패하므로
  검증기가 공허하지 않다.

## 🔎 원인 분석 — 왜 브랜치 메모리가 안 만들어졌나

`ai-workflow/memory/active/<branch>/` 는 **자동으로 생기지 않는다.** 만드는 자리는
`wk backlog-update` 하나다 (`common/workflow_writes.py::write_task_entry` 가
`tasks_dir.mkdir(parents=True)` 로 브랜치 트리를 통째로 만든다). `session-start` /
`refresh-state` 는 부재를 *warning* 으로만 알리고 scaffold 하지 않는다 (graceful
skip 이 설계다).

경로 해석 자체는 정상이었다 — 이 브랜치에서 `branch_for_workspace` 는
`feat/plugin-harness-distribution` 을, `wk backlog-update` 는
`active/feat/plugin-harness-distribution/backlog/2026-08-13.md` 와
`TASK-2026-08-13-feat-plugin-harness-distribution-001` 을 낸다 (실측). 즉 도구를
썼다면 디렉터리도 브랜치 네임스페이스 ID 도 정상적으로 생겼다.

**실제 경위**: 작업 브랜치에서 `wk backlog-update` 를 쓰지 않고 `active/main/` 의
daily index·handoff·state.json 을 직접 편집했다 (`51e04eb` 이 건드린 메모리 경로가
전부 `active/main/` 이다). 그 결과 둘이 한꺼번에 따라왔다:

1. 브랜치 디렉터리가 끝내 안 생겨 `check_branch_context_matrix` /
   `check_claim_workspace` / `check_seed_workspace_memory` 3종이 **push 마다 red**.
   세 번의 push 모두 red 였고 원인은 내내 같았다.
2. task 번호를 main 네임스페이스에서 뽑아 `TASK-2026-08-13-main-008` 이 두 개가 됐다.
   governance 가 "순번을 브랜치 안에서만 매기므로 동시 생성해도 겹치지 않는다" 고
   적어 둔 보호가 정확히 이 우회로 무력화됐다.

**남는 구멍**: 손 편집을 막을 자리가 없다. 부재를 알리는 warning 은 있지만 그것을
보고도 `active/main/` 에 쓰면 아무것도 실패하지 않는다. 중복 ID 는 이제
`check_appendonly_memory_layout` case 7 이 잡지만, "작업 브랜치인데 그 브랜치
디렉터리가 없다" 는 여전히 3개 검사의 *간접* 증상으로만 드러난다.

## 🔁 로컬 green / CI red (3번째)

브랜치 메모리를 만든 뒤에도 CI 만 2건 red 였다. `check_claim_workspace` /
`check_seed_workspace_memory` 가 임시 workspace 를 판정한다면서
`--project-profile-path` 로 실제 저장소를 가리켜 `state.json` 을 호스트에서 찾았고,
판정이 호스트의 브랜치 상태에 달려 있었다 (main 통과 / detached HEAD = CI 의 PR
checkout FAIL). 로컬 detached worktree 로 재현 → `STATE_ABSENT_WARNING` 정본 상수를
뽑아 그 한 줄만 허용하고 나머지 warning 을 본다. 되주입으로 비공허성 확인.

## 후속 작업

- 신규 하네스의 native manifest 와 `PluginHarnessSpec` 등록 후 distribution smoke 확장.
- 작업 브랜치에 `active/<branch>/` 가 없으면 직접 지목해 알리는 자리 검토
  (지금은 3개 검사의 간접 증상으로만 드러난다).
