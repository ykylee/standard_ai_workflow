# Anthropic "The AI-native SDLC playbook" — 조사 정리와 적용 검토

- 문서 목적: Anthropic 이 공개한 "The AI-native SDLC playbook" 의 내용을 원문 출처와 함께 정리하고, 이 저장소의 표준 워크플로우(로드맵·SDLC 어휘 ADR-027, 메모리, 게이트, 플러그인)에 가져올 부분을 소유자가 판단할 수 있는 형태로 정리한다 (TASK-2026-10-05-main-001).
- 범위: 블로그 글 1편 + Claude Academy 과정 14개 장(본문 13장 + 수료 페이지). 우리 쪽 대응 현황, 적용 후보(채택 권고 / 소유자 결정 / 기각), 결정 질문
- 대상 독자: 소유자 (적용 후보 결정), maintainer
- 상태: draft — 적용 후보는 소유자 결정 대기
- 최종 수정일: 2026-10-05
- 관련 문서: [`roadmap_milestone_wbs_spec.md`](../../workflow-source/core/roadmap_milestone_wbs_spec.md) (SDLC 어휘 · 게이트), [`global_workflow_standard.md`](../../workflow-source/core/global_workflow_standard.md) (작업 원칙 · 메모리 갱신 경로), [`session_context_budget_spec.md`](../../workflow-source/core/session_context_budget_spec.md) (진입점 분량 예산), [`LOCAL_GATE.md`](../LOCAL_GATE.md) (로컬 게이트), [`workflow-assessment-2026-09.md`](./workflow-assessment-2026-09.md) (직전 자체 평가)

## 0. 한 줄 결론

> 플레이북의 뼈대는 **"사람은 판단하는 게이트에, 에이전트는 기계적 실행에. 게이트는 버전 관리된 산출물과 결정적 검사로 세운다"** 이다. 우리 워크플로우는 그 뼈대의 절반, 즉 결정적 검사 · 게이트 근거 · 버전 관리된 메모리를 이미 더 엄격하게 갖고 있다. 비어 있는 쪽은 **변경 단위의 산출물 사슬**(intent → spec → plan)과 **작성자와 검증자의 분리**(독립 리뷰 · 새 컨텍스트 검증)다. 엔터프라이즈 운영 부분(managed settings, 배포 tiering, 관제 밴드)은 이 프로젝트에 해당하지 않는다. 권고는 §4.A 의 저비용 3건부터다.

## 1. 출처와 조사 범위

