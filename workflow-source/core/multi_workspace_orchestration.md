# Multi-Workspace Orchestration (사용자 · 서버 · 하네스)

- 문서 목적: 여러 하네스 워크스페이스에서 각 에이전트가 워크플로우를 돌리고, 중앙 메인 에이전트가 이를 취합해 `main` 을 관리하는 운영 모델의 설계를 정의한다.
- 범위: 3계층 워크스페이스 구분, 격리 키 결정과 근거, 하네스 동시 운영 시 lease 규약, 중앙 취합 확장 지점, 미해결 질문
- 대상 독자: AI workflow 설계자, 멀티 에이전트 운영자, 저장소 관리자
- 상태: draft (설계 단계 — 구현 미착수)
- 최종 수정일: 2026-08-07
- 관련 문서: `./workflow_configuration_layers.md`, `./workflow_harness_distribution.md`, `./workflow_agent_topology.md`, `./orchestrator_subagent_contract_v1.md`, `./merge_doc_reconcile_skill_spec.md`, `../MEMORY_GOVERNANCE.md`

> **상태 고지**: 본 문서는 *설계* 다. §2 의 "이미 있다" 항목과 §5A~§5D 의 실측은
> 2026-08-07 에 확인했고 근거를 함께 적었다. §7 의 확장 제안은 **아직 구현도 검증도
> 되지 않았다**. 둘을 섞어 읽지 않는다.
>
> **읽는 순서**: **§0 이 정본 요약**이다. §1 이후는 결론에 이른 조사 기록이며 **조사
> 순서대로** 쌓여 있어, 뒤 절이 앞 절의 결정을 뒤집은 곳이 있다. 뒤집힌 자리에는 교체
> 표시를 달아 두었다:
>
> | 절 | 상태 |
> | --- | --- |
> | §4.2 파일 lease | ⚠️ §5D 가 **브랜치 선점으로 교체** |
> | §5B.2 "조용한 소실" | ⚠️ §5C.2 가 **진단 정정** (도구는 안전, 손 편집이 위험) |
> | §5B.8 우선순위 | ⚠️ §5C.5 가 **갱신** (P4 강등) |
> | §5C.3 lease 구현 | ⚠️ §5D 가 **대체** |

## 0. 확정 워크플로우 (정본 요약)

> 본 절이 **결론**이다. §1~§8 은 그 결론에 이른 *조사 기록과 실측 근거* 이며, 조사
> 순서대로 쌓여 있어 중간에 뒤집힌 결정이 포함돼 있다. 구현하거나 운영할 때는 **본 절을
> 먼저** 읽고, 근거가 필요할 때만 해당 절로 내려간다.

### 0.1 한 줄 요약

**워크스페이스는 브랜치로 가르고, 배타 점유는 `git push` 가 하며, 취합은 파생 뷰로 둔다.**
새 인프라 없이 git 이 이미 제공하는 보장을 그대로 쓴다.

### 0.2 3계층 매핑

| 컨셉 계층 | 실체 | 상태 |
| --- | --- | --- |
| 사용자 | `global-snippets/` + Harness Global Layer | 기존 (11 하네스 중 3종 커버) |
| **서버** | workspace registry — `host_id` 매핑 + in-flight 가시성 | **미구현** (§7) |
| 하네스 | 워크스페이스의 *속성*. 격리 키가 **아님** | 결정됨 (§3) |

### 0.3 핵심 결정 5가지

1. **격리 키 = 작업/브랜치** (하네스 ❌). 하네스 이름 디렉터리는 자동 아카이브가
   고아로 판정해 치운다 — git 이 존재를 검증할 수 있는 이름이어야 한다. → §3.3
2. **배타 점유 = 브랜치 선점(`git push`)**. ref 생성이 원자적이라 분산 CAS 로 동작한다
   (5-way 경합 → 정확히 1명). 파일 lease·TTL·registry 불필요. → §5D.1
3. **서버 식별 = `host_id`**(registry 발급). hostname/IP 는 진단 표시,
   `endpoint` 는 접속 정보. 셋을 한 필드에 섞지 않는다. → §4.5
4. **취합은 파생 뷰**. 중앙에 mutable 집계 파일을 두지 않는다. 단 취합 뷰는 **커밋·병합된
   것만** 보인다(메모리가 git-tracked). in-flight 가시성은 registry 몫. → §5A.3, §6
5. **되돌릴 수 없는 작업은 에이전트 단독 결정 ❌** — 남의 브랜치 삭제·덮어쓰기는 반드시
   사용자 확인. → §5D.4

### 0.4 세션 워크플로우

```
[중앙]  취합 뷰(main) → 작업 선정 → 하네스 배정
                                      ↓
[선점]  fetch --prune → 원격 현황 조회 → 브랜치 생성 + 메모리 seed + 예정 내역
                                      ↓
                          git push origin <branch>   ← 배타 획득 지점
                          ├ 성공   → 진행
                          └ rejected → 남이 가져감. 다른 작업 선택 (--force ❌)
                                      ↓
[작업]  session-start → 기존 워크플로우 그대로 (contract v1 위임)
                                      ↓
[종료]  memory 갱신 → commit → push   (표준 §8 순서)
                                      ↓
[합류]  중앙 병합 → merge-doc-reconcile → 브랜치 삭제(= 점유 해제)
                                      → archive_branch_memory 가 메모리 정리
```

**단계별 필수 사항**

| 단계 | 반드시 | 근거 |
| --- | --- | --- |
| 조회 전 | `git fetch origin --prune` | 안 하면 되살아난 브랜치를 stale 로 오판 → §5D.4a |
| 조회 | 1일 초과 무활동 = `STALE` → **사용자 문의** (삭제 ❌) | §5D.4a |
| 선점 전 | **메모리 seed** (`active/<branch>/`) | 없으면 `session-start` 가 `missing_required_document` 로 실패 → §5A.2 |
| 선점 | push 1회. `rejected` = 신호이지 장애가 아님 | §5D.2 |
| 종료 | memory 갱신을 commit 과 같은 turn 에 | 표준 `global_workflow_standard.md` §8 |

### 0.5 충돌 방지 규약

| 대상 | 규약 | 상태 |
| --- | --- | --- |
| `log.md`, telemetry `*.jsonl`, daily backlog index | `.gitattributes` `merge=union` | ✅ **적용됨** |
| `state.json` | union ❌ (JSON 깨짐). 충돌 시 **rebuild** | ✅ 적용됨(제외 확인) |
| 공유 append 라인 | 타임스탬프 + `host_id` 포함 — union 이 동일 줄을 접는다 | ✅ 규약 명시 |
| backlog / handoff | **도구를 통해 갱신**. 손으로 통째 덮어쓰기 ❌ | ✅ 규약 명시 |
| `active/<branch>/**` | 전략 불필요 (물리 격리로 안 만남) | — |
| 병합 순서 | 별도 큐 불필요 — git 이 non-fast-forward push 를 거부해 직렬화 | §5C.4 |

### 0.6 지시 전달 방식

**중앙이 하네스에 메시지를 보내지 않는다.** `session-start` 는 인자로 받은 경로의 문서만
읽으므로, **업무 지시 = 워크스페이스에 미리 놓인 `session_handoff.md` + backlog** 다.
새 프로토콜을 만들지 않는다. → §5A.1

다른 에이전트의 작업 내역도 같은 원리로 공유된다 — 선점 push 에 예정 내역을 실어 두면
`git show origin/<branch>:<path>` 로 체크아웃 없이 읽힌다. → §5D.3

### 0.7 적용 상태

| 항목 | 상태 |
| --- | --- |
| `.gitattributes` union merge | ✅ 적용 (`git check-attr` + 실제 병합 검증) |
| `memory/active/README.md` 규약 2건 | ✅ 적용 |
| 브랜치 선점 플로우 | 📋 설계 확정, **구현 미착수** |
| workspace registry | 📋 미구현 — §7 착수 1순위 |
| 메모리 seed 도구 | 📋 미구현 — §7 착수 2순위 |
| 복수 root 취합 | 📋 미구현 — §7 착수 3순위 |

