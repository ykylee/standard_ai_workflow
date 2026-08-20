---
type: decision
status: accepted
adr_id: ADR-026
decided_at: 2026-08-20
alternatives_considered: [stay-on-v01, v02-only-drop-legacy, emit-both-bundles, omit-status-entirely]
related_pages: [decisions/adr-006-okf-compat-frontmatter, decisions/adr-007-okf-consumer-mode, decisions/adr-011-okf-version-auto-detect, concepts/okf-open-knowledge-format]
last_ingested_from: https://raw.githubusercontent.com/GoogleCloudPlatform/knowledge-catalog/main/okf/SPEC.md
created: 2026-08-20
updated: 2026-08-20
r9_skip: true
---

# ADR-026: OKF v0.2 이행 — legacy 를 남긴 채 정규 필드를 더한다

## Status

**Accepted** (2026-08-20). ADR-006 이 2026-06-16 에 고정한 `okf_version: "0.1"` 을
대체한다. 근거는 SPEC 원문 재취득(v0.2, 1003줄)이고, 48차(2026-08-18)의
상호운용 실측이 이 결정의 배경이다.

## Context

ADR-006 은 v0.1 을 **명시적으로** 고정했다. 그래서 버전을 올리려면 새 ADR 이
필요하다 — 그것이 이 문서다.