| 출처 | 내용 | 비고 |
|---|---|---|
| [블로그 — The AI-native SDLC playbook](https://claude.com/blog/the-ai-native-sdlc-playbook) | 2026-08-21, Louis Claxton (Enterprise AI · Claude Code) | 6단계 요약 + 통제 원칙 + 지표 |
| [Claude Academy 과정](https://academy.claude.com/courses/ai-native-sdlc-playbook) | 1시간, 14개 장, 퀴즈·배지 없음. 대상: Claude Code 를 쓰는 엔지니어링 · 플랫폼 · 보안 리드 | 전제: Claude Code 일상 사용, Git 저장소와 수정 가능한 CI |

- 조사일 2026-10-05. Academy 의 각 장(Introduction ~ Closing thoughts) 본문을 직접 읽었다.
- 원문에서 장마다 반복되는 틀: **무엇이 바뀌나 → 시작하기(전제 · 인프라) → 실행 단계 → 거버넌스 → 측정(선행 · 후행 지표)**.
- 원문 인용은 영어 그대로 둔다. 요약은 원문에 있는 것만 적었다. 우리 쪽 판단은 §3 부터 분리했다.
- 2차 해설 글(port.io, Substack 등)은 검색에 나왔지만 근거로 쓰지 않았다.

## 2. 플레이북 요약

### 2.1 전제

- 기존 SDLC 는 "code writing was the bottleneck" 인 시대에 설계됐다. 에이전트가 코드를 빠르게 만들자 병목이 사람 속도의 단계(계획 · 리뷰 · 배포)로 옮겨 갔다.
- SDLC 는 선형 흐름이 아니라 **루프**가 된다. 각 지점에 AI 가 들어가고, 사람이 통제하는 게이트 안에서 돈다.
- 핵심 원칙: *"Humans remain accountable for every decision that requires judgment."*
- 장(play)은 선형이 아니다. 의존 그래프로 묶여 있고, **전제가 없는 시작점 6개**가 있다: intent.md 기록, plan mode, CLAUDE.md, Skills, feedback loop, Hooks.

### 2.2 6단계와 산출물

| 단계 | 기존 방식 | AI-native | 핵심 산출물 |
|---|---|---|---|
| 1 Plan | 위원회·워크숍으로 요구 수집, 백로그·스토리·포인트·정제 회의 | 발의자가 Claude 와 브레인스토밍해 그 결과를 자기 말로 적는다 | `intent.md` |
| 2 Design | 요구와 설계가 다른 팀·다른 단계 | 승인된 intent 로 Claude 가 요구+설계를 **한 세션에** 만든다. 조직 skill(브랜드·보안·컴플라이언스·UX)이 제약한다 | `spec.md` |
| 3 Build | 설계를 읽고 바로 코딩. 리뷰어가 처음 보는 것이 완성된 diff | plan mode 로 계획부터. CLAUDE.md · skills · hooks · 병렬 세션 · subagent | `plan.md`, `CLAUDE.md`, skills, hooks |
| 4 Test | 경계의 QA 게이트, 검증이 늦게 온다 | 세션이 스스로 검증한 뒤 사람에게. 에이전트 설정이 바뀌면 eval 이 돈다 | feedback loop, eval suite |
| 5 Deploy | 사람이 모든 줄을 리뷰 | 에이전트 리뷰를 깔고 사람은 의도·위험 판단. hook 이 승인 게이트, CI 안에서 비대화형 실행 | `REVIEW.md`, gate hooks, managed settings |
| 6 Maintain | 사람이 운영 관제 | 결정적 관제가 밴드 이탈 시 Claude 를 깨운다. 진단은 새 `intent.md` 가 되어 루프를 닫는다 | `bands.yaml`, `intent.md` |

### 2.3 장별 요지

**Stage 1 — Capture as intent.md**
- 절차: 발의자가 문제를 대화로 설명한다 → Claude 가 범위·사용자·제약을 묻는다 → 조직 템플릿(skill 로 인코딩)으로 `intent.md` 를 만든다 → 발의자가 교정한다 → 버전 관리 위치(`intent/` 폴더)에 커밋한다 → product owner 가 리뷰한다.
- 템플릿 절: Problem · Proposed Outcome · Affected Users and Systems · Constraints · Open Questions.
- 인프라: 비엔지니어용 Claude 접근(claude.ai / Cowork), 합의된 템플릿, Git 을 모르는 사람 대신 커밋하는 GitHub connector.
- 지표: 선행 — 대화에서 커밋된 intent 까지 시간(주 → 시간 단위로 줄 것으로 본다). 후행 — **생존율**(Stage 2 로 넘어간 intent 의 비율).

**Stage 2 — Requirements and design**
- product owner 는 spec 을 쓰지 않고 리뷰한다. Claude 가 조직 skill 을 적용해 spec 을 만들고 **Areas of Concern** 을 담당자와 함께 표시한다.
- 실행: 처음에는 손으로 프롬프트를 돌리고, 그다음 slash command 로 굳히고, 그다음 intent 병합 시 비대화형 작업으로 자동화한다. concern 은 엔지니어링 리뷰 전에 정책 담당자와 푼다. `spec.md` 는 `intent.md` 옆에 커밋한다. 위험이 높으면 기술 리드에게 묻는다.
- spec 구조: 요구(R1~R4 번호) · 설계 · 제약 매핑 표 · 미결 질문 · Areas of Concern(담당자).
- 지표: 선행 — intent → spec 커밋 간격. 후행 — **첫 `plan.md` 이후의 `spec.md` 커밋 수**(계획 뒤에 spec 이 흔들린 횟수).

**Stage 3 — Plan mode as the default starting point**
- 코드를 바꾸지 않고 읽기만 하는 plan mode 에서 시작한다. spec 을 주면 Claude 가 엔지니어를 인터뷰하며 계획을 다듬는다.
- 완료 기준: *"an engineer who has never seen the conversation could implement the change from the plan alone"*. 승인된 계획은 `plan.md` 로 커밋하고, 구현이 벗어나면 갱신한다.
- `plan.md` 구조: Files that change · Order of work(요구 번호 인용) · Risks · Proof(검증 방법).
- 거버넌스: 코드 생성 **전에** 설계 리뷰. 일상 변경은 엔지니어가, 고위험 변경은 리드·아키텍트가 승인한다.
- 지표: 선행 — first-pass merge 율, 병합까지 시간. 후행 — 변경당 재작업 사이클, **병합된 diff 와 `plan.md` 의 일치**.
- 레거시 연계: 저장소가 정본이거나, Jira 같은 레거시 시스템이 정본이어도 된다. 최소 연결은 산출물이 레코드 ID 를, 레코드가 커밋 SHA 를 서로 참조하는 것이다.

**Stage 3 — The CLAUDE.md**
- 담는 것: 빌드·테스트·린트 명령, 중요한 팀 관례, 아키텍처 결정, Claude 가 자주 하는 실수. 빼는 것: 낡은 정보, 비필수 세부.
- 규칙: *"When Claude makes a mistake twice, the correction goes into `CLAUDE.md`"*. 분량은 *"under a page"* — 세션 시작에 전부 읽히므로 낡은 줄은 컨텍스트만 차지한다.
- 지표: 선행 — 파일이 막아야 할 실수의 반복 빈도. 후행 — 신규 인원의 첫 병합 PR 까지 시간.

**Stage 3 — Skills as institutional knowledge**
- *"Skills are how an organization makes its institutional knowledge operational."* 일관되게 적용해야 하는 지식은 skill 로, 나머지는 CLAUDE.md 나 프롬프트로.
- 인프라: 이름 있는 담당자와 정본이 문서화된 정책 하나. `.claude/skills/<name>/SKILL.md` 에 두거나 plugin 으로 조직에 배포한다. 정책이 바뀌면 담당자 승인 후 갱신하고, 엔지니어는 다음 세션에 자동으로 받는다.
- 거버넌스: skill 은 **권고형 통제**다. *"A policy that must always hold needs something deterministic behind the skill, such as a hook."*
- 지표: 선행 — 정책 승인에서 skill 갱신 병합까지 시간. 후행 — 정책을 인용하는 리뷰 지적이 0 으로 수렴하는가. 남는다면 skill 이 발동하지 않거나 정책과 어긋난 것이다.

**Stage 3 — Parallel sessions and subagents**
- 병렬 세션은 독립 worktree 에서 도는 별도 Claude Code 인스턴스다. subagent 는 한 세션 안에서 자기 컨텍스트와 도구 제한을 가진 보조자다.
- 실행: plan mode 로 파일이 겹치지 않는 작업으로 나눈다 → `claude --worktree <name>` 로 띄운다 → **2~3개로 시작하고 리뷰 용량이 허락할 때만** 늘린다 → 반복 작업은 `.claude/agents/` 의 subagent 로 만든다.
- 예: verifier agent 는 Bash · Read 만 쓰고, 고치지 않고 보고만 한다.
- 지표: 선행 — 엔지니어당 동시 세션 수, 조향 시간 대 대기 시간. 후행 — 주간 병합 수, 재작업률.

**Stage 4 — Give Claude a feedback loop**
- *"Always give Claude a way to verify its own work, whether tests, a build, or a screenshot diff."* feedback loop 는 작업 내내 돌고, verifier subagent 는 끝났다고 믿을 때 **새 컨텍스트에서** 하는 마지막 검사다.
- 실행: 검증을 실패 시 non-zero 로 끝나는 단일 명령으로 감싼다. CLAUDE.md 에 정상 출력 예와 함께 적는다. 목표를 정량으로 말한다. 버그 수정은 실패 테스트를 먼저 쓰고 **에이전트가 테스트 파일을 고치지 못하게** 한다. 완료 절차에 검증을 의무화한다. **hook 으로 검사가 약해지는 것을 막는다.**
- 근거 자료: `make test` 의 출력 원문, 빌드 로그, 스크린샷 diff.
- 지표: 선행 — 에이전트 변경의 first-pass CI 성공률. 후행 — PR 당 리뷰 시간, 변경 실패율.

**Stage 4 — Continuous evals in CI**
- *"Evals are the AI-native equivalent of stage-gate QA."* 모델 교체·프롬프트 재작성 등 **에이전트 설정이 바뀔 때마다** 도는 살아 있는 suite 다.
- 실행: 실제 작업 20~50개를 기대 결과와 함께 모은다 → eval 로 바꾼다(테스트 통과, 린트 clean, 동작 불변, 정책 준수) → CLAUDE.md · skills · hooks 가 바뀔 때와 정기적으로 돌린다 → 통과율로 설정 변경 병합을 게이트한다 → **사고마다 영구 회귀 eval 을 하나씩** 추가한다.
- eval 구조: `from`(기준 커밋) · `prompt` · `may_change`(바꿔도 되는 파일) · `checks`(검증 명령). worktree 로 과거 커밋에서 격리 실행한다.
- 인프라: Claude Code 를 비대화형으로 돌릴 수 있는 CI 와 API 예산.
- 지표: 선행 — 통과율 추이, 사고 → eval 전환 속도. 후행 — CI 가 잡은 회귀 대 운영 사고.

**Stage 5 — AI in the PR review loop**
- Claude 가 리뷰를 하고 받기도 한다. 모든 PR 에 같은 리뷰 패스를 돌리고 지적을 심각도로 정렬한다. 사람은 *"whether the change does what the plan intended and whether the risk is acceptable"* 로 올라간다.
- 실행: managed Code Review 나 claude-code-action 을 켠다 → 저장소 루트에 `REVIEW.md` 를 두고 패스를 정한다(버그 · 보안 · spec/plan 준수 · 설계 원칙) → 리드가 사람 승인 임계를 정한다(지적은 자동 승인·차단하지 않는다) → `@claude` 로 코멘트를 처리한다 → 반복 지적은 CLAUDE.md 로 보낸다 → 월 1회 튜닝(nit 상한).
- 거버넌스: *"Separation of duties is preserved, because the agent that wrote the code has no way to approve it."* 전제는 code owner 승인을 요구하는 branch protection 이다.
- 지표: 선행 — 첫 리뷰까지 시간(분 단위), 사람 개입 없이 해결된 코멘트 비율. 후행 — 병합 전에 잡힌 결함 대 운영까지 간 결함.

**Stage 5 — Hooks as approval gates**
- hook 은 allow / ask / block 셋 중 하나를 낸다. 승인 게이트 hook 은 사람 확인을 기다리거나 지정 승인자의 기록을 확인한다.
- 실행: 리더십이 사람 승인 게이트를 정한다(변경 관리, 릴리스 승인, 보호 경로) → 플랫폼 엔지니어가 hook 스크립트로 표현한다 → 팀 hook 은 `.claude/settings.json`, 양보 불가 hook 은 managed settings 에 둔다 → **차단은 이유와 승인 경로를 스스로 설명해야 한다.**
- 예: 릴리스 게이트 스크립트 — dev 는 자동, staging 은 main 파이프라인이 아니면 ask, production 은 `CHG-[0-9]+` 형식의 승인된 변경 티켓과 버전 해시 대조.
- managed settings 예: `permissions.deny`(`.env*`, `./secrets/**`, 네트워크 도구) · `permissions.allow` · `disableBypassPermissionsMode` · `sandbox.enabled` + `failIfUnavailable` · `allowManagedHooksOnly` · `strictKnownMarketplaces` · `allowManagedMcpServersOnly` · `requiredMinimumVersion`.
- 지표: 선행 — 게이트별 대기 시간(OpenTelemetry). 후행 — hook 도입 전후로 운영까지 간 게이트 위반.

**Stage 5 — CI/CD integration and deployment**
- 판단 단계는 Claude 가 파이프라인 안에서 비대화형으로, 범위가 좁은 자격 증명과 sandbox 안에서 맡는다.
- 6단계 도입: 읽기 전용(`claude -p` 로 빌드 분류, 테스트 요약, changelog 초안) → 게이트 뒤의 쓰기(main 직접 접근 없음) → sandbox 컨테이너와 단기 토큰 → MCP 로 배포·상태·롤백 도구 노출(allowlist) → 환경 tiering → **리허설된 롤백**: *"Rollback should be the most rehearsed path in the pipeline"*.
- 지표: 선행 — 사람 호출 없이 분류된 파이프라인 실패. 후행 — DORA 지표.

**Stage 6 — Closing the loop on metrics**
- 관제 에이전트가 버그 티켓에서 `intent.md` 를 만들고 이후 단계를 headless 로 탄다. 단계 사이에는 *"an independent confidence gate … a deterministic check or an adversarial reviewing agent"* 를 둔다.
- 관제 밴드: 직전 30일 시간별 측정의 평균과 σ. 720개 측정 기준으로 1σ 는 하루 약 4번, 2σ 는 월 약 16번, 3σ 는 잡음만으로 월 약 1번 이탈한다. Western Electric 규칙(1956)으로 3σ 를 넘지 않는 느린 drift 를 잡는다: 최근 5개 중 4개가 1σ 위, 또는 8개 연속 평균 위.
- 대응 계층(`bands.yaml`): 1σ 기록만 / 2σ 읽기 전용 진단 / 3σ PR 을 리뷰 게이트로 열거나 사전 승인된 runbook 실행.
- 실행: 안정적인 기준선이 있는 지표 하나를 고른다(CI 테스트 실패율, 배포 후 5xx, PR cycle time) → **모델 없이** 결정적 규칙으로 탐지하는 스크립트 → 계층 설정 → 트리거(예약 workflow, webhook, cron) → 진단을 `intent.md` 로 → 담당자가 분류 → 수리가 나가면 eval 추가.
- 지표: 선행 — 밴드 이탈에서 `intent.md` 까지 시간. 후행 — 병합된 수리가 된 진단의 비율, 반복 사고 빈도.
- Claude Tag(Slack 공개 베타)는 채널의 1차 대응자로서, 작은 수리는 PR 로, 큰 일은 `intent.md` 로 보낸다.

### 2.4 통제 원칙과 측정

- **직무 분리**: 코드를 쓴 에이전트가 그 코드를 승인할 수 없다.
- **버전 관리 = 감사 기록**: 모든 결정이 시각·작성자와 함께 남는다.
- **판단은 사람**: 사람은 게이트에서 결정하고, AI 는 실행한다.
- **managed settings**: 양보할 수 없는 통제는 플랫폼 팀이 서버 관리 설정으로 강제한다.
- 측정 틀(블로그): 선행 — intent 에서 병합 PR 까지 시간, 엔지니어당 동시 세션, eval 통과율. 후행 — 운영 유출 결함, 반복 사고, 재작업 사이클. 모든 장이 **선행·후행 지표 한 쌍**을 단다.
- 도입 순서(Closing): 조직 설정 → settings · managed settings → 권한 → sandbox → hooks · skills · plugin marketplace → managed MCP → 엔터프라이즈 배포 · 네트워크 → 모니터링 · 분석 → 컴플라이언스 API · 보안 모델.

## 3. 우리 워크플로우 대응표

판정: **있음**(같은 목적을 같은 강도로) · **부분**(목적은 같지만 범위나 강도가 다름) · **없음** · **해당 없음**(이 프로젝트 성격 밖).

| 플레이북 play | 우리 쪽 대응 | 판정 | 근거 |
|---|---|---|---|
| intent.md (Plan) | 마일스톤 단위: `concept` 단계 산출물(`PURPOSE.md`, `docs/planning/*-review`). 변경 단위: backlog task 의 brief · done criteria | 부분 | 마일스톤은 산출물로 남지만, 변경 단위 intent 는 task 파일의 한 줄 brief 다. 템플릿 절(Problem/Outcome/Constraints/Open Questions)이 없다 |
| spec.md (Design) | `requirements` · `design` 마일스톤 산출물(`*-requirements-*.md`, ADR, core spec) | 부분 | 기능 축에서는 concept → requirements → design 문서가 실제로 쓰인다(compact relay M-018~021). 작은 변경은 건너뛴다. Areas of Concern(담당자 표시) 개념이 없다 |
| plan mode → plan.md (Build) | 정본 §1 원칙 "Before starting work, briefly state its purpose, scope, expected deliverables, and affected documents" | 부분 | 원칙은 있지만 **산출물로 남지 않는다.** 대화에만 있고, 병합된 diff 와 계획을 대조할 근거가 없다 |
| CLAUDE.md | 정본에서 생성한 규칙 블록 + 프로젝트 실행 기본값. 분량 예산 12,288 B (red) | 있음(더 엄격) | 생성 블록 단일 출처 검사, 분량 예산 검사. 단 현재 11,916 B 로 예산의 97% — 플레이북의 "under a page" 보다 3배 이상 길다 |
| "실수 두 번 → CLAUDE.md" | 같은 수작업 2회 = 규약을 **코드·검사로** 옮긴다(lessons · memory) | 있음(더 강함) | 우리는 산문이 아니라 결정적 검사로 옮긴다 — 플레이북 Skills 장의 "deterministic behind the skill" 과 같은 방향 |
| Skills | 플러그인 스킬 5종(session-start / backlog-update / doc-sync / session-end / compact-relay), 정본 파생 | 있음 | 정본 §11 블록을 스킬에 생성 주입한다. 정책 담당자 승인 흐름은 소유자 1인이라 해당 없음 |
| Hooks (build-time) | 플러그인 hook(SessionStart 규칙 주입 · SessionEnd state 재생성 · compact 중계 3종) | 부분 | 세션 경계 자동화는 있지만, 보호 경로 차단이나 검사 약화 차단 같은 **가드 hook** 은 없다 |
| Parallel sessions | 브랜치별 메모리 + worktree 자동 seed(v1.17.0) · 합류 반영(v1.18.0) | 있음 | 병렬 세션의 **메모리 왕복**은 플레이북보다 앞서 있다. "2~3개로 시작" 같은 용량 지침은 없다 |
| Subagents | 없음 (`.claude/agents/` 부재) | 없음 | 반복 검증(전량 게이트, 되주입)이 매번 주 세션 컨텍스트에서 돈다 |
| Feedback loop | `run_all_checks.py --filter / --changed`, 되주입(결함을 넣어 red 확인), 게이트 명령 파이프 금지 | 있음(더 엄격) | 검사 자체가 무력화되는지까지 잰다(meta-check 3층). 테스트 파일 편집 차단 hook 은 없다 — 대신 되주입으로 검사의 생존을 확인한다 |
| Continuous evals | 없음. 검사는 **산출물 텍스트**(생성 블록, payload, hook 명령)를 재고, 에이전트가 그 지시를 받아 **어떻게 행동하는지**는 재지 않는다 | 없음 | CI 폐지(2026-09-23), API 예산 없음 |
| AI PR review / REVIEW.md | 없음. 대부분 main 직접 push. worktree 는 PR 병합(#30) | 없음 | 쓰는 에이전트와 검증하는 에이전트가 같다 — 직무 분리가 없다 |
| Hooks as approval gates | push 게이트(HEAD sha 의 게이트 통과 기록 없으면 pre-push 차단) · `release --apply` 의 게이트 기록 요구 · 소유자 승인 | 있음 | 결정적 근거(`gate_evidence/<sha>.json`)로 게이트를 세운다. 차단 시 이유를 출력한다 |
| CI/CD · sandbox · MCP 배포 도구 | read-only MCP 서버, 릴리스 파이프라인(dry-run 기본) | 해당 없음 / 부분 | 운영 배포 대상이 없는 kit 다. 릴리스가 우리의 "배포"다 |
| 리허설된 롤백 | 없음 | 없음 | 발행 뒤 소비 채널을 이전 버전으로 되돌리는 경로를 리허설한 적이 없다 |
| 관제 밴드 / Maintain 루프 | north-star 지표, 대시보드 8 패널, `wk doctor` drift 탐침. 소유자 보고 → task | 부분 | 결정적 탐지는 있지만 통계 밴드나 자동 트리거는 없다. 루프를 닫는 것(발견 → 새 task)은 사람이다 |
| 선행·후행 지표 한 쌍 | 기능별 판정 검사는 있지만 **지표 쌍**으로 선언하지 않는다 | 부분 | 대시보드 지표는 kit 전체 상태다. 기능 단위로 "효과가 있었나"를 재는 후행 지표가 없다 |
| managed settings | 해당 없음 | 해당 없음 | 조직 MDM 이 없는 1인 프로젝트 |
| SDLC 단계 어휘 | `concept / requirements / design / implementation / stabilization / release` | 부분 | Test 는 implementation · stabilization 안에 녹아 있다(플레이북도 지속 검증으로 녹인다). **Maintain → 새 intent** 루프 단계가 어휘에 없다 |

## 4. 적용 후보

### 4.A 채택 권고 — 비용이 낮고 우리 원칙과 맞는 것

**A1. 작업 전 계획을 task 파일에 남긴다 (plan.md 대응)**
- 내용: task 파일에 `## Plan` 절을 둔다 — 바뀌는 파일, 작업 순서(done criteria 인용), 위험, 검증 방법(Proof). 정본 §1 의 "작업 전 목적·범위·산출물 진술" 원칙을 대화가 아니라 **기록**으로 만든다.
- 근거: 플레이북 완료 기준 — 대화를 못 본 사람이 계획만으로 구현할 수 있어야 한다. 우리는 compact 와 세션 경계에서 판단을 잃는 문제를 이미 겪었다(ADR-030). 계획이 task 파일에 있으면 compact 중계와 다음 세션이 그대로 읽는다.
- 비용: `backlog-update` 에 `--plan-*` 인자 또는 템플릿 절 하나, 파서 보존 확인. 새 파일은 만들지 않는다 — 산출물을 늘리면 우리 원칙(정본 하나)과 어긋난다.
- 측정(후행): 완료된 task 의 결과 · 검증이 Plan 의 Proof 와 맞는가를 session-end 에서 대조한다.

**A2. 새 컨텍스트 verifier subagent (작성자 ≠ 최종 검증자의 최소형)**
- 내용: `.claude/agents/verifier.md` — Bash · Read 만 쓰고, 고치지 않고 보고만 한다. task 의 done criteria 와 `--changed` 결과, 변경 diff 를 새 컨텍스트에서 대조한다. task 를 `done` 으로 닫기 전에 부른다.
- 근거: 정본 원칙 "Never mark an unverified result as done" 의 판정자가 지금은 작성한 세션 자신이다. 메모리에 쌓인 결함 상당수(예: "부수 효과는 hook 성공이 아니다", "재현은 검증이 아니다")가 **같은 컨텍스트가 자기 판단을 확인한** 경우였다.
- 배포: 우선 이 저장소에서 실측한다. 플러그인 payload 에 agents 를 싣는 것은 채널별 지원을 조사한 뒤에 결정한다(B 로 넘긴다).
- 측정: verifier 가 `done` 을 막은 횟수와 그 이유(후행). 0 이 계속되면 판정이 맹목인지 되주입으로 확인한다.

**A3. 검사 약화 차단 가드 hook**
- 내용: PreToolUse hook 으로 `git push --no-verify`, `--no-lock` 전량 실행, `gate_evidence/` 직접 쓰기를 막는다. 막을 때는 이유와 정상 경로를 출력한다(플레이북: 차단은 스스로 설명해야 한다).
- 근거: 플레이북 Feedback loop 장 7단계 — "hook 으로 검사가 약해지는 것을 막는다". 우리 CLAUDE.md 는 이것을 산문 규칙으로만 갖는다("`--no-verify` push 는 게이트 근거가 없다").
- 비용: 이 저장소의 `.claude/settings.json` 에 hook 하나. 소비자 배포는 하지 않는다(프로젝트별 정책).
- 측정: 차단 로그 횟수.

### 4.B 소유자 결정 필요 — 효과는 있지만 범위나 비용이 크다

**B1. 변경 단위 intent 템플릿 (concept 의 가벼운 형)**
- 선택지: (a) 하지 않는다 — 마일스톤 concept 문서로 충분하다. (b) `backlog-update` create 의 brief 를 Problem · Outcome · Constraints · Open Questions 4절로 구조화한다. (c) 소비자 온보딩(bootstrap 씨앗)에 `intent/` 템플릿을 싣는다.
- 판단 재료: 우리 concept → requirements → design 은 기능 축에서 이미 돈다(M-018~021). 소유자 보고에서 출발한 작은 결함(이번 cp949 · V3)은 한 줄 brief 로 시작했고 문제없었다. 소비자 프로젝트에서는 효과가 클 수 있다(ADR-027 온보딩 기본 흐름과 맞물린다).
- 권고: (b) 를 A1 과 묶어 task 템플릿 개편 한 번으로 처리한다.

**B2. 에이전트 행동 eval (지시 → 행동)**
- 공백: 정본 §11 문구, 스킬, hook 을 바꾸면 검사는 **텍스트가 맞는지**만 본다. 그 지시를 받은 에이전트가 실제로 `python -m workflow_kit refresh-state` 를 부르는지, handoff 형식을 지키는지는 아무도 재지 않는다. v1.19.0 의 호출 형태 전환이 정확히 이 공백 위에 있다.
- 선택지: (a) 보류. (b) 릴리스 전 수동 eval 5~10건 — 격리 workspace 에서 `claude -p` 로 session-start → 작업 → session-end 를 돌리고 산출물 형식을 결정적 검사로 판정한다(플레이북 구조: `from` · `prompt` · `may_change` · `checks`). (c) 정기 자동 실행 — API 예산과 CI 가 전제다.
- 비용: (b) 는 모델 호출 비용이 들고 판정이 비결정적이다. 통과율은 표본 크기를 정하고 읽어야 한다(메모리 "무재발 주장에는 표본이 필요하다").

**B3. 독립 리뷰 (REVIEW.md + 릴리스 전 리뷰 패스)**
- 선택지: (a) 보류 — 소유자 1인, main 직접 push 문화. (b) 릴리스 준비 커밋에서만 `/code-review` 를 돌리고, `REVIEW.md` 에 패스(버그 · 보안 · 정본 단일 출처 위반 · 검사 무력화)를 정한다. (c) worktree 브랜치는 PR 로 병합하고 리뷰를 필수화한다.
- 판단 재료: 우리 결함의 상당수는 "검사는 green 인데 판정이 맹목"인 유형이라, 같은 컨텍스트의 리뷰보다 **다른 컨텍스트의 리뷰**가 효과를 낼 자리다.

**B4. SDLC 어휘에 Maintain 루프**
- 내용: `stabilization` 다음, 또는 상시 단계로 "운영 발견 → 새 concept/intent" 를 선언한다. 지금 이 저장소는 M-007(stabilization)이 사실상 그 역할이다(소유자 보고 → 결함 task).
- 선택지: (a) 어휘는 그대로 두고 stabilization 의 정의에 "발견을 새 task/concept 로 되돌린다"를 적는다. (b) 7번째 phase `maintain` 을 추가한다 — 어휘 변경은 `check_roadmap_format` 과 소비자 roadmap 에 파급되므로 minor 등급 판단이 필요하다.

**B5. 기능별 선행·후행 지표 한 쌍**
- 내용: 새 기능의 requirements 문서에 "선행 지표 / 후행 지표" 칸을 의무화한다. 예: compact 중계라면 선행 = 재주입 도달률, 후행 = compact 뒤 같은 질문 반복 수.
- 판단 재료: north-star 지표는 상수 판정 문제를 여러 번 겪었다(메모리 "north-star 지표 재정의"). 기능 단위로 쌍을 선언하면 "고친 값이 실제로 변하는지"를 기능마다 잴 수 있다.

### 4.C 기각 / 해당 없음

| 항목 | 이유 |
|---|---|
| managed settings · MDM | 조직 플랫폼 팀이 없는 1인 프로젝트. 소비자 조직이 쓸 일이고, kit 가 대신할 일이 아니다 |
| 환경 tiering · MCP 배포 도구 · sandbox 자격 증명 | 운영 배포 대상이 없다. 릴리스는 GitHub Releases 하나(PyPI 발행 안 함 — 소유자 결정) |
| 관제 밴드(σ · Western Electric) | 시간별 측정 시계열이 없다. 게이트 소요 시간 같은 후보는 있지만 표본 빈도(하루 몇 회)가 밴드 통계를 받치지 못한다 |
| Claude Tag · Slack 1차 대응 | 운영 채널이 없다 |
| DORA 지표 | 배포 파이프라인이 없다 |

> **리허설된 롤백**은 기각하지 않고 메모해 둔다: 발행 뒤 소비 채널(§2.8)을 이전 버전으로 되돌리는 절차가 문서에도 검사에도 없다. 지금까지 필요한 적이 없었지만, v1.19.0 처럼 hook 명령이 바뀌는 발행에서는 문제가 생기면 돌아갈 길이 필요하다. 별도 후보로 등록할지는 소유자 판단에 맡긴다.

## 5. 우리가 이미 더 엄격한 곳 / 플레이북이 앞선 곳

**우리가 더 엄격한 곳**
- **검사의 검사**: 플레이북은 "eval 통과율"을 믿는다. 우리는 판정이 살아 있는지 결함 되주입으로 따로 잰다. 모름(SKIP · 미측정)을 통과로 세지 않는다.
- **게이트 근거의 결정성**: push · 릴리스 게이트가 HEAD sha 단위의 통과 기록을 요구한다. 플레이북의 승인 게이트는 티켓 시스템 조회다.
- **산출물 단일 출처**: CLAUDE.md 규칙 블록, 스킬, hook 이 한 정본에서 생성되고 일치가 강제된다. 플레이북은 CLAUDE.md 를 손으로 관리한다.
- **병렬 세션의 메모리**: 브랜치별 메모리, 자동 seed, 합류 반영. 플레이북은 "엔지니어가 유일한 연결점"이라고 하는데, 우리는 그 연결을 도구가 한다.

**플레이북이 앞선 곳**
- **변경 단위 산출물 사슬**: intent → spec → plan 이 각 변경마다 커밋된다. 사람의 판단 지점(승인)이 산출물에 붙는다.
- **직무 분리**: 쓴 에이전트가 승인하지 않는다. 우리는 같은 세션이 쓰고, 검증하고, `done` 을 선언한다.
- **에이전트 설정의 회귀 검사(eval)**: 지시문을 바꾸면 행동이 유지되는지 잰다.
- **분량 규율**: CLAUDE.md "under a page". 우리는 예산을 두었지만 상한 바로 아래에 머물러 있다.

## 6. 소유자 결정 질문

1. §4.A 세 건(task Plan 절 · verifier subagent · 검사 약화 차단 hook)을 이 저장소에 적용할까? 적용하면 A1 은 B1(b) 와 묶어 task 템플릿 개편 한 번으로 처리하는 것을 권고한다.
2. B2(행동 eval)를 릴리스 전 수동 5~10건(b)으로 시작할까, 보류할까?
3. B3(독립 리뷰)를 릴리스 준비 커밋에서만(b) 할까?
4. B4 는 어휘를 유지하고 stabilization 정의를 보강(a)할까, `maintain` phase 를 추가(b)할까?
5. 리허설된 롤백을 별도 후보 task 로 등록할까?

## 7. 확인하지 못한 것

- Academy 각 장의 코드 예시(hook 스크립트, eval YAML, `bands.yaml`)는 구조만 옮겼고 원문 코드는 싣지 않았다. 적용 단계에서 원문을 다시 읽는다.
- 플러그인으로 subagent(`agents/`)를 배포할 수 있는지는 채널별로 조사하지 않았다(Claude Code 외 Codex · Grok · Antigravity · MiniMax · pi-dev).
- 블로그 원문의 측정 틀 전체(지표 목록)는 페이지 본문만 봤다. 별도 다운로드 자료가 있는지는 확인하지 않았다.
