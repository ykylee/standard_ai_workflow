# Beta v1.14.0 (2026-09-28)

> **상태: 릴리스 준비.** package `1.14.0`, runtime `__version__ = 1.14.0`, tag `v1.14.0`.
> **minor release** — **Antigravity 에서 MCP 도구가 하나도 안 뜨던 결함 수리 + `wk doctor` 가
> "설치됐는데 꺼진 플러그인" 을 4채널에서 잰다.**
>
> 등급 근거 (§1.5): `wk release-status` 는 feat 2 · breaking 0 으로 **1.14.0 (minor)** 을 제안하고
> 그대로 따른다. Antigravity 의 도구 이름이 바뀌지만(§2.1) 옛 이름은 **전부 무효**였으므로 그
> 이름에 기대던 소비자는 없다.

## 0. 릴리스 판정

v1.13.0 까지 Antigravity 플러그인 채널은 skills 4종만 동작하고 read-only MCP 도구 11종은
**조용히 전부 버려지고** 있었다. 설치·검증(`agy plugin validate`)·`wk doctor` 어디에서도
red 가 아니었다 — 거부는 `agy --log-file` 에만 남았다. 이 수리가 소비자에게 닿는 길은 새
payload 배포뿐이라 발행한다.

## 1. 릴리스 요약

- 범위: `v1.13.0..` 발행 준비 직전까지 **7 commit**. 이 중 1건(`756a181e`)은 **v1.13.0 발행
  마무리**가 태그 뒤에 착지한 것이고 3건은 memory 기록이라 실질은 **3 commit** 이다.
- 누적 smoke **296/296 PASS** (로컬 `--branch-context=all` = 296 × native/slash).
- 검사 **296 → 296** (신설·은퇴 없음 — 기존 검사에 case 추가).

## 2. 소비자에게 보이는 변화

### 2.1 Antigravity 에서 MCP 도구 11종이 뜬다 (`0a232c99`, TASK-2026-09-28-main-020)

agy 1.0.16 은 플러그인 MCP 도구 이름을 `mcp_<플러그인>_<서버 별칭>_<도구>` 로 합성하고
`^[a-zA-Z0-9_-]{1,64}$` 에 어긋나면 버린다. 공용 별칭 `standardAiWorkflowReadOnly` 로는 66~82자라
**11/11 이 거부**됐다. 이제 Antigravity 사본 `plugin/mcp_config.json` 만 별칭 `ro` 를 쓴다 —
도구 이름은 `mcp_standard-ai-workflow_ro_<도구>`(최장 58자). 다른 채널의 공용 별칭과 도구
이름(`mcp__standardAiWorkflowReadOnly__…`)은 그대로다.

**적용**: Antigravity 사용자는 `agy plugin install <경로>/plugin` 으로 다시 설치한다.

### 2.2 `wk doctor` 의 `plugin_enabled` 절 — 설치 ≠ 활성 (`880f8327` · `90e3d52a` · `0a232c99`)

`claude plugin update` 직후 `enabledPlugins` 선언이 사라져 스킬이 조용히 없어진 실측
(TASK-2026-09-28-main-017)에서 출발했다. 사본·설치 기록·프로세스를 재는 절은 전부 green
이었다. 새 절은 채널별 활성 선언을 읽고 **키 부재**와 **명시 false** 를 다른 문장·처방으로 낸다.

| 채널 | 선언 자리 | 발견이 되는 상태 |
|---|---|---|
| claude-code | `enabledPlugins["<plugin>@<market>"]` | 키 부재 · false |
| codex | `~/.codex/config.toml` `[plugins."…"] enabled` | 블록에 `enabled` 없음 · false |
| grok-build | `~/.grok/config.toml` `[plugins] disabled` | `disabled` 에 있을 때만 — 양쪽 목록 부재는 **기본 로드** |
| antigravity | `~/.gemini/config/config.json` `plugins.<이름>.enabled` | false 만 — 부재는 자동 발견 로드 |

grok · antigravity 의 "부재 = 로드" 는 실제 세션으로 쟀다 (TASK-2026-09-28-main-019): grok 은
`grok -p` 프롬프트가 enabled 와 바이트 동일, antigravity 는 `agy -p --log-file` 의 MCP 로드 줄.
워크스페이스 `plugins.json` 의 `exclude` 는 자기 `entries` 만 걸러 자동 발견 설치본을 끄지 못한다.

## 3. 검증

- 전량 게이트 `--branch-context=all` — 발행 준비 커밋에서 실행 (결과는 발행 기록에 남긴다)
- Antigravity: `check_agent_plugin_payload` case 14 가 정본 도구 목록에서 합성 이름을 파생해
  64자 계약을 잰다. 되주입 2종(별칭 상수 복귀 / 렌더러가 별칭 무시) 각각 red. 실호스트에서
  `agy plugin install` 뒤 `invalid tool` 0 (수리 전 11)
- doctor: `check_deploy_doctor` 52 case, grok 부재 판정 되주입 2종 red

## 4. 알려진 한계 (감추지 않는다)

- Antigravity 에서 도구가 **로드**되는 것까지 쟀고, 실제 **호출**은 재지 않았다.
- Antigravity 의 bootstrap 채널(`~/.gemini/config/mcp_config.json`) 합성 규칙은 미실측이다.
- 미측정으로 남은 활성 축: Antigravity IDE 패널 토글, grok 이 disabled 일 때 hook 실행 여부
  (`plugin_enabled.declared_unmeasured`).
- **Windows 는 현재 미측정이다** (`TASK-2026-08-25-main-017` blocked).

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-09-29T00:06:30Z)_

- total wiki pages: **96**
- total memory entries: **30**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