48차에 [langchain-ai/openwiki](https://github.com/langchain-ai/openwiki) 와의
상호운용을 실측하면서 **SPEC 이 v0.2 로 움직였다**는 사실이 드러났다. 이번에
SPEC 원문을 다시 받아 §13(Changes from v0.1)을 직접 대조했다.

### v0.2 가 바꾼 것

§13 이 스스로 정리한다. **breaking 2건**:

| v0.1 | v0.2 | 소비자 fallback (§13.1) |
|---|---|---|
| `timestamp` | `generated.at` | "MAY fall back to a legacy `timestamp`" |
| 본문 `# Citations` | `sources` (frontmatter) | "MAY still parse a legacy `# Citations`" |

**나머지는 전부 additive** — `sources` 신용 신호, `generated`/`verified`,
`status`, `stale_after`, `Attested Computation` 타입, `# Computation` 헤딩.
"Their absence yields a plain v0.1 concept."

즉 **legacy 형태를 남긴 채 정규 필드를 더하면 한 번들이 v0.1·v0.2 소비자를 다
만족한다.** 이 관측이 이 ADR 의 축이다.

### 실질 위험은 `status` 하나

§5.4 가 `status: draft | stable | deprecated` 로 정하고 **`Absent status ⇒
stable`** 이라고 못 박는다. 우리 값 분포(71장)는:

| 우리 값 | 장수 |
|---|---|
| `active` | 42 |
| `accepted` | 25 |
| `draft` | 2 |
| `proposed` | 1 |

§11 의 관용 보장("consumers MUST NOT reject ... unknown additional frontmatter
keys")은 **unknown key 에만** 걸린다. `status` 는 v0.2 에서 *정규 필드로
승격*됐으므로 그 보장 밖이다 — v0.2 소비자가 `stable` 필터를 걸면 **71장 중
69장이 조용히 빠진다.** 거부되는 게 아니라 **필터에서 사라진다**는 점이 더
나쁘다: 아무 오류도 안 난다.

**그리고 `status` 를 빼는 것도 답이 아니다.** 부재가 `stable` 로 정의돼 있으니
생략은 "안 정함" 이 아니라 **stable 이라는 주장**이다.

## Decision

**`okf_version` 을 `"0.2"` 로 올린다. legacy 형태는 남기고, v0.2 정규 필드를
더한다.**

1. **버전 리터럴은 한 곳** — `okf_export.OKF_SPEC_VERSION` 이 정본이고
   `okf_import.OUR_OKF_VERSION` 은 거기서 **파생**한다(문자열과 튜플을 따로
   적어 두면 한쪽만 올렸을 때 조용히 갈라진다). 상수를 export 쪽에 두는 것은
   의존 방향 때문이다 — `okf_import` 가 `okf_export` 를 참조한다.

2. **`status` 어휘 매핑 + 원문 보존**

   | 우리 | OKF v0.2 | 근거 |
   |---|---|---|
   | `active`, `accepted`, `stable` | `stable` | §5.4 "ready for consumption" |
   | `draft`, `proposed` | `draft` | §5.4 "not yet reviewed; possibly incomplete" |
   | `deprecated`, `superseded` | `deprecated` | §5.4 "kept for links and history" |
   | 그 밖의 값 | `draft` | 아래 참조 |

   원래 값은 `wiki_status` 확장 키로 보존한다 — 그쪽은 unknown key 라 §11 의
   관용 보장이 걸린다. 어휘 밖의 값을 `stable` 로 올리거나 필드를 생략하면
   **모르는 것을 통과로 세는** 것이 되므로, 가장 보수적인 `draft` 로 내린다.

3. **`sources` 를 emit 한다** (§5.1) — 우리 `last_ingested_from` 이 정확히 이
   필드가 말하는 "이 개념이 파생된 재료" 다. v0.1 에서 in-repo 경로는 `resource`
   로 못 나가고 본문 산문(`# Citations`)으로만 남았는데, §5.1 은 entry 의
   `resource` 값으로 **번들 상대 경로와 범위 서술도** 허용한다. 그래서 in-repo
   출처가 처음으로 기계가 읽는 필드에 들어간다.

4. **legacy 를 지우지 않는다** — `timestamp` 와 본문 `# Citations` 를 그대로
   낸다. §13.1 이 두 fallback 을 모두 명시하므로 v0.2 소비자도 손해가 없고,
   아직 v0.1 만 아는 소비자(openwiki 포함)는 계속 읽을 수 있다.

5. **더 낮은 minor 를 거부하지 않는다** — 소비자 정책을 고친다. 아래 참조.

6. **`generated` / `verified` 는 채택하지 않는다** — 아래 참조.

## 이행하면서 드러난 결함: 소비자가 v0.1 을 거부하고 있었다

ADR-011 의 버전 정책은 `older → error (refusing)` 였다. 우리가 v0.1 인 동안에는
**도달 불가능한 분기**라 아무도 밟지 않았다. v0.2 로 올리는 순간 그 분기가
살아나 **v0.1 번들 전부를 거부**한다 — 48차에 실측으로 상호운용을 확인한
openwiki 가 정확히 `okf_version: "0.1"` 이다.

SPEC 은 정반대를 말한다:

- §12 — "Consumers that do not understand the declared version SHOULD attempt
  best-effort consumption rather than refusing the bundle."
- §13 — "A v0.1 bundle is consumable by a v0.2 consumer under the fallbacks
  noted here."

그래서 **같은 major 의 낮은 minor 는 `pass`** 로 바꿨다. 우리는 그 fallback 을
실제로 구현하고 있으므로(§13.1 의 `timestamp` 와 `# Citations` 를 여전히 읽고
쓴다) 근거 있는 통과다. 더 낮은 major 는 아직 존재하지 않으며, 만나면 `warn`
으로 "모른다" 고 말한다.

> 버전을 올리는 일은 **생산 형식만의 문제가 아니었다.** 소비 정책을 같이 보지
> 않았다면 이번 이행이 유일하게 실측된 상호운용을 조용히 끊었을 것이다.

## 채택하지 않은 것: `generated` / `verified`

§5.2 는 `generated.by` 를 **REQUIRED** 로 두고 §7 은 그것을 actor 로 규정한다
(`<producer>/<version>` / `human:<id>` / `process:<id>`).

우리 wiki 는 **페이지별 저자·생성 주체를 기록하지 않는다.** 채우려면 둘 중
하나인데 둘 다 거짓이다:

- 도구 이름(`workflow_kit.okf_export/...`) → "이 도구가 내용을 썼다" 는 거짓.
  exporter 는 변환만 한다.
- `human:<id>` → wiki score 대시보드 같은 **생성물 페이지까지** 사람이 쓴 것이
  된다. §5.3 이 `human:` 접두사로 trust tier 를 올리므로 이건 신뢰 등급을
  부풀리는 거짓말이 된다.

§13.1 의 `timestamp` fallback 이 이 자리를 덮으므로, **비워 두는 편이
정확하다.** 저장소 규칙 *없는 것을 있는 것처럼 채우지 않는다* 의 적용이다.

페이지별 actor 를 실제로 기록하게 되면(예: git 이력에서 파생) 그때 다시 연다.

## 대안 검토

| 대안 | 기각 사유 |
|---|---|
| **v0.1 유지** | 지금 당장의 손실은 없지만, v0.2 소비자가 등장하는 순간 `status` 필터로 69/71 장이 조용히 사라진다. 그 시점에는 우리가 모른다 — 오류가 안 나니까. |
| **v0.2 만, legacy 제거** | §13.1 의 fallback 은 소비자 쪽 *선택*(`MAY`)이다. legacy 를 지우면 그 선택을 안 한 소비자에게서 provenance 와 시각이 사라진다. 남겨도 비용이 거의 없다. |
| **v0.1·v0.2 번들 2벌 발행** | 배포 표면이 2배가 되고 둘이 갈라질 자리가 생긴다. legacy 병행이면 한 벌로 족하다. |
| **`status` 생략** | §5.4 가 `Absent status ⇒ stable` 이라 생략이 곧 stable 주장이다. `draft`/`proposed` 페이지를 stable 로 만든다. |

## Consequences

- `wk okf-export` 산출물이 `okf_version: "0.2"` 를 선언하고 `status` 는 v0.2
  어휘로, 우리 원문은 `wiki_status` 로 나간다.
- in-repo 출처가 `sources` 로 기계 판독 가능해진다.
- 우리 소비자가 v0.1 번들을 받아들인다 (이전에는 거부했을 것).
- `check_okf_export` 20→24 cases, `check_okf_import` 25→27 cases. 버전 리터럴을
  박은 단언은 정본 상수 참조로 바꿨다 — 버전이 오를 때마다 검사가 red 가 되면
  그 검사는 계약이 아니라 그 시점 상수를 지키는 것이다.

## 관련 문서

- [OKF SPEC v0.2](https://raw.githubusercontent.com/GoogleCloudPlatform/knowledge-catalog/main/okf/SPEC.md) (1003줄, §5 · §11 · §12 · §13)
- [[decisions/adr-006-okf-compat-frontmatter]] — 이 ADR 이 대체하는 v0.1 고정
- [[decisions/adr-011-okf-version-auto-detect]] — 소비자 버전 정책 (본 ADR 이 older 분기를 수정)
- [[concepts/okf-open-knowledge-format]] — SPEC 정리