### 0.8 아직 열려 있는 것

- registry **저장 위치** — 여러 호스트로 흩어지면 파일 기반이 성립하지 않는다.
- in-flight 워크스페이스를 취합 뷰에 **어떤 신뢰도로** 표시할 것인가.
- seed 한 지시와 실제 한 일이 갈라졌을 때(범위 이탈) 병합 시점 검출.
- `--force` 를 서버측(branch protection)으로 이중화할지 — 규약만으로는 실수를 못 막는다.

---

## 1. 무엇을 풀려는 문제인가

한 사람이 여러 AI 하네스(Claude Code / Codex / OpenCode / …)를 동시에 굴린다. 각
하네스는 자기 워크스페이스에서 표준 워크플로우대로 작업한다. 중앙의 메인 에이전트가
그 결과를 모아 `main` 브랜치를 관리한다.

원래 컨셉의 계층은 **사용자 → 서버 → 하네스** 였다. 실측해 보니 세 계층 중 둘은
기존 개념에 이미 대응물이 있고, 하나만 새롭다.

| 컨셉 계층 | 기존 대응물 | 판정 |
| --- | --- | --- |
| 사용자 | `global-snippets/` + Harness Global Layer (`workflow_configuration_layers.md` §2) | 있음 (단 11 하네스 중 3종만 커버: codex / opencode / grok-build) |
| **서버** | — | **없음. 실제 신규 설계 대상** |
| 하네스 | 하네스 오버레이 (`workflow_harness_distribution.md`) + branch-scoped memory | 있음 |

따라서 본 문서의 실질 주제는 **"서버 = 여러 워크스페이스를 담은 한 호스트"** 계층을
어떻게 정의하고, 그 위에서 중앙 취합을 어떻게 성립시키는가다.

## 2. 이미 있는 기계장치 (실측 근거 포함)

컨셉의 하부 구조는 상당 부분 이미 구현돼 있다. 새로 만들 것과 재사용할 것을 가르기
위해 실측한 결과를 남긴다.

### 2.1 격리 — `active/<branch>/`

v1.0.0 의 branch-scoped memory 가 이미 동시 작업 충돌을 물리적으로 없앤다. 동기가
정확히 본 컨셉과 같다 (`MEMORY_GOVERNANCE.md`):

> sub-agent 2개+ 동시 fan-out 시 `state.json.recent_done_items` / `work_backlog.md`
> 의 3-way merge conflict 를 해소. 신규 layout 에서는 mutable 공유 파일이
> `state.json` 단 1개 (rebuild race only), 나머지는 append-only 또는 자기 소유 파일.

### 2.2 중앙 취합 — 파일이 아니라 뷰

`MEMORY_GOVERNANCE.md` §2 의 *"집계는 파일이 아니라 뷰: dashboard 가
`active/*/state.json` 을 모두 스캔해 합친다"* 는 문서상의 다짐이 아니라 **실제 코드**임을
확인했다 — `workflow_kit/common/dashboard_data.py:1267` `_branch_state_paths()` 가
`active` 를 `rglob("state.json")` 으로 훑는다.

이 설계가 중요한 이유: **중앙에 mutable 집계 파일이 없으므로 merge 마다 갱신할 대상이
없다.** 취합을 파생 뷰로 두는 원칙을 본 컨셉도 그대로 승계해야 한다.

### 2.3 워크스페이스 식별자 주입점 — `BRANCH_ENV_KEYS`

`workflow_kit/common/paths.py:9` 가 5종 환경변수로 slug override 를 허용한다
(`CODEX_WORKFLOW_BRANCH`, `GITHUB_HEAD_REF`, `GITHUB_REF_NAME`, `CI_COMMIT_REF_NAME`,
`BRANCH_NAME`). 실측 거동:

| 입력 | 결과 |
| --- | --- |
| (없음) | `main` (git 조회 fallback) |
| `feat-a` | `feat-a` |
| `harness/codex` | `harness/codex` (슬래시 허용 → 중첩 디렉터리) |
| `../escape` | `main` (traversal 거부) |

또한 `get_current_branch()` 의 git 조회는 CWD 가 아니라 **모듈 자신의
`parents[3]`** 에 anchor 한다. 즉 워크트리마다 kit 사본이 따로 있으면 각자 자기
브랜치를 본다.

### 2.4 위임 계약 — contract v1

`orchestrator_subagent_contract_v1.md` 가 이미 오케스트레이터↔워커의 입출력 스키마,
5역할, fan-out/in, P0 enforce 를 규정한다. **본 컨셉은 이 계약을 대체하지 않는다** —
contract v1 이 *한 워크스페이스 안* 의 위임이라면, 본 문서는 *워크스페이스 사이* 를
다룬다. 두 축을 섞지 않는다.

## 3. 격리 키 결정 — 하네스가 아니라 작업/브랜치

컨셉의 원안은 하네스를 워크스페이스 격리 키로 삼았다(`active/codex/`,
`active/claude-code/`). **이 안은 채택하지 않는다.** 근거는 셋이고, 세 번째가 결정적이다.

### 3.1 축이 어긋난다

브랜치는 *작업* 축이고 하네스는 *도구* 축이다. 하네스를 격리 키로 쓰면:

- 하네스 A·B 가 **같은 기능**을 만지면 인위적으로 쪼개진다.
- 하네스 하나가 **두 기능**을 만지면 여전히 충돌한다 — 격리가 막아주지 못한다.

### 3.2 재통합 메커니즘이 없다

브랜치 격리에는 짝이 되는 재통합 경로가 있다 — git merge 가 직렬화하고, 합류 시점에
`merge-doc-reconcile` 이 정합을 복구한다. 하네스 축에는 그런 것이 없다. "N개 하네스가
`main` 에 기여" 는 결국 중앙이 N개 브랜치를 병합하는 것이고, 그건 **하네스 이름이 붙은
브랜치 모델**이다.

### 3.3 (결정적) 자동 아카이브가 하네스 디렉터리를 치운다

`tools/archive_branch_memory.py` 는 *"`active/<branch>/` 가 있는데 git 에 그 브랜치가
없으면 종료로 보고 `archived/<branch>/` 로 옮긴다"* 는 역방향 점검을 수행한다.
`find_branch_memories()` + `branch_exists()` 를 임시 트리에 실제로 호출한 결과:

```
active/feat-x/codex   -> branch_exists? False   → 아카이브 대상
active/feat-x/claude  -> branch_exists? False   → 아카이브 대상
active/main           -> branch_exists? True    → 유지
```

즉 **하네스 이름 디렉터리(`active/codex/`)도, 하네스 중첩(`active/<branch>/<harness>/`)도
고아로 판정되어 자동으로 치워진다.** 격리 키를 하네스로 잡으려면 이 도구의 판별 규칙을
먼저 바꿔야 하고, 그러면 "고아 디렉터리가 구조적으로 생길 수 없다" 는 기존 보장이 깨진다.

> **결론**: 격리 키는 **git 이 존재를 검증할 수 있는 브랜치**여야 한다. 이 제약은 우연이
> 아니라 자동 아카이브가 성립하는 근거다.

### 3.4 채택안

**격리 키 = 작업/브랜치. 하네스는 워크스페이스의 *속성*(metadata).**

```
active/<branch>/state.json          ← 격리 키 = 작업 (git 브랜치와 1:1)
  └ workspace: { harness: "codex", host_id: "srv-1", lease: {...} }
```

기존 병합 경로·자동 아카이브·dashboard 집계를 **그대로** 재사용한다.

## 4. "같은 서버에서 여러 하네스를 동시에" — 어떻게 대응하는가

§3 채택안에 대한 정당한 반문이다. 답은 **하네스마다 자기 브랜치 + 자기 worktree, 점유는
lease 로 배타** 다.

