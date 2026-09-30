# compact 중계 — concept 검토

- 문서 목적: 하네스가 컨텍스트를 압축할 때 잃는 작업 상태를 워크플로우 메모리로 건너뛰게 하는 기능(스킬 + hook 2종)의 표면을 실측하고, 무엇을 싣는가 · 어디에 두는가 · 무엇을 새로 만드는가의 소유자 선택지를 판단 가능한 형태로 정리한다 (TASK-2026-09-30-main-003, M-018/WBS-18.1).
- 범위: 하네스별 compact 표면(명령 · hook · 재주입 경로), checkpoint 내용 · 위치 · 수명 · 동시 세션, 정본 §11.1 명령과 플러그인 파생 구조에 주는 영향, 재주입 분량 예산
- 대상 독자: 소유자 (M-018 다음 단계 결정), maintainer
- 상태: **종결 (2026-09-30)** — 소유자 결정 = **안 B** + 위치 §4 c + Grok 같은 사본·선언 + 재주입 예산 4KB 초안(requirements 에서 실측 확정). requirements 는 M-019
- 최종 수정일: 2026-09-30
- 관련 문서: [`M-018`](../../ai-workflow/memory/active/roadmap/M-018-compact-relay.md), [`session_context_budget_spec.md`](../../workflow-source/core/session_context_budget_spec.md) (재주입 분량), [`session-context-budget-review-2026-09.md`](./session-context-budget-review-2026-09.md) (같은 형식의 선행 concept), [`plugin_payload.py`](../../workflow-source/workflow_kit/plugin_payload.py) (스킬·hook 파생)

## 0. 한 줄 결론

> Claude Code 에는 **압축 전 기록 → 압축 → 압축 뒤 재주입** 세 지점이 모두 있고, 이 호스트에서
> 실측으로 끝까지 통했다 (§2.1). 게다가 `PostCompact` 가 **하네스가 만든 요약 원문**을 넘겨준다 —
> checkpoint 와 요약을 대조하면 "요약이 무엇을 잃었는가" 를 **잴 수 있다**. 다만 이식성은 좁다:
> 같은 모양을 가진 것은 Codex 와 mcode(비공식) 뿐이고, Grok 은 재주입이 막혀 있고, Antigravity 는
> 압축 hook 이 없다 (§2.2). 그래서 **스킬(수동)을 이식 가능한 층, hook 을 하네스별 가속 층**으로
> 나누는 안을 권한다 (§7 안 B).

## 1. 전제 — 무엇을 하지 않는가

1. **`session_handoff.md` 에 쓰지 않는다** (착수 시 소유자 결정). handoff 는 `state.json` 생성기의
   입력이다 — 세션 도중 기계가 쓰면 형식이 조용히 깨진다.
2. **요약을 대체하지 않는다.** 압축 요약은 하네스가 만든다. checkpoint 는 그 옆에 놓이는 **근거
   기록**이다. (pi 는 extension 이 요약을 통째로 갈아 끼울 수 있지만, §2.2 의 이유로 범위 밖이다.)
3. **transcript 를 파싱하지 않는다.** `PreCompact` 가 `transcript_path` 를 주지만 그 JSONL 형식은
   공개 계약이 아니다 — 이번 실측에서도 레코드 종류가 `attachment` · `atis-latch` · `queue-operation` 등
   10종이었다. 하네스 버전마다 바뀌는 형식에 기대면 코드가 그대로여도 측정이 바뀐다.
4. **재주입된 내용은 지시가 아니라 상태다.** 실측에서 모델은 hook 이 넣은 줄을 "사용자가 시키지 않았으니
   할 일로 세지 않는다" 고 답했다 (§2.1-④). 이것은 옳은 행동이다 — checkpoint 는 "무엇을 하라" 가
   아니라 "어디까지 왔고 무엇이 검증됐는가" 로 쓴다.

## 2. 실측

### 2.1 Claude Code 2.1.285 — 이 호스트, 2026-09-30

임시 git 저장소에서 `--settings` 로 `PreCompact` · `PostCompact` · `SessionStart(matcher=compact)` hook 을
걸고, 대화 한 턴 → `--resume` 으로 `/compact keep the code word` → 한 턴 더. 스크립트와 덤프는
세션 scratchpad (`compact-probe/`) 에 있다.

