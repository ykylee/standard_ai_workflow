# Workflow Deployment Idempotency

- 문서 목적: 언제·어떤 환경에서·어떤 프로젝트에·어떤 하네스 조합용으로 배포해도 **일관성과 멱등성**이 성립하도록, 배포를 하나의 함수로 정의하고 그 계약을 고정한다.
- 범위: 배포 함수 정의, 변수 5축, 3계약+1탐침 골격, 파일 소유권 3분류, 멀티 하네스 공존 규칙, 설치 스코프(글로벌/프로젝트) 규칙, 현재 구현 매핑과 gap
- 대상 독자: 저장소 관리자, 하네스 통합 담당자, AI workflow 설계자
- 상태: draft (2026-08-14 소유자 방향 승인 — 45차 세션)
- 최종 수정일: 2026-08-14
- 관련 문서: `./workflow_harness_distribution.md` (§2.1 채널×하네스 매트릭스), `./workflow_configuration_layers.md` (3계층·우선순위), `./workflow_global_injection_policy.md` (비침투 주입), `../workflow_kit/upgrade_diff.py` (적용 계약 구현), `../../docs/INSTALLATION_AND_USAGE.md` §7.0 (채널별 설치 명령), `../../docs/RELEASE.md` (패키지 채널 정책)

## 0. 배포는 함수다

> `deploy(버전, 하네스 집합, 설치 스코프, 프로젝트 상태) → 프로젝트 상태'`

- **일관성** = 같은 입력이면 언제 어디서 누가 실행해도 같은 출력.
- **멱등성** = `deploy ∘ deploy = deploy`. 재실행이 한 번 실행과 같고, 사용자 작업을
  파괴하지 않는다.

함수가 순수해지려면 (1) 변수가 전부 **입력으로 명시**되고, (2) 출력의 소유권이 파일
단위로 **분류**되어 있어야 하며, (3) 출력을 **검증하는 탐침**이 있어야 한다.

## 1. 변수 5축 — 무엇이 결과를 흔드는가