### 4.1 물리 배치

```
/srv/ws/
├── feat-login/     (git worktree, branch=feat-login)   ← codex 가 점유
├── feat-search/    (git worktree, branch=feat-search)  ← claude-code 가 점유
└── fix-oauth/      (git worktree, branch=fix-oauth)    ← opencode 가 점유
```

각 worktree 는 자기 브랜치를 체크아웃하므로 `get_current_branch()` 가 별도 설정 없이
서로 다른 slug 를 돌려준다(§2.3 의 `parents[3]` anchor). 하네스가 몇 종이든 메모리는
브랜치별로 갈린다.

**핵심 규칙: 하네스는 워크스페이스를 고르는 게 아니라 워크스페이스에 배정된다.**
"codex 의 워크스페이스" 가 아니라 "`feat-login` 워크스페이스를 지금 codex 가 잡고 있다".

### 4.2 배타 점유 (lease)

> ⚠️ **§5D 에서 교체됨**: 아래 파일 lease 설계는 **브랜치 선점(`git push`)** 으로
> 대체됐다. git 의 ref 생성이 원자적이라 별도 lease 파일·TTL·registry 가 필요 없다
> (5-way 동시 경합에서 정확히 1명 획득 실측). 본 절은 배경으로 남긴다.

같은 워크스페이스를 두 하네스가 동시에 잡으면 격리가 무너진다. 그래서 점유는 배타여야
한다. lease 는 워크스페이스 안에 두고, 필드는 최소로 한다.

| 필드 | 의미 |
| --- | --- |
| `harness` | 지금 점유한 하네스 이름 |
| `host_id` | 서버 식별자 — registry 발급 안정 ID (§4.5) |
| `acquired_at` / `expires_at` | 만료 기반 회수 (죽은 에이전트가 영구 점유하는 것 방지) |
| `session_id` | 누가 잡았는지 추적 |

만료를 두는 이유: 에이전트가 죽으면 lease 를 놓지 못한다. TTL 이 없으면 사람이 손으로
치워야 한다.

### 4.3 왜 하네스별 디렉터리보다 나은가

- 같은 기능을 여러 하네스가 만져도 **한 브랜치 안**에서 순차 처리된다 (§3.1 해소).
- 한 하네스가 두 기능을 만지면 **두 워크스페이스로 자연히 갈린다** (§3.1 해소).
- 병합은 그냥 git 병합이다 (§3.2 해소).
- 자동 아카이브가 그대로 동작한다 (§3.3 해소).

### 4.4 하네스 축이 사라지는 것은 아니다

하네스별 역량 차이(sub-agent 유무, 병렬성)는 여전히 의미가 있다 —
`strategic_threads.md` THREAD-005 *하네스 인지형 오케스트레이션* 이 다루는 축이다.
다만 그건 **워크스페이스를 나누는 기준이 아니라 워크스페이스에 하네스를 배정하는
기준**이다. Antigravity 는 병렬 fan-out 이 되니 큰 작업에, Codex 는 순차이니 작은
작업에 — 이런 판단에 `workspace.harness` 메타데이터를 쓴다.

## 4.5 서버 식별자 — hostname 도 IP 도 *식별자* 로는 쓰지 않는다

"서버를 hostname 으로 식별할까, IP 로 할까" 는 자연스러운 질문이지만, 이 저장소의 실제
기록을 보면 **둘 다 이미 시도됐고 둘 다 실패했다.** 새로 정하기 전에 그 데이터를 본다.

### 4.5.1 실측 — 기존 필드는 거의 채워지지 않았다

task 템플릿에는 이미 `호스트명` / `호스트 IP` 필드가 있다. 전체 메모리
(`active` + `archive` + `release`, 66개 파일)에서 실제 값을 세어 보면:

| 필드 | 값 | 건수 |
| --- | --- | --- |
| `호스트 IP` | *(빈칸)* | 87 |
| `호스트 IP` | `127.0.0.1` | 20 |
| `호스트 IP` | `192.168.0.139` | 12 |
| `호스트명` | *(빈칸)* | 35 |
| `호스트명` | `homelab (darwin)` | 2 |

**압도적 다수가 빈칸이다.** 사람이 손으로 채우는 식별자는 채워지지 않는다.

### 4.5.2 채워진 값도 식별자 구실을 못 한다

- **`127.0.0.1` (20건)** — 모든 호스트가 자기 자신에게 `127.0.0.1` 이다. 이 값은
  **아무것도 식별하지 않는다.**
- **`192.168.0.139` (12건)** — DHCP 사설 대역. 재접속하면 바뀌고, 다른 LAN 의 다른
  장비가 같은 주소를 갖는다. 이 머신의 현재 `en0` 도 `192.168.0.139` 라 값 자체는
  맞지만, **맞다는 걸 확인할 방법이 없다는 게 문제다.**
- **`homelab` (2건)** — 이 머신의 실제 hostname 은
  `iyeong-gyun-ui-MacBookAir.local` 이다. 기록된 `homelab` 은 사람이 부르는 별명이고
  **이미 실제 값과 갈라져 있다.**

즉 hostname 은 *drift* 하고, IP 는 *재사용* 된다. 둘 다 시간이 지나면 거짓이 된다.

### 4.5.3 결정

**서버 식별자는 registry 가 발급한 안정적 ID (`host_id`) 를 정본으로 둔다.**
hostname 과 IP 는 식별자가 아니라 **사람이 읽는 진단 정보**로 강등한다.

| 항목 | 역할 | 채우는 주체 |
| --- | --- | --- |
| `host_id` | **정본 식별자.** lease/registry 가 참조 | registry 등록 시 1회 발급 |
| `hostname` | 진단용 표시 | 자동 수집 (`socket.gethostname()`) |
| `ip` | 진단용 표시(선택) | 자동 수집, **신뢰하지 않음** |

근거:

1. **손으로 채우면 안 채워진다** — §4.5.1 이 그 증거다. 자동 수집만이 유효하다.
   `create_environment_record_stub` 도 `hostname` 을 **호출자가 넘기는 필수 인자**로
   두고 있어(`read_only_registry.py:207`) 자동 수집이 아니다. 같은 함정이다.
2. **식별자는 변하면 안 된다** — hostname 도 IP 도 변한다. 워크스페이스 lease 가
   가리키는 대상이 조용히 바뀌면 배타 점유가 깨진다.
3. **registry 는 어차피 필요하다**(§7) — host 목록을 이미 들고 있으므로 ID 발급 주체로
   자연스럽다.

### 4.5.4 IP 를 아예 버리지는 않는 이유

중앙이 워크스페이스에 *접속* 해야 하는 경우(원격 호스트 운영)에는 주소가 필요하다. 다만
그건 **식별이 아니라 접속 정보**다. registry 에 `endpoint` 로 따로 두고, 바뀔 수 있는
값으로 다룬다 — `host_id` 는 그대로인 채 `endpoint` 만 갱신된다.

> 정리: **`host_id` 로 식별하고, hostname/IP 로 사람에게 보여주고, endpoint 로 접속한다.**
> 세 가지를 한 필드에 섞으면 셋 다 못 한다.

### 4.5.5 인벤토리를 따로 관리할 것인가 — 이미 한 번 시도됐다

"호스트 정보를 별도 인벤토리로 관리하자" 는 자연스러운 다음 수순이고, **이 저장소는 이미
그 자리를 만들어 뒀다.** 다만 비어 있다.

실측:

| 확인 | 결과 |
| --- | --- |
| `state.json` 이 선언한 `environment_path` | `ai-workflow/memory/active/environments/` |
| 그 디렉터리 실제 존재 | **없음** (`No such file or directory`) |
| bootstrap 기본값 | `--environment-dir ai-workflow/memory/active/environments/` (`bootstrap_lib/__main__.py:315`) |
| 전용 생성 도구 | `create_environment_record_stub` (MCP) — 존재 |
| **그 기록을 읽는 코드** | **없음** — `environment_path` 는 `project_docs.py:266` 에서 읽어 `builder.py:445` 로 **state.json 에 그대로 옮겨 담기만** 한다 |