| # | 확인한 것 | 결과 |
|---|---|---|
| ① | `PreCompact` 입력 | `session_id` · `transcript_path` · `cwd` · `prompt_id` · `hook_event_name` · **`trigger`**(`manual`) · **`custom_instructions`**(`/compact` 뒤 문자열 원문) |
| ② | `PostCompact` 입력 | 위 공통 필드 + `trigger` + **`compact_summary`** (요약 원문 — `<analysis>` + `<summary>` 9절, 이번 표본 2.3KB) |
| ③ | `SessionStart` 재발화 | 압축 직후 `source: "compact"`, `model` 필드 포함. matcher `compact` 가 걸렸다 |
| ④ | 재주입 | `SessionStart(compact)` 의 stdout 한 줄이 다음 턴 컨텍스트에 있었다 (모델이 원문 인용). 모델은 그것을 **할 일로 취급하지 않았다** |
| ⑤ | `PreCompact` stdout | 요약 입력에 들어가지 **않는다** — 압축 뒤 `<local-command-stdout>` 로 사용자 화면에만 표시 |
| ⑥ | 요약이 이미 보는 것 | 설치된 이 플러그인의 matcher 없는 `SessionStart` hook(규칙 블록 주입)이 요약 안에 "배경 규칙" 으로 언급됐다 — 플러그인 hook 은 압축 경계와 무관하게 이미 돌고 있다 |
| ⑦ | 빈 대화에서 `/compact` | `PreCompact` 는 발화, 압축·`PostCompact` 는 없음 (정상 종료) |

문서 쪽 사실 (출처: code.claude.com/docs `hooks-guide` · `memory` · `commands`): 루트 `CLAUDE.md` 는 압축 뒤
디스크에서 다시 읽힌다 · 스킬 설명은 압축 뒤 재주입되지 않는다(호출한 스킬만 남는다) · 스킬은 `/compact`
를 스스로 실행할 수 없다 · `PreCompact` 는 압축을 막거나 바꾸지 못한다.

**재지 못한 것**: 재주입 크기 상한 (문서에 일부 hook 출력 10,000자 언급이 있으나 `SessionStart` 에
대한 명시 없음) · 자동 압축(`trigger: auto`)에서의 같은 흐름 (headless 로 한계까지 채우기 어렵다) ·
**플러그인으로 배포한 hook** 의 matcher 동작 (이번 실측은 `--settings` hook).

### 2.2 다른 하네스 — 문서·출하 코드 조사 (2026-09-30)