| 축 | 변수 | 실측된 함정 (전부 이 저장소에서 실제로 밟았다) |
|---|---|---|
| **시간** | kit 버전 · 소비자에 이미 깔린 버전 | 쓰는 쪽을 먼저 바꾸면 옛 리더가 못 읽는다 (TASK-2026-08-14-main-009, 라벨 전환) |
| **환경** | OS · python/venv · 온라인/오프라인 | PEP 668 거부, uv venv 의 pip 부재, 시스템 python 으로 검사 시 의존성 오탐 무더기 (main-019) |
| **프로젝트** | 신규 / 기존 적용 / 부분 적용 / 사용자 수정 있음 | 기존 `AGENTS.md` 보유 프로젝트, 브랜치 메모리 미seed 가 CI 를 red 로 (PR #26) |
| **하네스** | **집합이다** — 한 환경에서 여러 하네스 동시 사용 | Codex+Grok 동시 적용 시 `AGENTS.md` 1회 emit, `GROK.md` 는 additive (§4) |
| **설치 스코프** | 글로벌(사용자 홈) / 프로젝트 로컬 / **양쪽 기설치** | Claude 플러그인 선언은 user settings 에 살고 외부 도구가 지울 수 있다 (실측 1회), mavis 는 글로벌 한 곳만 읽는다 (§5) |

## 2. 골격 — 3계약 + 1탐침

```
배포 = 선언(registry) → 적용(소유권 3분류) → 검증(post-apply probe)
                ↑                                        |
                └────── 드리프트 감지 (버전 마커 → 정본 비교) ←┘
```

| 계약 | 내용 | 현재 구현 |
|---|---|---|
| **선언** — 무엇이 깔리는가 | registry 가 정본, 산출물은 파생. 손 목록 금지 | `HARNESS_SPECS` · `PLUGIN_HARNESS_SPECS` · `PLUGIN_SKILLS` — "정본을 바꾸면 산출물이 따라 바뀐다" 를 검사가 강제 |
| **적용** — 어떻게 깔리는가 | 파일 소유권 3분류(§3) + 재실행 안전(§6 원칙 B) | `upgrade_diff.decide_action` (smart update), seed 의 create-if-absent |
| **호환** — 낡은 소비자 | 리더 먼저, deprecation 1-release 창구 | 라벨 registry 전환 절차가 산 예시 |
| **탐침** — 깔린 뒤 확인 | 버전·구성·로드 가능성을 한 명령으로 | `wk doctor` (`workflow_kit.deploy_doctor`) — environment/project_scope/global_scope/drift 4절, report-only. `check_deploy_doctor` 9 cases |

## 3. 파일 소유권 3분류 — 멱등성의 근거

멱등성은 "이 파일을 누가 소유하는가" 가 파일마다 명시돼야 성립한다.

| 분류 | 규칙 | 구현 |
|---|---|---|
| **kit 소유** (generated) | 버전 마커(`<!-- standard-ai-workflow-kit: vX -->`) 우선 + content hash 로 비교. **새것일 때만** 덮는다 | `decide_action` — v0.5.10.1+ smart update |
| **공유** (진입점) | 덮지 않고 **병합**. 여러 하네스가 같은 파일을 쓸 때 1회만 emit | `AGENTS.md` dispatch block, `@AGENTS.md` import |
| **불가침** (사용자 상태) | `--force` 로도 덮지 않는다 | `PRESERVE_RELATIVE_PATHS` (`memory/active` 등) — `decide_action` PRESERVED |

새 산출물을 추가할 때는 **셋 중 하나로 반드시 분류**한다. 분류가 없는 파일이 곧
"재실행이 무엇을 할지 모르는 파일" 이다.

## 4. 멀티 하네스 공존 — 하네스는 집합 인자다

한 환경/프로젝트에서 여러 하네스를 함께 쓰는 것이 정상 케이스다 (예: Claude Code +
Codex + Grok Build). 규칙:

1. **공유 진입점은 1회 emit** — `AGENTS.md` 는 codex/opencode/pi-dev/grok-build 가
   공유하며 dispatch block 이 중복 emit 을 막는다. 동시 선택이 아니라 **순차 적용**
   (오늘 codex, 다음 주 grok)이어도 결과가 같아야 한다 — 이것이 멱등성의 하네스판이다.
2. **하네스 전용 진입점은 additive rule** — `GROK.md`/`CLAUDE.md` 는 공유 진입점을
   master 로 참조하고 자기 하네스 고유분만 더한다. 두 문서의 공통 baseline 은 동일하게
   유지한다 (같은 정본에서 파생).
3. **규칙 이중 주입 방지** — 플러그인 hook 이 세션 시작에 규칙을 주입하기 전에
   진입점 파일(`CLAUDE.md`/`GROK.md`/`@AGENTS.md`)에 이미 규칙이 있는지 **탐침**한다.
   bootstrap 로 이미 주입된 프로젝트에 플러그인을 또 설치해도 규칙이 두 번 들어가지
   않는다 (PR #27 의 SessionStart 탐침이 구현 예).
4. **하네스 간 충돌은 채널이 아니라 파일 소유권으로 푼다** — 두 하네스가 같은 파일을
   요구하면 그 파일은 §3 의 "공유" 로 분류하고 병합 규칙을 정의한다. 채널별 예외를
   만들지 않는다.

## 5. 설치 스코프 — 글로벌·프로젝트·양쪽 기설치

플러그인/스킬은 **글로벌**(사용자 홈: `~/.claude/settings.json` 의 enabledPlugins,
`~/.grok/`, `~/.minimax/mcp/mcp.json`)과 **프로젝트 로컬**(`.claude/skills/`,
`.grok/`, `.opencode/` 등)에 각각, 또는 **양쪽에 동시에** 깔려 있을 수 있다.

우선순위는 `workflow_configuration_layers.md` §3 을 그대로 승계한다:
**Project Local > Shared > Harness Global.**

스코프 규칙:

1. **글로벌 설치는 비침투** — 사용자 전역 설정의 기존 항목을 덮지 않는다
   (`workflow_global_injection_policy.md`). 글로벌 merge 는 atomic + backup + 기존
   항목 보존이 계약이다 (mavis 글로벌 mcp.json merge 가 구현 예 — builtin 5종 보존).
2. **양쪽 기설치는 오류가 아니라 상태다** — 같은 스킬이 글로벌과 프로젝트에 둘 다
   있으면: 로드는 하네스의 우선순위 규칙(대개 project 우선)을 따르고, 배포 도구는
   **감지하고 보고**하되 어느 쪽도 임의로 지우지 않는다. 제거는 사용자 결정이다.
3. **스코프 간 버전 어긋남은 드리프트로 보고** — 글로벌 v1.1, 프로젝트 v1.2 같은
   상태를 탐침(§7)이 표로 보여준다. "동작은 하는데 왜 옛 동작이지" 의 대부분이
   이 케이스다.
4. **선언의 거주지를 기록** — 설치 선언이 어디 사는지(예: Claude 는 user settings)를
   하네스별로 명시한다. 그 자리를 재작성하는 외부 도구가 있으면 선언이 소실될 수
   있고(실측 1회), 그때의 복구 명령이 문서에 있어야 한다 (INSTALLATION §7.0).
5. **스코프도 함수 입력이다** — 같은 명령이 스코프에 따라 다른 곳에 쓰면 안 된다.
   글로벌/프로젝트는 명시 인자(또는 하네스의 고정 규약)로 갈라져야 한다.

## 6. 운영 원칙 4개

- **A. 채널이 달라도 계약은 하나** — 플러그인 5·오버레이 13·패키지 채널 모두 같은
  3분류와 같은 탐침을 통과한다. 채널은 운송 수단이지 규칙이 아니다.
- **B. 재실행은 언제나 안전** — 무인자 재실행 = 관찰(변경 없으면 no-op 보고),
  `--force` 만 파괴적이며 그마저 불가침(§3)은 못 넘는다.
- **C. 깔린 것은 스스로 말한다** — 모든 kit 소유 산출물에 버전 마커. 탐침 한 명령이
  "무엇이·어떤 버전으로·어느 스코프에·온전하게" 깔렸는지 보고한다.
- **D. 낡은 소비자를 깨뜨리지 않는다** — 리더 먼저, 1-release deprecation 창구.

## 7. 현재 gap — 구현 순서 제안

| # | gap | 왜 | 상태 |
|---|---|---|---|
| 1 | **post-apply 탐침 부재** | 지금은 "설치 명령 성공" 이 끝. 출력 검증이 없다 | ✅ **해소** (2026-08-16, TASK-2026-08-14-main-016) — `wk doctor`. 설치 안내는 `docs/INSTALLATION_AND_USAGE.md` §7.0.1 |
| 2 | **채널 간 적용 계약 불일치** | smart update 는 bootstrap 채널 규율. 플러그인 5채널은 하네스 설치기가 제각각 | 열림 — 채널별 "재실행 시 무슨 일이 나는가" 를 §7.0 에 표로 고정 + 탐침이 검증 (TASK-2026-08-14-main-017) |
| 3 | **드리프트 감지 부재** | 마커에 버전이 있는데 읽는 도구가 없다 | **부분 해소** — 탐침의 `drift` 절이 마커 스캔·스코프 간 어긋남을 본다. **잔여: 내용 드리프트** (아래) |
| 4 | **환경 전제 미계약** | venv/오프라인 전제가 문서에 흩어져 있고 도구가 선검사 안 함 | **부분 해소** — 탐침의 `environment` 절이 venv·PEP 668·`wk` PATH·import 를 본다. 잔여: 채널별 설치 안내 첫 줄의 전제 명시 (TASK-2026-08-14-main-019) |

**gap 3 의 잔여 — 마커가 같아도 내용은 낡을 수 있다.** 2026-08-16 에 Codex
플러그인이 정확히 그 상태였다: 버전 문자열은 `1.2.0` 으로 정본과 같은데 페이로드
내용만 구버전(KO 단일 description, `rollover-baselines` 항목 누락)이었다.
**버전 비교로는 원리적으로 안 걸린다.** 내용까지 보려면 마커가 아니라 페이로드
해시를 비교해야 한다 — 탐침의 출력이 이 한계를 스스로 밝히고 있다
(`drift.limitation`). 해시 비교는 TASK-2026-08-14-main-018 로 이월.

**탐침이 지키는 계약 3개** (구현과 검사가 함께 고정한다):

1. **report-only** — 아무것도 쓰지 않는다 (§5.2). `check_deploy_doctor` case 2 가
   트리 지문 대조로 고정하고, 지문 자체가 쓰기를 구분하는지까지 되주입으로 확인한다.
2. **기본 rc 0** — 발견은 보고이지 실패가 아니다. `--strict` 만 rc 1 (case 7).
3. **존재는 적용이 아니다** — kit 소유 표식(버전 마커, §3)이 있는 것만 적용으로
   센다 (case 4). 실측: 다른 도구가 쓴 `AGENTS.md` **하나**가 codex·grok-build·
   minimax-code·opencode·pi-dev **5개 하네스를 적용됨으로** 만들었다.

## 다음에 읽을 문서

- 채널×하네스 매트릭스: [./workflow_harness_distribution.md](./workflow_harness_distribution.md) §2.1
- 설정 계층과 우선순위: [./workflow_configuration_layers.md](./workflow_configuration_layers.md)
- 비침투 주입 원칙: [./workflow_global_injection_policy.md](./workflow_global_injection_policy.md)
- 채널별 설치 명령 정본: `docs/INSTALLATION_AND_USAGE.md` §7.0