즉 인벤토리는 **경로 · 기본값 · 생성 도구까지 갖췄는데 소비자가 없어서 비어 있다.**
`create_environment_record_stub` 의 출력도 `draft_record` 문자열 배열일 뿐, 저장 위치도
스키마도 강제하지 않는다 (`- Python 버전: N/A`, `- 프로젝트 루트: N/A` 같은 빈 골격).

**이것이 §4.5.1 의 빈칸 87건과 같은 실패다** — 쓰는 곳은 있는데 읽는 곳이 없으면 아무도
채우지 않는다. 인벤토리를 새로 만들 때 이 함정을 반복하지 않는 것이 설계 조건이다.

### 4.5.6 결정 — 인벤토리는 만들되, "읽는 쪽" 부터 만든다

인벤토리(= §7 의 workspace registry)를 별도로 두는 것에는 **찬성**한다. `host_id` 발급
주체가 필요하고(§4.5.3), 중앙이 in-flight 상태를 아는 유일한 경로이기 때문이다(§5A.3).

다만 기존 `environments/` 의 실패를 반복하지 않기 위한 조건을 붙인다.

| 조건 | 이유 |
| --- | --- |
| **소비자를 먼저 만든다** | 읽는 코드 없이 만들면 `environments/` 처럼 빈 채로 남는다. 취합 뷰·lease 중재가 registry 를 *실제로 읽어야* 한다 |
| **자동 생성** | 손으로 채우면 안 채워진다(§4.5.1). 워크스페이스 생성 시 도구가 등록한다 |
| **git 밖에 둔다** | 브랜치에 실려 다니면 중앙이 in-flight 를 못 본다(§5A.3). `environments/` 가 git 안이라 브랜치마다 갈라지는 문제도 같다 |
| **기존 `environments/` 와 역할을 겹치지 않는다** | 아래 참조 |

**역할 분리**: 두 개를 하나로 합치지 않는다.

- `environments/` — *사람이 읽는* 환경 기록 (Python 버전, venv, 검증 도구 상태). 진단용.
  스냅샷 성격, 자주 안 변한다.
- **workspace registry** — *기계가 읽는* 운영 상태 (`host_id`, path, branch, harness,
  lease). 배정·취합의 입력. 자주 변한다.

섞으면 "자주 변하는 값" 과 "가끔 쓰는 문서" 가 한 파일에서 충돌한다 — v1.0.0 이
branch-scoped memory 로 없앤 바로 그 문제다.

> 정리: **인벤토리는 따로 관리한다. 단 `environments/` 를 채우는 방식이 아니라, 읽는
> 소비자를 먼저 갖춘 registry 로 만든다.** 비어 있는 `environments/` 는 그 자리에 무엇을
> 두면 안 되는지 알려주는 증거다.

## 5. 중앙 메인 에이전트의 역할

`workflow_agent_topology.md` §5 의 오케스트레이터 원칙을 워크스페이스 축으로 확장한다.

- **한다**: 워크스페이스 배정(어떤 작업을 어느 하네스에), lease 중재, 취합 뷰 생성,
  병합 순서 결정, `main` 관리, 사용자 보고.
- **하지 않는다**: 워크스페이스 *안* 의 구현. 그건 그 워크스페이스의 에이전트 몫이고,
  거기서는 contract v1 이 그대로 적용된다.

즉 계층이 둘로 겹친다:

```
중앙 에이전트  ──(워크스페이스 배정 / lease / 병합)──▶  워크스페이스
                                                        └ 로컬 오케스트레이터
                                                            └(contract v1 위임)▶ worker
```

**contract v1 을 확장해 워크스페이스 배정까지 넣지 않는다.** contract v1 은 "한 세션 안의
위임" 계약이고, 워크스페이스 배정은 "세션 자체를 만드는" 층이다. 섞으면 두 계약이 서로를
오염시킨다.

## 5A. 세션 시작 흐름 — 하네스는 업무 지시를 어떻게 받는가

본 절은 2026-08-07 에 **실제 worktree 를 만들어 실측**한 결과에 기반한다. 실측 절차와
원문 결과는 §5A.5 에 남긴다.

### 5A.1 핵심 제약 — 지시는 "전달"되지 않고 "워크스페이스에 놓인다"

가장 중요한 사실부터. `session-start` 는 **인자로 받은 경로의 문서만 읽는다.** 중앙에서
하네스로 지시를 push 하는 채널이 없고, 만들 필요도 없다.

> **하네스는 메시지를 받는 게 아니라, 자기 워크스페이스에 놓인 상태 문서를 읽는다.**

따라서 "업무 지시" 의 실체는 **워크스페이스 안의 `session_handoff.md` + 오늘 backlog**
다. 중앙 에이전트가 하는 일은 명령을 보내는 것이 아니라 **그 문서를 미리 써 두는 것**이다.
이것이 기존 워크플로우와 정합하는 유일한 지시 경로다 — 새 프로토콜을 만들지 않는다.

### 5A.2 실측된 함정 — 새 워크스페이스는 그냥 시작되지 않는다

새 worktree 를 만들고 그 안에서 `session-start` 를 돌리면 **실패한다**:

```
status: error
error_code: missing_required_document
warnings: ["session-start 기준선을 복원할 수 없어 후속 판단을 중단한다."]
recommended_next_action: None
```

이유: `active/<branch>/` 는 브랜치를 만든다고 생기지 않는다. 새 브랜치의 메모리
디렉터리는 **아무도 만들어 주지 않는다.**

**그래서 배정의 첫 단계는 "브랜치 생성" 이 아니라 "메모리 seed" 다.** 이 단계를 빠뜨리면
하네스는 시작하자마자 멈춘다 — 실측된 실패 모드다.

### 5A.3 실측된 제약 — 중앙은 in-flight 작업을 볼 수 없다

`ai-workflow/memory/` 는 **git 으로 추적된다** (`git ls-files` 확인). 따라서 각 worktree 는
자기 체크아웃에 커밋된 브랜치 메모리만 본다.

실측: worktree 에 `active/demo-feat-login/state.json` 을 만든 뒤 중앙(main worktree)에서
`_branch_state_paths()` 를 호출하면:

```
central rglob sees:
    ai-workflow/memory/active/main/state.json      ← demo-feat-login 은 안 보인다
```

> **중앙의 취합 뷰는 "커밋되고 합쳐진 것" 만 본다.** 진행 중 작업은 구조적으로 보이지
> 않는다.

이건 결함이 아니라 성질이다. §6 의 "취합은 파생 뷰" 원칙과 정합한다 — 커밋 전 작업은
사실이 아니기 때문이다. 다만 **중앙이 "지금 누가 뭘 하는지" 를 알려면 별도 경로가
필요**하다. 그 경로가 §4.2 의 lease 이고, lease 를 registry(중앙에서 읽는 단일 지점)에
두어야 하는 이유가 여기서 나온다. state.json 에만 두면 중앙에서 안 보인다.

### 5A.4 세션 시작 흐름

위 두 실측을 반영한 흐름이다. 굵은 단계가 기존에 없던 부분이다.

**A. 중앙 에이전트 (배정 시점)**

1. `main` 에서 취합 뷰를 만든다 — 합쳐진 것 기준의 현재 상태.
2. 다음 작업을 고르고 워크스페이스 1개 = 작업 1개로 자른다.
3. 하네스를 **배정**한다 (§4.4 — 역량 기준. 병렬 fan-out 되는 하네스에 큰 작업).
4. **lease 획득** — 이미 점유 중이면 배정하지 않는다.
5. worktree + 브랜치 생성.
6. **메모리 seed (필수)** — `active/<branch>/` 에 `session_handoff.md` + 오늘 backlog +
   task 파일을 쓴다. **이 문서 자체가 업무 지시다.** §5A.2 의 실패를 막는 단계.
