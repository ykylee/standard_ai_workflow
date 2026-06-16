---
type: concept
status: proposed
last_ingested_from: internal (this page is the rule definition, not ingest of an external source)
r9_skip: true
verification_status: N/A (internal rule definition)
contradiction_flags: []
related_pages: [concepts/okf-open-knowledge-format, decisions/adr-006-okf-compat-frontmatter, decisions/adr-007-okf-consumer-mode, patterns/wiki-stub-emit, patterns/r4-anchor-index, concepts/wiki-source-rule-r9]
created: 2026-06-16
updated: 2026-06-16
---

# V-T1 Rule: wiki frontmatter `title` ↔ body H1 일치 강제

- 문서 목적: ADR-006 (OKF 5-field bridge) 채택으로 wiki frontmatter 에 optional `title` field 가 추가됨. `title` 과 body 첫 `# ` (H1) heading 이 *동일한 정보를 다른 syntax* 로 표현 — prose 도중 H1 변경 시 frontmatter 미갱신 위험. V-T1 lint 가 이 일치를 강제.
- 범위: lint 정의 (rule + mode matrix) + 7 test + ADR 후보 (ADR-009)
- 최종 수정일: 2026-06-16

## §0 Status Notice  {#s0-status}

| # | 항목 | 값 |
|---|---|---|
| 1 | status | **proposed** — ADR-009 채택 시 `active` 전환 |
| 2 | rule ID | **V-T1** (Title consistency) |
| 3 | 도입 예정 버전 | v0.7.33 (PATCH, ADR-009 채택 시) |
| 4 | 면제 범위 | 없음 (모든 wiki page 강제) |
| 5 | Lint 심각도 | **mode-conditional** (strict: error / loose: warn) — ADR-007 §3 mode matrix 통합 |
| 6 | 관련 ADR | ADR-006 (OKF 5-field bridge, follow-up 3) + ADR-007 (mode matrix 통합 의무) |
| 7 | Lint 위치 | `workflow-source/tests/check_wiki_title_consistency.py` (PoC, 7 test) |

## §1 TL;DR  {#s1-tldr}

| # | 항목 | 값 |
|---|---|---|
| 1 | Rule ID | **V-T1** |
| 2 | 강제 invariant | wiki page 의 `title` frontmatter field 와 body 첫 `# H1` heading 이 **exact match** (post-trim, post-collapse-whitespace) |
| 3 | frontmatter `title` 부재 시 | OK (body H1 만으로 충분) — `title` 이 optional 이므로 (ADR-006 §3) |
| 4 | body H1 부재 시 | **error in strict, warn in loose** — body H1 없는 page 는 markdown 아님 |
| 5 | mismatch | **error in strict, warn in loose** — 동일 정보 다른 표현 |
| 6 | Lint 심각도 | strict mode = error (현재 wiki 의 R-8/R-9 strict 정책과 양립), loose mode = warn (OKF spec §9 의 MUST NOT reject 정책) |
| 7 | 자동 fix | **scope 외** — 운영자가 명시적 결정. lint 는 report 만 |
| 8 | 면제 marker | 없음 (모든 page 적용) |

## §2 Rule Definition  {#s2-rule}

### §2.1 Invariant

A wiki page 가 V-T1 을 통과하려면:

1. body 에 정확히 하나의 `# H1` heading 이 존재 (선두에 위치 권장, 그러나 strict invariant 아님)
2. `title` frontmatter field 가 존재하면, 그 값이 body `# H1` 의 trimmed text 와 **exact match** (post-collapse-whitespace)
3. `title` field 가 없으면 V-T1 PASS (frontmatter `title` optional, ADR-006 §3)

### §2.2 Normalization

비교 전 양쪽 normalize:

| Step | Frontmatter `title` | Body `# H1` |
|---|---|---|
| 1 | raw string | `# ` prefix 제거 |
| 2 | strip leading/trailing whitespace | strip leading/trailing whitespace |
| 3 | collapse multiple internal whitespace → single space | 동일 |
| 4 | lowercase 비교 (대소문자 무시) | 동일 |