| 하네스 | 수동 / 자동 압축 | 압축 전 | 압축 뒤 재주입 | 지시문 전달 |
|---|---|---|---|---|
| **Claude Code** | `/compact [지시]` / 자동 | `PreCompact` (수동적) | `SessionStart(compact)` stdout ✅ 실측 | `custom_instructions` ✅ |
| **Codex CLI** | `/compact` (인자 없음) / 자동 | `PreCompact` (`continue:false` 로 **차단 가능**) | `SessionStart(compact)` · `additionalContext` | 설정 `compact_prompt` 만 |
| **mcode 0.5.9** | `/compact [지시]` / 자동 | `PreCompact` (`custom_instructions`) | `PostCompact(compact_summary)` → `SessionStart(compact)` | ✅ — **출하 번들에서만 확인, 문서 없음** |
| **Grok Build** | `/compact` / 자동 85% | `PreCompact` (수동적, 출력 무시) | ❌ `SessionStart` stdout 무시 | 없음 |
| **Antigravity** | 자동만 (`/compact` 요청 이슈 #999 open) | ❌ 압축 이벤트 없음 | ❌ | 없음 |
| **pi** | `/compact [지시]` / 자동 | TS extension `session_before_compact` (요약 대체 가능) | 없음 (`session_start` 에 compact 사유 없음) | ✅ |
| **OpenCode** | `/compact` / 자동 | JS plugin `experimental.session.compacting` (context 추가 · prompt 대체) | 없음 | 플러그인 경유만 |

출처: Codex `learn.chatgpt.com/docs/hooks` · `codex-rs/tui/src/slash_command.rs`; Grok `xai-org/grok-build`
`docs/user-guide/10-hooks.md`; Antigravity `antigravity.google/docs/hooks` · `antigravity-cli` #999;
pi `pi-mono` `docs/compaction.md` · `extensions/types.ts`; mcode npm `@minimax-ai/code` 0.5.9 번들
`chunk-6ETTLULN.js`; OpenCode `opencode.ai/docs/plugins` · `packages/plugin/src/index.ts`.

읽는 법:

- **같은 모양 (Pre + Post + 재주입)**: Claude Code · Codex · mcode. 이 셋은 command hook 한 벌로 덮을 수
  있다 — 단 Codex 는 입력 필드가 다르고(`custom_instructions` 없음, `turn_id` 있음) 플러그인 hook 적재가
  이 payload 로 미실측, mcode 는 문서가 없어 언제든 바뀔 수 있다.
- **pi · OpenCode**: 압축 표면이 가장 강하지만 TS/JS 런타임 extension 이다 — `PURPOSE.md` §3 제외 영역
  "non-Python 기반 runtime" 에 걸린다. 이 축에서 다루지 않는다.
- **Grok · Antigravity**: hook 층이 성립하지 않는다. **스킬(수동)만** 통한다.
- **공유 사본 문제**: `plugin/hooks/hooks.json` 은 Claude 어댑터 hook 의 **동일 사본**이고 Grok 이 그 경로를
  읽는다. `PreCompact` 를 넣어도 Grok 에서는 수동적 이벤트라 무해하지만, Grok 사용자는 재주입이 없다는
  사실을 모른다 — 선언이 필요하다.

## 3. checkpoint 에 무엇을 싣는가

두 층의 작성자가 다르다.

| 항목 | 기계 (hook) | 판단 (스킬) | 출처 |
|---|---|---|---|
| 브랜치 · HEAD · 미커밋 파일 목록 | ✅ | | `git` |
| `in_progress` / `blocked` task ID + 제목 | ✅ | | `backlog/tasks/` frontmatter (SSOT) |
| 현재 마일스톤 · WBS | ✅ | | `roadmap_state.json` |
| `/compact` 지시문 원문 · trigger | ✅ | | `PreCompact` 입력 |
| 검증된 사실 / **미검증** 사실 (명령 + 결과) | | ✅ | 모델만 안다 |
| 방금 기각한 안과 이유 | | ✅ | 모델만 안다 |
| 다음 한 걸음 | | ✅ | 모델만 안다 |
| 하네스 요약 원문 | `PostCompact` | | §5 대조 재료 |

기계 층만으로도 "어떤 task 를 하던 중이었나" 는 복원된다. 그러나 압축이 가장 자주 지우는 것은
**"확인했다 / 아직 안 확인했다" 의 구분**이다 — 요약은 결론만 남기고 근거를 버린다. 이 저장소의 원칙
"검증 안 된 결과를 done 으로 표시하지 않는다" 가 압축 경계에서 깨지는 경로가 바로 그것이라, 스킬 층을
버리면 기능의 핵심이 빠진다. **자동 압축은 스킬이 못 부르므로** 그때는 기계 층만 남는다 — 이 차이는
재주입 머리말에 "판단 층 없음 (자동 압축)" 으로 적는다 (조용한 fallback 금지).

## 4. 어디에 두는가 — 위치 · 수명 · 동시 세션

**위치 후보**

| 안 | 경로 | 장점 | 문제 |
|---|---|---|---|
| a | `active/<branch>/compact_checkpoint.md` (커밋) | 다른 호스트에서도 보인다 | 세션 도중 커밋 대상이 생긴다 · 두 에이전트가 같은 파일을 덮는다 |
| b | `active/<branch>/.compact/<session_id>.md` (gitignore) | 세션별 격리 · 커밋 오염 없음 | 스킬(모델)은 `session_id` 를 모른다 |
| c | 워크트리 로컬 `active/<branch>/.compact/current.md` (gitignore) | 스킬도 hook 도 같은 경로를 안다 | 한 워크트리에 세션 둘이면 충돌 — 단 `CLAUDE.md` 는 이미 "두 에이전트는 워크트리를 나눈다" |

**권장: c** — 스킬이 쓴 판단 층을 다음 `PreCompact` hook 이 기계 층과 합쳐 같은 파일에 확정한다. 한 워크트리
동시 세션은 `session_id` 를 파일 머리에 적고, 재주입 시 불일치하면 **내용을 넣지 않고 불일치만 알린다**
(남의 checkpoint 를 자기 것으로 믿는 것이 가장 나쁜 실패다).

**수명**: 재주입은 소비가 아니다 — 같은 세션에 압축이 두 번 오면 앞 checkpoint 위에 갱신된다. 세션 종료
(`session-end`) 때 남길 가치가 있는 줄은 handoff 로 옮기고 파일은 지운다. **커밋하지 않는다** — 세션을
넘어 남는 정본은 여전히 handoff · backlog 다.

**예산**: `wk session-start` 출력이 13.5KB 다 (이 저장소 실측). 재주입까지 그 크기면 압축이 줄인 것을
도로 채운다. checkpoint 재주입은 **별도 예산 레코드**(초안: 4KB)로 `session_context_budget_spec` §1 에
올리는 것을 requirements 에서 정한다.

## 5. '잃지 않음' 을 재는 법

`PostCompact.compact_summary` 가 있으므로, checkpoint 의 **식별자형 항목**(task ID · 파일 경로 · 커밋 sha ·
"미검증" 표지가 붙은 항목) 중 요약에 나타나지 않은 것을 뽑을 수 있다. 재주입 머리말에 "요약에서 빠진 항목
N개" 를 숫자로 싣는다 — 재주입이 실제로 무엇을 되살렸는지가 보이고, 0 이 계속되면 기능이 쓸모없다는
증거도 된다. 자연어 항목은 대조하지 않는다 (위양성).

## 6. 새로 만드는 것 — 정본과 파생

- **§11.1 명령 신설이 필요하다.** `PLUGIN_SKILLS` 는 정본 §11.1 명령과 1:1 이다 (session-end 가 명령만 있고
  스킬이 없어 단계를 못 밟던 선례). 초안: `wk compact-checkpoint` (기록 · 합치기) + `--restore` (재주입 출력).
  §11.1 에 한 줄이 늘면 모든 진입점의 생성 규칙 블록이 바뀐다 → `check_standard_single_source` · bootstrap
  진입점 · `rules.md` 가 함께 움직인다 (정본 개정 1회).
- **hook 은 `render_claude_code_hooks` 에 추가**한다 — `PreCompact` · `PostCompact` · `SessionStart(matcher=compact)`.
  명령 문자열은 §11.1 파생 (`find_memory_command`).
- **스킬 `compact`**: checkpoint 판단 층을 쓰고, 사용자가 붙여 넣을 `/compact <지시문>` 을 만든다 (스킬은
  `/compact` 를 실행하지 못한다). 지시문은 "checkpoint 경로의 항목을 요약에 보존하라" 한 줄이면 충분하다.
- **`.gitignore`**: `active/*/.compact/` — 소비자 bootstrap 이 심는 `.gitignore` 에도.

## 7. 소유자 선택지

| 안 | 내용 | 덮는 하네스 | 비용 |
|---|---|---|---|
| **A** 최소 | 스킬 + `PreCompact`/`SessionStart(compact)` hook, 기계 층 + 판단 층 | Claude Code (실측), Codex·mcode 는 같은 JSON 이 통할 수도 | §11.1 명령 1 + 렌더러 + 검사 |
| **B** A + 대조 (권장) | A + `PostCompact` 요약 보관 + §5 누락 계수를 재주입 머리말에 | 같음 | A + 대조 로직 · 요약 원문 보관(gitignore) |
| **C** B + 하네스 확장 | B + Codex 플러그인 hook 실측·필드 차이 흡수 + mcode 어댑터 | Claude · Codex · mcode | Codex 호스트 실측 필요 · mcode 는 TASK-2026-09-30-main-001(채널 미지원)에 막힘 |

**권장: B.** 근거: 기능의 가치가 "요약이 잃은 것을 되살린다" 인데, A 는 되살렸는지 **재지 못한다**
— 이 저장소가 반복해서 겪은 '고친 것 없이 숫자만 좋아진다' 의 반대편, '고쳤는지 모른다' 가 된다.
C 의 Codex 흡수는 requirements 에 **미실측 칸**으로 남기고 별도 leaf 로 뺀다.

**함께 정할 것**

1. checkpoint 위치 — §4 **c** (워크트리 로컬 · gitignore · 커밋 안 함) 로 가는가.
2. Grok 공유 사본 — 같은 `hooks/hooks.json` 에 압축 hook 을 싣고 "Grok 은 재주입 없음" 을 선언하는가,
   Grok 사본을 분리하는가. (권장: 같은 사본 + 선언 — 사본을 가르면 정본이 둘이 된다)
3. 재주입 예산 — 4KB 초안을 requirements 에서 실측으로 확정하는가.

## 8. 미실측 · 리스크

- 플러그인 배포 hook 의 `matcher: compact` 동작 · 자동 압축 경로 — design 전에 실측한다.
- mcode 의 압축 hook 은 문서화되지 않은 출하 코드다 — 채널 지원(main-001)이 먼저다.
- 재주입 크기 상한 미확인 — 예산을 상한보다 충분히 작게 두면 영향이 없지만, 넘치면 조용히 잘릴 수 있다.
- 모델이 재주입을 "할 일 아님" 으로 다루는 것은 의도된 동작이지만, 반대로 **checkpoint 를 무시할** 수도 있다
  — 스킬 본문이 "압축 뒤 checkpoint 머리말을 먼저 확인한다" 를 절차로 갖는다.

## 9. 소유자 결정 (2026-09-30, 107차)

권장안대로:

1. 범위 = **안 B** — 스킬 + `PreCompact` · `PostCompact` · `SessionStart(compact)` hook, 기계 층 + 판단 층,
   `PostCompact` 요약 보관 + 식별자형 누락 계수를 재주입 머리말에. Codex 흡수는 requirements 의 미실측 칸.
2. 위치 = §4 **c** — 워크트리 로컬 `active/<branch>/.compact/current.md`, gitignore, 커밋 안 함,
   `session_id` 불일치 시 내용 대신 불일치만 알림.
3. Grok = 같은 `hooks/hooks.json` 사본 + "Grok 은 재주입 없음" 선언.
4. 재주입 예산 = 4KB 초안, requirements 에서 실측으로 확정.

requirements 단계는 [`M-019`](../../ai-workflow/memory/active/roadmap/M-019-compact-relay-requirements.md) 로 이어진다.