7. 하네스 세션을 그 worktree 에서 연다.

**B. 하네스 에이전트 (세션 시작)**

8. 자기 워크스페이스에서 `session-start` 실행 → `status: ok` 면 기준선 복원 완료.
   `get_current_branch()` 가 worktree 의 브랜치를 자동으로 잡으므로 별도 설정이 필요 없다
   (실측: worktree 안에서 `demo-feat-login` 반환).
9. 이후는 **기존 워크플로우 그대로** — contract v1 위임, backlog 갱신, 세션 종료 순서
   (memory 갱신 → commit → push).

**C. 합류**

10. 하네스가 push. 메모리가 브랜치에 함께 실려 온다.
11. 중앙이 병합 → 그 시점에 비로소 취합 뷰에 나타난다 (§5A.3).
12. `merge-doc-reconcile` 로 정합 복구. **lease 해제.**

### 5A.5 지시에 무엇을 담는가

`session_handoff.md` 는 이미 "다음 세션이 이어받는" 형식이다. 워크스페이스 배정은 그
형식을 그대로 쓴다 — 새 스키마를 만들지 않는다. 최소 항목:

| 항목 | 왜 |
| --- | --- |
| 작업 축 1줄 | `session-start` 의 `summary` 로 나온다 |
| 범위 밖 명시 | 하네스가 옆 워크스페이스 영역을 건드리면 병합이 깨진다 |
| task 파일 링크 | backlog ↔ state 정합 (린터의 `task_status_mismatch` 회피) |
| 완료 기준 | 검증 없이 done 처리 방지 (표준 §작업 원칙) |

### 5A.6 실측 절차 (재현용)

```bash
git worktree add <path> -b demo-feat-login
cd <path> && python3 -c "from workflow_kit.common.paths import get_current_branch; print(get_current_branch())"
#   -> demo-feat-login   (worktree 별 자동 분리 확인)
python3 workflow-source/skills/session-start/scripts/run_session_start.py \
  --session-handoff-path ai-workflow/memory/active/demo-feat-login/session_handoff.md ...
#   -> status: error / missing_required_document   (seed 없으면 시작 불가)
```

`archive_branch_memory.py --dry-run` 도 함께 확인했다 — 살아 있는 브랜치는
`skip (git 에 브랜치가 살아 있음)` 으로 보호되고, git 에서 사라진 것만 `ARCHIVE` 대상이
된다. **동시 운영 중인 다른 워크스페이스의 메모리를 치우지 않는다.**

## 5B. 다중 호스트 동시 작업 — 충돌 최소화 (실측 기반)

여러 호스트에서 여러 에이전트가 동시에 일할 때 무엇이 실제로 충돌하는지를,
**bare remote + 2 클론으로 재현해** 측정했다. 기존 문서(`memory/active/README.md` §2)의
충돌 표면 표는 *한 저장소 안* 을 전제하므로, 다중 호스트에서 다시 검증할 필요가 있었다.

### 5B.1 실측 결과 요약

| 시나리오 | 결과 | 심각도 |
| --- | --- | --- |
| 서로 다른 브랜치, 브랜치별 메모리(`active/<branch>/`) | **깨끗이 병합** — `feat-a` / `feat-b` 양쪽 보존 | ✅ 문제없음 |
| 서로 다른 브랜치, **공유 append-only 파일**(`log.md`) | **CONFLICT** | 🔴 실측 |
| 같은 브랜치, 파일 **통째 rewrite** | **조용한 데이터 소실** (충돌 표시 없음) | 🔴🔴 최악 |
| 같은 브랜치, **진짜 append**(`>>`) | CONFLICT (충돌 표시 있음) | 🟡 복구 가능 |

두 가지가 핵심이다.

**(1) 브랜치별 물리 격리는 실제로 작동한다.** `active/feat-a/` 와 `active/feat-b/` 는
서로 다른 호스트에서 만들어져도 병합 시 충돌 0 이었다. §3 의 격리 키 결정이 다중
호스트에서도 유효함을 확인했다.

**(2) 남은 충돌은 전부 *공유 파일* 에서 나온다.** 브랜치를 갈라도 `log.md` 처럼 브랜치
바깥에 있는 파일은 그대로 충돌한다. `memory/active/README.md` §2 는 `log.md` 를
*"❌ append-only (충돌 없음)"* 으로 분류하지만, **그건 한 저장소 안의 이야기다.** 두
호스트가 각자 append 하면 git 은 같은 줄 위치의 서로 다른 내용으로 보고 CONFLICT 를 낸다.

### 5B.2 가장 위험한 것 — 조용한 소실

같은 브랜치에서 두 에이전트가 daily backlog index 를 **통째로 다시 쓰면**, 나중에 push
한 쪽이 앞의 것을 지운다. 실측:

```
A 커밋: - TASK-001 from agent A
B 커밋: - TASK-002 from agent B     (A 를 fetch 한 뒤 whole-file rewrite)
HEAD  : - TASK-002 from agent B     ← TASK-001 소실
```

**git 은 아무 충돌도 보고하지 않는다.** 히스토리에는 남아 있지만 HEAD 에는 없다. 반면
같은 상황에서 *진짜 append*(`>>`) 를 하면 git 이 CONFLICT 를 낸다 — 시끄럽지만 안전하다.

> **원칙: 조용한 소실보다 시끄러운 충돌이 낫다.** append-only 규약
> (`memory/active/README.md` §4 *"절대 기존 section 수정 ❌"*)이 스타일 권고가 아니라
> **데이터 보존 장치**인 이유가 이것이다.

> ⚠️ **§5C.2 에서 정정됨**: 위 소실은 *손으로 파일을 덮어썼을 때* 재현된 것이다.
> 저장소의 실제 도구(`upsert_backlog_entry`)는 read-modify-write 라 이렇게 동작하지
> 않는다 — 도구를 쓰면 충돌이 *보이게* 난다. 위험은 **도구 우회**에 있다.

### 5B.3 방안 1 — `.gitattributes` union merge (가장 효과 큼)

공유 append-only 파일에 union merge 를 걸면 위 충돌이 **자동 해소**된다. 실측으로
확인했다:

```gitattributes
ai-workflow/memory/log.md                      merge=union
ai-workflow/memory/**/telemetry/*.jsonl        merge=union
ai-workflow/memory/active/**/backlog/*.md      merge=union
```

- 적용 전: `log.md` CONFLICT
- 적용 후: `- A entry` / `- B entry` **양쪽 보존, 충돌 0**
- daily backlog index 에도 적용 시 A·B 의 task 항목이 모두 살아남음

**이 저장소에는 현재 `.gitattributes` 가 없다** (실측). 즉 위 `log.md` 충돌은 오늘도
재현 가능한 상태다. 다중 호스트로 가기 전에 넣는 것이 비용 대비 효과가 가장 크다.

### 5B.4 union merge 를 걸면 안 되는 것 — JSON

**`state.json` 에는 절대 걸지 않는다.** 실측:

```
union merge 결과: {"a":3}
                  {"a":2}
→ json.JSONDecodeError: Extra data: line 2 column 1
```

union 은 "양쪽 줄을 다 남긴다" 이므로 **구조화 포맷을 깨뜨린다.** 줄 단위로 의미가
독립적인 파일(로그, jsonl, 링크 목록)에만 안전하다.

`state.json` 은 union 이 필요 없다 — **파생 파일**이기 때문이다
(`memory/active/README.md` §4: *"손으로 편집하지 않는다. 항상 rebuild"*).
충돌하면 한쪽을 고르고 `generate_workflow_state.py` 로 다시 만들면 된다. 이것을 규약으로
명시한다.

| 파일 | 병합 전략 | 근거 |
| --- | --- | --- |
| `log.md`, `*.jsonl`, daily backlog index | `merge=union` | 줄 단위 독립, 실측 검증 |
| `state.json` | **union ❌** — 아무거나 고른 뒤 **rebuild** | 파생 파일, union 시 JSON 깨짐(실측) |
| `active/<branch>/**` | 전략 불필요 | 물리 격리로 애초에 안 만남(실측) |
| task 파일 | 전략 불필요 | 1 task = 1 file, 소유자 단일 |