→ normalize 후 양쪽이 **byte-equal** 이어야 PASS.

### §2.3 Edge Cases

| Case | Behavior | Mode |
|---|---|---|
| `title: ""` (empty) | error (frontmatter 의 `title` 가 빈 string 이면 *없다* 가 아니라 *있다-but-empty* — 의미상 동일하지만 lint 입장에선 fail) | strict error / loose warn |
| body 가 H1 없이 시작 (e.g. H2 부터) | error (H1 부재) | strict error / loose warn |
| body H1 이 multiple (e.g. `# foo ... # bar`) | error (H1 uniqueness) | strict error / loose warn |
| frontmatter `title` 이 markdown syntax 포함 (e.g. `**bold**`) | normalize 후 비교. bold marker 제거 후 비교 | strict + loose 동일 |
| frontmatter `title` 이 line break 포함 (`title: "foo\nbar"`) | normalize 후 비교 (collapse whitespace) | strict + loose 동일 |
| body H1 이 line break 포함 | error (heading text 가 line break 가질 수 없음, markdown spec) | strict + loose 동일 |

## §3 Mode Matrix (ADR-007 §3 통합)  {#s3-mode-matrix}

| Mode | Lint 결과 | Exit code | 예시 출력 |
|---|---|---|---|
| strict (default) | error | 1 | `FAIL: [V-T1] <path>: title "X" != H1 "Y"` |
| loose (OKF consumer) | warn | 0 | `WARN: [V-T1] <path>: title "X" != H1 "Y"` |

→ V-T1 의 mode 동작은 ADR-007 §3 의 mode matrix (8 lint × 2 mode) 의 한 row. ADR-009 가 V-T1 을 *formal rule* 로 채택 시 ADR-007 mode matrix 도 동시 갱신.

## §4 Example  {#s4-example}

### §4.1 PASS — frontmatter title matches body H1

```markdown
---
type: concept
title: V-T1 Rule: wiki frontmatter `title` ↔ body H1 일치 강제
---

# V-T1 Rule: wiki frontmatter `title` ↔ body H1 일치 강제

body...
```

→ normalize 후 양쪽 byte-equal. V-T1 PASS.

### §4.2 PASS — frontmatter title absent, body H1 present

```markdown
---
type: concept
---

# R9 Rule: wiki-ingest source = `archive/` only

body...
```

→ frontmatter `title` 없음. V-T1 PASS (rule §2.1 case 2).

### §4.3 FAIL — mismatch

```markdown
---
type: concept
title: R9 Source Rule
---

# R9 Rule: wiki-ingest source = `archive/` only

body...
```

→ normalize: `R9 Source Rule` vs `R9 Rule: wiki-ingest source = archive/ only`. byte-unequal. V-T1 FAIL.

## §5 Linter Spec  {#s5-linter}

### §5.1 Location

`workflow-source/tests/check_wiki_title_consistency.py` (PoC, 7 test). 기존 `check_wiki_*.py` 와 동일 importlib-based test runner pattern.

### §5.2 CLI

```bash
python3 tests/check_wiki_title_consistency.py          # default strict mode
python3 tests/check_wiki_title_consistency.py --mode=loose   # OKF consumer mode
```

### §5.3 Test Cases (7 test)

| # | Test | Expected |
|---|---|---|
| 1 | `test_title_matches_h1` | frontmatter `title` = body `# H1` trimmed → PASS |
| 2 | `test_title_absent_passes` | frontmatter `title` 없음, body H1 있음 → PASS |
| 3 | `test_title_mismatch_fails_strict` | frontmatter `title` ≠ body H1, strict mode → error |
| 4 | `test_title_mismatch_warns_loose` | frontmatter `title` ≠ body H1, loose mode → warn (exit 0) |
| 5 | `test_h1_absent_fails` | body H1 부재 → error (strict + loose 둘 다 fail, 단 loose 는 warn) |
| 6 | `test_h1_normalization_whitespace` | H1 의 internal whitespace collapse 후 비교 | PASS |
| 7 | `test_h1_uniqueness` | body 의 H1 이 multiple → error | strict error / loose warn |

