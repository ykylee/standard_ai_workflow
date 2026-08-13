# 세션 기록 — Codex·Claude Code native plugin 배포 + main 정합 보완 (2026-08-13)

- 문서 목적: `feat/plugin-harness-distribution` 브랜치(PR #23)의 작업과 판단 근거를 남긴다.
- 범위: native plugin ZIP 분리, Codex 실기 검증, main 병합 정합 보완 10건 (§3 에 7건, §5·§6 에 3건)
- 대상 독자: AI agent, 저장소 관리자
- 상태: stable
- 최종 수정일: 2026-08-13
- 관련 문서: [task](../backlog/tasks/TASK-2026-08-13-feat-plugin-harness-distribution-001.md), [handoff](../session_handoff.md)

## 1. 무엇을 했나

공유 payload 에 Codex manifest 를 더하고, `PLUGIN_HARNESS_SPECS` registry 로
하네스별 native plugin ZIP 을 분리 생성해 GitHub Release asset 으로 붙였다.
`release` 는 ZIP 이 없으면 중단한다.

그 위에 **main 병합 정합 보완 10건**을 얹었다. PR #23 의 CI 는 세 번의 push 모두
red 였고(11건), 그 원인이 전부 여기서 닫힌다.

내역은 두 곳에 나뉘어 있다: §3 에 7건, §5·§6 에 "판정이 호스트 환경에 달려 있던
자리" 3건. 세션 중에 뒤늦게 3건이 늘어 §3 의 제목만 7 로 남았다.

## 2. Codex 실기 검증 — "validate 통과는 로드 증명이 아니다"

이 저장소는 Gemini 어댑터에서 그 교훈을 이미 치렀다. Codex 도 같은 기준을 적용했다.

- 격리 `CODEX_HOME` 에 ZIP 을 풀어 `codex plugin marketplace add` →
  `codex plugin add` → `installed, enabled` (codex-cli **0.143.0**).
- **로드 증명**: `codex debug prompt-input` (모델 호출 없이 model-visible prompt 를
  JSON 으로 덤프) 의 `<skills_instructions>` → `Available skills` 에 스킬 4종이
  `standard-ai-workflow:session-start` 형태로 잡힌다. `codex mcp list` 에
  read-only 번들이 `enabled`.
- **함정 하나를 지나쳤다**: 처음엔 prompt 전문에 `session-start` 문자열이 몇 번
  나오는지 grep 했는데, 그 히트는 대부분 `AGENTS.md` 본문이었다. 문자열 개수는
  로드 증명이 아니다 — `Available skills` 목록 자체를 파싱해야 한다.
- **스펙 원문을 찾았다**: Codex CLI 가 번들하는 `plugin-creator` 스킬의
  `references/plugin-json-spec.md`. manifest 에 쓴 필드
  (`author`/`repository`/`license`/`keywords`/`skills`/`mcpServers`/`interface`)
  는 전부 그 field guide 에 있는 정식 필드다 — 지어낸 것이 아니다.
- **외부 증인**: 같은 번들의 `scripts/validate_plugin.py` 가 통과한다. 공허하지
  않음도 확인했다 — `interface.displayName` 을 빼서 되주입하면 그 필드를
  지목하며 실패한다.
- **미확인으로 남긴 것**: `interface` 블록과 `agents/openai.yaml` 은 UI 표면이라
  이 경로로 관측되지 않는다. 스킬 설명은 `SKILL.md` frontmatter 에서 온다.
  goose snippet 과 같은 취급 — 미검증을 미검증으로 적는다.

## 3. 정합 보완 7건 (전체 10건 중 — 나머지 3건은 §5·§6)

1. **task ID 충돌** — `TASK-2026-08-13-main-008` 이 두 개였다 (main 의 TestPyPI
   리허설 / 이 브랜치의 Codex 배포). §4 참조.
2. **`RELEASE.md §1`** — main 의 TestPyPI `⚠️ 1회 한정 허용 + 각주 1`(소유자 승인)
   을 유지하고 native plugin ZIP 표기를 GitHub Releases 행에 얹었다.
3. **살아있는 수치 252 → 253** (release note / CODE_INDEX / INSTALLATION).
   release note 는 릴리스 **시점**(252)과 현재(253)를 구분해 적는다 — 발행된
   노트의 과거 서술을 고쳐 쓰지 않는다.
4. **TST-WF-01 판정식의 사각지대** — `check_plugin_distribution` 은 검증을 전부
   `raise AssertionError` 로 하는데 `_count_verification_signals` 가 그 형태를
   인정하지 않아 signal 0 → min 0 → testing baseline non_compliant → 릴리스
   pre_check 의 doctor 게이트가 막혔다. **신규 파일의 결함이 아니다**: 저장소
   smoke **89개**가 같은 관용구를 쓰는데 그 파일들은 다른 형태를 곁들여 *우연히*
   >0 이었다. 이 형태만 쓰는 파일이 처음 들어오자 사각지대가 드러났다.
   `raise AssertionError` 를 `assert` 와 같은 지위로 세고, 다른 예외·bare raise 는
   제외한다 (넓히면 floor 가 무력해진다). case 10·11 신설, 되주입 실증.
5. **배포 신원이 손 사본이었다** — Codex manifest 의 저자 이메일이
   `yklee@users.noreply.github.com`, 정본은 `ykylee@…`. **`y` 하나가 빠진 채**
   배포 payload 까지 갔다. pyproject 를 읽어 나르고(못 읽으면 loud raise),
   case 18 은 렌더러 helper 가 아니라 **pyproject 를 직접 읽어** 대조한다 —
   helper 로 대조하면 helper 가 틀렸을 때 같이 틀린다.
6. **fail-open 검사** — `test_codex_skill_metadata` 가 PyYAML 부재 시 `continue`
   로 조용히 통과했다. 같은 파일 case 2 는 같은 상황을 FAIL 로 적는다. 맞췄다.
7. **브랜치 메모리 디렉터리** — §4.

## 4. 브랜치 메모리가 왜 안 만들어졌나

`ai-workflow/memory/active/<branch>/` 는 **자동으로 생기지 않는다.** 만드는 자리는
`wk backlog-update` 하나다 (`write_task_entry` 가 `tasks_dir.mkdir(parents=True)`).
`session-start` / `refresh-state` 는 부재를 warning 으로만 알린다 (graceful skip).

> **정정 (2026-08-13, TASK-…-fix-branch-memory-namespace-guard-001)**: 위 문장의
> "만드는 자리는 `wk backlog-update` 하나" 는 틀렸다. `backlog-update` 는
> `tasks_dir.mkdir()` 의 **부수효과로** `backlog/` 만 만든다 — `sessions/` 와
> `session_handoff.md` 가 빠져 `check_appendonly_memory_layout` /
> `check_memory_freeze_lint` / `check_self_application` 이 red 로 남는다.
> 한 벌로 만드는 정본 창구는 **`wk seed-workspace-memory`** 다 (그 도구의
> docstring 이 바로 이 실패 — `missing_required_document` — 를 계보로 적고 있다).
> 이 정정을 실측한 경위: 위 진단을 그대로 따라 `backlog-update` 를 먼저 돌렸더니
> 전량에서 정확히 그 3검사가 red 였다. **도구를 옳게 썼는데도 red** 이므로, 다음
> 사람이 손 편집으로 도망갈 유인이 그대로 남아 있었다.

경로 해석은 정상이었다. 이 브랜치에서 `wk backlog-update` 는
`active/feat/plugin-harness-distribution/backlog/2026-08-13.md` 와
`TASK-2026-08-13-feat-plugin-harness-distribution-001` 을 낸다 (실측).

**실제 경위**: 작업 브랜치에서 그 도구를 쓰지 않고 `active/main/` 의 daily index·
handoff·state.json 을 직접 편집했다 (`51e04eb` 이 건드린 메모리 경로가 전부
`active/main/`). 결과가 둘이었다:

- 브랜치 디렉터리가 끝내 안 생겨 `check_branch_context_matrix` /
  `check_claim_workspace` / `check_seed_workspace_memory` 가 **push 마다 red**.
- task 번호를 main 네임스페이스에서 뽑아 ID 가 충돌했다. governance 가
  "순번을 브랜치 안에서만 매기므로 동시 생성해도 겹치지 않는다" 고 적어 둔
  보호가 정확히 이 우회로 무력화됐다.

**병합 시 이 충돌은 조용하다**: daily index 는 서로 다른 줄이라 conflict 없이
auto-merge 되어 같은 ID bullet 두 개가 남고, task 파일만 add/add conflict 를 낸다.
한쪽으로 해소하면 남은 bullet 이 *다른 작업을 설명하는 파일*을 가리킨다. 실측으로
확인했다 — 보완 전 backlog 검사 4종도 `generate_workflow_state.py` 도 중복을
검출하지 못했고, 생성된 state.json 은 한쪽만 담은 채 `ok` 였다.

`check_appendonly_memory_layout` case 7 을 신설했다. 정상적인 재등장(다음 날
index 에 같은 제목으로 다시 실려 상태만 갱신)과 구분해 ①한 daily index 안의 중복
②같은 ID 에 다른 제목 만 잡는다. 실제 충돌을 되주입하면 둘 다 검출한다.

## 5. 로컬 green / CI red 가 한 번 더 나왔다

브랜치 메모리를 만들자 로컬 전량은 2축 green 이 됐는데 **CI 는 같은 SHA 에서 2건
red** 였다 (`check_claim_workspace` / `check_seed_workspace_memory`). 이 저장소가
두 번 치른 비대칭(SDK 매트릭스 / 브랜치 매트릭스)의 세 번째다.

원인: 두 검사는 임시 workspace 를 판정한다면서 `--project-profile-path` 로 **실제
저장소**를 가리켰다. handoff·backlog 는 임시 workspace 것을 넘기지만 `state.json` 은
프로필 경로에서 파생되므로 호스트 저장소에서 찾는다. 그래서 판정이 seed 산출물이
아니라 **호스트의 브랜치 상태**에 달려 있었다:

- `main` 체크아웃 → 브랜치 state.json 이 채워져 있음 → warning 없음 → PASS
- detached HEAD (CI 의 PR checkout) → 브랜치 slug 이 short SHA → 그 경로 없음 →
  `state.json 부재` warning → FAIL

로컬 detached worktree 로 **재현했다**. seed 는 state.json 을 일부러 만들지 않으므로
(`test_no_state_json`) 그 warning 은 정상이다 — 문구를 `STATE_ABSENT_WARNING` 정본
상수로 뽑아 두 검사가 그 한 줄만 허용 목록에 두고 *나머지* warning 을 본다.
되주입으로 공허하지 않음을 확인했다: 다른 warning 을 하나 심으면 두 검사 모두 FAIL.

## 6. 같은 비대칭이 두 번 더 나왔다 (4·5번째)

**4번째 — canonical URL 이 체크아웃 브랜치를 따라다녔다.** `_detect_default_branch`
는 `origin/HEAD` 가 없으면 *현재 브랜치*를 기본 브랜치로 썼다. `actions/checkout` 은
단일 ref 만 가져와 `origin/HEAD` 를 만들지 않으므로, 같은 커밋인데도 feature 브랜치
**push** 셀은 `…/blob/feat/plugin-harness-distribution/…` 을 내고 **pull_request** 셀은
detached 라 `main` 으로 떨어져 통과했다. 커밋된 bundle 은 `…/blob/main/…` 이라 push
셀만 red. `check_frontmatter_url_extraction` 의 fork/ref 완화(`_blob_suffix`)도 슬래시
든 브랜치에서는 ref 를 한 segment 로만 떼어 못 살린다. → origin 이 있으면 현재
브랜치로 내려가지 않고 문서화된 기본값 `main` 을 쓴다.

**5번째 — 내가 그 수리에 붙인 회귀 테스트가 CI 에서만 red 였다.** gate 를
`_detect_origin_url` 로 물었는데 그 함수는 **CI env(`GITHUB_REPOSITORY`)를 먼저 본다**
— GitHub Actions 안에서는 remote 없는 temp 저장소에도 URL 을 돌려주므로 gate 가
CI 에서만 반대로 열렸다. 판단을 `_repo_has_origin_remote`(env 를 보지 않고 그 저장소의
`remote.origin.url` 만 본다)로 바꿨다.

**교훈**: 이 세션에서만 같은 모양이 세 번(3·4·5번째) 나왔다. 셋 다 "판정이 호스트
환경의 무언가에 달려 있는데 로컬에는 그 축이 없다" 였다. 그래서 전량을 CI 환경변수를
씌운 축으로도 한 번 돌리는 것을 이 세션의 검증 절차에 넣었다:

```bash
GITHUB_SERVER_URL=https://github.com GITHUB_REPOSITORY=<owner/repo> \
GITHUB_ACTIONS=true CI=true \
python3 workflow-source/tests/run_all_checks.py --tmp-dir=<실디스크>
```

## 7. 남은 구멍 — ✅ 닫힘 (2026-08-13)

> 손 편집을 막을 자리가 없다. 작업 브랜치에 `active/<branch>/` 가 없다는 사실을
> 직접 지목하는 검사가 아직 없고, 3개 검사의 간접 증상으로만 드러난다.

`check_branch_memory_namespace` 신설로 닫혔다
([TASK-2026-08-13-fix-branch-memory-namespace-guard-001](../../../fix/branch-memory-namespace-guard/backlog/tasks/TASK-2026-08-13-fix-branch-memory-namespace-guard-001.md)).
구멍이 하나가 아니라 둘이었다 — (A) 작업 브랜치가 **다른 브랜치 네임스페이스에
추가/수정**(원인), (B) `active/<branch>/` **부재**(결과). §4 의 case 7 은 병합 *뒤*
흔적만 잡으므로, 브랜치에서 일하는 동안에는 여전히 아무도 지적하지 않았다.
새 검사는 커밋 전 워킹 트리까지 보고 A·B 를 직접 지목한다.

구멍을 메우다 **§4 의 진단 자체가 절반 틀렸다는 것**도 드러났다 (§4 의 정정 블록).
안내가 가리키던 `wk backlog-update` 는 절반짜리 네임스페이스를 만들어 3검사가 red 로
남는다 — 그래서 새 검사의 안내 문구는 `wk seed-workspace-memory` 를 가리킨다.
따라 하면 실제로 green 이 되지 않는 안내는 손 편집으로 도망갈 유인을 남긴다.