### 5B.5 방안 2 — 운영 규칙 (도구 없이 즉시 적용)

1. **워크스페이스 1개 = 브랜치 1개 = 에이전트 1개.** §4.2 의 lease 가 이걸 강제한다.
   같은 브랜치에 둘을 붙이지 않으면 §5B.2 의 소실은 구조적으로 안 생긴다.
2. **공유 파일은 append 만.** 통째 rewrite 금지 — 소실이 조용하기 때문이다.
3. **`state.json` 은 손대지 않고 rebuild.** 병합 후 항상 재생성.
4. **task ID 에 브랜치 slug 포함** — 이미 규약이다(`TASK-<date>-<slug>-<NNN>`). 호스트가
   달라도 브랜치가 다르면 번호가 겹치지 않는다.

### 5B.6 방안 3 — 합류 순서 직렬화

중앙이 병합을 **한 번에 하나씩** 처리한다. 동시 병합을 허용하지 않으면 3-way 상황 자체가
줄어든다. 이는 `merge-doc-reconcile` 의 전제(*"병합 이전 두 상태를 임의로 합쳐 사실처럼
확정하지 않는다"*)와도 정합한다.

병합 큐는 registry(§7)가 들고 있기 좋다 — lease 와 같은 자리다.

### 5B.7 재현 절차

```bash
git init --bare origin.git && git clone origin.git hostA && git clone origin.git hostB
# hostA: feat-a 브랜치 + active/feat-a/ + log.md append
# hostB: feat-b 브랜치 + active/feat-b/ + log.md append
# 중앙에서 둘 다 merge → log.md 만 CONFLICT, active/* 는 clean
```

### 5B.8 우선순위

| 순위 | 조치 | 비용 | 효과 |
| --- | --- | --- | --- |
| 1 | `.gitattributes` union merge 추가 | 매우 낮음 (파일 1개) | 실측된 충돌 대부분 제거 |
| 2 | 공유 파일 whole-file rewrite 금지 규약 명시 | 낮음 | **조용한 소실 차단** |
| 3 | lease 로 브랜치당 에이전트 1명 강제 | 중간 (§7 구현) | 같은 브랜치 충돌 원천 차단 |
| 4 | 병합 직렬화 | 중간 | 3-way 상황 감소 |

1·2 는 **다중 호스트가 아니어도 지금 적용 가능하고, 지금도 유효하다.**

## 5C. 우선순위별 상세 검토 (실측)

§5B.8 의 4개 조치를 각각 실측으로 검토했다. **결과적으로 P1·P2 는 유지, P3 는 구현 방식이
바뀌었고, P4 는 강등됐다.**

### 5C.1 P1 — `.gitattributes` union merge ✅ 채택 (조건부)

**검증한 것과 결과**:

| 엣지 케이스 | 결과 |
| --- | --- |
| JSONL(telemetry) union | ✅ 3줄 전부 valid JSON — 안전 |
| union 병합본을 **저장소 자체 파서**(`parse_backlog`)로 파싱 | ✅ task 4건 전부 인식, 상태 정확, warning 0 |
| daily index 머리말 중복 | ✅ 중복 0 (`# Backlog Index` / `## Tasks` / `최종 수정일` 각 1회) |
| **동일 내용 2줄 append** | ⚠️ **중복 제거됨 — 2 이벤트가 1줄로 합쳐짐** |

**발견된 한계 (중요)**: union merge 는 *같은 줄* 을 하나로 접는다. 두 호스트가
`- session start` 같은 **동일 문자열**을 append 하면 한 건이 조용히 사라진다.

**완화**: append 하는 줄에 **고유값(타임스탬프 + host_id)** 을 포함시킨다. 실측으로
`- 2026-08-07T10:00 hostA session start` / `...hostB...` 는 양쪽 모두 보존됐다. 즉
union 을 쓰려면 **로그 라인 포맷에 host 식별자를 넣는 것이 짝 조건**이다. §4.5 의
`host_id` 가 여기서 두 번째 용도를 갖는다.

**적용 대상** (실측 기반):

```gitattributes
ai-workflow/memory/log.md                    merge=union
ai-workflow/memory/**/telemetry/*.jsonl      merge=union
ai-workflow/memory/active/**/backlog/*.md    merge=union
```

`state.json` 은 제외 — §5B.4 에서 JSON 이 깨짐을 실측했다.

### 5C.2 P2 — whole-file rewrite 금지 ✅ 유지 (단, 진단이 정정됨)

**정정**: §5B.2 에서 "통째 rewrite → 조용한 소실" 을 실측했는데, 그건 내가 손으로 파일을
덮어쓴 경우였다. **저장소의 실제 도구는 그렇게 동작하지 않는다.**

`workflow_writes.py:150` `upsert_backlog_entry` 는 read-modify-write 다 — 기존 내용을
읽어 해당 task block 만 교체하고 나머지는 보존한다(`_upsert_index_block`). 두 호스트가
각자 다른 task 를 추가한 실측:

```
hostA 파일: 900 있음 / 901 없음
hostB 파일: 900 없음 / 901 있음
git merge (union 없이) → CONFLICT (조용한 소실 ❌, 시끄러운 충돌 ✅)
git merge (union 적용) → 900·901 both 보존, 파서 4건 정상 인식
```

즉 **도구를 통해 쓰는 한 조용한 소실은 발생하지 않는다.** 위험은 *도구를 우회해 손으로
파일을 덮어쓸 때* 생긴다.

> **규약 문구 정정**: "whole-file rewrite 금지" 가 아니라 **"backlog/handoff 는 반드시
> 도구(`backlog-update` 등)를 통해 갱신하고, 손으로 통째 덮어쓰지 않는다"**. 도구는 이미
> 올바르게 동작하므로 새 구현이 필요 없고, **문서 규약만 명시하면 된다** — 비용 최저,
> 효과 유지.

### 5C.3 P3 — lease ⚠️ 채택하되 **구현 방식 변경**

세 가지를 실측했다.

**(a) 로컬 FS 배타성 — 안전**: `os.open(O_CREAT|O_EXCL)` 로 10 프로세스 동시 경합 →
**정확히 1명만 획득**. 로컬에서는 이것으로 충분하다.

**(b) git 에 lease 를 두면 안 됨 — 확증**: 두 호스트가 각자 lease 파일을 커밋하면 둘 다
"내가 획득했다" 고 믿고 일하다가 **병합 시점에야 CONFLICT 로 발견**된다. 배타 제어로
쓸모가 없다. §4.5.6 의 "registry 는 git 밖" 결정을 이 실측이 뒷받침한다.

**(c) TTL 회수에 race 가 있다 — 설계 수정 필요**: 만료된 lease 를 회수하는 순진한 구현
(읽고 → 만료 확인 → 덮어쓰기)은 **동시에 훔치면 2명이 동시 획득**한다. 실측:

```
thief2 -> ACQUIRED(new)
thief4 -> ACQUIRED(stole from slow-agent)    ← 배타성 붕괴 + 크래시
```

**해법 (실측 검증)**: 회수도 원자적 연산으로 승자를 정한다 — 고유 임시파일 생성 후
`os.link()`(원자적)로 claim 을 걸고, 이긴 쪽만 `os.replace`. 5 프로세스 동시 경합 재실측:

```
thief5 -> ACQUIRED(stole from slow)
나머지 4 -> denied
```

**정확히 1명.** TTL 을 쓰려면 이 패턴이 필수다.

**남은 제약**: 위 원자성은 **같은 파일시스템** 전제다. 여러 호스트가 NFS 등으로 공유하면
`O_EXCL`/`link` 의 원자성 보장이 약해진다. 진짜 다중 호스트에서는 파일 lease 대신 작은
서비스(또는 DB의 unique constraint)가 필요하다 — §7 의 열린 질문과 연결된다.

### 5C.4 P4 — 병합 직렬화 ⬇️ **강등 (별도 구현 불필요)**

**실측 결과 git 이 이미 직렬화한다.** 두 클론이 같은 브랜치에 동시 push 하면:

```
X pushed OK
Y: ! [rejected] main -> main (fetch first)
```

진 쪽은 `git pull` 후 재시도하면 되고, 실측에서 **양쪽 엔트리가 모두 보존**된 뒤 정상
push 됐다. ref 업데이트가 원자적이므로 **애플리케이션 레벨 병합 큐는 중복**이다.

또한 union 을 적용한 상태에서 3개 브랜치를 연속 병합해도 충돌 0, 순서 보존이었다.

> **결론**: P4 는 "구현할 것" 이 아니라 **"push 거부 시 pull 후 재시도" 라는 운영 규칙**
> 으로 충분하다. 별도 큐는 §7 에서 뺀다. 단, *병합 순서* 를 사람이 정해야 하는 경우
> (릴리스 순서 등)는 별개 문제이며 그때는 registry 가 큐를 들 수 있다.

### 5C.5 검토 후 우선순위

| 순위 | 조치 | 변경 | 비용 |
| --- | --- | --- | --- |
| 1 | `.gitattributes` union + **로그 라인에 host_id/타임스탬프** | 조건 추가 | 매우 낮음 |
| 2 | "도구를 통해 갱신" 규약 명시 | 문구 정정 (구현 불필요) | 매우 낮음 |
| 3 | lease — **원자적 claim 패턴** 필수, git 밖 | 구현 방식 변경 | 중간 |
| ~~4~~ | ~~병합 직렬화~~ | **강등** — git 이 이미 함 | 0 |

## 5D. 원격 브랜치 선점 플로우 — lease 를 대체한다 (실측)

§4.2 는 배타 점유를 **파일 lease** 로 설계했다. 그런데 "세션 시작 시 원격 활성 브랜치를
조회 → 작업 선정 → 브랜치 생성 + 1회 push 로 예정 내역 공유" 라는 플로우를 실측한 결과,
**이 플로우가 별도 lease 를 대체한다.** §4.2/§5C.3 의 파일 lease 설계는 이것으로 교체한다.

### 5D.1 핵심 실측 — push 자체가 원자적 배타 획득이다

5개 클론이 **같은 브랜치명을 동시에** 선점 시도:

```
agent3 WON
agent1 lost / agent2 lost / agent4 lost / agent5 lost
```

**정확히 1명.** git 의 ref 생성이 원자적이므로, `git push origin <branch>` 는
**분산 compare-and-swap** 이다. §5C.3 에서 파일 lease 에 필요했던 `os.link` 원자 claim
패턴을 **git 이 이미 서버 측에서 제공**한다.

이것이 왜 중요한가 — §5C.3 의 파일 lease 는 세 가지 문제가 있었다:

| 파일 lease 문제 | 브랜치 선점에서는 |
| --- | --- |
| TTL 회수 race (2명 동시 획득 실측) | **없음** — 회수 개념 자체가 없다 |
| 같은 파일시스템 전제 (NFS 취약) | **없음** — git 서버가 단일 판정자 |
| registry 저장 위치 미해결(§7) | **없음** — 원격 저장소가 곧 registry |

**결론: 다중 호스트에서 파일 lease 보다 브랜치 선점이 우월하다.** 새 인프라가 0 이다.

### 5D.2 TOCTOU 는 문제되지 않는다

"조회 시점엔 없었는데 push 직전에 남이 선점" 하는 경우를 실측했다:

```
c1: 조회 -> 'new-task' 없음, 선점 가능하다고 판단
c2: 그 사이 선점 완료
c1: push -> rejected (fetch first)
```

**조회 결과가 낡아도 안전하다.** 판정은 조회가 아니라 push 에서 일어나므로, 조회는
*후보 선정용 힌트* 이고 **push 가 유일한 진실**이다. 이 성질 덕에 조회-push 사이에 락이
필요 없다.

### 5D.3 세션 시작 시 조회 가능한 것 (실측)

clone 이나 checkout 없이 원격만으로 다른 에이전트 현황을 볼 수 있다.

```bash
git ls-remote --heads origin              # 활성 브랜치 목록
git log origin/<branch> --format='%an %ar' -1   # 누가, 언제
git show origin/<branch>:<path>           # 남의 작업계획을 체크아웃 없이 읽기
```

실측 출력:

```
feat-login     owner=A    age=39 seconds ago
race-branch    owner=c3   age=28 seconds ago
```

즉 **"1회 push 로 예정 내역 공유"** 가 실제로 동작한다 — 다른 에이전트가
`git show origin/<branch>:<plan>` 으로 읽는다. §5A.1 의 "지시는 워크스페이스에 놓인다"
와 같은 원리가 *에이전트 사이* 에도 적용된다.

### 5D.4 남는 취약점 두 가지 — 사람 확인 게이트로 닫는다

두 취약점 모두 **자동 처리하지 않고 사용자 확인을 거치는 것**으로 정한다. 둘 다 잘못
자동화하면 *남의 작업을 지우는* 방향으로 실패하기 때문이다.

#### (a) TTL 부재 → **마지막 활동 1일 경과 시 사용자에게 문의**

git 은 "이 브랜치가 살아있는 작업인지" 를 모르고 **마지막 커밋 시각만** 안다. 따라서
stale 판정은 heuristic 이며, **임계값은 마지막 활동 이후 1일(86400초)** 로 둔다.

- 1일 이내 → `active`. 손대지 않는다.
- **1일 초과 → `STALE` 로 분류하고 사용자에게 문의한다.** 에이전트가 직접 삭제하거나
  선점하지 않는다.

세션 시작 시 조회 (실측 검증):

```bash
git fetch origin --prune          # ← 필수. 아래 §주의 참조
now=$(date +%s)
for ref in $(git for-each-ref --format='%(refname:short)' refs/remotes/origin \
             | grep -v 'origin/HEAD\|origin/main'); do
  ts=$(git log -1 --format='%ct' "$ref")
  age=$(( now - ts ))
  [ $age -gt 86400 ] && echo "STALE: ${ref#origin/} (idle $(( age/3600 ))h, owner $(git log -1 --format='%an' "$ref"))"
done
```

실측 출력 (0h / 12h / 72h 브랜치):

```
dead     owner=T   idle= 72h   STALE → 사용자 문의
fresh    owner=T   idle=  0h   active
half     owner=T   idle= 12h   active
```

> **주의 — `fetch` 를 먼저 하지 않으면 오판한다.** 다른 호스트가 그 브랜치를 되살렸는데
> 로컬 remote-tracking ref 가 낡아 있으면 여전히 `idle=72h` 로 보인다 (실측: fetch 전
> 72h → fetch 후 0h). **살아있는 작업을 지우자고 사용자에게 제안하게 되므로**, stale
> 판정 직전에 반드시 `git fetch` 한다.

> **참고**: `%ct`(commit date)를 쓴다. `%at`(author date)는 rebase/cherry-pick 시
> 원본 시각을 유지하므로 *활동성* 지표로 부적합하다.

사용자에게 문의할 때 함께 제시할 것: 브랜치명, owner, idle 시간, 마지막 커밋 메시지,
그리고 `git show origin/<branch>:<plan>` 로 읽은 작업 예정 내역. 판단 근거 없이
"지울까요?" 만 묻지 않는다.

#### (b) `--force` → **사용자 확인 없이 실행 금지**

`git push --force` 는 브랜치 선점의 배타성을 뚫는다 (실측: `forced update` 로 남의
브랜치를 덮어씀). 배타성이 *규약* 이지 *강제* 가 아니므로:

- **에이전트는 `--force` / `--force-with-lease` 를 자율적으로 실행하지 않는다.**
  워크스페이스 브랜치에 대해서는 **반드시 사용자 확인을 받고 진행**한다.
- push 가 `rejected` 되면 그것은 *뚫어야 할 장애* 가 아니라 **다른 에이전트가 이미
  그 작업을 가져갔다는 신호**다. 기본 대응은 §5D.5 5 번 — 다른 작업을 고른다.
- 가능하면 서버측 branch protection / pre-receive hook 으로 이중화한다. 규약만으로는
  실수를 막지 못한다.

> 두 항목의 공통 원칙: **되돌릴 수 없는 작업(남의 브랜치 삭제·덮어쓰기)은 에이전트가
> 단독으로 결정하지 않는다.**

### 5D.5 플로우 (채택안)

**세션 시작**

1. **`git fetch origin --prune`** (필수 — §5D.4 주의) 후
   `git for-each-ref refs/remotes/origin` — 활성 브랜치 = 진행 중 작업 목록.
2. 각 브랜치의 owner / 최종 활동 시각 조회. **1일 초과 무활동은 `STALE` 로 분류해
   사용자에게 문의한다** (에이전트가 삭제·선점하지 않는다, §5D.4a).
3. 겹치지 않는 작업을 고른다. (조회는 힌트일 뿐 — §5D.2)

**선점 (= 배타 획득)**

4. 브랜치 생성 + **메모리 seed**(§5A.2 — 없으면 `session-start` 가 실패한다) +
   작업 예정 내역 작성.
5. `git push origin <branch>` **1회**.
   - 성공 → 선점 완료. 이 순간이 lease 획득 시점이다.
   - **rejected → 남이 이미 가져갔다는 신호. 1로 돌아가 다른 작업을 고른다.**
     `--force` 로 뚫지 않는다 — 필요하다고 판단되면 **사용자 확인을 받는다**(§5D.4b).

**작업 / 종료**

6. 이후는 기존 워크플로우 그대로 (§5A.4 B·C).
7. 병합 후 브랜치 삭제 = **lease 해제**. `archive_branch_memory.py` 가 git 에 없는
   브랜치의 메모리를 정리하므로(§3.3) 해제가 메모리 정리까지 연결된다.

### 5D.6 설계 변경 요약

| 항목 | 이전(§4.2/§5C.3) | 변경 후 |
| --- | --- | --- |
| 배타 점유 | 파일 lease + TTL + 원자 claim | **브랜치 push (git ref CAS)** |
| lease 저장 위치 | git 밖 registry (미해결) | **원격 저장소 자체** |
| 만료 회수 | TTL 자동 회수 (race 실측) | **자동 회수 없음** — 1일 초과 시 사용자 문의 |
| 필요한 새 인프라 | registry 서비스/DB | **없음** |
| 남은 위험 | NFS 원자성, race | `--force` 우회(→ 사용자 확인), stale 판정 heuristic |

**registry(§7)는 여전히 필요하지만 역할이 줄어든다** — 배타 제어는 git 이 맡고, registry 는
`host_id` ↔ 워크스페이스 경로 매핑과 in-flight 가시성(§5A.3)만 담당한다.

## 6. 취합은 파생 뷰로 둔다

§2.2 의 원칙을 그대로 승계한다. 중앙에 mutable 집계 파일을 만들지 않는다.

- 취합 결과는 **언제든 워크스페이스들에서 다시 계산 가능**해야 한다.
- 집계 파일을 두면 워크스페이스가 늘 때마다 그 파일이 충돌 지점이 된다 — v1.0.0 이
  없앤 바로 그 문제를 다시 만드는 셈이다.

## 7. 확장 지점 (미구현 제안)

> 이 절은 **제안이며 검증되지 않았다**.

현재 `_branch_state_paths(root)` 는 **단일 root** 만 받는다. 여러 worktree 를 가로지르려면
여기가 확장 지점이다.

1. **workspace registry** — 서버 계층의 실체. `{path, branch, harness, host_id, endpoint, lease}`
   목록 (§4.5 — `host_id` 발급 주체이기도 하다). **소비자(취합 뷰 / lease 중재)를 같은
   사이클에 함께 만든다** — §4.5.5 의 `environments/` 가 소비자 없이 만들어져 비어 있는
   전례가 있다. git 밖에 둔다. §1 표의 "서버 = 없음" 을 메우는 산출물. **§5A.3 실측으로 우선순위가 올라갔다** —
   메모리가 git-tracked 라 중앙이 in-flight 워크스페이스를 볼 수 없으므로, registry 는
   "있으면 좋은 것" 이 아니라 **중앙이 현재 상황을 아는 유일한 경로**다. git 밖에 두어야
   한다(브랜치에 실려 다니면 안 됨).
2. **메모리 seed 도구** — 새 워크스페이스에 `active/<branch>/` 를 만들고 handoff +
   backlog + task 를 쓴다. §5A.2 에서 이게 없으면 `missing_required_document` 로 세션이
   시작조차 못 함을 실측했다. **배정 자동화의 최소 단위.**
3. **복수 root 취합** — `_branch_state_paths` 가 root 목록을 받도록. registry 가 무엇을
   훑을지 알려준다.
4. **lease 도구** — **§5D 에서 대체됨**. 배타 점유는 브랜치 선점(`git push`)이 담당하므로
   별도 lease 도구를 만들지 않는다. 대신 필요한 것은 (a) 원격 브랜치 현황 조회
   (`fetch --prune` 선행 필수), (b) **1일 초과 stale 브랜치를 사용자에게 문의**
   (자동 삭제 ❌), (c) **`--force` 는 사용자 확인 후에만** 이다.

~~5. 병합 직렬화 큐~~ — **§5C.4 에서 제외**. git 의 ref 업데이트가 이미 직렬화하며
(non-fast-forward push 거부 실측), "거부되면 pull 후 재시도" 운영 규칙으로 충분하다.

**착수 순서**: 1 → 2 → 3 → 4. registry 가 없으면 3 이 무엇을 훑을지 모르고, 2 가 없으면
배정해도 하네스가 시작하지 못한다.

미해결 질문:

- 아직 병합되지 않은(in-flight) 워크스페이스의 상태를 취합 뷰에 어떤 신뢰도로 표시할
  것인가. 커밋 전 작업은 "사실" 이 아니다. (§5A.3 이 이 질문을 구체화했다 — 선택지는
  "안 보여준다" 와 "lease 기반으로 *진행 중* 이라고만 표시한다" 둘이다.)
- 워크스페이스가 여러 **호스트**에 흩어지면 registry 를 어디에 두는가. (§5D 로 *배타
  제어* 는 git 이 맡게 되어 이 질문의 범위가 줄었다 — registry 는 `host_id` 매핑과
  in-flight 가시성만 담당한다.)
- ~~lease TTL 만료와 실제 작업 중단 사이의 간극~~ — **§5D.4 에서 결정 완료**: 자동
  회수하지 않고, 마지막 활동 **1일 초과 시 사용자에게 문의**한다. 되돌릴 수 없는 작업은
  에이전트가 단독으로 결정하지 않는다.
- seed 한 지시와 하네스가 실제로 한 일이 갈라졌을 때(범위 이탈) 병합 시점에 어떻게
  잡아낼 것인가.

## 8. 범위 밖

- 하네스별 프롬프트/역량 튜닝 — THREAD-005 소관.
- cross-repo(여러 저장소) 취합 — 본 문서는 **한 저장소의 여러 worktree** 까지만 다룬다.
- CI 통합.

## 다음에 읽을 문서

- 설정 계층: [./workflow_configuration_layers.md](./workflow_configuration_layers.md)
- 에이전트 토폴로지: [./workflow_agent_topology.md](./workflow_agent_topology.md)
- 위임 계약: [./orchestrator_subagent_contract_v1.md](./orchestrator_subagent_contract_v1.md)
- 메모리 거버넌스: [../MEMORY_GOVERNANCE.md](../MEMORY_GOVERNANCE.md)