### §5.4 Failure Message Format

```
FAIL: [V-T1] ai-workflow/wiki/concepts/foo.md: title "X" != H1 "Y"
```

또는 loose mode:

```
WARN: [V-T1] ai-workflow/wiki/concepts/foo.md: title "X" != H1 "Y"
```

## §6 Rationale  {#s6-rationale}

### §6.1 Why enforce?

- **Single source of truth**: `title` (frontmatter) + H1 (body) 가 동일 정보 중복 → 어느 한쪽만 갱신 시 drift
- **OKF interop**: ADR-006 의 OKF export 시 `title` 이 frontmatter 우선 (없으면 body H1 derive). 두 source 의 일치 강제 시 OKF `title` 의 source 명확.
- **Search snippet quality**: `title` 일치 = search 결과 의 preview 가 page 의 *visual* title 과 일치 → 운영자/사용자 혼란 감소
- **Linter ROI 높음**: cheap to compute (2 string compare) + high signal (drift 즉시 detect)

### §6.2 Why optional (not required)?

- `title` field 가 없는 page 도 PASS (rule §2.1 case 2) — 기존 wiki page 의 100% 가 `title` field 미사용. 강제 required 시 모든 page 갱신 필요.
- ADR-006 의 *bridge* 정신 — frontmatter `title` 은 *enabler*, not *enforcee*. body H1 만으로 충분.
- 점진적 채택: 운영자가 frontmatter `title` 추가 → V-T1 이 자연스럽게 enforce.

### §6.3 Why not auto-fix?

- Auto-fix 는 *어느 쪽을 source of truth* 로 할지 결정 필요 (frontmatter vs body) — 운영자의 의도된 mismatch (e.g. frontmatter 는 short label, body H1 은 descriptive) 가능
- Lint 의 역할 = *report*, fix = 운영자. R-7 (semantic conflict LLM review) 와 일치.

## §7 Compliance  {#s7-compliance}

- [SCHEMA.md §5.1](../SCHEMA.md) R1~R9: R-9 면제 (in-repo source 정의 자체), R-8 (status) 와 무관
- [ADR-006 §3](../decisions/adr-006-okf-compat-frontmatter) Decision 1: frontmatter `title` optional + body H1 derive — V-T1 이 두 source 일치 강제
- [ADR-007 §3](../decisions/adr-007-okf-consumer-mode) mode matrix: 8 lint × 2 mode table 의 한 row 로 V-T1 추가
- [OKF SPEC.md §4.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md): `title` recommended field — V-T1 이 OKF `title` 의 source 일관성 보장

## §8 Related  {#s8-related}

- [[concepts/okf-open-knowledge-format]] — V-T1 의 1차 trigger. ADR-006 의 `title` field 추가 → drift 가능성.
- [[decisions/adr-006-okf-compat-frontmatter]] — ADR-006 §5 Negative 2 ("Title/description 중복 위험") 가 V-T1 의 source.
- [[decisions/adr-007-okf-consumer-mode]] — V-T1 의 mode matrix 가 ADR-007 의 mode matrix 와 통합.
- [[patterns/wiki-stub-emit]] — wiki stub emit 시 frontmatter `title` 자동 populate 패턴. V-T1 의 PASS case 1 와 직접 연결.
- [[patterns/r4-anchor-index]] — index.md 의 `### [[path]] {#anchor}` anchor 가 V-T1 의 `title` 과 무관 (별도 namespace).
- [[concepts/wiki-source-rule-r9]] — R-9 의 `last_ingested_from` 와 V-T1 의 `title` 는 독립 frontmatter field. lint matrix 양립.

## §9 Revision Log  {#s9-revision-log}

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-006 follow-up 3 + ADR-007 §3 mode matrix 통합 의무 기반. 7 test case 정의. | Sisyphus (orchestrator) |
