# Beta v1.16.0 (2026-09-30)

> **상태: 릴리스 준비.** package `1.16.0`, runtime `__version__ = 1.16.0`, tag `v1.16.0`.
> **minor release** — compact 중계를 **Codex 플러그인에서도** 돌게 한다 (hook 3종 탑재 + Codex 출력 형식).
>
> 등급 근거 (§1.5): `wk release-status` 의 파생 근거는 feat 1 · fix 1 · breaking 0 — **minor**.
> 공개 Python API 는 **추가만** 있다 — `compact_relay.OUTPUT_FORMATS` · `OUTPUT_TEXT` · `OUTPUT_CODEX_JSON` ·
> `codex_system_message` · `codex_additional_context`. `wk compact-checkpoint` 에 인자 `--output-format`
> (기본값 `text` — 기존 호출 그대로)가 늘었다. 진입점 증감 0.

## 0. 릴리스 판정

v1.15.0 의 compact 중계는 Codex 에서 돌지 않았다 — Codex manifest 에 hook 이 없었고(v1.15.0 노트 §4),
이번 사이클에 싣고 나서 인증 압축 왕복으로 재 보니 **싣기만 해서는 재주입이 모델에 닿지 않았다**(§2.2).
두 커밋이 합쳐져야 Codex 소비자에게 동작하는 기능이 되므로 함께 발행한다.

## 1. 릴리스 요약

- 범위: `v1.15.0..` 발행 준비 직전까지 **5 commit** — 1건(`672fa400`)은 v1.15.0 발행 마무리가 태그 뒤에
  착지한 것이고 2건은 세션 기록이라 실질은 **2 commit** (`0baeb787` · `8a35197b`).
- 누적 smoke **298/298 PASS** (로컬 `--branch-context=all` = 298 × native/slash).
- 검사 수 **298 → 298** (신설 0 — `check_compact_relay` 가 12 → 15 cases).

## 2. 소비자에게 보이는 변화

### 2.1 Codex 플러그인에 compact 중계 hook 3종 (`0baeb787`, TASK-2026-09-30-main-008)

- 전용 사본 `plugin/adapters/codex/hooks.json` 에 `PreCompact` · `PostCompact` · `SessionStart(compact)` 만
  싣고 Codex manifest 의 `hooks` 가 그것을 가리킨다. Codex 배포 zip 에 포함된다. 기본 경로
  `hooks/hooks.json`(Grok 사본)은 규칙 주입 이중화와 Codex 에 없는 `SessionEnd` 가 딸려 와 쓰지 않는다.
- **플러그인 hook 은 설치 직후 `untrusted` 이고 그 상태로는 돌지 않는다.** 사용자가 Codex TUI 의
  "Hooks need review" 에서 신뢰해야 한다. 신뢰는 handler 별 해시라 **명령이 바뀌는 업그레이드마다 다시
  `modified` 로 풀린다** — v1.16.0 으로 올리면 한 번 더 신뢰해야 한다.
- 하네스가 요약 원문을 주지 않으면(Codex `PostCompact` 입력에 `compact_summary` 필드가 없다) 대조하지 않고
  "요약 대조 불가" 로 말한다. 이전에는 빈 요약과 대조해 식별자 전부를 '누락' 으로 **날조**했다.

### 2.2 Codex hook 출력을 Codex wire JSON 으로 (`8a35197b`, TASK-2026-09-30-main-009 · 010)

**실측** (codex-cli 0.159.2, 인증된 격리 `CODEX_HOME`, app-server `thread/compact/start` 왕복): 발화 순서는
`PreCompact` → 원격 압축 → `PostCompact` → **다음 turn 시작 시** `SessionStart(compact)` (Claude Code 와
달리 재주입이 대조보다 뒤). 그런데 세 hook 모두 `failed` — "hook returned invalid … JSON output".
Codex 는 앞 공백을 걷은 stdout 이 `{` · `[` 로 시작하면 JSON 으로 파싱하고
(`codex-rs/hooks/src/engine/output_parser.rs` `looks_like_json`), 우리 머리말 `[compact-checkpoint]` 가
거기 걸렸다. checkpoint 파일은 써졌지만 재주입은 rollout 에 **없었다**.

- `wk compact-checkpoint --output-format codex-json` — 재주입 본문은
  `hookSpecificOutput.additionalContext`, 그 밖(기록 줄 · 대조 결과 · 실패)은 `systemMessage` 한 줄.
  hook 모드 밖(`--note` · `--clear`)에서는 exit 2.
- Codex hook 사본만 이 인자를 붙이고, 구버전 kit 실패 안내도 `systemMessage` JSON 으로 낸다
  (평문 `[standard-ai-workflow] …` 도 같은 오판에 걸린다). Claude Code · Grok 사본은 **변경 없음**.
- **재실측**: 세 hook `completed`, pre · post 는 경고 줄로 사용자에게 보이고, 재주입 본문이 rollout 에
  developer 메시지로 들어갔다.

**적용**: kit 과 플러그인을 **같은 버전(1.16.0)** 으로 올린 뒤 Codex 에서 hook 3종을 다시 신뢰한다.
플러그인만 새것이면 `--output-format` 을 모르는 kit 이 실패하고, 그 사실이 경고 한 줄로 뜬다
(압축은 막지 않는다).

## 3. 검증

- 전량 게이트 `--branch-context=all` — 발행 준비 커밋에서 실행 (결과는 발행 기록에 남긴다)
- `check_compact_relay` 15/15 — case 15 는 Codex 사본의 hook 명령을 **그대로** bash 로 돌려 stdout 을
  Codex 출력 스키마(`additionalProperties: false`)로 판정한다 (현재 kit · 구버전 kit · 깨진 stdin · 예외).
  결함 되주입 6건 각 해당 case red.
- Codex 0.159.2 격리 압축 왕복 — 수리 전 3종 `failed` · 재주입 0 / 수리 후 3종 `completed` · 재주입 도달.

## 4. 알려진 한계 (감추지 않는다)

- **Codex TUI 의 "Hooks need review" 화면은 실측하지 않았다** — 측정은 격리 config 에 신뢰 해시를 적어서
  했다. 문구는 바이너리 문자열 근거다.
- Codex `PostCompact` 는 요약 원문을 주지 않으므로 **요약 누락 대조는 Codex 에서 영영 "대조 불가"** 다.
- **자동 압축(`trigger: auto`) 경로는 두 하네스 모두 미실측**이다.
- `TASK-2026-08-25-main-017` (MCP emit command 가 항상 `python3`) 는 blocked 그대로다.
- minimax-code 플러그인 채널(`TASK-2026-09-30-main-001`)은 형식 미확정으로 planned 그대로다.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-09-30T05:55:44Z)_

- total wiki pages: **97**
- total memory entries: **30**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
